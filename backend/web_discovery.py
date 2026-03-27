"""Web discovery: find intern jobs via search engines.

Uses DuckDuckGo HTML search (no API key needed).
Every job must pass verification before storage.
"""

import re
import time
import requests
from typing import Any
from datetime import datetime, timezone
from urllib.parse import quote_plus, urlparse

from models import db, CachedJob
from verifier import verify_one
from searcher import infer_region

# ── Aggregator domains to skip ────────────────────────────

AGGREGATORS = {
    "linkedin.com", "indeed.com", "glassdoor.com", "ziprecruiter.com",
    "monster.com", "simplyhired.com", "handshake.com", "seek.com.au",
    "seek.com", "reed.co.uk", "totaljobs.com", "cwjobs.co.uk",
    "jobsite.co.uk", "mycareer.com.au", "zhipin.com", "liepin.com",
    "lagou.com", "51job.com", "zhaopin.com", "boss.com",
    "careerbuilder.com", "dice.com", "angel.co", "wellfound.com",
    "adzuna.com", "jora.com", "neuvoo.com", "talent.com",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
}

# ── Query generation ──────────────────────────────────────

DIRECTION_SEARCH_TERMS = {
    "DS/ML": ["data science intern", "machine learning intern", "data analyst intern"],
    "Software Engineering": ["software engineer intern", "software developer intern"],
    "Data Engineering": ["data engineer intern", "data pipeline intern"],
    "Health Informatics": ["health informatics intern", "clinical data intern", "biomedical data intern"],
    "Business Analytics": ["business analyst intern", "strategy analyst intern"],
    "Quantitative Finance": ["quantitative analyst intern", "quant trading intern"],
    "Research / NLP": ["research intern AI", "NLP research intern"],
    "Product Management": ["product manager intern", "APM intern"],
    "Consulting": ["consulting intern", "management consulting intern"],
}

REGION_SEARCH_SUFFIXES = {
    "US": ["USA", "United States"],
    "CA": ["Canada", "Toronto", "Vancouver"],
    "UK": ["UK", "London", "United Kingdom"],
    "AU": ["Australia", "Sydney", "Melbourne"],
    "HK": ["Hong Kong"],
    "CN": ["中国", "实习", "招聘"],
}

CN_DIRECTION_TERMS = {
    "DS/ML": ["数据科学 实习", "机器学习 实习", "数据分析 实习"],
    "Software Engineering": ["软件工程 实习", "后端开发 实习"],
    "Health Informatics": ["医疗数据 实习", "生物信息 实习"],
    "Business Analytics": ["商业分析 实习", "战略分析 实习"],
    "Quantitative Finance": ["量化分析 实习", "量化交易 实习"],
}


def _build_queries(regions: list, directions: list) -> list[tuple[str, str]]:
    """Generate search queries. Returns [(query_string, target_region), ...]"""
    queries = []
    for region in regions:
        for direction in directions:
            if region == "CN":
                # Chinese language queries
                cn_terms = CN_DIRECTION_TERMS.get(direction, [f"{direction} 实习"])
                for term in cn_terms[:2]:
                    queries.append((f"{term} 2026 官网 招聘", "CN"))
            else:
                terms = DIRECTION_SEARCH_TERMS.get(direction, [f"{direction} intern"])
                suffixes = REGION_SEARCH_SUFFIXES.get(region, [region])
                for term in terms[:2]:
                    for suffix in suffixes[:1]:
                        queries.append((f"{term} 2026 {suffix} careers apply", region))
    return queries


# ── DuckDuckGo search ─────────────────────────────────────

def _search_ddg(query: str, max_results: int = 10) -> list[str]:
    """Search DuckDuckGo HTML and extract URLs."""
    try:
        url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code != 200:
            return []

        # Extract result URLs
        urls = re.findall(r'href="(https?://[^"]+)"', r.text)

        # Filter out DuckDuckGo internal URLs
        filtered = []
        for u in urls:
            parsed = urlparse(u)
            domain = parsed.netloc.lower()
            if "duckduckgo" in domain:
                continue
            if any(agg in domain for agg in AGGREGATORS):
                continue
            # Keep URLs that look like career pages
            path = parsed.path.lower() + parsed.query.lower()
            career_signals = ["career", "jobs", "hiring", "talent", "recruit",
                              "campus", "graduate", "intern", "hr", "work", "apply"]
            if any(s in domain or s in path for s in career_signals):
                filtered.append(u)
            elif len(filtered) < 3:
                # Also keep first few non-aggregator results
                filtered.append(u)

        return filtered[:max_results]
    except Exception as e:
        print(f"  [ddg] Search failed: {e}")
        return []


# ── Job extraction from page ──────────────────────────────

def _extract_job_from_url(url: str, target_region: str) -> dict | None:
    """Fetch a URL and try to extract job info."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=8, allow_redirects=True)
        if r.status_code != 200:
            return None
        if "captcha" in r.text.lower() or "login" in r.url.lower():
            return None

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(r.text, "lxml")

        # Extract title
        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True)[:120] if title_tag else ""
        og_title = soup.find("meta", property="og:title")
        if og_title:
            title = og_title.get("content", title)[:120]

        # Extract company
        company = ""
        og_site = soup.find("meta", property="og:site_name")
        if og_site:
            company = og_site.get("content", "")[:60]
        if not company:
            # Try domain name
            company = urlparse(url).netloc.replace("www.", "").split(".")[0].title()

        # Location
        location = ""
        for meta_name in ["geo.region", "geo.placename"]:
            tag = soup.find("meta", attrs={"name": meta_name})
            if tag:
                location = tag.get("content", "")
                break

        if not location:
            # Try to find location in page text
            text = soup.get_text(" ", strip=True)[:2000].lower()
            from searcher import REGION_MAP_CITIES
            for region_code, signals in REGION_MAP_CITIES.items():
                for s in signals:
                    if s in text:
                        location = s.title()
                        break
                if location:
                    break

        return {
            "title": title,
            "company": company,
            "location": location or target_region,
            "apply_url": r.url,  # Use final URL after redirects
        }
    except Exception:
        return None


# ── Quality filter ────────────────────────────────────────

def _is_quality_job(title: str) -> bool:
    """Check if job title suggests intern/entry level and is relevant."""
    title_lower = title.lower()

    # Must contain intern signal
    if not re.search(r'\bintern\b|\binternship\b|\b实习\b', title_lower):
        return False

    # Must NOT contain senior/director signals
    bad = ["senior", "lead", "manager", "director", "phd", "principal", "staff", "vp"]
    if any(b in title_lower for b in bad):
        return False

    # Noise filter
    noise = ["android", "design", "legal", "tax", "mba ", "support"]
    if any(n in title_lower for n in noise):
        return False

    return True


# ── Main discovery function ───────────────────────────────

def discover_jobs(regions: list, directions: list, max_per_combination: int = 10) -> list[dict]:
    """Discover jobs via web search. Returns verified job dicts ready to store."""
    queries = _build_queries(regions, directions)
    print(f"[discovery] Generated {len(queries)} queries for {regions} x {directions}")

    all_urls = set()
    url_region_map = {}
    failed_domains = set()

    # Search phase
    for i, (query, region) in enumerate(queries):
        if len(all_urls) >= 30:  # Cap at 30 URLs total
            break
        print(f"  [{i+1}/{len(queries)}] Searching: {query[:50]}...")
        urls = _search_ddg(query)
        for u in urls:
            if u not in all_urls:
                all_urls.add(u)
                url_region_map[u] = region
        time.sleep(2.5)  # Rate limit

    print(f"[discovery] Found {len(all_urls)} candidate URLs")

    # Extract + verify phase
    verified = []
    processed = 0

    for url in list(all_urls)[:30]:
        domain = urlparse(url).netloc
        if domain in failed_domains:
            continue

        # Skip if already in DB
        if CachedJob.query.filter_by(apply_url=url).first():
            continue

        target_region = url_region_map.get(url, "US")
        job = _extract_job_from_url(url, target_region)

        if not job:
            failed_domains.add(domain)
            continue

        if not _is_quality_job(job["title"]):
            continue

        processed += 1
        region = infer_region(job["location"])
        is_cn = (region == "CN" or target_region == "CN")

        # Verify
        if is_cn:
            # CN: just check HTTP 200 + title present
            confidence = "medium"
            print(f"  CN verified (HTTP 200): {job['company']} — {job['title']}")
        else:
            # All others: full verify_one
            job_dict = {"apply_url": job["apply_url"], "job_board": "web_discovery",
                        "title": job["title"], "company": job["company"]}
            result = verify_one(job_dict, {"degree_level": "Master"}, {"visa_needed": False})
            audit = result.get("audit", {})
            if not (audit.get("status", "").startswith("\u2713") and audit.get("confidence") == "high"):
                continue
            confidence = "high"

        verified.append({
            "company": job["company"],
            "title": job["title"],
            "apply_url": job["apply_url"],
            "location": job["location"],
            "region": region if region != "US" else target_region,
            "language": "CN" if is_cn else "EN",
            "confidence": confidence,
            "discovery_source": "web_discovery",
        })
        print(f"  VERIFIED [{region}]: {job['company']} — {job['title'][:40]}")

        time.sleep(2)  # Rate limit

        if len(verified) >= max_per_combination * len(regions):
            break

    print(f"[discovery] Result: {len(all_urls)} URLs → {processed} processed → {len(verified)} verified")
    return verified
