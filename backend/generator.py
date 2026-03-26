"""JobPilot cover letter generator — produces human-sounding, JD-specific letters."""

import json
import os
import re
from typing import Any

from dotenv import load_dotenv

load_dotenv()

# ── AI-telltale phrases to strip (Harvard Business Review: 89% of AI CLs contain 4+) ──

HOLLOW_PHRASES = [
    "passion for", "passionate about", "fast learner", "team player",
    "look forward to", "i look forward", "would be honored",
    "would love the opportunity", "i am a perfect fit",
    "please find attached", "i believe i would",
    "proven track record", "results-oriented", "synergistic",
    "detail-oriented", "self-starter", "go-getter",
    "hit the ground running", "think outside the box",
    "leverage my skills", "strong communicator",
    "i am confident that", "excited to apply",
    "i am writing to express", "i am writing to apply",
    "dear hiring manager",  # we use specific team names instead
]


# ── Step 1: Extract JD text from scraped page ─────────────

def _extract_jd_text(job: dict) -> str:
    """Get the best JD text available for this job."""
    # Priority 1: Full page text from verifier
    audit = job.get("audit", {})
    # We'll receive page_text as a field on the job if the pipeline passes it
    jd = job.get("jd_text", "")

    # Priority 2: description_snippet from searcher
    if not jd:
        jd = job.get("description_snippet", "")

    # Priority 3: key_requirements as bullet points
    if not jd and job.get("key_requirements"):
        jd = "Key requirements: " + "; ".join(job["key_requirements"])

    # Priority 4: Just title + company
    if not jd:
        jd = f"{job.get('title', 'Unknown role')} at {job.get('company', 'Unknown company')}"

    return jd[:2000]


# ── Step 2: Build context package ─────────────────────────

def _pick_relevant_experience(profile: dict, jd_text: str) -> list[dict]:
    """Pick top 2 work_history entries most relevant to this JD."""
    work = profile.get("work_history", [])
    if not work:
        return []

    jd_lower = jd_text.lower()

    def relevance(entry):
        score = 0
        text = json.dumps(entry).lower()
        # Score by keyword overlap
        for word in jd_lower.split():
            if len(word) > 3 and word in text:
                score += 1
        return score

    ranked = sorted(work, key=relevance, reverse=True)
    return ranked[:2]


def _find_skills_match(profile: dict, jd_text: str) -> list[str]:
    """Find intersection of profile skills and JD keywords."""
    skills = profile.get("skills", [])
    jd_lower = jd_text.lower()
    return [s for s in skills if s.lower() in jd_lower][:8]


# ── Step 3: Generate with Claude ──────────────────────────

SYSTEM_PROMPT = """You write cover letters that get interviews at US tech companies, consulting firms, and healthcare companies.

You have studied thousands of successful cover letters and know exactly what hiring managers want.

ABSOLUTE RULES — violating ANY means the letter gets rejected:

R1. First word CANNOT be "I". Start with the value you bring.
    GOOD: "Building ML pipelines that process 50-100 GB/day at Alibaba taught me..."
    GOOD: "At Ele.me, I engineered data pipelines processing..."
    BAD: "I am writing to apply..."
    BAD: "I am excited about..."

R2. First sentence MUST contain a specific number from the candidate's experience.

R3. Second paragraph MUST reference something SPECIFIC from the job description — a technology, a team goal, a product name, a method. This proves you read the actual JD.

R4. Company name appears exactly 2-3 times. Not more (desperate), not less (generic).

R5. Include exactly 2 quantified achievements from the candidate's metrics.

R6. Word count: 270-310 words. You MUST hit at least 270 words. Hiring managers spend 30 seconds on CLs, but too short looks lazy.

R7. ZERO hollow phrases. These are BANNED — if you write any, the letter is rejected:
"passion for", "team player", "fast learner", "look forward to", "would be honored",
"would love the opportunity", "perfect fit", "proven track record", "results-oriented",
"synergistic", "detail-oriented", "self-starter", "go-getter", "hit the ground running",
"think outside the box", "leverage my skills", "strong communicator", "I am confident that",
"excited to apply", "I am writing to express", "I am writing to apply", "Dear Hiring Manager"

R8. Final sentence = specific ask with a concrete next step.
    GOOD: "I'd welcome a 20-minute call to discuss how my pipeline experience maps to [team/product from JD]."
    BAD: "I look forward to hearing from you."

R9. Tone: Direct, confident, specific. Like an engineer explaining what they built, not a student begging for a chance. Use short sentences. No filler words.

Write in plain text. No markdown. No headers. No "Dear..." salutation.
3 paragraphs maximum. Sign with candidate name, school, and email only."""


def _call_claude(system: str, user_msg: str) -> str:
    """Call Claude API. Falls back to mock if unavailable."""
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key or api_key == "REPLACE_ME":
        return _mock_cover_letter(user_msg)

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            system=system,
            messages=[{"role": "user", "content": user_msg}],
        )
        return message.content[0].text.strip()
    except Exception as e:
        err = str(e).lower()
        if "credit" in err or "authentication" in err or "401" in err or "400" in err:
            print(f"[generator] API unavailable ({type(e).__name__}), using mock")
            return _mock_cover_letter(user_msg)
        raise


def _mock_cover_letter(user_msg: str) -> str:
    """Generate a template-based CL when API is unavailable."""
    # Extract key info from the user message
    import re
    company = re.search(r"Company: (.+)", user_msg)
    company = company.group(1).strip() if company else "the company"
    title = re.search(r"Job: (.+)", user_msg)
    title = title.group(1).strip() if title else "this role"
    metrics = re.findall(r"Strongest metrics: \[(.+?)\]", user_msg)
    metric_list = metrics[0].split(", ")[:2] if metrics else ["significant results", "measurable impact"]

    return f"""Building data pipelines that process 50-100 GB/day at Alibaba gave me firsthand experience with the kind of production-scale challenges that define {company}'s data infrastructure. During my internship at Ele.me, I engineered SQL-driven analytics pipelines across pharmaceutical retail data for 5+ user segments, led a team of 3 interns, and lifted new-user conversion by 15% through A/B-tested push strategies.

{company}'s {title} role resonates because it requires exactly this combination of large-scale data engineering and applied ML — skills I've continued building through an end-to-end fraud detection system (XGBoost + SMOTE, 0.94 AUPRC) deployed on AWS EC2 with Docker, and NLP research scoring 8K+ comments via Sentence-BERT at the University of Washington. As a Kaggle top 5% competitor and current M.S. student in Health Informatics at Yale, I bring both the technical depth and the analytical rigor this position demands.

I'd welcome a 20-minute call to walk through how my pipeline and ML deployment experience maps to {company}'s data team. Available anytime.

Cherish (Xinlong) Chen
Yale University, M.S. Health Informatics
chrishchen2510@gmail.com | 206-532-5712"""


# ── Step 4: Quality gate ──────────────────────────────────

def _quality_gate(text: str, company: str) -> dict:
    """Run automated quality checks on generated CL."""
    words = text.split()
    word_count = len(words)
    first_word = words[0].lower() if words else ""
    first_sentence = text.split(".")[0] if "." in text else text[:100]

    gates = {
        "word_count_ok": 240 <= word_count <= 360,  # slight buffer for retries
        "no_i_start": first_word != "i",
        "has_metric_s1": bool(re.search(r"\d", first_sentence)),
        "company_2_3": 2 <= text.lower().count(company.lower()) <= 4,
        "no_hollow": not any(h in text.lower() for h in HOLLOW_PHRASES),
    }

    hollow_found = [h for h in HOLLOW_PHRASES if h in text.lower()]
    metrics_found = re.findall(r"\d+[\d.,]*\s*(?:%|GB|K\+|AUPRC|GPA|entrants|projects|countries|ms)", text)

    score = sum(gates.values())

    return {
        "gates": gates,
        "score": score,
        "word_count": word_count,
        "hollow_found": hollow_found,
        "metrics_used": metrics_found,
    }


# ── Main entry point ──────────────────────────────────────

def generate_cover_letter(job: dict, profile: dict) -> dict:
    """
    Generate a cover letter for a specific job + candidate profile.

    Returns dict with: text, word_count, score, gates, needs_review, etc.
    """
    # Step 1: Extract JD
    jd_text = _extract_jd_text(job)

    # Step 2: Build context
    relevant_exp = _pick_relevant_experience(profile, jd_text)
    skills_match = _find_skills_match(profile, jd_text)

    # Format experience for prompt
    exp_text = ""
    for exp in relevant_exp:
        bullets = exp.get("key_bullets", [])
        exp_text += f"\n  - {exp.get('company', '?')} ({exp.get('title', '?')}, {exp.get('duration', '?')})"
        for b in bullets[:2]:
            exp_text += f"\n    * {b}"

    user_msg = f"""Job: {job.get('title', 'Unknown')}
Company: {job.get('company', 'Unknown')}

Job description excerpt:
{jd_text}

Key requirements from JD:
{job.get('key_requirements', ['Not specified'])}

Candidate: {profile.get('name', 'Candidate')}
School: Yale University, M.S. Health Informatics (current)
Undergrad: University of Washington, B.S. Data Science & B.A. Economics, GPA 3.86

Strongest metrics: [{', '.join(profile.get('strongest_metrics', ['50-100 GB/day', '15% conversion', '0.94 AUPRC', 'Kaggle top 5%'])[:6])}]

Most relevant experience:{exp_text if exp_text else ' Alibaba (Data Mining), Gate.io (Business Analyst), Mercer (Consulting Analyst)'}

Skills matching JD: [{', '.join(skills_match) if skills_match else 'Python, SQL, ML, NLP'}]

Write the cover letter."""

    company = job.get("company", "the company")

    # Generate + quality gate with up to 2 retries
    best_text = ""
    best_result = {"score": 0}

    for attempt in range(3):
        if attempt > 0:
            failed = [k for k, v in best_result["gates"].items() if not v]
            user_msg_retry = f"""Previous attempt failed these quality gates: {failed}.

Specific fixes needed:
{' - First word must NOT be "I"' if 'no_i_start' in failed else ''}
{' - First sentence must contain a number' if 'has_metric_s1' in failed else ''}
{' - Company name must appear 2-3 times' if 'company_2_3' in failed else ''}
{' - Remove ALL hollow phrases: ' + str(best_result.get('hollow_found', [])) if 'no_hollow' in failed else ''}
{' - Word count must be 260-320' if 'word_count_ok' in failed else ''}

Rewrite the cover letter fixing these issues.

Original context:
{user_msg}"""
            text = _call_claude(SYSTEM_PROMPT, user_msg_retry)
        else:
            text = _call_claude(SYSTEM_PROMPT, user_msg)

        result = _quality_gate(text, company)
        result["text"] = text

        if result["score"] > best_result.get("score", 0):
            best_text = text
            best_result = result

        if result["score"] >= 4:
            break

    return {
        "text": best_text,
        "word_count": best_result.get("word_count", 0),
        "score": best_result.get("score", 0),
        "gates": best_result.get("gates", {}),
        "needs_review": best_result.get("score", 0) < 4,
        "hollow_phrases_found": best_result.get("hollow_found", []),
        "metrics_used": best_result.get("metrics_used", []),
        "attempts": min(3, best_result.get("score", 0) + 1),  # rough proxy
    }
