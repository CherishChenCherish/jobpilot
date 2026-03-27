"""Daily job database refresh. Keeps 50-100 verified jobs cached."""

from datetime import datetime, timezone
from models import db, CachedJob
from searcher import search_jobs
from verifier import verify_one


def daily_refresh():
    """Re-verify existing jobs, add new ones to fill gaps."""
    now = datetime.now(timezone.utc)
    log = {"checked": 0, "closed": 0, "new_added": 0, "active_total": 0}

    # Step 1: Re-verify all active jobs
    active_jobs = CachedJob.query.filter_by(is_active=True).all()
    print(f"[refresh] Re-verifying {len(active_jobs)} active jobs...")

    for cj in active_jobs:
        job_dict = {"apply_url": cj.apply_url, "job_board": cj.job_board or "direct",
                    "title": cj.title, "company": cj.company, "match_reason": cj.match_reason or ""}
        result = verify_one(job_dict, {"degree_level": "Master"}, {"visa_needed": False})
        audit = result.get("audit", {})
        log["checked"] += 1

        if audit.get("status", "").startswith("\u2717") or audit.get("drop"):
            cj.is_active = False
            cj.status = "closed"
            log["closed"] += 1
            print(f"  CLOSED: {cj.company} — {cj.title}")
        else:
            cj.last_verified_at = now
            cj.status = "open"
            cj.confidence = audit.get("confidence", "high")

    db.session.commit()

    # Step 2: Fill gaps
    active_count = CachedJob.query.filter_by(is_active=True).count()
    print(f"[refresh] {active_count} active after re-verification")

    if active_count < 50:
        needed = 60 - active_count
        print(f"[refresh] Need {needed} more jobs. Searching...")

        for direction in ["DS/ML", "Health Informatics", "Business Analytics", "Software Engineering", "Data Engineering"]:
            if active_count >= 60:
                break

            profile = {"name": "cache", "skills": ["Python", "SQL", "Machine Learning"],
                       "degree_level": "Master", "strongest_metrics": []}
            prefs = {"directions": [direction], "job_type": "intern_2026", "visa_needed": False}
            new_jobs = search_jobs(profile, prefs)

            for job in new_jobs[:15]:
                url = job.get("apply_url", "")
                if not url:
                    continue

                # Skip if already in DB
                existing = CachedJob.query.filter_by(apply_url=url).first()
                if existing:
                    continue

                # Quick verify
                result = verify_one(job, {"degree_level": "Master"}, {"visa_needed": False})
                audit = result.get("audit", {})

                if not audit.get("status", "").startswith("\u2713"):
                    continue

                # Quality filter: skip non-intern/entry roles
                title_lower = job.get("title", "").lower()
                skip_titles = ["director", "manager", "senior", "lead", "head of",
                               "principal", "staff", "vp ", "vice president", "mba "]
                if any(s in title_lower for s in skip_titles) and "intern" not in title_lower:
                    continue

                # PhD filter: skip PhD-only roles for MS cache
                desc = job.get("description_snippet", "").lower() + " " + title_lower
                phd_signals = ["phd required", "current phd student", "ph.d. required",
                               "doctoral required", "phd candidate"]
                if any(p in desc for p in phd_signals):
                    continue

                cj = CachedJob(
                    company=job.get("company", ""),
                    title=job.get("title", ""),
                    apply_url=url,
                    job_board=job.get("job_board", "direct"),
                    location=job.get("location", ""),
                    remote=job.get("remote", False),
                    status="open",
                    confidence=audit.get("confidence", "high"),
                    ghost_risk=audit.get("ghost_risk", "low"),
                    description=job.get("description_snippet", ""),
                    degree_required=job.get("degree_required", ""),
                    visa_sponsorship=job.get("visa_sponsorship", "unspecified"),
                    recommended_cv=job.get("recommended_cv", "V1-DS"),
                    categories=job.get("categories", []),
                    match_reason=job.get("match_reason", ""),
                    key_requirements=job.get("key_requirements", []),
                    company_size=job.get("company_size", "mid"),
                    is_active=True,
                )
                db.session.add(cj)
                log["new_added"] += 1
                active_count += 1
                print(f"  NEW: {cj.company} — {cj.title}")

        db.session.commit()

    log["active_total"] = CachedJob.query.filter_by(is_active=True).count()
    print(f"[refresh] Done: {log}")
    return log
