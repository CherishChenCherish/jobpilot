"""JobPilot job searcher — find real open US positions matching candidate profile."""

import json
import os
import re
import time
from typing import Any
from urllib.parse import quote_plus

import requests
from dotenv import load_dotenv

load_dotenv()


# ── ATS Direct JSON APIs (free, structured, no auth) ──────

# Companies known to hire DS/ML/Health interns on Greenhouse
GREENHOUSE_COMPANIES = [
    "rivian", "flagshippioneeringinc", "lucidmotors", "honehealth",
    "tempus", "flatiron", "noom", "tempusinc", "benchling",
    "duolingo", "figma", "notion", "stripe", "plaid", "ramp",
    "verkada", "anduril", "palantir", "databricks",
    "scale", "brex", "gusto", "airtable", "retool",
]

# Companies on Lever
LEVER_COMPANIES = [
    "matchgroup", "spotify", "netflix", "wealthsimple",
    "bhg-inc", "samsara", "relativity", "grammarly",
    "zocdoc", "everbridge", "viz-ai",
]


def _fetch_greenhouse_jobs(company_slug: str) -> list[dict]:
    """Fetch jobs from Greenhouse public API."""
    url = f"https://boards-api.greenhouse.io/v1/boards/{company_slug}/jobs"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return []
        data = r.json()
        return data.get("jobs", [])
    except Exception:
        return []


def _fetch_lever_jobs(company_slug: str) -> list[dict]:
    """Fetch jobs from Lever public API."""
    url = f"https://api.lever.co/v0/postings/{company_slug}?mode=json"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return []
        return r.json()
    except Exception:
        return []


def _normalize_greenhouse_job(job: dict, company_slug: str) -> dict:
    """Convert Greenhouse job JSON to our standard format."""
    location = job.get("location", {}).get("name", "Unknown")
    title = job.get("title", "")

    snippet = _extract_snippet(job.get("content", ""))

    return {
        "title": title,
        "company": company_slug.replace("-", " ").title(),
        "location": location,
        "remote": "remote" in location.lower(),
        "apply_url": job.get("absolute_url", f"https://boards.greenhouse.io/{company_slug}/jobs/{job.get('id')}"),
        "linkedin_url": "",
        "job_board": "greenhouse",
        "posting_date": job.get("updated_at", "unknown")[:10] if job.get("updated_at") else "unknown",
        "degree_required": "",
        "visa_sponsorship": "unknown",
        "description_snippet": snippet,
        "key_requirements": [],
        "match_reason": "",
        "recommended_cv": "",
    }


def _fetch_greenhouse_snippet(company_slug: str, job_id: int) -> str:
    """Fetch individual job detail for description snippet."""
    url = f"https://boards-api.greenhouse.io/v1/boards/{company_slug}/jobs/{job_id}"
    try:
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            return _extract_snippet(r.json().get("content", ""))
    except Exception:
        pass
    return ""


def _normalize_lever_job(job: dict, company_slug: str) -> dict:
    """Convert Lever job JSON to our standard format."""
    categories = job.get("categories", {})
    location = categories.get("location", job.get("workplaceType", "Unknown"))
    return {
        "title": job.get("text", ""),
        "company": company_slug.replace("-", " ").title(),
        "location": location,
        "remote": "remote" in str(location).lower(),
        "apply_url": job.get("hostedUrl", job.get("applyUrl", "")),
        "linkedin_url": "",
        "job_board": "lever",
        "posting_date": _ts_to_date(job.get("createdAt")),
        "degree_required": "",
        "visa_sponsorship": "unknown",
        "description_snippet": job.get("descriptionPlain", "")[:300],
        "key_requirements": [],
        "match_reason": "",
        "recommended_cv": "",
    }


def _extract_snippet(html_content: str) -> str:
    """Extract plain text snippet from HTML job description."""
    text = re.sub(r'<[^>]+>', ' ', html_content)
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:300]


def _ts_to_date(ts) -> str:
    """Convert millisecond timestamp to YYYY-MM-DD."""
    if not ts:
        return "unknown"
    try:
        return time.strftime("%Y-%m-%d", time.gmtime(int(ts) / 1000))
    except Exception:
        return "unknown"


def _matches_keywords(title: str, keywords: list[str]) -> bool:
    """Check if job title matches any of the search keywords."""
    title_lower = title.lower()
    return any(kw.lower() in title_lower for kw in keywords)


def _recommend_cv(title: str, description: str) -> str:
    """Recommend which CV version to use based on job content."""
    text = (title + " " + description).lower()
    health_kw = ["health", "clinical", "medical", "biomedical", "pharma", "epidem", "ehr", "fhir"]
    biz_kw = ["business analyst", "strategy", "consulting", "operations", "product manager"]

    if any(k in text for k in health_kw):
        return "V3-Health"
    if any(k in text for k in biz_kw):
        return "V2-Biz"
    return "V1-DS"


# ── Main search function ──────────────────────────────────

def search_jobs(profile: dict, prefs: dict) -> list[dict]:
    """
    Search for real open US positions matching candidate profile.

    Args:
        profile: Structured profile from parser (skills, degree_level, etc.)
        prefs: User preferences dict with keys:
            - directions: list of ["DS/ML", "Health Informatics", "Business Analytics"]
            - job_type: "intern_2026" | "new_grad_2027"
            - location: "US" (default)

    Returns:
        List of job dicts, deduplicated, sorted by relevance.
    """
    directions = prefs.get("directions", ["DS/ML"])
    job_type = prefs.get("job_type", "intern_2026")

    # Build keyword sets based on directions and job type
    title_keywords = []
    if "DS/ML" in directions:
        title_keywords += ["data science", "data scientist", "machine learning", "ml engineer",
                          "ai ", "artificial intelligence", "nlp", "data analyst", "data engineer"]
    if "Health Informatics" in directions:
        title_keywords += ["health informatics", "clinical data", "biomedical", "bioinformatics",
                          "health data", "clinical informatics", "epidemiol"]
    if "Business Analytics" in directions:
        title_keywords += ["business analyst", "strategy", "analytics", "business intelligence"]

    # Add seniority keywords
    if job_type == "intern_2026":
        title_keywords += ["intern", "internship", "co-op"]
    else:
        title_keywords += ["new grad", "entry level", "junior", "associate"]

    # Also match "2026" or "2027" in title
    year_keywords = ["2026"] if job_type == "intern_2026" else ["2027", "2026"]

    all_jobs = []

    # ── Phase A: Scrape Greenhouse companies ──────────────
    for slug in GREENHOUSE_COMPANIES:
        jobs = _fetch_greenhouse_jobs(slug)
        for job in jobs:
            title = job.get("title", "")
            # Match by title keywords OR year
            if _matches_keywords(title, title_keywords) or any(y in title for y in year_keywords):
                normalized = _normalize_greenhouse_job(job, slug)
                # US only filter
                loc = normalized["location"].lower()
                if any(x in loc for x in ["us", "united states", "new york", "san francisco",
                                           "seattle", "remote", "boston", "chicago", "los angeles",
                                           "austin", "denver", " ca", " wa", " ny", " ma", " tx",
                                           " il", " co", " ct", " pa", " or", " ga"]):
                    normalized["recommended_cv"] = _recommend_cv(title, normalized["description_snippet"])
                    all_jobs.append(normalized)

    # ── Phase B: Scrape Lever companies ───────────────────
    for slug in LEVER_COMPANIES:
        jobs = _fetch_lever_jobs(slug)
        for job in jobs:
            title = job.get("text", "")
            if _matches_keywords(title, title_keywords) or any(y in title for y in year_keywords):
                normalized = _normalize_lever_job(job, slug)
                loc = normalized["location"].lower()
                if any(x in loc for x in ["us", "united states", "new york", "san francisco",
                                           "seattle", "remote", "boston", "chicago", "los angeles",
                                           "austin", "denver", " ca", " wa", " ny", " ma", " tx"]):
                    normalized["recommended_cv"] = _recommend_cv(title, normalized["description_snippet"])
                    all_jobs.append(normalized)

    # ── Phase C: Add known high-priority jobs (curated) ───
    # These are manually verified open positions from our earlier research
    curated = _get_curated_jobs(job_type)
    all_jobs.extend(curated)

    # ── Deduplicate by company + title ────────────────────
    seen = set()
    deduped = []
    for job in all_jobs:
        key = (job["company"].lower().strip(), job["title"].lower().strip())
        if key not in seen:
            seen.add(key)
            deduped.append(job)

    # ── Sort by match relevance ───────────────────────────
    profile_skills = set(s.lower() for s in profile.get("skills", []))

    def _score(job):
        """Score a job by relevance to profile."""
        s = 0
        desc = (job["title"] + " " + job.get("description_snippet", "")).lower()
        # Skill matches
        for skill in profile_skills:
            if skill in desc:
                s += 10
        # Year match
        if any(y in job["title"] for y in year_keywords):
            s += 20
        # Intern/new grad match
        if job_type == "intern_2026" and "intern" in job["title"].lower():
            s += 15
        # Known good companies
        big_names = ["amazon", "google", "visa", "iqvia", "meta", "microsoft", "rivian", "intuit"]
        if any(n in job["company"].lower() for n in big_names):
            s += 10
        return s

    deduped.sort(key=_score, reverse=True)

    return deduped


def _get_curated_jobs(job_type: str) -> list[dict]:
    """Return manually verified open positions from earlier research."""
    if job_type != "intern_2026":
        return []

    return [
        {
            "title": "2026 Data Science Internship (MS/PhD)",
            "company": "Amazon",
            "location": "Seattle, WA + Multiple US",
            "remote": False,
            "apply_url": "https://www.amazon.jobs/en/jobs/3144155/2026-data-science-internship-united-states-phd-or-masters-student",
            "linkedin_url": "",
            "job_board": "direct",
            "posting_date": "2025-12-01",
            "degree_required": "Master's or PhD",
            "visa_sponsorship": "OPT/CPT accepted",
            "description_snippet": "Amazon is looking for MS/PhD students with strong modeling skills for data science internships. Build tools to analyze data and present findings to business partners. $97K-185K annualized.",
            "key_requirements": ["MS/PhD in quantitative field", "Python/R/SQL", "ML/data mining experience", "Large-scale data (100K+ rows)"],
            "match_reason": "Top H1B sponsor, production-scale data, ML modeling — matches your Alibaba pipeline experience",
            "recommended_cv": "V1-DS",
        },
        {
            "title": "Data Science Intern - Summer 2026",
            "company": "Visa",
            "location": "Foster City, CA",
            "remote": False,
            "apply_url": "https://corporate.visa.com/en/jobs/REF94329J",
            "linkedin_url": "",
            "job_board": "direct",
            "posting_date": "2026-01-15",
            "degree_required": "Currently enrolled in degree program",
            "visa_sponsorship": "Supports international students",
            "description_snippet": "Visa seeks Data Science Intern for Summer 2026. Work with payment transaction data to build ML models and derive business insights.",
            "key_requirements": ["Enrolled in MS program", "Python/SQL", "ML experience", "Statistics"],
            "match_reason": "Payment + behavioral data intersection — directly maps to your Alipay/Ele.me experience",
            "recommended_cv": "V1-DS",
        },
        {
            "title": "Data Science Intern - Summer 2026 (Remote)",
            "company": "IQVIA",
            "location": "Remote (King of Prussia, PA)",
            "remote": True,
            "apply_url": "https://jobs.iqvia.com/en/search-jobs?k=data+science+intern",
            "linkedin_url": "",
            "job_board": "direct",
            "posting_date": "2026-01-01",
            "degree_required": "Master's in quantitative field",
            "visa_sponsorship": "Large company, typically supports",
            "description_snippet": "IQVIA Data Science team works with pharmaceutical retail data to develop ML models. Remote position with Information Partner Services team.",
            "key_requirements": ["MS in Data Science/Stats/CS", "Python or R", "ML/statistical modeling", "Healthcare data interest"],
            "match_reason": "Pharmaceutical data + ML = perfect match for Yale Health Informatics + Ele.me pharma retail experience",
            "recommended_cv": "V3-Health",
        },
        {
            "title": "Data Engineer Internship 2026 (US)",
            "company": "Amazon",
            "location": "Multiple US locations",
            "remote": False,
            "apply_url": "https://www.amazon.jobs/en/jobs/3066625/data-engineer-internship-2026-us",
            "linkedin_url": "",
            "job_board": "direct",
            "posting_date": "2025-11-01",
            "degree_required": "BS/MS in CS or related",
            "visa_sponsorship": "OPT/CPT accepted",
            "description_snippet": "Amazon Data Engineer internship. Build and maintain data pipelines, ETL processes, and data warehousing solutions at scale.",
            "key_requirements": ["SQL proficiency", "Python/Java", "ETL/data pipeline experience", "Large-scale data"],
            "match_reason": "Your 50-100 GB/day ETL pipeline experience at Alibaba directly matches",
            "recommended_cv": "V1-DS",
        },
        {
            "title": "Graduate Data Science Internship - Summer 2026",
            "company": "UnitedHealth Group / Optum",
            "location": "Eden Prairie, MN / Remote",
            "remote": True,
            "apply_url": "https://www.unitedhealthgroup.com/careers/en/work/early-careers/technology-and-analytics.html",
            "linkedin_url": "",
            "job_board": "direct",
            "posting_date": "2026-01-15",
            "degree_required": "Master's in quantitative field",
            "visa_sponsorship": "Large company, typically supports",
            "description_snippet": "Optum graduate data science internship. $27-37/hr. Work with healthcare data to build ML models for clinical and operational insights.",
            "key_requirements": ["Enrolled in MS program", "Python/R/SQL", "ML experience", "Healthcare interest"],
            "match_reason": "Healthcare + DS = ideal for Yale Health Informatics. NHANES project directly relevant.",
            "recommended_cv": "V3-Health",
        },
    ]
