"""JobPilot API — Flask backend, full pipeline."""

import json
import os
from datetime import datetime, timezone

import logging
from functools import wraps

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

logger = logging.getLogger(__name__)

from models import db, User, Search, Subscription, CachedJob, PendingDiscovery
from parser import parse_resume, ParseError
from searcher import search_jobs as run_search
from verifier import verify_all_jobs, verify_one
from generator import generate_cover_letter
from exporter import export_excel
from daily_refresh import daily_refresh
from promise import filter_by_promise

load_dotenv()

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL", "sqlite:///jobpilot.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10MB

CORS(app, origins=[
    os.getenv("FRONTEND_URL", "http://localhost:3000"),
    "http://localhost:3000",
    "https://jobpilot-plum.vercel.app",
    "https://jobpilot.vercel.app",
], supports_credentials=True)
db.init_app(app)

# Rate limiting — prevent API abuse
limiter = Limiter(get_remote_address, app=app, default_limits=["60 per minute"],
                  storage_uri="memory://")

FREE_SEARCH_LIMIT = 3


def require_admin(f):
    """Decorator that checks X-Admin-Secret header against ADMIN_SECRET env var."""
    @wraps(f)
    def decorated(*args, **kwargs):
        secret = request.headers.get("X-Admin-Secret", "")
        if secret != os.getenv("ADMIN_SECRET", ""):
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated


# ── Helpers ────────────────────────────────────────────────

def _get_user_or_mock(google_id: str = None) -> User | dict:
    """Get user from DB or return mock for dev."""
    if google_id:
        user = User.query.filter_by(google_id=google_id).first()
        if user:
            return user
    # Dev mock
    return {
        "id": 0, "google_id": "dev", "email": "dev@test.com",
        "name": "Dev User", "plan": "free", "searches_used": 0,
    }


# ── Health ─────────────────────────────────────────────────

@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "ts": datetime.now(timezone.utc).isoformat()})


@app.route("/api/debug/tables")
def debug_tables():
    """Temporary: show what tables exist in the database."""
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(db.engine)
        table_names = inspector.get_table_names()
        db_url = str(app.config.get("SQLALCHEMY_DATABASE_URI", "?"))
        safe_url = db_url.split("@")[-1] if "@" in db_url else db_url[:30]
        tables = {}
        for name in table_names:
            try:
                tables[name] = db.session.execute(text(f'SELECT COUNT(*) FROM "{name}"')).scalar()
            except Exception:
                tables[name] = None
        return jsonify({
            "tables": tables,
            "db_host": safe_url[:60],
            "cached_jobs_exists": "cached_jobs" in tables,
            "cached_jobs_count": tables.get("cached_jobs"),
        })
    except Exception as e:
        return jsonify({"error": str(e), "type": type(e).__name__}), 500


# ── Demo verifier (no auth, rate-limited) ─────────────────

@app.route("/api/demo-verify")
@limiter.limit("5 per hour")
def demo_verify():
    """Free URL verifier — no signup required. The landing page hook."""
    url = request.args.get("url", "").strip()
    if not url:
        return jsonify({"error": "Please paste a job posting URL", "status": "error"}), 400
    if not url.startswith("http"):
        url = "https://" + url
    if len(url) > 2000:
        return jsonify({"error": "URL too long", "status": "error"}), 400

    from verifier import verify_one

    # Detect board type from URL
    board = "direct"
    if "greenhouse.io" in url:
        board = "greenhouse"
    elif "lever.co" in url:
        board = "lever"
    elif "workday" in url:
        board = "workday"

    job = {"title": "", "company": "", "apply_url": url, "job_board": board}

    try:
        result = verify_one(job, {"degree_level": "Master"}, {"visa_needed": False})
        a = result.get("audit", {})

        # Try to extract title/company from the page
        import requests as req
        from bs4 import BeautifulSoup
        try:
            r = req.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "lxml")
                title_tag = soup.find("title")
                if title_tag:
                    result["page_title"] = title_tag.get_text(strip=True)[:120]
                # Try OG tags
                og_title = soup.find("meta", property="og:title")
                if og_title:
                    result["job_title"] = og_title.get("content", "")[:100]
                og_site = soup.find("meta", property="og:site_name")
                if og_site:
                    result["company"] = og_site.get("content", "")[:60]
        except Exception:
            pass

        status_str = a.get("status", "⚠ Unverified")
        verified_open = "Open" in status_str and "Closed" not in status_str
        return jsonify({
            "verified_open": verified_open,
            "status": status_str,
            "confidence": a.get("confidence", "low"),
            "reason": a.get("reason", "Could not determine"),
            "posting_age_days": a.get("posting_age_days"),
            "ghost_risk": a.get("ghost_risk", "unknown"),
            "job_title": result.get("job_title", result.get("page_title", "")),
            "company": result.get("company", ""),
            "url": url,
        })
    except Exception as e:
        return jsonify({
            "verified_open": False,
            "status": "⚠ Unverified",
            "confidence": "low",
            "reason": f"Verification error: {str(e)[:80]}",
            "url": url,
        })


# ── Auth: sync user ────────────────────────────────────────

@app.route("/api/sync-user", methods=["POST"])
def sync_user():
    data = request.get_json() or {}
    google_id = (data.get("google_id") or "").strip() or None
    email = (data.get("email") or "").strip().lower()

    if not google_id and not email:
        return jsonify({"error": "email or google_id required"}), 400

    user = None
    if google_id:
        user = User.query.filter_by(google_id=google_id).first()
    if not user and email:
        user = User.query.filter_by(email=email).first()
        if user and google_id and (not user.google_id or user.google_id.startswith("email:")):
            user.google_id = google_id
            db.session.commit()

    if not user:
        plan = "pro" if email in ("chrishchen2510@gmail.com", "cherishchen2510@gmail.com") else "free"
        user = User(
            google_id=google_id or f"email:{email}",
            email=email,
            name=data.get("name", ""),
            avatar_url=data.get("avatar_url") or data.get("image"),
            plan=plan,
        )
        db.session.add(user)
        db.session.commit()
    elif user.email in ("chrishchen2510@gmail.com", "cherishchen2510@gmail.com") and user.plan != "pro":
        user.plan = "pro"
        db.session.commit()

    remaining = max(0, FREE_SEARCH_LIMIT - user.searches_used) if user.plan == "free" else 999
    result = user.to_dict()
    result["searches_remaining"] = remaining
    return jsonify(result), 200


# ── GET /api/me ────────────────────────────────────────────

@app.route("/api/me")
def me():
    google_id = request.args.get("google_id")
    if not google_id:
        return jsonify({"error": "Authentication required"}), 401
    user = User.query.filter_by(google_id=google_id).first()
    if not user:
        return jsonify({"error": "User not found"}), 404
    result = user.to_dict()
    result["searches_remaining"] = max(0, FREE_SEARCH_LIMIT - user.searches_used) if user.plan == "free" else 999
    return jsonify(result)


# ── POST /api/parse ────────────────────────────────────────

@app.route("/api/parse", methods=["POST"])
@limiter.limit("10 per minute")
def parse_resume_route():
    import base64

    file_bytes = None
    filename = "upload.docx"

    # Method 1: multipart/form-data (browser upload)
    if "file" in request.files:
        file = request.files["file"]
        if not file.filename:
            return jsonify({"error": "Empty filename. Please select a file."}), 400
        filename = file.filename
        file_bytes = file.read()

    # Method 2: JSON body with base64 resume (API/testing)
    elif request.is_json:
        data = request.get_json() or {}
        resume_b64 = data.get("resume", "")
        if not resume_b64:
            return jsonify({"error": "No resume provided. Send a file via multipart/form-data or base64 in JSON body."}), 400
        try:
            file_bytes = base64.b64decode(resume_b64)
        except Exception:
            return jsonify({"error": "Invalid base64 encoding for resume."}), 400
        filename = data.get("filename", "upload.docx")

    else:
        return jsonify({"error": "No file uploaded. Send as multipart/form-data with key 'file', or JSON with base64 'resume' field."}), 400

    if not file_bytes or len(file_bytes) == 0:
        return jsonify({"error": "Resume file is empty. Please upload a valid PDF or DOCX file."}), 400

    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in {"pdf", "docx", "doc"}:
        return jsonify({"error": f"Unsupported file type: .{ext}. Use PDF or DOCX."}), 400

    if len(file_bytes) > 10 * 1024 * 1024:
        return jsonify({"error": "File too large. Maximum size is 10MB."}), 400
    try:
        profile = parse_resume(file_bytes, filename)
        # Sanitize: force ASCII-safe JSON to eliminate all control char issues
        safe_json = json.dumps({"status": "parsed", "profile": profile}, ensure_ascii=True)
        return app.response_class(safe_json, mimetype='application/json')
    except ParseError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Unexpected: {str(e)}"}), 500


# ── POST /api/search — INSTANT from cache, fallback to live ──

@app.route("/api/search", methods=["POST"])
@limiter.limit("30 per minute")
def search_route():
    import re as _re
    data = request.get_json() or {}

    google_id = data.get("google_id")
    user = _get_user_or_mock(google_id)

    if isinstance(user, User) and user.plan == "free" and user.searches_used >= FREE_SEARCH_LIMIT:
        return jsonify({"error": "quota_exceeded", "searches_used": user.searches_used}), 402

    profile = data.get("profile", {})
    prefs = data.get("prefs", {"directions": ["DS/ML"], "job_type": "intern_2026", "visa_needed": True})
    directions = prefs.get("directions", ["DS/ML"])
    selected_regions = prefs.get("regions", ["US"])

    # ── Cache-only search (no live verification in request path) ──
    cached_count = CachedJob.query.filter_by(is_active=True).count()
    logger.info("[search] Cache has %d active jobs, regions=%s", cached_count, selected_regions)

    # Cache-only: daily GitHub Actions cron owns all live verification.
    # Empty cache → warming=true + pending discovery task enqueued.
    if True:  # kept as block to preserve indentation of cache-path body
        query = CachedJob.query.filter(
            CachedJob.is_active == True,
            CachedJob.status == "open",
            CachedJob.region.in_(selected_regions)
        )

        import re as _re
        DIRECTION_TITLE_KEYWORDS = {
            "DS/ML": ["data scien", "machine learn", "ml ", "ai ", "analytics", "algorithm", "nlp", "deep learn"],
            "Data Engineering": ["data engineer", "etl", "pipeline", "data infra"],
            "Software Engineering": ["software engineer", "software develop", "backend", "frontend", "full stack", "swe"],
            "Health Informatics": ["health", "clinical", "biomedical", "pharma", "bioinform"],
            "Business Analytics": ["business analyst", "strategy", "business intelligence", "analytics"],
            "Product Management": ["product manager", "product analyst", "program manager"],
            "Quantitative Finance": ["quant", "trading", "financial analyst"],
            "Research / NLP": ["research", "nlp", "natural language"],
            "Consulting": ["consult", "advisory"],
        }

        all_cached = query.all()
        matched = []
        for cj in all_cached:
            cats = cj.categories or []
            if not any(d in cats for d in directions):
                continue

            # Title must also match at least one keyword from selected directions
            title_lower = cj.title.lower()
            title_relevant = False
            for d in directions:
                kws = DIRECTION_TITLE_KEYWORDS.get(d, [])
                if any(k in title_lower for k in kws):
                    title_relevant = True
                    break
            # Fallback: if job title contains "intern" and category matches, still include
            # (catches generic "Data Intern" type titles)
            if not title_relevant and "intern" in title_lower:
                # Only if title has at least some data/tech signal
                tech_signals = ["data", "engineer", "scien", "analyst", "research", "ml", "ai"]
                if any(s in title_lower for s in tech_signals):
                    title_relevant = True

            if title_relevant:
                matched.append(cj)

        # Sort by date (newest first)
        matched.sort(key=lambda cj: cj.last_verified_at or cj.date_added, reverse=True)

        candidate_jobs = [cj.to_dict() for cj in matched[:20]]

        # ── FINAL GATE: Core Promise ──────────────────────
        promise_prefs = {
            "regions": selected_regions,
            "directions": directions,
            "visa_needed": prefs.get("visa_needed", False),
            "degree_level": profile.get("degree_level", "Master"),
        }
        result_jobs, promise_rejected = filter_by_promise(candidate_jobs, promise_prefs)
        result_jobs = result_jobs[:15]
        logger.info("[search] Returning %d jobs from cache (instant)", len(result_jobs))

        warming = False
        if len(result_jobs) < 3:
            warming = True
            # Create pending discovery task (dedup check)
            existing = PendingDiscovery.query.filter_by(
                status="pending"
            ).filter(
                PendingDiscovery.regions.cast(db.String).contains(str(selected_regions))
            ).first()
            if not existing:
                task = PendingDiscovery(regions=selected_regions, directions=directions)
                db.session.add(task)
                db.session.commit()
                logger.info("[search] Created pending discovery: %s x %s", selected_regions, directions)

        audit_summary = {
            "jobs_searched": cached_count, "jobs_verified": len(result_jobs),
            "jobs_open": len(result_jobs), "jobs_unverified": 0, "jobs_dropped": 0,
            "jobs_promise_rejected": len(promise_rejected),
            "cl_generated": 0, "cl_status": "pending", "source": "cache",
            "warming": warming,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # ── Zero results: clear message, not blank ──────────
    if not result_jobs:
        msg = "No jobs match your current filters."
        parts = []
        if selected_regions:
            parts.append(f"regions: {', '.join(selected_regions)}")
        if directions:
            parts.append(f"directions: {', '.join(directions)}")
        if prefs.get("visa_needed"):
            parts.append("visa sponsorship required")
        if parts:
            msg += f" ({'; '.join(parts)})"
        msg += " We're actively searching for more — check back soon."
        audit_summary["zero_reason"] = msg

    # ── Save + increment quota ──────────────────────────
    search_id = None
    if isinstance(user, User) and result_jobs:
        try:
            sr = Search(user_id=user.id, prefs_json=prefs,
                       results_json={"jobs": result_jobs}, audit_json=audit_summary)
            db.session.add(sr)
            user.searches_used += 1
            db.session.commit()
            search_id = sr.id
        except Exception:
            db.session.rollback()

    errors = [audit_summary["zero_reason"]] if audit_summary.get("zero_reason") else None
    response = {"search_id": search_id, "jobs": result_jobs, "audit_summary": audit_summary, "errors": errors}
    clean = _re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', json.dumps(response, ensure_ascii=False))
    return app.response_class(clean, mimetype='application/json')


# ── POST /api/generate-cls — generate CLs for given jobs ──
# Called AFTER /api/search returns jobs. This is the slow part.

@app.route("/api/generate-cls", methods=["POST"])
@limiter.limit("10 per minute")
def generate_cls_route():
    data = request.get_json() or {}
    jobs = data.get("jobs", [])
    profile = data.get("profile", {})

    # Validate job_id input — must resolve to a real cached job
    if not jobs and data.get("job_id"):
        from models import CachedJob
        cj = CachedJob.query.get(data["job_id"])
        if not cj:
            return jsonify({"error": f"Job {data['job_id']} not found"}), 400
        jobs = [cj.to_dict()]
    if not profile and data.get("user_id"):
        user = User.query.get(data["user_id"])
        if not user:
            return jsonify({"error": f"User {data['user_id']} not found"}), 400
        profile = {"name": user.name, "skills": [], "strongest_metrics": [], "work_history": []}

    if not jobs:
        return jsonify({"error": "No jobs provided. Send {jobs: [...], profile: {...}}"}), 400

    # Blocking endpoint is capped to 1 job to stay under Cloudflare/tunnel 30s ceiling.
    # For bulk generation use /api/generate-cls/stream.
    cl_target = 1
    results = []
    errors = []

    logger.info("[cls] Generating %d cover letters...", cl_target)
    for i, job in enumerate(jobs[:cl_target]):
        company = job.get("company", "?")
        try:
            cl = generate_cover_letter(job, profile)
            results.append({
                "index": i,
                "company": company,
                "cover_letter": cl,
            })
            logger.info("  CL %d/%d: %s — %s/%s", i+1, cl_target, company, cl.get('score', 0), cl.get('max_score', 6))
        except Exception as e:
            results.append({
                "index": i,
                "company": company,
                "cover_letter": {
                    "text": "", "word_count": 0, "score": 0, "max_score": 6,
                    "gates": {}, "needs_review": True, "error": str(e)[:100],
                    "tone": "unknown",
                },
            })
            errors.append(f"CL failed for {company}: {str(e)[:60]}")

    scores = [r["cover_letter"]["score"] for r in results if r["cover_letter"].get("text")]
    if scores:
        logger.info("[cls] Done: %d generated, avg %.1f", len(scores), sum(scores)/len(scores))
    else:
        logger.info("[cls] Done: 0 generated")

    return jsonify({
        "cover_letters": results,
        "cl_generated": len(scores),
        "avg_score": round(sum(scores) / len(scores), 1) if scores else 0,
        "errors": errors if errors else None,
    })


def _serialize_job(job: dict) -> dict:
    """Remove non-serializable fields and sanitize text for JSON."""
    import re as _re

    def _clean(v):
        if isinstance(v, str):
            # Replace control chars that break JSON
            return _re.sub(r'[\x00-\x1f\x7f]', lambda m: ' ' if m.group() in ('\n', '\r', '\t') else '', v)
        if isinstance(v, dict):
            return {dk: _clean(dv) for dk, dv in v.items() if dk not in ("soup",)}
        if isinstance(v, list):
            return [_clean(item) for item in v]
        return v

    safe = {}
    for k, v in job.items():
        if k in ("soup", "page_text"):
            continue
        safe[k] = _clean(v)
    return safe


# ── Admin: run migration for new columns ─────────────────

@app.route("/api/admin/migrate", methods=["POST"])
@require_admin
def admin_migrate():
    from sqlalchemy import text
    results = []
    # Add new columns to cached_jobs if they don't exist
    for col, coltype, default in [
        ("region", "VARCHAR(10)", "'US'"),
        ("language", "VARCHAR(5)", "'EN'"),
        ("discovery_source", "VARCHAR(30)", "'greenhouse'"),
    ]:
        try:
            db.session.execute(text(f"ALTER TABLE cached_jobs ADD COLUMN {col} {coltype} DEFAULT {default}"))
            db.session.commit()
            results.append(f"Added {col}: OK")
        except Exception as e:
            db.session.rollback()
            if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                results.append(f"{col}: already exists")
            else:
                results.append(f"{col}: error — {str(e)[:60]}")

    # Create pending_discovery table
    try:
        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS pending_discovery (
                id SERIAL PRIMARY KEY,
                regions JSON NOT NULL,
                directions JSON NOT NULL,
                requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status VARCHAR(20) DEFAULT 'pending'
            )
        """))
        db.session.commit()
        results.append("pending_discovery table: OK")
    except Exception as e:
        db.session.rollback()
        results.append(f"pending_discovery: {str(e)[:60]}")

    # Verify
    count = CachedJob.query.filter_by(is_active=True).count()
    results.append(f"Active jobs: {count}")

    return jsonify({"migration": results})


# ── GET /api/download/<search_id> ─────────────────────────

@app.route("/api/download/<int:search_id>")
def download(search_id):
    search = Search.query.get(search_id)
    if not search:
        return jsonify({"error": "Search not found"}), 404

    jobs = search.results_json.get("jobs", [])
    user = User.query.get(search.user_id)
    name = user.name.replace(" ", "_") if user else "User"
    date_str = datetime.now().strftime("%Y%m%d")

    excel_bytes = export_excel(jobs, profile_name=name)

    import io
    buf = io.BytesIO(excel_bytes)
    return send_file(
        buf,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=f"JobPilot_{name}_{date_str}.xlsx",
    )


# ── POST /api/export-direct — export without DB ──────────

@app.route("/api/export-direct", methods=["POST"])
def export_direct():
    """Export jobs to Excel directly from POST data (no DB needed for testing)."""
    data = request.get_json() or {}
    jobs = data.get("jobs", [])
    if not jobs:
        return jsonify({"error": "No jobs to export"}), 400

    name = data.get("name", "User").replace(" ", "_")
    date_str = datetime.now().strftime("%Y%m%d")
    excel_bytes = export_excel(jobs, profile_name=name)

    import io
    buf = io.BytesIO(excel_bytes)
    return send_file(
        buf,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=f"JobPilot_{name}_{date_str}.xlsx",
    )


# ── Admin: daily refresh ───────────────────────────────────

@app.route("/api/admin/wipe-and-reseed", methods=["POST"])
@require_admin
def admin_wipe():
    """Nuclear option: wipe all cached jobs and re-seed from scratch."""
    # Wipe everything
    count = CachedJob.query.delete()
    db.session.commit()
    logger.info("[admin] Wiped %d cached jobs", count)

    # Re-seed
    log = daily_refresh()
    log["wiped"] = count
    return jsonify(log)


@app.route("/api/admin/daily-refresh", methods=["POST"])
@require_admin
def admin_daily_refresh():
    log = daily_refresh()
    return jsonify(log)


@app.route("/api/admin/backfill-degree", methods=["POST"])
@require_admin
def admin_backfill_degree():
    """One-time: populate degree_required for all existing jobs."""
    from verifier import detect_degree_requirement

    jobs = CachedJob.query.filter(
        (CachedJob.degree_required == None) | (CachedJob.degree_required == "")
    ).all()

    counts = {"PhD": 0, "MS": 0, "BS": 0}
    details = []
    for cj in jobs:
        text = (cj.title or "") + " " + (cj.description or "")
        deg = detect_degree_requirement(text)
        cj.degree_required = deg
        counts[deg] += 1
        details.append({"company": cj.company, "title": cj.title, "degree": deg})

    db.session.commit()

    # Verify none remain null
    remaining = CachedJob.query.filter(
        (CachedJob.degree_required == None) | (CachedJob.degree_required == "")
    ).count()

    return jsonify({
        "updated": len(jobs),
        "counts": counts,
        "remaining_null": remaining,
        "details": details,
    })


@app.route("/api/admin/backfill-visa", methods=["POST"])
@require_admin
def admin_backfill_visa():
    """One-time: detect visa sponsorship from full job descriptions."""
    import re as _re
    import requests as req
    from verifier import detect_visa_sponsorship

    jobs = CachedJob.query.filter(
        (CachedJob.visa_sponsorship == None) | (CachedJob.visa_sponsorship == "")
    ).all()

    counts = {"confirmed": 0, "no_sponsor": 0, "unspecified": 0}
    details = []
    for cj in jobs:
        full_text = (cj.title or "") + " " + (cj.description or "")

        # Try to fetch full description from ATS API
        if cj.job_board == "greenhouse" and cj.apply_url:
            m = _re.search(r"greenhouse\.io/([^/]+)/jobs/(\d+)", cj.apply_url)
            if m:
                slug, job_id = m.group(1), m.group(2)
                try:
                    r = req.get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs/{job_id}", timeout=5)
                    if r.status_code == 200:
                        content = r.json().get("content", "")
                        full_text = cj.title + " " + _re.sub(r'<[^>]+>', ' ', content)
                except Exception:
                    pass
        elif cj.job_board == "lever" and cj.apply_url:
            try:
                # Lever posting API
                r = req.get(cj.apply_url, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
                if r.status_code == 200:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(r.text, "lxml")
                    for tag in soup(["script", "style", "nav", "footer"]):
                        tag.decompose()
                    full_text = cj.title + " " + soup.get_text(" ", strip=True)
            except Exception:
                pass

        visa = detect_visa_sponsorship(full_text)
        cj.visa_sponsorship = visa
        counts[visa] += 1
        if visa != "unspecified":
            details.append({"company": cj.company, "title": cj.title, "visa": visa})

    db.session.commit()

    remaining = CachedJob.query.filter(
        (CachedJob.visa_sponsorship == None) | (CachedJob.visa_sponsorship == "")
    ).count()

    return jsonify({
        "updated": len(jobs),
        "counts": counts,
        "remaining_null": remaining,
        "details": details,
    })


@app.route("/api/admin/fix-regions", methods=["POST"])
@require_admin
def admin_fix_regions():
    """Re-infer region for all cached jobs using updated REGION_MAP_CITIES."""
    from searcher import infer_region
    jobs = CachedJob.query.filter_by(is_active=True).all()
    fixed = []
    for cj in jobs:
        new_region = infer_region(cj.location or "")
        if new_region != cj.region:
            fixed.append({"company": cj.company, "location": cj.location,
                          "old": cj.region, "new": new_region})
            cj.region = new_region
    db.session.commit()
    return jsonify({"total": len(jobs), "fixed": len(fixed), "details": fixed})


# ── SSE: stream cover letters one by one ──────────────────

@app.route("/api/generate-cls/stream")
def stream_cls():
    """SSE endpoint: generate CLs one by one, stream as they complete."""
    import re as _re

    jobs_json = request.args.get("jobs", "[]")
    profile_json = request.args.get("profile", "{}")

    try:
        jobs = json.loads(jobs_json)
        profile = json.loads(profile_json)
    except json.JSONDecodeError:
        def error_stream():
            yield f"data: {json.dumps({'type': 'error', 'message': 'Invalid JSON input'})}\n\n"
        return app.response_class(error_stream(), mimetype='text/event-stream')

    def generate():
        for i, job in enumerate(jobs[:10]):
            company = job.get("company", "?")
            try:
                cl = generate_cover_letter(job, profile)
                # Clean control chars
                cl_clean = json.loads(
                    _re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', json.dumps(cl, ensure_ascii=False))
                )
                event = json.dumps({"type": "cl", "index": i, "company": company, "cover_letter": cl_clean})
                yield f"data: {event}\n\n"
            except Exception as e:
                event = json.dumps({"type": "cl", "index": i, "company": company,
                                   "cover_letter": {"text": "", "score": 0, "max_score": 6,
                                                    "needs_review": True, "error": str(e)[:80]}})
                yield f"data: {event}\n\n"

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return app.response_class(
        generate(),
        mimetype='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'}
    )


# ── Stripe ─────────────────────────────────────────────────

import stripe

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID")
_processed_events = set()


@app.route("/api/stripe/create-checkout", methods=["POST"])
def create_checkout():
    data = request.get_json() or {}
    google_id = data.get("google_id")

    if not stripe.api_key or "..." in (stripe.api_key or ""):
        return jsonify({"url": "/dashboard?upgraded=1"})

    user = User.query.filter_by(google_id=google_id).first() if google_id else None
    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            payment_method_types=["card"],
            line_items=[{"price": STRIPE_PRICE_ID, "quantity": 1}],
            success_url=os.getenv("FRONTEND_URL", "http://localhost:3000") + "/dashboard?upgraded=1",
            cancel_url=os.getenv("FRONTEND_URL", "http://localhost:3000") + "/pricing",
            metadata={"user_id": str(user.id) if user else "unknown"},
            customer_email=user.email if user else None,
        )
        return jsonify({"url": session.url})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/stripe/webhook", methods=["POST"])
def stripe_webhook():
    payload = request.get_data(as_text=False)
    sig = request.headers.get("Stripe-Signature")

    if not STRIPE_WEBHOOK_SECRET or "..." in (STRIPE_WEBHOOK_SECRET or ""):
        return "", 200

    try:
        event = stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)
    except ValueError:
        return jsonify({"error": "Invalid payload"}), 400
    except stripe.error.SignatureVerificationError:
        return jsonify({"error": "Invalid signature"}), 400

    if event.id in _processed_events:
        return "", 200
    _processed_events.add(event.id)
    if len(_processed_events) > 1000:
        _processed_events.clear()

    if event.type == "checkout.session.completed":
        s = event.data.object
        uid = s.metadata.get("user_id")
        if uid and uid != "unknown":
            user = User.query.get(int(uid))
            if user:
                user.plan = "pro"
                user.stripe_customer_id = s.customer
                user.stripe_sub_id = s.subscription
                db.session.commit()

    elif event.type == "customer.subscription.deleted":
        sub = event.data.object
        user = User.query.filter_by(stripe_sub_id=sub.id).first()
        if user:
            user.plan = "free"
            db.session.commit()

    elif event.type == "invoice.payment_failed":
        inv = event.data.object
        if inv.attempt_count >= 3:
            user = User.query.filter_by(stripe_customer_id=inv.customer).first()
            if user:
                user.plan = "free"
                db.session.commit()

    return "", 200


# ── Auto-create tables on startup (works with gunicorn too) ──

try:
    with app.app_context():
        db.create_all()
except Exception as e:
    logger.warning("[startup] db.create_all warning: %s", e)

# ── Run ────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=False, host="127.0.0.1", port=int(os.getenv("PORT", "5001")))
