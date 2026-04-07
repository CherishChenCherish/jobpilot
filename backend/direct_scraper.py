"""Direct scraper: fetch jobs from big company career APIs.

These companies don't use Greenhouse/Lever, but have public JSON APIs.
Each function returns a list of job dicts ready for verification.
"""

import re
import requests
from urllib.parse import quote_plus

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
}

INTERN_KEYWORDS = ["intern", "internship", "co-op"]

NOISE_TITLES = ["senior", "lead ", "director", "manager", "principal",
                "staff ", " vp ", "android", "design", "legal", "tax"]


def _is_intern_title(title: str) -> bool:
    t = title.lower()
    if not any(kw in t for kw in INTERN_KEYWORDS):
        return False
    if any(n in t for n in NOISE_TITLES):
        return False
    return True


# ── Amazon ──────────────────────────────────────────────

def fetch_amazon(query: str = "intern", country: str = "USA",
                 max_results: int = 50) -> list[dict]:
    """Fetch intern jobs from Amazon's public search API."""
    jobs = []
    offset = 0
    while len(jobs) < max_results:
        url = (f"https://www.amazon.jobs/en/search.json"
               f"?base_query={quote_plus(query)}"
               f"&country={quote_plus(country)}"
               f"&result_limit=25&offset={offset}")
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            if r.status_code != 200:
                break
            data = r.json()
            batch = data.get("jobs", [])
            if not batch:
                break
            for j in batch:
                title = j.get("title", "")
                if not _is_intern_title(title):
                    continue
                loc = j.get("normalized_location", j.get("location", ""))
                job_id = j.get("id_icims", j.get("id", ""))
                jobs.append({
                    "title": title,
                    "company": "Amazon",
                    "location": loc,
                    "apply_url": f"https://www.amazon.jobs/en/jobs/{job_id}",
                    "job_board": "amazon_careers",
                })
            offset += 25
            if offset >= data.get("hits", 0):
                break
        except Exception as e:
            print(f"  [amazon] Error: {e}")
            break
    return jobs


# ── Netflix ─────────────────────────────────────────────

def fetch_netflix(query: str = "intern", max_results: int = 50) -> list[dict]:
    """Fetch intern jobs from Netflix's Explore Jobs API."""
    jobs = []
    start = 0
    while len(jobs) < max_results:
        url = (f"https://explore.jobs.netflix.net/api/apply/v2/jobs"
               f"?domain=netflix.com&query={quote_plus(query)}"
               f"&num=25&start={start}")
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            if r.status_code != 200:
                break
            data = r.json()
            positions = data.get("positions", [])
            if not positions:
                break
            for j in positions:
                title = j.get("name", "")
                if not _is_intern_title(title):
                    continue
                loc = j.get("location", "")
                apply_url = j.get("url", j.get("canonicalPositionUrl", ""))
                if not apply_url and j.get("id"):
                    apply_url = f"https://explore.jobs.netflix.net/careers/job/{j['id']}"
                jobs.append({
                    "title": title,
                    "company": "Netflix",
                    "location": loc,
                    "apply_url": apply_url,
                    "job_board": "netflix_careers",
                })
            start += 25
            if start >= data.get("count", 0):
                break
        except Exception as e:
            print(f"  [netflix] Error: {e}")
            break
    return jobs


# ── Nvidia (Workday) ────────────────────────────────────

def fetch_nvidia(query: str = "intern", max_results: int = 50) -> list[dict]:
    """Fetch intern jobs from Nvidia's Workday API."""
    url = "https://nvidia.wd5.myworkdayjobs.com/wday/cxs/nvidia/NVIDIAExternalCareerSite/jobs"
    jobs = []
    offset = 0
    while len(jobs) < max_results:
        body = {
            "appliedFacets": {},
            "limit": 20,
            "offset": offset,
            "searchText": query,
        }
        try:
            r = requests.post(url, json=body, headers={
                **HEADERS, "Content-Type": "application/json"
            }, timeout=10)
            if r.status_code != 200:
                break
            data = r.json()
            postings = data.get("jobPostings", [])
            if not postings:
                break
            for j in postings:
                title = j.get("title", "")
                if not _is_intern_title(title):
                    continue
                loc = j.get("locationsText", "")
                path = j.get("externalPath", "")
                apply_url = f"https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite{path}" if path else ""
                jobs.append({
                    "title": title,
                    "company": "Nvidia",
                    "location": loc,
                    "apply_url": apply_url,
                    "job_board": "nvidia_careers",
                })
            offset += 20
            total = data.get("total", 0)
            if offset >= total:
                break
        except Exception as e:
            print(f"  [nvidia] Error: {e}")
            break
    return jobs


# ── JPMorgan (Oracle HCM) ──────────────────────────────

def fetch_jpmorgan(query: str = "intern", max_results: int = 50) -> list[dict]:
    """Fetch intern jobs from JPMorgan's Oracle HCM API."""
    url = (f"https://jpmc.fa.oraclecloud.com/hcmRestApi/resources/latest/"
           f"recruitingCEJobRequisitions?onlyData=true&expand=requisitionList"
           f"&finder=findReqs;siteNumber=CX_1001,keyword={quote_plus(query)}"
           f",limit=25,offset=0")
    jobs = []
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            return []
        data = r.json()
        items = data.get("items", [{}])
        if items:
            req_list = items[0].get("requisitionList", [])
            for j in req_list[:max_results]:
                title = j.get("Title", "")
                if not _is_intern_title(title):
                    continue
                loc = j.get("PrimaryLocation", "")
                req_id = j.get("Id", "")
                jobs.append({
                    "title": title,
                    "company": "JPMorgan Chase",
                    "location": loc,
                    "apply_url": f"https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/job/{req_id}",
                    "job_board": "jpmorgan_careers",
                })
    except Exception as e:
        print(f"  [jpmorgan] Error: {e}")
    return jobs


# ── Aggregate all ───────────────────────────────────────

ALL_FETCHERS = [
    ("Amazon", fetch_amazon),
    ("Netflix", fetch_netflix),
    ("Nvidia", fetch_nvidia),
    ("JPMorgan", fetch_jpmorgan),
]


def fetch_all_direct(max_per_company: int = 30) -> list[dict]:
    """Fetch intern jobs from all direct company APIs."""
    all_jobs = []
    for name, fetcher in ALL_FETCHERS:
        try:
            jobs = fetcher(max_results=max_per_company)
            print(f"  [direct] {name}: {len(jobs)} intern jobs")
            all_jobs.extend(jobs)
        except Exception as e:
            print(f"  [direct] {name} failed: {e}")
    return all_jobs
