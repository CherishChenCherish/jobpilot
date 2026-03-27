"""JobPilot Core Promise — the final gate.

Every job shown to a user must satisfy ALL FOUR conditions:
1. OPEN — currently accepting applications
2. LOCATION MATCH — job is in the user's selected region
3. DIRECTION MATCH — job matches the user's selected field
4. IDENTITY MATCH — appropriate for user's degree and visa status

This function is the absolute last step before any job reaches any user.
Nothing bypasses it. Ever.

Zero results with a clear message is always better than one wrong result.
"""

import re

# ── Blocked titles: always rejected, no exceptions ──────────

SENIOR_PATTERNS = re.compile(
    r'\b(?:senior|lead|principal|director|manager|staff|partner|postdoc|post-doc)\b'
    r'|'
    r'\bvp\b',
    re.IGNORECASE,
)

# ── Direction → title keywords (must match at least one) ────

DIRECTION_KEYWORDS = {
    "DS/ML": ["data scien", "machine learn", "ml ", "ai ", "analytics", "algorithm", "nlp", "deep learn"],
    "Data Engineering": ["data engineer", "etl", "pipeline", "data infra"],
    "Software Engineering": ["software engineer", "software develop", "backend", "frontend", "full stack", "swe"],
    "Health Informatics": ["health", "clinical", "biomedical", "pharma", "bioinform"],
    "Business Analytics": ["business analyst", "strategy", "business intelligence", "analytics"],
    "Product Management": ["product manager", "product analyst", "program manager"],
    "Quantitative Finance": ["quant", "trading", "financial analyst"],
    "Research / NLP": ["research", "nlp", "natural language"],
    "Consulting": ["consult", "advisory"],
}


def passes_core_promise(job: dict, user_prefs: dict) -> tuple[bool, str]:
    """Check all four Core Promise conditions.

    Args:
        job: a job dict (from CachedJob.to_dict() or _serialize_job())
        user_prefs: dict with keys: regions, directions, visa_needed, degree_level

    Returns:
        (True, "") if the job passes all four conditions.
        (False, reason) if any condition is violated.
    """

    title = (job.get("title") or "").lower()
    company = job.get("company") or ""

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # CONDITION 1: OPEN
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    audit = job.get("audit", {})
    status = audit.get("status", "")

    # From cache: status field on the dict directly
    job_status = job.get("status") if "status" in job else None

    # Accept: "✓ Open" in audit, or status="open" from cache
    is_open = (
        status.startswith("✓")
        or status.startswith("\u2713")
        or job_status == "open"
    )
    if not is_open:
        return False, f"not_open: status={status or job_status} ({company})"

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # CONDITION 4: IDENTITY MATCH (checked before direction
    # because senior roles should fail fast)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    # 4a: Senior roles — always blocked, no exceptions
    if SENIOR_PATTERNS.search(title):
        return False, f"senior_role: '{job.get('title')}' ({company})"

    # 4b: PhD — search-time filter based on user's degree
    degree_required = (job.get("degree_required") or "").lower()
    user_degree = (user_prefs.get("degree_level") or "").lower()

    if "phd" in degree_required or "doctoral" in degree_required:
        if user_degree not in ("phd", "doctoral", "doctorate"):
            return False, f"phd_required: user_degree={user_degree} ({company})"

    # Also check title for PhD signals
    phd_title = bool(re.search(r'\bphd\b|\bph\.d\b|\bdoctoral\b', title))
    if phd_title and user_degree not in ("phd", "doctoral", "doctorate"):
        return False, f"phd_in_title: '{job.get('title')}' user_degree={user_degree} ({company})"

    # 4c: Visa — if user needs sponsorship, unknown is not yes
    visa_needed = user_prefs.get("visa_needed", False)
    visa_status = (job.get("visa_sponsorship") or "").lower()
    # Also check audit.visa for live-search jobs
    if not visa_status:
        visa_status = (audit.get("visa") or "").lower()

    if visa_needed:
        # Only pass if visa is explicitly confirmed
        if visa_status not in ("confirmed", "visa sponsorship", "yes", "available"):
            # "unspecified" and "no_sponsor" both fail
            return False, f"visa_not_confirmed: visa={visa_status} ({company})"

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # CONDITION 2: LOCATION MATCH
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    selected_regions = user_prefs.get("regions", [])
    if selected_regions:
        job_region = (job.get("region") or "").upper()
        job_remote = job.get("remote", False)

        if not job_remote and job_region not in selected_regions:
            return False, f"region_mismatch: job={job_region} user={selected_regions} ({company})"

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # CONDITION 3: DIRECTION MATCH
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    selected_directions = user_prefs.get("directions", [])
    if selected_directions:
        # Check 1: category overlap
        categories = job.get("categories") or []
        category_match = any(d in categories for d in selected_directions)

        # Check 2: title keyword match
        title_match = False
        for d in selected_directions:
            kws = DIRECTION_KEYWORDS.get(d, [])
            if any(k in title for k in kws):
                title_match = True
                break

        # Fallback: generic intern title with tech signal + category match
        if not title_match and "intern" in title and category_match:
            tech_signals = ["data", "engineer", "scien", "analyst", "research", "ml", "ai"]
            if any(s in title for s in tech_signals):
                title_match = True

        if not (category_match or title_match):
            return False, f"direction_mismatch: dirs={selected_directions} title='{job.get('title')}' cats={categories} ({company})"

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # ALL FOUR CONDITIONS PASSED
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    return True, ""


def filter_by_promise(jobs: list[dict], user_prefs: dict) -> tuple[list[dict], list[dict]]:
    """Apply the Core Promise gate to a list of jobs.

    Returns:
        (passed, rejected) — two lists. rejected contains dicts with
        the job and the rejection reason for logging.
    """
    passed = []
    rejected = []

    for job in jobs:
        ok, reason = passes_core_promise(job, user_prefs)
        if ok:
            passed.append(job)
        else:
            rejected.append({"job": job, "reason": reason})
            print(f"[promise] REJECTED: {reason}")

    if rejected:
        print(f"[promise] {len(passed)} passed, {len(rejected)} rejected")

    return passed, rejected
