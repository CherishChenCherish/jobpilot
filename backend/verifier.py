"""JobPilot verifier v2 — paranoid about accuracy.

Philosophy: An honest "unverified" beats a wrong "open".
A "closed" on a truly closed job is critical value.
A "open" on a truly closed job destroys trust instantly.

Approach:
1. ATS API verification first (Greenhouse/Lever) — 100% definitive
2. HTML analysis second — look for definitive signals only
3. When ambiguous, say "unverified" not "open"
4. Ghost job detection: posting age > 60 days = high suspicion
5. Parallel execution for speed
"""

import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# ── Signal dictionaries ───────────────────────────────────

CLOSED_SIGNALS = [
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
    "this page isn't available",
    "we couldn't find that page",
    "page not found",
]

OPEN_SIGNALS = [
    "apply now",
    "apply for this job",
    "submit application",
    "apply for this position",
    "start application",
    "submit your application",
    "apply for this role",
    "apply to this job",
]

PHD_SIGNALS = [
    "phd required",
    "doctoral degree required",
    "ph.d. required",
    "ph.d required",
    "requires a phd",
    "must have a phd",
    "current phd student",
    "currently enrolled in a phd",
]

NO_SPONSOR = [
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
    "not available for work sponsorship",
    "not eligible for f1",
    "not eligible for f-1",
]

YES_SPONSOR = [
    "visa sponsorship",
    "will sponsor",
    "sponsorship available",
    " opt ", " cpt ", " h-1b", " h1b ",
    "f-1 ", "international students",
]


# ══════════════════════════════════════════════════════════
# ATS API verification — 100% definitive
# ══════════════════════════════════════════════════════════

def _verify_greenhouse_api(url: str) -> tuple[str, str, str]:
    """Returns (status, confidence, reason)."""
    m = re.search(r"greenhouse\.io/([^/]+)/jobs/(\d+)", url)
    if not m:
        return "unknown", "low", ""

    slug, job_id = m.group(1), m.group(2)
    api_url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs/{job_id}"
    try:
        r = requests.get(api_url, timeout=8)
        if r.status_code == 200:
            data = r.json()
            title = data.get("title", "")
            return "open", "high", f"Confirmed via Greenhouse API (job #{job_id} active)"
        elif r.status_code == 404:
            return "closed", "high", f"Greenhouse API 404 — job #{job_id} removed/unpublished"
        else:
            return "unknown", "low", f"Greenhouse API returned {r.status_code}"
    except requests.Timeout:
        return "unknown", "low", "Greenhouse API timeout"
    except Exception:
        return "unknown", "low", "Greenhouse API error"


def _verify_lever_api(url: str) -> tuple[str, str, str]:
    """Returns (status, confidence, reason)."""
    try:
        r = requests.get(url, timeout=8, allow_redirects=False, headers=HEADERS)
        if r.status_code == 200:
            return "open", "high", "Lever posting responds 200 (active)"
        elif r.status_code in (301, 302):
            # Lever redirects to /jobs when posting is removed
            loc = r.headers.get("Location", "")
            if "/jobs" in loc and "/jobs/" not in loc:
                return "closed", "high", f"Lever redirected to jobs listing (posting removed)"
            return "unknown", "medium", f"Lever redirected to {loc[:60]}"
        elif r.status_code == 404:
            return "closed", "high", "Lever 404 — posting removed"
        else:
            return "unknown", "low", f"Lever returned {r.status_code}"
    except Exception:
        return "unknown", "low", "Lever connection error"


# ══════════════════════════════════════════════════════════
# HTML page analysis — for non-ATS URLs
# ══════════════════════════════════════════════════════════

def _fetch_page(url: str) -> dict:
    """Fetch URL, return structured result with clean text and soup."""
    result = {"url": url, "final_url": url, "status": 0, "text": "", "soup": None, "error": None}
    try:
        r = requests.get(url, headers=HEADERS, timeout=6, allow_redirects=True)
        result["final_url"] = r.url
        result["status"] = r.status_code
        if r.status_code == 200 and "text/html" in r.headers.get("Content-Type", ""):
            soup = BeautifulSoup(r.text, "lxml")
            for tag in soup(["script", "style", "noscript", "nav", "footer"]):
                tag.decompose()
            result["text"] = re.sub(r"\s+", " ", soup.get_text(" ", strip=True)).lower()
            result["soup"] = soup
    except requests.Timeout:
        result["error"] = "timeout"
    except requests.ConnectionError:
        result["error"] = "connection_error"
    except Exception as e:
        result["error"] = str(e)[:100]
    return result


def _check_redirect_closed(page: dict) -> tuple[bool, str]:
    """Redirect from specific job page to generic listing = closed."""
    orig = urlparse(page["url"])
    final = urlparse(page["final_url"])
    if orig.netloc == final.netloc and orig.path != final.path:
        orig_has_id = bool(re.search(r"\d{4,}", orig.path))
        final_is_listing = final.path.rstrip("/") in ("/jobs", "/careers", "/openings", "/en/jobs", "")
        if orig_has_id and final_is_listing:
            return True, f"Redirected to generic listing ({final.path}) — job removed"
    return False, ""


def _check_closed_text(text: str) -> tuple[bool, str]:
    """Check for definitive closed signals in page text."""
    for phrase in CLOSED_SIGNALS:
        if phrase in text:
            return True, f"Closed signal found: '{phrase}'"
    return False, ""


def _check_open_text(text: str, soup) -> tuple[bool, str]:
    """Check for definitive open signals — text + buttons/links."""
    # Text signals
    for phrase in OPEN_SIGNALS:
        if phrase in text:
            return True, f"Open signal: '{phrase}'"

    # Button/link elements with "apply"
    if soup:
        for tag in soup.find_all(["button", "a", "input"]):
            tag_text = tag.get_text(" ", strip=True).lower()
            if any(s in tag_text for s in ["apply", "submit application"]):
                return True, f"Apply element found: <{tag.name}> '{tag_text[:30]}'"
            href = (tag.get("href") or "").lower()
            if "apply" in href:
                return True, f"Apply link: href='{href[:40]}'"

    return False, ""


def _extract_posting_date(text: str, soup) -> tuple[str | None, int | None]:
    """Extract posting date. Returns (date_str, age_days)."""
    now = datetime.now(timezone.utc)

    # JSON-LD schema.org
    if soup:
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
                if isinstance(data, list):
                    data = data[0] if data else {}
                dp = data.get("datePosted")
                if dp:
                    dt = datetime.fromisoformat(dp.replace("Z", "+00:00"))
                    return dp[:10], (now - dt).days
            except Exception:
                pass

    # "X days/weeks ago"
    m = re.search(r"(\d+)\s+days?\s+ago", text)
    if m:
        return f"~{m.group(1)}d ago", int(m.group(1))
    m = re.search(r"(\d+)\s+weeks?\s+ago", text)
    if m:
        d = int(m.group(1)) * 7
        return f"~{d}d ago", d

    return None, None


def _check_degree(text: str, degree: str) -> str:
    """Check if job requires PhD when candidate doesn't have one."""
    for phrase in PHD_SIGNALS:
        if phrase in text:
            return "mismatch" if degree != "PhD" else "ok"
    return "ok"


def _check_visa(text: str) -> str:
    """Check visa sponsorship signals."""
    for phrase in NO_SPONSOR:
        if phrase in text:
            return "no_sponsor"
    for phrase in YES_SPONSOR:
        if phrase in text:
            return "confirmed"
    return "unspecified"


# ══════════════════════════════════════════════════════════
# Main: verify one job
# ══════════════════════════════════════════════════════════

def verify_one(job: dict, profile: dict, prefs: dict) -> dict:
    """Verify a single job posting. Returns job with 'audit' key."""
    audit = {
        "url_checked": "",
        "final_url": "",
        "http_status": 0,
        "status": "⚠ Unverified",
        "confidence": "low",
        "reason": "Not yet checked",
        "posting_age_days": None,
        "ghost_risk": "unknown",
        "degree_match": "unknown",
        "visa": "unspecified",
        "drop": False,
        "drop_reason": None,
        "needs_manual_check": False,
    }

    url = job.get("apply_url", "")
    board = job.get("job_board", "")

    if not url or not url.startswith("http"):
        audit["reason"] = "No valid URL"
        audit["needs_manual_check"] = True
        job["audit"] = audit
        return job

    audit["url_checked"] = url
    degree = profile.get("degree_level", "Master")

    # ── PRIORITY 1: ATS API verification (100% definitive) ──
    if board == "greenhouse":
        status, conf, reason = _verify_greenhouse_api(url)
        if status in ("open", "closed"):
            audit["status"] = "✓ Open" if status == "open" else "✗ Closed"
            audit["confidence"] = conf
            audit["reason"] = reason
            if status == "closed":
                audit["drop"] = True
                audit["drop_reason"] = reason

            # Still fetch page for degree/visa/age checks if open
            if status == "open":
                page = _fetch_page(url)
                audit["final_url"] = page["final_url"]
                audit["http_status"] = page["status"]
                if page["text"]:
                    audit["degree_match"] = _check_degree(page["text"], degree)
                    audit["visa"] = _check_visa(page["text"])
                    _, age = _extract_posting_date(page["text"], page.get("soup"))
                    audit["posting_age_days"] = age
                    audit["ghost_risk"] = "high" if age and age > 60 else ("medium" if age and age > 30 else "low")

            _apply_drop_rules(audit, degree, prefs)
            job["audit"] = audit
            return job

    if board == "lever":
        status, conf, reason = _verify_lever_api(url)
        if status in ("open", "closed"):
            audit["status"] = "✓ Open" if status == "open" else "✗ Closed"
            audit["confidence"] = conf
            audit["reason"] = reason
            if status == "closed":
                audit["drop"] = True
                audit["drop_reason"] = reason

            if status == "open":
                page = _fetch_page(url)
                audit["final_url"] = page["final_url"]
                audit["http_status"] = page["status"]
                if page["text"]:
                    audit["degree_match"] = _check_degree(page["text"], degree)
                    audit["visa"] = _check_visa(page["text"])

            _apply_drop_rules(audit, degree, prefs)
            job["audit"] = audit
            return job

    # ── PRIORITY 2: HTML page analysis (for direct URLs) ────
    if "linkedin.com" in url:
        audit["needs_manual_check"] = True
        audit["reason"] = "LinkedIn URLs cannot be reliably verified"
        job["audit"] = audit
        return job

    page = _fetch_page(url)
    audit["final_url"] = page["final_url"]
    audit["http_status"] = page["status"]

    if page["error"]:
        audit["reason"] = f"Fetch error: {page['error']}"
        audit["needs_manual_check"] = True
        job["audit"] = audit
        return job

    # HTTP-level closed
    if page["status"] in (404, 410):
        audit["status"] = "✗ Closed"
        audit["confidence"] = "high"
        audit["reason"] = f"HTTP {page['status']} — page removed"
        audit["drop"] = True
        audit["drop_reason"] = audit["reason"]
        job["audit"] = audit
        return job

    # Redirect closed
    is_redirect_closed, redirect_reason = _check_redirect_closed(page)
    if is_redirect_closed:
        audit["status"] = "✗ Closed"
        audit["confidence"] = "high"
        audit["reason"] = redirect_reason
        audit["drop"] = True
        audit["drop_reason"] = redirect_reason
        job["audit"] = audit
        return job

    # Text-based closed (check FIRST — closed is more definitive)
    is_closed, closed_reason = _check_closed_text(page["text"])
    if is_closed:
        audit["status"] = "✗ Closed"
        audit["confidence"] = "high"
        audit["reason"] = closed_reason
        audit["drop"] = True
        audit["drop_reason"] = closed_reason
        job["audit"] = audit
        return job

    # Text-based open
    is_open, open_reason = _check_open_text(page["text"], page.get("soup"))
    if is_open:
        audit["status"] = "✓ Open"
        audit["confidence"] = "high"
        audit["reason"] = open_reason
    else:
        # Ambiguous — be honest
        audit["status"] = "⚠ Unverified"
        audit["confidence"] = "low"
        audit["reason"] = "No definitive open or closed signal found on page"
        audit["needs_manual_check"] = True

    # Posting age + ghost risk
    _, age = _extract_posting_date(page["text"], page.get("soup"))
    audit["posting_age_days"] = age
    if age:
        if age > 90:
            audit["ghost_risk"] = "high"
            if audit["status"] == "✓ Open":
                audit["status"] = "⚠ Unverified"
                audit["confidence"] = "medium"
                audit["reason"] = f"Apply button found but posted {age} days ago — possible ghost job"
        elif age > 60:
            audit["ghost_risk"] = "high"
        elif age > 30:
            audit["ghost_risk"] = "medium"
        else:
            audit["ghost_risk"] = "low"

    # Degree + visa
    audit["degree_match"] = _check_degree(page["text"], degree)
    audit["visa"] = _check_visa(page["text"])

    _apply_drop_rules(audit, degree, prefs)
    job["audit"] = audit
    return job


def _apply_drop_rules(audit: dict, degree: str, prefs: dict):
    """Apply drop rules for degree mismatch and visa."""
    if audit["degree_match"] == "mismatch" and not audit["drop"]:
        audit["drop"] = True
        audit["drop_reason"] = f"PhD required — candidate has {degree}"
    if prefs.get("visa_needed") and audit["visa"] == "no_sponsor" and not audit["drop"]:
        audit["drop"] = True
        audit["drop_reason"] = "No visa sponsorship available"


# ══════════════════════════════════════════════════════════
# Main: verify all jobs in parallel
# ══════════════════════════════════════════════════════════

def verify_all_jobs(jobs: list[dict], profile: dict, prefs: dict) -> list[dict]:
    """Verify all jobs in parallel. Returns kept list (dropped removed)."""
    verified = []

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(verify_one, job, profile, prefs): i for i, job in enumerate(jobs)}
        for future in as_completed(futures):
            try:
                result = future.result()
                verified.append(result)
            except Exception as e:
                idx = futures[future]
                job = jobs[idx]
                job["audit"] = {
                    "status": "⚠ Unverified", "confidence": "low",
                    "reason": f"Verification error: {str(e)[:80]}",
                    "drop": False, "needs_manual_check": True,
                    "degree_match": "unknown", "visa": "unspecified",
                    "posting_age_days": None, "ghost_risk": "unknown",
                }
                verified.append(job)

    kept = [j for j in verified if not j.get("audit", {}).get("drop")]
    dropped = [j for j in verified if j.get("audit", {}).get("drop")]

    # Sort: ✓ Open (high conf) → ✓ Open (medium) → ⚠ Unverified
    order = {"✓ Open": 0, "⚠ Unverified": 1, "✗ Closed": 2}
    conf_order = {"high": 0, "medium": 1, "low": 2}
    kept.sort(key=lambda j: (
        order.get(j.get("audit", {}).get("status", ""), 9),
        conf_order.get(j.get("audit", {}).get("confidence", ""), 9),
    ))

    o = sum(1 for j in verified if j.get("audit", {}).get("status") == "✓ Open")
    c = sum(1 for j in verified if j.get("audit", {}).get("status") == "✗ Closed")
    u = sum(1 for j in verified if j.get("audit", {}).get("status") == "⚠ Unverified")
    print(f"[verifier] {len(verified)} checked: {o} open, {c} closed, {u} unverified. Dropped {len(dropped)}.")

    return kept
