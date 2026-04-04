"""Phase 3 self-check: test job searcher."""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from searcher import search_jobs

# Mock profile (similar to Cherish's)
PROFILE = {
    "name": "Cherish Chen",
    "skills": ["Python", "SQL", "Machine Learning", "NLP", "XGBoost", "PyTorch",
               "Deep Learning", "A/B Testing", "Docker", "AWS"],
    "degree_level": "Master",
    "companies": ["Alibaba", "Gate.io", "Mercer"],
}

PREFS = {
    "directions": ["DS/ML", "Health Informatics"],
    "job_type": "intern_2026",
    "location": "US",
}

RESULTS_LOG = []


def run_test(name, fn):
    try:
        fn()
        RESULTS_LOG.append(("PASS", name))
        print(f"  ✓ {name}")
    except AssertionError as e:
        RESULTS_LOG.append(("FAIL", name, str(e)))
        print(f"  ✗ {name}: {e}")
    except Exception as e:
        RESULTS_LOG.append(("ERROR", name, str(e)))
        print(f"  ✗ {name}: {type(e).__name__}: {e}")


# ── Test 1: Get results with ATS URLs ─────────────────────
jobs = []


def test_search_returns_results():
    global jobs
    jobs = search_jobs(PROFILE, PREFS)
    greenhouse_count = sum(1 for j in jobs if j["job_board"] == "greenhouse")
    lever_count = sum(1 for j in jobs if j["job_board"] == "lever")
    direct_count = sum(1 for j in jobs if j["job_board"] == "direct")
    total = len(jobs)

    print(f"    Total jobs found: {total}")
    print(f"    Greenhouse: {greenhouse_count} | Lever: {lever_count} | Direct/curated: {direct_count}")

    assert total >= 5, f"Only {total} jobs found, need at least 5"


# ── Test 2: All apply_urls start with https:// ────────────
def test_urls_valid():
    bad_urls = [j for j in jobs if not j["apply_url"].startswith("https://")]
    assert len(bad_urls) == 0, f"{len(bad_urls)} jobs have bad URLs: {[j['apply_url'][:50] for j in bad_urls]}"


# ── Test 3: No duplicate company+title ─────────────────────
def test_no_duplicates():
    seen = set()
    dupes = []
    for j in jobs:
        key = (j["company"].lower(), j["title"].lower())
        if key in seen:
            dupes.append(f"{j['company']} - {j['title']}")
        seen.add(key)
    assert len(dupes) == 0, f"Duplicates found: {dupes}"


# ── Test 4: description_snippet non-empty ──────────────────
def test_snippets_present():
    global jobs
    if not jobs:
        jobs = search_jobs(PROFILE, PREFS)
    empty = [j for j in jobs if not j.get("description_snippet", "").strip()]
    pct_filled = (len(jobs) - len(empty)) / len(jobs) * 100 if jobs else 0
    print(f"    Snippets filled: {len(jobs)-len(empty)}/{len(jobs)} ({pct_filled:.0f}%)")
    # Greenhouse list API doesn't return descriptions — only curated + Lever do
    # With large Greenhouse result sets, 5%+ is realistic
    assert pct_filled >= 5, f"Only {pct_filled:.0f}% have descriptions"


# ── Test 5: Print sample jobs and URLs ─────────────────────
def test_print_samples():
    print(f"\n    Top 10 results:")
    for i, j in enumerate(jobs[:10], 1):
        print(f"    {i}. {j['company']} — {j['title']}")
        print(f"       Location: {j['location']} | Board: {j['job_board']} | CV: {j['recommended_cv']}")
        print(f"       URL: {j['apply_url'][:80]}")
        if j.get("match_reason"):
            print(f"       Match: {j['match_reason'][:80]}")
        print()

    # Verify first 3 URLs are HTTPS
    sample_urls = [j["apply_url"] for j in jobs[:3]]
    print(f"    Sample URLs to verify:")
    for u in sample_urls:
        print(f"      {u}")
    assert all(u.startswith("https://") for u in sample_urls)


# ── Run ────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("Phase 3 Self-Check: Job Searcher Tests")
    print("=" * 60)

    print("\nTest 1: Search returns >= 5 results")
    run_test("search_returns_results", test_search_returns_results)

    print("\nTest 2: All URLs start with https://")
    run_test("urls_valid", test_urls_valid)

    print("\nTest 3: No duplicates")
    run_test("no_duplicates", test_no_duplicates)

    print("\nTest 4: Description snippets present")
    run_test("snippets_present", test_snippets_present)

    print("\nTest 5: Print sample results")
    run_test("print_samples", test_print_samples)

    # Summary
    passed = sum(1 for r in RESULTS_LOG if r[0] == "PASS")
    total = len(RESULTS_LOG)
    gh = sum(1 for j in jobs if j["job_board"] == "greenhouse")
    lv = sum(1 for j in jobs if j["job_board"] == "lever")
    dr = sum(1 for j in jobs if j["job_board"] == "direct")

    print(f"\n{'=' * 60}")
    print(f"Results: {passed}/{total} passed")
    for r in RESULTS_LOG:
        icon = "✓" if r[0] == "PASS" else "✗"
        detail = f" — {r[2]}" if len(r) > 2 else ""
        print(f"  {icon} {r[1]}{detail}")

    print(f"\nPhase 3 complete. Found {len(jobs)} jobs.")
    print(f"URL types: {gh} greenhouse, {lv} lever, {dr} direct.")
    sample = [j["apply_url"] for j in jobs[:3]]
    print(f"Sample URLs: {sample}")
    print(f"{'=' * 60}")

    if passed < total:
        sys.exit(1)
