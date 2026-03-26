"""Phase 5 self-check: test cover letter generator."""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from generator import generate_cover_letter

# Cherish's profile (mock — same as what parser would return)
PROFILE = {
    "name": "Cherish (Xinlong) Chen",
    "email": "chrishchen2510@gmail.com",
    "degree_level": "Master",
    "strongest_metrics": [
        "50-100 GB/day", "15% conversion lift", "0.94 AUPRC",
        "Kaggle top 5% (11,962 entrants)", "12% prediction accuracy",
        "14% engagement increase", "8K+ comments scored", "100K+ interactions",
        "35% toxic content reduction", "3.86 GPA",
    ],
    "skills": ["Python", "SQL", "Machine Learning", "NLP", "XGBoost",
               "PyTorch", "Deep Learning", "A/B Testing", "Docker", "AWS",
               "Sentence-BERT", "Flask", "Supabase", "Tableau", "Power BI"],
    "work_history": [
        {
            "company": "Ele.me (Alibaba Group)",
            "title": "Data Mining Engineer Intern",
            "duration": "Jul 2024 – Sep 2024",
            "key_bullets": [
                "Engineered SQL-driven analytics pipeline processing 50-100 GB/day of pharmaceutical retail data",
                "Led 3 interns in data collection; lifted conversion by 15% via A/B-tested push strategy",
            ],
        },
        {
            "company": "Gate.io",
            "title": "Business Analyst Intern",
            "duration": "Jun 2023 – Sep 2023",
            "key_bullets": [
                "Built RF + RNN ensemble boosting news prediction by 12%",
                "Drove 14% UAE engagement via PCA + SVM on 50K+ users",
            ],
        },
        {
            "company": "Mercer Consulting",
            "title": "Summer Analyst",
            "duration": "Jul 2022 – Sep 2022",
            "key_bullets": [
                "Redesigned compensation framework for 200+ employees using Decision Trees + Neural Networks",
                "Delivered market intelligence on China self-driving car industry to C-suite",
            ],
        },
    ],
}

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


def _print_cl(result):
    print(f"\n    --- COVER LETTER ({result['word_count']} words, score {result['score']}/5) ---")
    print(f"    {result['text'][:500]}...")
    print(f"    --- END ---")
    print(f"    Gates: {result['gates']}")
    print(f"    Hollow found: {result['hollow_phrases_found']}")
    print(f"    Metrics used: {result['metrics_used']}")
    print(f"    Needs review: {result['needs_review']}")


# ── Test 1: DS job ─────────────────────────────────────────
def test_ds_job():
    job = {
        "title": "2026 Data Science Internship (MS/PhD)",
        "company": "Amazon",
        "description_snippet": "Amazon is looking for MS/PhD students with strong modeling skills. Build tools to analyze data and present findings. Experience with Python, R, SQL, large-scale data (100K+ rows). Machine learning, data mining experience required.",
        "key_requirements": ["MS/PhD in quantitative field", "Python/R/SQL", "ML experience", "Large-scale data"],
    }
    result = generate_cover_letter(job, PROFILE)
    _print_cl(result)

    assert result["score"] >= 4, f"Score {result['score']}/5 too low"
    assert result["gates"]["no_i_start"], "Starts with I"
    assert result["gates"]["has_metric_s1"], "No metric in first sentence"
    assert result["word_count"] <= 360, f"Too long: {result['word_count']} words"


# ── Test 2: Health informatics job ─────────────────────────
def test_health_job():
    job = {
        "title": "Data Science Intern - Summer 2026 (Remote)",
        "company": "IQVIA",
        "description_snippet": "IQVIA Data Science team works with pharmaceutical retail data to develop ML models. Support data-driven insights for retail pharmacies using machine learning and statistical analysis. Python or R required. Master's in Data Science, Statistics, or related field.",
        "key_requirements": ["MS in quantitative field", "Python or R", "ML/statistical modeling", "Healthcare data interest"],
    }
    result = generate_cover_letter(job, PROFILE)
    _print_cl(result)

    assert result["score"] >= 4, f"Score {result['score']}/5 too low"
    assert "iqvia" in result["text"].lower(), "IQVIA not mentioned"


# ── Test 3: Consulting/business job ────────────────────────
def test_biz_job():
    job = {
        "title": "Business Analyst Intern, Summer 2026",
        "company": "Deloitte",
        "description_snippet": "Join Deloitte's Internal Strategy team for an 8-10 week summer internship. Analyze business data, build presentations for senior leadership, support strategic initiatives. SQL, Excel, PowerBI required. Strong communication and stakeholder management skills.",
        "key_requirements": ["SQL/Excel/PowerBI", "Business analysis", "Stakeholder communication", "Presentation skills"],
    }
    result = generate_cover_letter(job, PROFILE)
    _print_cl(result)

    assert result["score"] >= 4, f"Score {result['score']}/5 too low"
    assert "deloitte" in result["text"].lower(), "Deloitte not mentioned"


# ── Run ────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("Phase 5 Self-Check: Cover Letter Generator Tests")
    print("=" * 60)

    print("\nTest 1: DS job (Amazon)")
    run_test("DS job CL", test_ds_job)

    print("\nTest 2: Health informatics job (IQVIA)")
    run_test("Health job CL", test_health_job)

    print("\nTest 3: Business/consulting job (Deloitte)")
    run_test("Biz job CL", test_biz_job)

    passed = sum(1 for r in RESULTS if r[0] == "PASS")
    total = len(RESULTS)
    print(f"\n{'=' * 60}")
    print(f"Results: {passed}/{total} passed")
    for r in RESULTS:
        icon = "✓" if r[0] == "PASS" else "✗"
        detail = f" — {r[2]}" if len(r) > 2 else ""
        print(f"  {icon} {r[1]}{detail}")
    print(f"{'=' * 60}")

    if passed < total:
        sys.exit(1)
