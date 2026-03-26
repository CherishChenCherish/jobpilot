"""JobPilot API — Flask backend, full pipeline."""

import json
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from models import db, User, Search, Subscription
from parser import parse_resume, ParseError
from searcher import search_jobs as run_search
from verifier import verify_all_jobs
from generator import generate_cover_letter
from exporter import export_excel

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

        return jsonify({
            "status": a.get("status", "⚠ Unverified"),
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
            "status": "⚠ Unverified",
            "confidence": "low",
            "reason": f"Verification error: {str(e)[:80]}",
            "url": url,
        })


# ── Auth: sync user ────────────────────────────────────────

@app.route("/api/sync-user", methods=["POST"])
def sync_user():
    data = request.get_json() or {}
    google_id = data.get("google_id")
    if not google_id:
        return jsonify({"error": "google_id required"}), 400

    user = User.query.filter_by(google_id=google_id).first()
    if not user:
        user = User(
            google_id=google_id,
            email=data.get("email", ""),
            name=data.get("name", ""),
            avatar_url=data.get("avatar_url"),
        )
        db.session.add(user)
        db.session.commit()

    remaining = max(0, FREE_SEARCH_LIMIT - user.searches_used) if user.plan == "free" else 999
    result = user.to_dict()
    result["searches_remaining"] = remaining
    return jsonify(result), 200


# ── GET /api/me ────────────────────────────────────────────

@app.route("/api/me")
def me():
    google_id = request.args.get("google_id")
    user = _get_user_or_mock(google_id)
    if isinstance(user, dict):
        return jsonify(user)
    result = user.to_dict()
    result["searches_remaining"] = max(0, FREE_SEARCH_LIMIT - user.searches_used) if user.plan == "free" else 999
    return jsonify(result)


# ── POST /api/parse ────────────────────────────────────────

@app.route("/api/parse", methods=["POST"])
@limiter.limit("10 per minute")
def parse_resume_route():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded. Send multipart/form-data with key 'file'"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "Empty filename"}), 400

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in {"pdf", "docx", "doc"}:
        return jsonify({"error": f"Unsupported: .{ext}. Use PDF or DOCX."}), 400

    file_bytes = file.read()
    try:
        profile = parse_resume(file_bytes, file.filename)
        # Sanitize: remove control characters that break JSON in transit
        import re as _re
        clean_profile = json.loads(
            _re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', json.dumps(profile, ensure_ascii=False))
        )
        return jsonify({"status": "parsed", "profile": clean_profile})
    except ParseError as e:
        return jsonify({"error": str(e)}), 422
    except Exception as e:
        return jsonify({"error": f"Unexpected: {str(e)}"}), 500


# ── POST /api/search — FULL PIPELINE ──────────────────────
# Design: partial results > total failure. Every stage wraps errors.
# Quota only increments on success.

@app.route("/api/search", methods=["POST"])
@limiter.limit("5 per minute")
def search_route():
    data = request.get_json() or {}
    errors = []  # Collect non-fatal errors for transparency

    # a. Auth
    google_id = data.get("google_id")
    user = _get_user_or_mock(google_id)

    # b. Quota check (BEFORE any work)
    if isinstance(user, User) and user.plan == "free" and user.searches_used >= FREE_SEARCH_LIMIT:
        return jsonify({
            "error": "quota_exceeded",
            "message": f"Free plan allows {FREE_SEARCH_LIMIT} searches. Upgrade to Pro for unlimited.",
            "searches_used": user.searches_used,
        }), 402

    # c. Preferences
    profile = data.get("profile", {})
    prefs = data.get("prefs", {
        "directions": ["DS/ML", "Health Informatics"],
        "job_type": "intern_2026",
        "visa_needed": True,
    })

    print(f"\n[pipeline] Starting for {profile.get('name', 'Unknown')}")
    print(f"[pipeline] Directions: {prefs.get('directions')}, Type: {prefs.get('job_type')}")

    # ── STAGE 1: Search ──────────────────────────────────
    print("[pipeline] Stage 1: Searching...")
    try:
        all_jobs = run_search(profile, prefs)
        total_found = len(all_jobs)
        print(f"[pipeline] Found {total_found} jobs")
    except Exception as e:
        errors.append(f"Search failed: {str(e)[:100]}")
        return jsonify({"jobs": [], "audit_summary": {"error": str(e)}, "errors": errors}), 200

    if total_found == 0:
        return jsonify({
            "jobs": [], "search_id": None,
            "audit_summary": {"jobs_searched": 0, "jobs_verified": 0, "cl_generated": 0},
            "errors": ["No jobs found matching your criteria. Try broadening your search directions."],
        }), 200

    # Top 5 for verification (keep total response under 15s)
    to_verify = all_jobs[:5]

    # ── STAGE 2: Verify ──────────────────────────────────
    print(f"[pipeline] Stage 2: Verifying {len(to_verify)} jobs...")
    try:
        verified = verify_all_jobs(to_verify, profile, prefs)
    except Exception as e:
        # Verification failed — return unverified results rather than nothing
        errors.append(f"Verification partially failed: {str(e)[:100]}. Showing unverified results.")
        verified = to_verify
        for j in verified:
            if "audit" not in j:
                j["audit"] = {"status": "⚠ Unverified", "confidence": "low",
                              "reason": "Verification unavailable", "drop": False}

    # Add remaining jobs as unverified (so user still sees them)
    for j in all_jobs[5:15]:
        if j not in verified:
            j["audit"] = {"status": "⚠ Unverified", "confidence": "low",
                          "reason": "Not verified (skipped for speed)", "drop": False,
                          "degree_match": "unknown", "visa": "unspecified",
                          "posting_age_days": None, "ghost_risk": "unknown", "needs_manual_check": True}
            verified.append(j)

    open_count = sum(1 for j in verified if j.get("audit", {}).get("status") == "✓ Open")
    unverified_count = sum(1 for j in verified if j.get("audit", {}).get("status") == "⚠ Unverified")
    print(f"[pipeline] {len(verified)} kept ({open_count} open, {unverified_count} unverified)")

    if not verified:
        errors.append("All jobs were filtered out during verification (degree mismatch, visa, or closed).")

    # ── STAGE 3: Skip CLs — return jobs immediately ────
    # CLs are generated separately via /api/generate-cls
    print(f"[pipeline] Jobs ready. CLs will be generated on demand via /api/generate-cls")

    # ── Build audit summary ──────────────────────────────
    cl_scores = []
    drop_reasons = {}
    for j in all_jobs[:20]:
        dr = j.get("audit", {}).get("drop_reason")
        if dr:
            key = dr.split("—")[0].strip() if "—" in dr else dr[:40]
            drop_reasons[key] = drop_reasons.get(key, 0) + 1

    audit_summary = {
        "jobs_searched": total_found,
        "jobs_verified": len(verified),
        "jobs_open": open_count,
        "jobs_unverified": unverified_count,
        "jobs_dropped": len(all_jobs[:20]) - len(verified),
        "drop_reasons": drop_reasons,
        "cl_generated": 0,
        "cl_scores": [],
        "avg_cl_score": 0,
        "max_cl_score": 0,
        "needs_review_count": 0,
        "cl_status": "pending",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    result_jobs = [_serialize_job(j) for j in verified[:10]]

    # ── Save to DB + increment quota (only on success) ───
    search_id = None
    if isinstance(user, User) and result_jobs:
        try:
            search_record = Search(
                user_id=user.id,
                prefs_json=prefs,
                results_json={"jobs": result_jobs},
                audit_json=audit_summary,
            )
            db.session.add(search_record)
            user.searches_used += 1  # Only increment on success
            db.session.commit()
            search_id = search_record.id
        except Exception as e:
            errors.append(f"Failed to save results: {str(e)[:60]}")
            db.session.rollback()

    print(f"[pipeline] Complete: {audit_summary['jobs_verified']} verified, CLs pending, search_id={search_id}")

    # Sanitize response to remove control characters
    import re as _re
    response_data = {
        "search_id": search_id,
        "jobs": result_jobs,
        "audit_summary": audit_summary,
        "errors": errors if errors else None,
    }
    clean_json = _re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', json.dumps(response_data, ensure_ascii=False))
    return app.response_class(clean_json, mimetype='application/json')


# ── POST /api/generate-cls — generate CLs for given jobs ──
# Called AFTER /api/search returns jobs. This is the slow part.

@app.route("/api/generate-cls", methods=["POST"])
@limiter.limit("3 per minute")
def generate_cls_route():
    data = request.get_json() or {}
    jobs = data.get("jobs", [])
    profile = data.get("profile", {})

    if not jobs:
        return jsonify({"error": "No jobs provided"}), 400

    cl_target = min(10, len(jobs))
    results = []
    errors = []

    print(f"[cls] Generating {cl_target} cover letters...")
    for i, job in enumerate(jobs[:cl_target]):
        company = job.get("company", "?")
        try:
            cl = generate_cover_letter(job, profile)
            results.append({
                "index": i,
                "company": company,
                "cover_letter": cl,
            })
            print(f"  CL {i+1}/{cl_target}: {company} — {cl.get('score', 0)}/{cl.get('max_score', 6)}")
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
    print(f"[cls] Done: {len(scores)} generated, avg {sum(scores)/len(scores):.1f}" if scores else "[cls] Done: 0 generated")

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


# ── Run ────────────────────────────────────────────────────

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=False, port=5000)
