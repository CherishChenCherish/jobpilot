"""Daily job database refresh. Keeps 50-100 verified jobs cached."""

from datetime import datetime, timezone
from models import db, CachedJob
from searcher import search_jobs
from verifier import verify_one


def daily_refresh():
    """Re-verify existing jobs, add new ones to fill gaps."""
    now = datetime.now(timezone.utc)
    log = {"checked": 0, "closed": 0, "new_added": 0, "cleaned": 0, "active_total": 0}

    # Step 0: Clean out non-intern/irrelevant jobs from cache
    import re
    all_active = CachedJob.query.filter_by(is_active=True).all()
    for cj in all_active:
        title_lower = cj.title.lower()
        # Must contain "intern" as a whole word (not "internal"/"international")
        has_intern = bool(re.search(r'\bintern\b|\binternship\b|\bco-op\b|\bnew grad\b|\bentry level\b|\bjunior\b', title_lower))
        if not has_intern:
            cj.is_active = False
            log["cleaned"] += 1
        # Remove PhD-only roles
        phd_signals = ["phd ", "ph.d.", "doctoral"]
        if any(p in title_lower for p in phd_signals):
            cj.is_active = False
            log["cleaned"] += 1
        # Remove irrelevant titles (noise for DS/ML/Health users)
        noise_words = ["android", "design", "legal", "tax", "recruiting",
                       "hr ", "human resources", "mba ", "support engineer",
                       "technical support", "interested in"]
        if any(n in title_lower for n in noise_words):
            cj.is_active = False
            log["cleaned"] += 1
    db.session.commit()
    if log["cleaned"]:
        print(f"[refresh] Cleaned {log['cleaned']} non-intern jobs from cache")

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

                # Quality filter: must contain intern/entry as whole word
                title_lower = job.get("title", "").lower()
                import re as _re
                has_intern = bool(_re.search(r'\bintern\b|\binternship\b|\bco-op\b|\bnew grad\b|\bentry level\b|\bjunior\b', title_lower))
                if not has_intern:
                    continue

                # PhD filter
                desc = job.get("description_snippet", "").lower() + " " + title_lower
                phd_signals = ["phd required", "current phd student", "ph.d. required",
                               "doctoral required", "phd candidate"]
                if any(p in desc for p in phd_signals):
                    continue

                # Noise title filter
                noise_words = ["android", "design", "legal", "tax", "recruiting",
                               "hr ", "human resources", "mba ", "support engineer",
                               "technical support", "interested in"]
                if any(n in title_lower for n in noise_words):
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
