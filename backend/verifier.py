"""JobPilot job verifier — confirm each posting is genuinely still open."""

import os
import re
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

# ── Constants ──────────────────────────────────────────────

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

CLOSED_PHRASES = [
    "this job is no longer available",
    "this position has been filled",
    "this posting has expired",
    "no longer accepting applications",
    "position has been closed",
    "this requisition is no longer open",
    "job has been removed",
    "this opening is closed",
    "this role has been filled",
    "job listing has expired",
    "this opportunity is no longer available",
    "sorry, this position is no longer available",
    "this job post is closed",
    "this position is closed",
    "job not found",
    "the position you are looking for is no longer posted",
]

OPEN_PHRASES = [
    "apply now",
    "apply for this job",
    "submit application",
    "apply for this position",
    "apply to this role",
    "start application",
    "easy apply",
    "quick apply",
    "apply with linkedin",
    "submit your application",
    "apply for this role",
]

PHD_PHRASES = [
    "phd required",
    "doctoral degree required",
    "ph.d. required",
    "ph.d required",
    "requires a phd",
    "must have a phd",
    "current phd student",  # for intern postings requiring PhD enrollment
]

NO_SPONSOR_PHRASES = [
    "no sponsorship available",
    "not able to sponsor",
    "unable to sponsor",
    "does not sponsor",
    "will not sponsor",
    "without the need for employer sponsorship",
    "must be authorized to work in the united states",
    "us citizens and permanent residents only",
    "must be a u.s. citizen",
    "not eligible for visa sponsorship",
    "is not available for work sponsorship",
]

SPONSOR_POSITIVE = [
    "visa sponsorship",
    "will sponsor",
    "sponsorship available",
    " opt ",
    " cpt ",
    " h-1b",
    " h1b ",
    "f-1 ",
    "international students",
]


# ── STEP A: Resolve best URL ──────────────────────────────

def _resolve_url(job: dict) -> tuple[str, bool]:
    """Determine the best URL to verify. Returns (url, needs_manual_check)."""
    url = job.get("apply_url", "")
    board = job.get("job_board", "")

    if not url or not url.startswith("http"):
        return "", True

    # ATS boards are reliable — use directly
    if board in ("greenhouse", "lever"):
        return url, False

    # LinkedIn URLs: try to use, but flag for manual check
    if "linkedin.com" in url:
        return url, True

    # Direct company URLs — use as-is
    return url, False


# ── STEP B: Fetch page ────────────────────────────────────

def _fetch_page(url: str) -> dict:
    """Fetch a URL and return structured result."""
    result = {
        "original_url": url,
        "final_url": url,
        "http_status": 0,
        "page_text": "",
        "soup": None,
        "error": None,
    }

    try:
        r = requests.get(url, headers=HEADERS, timeout=12, allow_redirects=True)
        result["final_url"] = r.url
        result["http_status"] = r.status_code

        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "lxml")
            # Remove script/style tags for cleaner text
            for tag in soup(["script", "style", "noscript"]):
                tag.decompose()
            result["page_text"] = re.sub(r"\s+", " ", soup.get_text(" ", strip=True)).lower()
            result["soup"] = soup
    except requests.Timeout:
        result["error"] = "timeout"
    except requests.ConnectionError:
        result["error"] = "connection_error"
    except Exception as e:
        result["error"] = str(e)

    return result


# ── STEP C: Closed signal detection ──────────────────────

def _check_closed(page: dict) -> tuple[bool, str]:
    """Check for closed signals. Returns (is_closed, reason)."""
    status = page["http_status"]

    # HTTP-level signals
    if status in (404, 410):
        return True, f"HTTP {status} — page not found/removed"
    if status == 0:
        return False, ""  # couldn't fetch — not conclusively closed

    # Redirect: job page → generic jobs listing = removed
    orig = urlparse(page["original_url"])
    final = urlparse(page["final_url"])
    if orig.path != final.path:
        # Original had a specific job ID, final is just /jobs or /careers
        orig_has_id = bool(re.search(r"\d{4,}", orig.path))
        final_is_listing = final.path.rstrip("/") in ("/jobs", "/careers", "/openings", "/en/jobs", "")
        if orig_has_id and final_is_listing:
            return True, f"Redirected from job page to generic listing ({final.path})"

    # Text-based closed signals
    text = page["page_text"]
    for phrase in CLOSED_PHRASES:
        if phrase in text:
            return True, f"Page contains closed signal: '{phrase}'"

    return False, ""


# ── STEP D: Open signal detection ─────────────────────────

def _check_open(page: dict) -> tuple[bool, str]:
    """Check for open signals. Returns (is_open, reason)."""
    text = page["page_text"]
    soup = page.get("soup")

    # Text-based open signals
    for phrase in OPEN_PHRASES:
        if phrase in text:
            return True, f"Found open signal: '{phrase}'"

    # Tag-based: look for apply buttons/links
    if soup:
        for tag in soup.find_all(["button", "a", "input"]):
            tag_text = tag.get_text(" ", strip=True).lower()
            if "apply" in tag_text:
                return True, f"Found apply element: <{tag.name}> '{tag_text[:40]}'"
            # Also check href
            href = tag.get("href", "").lower()
            if "apply" in href or "application" in href:
                return True, f"Found apply link in href: '{href[:60]}'"

    return False, ""


# ── STEP E: Greenhouse/Lever API verification (bonus) ─────

def _verify_via_api(job: dict) -> tuple[str, str]:
    """For Greenhouse/Lever jobs, verify via their JSON API. Fast + definitive."""
    board = job.get("job_board", "")
    url = job.get("apply_url", "")

    if board == "greenhouse":
        # Extract company slug and job ID from URL
        # Pattern: boards.greenhouse.io/COMPANY/jobs/ID or job-boards.greenhouse.io/COMPANY/jobs/ID
        m = re.search(r"greenhouse\.io/([^/]+)/jobs/(\d+)", url)
        if m:
            slug, job_id = m.group(1), m.group(2)
            api_url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs/{job_id}"
            try:
                r = requests.get(api_url, timeout=8)
                if r.status_code == 200:
                    return "open", "Confirmed open via Greenhouse API (job ID exists)"
                elif r.status_code == 404:
                    return "closed", "Greenhouse API returned 404 — job removed"
            except Exception:
                pass

    elif board == "lever":
        # Lever public API: /v0/postings/COMPANY/JOB_ID
        # Or just check if the page loads
        try:
            r = requests.get(url, timeout=8, allow_redirects=False)
            if r.status_code == 200:
                return "open", "Lever posting responds 200"
            elif r.status_code in (301, 302, 404):
                return "closed", f"Lever returned {r.status_code}"
        except Exception:
            pass

    return "unknown", ""


# ── STEP F: Extract posting date ──────────────────────────

def _extract_posting_date(page: dict) -> tuple[str | None, int | None]:
    """Try to find when the job was posted. Returns (date_str, age_days)."""
    text = page["page_text"]
    soup = page.get("soup")
    now = datetime.now(timezone.utc)

    # 1. JSON-LD schema.org datePosted
    if soup:
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
                if isinstance(data, list):
                    data = data[0] if data else {}
                dp = data.get("datePosted")
                if dp:
                    dt = datetime.fromisoformat(dp.replace("Z", "+00:00"))
                    age = (now - dt).days
                    return dp[:10], age
            except Exception:
                pass

    # 2. Meta tags
    if soup:
        for meta_name in ["article:published_time", "datePublished", "date"]:
            tag = soup.find("meta", property=meta_name) or soup.find("meta", attrs={"name": meta_name})
            if tag and tag.get("content"):
                try:
                    dt = datetime.fromisoformat(tag["content"].replace("Z", "+00:00"))
                    age = (now - dt).days
                    return tag["content"][:10], age
                except Exception:
                    pass

    # 3. "X days/weeks ago" in text
    m = re.search(r"(\d+)\s+days?\s+ago", text)
    if m:
        days = int(m.group(1))
        return f"~{days} days ago", days

    m = re.search(r"(\d+)\s+weeks?\s+ago", text)
    if m:
        days = int(m.group(1)) * 7
        return f"~{days} days ago", days

    # 4. Explicit date patterns
    m = re.search(r"(20\d{2}-\d{2}-\d{2})", text)
    if m:
        try:
            dt = datetime.strptime(m.group(1), "%Y-%m-%d").replace(tzinfo=timezone.utc)
            age = (now - dt).days
            return m.group(1), age
        except Exception:
            pass

    return None, None


# ── STEP G: Degree check ─────────────────────────────────

def _check_degree(page: dict, profile: dict) -> str:
    """Check if job requires PhD when candidate doesn't have one."""
    text = page["page_text"]
    user_degree = profile.get("degree_level", "Bachelor")

    for phrase in PHD_PHRASES:
        if phrase in text:
            if user_degree != "PhD":
                return "mismatch"
            return "ok"
    return "ok"  # No PhD requirement found


# ── STEP H: Visa check ───────────────────────────────────

def _check_visa(page: dict) -> str:
    """Check visa sponsorship status from page text."""
    text = page["page_text"]

    # Check negative signals first (more definitive)
    for phrase in NO_SPONSOR_PHRASES:
        if phrase in text:
            return "no_sponsor"

    # Check positive signals
    for phrase in SPONSOR_POSITIVE:
        if phrase in text:
            return "confirmed"

    return "unspecified"


# ── Main: verify one job ──────────────────────────────────

def verify_one(job: dict, profile: dict, prefs: dict) -> dict:
    """Verify a single job posting. Returns job dict with 'audit' key."""
    audit = {
        "url_checked": "",
        "final_url": "",
        "http_status": 0,
        "status": "⚠ Unverified",
        "confidence": "low",
        "reason": "",
        "posting_age_days": None,
        "degree_match": "unknown",
        "visa": "unspecified",
        "drop": False,
        "drop_reason": None,
        "needs_manual_check": False,
    }

    # STEP A: Resolve URL
    url, needs_manual = _resolve_url(job)
    audit["needs_manual_check"] = needs_manual

    if not url:
        audit["reason"] = "No valid URL to verify"
        job["audit"] = audit
        return job

    audit["url_checked"] = url

    # Greenhouse/Lever: try API verification first (fast + definitive)
    if job.get("job_board") in ("greenhouse", "lever"):
        api_status, api_reason = _verify_via_api(job)
        if api_status == "open":
            audit["status"] = "✓ Open"
            audit["confidence"] = "high"
            audit["reason"] = api_reason
            # Still fetch page for degree/visa checks
            page = _fetch_page(url)
            audit["final_url"] = page["final_url"]
            audit["http_status"] = page["http_status"]
            if page["page_text"]:
                audit["degree_match"] = _check_degree(page, profile)
                audit["visa"] = _check_visa(page)
                _, age = _extract_posting_date(page)
                audit["posting_age_days"] = age
            # Degree mismatch → drop
            if audit["degree_match"] == "mismatch":
                audit["drop"] = True
                audit["drop_reason"] = "PhD required — candidate has " + profile.get("degree_level", "?")
            # Visa no_sponsor → drop if needed
            if prefs.get("visa_needed") and audit["visa"] == "no_sponsor":
                audit["drop"] = True
                audit["drop_reason"] = "No visa sponsorship available"
            job["audit"] = audit
            return job
        elif api_status == "closed":
            audit["status"] = "✗ Closed"
            audit["confidence"] = "high"
            audit["reason"] = api_reason
            audit["drop"] = True
            audit["drop_reason"] = api_reason
            job["audit"] = audit
            return job

    # STEP B: Fetch page
    page = _fetch_page(url)
    audit["final_url"] = page["final_url"]
    audit["http_status"] = page["http_status"]

    if page["error"]:
        audit["reason"] = f"Fetch error: {page['error']}"
        audit["needs_manual_check"] = True
        job["audit"] = audit
        return job

    # STEP C: Check closed
    is_closed, closed_reason = _check_closed(page)
    if is_closed:
        audit["status"] = "✗ Closed"
        audit["confidence"] = "high"
        audit["reason"] = closed_reason
        audit["drop"] = True
        audit["drop_reason"] = closed_reason
        job["audit"] = audit
        return job

    # STEP D: Check open
    is_open, open_reason = _check_open(page)
    if is_open:
        audit["status"] = "✓ Open"
        audit["confidence"] = "high"
        audit["reason"] = open_reason
        # Continue to check degree/visa/age
    else:
        audit["status"] = "⚠ Unverified"
        audit["confidence"] = "low"
        audit["reason"] = "No definitive open or closed signal found"
        audit["needs_manual_check"] = True

    # STEP F: Posting date
    date_str, age_days = _extract_posting_date(page)
    audit["posting_age_days"] = age_days
    if age_days and age_days > 90 and audit["status"] == "✓ Open":
        audit["status"] = "⚠ Unverified"
        audit["confidence"] = "medium"
        audit["reason"] = f"Open signals found but posted {age_days} days ago — may be stale"

    # STEP G: Degree check
    audit["degree_match"] = _check_degree(page, profile)
    if audit["degree_match"] == "mismatch":
        audit["drop"] = True
        audit["drop_reason"] = "PhD required — candidate has " + profile.get("degree_level", "?")

    # STEP H: Visa check
    if prefs.get("visa_needed", True):
        audit["visa"] = _check_visa(page)
        if audit["visa"] == "no_sponsor":
            audit["drop"] = True
            audit["drop_reason"] = "No visa sponsorship available"

    job["audit"] = audit
    return job


# ── Main: verify all jobs ─────────────────────────────────

def verify_all_jobs(jobs: list[dict], profile: dict, prefs: dict) -> list[dict]:
    """
    Verify all jobs in parallel. Returns filtered list with audits.
    Drops jobs where audit.drop == True.
    """
    verified = []

    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(verify_one, job, profile, prefs): job for job in jobs}
        for future in as_completed(futures):
            try:
                result = future.result()
                verified.append(result)
            except Exception as e:
                job = futures[future]
                job["audit"] = {
                    "status": "⚠ Unverified",
                    "confidence": "low",
                    "reason": f"Verification error: {e}",
                    "drop": False,
                    "needs_manual_check": True,
                }
                verified.append(job)

    # Separate into kept and dropped
    kept = [j for j in verified if not j.get("audit", {}).get("drop", False)]
    dropped = [j for j in verified if j.get("audit", {}).get("drop", False)]

    # Sort kept: ✓ Open first, then ⚠ Unverified
    status_order = {"✓ Open": 0, "⚠ Unverified": 1, "✗ Closed": 2}
    kept.sort(key=lambda j: status_order.get(j.get("audit", {}).get("status", ""), 9))

    # Log summary
    open_count = sum(1 for j in verified if j.get("audit", {}).get("status") == "✓ Open")
    closed_count = sum(1 for j in verified if j.get("audit", {}).get("status") == "✗ Closed")
    unverified_count = sum(1 for j in verified if j.get("audit", {}).get("status") == "⚠ Unverified")
    print(f"[verifier] Verified {len(verified)} jobs: {open_count} open, {closed_count} closed, {unverified_count} unverified. Dropped {len(dropped)}.")

    return kept
