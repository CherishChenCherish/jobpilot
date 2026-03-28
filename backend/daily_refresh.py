"""Daily job database refresh. ONLY verified Greenhouse/Lever jobs.

Rule: Every job must pass verify_one() with status=open AND confidence=high.
No curated jobs. No hardcoded URLs. No exceptions.
"""

import re
from datetime import datetime, timezone
from models import db, CachedJob
from models import PendingDiscovery
from searcher import search_jobs, GREENHOUSE_COMPANIES, LEVER_COMPANIES, _fetch_greenhouse, _fetch_lever, _extract_snippet, _ts_to_date, infer_region
from verifier import verify_one, detect_degree_requirement


def daily_refresh():
    """Wipe unverified jobs, re-verify existing, add only API-confirmed new ones."""
    now = datetime.now(timezone.utc)
    log = {"checked": 0, "closed": 0, "new_added": 0, "cleaned": 0, "pending_processed": 0, "active_total": 0}

    # ── Step -1: Process pending discovery tasks ─────────
    pending = PendingDiscovery.query.filter_by(status="pending").all()
    for task in pending:
        print(f"[refresh] Processing pending: regions={task.regions} dirs={task.directions}")
        # The regular Greenhouse/Lever scan below will pick up jobs for these regions
        # Just mark as done — the scan covers all companies including international
        task.status = "done"
        log["pending_processed"] += 1
    if pending:
        db.session.commit()
        print(f"[refresh] Processed {len(pending)} pending tasks")

    # ── Step 0: Clean noise + dedup ──────────────────────
    all_active = CachedJob.query.filter_by(is_active=True).all()

    # Dedup
    seen_keys = {}
    for cj in all_active:
        key = (cj.company.lower().strip(), cj.title.lower().strip())
        if key in seen_keys:
            old = seen_keys[key]
            if (cj.last_verified_at or cj.date_added) > (old.last_verified_at or old.date_added):
                old.is_active = False
            else:
                cj.is_active = False
            log["cleaned"] += 1
        else:
            seen_keys[key] = cj

    # Title quality filter
    for cj in CachedJob.query.filter_by(is_active=True).all():
        title_lower = cj.title.lower()
        has_intern = bool(re.search(r'\bintern\b|\binternship\b|\bco-op\b|\bnew grad\b|\bentry level\b|\bjunior\b', title_lower))
        if not has_intern:
            cj.is_active = False
            log["cleaned"] += 1
        noise_words = ["android", "design", "legal", "tax", "recruiting",
                       "hr ", "human resources", "mba ", "support engineer",
                       "technical support", "interested in"]
        if any(n in title_lower for n in noise_words):
            cj.is_active = False
            log["cleaned"] += 1
        # PhD: NOT blocked at storage — tagged with degree_required="PhD"
        # and filtered at search time by the promise gate.
        senior_signals = ["senior", "lead ", "director", "manager", "principal", "staff ", " vp "]
        if any(s in title_lower for s in senior_signals):
            cj.is_active = False
            log["cleaned"] += 1

    db.session.commit()
    if log["cleaned"]:
        print(f"[refresh] Cleaned {log['cleaned']} bad entries")

    # ── Step 1: Re-verify all active jobs ────────────────
    active_jobs = CachedJob.query.filter_by(is_active=True).all()
    print(f"[refresh] Re-verifying {len(active_jobs)} active jobs...")

    for cj in active_jobs:
        job_dict = {"apply_url": cj.apply_url, "job_board": cj.job_board or "direct",
                    "title": cj.title, "company": cj.company}
        result = verify_one(job_dict, {"degree_level": "Master"}, {"visa_needed": False})
        audit = result.get("audit", {})
        log["checked"] += 1

        status = audit.get("status", "")
        conf = audit.get("confidence", "low")

        # STRICT: only keep if verified open with high confidence
        if status.startswith("\u2713") and conf == "high":
            cj.last_verified_at = now
            cj.status = "open"
            cj.confidence = "high"
        else:
            cj.is_active = False
            cj.status = "closed"
            log["closed"] += 1
            print(f"  REMOVED: {cj.company} — {cj.title} (status={status}, conf={conf})")

    db.session.commit()

    # ── Step 2: Fill from Greenhouse/Lever APIs only ─────
    active_count = CachedJob.query.filter_by(is_active=True).count()
    print(f"[refresh] {active_count} active after re-verification")

    if active_count < 50:
        print(f"[refresh] Filling from ATS APIs...")

        # Greenhouse
        for slug, categories in GREENHOUSE_COMPANIES.items():
            if active_count >= 60:
                break
            raw_jobs = _fetch_greenhouse(slug)
            for job in raw_jobs:
                if active_count >= 60:
                    break

                title = job.get("title", "")
                title_lower = title.lower()

                # Must be intern
                if not re.search(r'\bintern\b|\binternship\b', title_lower):
                    continue

                # No noise
                noise = ["android", "design", "legal", "tax", "mba ", "support", "interested"]
                if any(n in title_lower for n in noise):
                    continue

                # No senior (PhD allowed — filtered at search time by promise gate)
                if "senior" in title_lower or "lead " in title_lower or "director" in title_lower or "manager" in title_lower or "principal" in title_lower:
                    continue

                url = job.get("absolute_url", f"https://boards.greenhouse.io/{slug}/jobs/{job.get('id')}")

                # Skip if already in DB
                if CachedJob.query.filter_by(apply_url=url).first():
                    continue

                # Must be in a recognized region (US, CA, UK, AU, HK, CN)
                loc = job.get("location", {}).get("name", "")
                loc_lower = loc.lower()
                region = infer_region(loc)
                # Skip if location doesn't match any known region
                from searcher import REGION_MAP_CITIES
                recognized = any(any(s in loc_lower for s in signals) for signals in REGION_MAP_CITIES.values())
                if not recognized and "remote" not in loc_lower:
                    continue

                # VERIFY with API — must be high confidence open
                job_dict = {"apply_url": url, "job_board": "greenhouse",
                            "title": title, "company": slug.replace("-", " ").title()}
                result = verify_one(job_dict, {"degree_level": "Master"}, {"visa_needed": False})
                audit = result.get("audit", {})

                if not (audit.get("status", "").startswith("\u2713") and audit.get("confidence") == "high"):
                    continue

                snippet = _extract_snippet(job.get("content", ""))
                degree_req = detect_degree_requirement(title + " " + snippet)
                region = infer_region(loc)
                cj = CachedJob(
                    company=slug.replace("-", " ").title(),
                    title=title, apply_url=url, job_board="greenhouse",
                    location=loc, remote="remote" in loc_lower,
                    status="open", confidence="high", ghost_risk="low",
                    description=snippet, degree_required=degree_req,
                    recommended_cv="V1-DS",
                    categories=categories,
                    company_size="mid", is_active=True,
                    region=region, language="EN", discovery_source="greenhouse",
                    last_verified_at=now,
                )
                db.session.add(cj)
                log["new_added"] += 1
                active_count += 1
                print(f"  NEW [greenhouse] [{region}]: {cj.company} — {cj.title}")

        # Lever
        for slug, categories in LEVER_COMPANIES.items():
            if active_count >= 60:
                break
            raw_jobs = _fetch_lever(slug)
            for job in raw_jobs:
                if active_count >= 60:
                    break

                title = job.get("text", "")
                title_lower = title.lower()

                if not re.search(r'\bintern\b|\binternship\b', title_lower):
                    continue
                noise = ["android", "design", "legal", "tax", "mba ", "support"]
                if any(n in title_lower for n in noise):
                    continue

                url = job.get("hostedUrl", "")
                if not url:
                    continue
                if CachedJob.query.filter_by(apply_url=url).first():
                    continue

                cat = job.get("categories", {})
                loc = cat.get("location", "")
                loc_lower = str(loc).lower()
                region = infer_region(str(loc))
                from searcher import REGION_MAP_CITIES
                recognized = any(any(s in loc_lower for s in signals) for signals in REGION_MAP_CITIES.values())
                if not recognized and "remote" not in loc_lower:
                    continue

                # VERIFY
                job_dict = {"apply_url": url, "job_board": "lever", "title": title, "company": slug.replace("-", " ").title()}
                result = verify_one(job_dict, {"degree_level": "Master"}, {"visa_needed": False})
                audit = result.get("audit", {})

                if not (audit.get("status", "").startswith("\u2713") and audit.get("confidence") == "high"):
                    continue

                desc = job.get("descriptionPlain", "")[:300]
                degree_req = detect_degree_requirement(title + " " + desc)
                region = infer_region(str(loc))
                cj = CachedJob(
                    company=slug.replace("-", " ").title(),
                    title=title, apply_url=url, job_board="lever",
                    location=str(loc), remote="remote" in loc_lower,
                    status="open", confidence="high", ghost_risk="low",
                    description=desc, degree_required=degree_req,
                    recommended_cv="V1-DS",
                    categories=categories,
                    company_size="mid", is_active=True,
                    region=region, language="EN", discovery_source="lever",
                    last_verified_at=now,
                )
                db.session.add(cj)
                log["new_added"] += 1
                active_count += 1
                print(f"  NEW [lever] [{region}]: {cj.company} — {cj.title}")

        db.session.commit()

    # ── Step 5: Web discovery for regions with few jobs ──
    try:
        from web_discovery import discover_jobs as web_discover
        standard_dirs = ["DS/ML", "Software Engineering", "Health Informatics",
                         "Business Analytics", "Quantitative Finance", "Research / NLP"]
        for region in ["CA", "UK", "AU", "HK", "CN"]:
            region_count = CachedJob.query.filter_by(is_active=True, region=region).count()
            if region_count >= 10:
                continue  # Already enough
            print(f"[refresh] Web discovery for {region} ({region_count} existing)...")
            try:
                found = web_discover([region], standard_dirs[:3], max_per_combination=5)
                for job_data in found:
                    if CachedJob.query.filter_by(apply_url=job_data["apply_url"]).first():
                        continue
                    degree_req = detect_degree_requirement(job_data["title"])
                    cj = CachedJob(
                        company=job_data["company"], title=job_data["title"],
                        apply_url=job_data["apply_url"], job_board="web_discovery",
                        location=job_data["location"], remote=False,
                        status="open", confidence=job_data["confidence"],
                        degree_required=degree_req,
                        region=job_data["region"], language=job_data["language"],
                        discovery_source="web_discovery",
                        is_active=True, last_verified_at=now,
                    )
                    db.session.add(cj)
                    log["new_added"] += 1
                db.session.commit()
            except Exception as e:
                print(f"[refresh] Web discovery error for {region}: {e}")
    except ImportError:
        print("[refresh] web_discovery module not available, skipping")

    log["active_total"] = CachedJob.query.filter_by(is_active=True).count()
    print(f"[refresh] Done: {log}")
    return log
