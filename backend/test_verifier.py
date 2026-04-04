"""Phase 4 self-check: test job verifier on 5 real URLs."""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from verifier import verify_one

PROFILE = {
    "degree_level": "Master",
    "skills": ["Python", "SQL", "Machine Learning"],
}
PREFS = {"visa_needed": True}

RESULTS = []


def run_test(name, fn):
    try:
        fn()
        RESULTS.append(("PASS", name))
        print(f"  ✓ {name}")
    except AssertionError as e:
        RESULTS.append(("FAIL", name, str(e)))
        print(f"  ✗ {name}: {e}")
    except Exception as e:
        RESULTS.append(("ERROR", name, str(e)))
        print(f"  ✗ {name}: {type(e).__name__}: {e}")


def _print_audit(job):
    a = job.get("audit", {})
    print(f"    Status: {a.get('status')}")
    print(f"    Confidence: {a.get('confidence')}")
    print(f"    Reason: {a.get('reason')}")
    print(f"    HTTP: {a.get('http_status')}")
    print(f"    Degree: {a.get('degree_match')} | Visa: {a.get('visa')}")
    print(f"    Age: {a.get('posting_age_days')} days | Drop: {a.get('drop')} ({a.get('drop_reason')})")
    print(f"    Manual check: {a.get('needs_manual_check')}")


# ── URL 1: Greenhouse job verification (mocked API) ─────────
def test_greenhouse_open():
    from unittest.mock import patch, Mock
    job = {
        "title": "AI Research Scientist Intern (Summer 2026)",
        "company": "Flagship Pioneering",
        "apply_url": "https://boards.greenhouse.io/flagshippioneeringinc/jobs/8373309002",
        "job_board": "greenhouse",
    }
    mock_resp = Mock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"title": "AI Research Scientist Intern (Summer 2026)"}
    mock_resp.text = '{"title": "AI Research Scientist Intern (Summer 2026)"}'
    mock_resp.headers = {"Content-Type": "application/json"}

    with patch("verifier.requests.get", return_value=mock_resp):
        result = verify_one(job, PROFILE, PREFS)
    _print_audit(result)
    a = result["audit"]
    assert a["status"] == "✓ Open", f"Expected Open, got {a['status']}"
    assert a["confidence"] == "high"
    assert a["reason"]  # non-empty


# ── URL 2: Known-open Lever job (Match Group) ──────────────
def test_lever_open():
    job = {
        "title": "Data Scientist Intern",
        "company": "Match Group",
        "apply_url": "https://jobs.lever.co/matchgroup/596091e0-9d8e-4a3a-92a6-5699386b833e",
        "job_board": "lever",
    }
    result = verify_one(job, PROFILE, PREFS)
    _print_audit(result)
    a = result["audit"]
    assert a["status"] == "✓ Open", f"Expected Open, got {a['status']}"
    assert a["reason"]


# ── URL 3: Known-open direct job (Amazon) ──────────────────
def test_direct_open():
    job = {
        "title": "2026 Data Science Internship (MS/PhD)",
        "company": "Amazon",
        "apply_url": "https://www.amazon.jobs/en/jobs/3144155/2026-data-science-internship-united-states-phd-or-masters-student",
        "job_board": "direct",
    }
    result = verify_one(job, PROFILE, PREFS)
    _print_audit(result)
    a = result["audit"]
    # Amazon may show open or unverified (their pages are JS-heavy)
    assert a["status"] in ("✓ Open", "⚠ Unverified"), f"Unexpected: {a['status']}"
    assert a["reason"]


# ── URL 4: Expired/removed Greenhouse job (fake ID) ────────
def test_closed_job():
    job = {
        "title": "Fake Old Job",
        "company": "Test",
        "apply_url": "https://boards.greenhouse.io/testcompany/jobs/9999999999",
        "job_board": "greenhouse",
    }
    result = verify_one(job, PROFILE, PREFS)
    _print_audit(result)
    a = result["audit"]
    assert a["status"] == "✗ Closed", f"Expected Closed, got {a['status']}"
    assert a["drop"] == True


# ── URL 5: LinkedIn job URL → should not crash ─────────────
def test_linkedin_url():
    job = {
        "title": "Data Scientist",
        "company": "Some Company",
        "apply_url": "https://www.linkedin.com/jobs/view/3800000000",
        "job_board": "linkedin",
    }
    result = verify_one(job, PROFILE, PREFS)
    _print_audit(result)
    a = result["audit"]
    # Should not crash, any status is fine
    assert a["status"] in ("✓ Open", "⚠ Unverified", "✗ Closed")
    assert a["reason"]  # non-empty
    assert a["needs_manual_check"] == True  # LinkedIn URLs always flagged


# ── Run all ────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("Phase 4 Self-Check: Job Verifier Tests")
    print("=" * 60)

    tests = [
        ("URL 1: Greenhouse Open (Flagship)", test_greenhouse_open),
        ("URL 2: Lever Open (Match Group)", test_lever_open),
        ("URL 3: Direct Open (Amazon)", test_direct_open),
        ("URL 4: Closed (fake Greenhouse ID)", test_closed_job),
        ("URL 5: LinkedIn URL (no crash)", test_linkedin_url),
    ]

    for name, fn in tests:
        print(f"\n{name}:")
        run_test(name, fn)

    passed = sum(1 for r in RESULTS if r[0] == "PASS")
    total = len(RESULTS)
    print(f"\n{'=' * 60}")
    print(f"Results: {passed}/{total} passed")
    for r in RESULTS:
        icon = "✓" if r[0] == "PASS" else "✗"
        detail = f" — {r[2]}" if len(r) > 2 else ""
        print(f"  {icon} {r[1]}{detail}")
    print(f"\nPhase 4 complete. Accuracy: {passed}/{total} correct.")
    print(f"{'=' * 60}")

    if passed < total:
        sys.exit(1)
