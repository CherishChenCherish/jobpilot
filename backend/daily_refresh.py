"""Daily job database refresh. Keeps 50-100 verified jobs cached."""

from datetime import datetime, timezone
from models import db, CachedJob
from searcher import search_jobs
from verifier import verify_one


def daily_refresh():
    """Re-verify existing jobs, add new ones to fill gaps."""
    now = datetime.now(timezone.utc)
    log = {"checked": 0, "closed": 0, "new_added": 0, "cleaned": 0, "active_total": 0}

    # Step 0: Clean noise + dedup
    import re
    all_active = CachedJob.query.filter_by(is_active=True).all()

    # Dedup: if same company+title exists twice, keep newer one
    seen_keys = {}
    for cj in all_active:
        key = (cj.company.lower().strip(), cj.title.lower().strip())
        if key in seen_keys:
            # Keep the one with more recent verification
            old = seen_keys[key]
            if (cj.last_verified_at or cj.date_added) > (old.last_verified_at or old.date_added):
                old.is_active = False
                seen_keys[key] = cj
            else:
                cj.is_active = False
            log["cleaned"] += 1
        else:
            seen_keys[key] = cj
    db.session.commit()
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

    # Step 2b: Add known good intern positions directly
    _seed_curated_jobs(log)
    active_count = CachedJob.query.filter_by(is_active=True).count()

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


def _seed_curated_jobs(log):
    """Add known-good intern positions that the ATS scraper might miss."""
    curated = [
        ("Amazon", "2026 Data Science Internship (MS/PhD)", "https://www.amazon.jobs/en/jobs/3144155/2026-data-science-internship-united-states-phd-or-masters-student", "direct", "Seattle, WA", ["DS/ML"], "V1-DS", "OPT/CPT accepted", "Build ML models, analyze data at scale. $97K-185K annualized."),
        ("Amazon", "Data Engineer Internship 2026 (US)", "https://www.amazon.jobs/en/jobs/3066625/data-engineer-internship-2026-us", "direct", "Multiple US", ["DS/ML", "Data Engineering"], "V1-DS", "OPT/CPT accepted", "Build data pipelines and ETL at scale."),
        ("Visa", "Data Science Intern - Summer 2026", "https://corporate.visa.com/en/jobs/REF94329J", "direct", "Foster City, CA", ["DS/ML"], "V1-DS", "Supports international students", "Payment data ML models."),
        ("IQVIA", "Data Science Intern - Summer 2026 (Remote)", "https://jobs.iqvia.com/en/search-jobs?k=data+science+intern", "direct", "Remote", ["Health Informatics", "DS/ML"], "V3-Health", "Large company", "Pharma retail ML models."),
        ("Two Sigma", "Data Scientist Internship (Summer 2026)", "https://careers.twosigma.com/careers/JobDetail/New-York-New-York-United-States-Data-Scientist-Internship-Summer-2026/13585", "direct", "New York, NY", ["DS/ML", "Quantitative Finance"], "V1-DS", "Top H1B sponsor", "Quantitative research, 10-week program."),
        ("UnitedHealth Group / Optum", "Graduate Data Science Internship - Summer 2026", "https://www.unitedhealthgroup.com/careers/en/work/early-careers/technology-and-analytics.html", "direct", "Eden Prairie, MN / Remote", ["Health Informatics"], "V3-Health", "Large company", "Healthcare data ML. $27-37/hr."),
        ("Siemens Healthineers", "2026 Software & Data Science Internships", "https://careers.siemens-healthineers.com/global/en/job/R-23658/2026-Software-Data-Science-Internships", "direct", "Cary, NC", ["Health Informatics", "DS/ML"], "V3-Health", "Large company", "Healthcare technology data science."),
        ("Rivian", "AI/ML & Data Science Intern, Summer 2026", "https://careers.rivian.com/careers-home/jobs/27354?lang=en-us", "direct", "Multiple US", ["DS/ML"], "V1-DS", "Large company", "AI/ML for sustainable transportation."),
        ("JPMorgan Chase", "Data Science Intern 2026", "https://www.jpmorganchase.com/careers/explore-opportunities/programs/data-analytics-opportunities", "direct", "New York, NY", ["DS/ML", "Quantitative Finance"], "V1-DS", "Top H1B sponsor", "Quantitative analytics and data science."),
        ("Databricks", "Data Science Intern 2026", "https://www.databricks.com/company/careers/university-recruiting", "direct", "San Francisco, CA", ["DS/ML", "Data Engineering"], "V1-DS", "Large company", "Data and AI platform company."),
        ("Match Group", "Machine Learning Engineer Intern", "https://jobs.lever.co/matchgroup", "lever", "Los Angeles, CA", ["DS/ML"], "V1-DS", "Large company", "ML for dating platforms."),
        ("Intuit", "AI Science Intern - Summer 2026", "https://jobs.intuit.com/job/mountain-view/summer-2026-ai-science-intern/27595/87369447088", "direct", "Mountain View, CA", ["DS/ML"], "V1-DS", "F-1 CPT", "AI for financial products."),
        # Software Engineering
        ("Palantir", "Software Engineer Intern", "https://www.palantir.com/careers/students/", "direct", "New York / Palo Alto", ["Software Engineering", "DS/ML"], "V1-DS", "Top H1B sponsor", "Data analytics platform."),
        ("Scale AI", "Software Engineering Intern", "https://scale.com/careers#open-positions", "direct", "San Francisco", ["Software Engineering", "DS/ML"], "V1-DS", "Large company", "AI data infrastructure."),
        # Data Engineering
        ("Snowflake", "Data Engineering Intern 2026", "https://careers.snowflake.com/us/en/search-results?keywords=intern", "direct", "San Mateo, CA", ["Data Engineering", "DS/ML"], "V1-DS", "Large company", "Cloud data platform."),
        # Health Informatics
        ("Epic Systems", "Data Science Intern", "https://careers.epic.com/jobs?search=intern", "direct", "Verona, WI", ["Health Informatics"], "V3-Health", "Large company", "Healthcare EHR systems."),
        ("Tempus", "Data Science Intern", "https://www.tempus.com/careers/#openings", "direct", "Chicago, IL", ["Health Informatics", "DS/ML"], "V3-Health", "Large company", "AI-driven precision medicine."),
        ("Flatiron Health", "Data Science Intern", "https://flatiron.com/careers/#open-roles", "direct", "New York, NY", ["Health Informatics", "DS/ML"], "V3-Health", "Large company", "Oncology data analytics."),
        # Business Analytics / Consulting
        ("McKinsey", "Business Analyst Intern", "https://www.mckinsey.com/careers/search-jobs/jobs/businessanalystintern-15275", "direct", "Multiple US", ["Business Analytics", "Consulting"], "V2-Biz", "Top sponsor", "Management consulting."),
        ("Deloitte", "Business Analyst Intern", "https://apply.deloitte.com/en_US/careers/JobDetail/Internal-Strategy-Business-Analyst-Summer-Intern/318348", "direct", "New York, NY", ["Business Analytics", "Consulting"], "V2-Biz", "Large company", "Consulting and advisory."),
        ("BCG", "Associate Intern", "https://careers.bcg.com/students", "direct", "Multiple US", ["Business Analytics", "Consulting"], "V2-Biz", "Top sponsor", "Strategy consulting."),
        # Quantitative Finance
        ("Citadel", "Quantitative Research Analyst Intern (BS/MS)", "https://www.citadel.com/careers/details/quantitative-research-analyst-intern-bs-ms-us/", "direct", "New York / Chicago / Miami", ["Quantitative Finance", "DS/ML"], "V1-DS", "Top sponsor", "11-week program. $4,300-$5,800/week."),
        ("DE Shaw", "Quantitative Analyst Intern (Summer 2026)", "https://www.deshaw.com/careers/quantitative-analyst-intern-new-york-summer-2026-5519", "direct", "New York, NY", ["Quantitative Finance", "DS/ML"], "V1-DS", "Top sponsor", "12-week program. $25K/month + $25K sign-on."),
        ("Jane Street", "Quantitative Trading Intern", "https://www.janestreet.com/join-jane-street/internships/trading/", "direct", "New York, NY", ["Quantitative Finance"], "V1-DS", "Top sponsor", "Trading internship with elective program."),
        # Product Management
        ("Google", "Product Manager Intern 2026", "https://www.google.com/about/careers/applications/internships/", "direct", "Multiple US", ["Product Management", "DS/ML"], "V2-Biz", "Top H1B sponsor", "Product strategy."),
        # Research / NLP
        ("OpenAI", "Research Intern (Summer 2026)", "https://openai.com/careers/emerging-talent/", "direct", "San Francisco, CA", ["Research / NLP", "DS/ML"], "V1-DS", "Top sponsor", "13-week paid internship. AI research."),
        ("Anthropic", "Research Intern", "https://www.anthropic.com/careers#open-roles", "direct", "San Francisco, CA", ["Research / NLP", "DS/ML"], "V1-DS", "Top sponsor", "AI safety research."),
        # More DS/ML
        ("Netflix", "Data Science Intern", "https://jobs.netflix.com/search?q=intern+data", "direct", "Los Gatos, CA", ["DS/ML"], "V1-DS", "Large company", "Recommendation systems."),
        ("Spotify", "Data Science Intern", "https://www.lifeatspotify.com/students", "direct", "New York, NY", ["DS/ML"], "V1-DS", "Large company", "Music ML and personalization."),
        ("Uber", "Data Science Intern", "https://www.uber.com/us/en/careers/list/?query=intern+data+science", "direct", "San Francisco, CA", ["DS/ML", "Data Engineering"], "V1-DS", "Large company", "Ride-sharing data platform."),
        ("Airbnb", "Data Science Intern", "https://careers.airbnb.com/positions/?search=intern", "direct", "San Francisco, CA", ["DS/ML"], "V1-DS", "Large company", "Travel marketplace analytics."),
        ("Pinterest", "Data Science Intern", "https://www.pinterestcareers.com/jobs/?search=intern+data", "direct", "San Francisco, CA", ["DS/ML"], "V1-DS", "Large company", "Visual discovery ML."),
        ("Block (Square)", "Data Science Intern", "https://block.xyz/careers?search=intern", "direct", "San Francisco, CA", ["DS/ML", "Quantitative Finance"], "V1-DS", "Large company", "Fintech data analytics."),
    ]

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    added = 0

    for company, title, url, board, location, categories, cv, visa, desc in curated:
        existing = CachedJob.query.filter_by(apply_url=url).first()
        if existing:
            continue

        cj = CachedJob(
            company=company, title=title, apply_url=url, job_board=board,
            location=location, remote="remote" in location.lower(),
            status="open", confidence="medium", ghost_risk="low",
            description=desc, visa_sponsorship=visa,
            recommended_cv=cv, categories=categories,
            company_size="large", is_active=True,
            last_verified_at=now,
        )
        db.session.add(cj)
        added += 1

    db.session.commit()
    log["new_added"] = log.get("new_added", 0) + added
    if added:
        print(f"[refresh] Added {added} curated jobs")
