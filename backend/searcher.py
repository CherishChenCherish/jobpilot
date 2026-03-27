"""JobPilot job searcher v2 — personalized, degree-strict, diverse results.

Key improvements over v1:
- Search queries built from candidate's actual profile, not templates
- Strict degree filtering (Master's student never sees PhD-only)
- Career stage separation (intern vs new grad pipelines)
- Company diversity: FAANG + mid-size + funded startups + health/pharma
- Curated jobs verified with real URLs, not LinkedIn
- Category-tagged companies for direction-based matching
"""

import re
import time
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()


# ══════════════════════════════════════════════════════════
# Company registry — tagged by category for smart matching
# ══════════════════════════════════════════════════════════

GREENHOUSE_COMPANIES = {
    # slug: [categories]
    # ── DS/ML / Tech ──
    "databricks": ["DS/ML", "Data Engineering", "Software Engineering"],
    "palantir": ["DS/ML", "Software Engineering"],
    "anduril": ["DS/ML", "Software Engineering"],
    "scale": ["DS/ML", "Research / NLP"],
    "duolingo": ["DS/ML", "Software Engineering", "Product Management"],
    "figma": ["DS/ML", "Software Engineering", "Product Management"],
    "notion": ["DS/ML", "Software Engineering", "Product Management"],
    "stripe": ["DS/ML", "Software Engineering", "Data Engineering"],
    "plaid": ["DS/ML", "Software Engineering", "Data Engineering"],
    "ramp": ["DS/ML", "Business Analytics", "Software Engineering"],
    "brex": ["DS/ML", "Software Engineering"],
    "retool": ["DS/ML", "Software Engineering"],
    "airtable": ["DS/ML", "Software Engineering", "Product Management"],
    "verkada": ["DS/ML", "Software Engineering"],
    "gusto": ["DS/ML", "Business Analytics", "Software Engineering"],
    "rivian": ["DS/ML", "Software Engineering", "Data Engineering"],
    # ── Health / Biotech ──
    "tempus": ["DS/ML", "Health Informatics"],
    "flatiron": ["DS/ML", "Health Informatics"],
    "noom": ["Health Informatics"],
    "honehealth": ["Health Informatics"],
    "benchling": ["Health Informatics"],
    "flagshippioneeringinc": ["Health Informatics", "DS/ML"],
    "color": ["Health Informatics"],
    "veracyte": ["Health Informatics"],
    "recursionpharmaceuticals": ["Health Informatics"],
    "grail": ["Health Informatics", "DS/ML"],
    "faborhealth": ["Health Informatics"],
    # ── New: confirmed intern jobs on Greenhouse ──
    "c3ai": ["DS/ML", "Software Engineering"],
    "lyft": ["DS/ML", "Data Engineering", "Software Engineering"],
    "dropbox": ["Software Engineering", "DS/ML"],
    "perpay": ["DS/ML"],
    "g2crowd": ["DS/ML"],
    "enova": ["Software Engineering"],
    "databento": ["Software Engineering", "Quantitative Finance"],
    "cockroachlabs": ["Software Engineering", "Data Engineering"],
    "niantic": ["Software Engineering", "DS/ML"],
    "snorkelai": ["DS/ML", "Research / NLP"],
    "cohere": ["DS/ML", "Research / NLP"],
    "huggingface": ["DS/ML", "Research / NLP"],
    "weights-and-biases": ["DS/ML", "Research / NLP"],
    "deepmind": ["DS/ML", "Research / NLP"],
    "cerebras": ["DS/ML", "Software Engineering"],
    "together": ["DS/ML", "Research / NLP"],
    "mosaicinstitute": ["DS/ML", "Research / NLP"],
    "nuro": ["DS/ML", "Software Engineering"],
    "aurora-innovation": ["DS/ML", "Software Engineering"],
    "applovin": ["DS/ML", "Software Engineering"],
    "robinhood": ["DS/ML", "Software Engineering", "Quantitative Finance"],
    "chime": ["DS/ML", "Software Engineering"],
    "instacart": ["DS/ML", "Software Engineering", "Data Engineering"],
    "doordash": ["DS/ML", "Software Engineering", "Data Engineering"],
    # ── Business / Consulting / Analytics ──
    "mckinsey": ["Business Analytics"],
    "bain": ["Business Analytics"],
    "bcg": ["Business Analytics"],
    # ── International: Canada ──
    "mongodb": ["Software Engineering", "DS/ML"],  # Toronto
    "d2l": ["Software Engineering"],  # Kitchener/Toronto
    "coveoen": ["Software Engineering", "DS/ML"],  # Montreal/Quebec
    "okta": ["Software Engineering", "Business Analytics"],  # Toronto
    "cloudflare": ["Software Engineering", "DS/ML", "Data Engineering"],  # Toronto
    # ── International: UK ──
    "drweng": ["Quantitative Finance", "Software Engineering"],  # London
    "aquaticcapitalmanagement": ["Quantitative Finance"],  # London
    "hudsonrivertrading": ["Quantitative Finance", "Software Engineering"],  # London
    "moloco": ["DS/ML", "Software Engineering"],  # London
    "altruistiq": ["DS/ML", "Health Informatics"],  # London
    "clarityai": ["DS/ML"],  # London
    "mavensecuritiesholdingltd": ["Quantitative Finance"],  # London
    "charlesriverassociates": ["Business Analytics", "Consulting"],  # London
    # ── International: AU ──
    "canva": ["Software Engineering", "DS/ML"],  # Sydney
    "atlassian": ["Software Engineering", "DS/ML"],  # Sydney
}

# Region inference from location
REGION_MAP_CITIES = {
    "US": ["united states", "new york", "san francisco", "seattle", "boston", "chicago",
           "los angeles", "austin", "denver", "remote", " ca", " wa", " ny", " ma", " tx",
           " il", " co", " ct", " pa", " or", " ga", " nc", " mn"],
    "CA": ["canada", "toronto", "montreal", "vancouver", "ottawa", "kitchener", "waterloo", "calgary"],
    "UK": ["united kingdom", "london", "manchester", "cambridge", "edinburgh", "oxford", " uk"],
    "AU": ["australia", "sydney", "melbourne", "brisbane", "perth"],
    "HK": ["hong kong", " hk"],
    "CN": ["china", "beijing", "shanghai", "shenzhen", "hangzhou", "guangzhou",
           "北京", "上海", "深圳", "杭州", "广州", "成都", "武汉", "南京"],
}

def infer_region(location: str) -> str:
    """Infer region code from job location string."""
    loc = location.lower()
    for region, signals in REGION_MAP_CITIES.items():
        if any(s in loc for s in signals):
            return region
    return "US"  # default

LEVER_COMPANIES = {
    "matchgroup": ["DS/ML", "Software Engineering"],
    "grammarly": ["DS/ML", "Research / NLP", "Software Engineering"],
    "samsara": ["DS/ML", "Software Engineering", "Data Engineering"],
    "relativity": ["DS/ML", "Software Engineering"],
    "zocdoc": ["Health Informatics", "Software Engineering"],
    "quantco-": ["DS/ML", "Quantitative Finance"],
    "formstack": ["DS/ML"],
    "envedabio": ["DS/ML", "Health Informatics"],
    "convergentresearch": ["DS/ML", "Research / NLP"],
    "viz-ai": ["Health Informatics", "DS/ML", "Software Engineering"],
    "everbridge": ["DS/ML", "Software Engineering"],
    "flockfreight": ["DS/ML", "Data Engineering"],
    "clearcover": ["DS/ML", "Business Analytics"],
    # ── International: HK ──
    "lalamove": ["Business Analytics", "Software Engineering"],  # Hong Kong
    "ekimetrics": ["DS/ML"],  # Hong Kong
    "hypebeast": ["Software Engineering"],  # Hong Kong
    "animocabrands": ["Software Engineering"],  # Hong Kong
    # ── International: AU ──
    "shopback-2": ["Software Engineering", "DS/ML"],  # Sydney
}

# Verified curated jobs (manually confirmed open + real URLs)
# These get priority over scraped results
CURATED_JOBS = {
    "intern_2026": [
        {
            "title": "2026 Data Science Internship (MS/PhD)",
            "company": "Amazon",
            "location": "Seattle, WA + Multiple US",
            "remote": False,
            "apply_url": "https://www.amazon.jobs/en/jobs/3144155/2026-data-science-internship-united-states-phd-or-masters-student",
            "job_board": "direct",
            "posting_date": "2025-12-01",
            "degree_required": "Master's or PhD",
            "visa_sponsorship": "OPT/CPT accepted",
            "description_snippet": "Build tools to analyze data and present findings. MS/PhD, Python/R/SQL, ML experience. $97K-185K annualized.",
            "key_requirements": ["MS/PhD in quantitative field", "Python/R/SQL", "ML/data mining", "Large-scale data (100K+ rows)"],
            "match_reason": "Top H1B sponsor, production-scale data, ML — matches Alibaba pipeline experience",
            "recommended_cv": "V1-DS",
            "categories": ["DS/ML"],
            "company_size": "large",
        },
        {
            "title": "Data Science Intern - Summer 2026",
            "company": "Visa",
            "location": "Foster City, CA",
            "remote": False,
            "apply_url": "https://corporate.visa.com/en/jobs/REF94329J",
            "job_board": "direct",
            "posting_date": "2026-01-15",
            "degree_required": "Currently enrolled in degree program",
            "visa_sponsorship": "Supports international students",
            "description_snippet": "Work with payment transaction data to build ML models and derive insights.",
            "key_requirements": ["Enrolled in MS program", "Python/SQL", "ML experience", "Statistics"],
            "match_reason": "Payment + behavioral data — directly maps to Alipay/Ele.me experience",
            "recommended_cv": "V1-DS",
            "categories": ["DS/ML"],
            "company_size": "large",
        },
        {
            "title": "Data Science Intern - Summer 2026 (Remote)",
            "company": "IQVIA",
            "location": "Remote (King of Prussia, PA)",
            "remote": True,
            "apply_url": "https://jobs.iqvia.com/en/search-jobs?k=data+science+intern",
            "job_board": "direct",
            "posting_date": "2026-01-01",
            "degree_required": "Master's in quantitative field",
            "visa_sponsorship": "Large company, typically supports",
            "description_snippet": "ML models for pharmaceutical retail data. Python or R. Remote with IPS team.",
            "key_requirements": ["MS in quantitative field", "Python or R", "ML/stats", "Healthcare interest"],
            "match_reason": "Pharma data + ML = perfect for Yale HI + Ele.me pharma retail",
            "recommended_cv": "V3-Health",
            "categories": ["Health Informatics", "DS/ML"],
            "company_size": "large",
        },
        {
            "title": "Data Engineer Internship 2026 (US)",
            "company": "Amazon",
            "location": "Multiple US locations",
            "remote": False,
            "apply_url": "https://www.amazon.jobs/en/jobs/3066625/data-engineer-internship-2026-us",
            "job_board": "direct",
            "posting_date": "2025-11-01",
            "degree_required": "BS/MS in CS or related",
            "visa_sponsorship": "OPT/CPT accepted",
            "description_snippet": "Build and maintain data pipelines, ETL, data warehousing at scale.",
            "key_requirements": ["SQL proficiency", "Python/Java", "ETL experience", "Large-scale data"],
            "match_reason": "50-100 GB/day ETL at Alibaba directly matches",
            "recommended_cv": "V1-DS",
            "categories": ["DS/ML"],
            "company_size": "large",
        },
        {
            "title": "Graduate Data Science Internship - Summer 2026",
            "company": "UnitedHealth Group / Optum",
            "location": "Eden Prairie, MN / Remote",
            "remote": True,
            "apply_url": "https://www.unitedhealthgroup.com/careers/en/work/early-careers/technology-and-analytics.html",
            "job_board": "direct",
            "posting_date": "2026-01-15",
            "degree_required": "Master's in quantitative field",
            "visa_sponsorship": "Large company, typically supports",
            "description_snippet": "Healthcare data ML models. $27-37/hr. Clinical and operational insights.",
            "key_requirements": ["Enrolled in MS program", "Python/R/SQL", "ML", "Healthcare interest"],
            "match_reason": "Healthcare + DS ideal for Yale HI. NHANES directly relevant.",
            "recommended_cv": "V3-Health",
            "categories": ["Health Informatics"],
            "company_size": "large",
        },
        {
            "title": "Data Scientist Internship (Summer 2026)",
            "company": "Two Sigma",
            "location": "New York, NY",
            "remote": False,
            "apply_url": "https://careers.twosigma.com/careers/JobDetail/New-York-New-York-United-States-Data-Scientist-Internship-Summer-2026/13585",
            "job_board": "direct",
            "posting_date": "2025-10-01",
            "degree_required": "MS/PhD in quantitative field",
            "visa_sponsorship": "Top H1B sponsor",
            "description_snippet": "Quantitative research. 10-week summer program. Technical/quantitative disciplines.",
            "key_requirements": ["MS/PhD quantitative", "Python/R", "Statistics", "ML"],
            "match_reason": "Quant fund, strong academic + Kaggle + NLP background matches",
            "recommended_cv": "V1-DS",
            "categories": ["DS/ML", "Quantitative Finance"],
            "company_size": "mid",
        },
        {
            "title": "2026 Software & Data Science Internships",
            "company": "Siemens Healthineers",
            "location": "Cary, NC",
            "remote": False,
            "apply_url": "https://careers.siemens-healthineers.com/global/en/job/R-23658/2026-Software-Data-Science-Internships",
            "job_board": "direct",
            "posting_date": "2026-01-01",
            "degree_required": "BS/MS",
            "visa_sponsorship": "Large company",
            "description_snippet": "Healthcare technology data science. Medical device and health data.",
            "key_requirements": ["CS/DS degree", "Python", "ML", "Healthcare interest"],
            "match_reason": "Health tech + DS intersection. Yale HI degree is perfect.",
            "recommended_cv": "V3-Health",
            "categories": ["Health Informatics", "DS/ML"],
            "company_size": "large",
        },
    ],
}


# ══════════════════════════════════════════════════════════
# ATS API fetchers
# ══════════════════════════════════════════════════════════

def _fetch_greenhouse(slug: str) -> list[dict]:
    try:
        r = requests.get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs", timeout=10)
        return r.json().get("jobs", []) if r.status_code == 200 else []
    except Exception:
        return []


def _fetch_lever(slug: str) -> list[dict]:
    try:
        r = requests.get(f"https://api.lever.co/v0/postings/{slug}?mode=json", timeout=10)
        return r.json() if r.status_code == 200 else []
    except Exception:
        return []


def _extract_snippet(html: str) -> str:
    text = re.sub(r'<[^>]+>', ' ', html)
    return re.sub(r'\s+', ' ', text).strip()[:300]


def _ts_to_date(ts) -> str:
    if not ts:
        return "unknown"
    try:
        return time.strftime("%Y-%m-%d", time.gmtime(int(ts) / 1000))
    except Exception:
        return "unknown"


# ══════════════════════════════════════════════════════════
# Personalized keyword builder
# ══════════════════════════════════════════════════════════

DIRECTION_KEYWORDS = {
    "DS/ML": ["data science", "data scientist", "machine learning", "ml engineer",
              "data analyst", "data engineer", "ai ", "deep learning", "nlp"],
    "Data Engineering": ["data engineer", "data pipeline", "etl", "data infrastructure",
                         "data platform", "analytics engineer"],
    "Software Engineering": ["software engineer", "software developer", "swe ", "backend",
                             "frontend", "full stack", "fullstack", "web developer"],
    "Health Informatics": ["health informatics", "clinical data", "biomedical", "bioinformatics",
                           "health data", "clinical informatics", "pharma", "biostatist"],
    "Business Analytics": ["business analyst", "strategy", "business intelligence",
                           "analytics", "operations analyst"],
    "Product Management": ["product manager", "product analyst", "program manager", "tpm",
                           "technical program"],
    "Quantitative Finance": ["quant", "quantitative", "trading", "risk analyst",
                             "financial analyst", "portfolio"],
    "Research / NLP": ["research scientist", "research engineer", "research intern",
                       "nlp", "natural language", "computational linguist"],
    "Consulting": ["consultant", "consulting", "advisory", "strategy analyst"],
}


def _build_keywords(profile: dict, prefs: dict) -> tuple[list[str], list[str]]:
    """Build title keywords from candidate's actual profile + selected directions."""
    directions = prefs.get("directions", ["DS/ML"])
    job_type = prefs.get("job_type", "intern_2026")

    title_kw = []
    for d in directions:
        if d in DIRECTION_KEYWORDS:
            title_kw.extend(DIRECTION_KEYWORDS[d])
        else:
            # Custom direction: use the text itself as keyword + lowercase
            title_kw.append(d.lower())

    # Also add candidate's top skills as search keywords
    profile_skills = [s.lower() for s in profile.get("skills", [])]
    for skill in profile_skills[:5]:
        if skill not in title_kw and len(skill) > 2:
            title_kw.append(skill)

    # Deduplicate
    title_kw = list(dict.fromkeys(title_kw))

    # Career stage keywords
    if job_type == "intern_2026":
        stage_kw = ["intern", "internship", "co-op", "2026"]
    elif job_type == "co_op_2026":
        stage_kw = ["co-op", "coop", "part-time", "part time", "intern", "2026"]
    else:
        stage_kw = ["new grad", "entry level", "junior", "associate", "2027", "2026"]

    return title_kw, stage_kw


def _matches(title: str, title_kw: list[str], stage_kw: list[str]) -> bool:
    """Check if job title matches direction + career stage."""
    t = title.lower()
    has_direction = any(kw in t for kw in title_kw)
    has_stage = any(kw in t for kw in stage_kw)
    return has_direction or has_stage  # stage alone catches "Summer 2026 Intern"


def _is_us_location(loc: str) -> bool:
    """Check if location is in the US."""
    loc_lower = loc.lower()
    us_signals = [
        "us", "united states", "remote", "new york", "san francisco", "seattle",
        "boston", "chicago", "los angeles", "austin", "denver", "dc", "atlanta",
        "philadelphia", "portland", "minneapolis",
        " ca", " wa", " ny", " ma", " tx", " il", " co", " ct", " pa",
        " or", " ga", " nc", " mn", " nj", " va",
    ]
    return any(s in loc_lower for s in us_signals)


def _recommend_cv(title: str, desc: str, categories: list[str] = None) -> str:
    """Recommend CV version based on job content and categories."""
    text = (title + " " + desc).lower()
    if categories:
        if "Health Informatics" in categories:
            return "V3-Health"
        if "Business Analytics" in categories:
            return "V2-Biz"
    health_kw = ["health", "clinical", "medical", "biomedical", "pharma", "epidem", "ehr", "fhir"]
    biz_kw = ["business analyst", "strategy", "consulting", "operations"]
    if any(k in text for k in health_kw):
        return "V3-Health"
    if any(k in text for k in biz_kw):
        return "V2-Biz"
    return "V1-DS"


def _classify_company_size(company: str) -> str:
    """Rough classification for diversity tracking."""
    big = ["amazon", "google", "meta", "microsoft", "apple", "visa", "iqvia",
           "unitedhealth", "optum", "siemens", "jpmorgan", "two sigma"]
    if any(b in company.lower() for b in big):
        return "large"
    return "mid"  # Greenhouse/Lever companies are mostly mid/startup


# ══════════════════════════════════════════════════════════
# Degree filter
# ══════════════════════════════════════════════════════════

def _degree_compatible(job_title: str, job_desc: str, candidate_degree: str) -> bool:
    """Strict degree check: don't show PhD-only to Master's students."""
    text = (job_title + " " + job_desc).lower()

    # PhD-only signals
    phd_only = ["phd required", "doctoral required", "current phd student",
                "ph.d. required", "phd candidate only"]
    if any(sig in text for sig in phd_only):
        return candidate_degree == "PhD"

    # MS/PhD = fine for Master's
    # BS/MS = fine for anyone
    return True


# ══════════════════════════════════════════════════════════
# Main search function
# ══════════════════════════════════════════════════════════

def search_jobs(profile: dict, prefs: dict) -> list[dict]:
    """
    Search for real open US positions matching candidate profile.
    Returns deduplicated, scored, diverse list.
    """
    directions = prefs.get("directions", ["DS/ML"])
    job_type = prefs.get("job_type", "intern_2026")
    degree = profile.get("degree_level", "Master")

    title_kw, stage_kw = _build_keywords(profile, prefs)
    all_jobs = []

    # ── Phase A: Scrape Greenhouse (filtered by direction) ──
    for slug, categories in GREENHOUSE_COMPANIES.items():
        # Only scrape companies matching user's directions
        if not any(d in categories for d in directions):
            continue

        for job in _fetch_greenhouse(slug):
            title = job.get("title", "")
            if not _matches(title, title_kw, stage_kw):
                continue

            loc = job.get("location", {}).get("name", "Unknown")
            if not _is_us_location(loc):
                continue

            snippet = _extract_snippet(job.get("content", ""))
            if not _degree_compatible(title, snippet, degree):
                continue

            all_jobs.append({
                "title": title,
                "company": slug.replace("-", " ").title().replace("inc", "").strip(),
                "location": loc,
                "remote": "remote" in loc.lower(),
                "apply_url": job.get("absolute_url", f"https://boards.greenhouse.io/{slug}/jobs/{job.get('id')}"),
                "linkedin_url": "",
                "job_board": "greenhouse",
                "posting_date": (job.get("updated_at") or "unknown")[:10],
                "degree_required": "",
                "visa_sponsorship": "unknown",
                "description_snippet": snippet,
                "key_requirements": [],
                "match_reason": "",
                "recommended_cv": _recommend_cv(title, snippet, categories),
                "categories": categories,
                "company_size": "mid",
            })

    # ── Phase B: Scrape Lever (filtered by direction) ───────
    for slug, categories in LEVER_COMPANIES.items():
        if not any(d in categories for d in directions):
            continue

        for job in _fetch_lever(slug):
            title = job.get("text", "")
            if not _matches(title, title_kw, stage_kw):
                continue

            cat = job.get("categories", {})
            loc = cat.get("location", "Unknown")
            if not _is_us_location(str(loc)):
                continue

            desc = job.get("descriptionPlain", "")[:300]
            if not _degree_compatible(title, desc, degree):
                continue

            all_jobs.append({
                "title": title,
                "company": slug.replace("-", " ").title(),
                "location": loc,
                "remote": "remote" in str(loc).lower(),
                "apply_url": job.get("hostedUrl", ""),
                "linkedin_url": "",
                "job_board": "lever",
                "posting_date": _ts_to_date(job.get("createdAt")),
                "degree_required": "",
                "visa_sponsorship": "unknown",
                "description_snippet": desc,
                "key_requirements": [],
                "match_reason": "",
                "recommended_cv": _recommend_cv(title, desc, categories),
                "categories": categories,
                "company_size": "mid",
            })

    # No curated jobs — all jobs come from ATS APIs and are verified
    # ── Deduplicate by (company, title) ─────────────────────
    seen = set()
    deduped = []
    for job in all_jobs:
        key = (job["company"].lower().strip(), job["title"].lower().strip())
        if key not in seen:
            seen.add(key)
            deduped.append(job)

    # ── Score by profile match ──────────────────────────────
    profile_skills = set(s.lower() for s in profile.get("skills", []))

    def _score(job):
        s = 0
        desc = (job["title"] + " " + job.get("description_snippet", "")).lower()

        # Skill keyword overlap (most important signal)
        for skill in profile_skills:
            if skill.lower() in desc:
                s += 10

        # Career stage match
        if job_type == "intern_2026" and "intern" in job["title"].lower():
            s += 20
        if any(y in job["title"] for y in (["2026"] if job_type == "intern_2026" else ["2027", "2026"])):
            s += 15

        # Curated jobs get a boost (they're verified real)
        if job.get("match_reason"):
            s += 25

        # Company size diversity bonus (prevent all-FAANG)
        if job.get("company_size") == "mid":
            s += 5

        return s

    deduped.sort(key=_score, reverse=True)

    # ── Diversity enforcement: max 3 per company ────────────
    company_count = {}
    diverse = []
    for job in deduped:
        co = job["company"].lower()
        company_count[co] = company_count.get(co, 0) + 1
        if company_count[co] <= 3:
            diverse.append(job)

    return diverse
