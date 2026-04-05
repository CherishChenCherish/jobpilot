"""Phase 2 self-check: test resume parser on real files."""

import os
import sys
from pathlib import Path

# Ensure we can import from backend
sys.path.insert(0, os.path.dirname(__file__))

from parser import parse_resume, ParseError, extract_text

CV_DIR = Path.home() / "Desktop" / "2026 no job no fuck" / "untitled folder" / " new cv"
PDF_PATH = CV_DIR / "CherishChen_CV_DataScience.docx"  # We'll test DOCX first
DOCX_V1 = CV_DIR / "CherishChen_CV_DataScience.docx"
DOCX_V3 = CV_DIR / "CherishChen_CV_HealthInformatics.docx"

# Also test with original PDF if available
ORIG_PDF = Path.home() / "Desktop" / "Resume Xinlong Chen.pdf"

RESULTS = []


def run_test(name: str, fn):
    """Run a test and record pass/fail."""
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


# ── Test 1: Parse DOCX (V1 DataScience) ───────────────────
def test_parse_docx_v1():
    """Parse a real DOCX resume → check all fields present."""
    assert DOCX_V1.exists(), f"File not found: {DOCX_V1}"
    file_bytes = DOCX_V1.read_bytes()
    profile = parse_resume(file_bytes, "CherishChen_CV_DataScience.docx")

    # Core fields must exist and be non-empty
    assert profile.get("name"), f"name is empty: {profile.get('name')}"
    assert profile.get("email"), f"email is empty"
    assert profile.get("degree_level") in ("Bachelor", "Master", "PhD", "Other"), \
        f"bad degree_level: {profile.get('degree_level')}"
    assert len(profile.get("universities", [])) >= 1, "no universities"
    assert len(profile.get("skills", [])) >= 5, f"only {len(profile.get('skills', []))} skills"
    assert len(profile.get("companies", [])) >= 2, f"only {len(profile.get('companies', []))} companies"
    assert len(profile.get("work_history", [])) >= 2, f"only {len(profile.get('work_history', []))} work entries"

    print(f"    Name: {profile['name']}")
    print(f"    Degree: {profile['degree_level']} in {profile.get('degree_fields', [])}")
    print(f"    Universities: {profile.get('universities', [])}")
    print(f"    Skills ({len(profile['skills'])}): {profile['skills'][:10]}...")
    print(f"    Companies: {profile.get('companies', [])}")
    print(f"    Work history: {len(profile['work_history'])} entries")
    print(f"    Metrics: {profile.get('strongest_metrics', [])}")


# ── Test 2: Parse DOCX (V3 HealthInformatics) ─────────────
def test_parse_docx_v3():
    """Parse a different DOCX resume → same checks."""
    assert DOCX_V3.exists(), f"File not found: {DOCX_V3}"
    file_bytes = DOCX_V3.read_bytes()
    profile = parse_resume(file_bytes, "CherishChen_CV_HealthInformatics.docx")

    assert profile.get("name"), "name is empty"
    assert len(profile.get("skills", [])) >= 5, f"only {len(profile.get('skills', []))} skills"
    assert len(profile.get("work_history", [])) >= 2, f"only {len(profile.get('work_history', []))} work entries"

    print(f"    Name: {profile['name']}")
    print(f"    Skills ({len(profile['skills'])}): {profile['skills'][:8]}...")
    print(f"    Metrics: {profile.get('strongest_metrics', [])}")


# ── Test 3: Bad file type → clean error ────────────────────
def test_bad_file_type():
    """Bad file (.txt) → returns clean error."""
    try:
        parse_resume(b"This is plain text", "resume.txt")
        assert False, "Should have raised ParseError"
    except ParseError as e:
        assert "Unsupported file type" in str(e), f"Wrong error: {e}"
        print(f"    Got expected error: {e}")


# ── Test 4: strongest_metrics >= 2 ────────────────────────
def test_metrics_count():
    """strongest_metrics has at least 2 numbers."""
    file_bytes = DOCX_V1.read_bytes()
    profile = parse_resume(file_bytes, "test.docx")

    metrics = profile.get("strongest_metrics", [])
    assert len(metrics) >= 2, f"Only {len(metrics)} metrics: {metrics}"
    print(f"    Found {len(metrics)} metrics: {metrics}")


# ── Test 5: work_history has key_bullets populated ─────────
def test_key_bullets():
    """work_history entries have key_bullets populated."""
    file_bytes = DOCX_V1.read_bytes()
    profile = parse_resume(file_bytes, "test.docx")

    wh = profile.get("work_history", [])
    assert len(wh) >= 1, "No work history"

    for entry in wh:
        bullets = entry.get("key_bullets", [])
        assert len(bullets) >= 1, f"{entry.get('company', '?')} has no key_bullets"

    total_bullets = sum(len(e.get("key_bullets", [])) for e in wh)
    print(f"    {len(wh)} work entries with {total_bullets} total bullets")
    for e in wh:
        print(f"      {e['company']} ({e.get('title', '?')}): {len(e.get('key_bullets', []))} bullets")


# ── Test 6 (bonus): Parse real PDF if available ────────────
def test_parse_pdf():
    """Parse a real PDF resume if available."""
    if not ORIG_PDF.exists():
        print(f"    SKIP: {ORIG_PDF} not found")
        return

    file_bytes = ORIG_PDF.read_bytes()
    profile = parse_resume(file_bytes, "Resume Xinlong Chen.pdf")

    assert profile.get("name"), "name is empty"
    print(f"    Name: {profile['name']}")
    print(f"    Skills: {profile.get('skills', [])[:8]}...")
    print(f"    Metrics: {profile.get('strongest_metrics', [])}")


# ── Run all tests ──────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 55)
    print("Phase 2 Self-Check: Resume Parser Tests")
    print("=" * 55)

    print("\nTest 1: Parse DOCX (V1 DataScience)")
    run_test("parse_docx_v1", test_parse_docx_v1)

    print("\nTest 2: Parse DOCX (V3 HealthInformatics)")
    run_test("parse_docx_v3", test_parse_docx_v3)

    print("\nTest 3: Bad file type → error")
    run_test("bad_file_type", test_bad_file_type)

    print("\nTest 4: strongest_metrics >= 2")
    run_test("metrics_count", test_metrics_count)

    print("\nTest 5: work_history has key_bullets")
    run_test("key_bullets", test_key_bullets)

    if ORIG_PDF.exists():
        print("\nTest 6 (bonus): Parse real PDF")
        run_test("parse_pdf", test_parse_pdf)

    # Summary
    passed = sum(1 for r in RESULTS if r[0] == "PASS")
    total = len(RESULTS)
    print(f"\n{'=' * 55}")
    print(f"Results: {passed}/{total} passed")
    for r in RESULTS:
        icon = "✓" if r[0] == "PASS" else "✗"
        detail = f" — {r[2]}" if len(r) > 2 else ""
        print(f"  {icon} {r[1]}{detail}")
    print(f"{'=' * 55}")

    if passed < total:
        sys.exit(1)
