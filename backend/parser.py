"""JobPilot resume parser — extract structured profile from PDF or DOCX."""

import io
import json
import os
import re
from typing import Any

import anthropic
import fitz  # PyMuPDF
from docx import Document as DocxDocument
from dotenv import load_dotenv

load_dotenv()


class ParseError(Exception):
    """Raised when resume parsing fails."""
    pass


# ── Step 1: Raw text extraction ────────────────────────────

def _extract_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF preserving layout order via PyMuPDF."""
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as e:
        raise ParseError(f"Cannot open PDF: {e}")

    pages = []
    for page in doc:
        # sort=True preserves natural reading order (top-to-bottom, left-to-right)
        text = page.get_text("text", sort=True)
        if text.strip():
            pages.append(text)
    doc.close()

    if not pages:
        raise ParseError("PDF contains no extractable text (may be scanned/image-based)")
    return "\n\n".join(pages)


def _extract_docx(file_bytes: bytes) -> str:
    """Extract text from DOCX including paragraphs and tables."""
    try:
        doc = DocxDocument(io.BytesIO(file_bytes))
    except Exception as e:
        raise ParseError(f"Cannot open DOCX: {e}")

    parts = []

    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            parts.append(text)

    # Also extract table content (some resumes use tables for layout)
    for table in doc.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if cells:
                parts.append(" | ".join(cells))

    if not parts:
        raise ParseError("DOCX contains no extractable text")
    return "\n".join(parts)


def _clean_text(raw: str) -> str:
    """Clean extracted text: fix whitespace, encoding artifacts."""
    # Collapse multiple blank lines
    text = re.sub(r"\n{3,}", "\n\n", raw)
    # Collapse multiple spaces (but keep single newlines)
    text = re.sub(r"[ \t]{2,}", " ", text)
    # Remove common PDF artifacts
    text = text.replace("\x00", "").replace("\ufffd", "")
    return text.strip()


def extract_text(file_bytes: bytes, filename: str) -> str:
    """Route to correct extractor based on file extension."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext == "pdf":
        raw = _extract_pdf(file_bytes)
    elif ext in ("docx", "doc"):
        raw = _extract_docx(file_bytes)
    else:
        raise ParseError(f"Unsupported file type: .{ext} (only PDF and DOCX accepted)")

    return _clean_text(raw)


# ── Step 2: Structure with Claude ──────────────────────────

SYSTEM_PROMPT = """You are a resume parser. Extract structured data from the resume text below.

Return ONLY valid JSON — no markdown fences, no prose, no explanation.

The JSON must have exactly these fields:
{
  "name": "string or null",
  "email": "string or null",
  "phone": "string or null",
  "degree_level": "Bachelor" | "Master" | "PhD" | "Other",
  "degree_fields": ["list of degree field names"],
  "universities": ["list of university names"],
  "graduation_year": integer or null,
  "gpa": float or null,
  "years_experience": float (estimate from work history dates),
  "skills": ["ALL technical keywords, tools, languages, frameworks mentioned"],
  "companies": ["list of all company names worked at"],
  "industries": ["list of industries: e.g. fintech, e-commerce, healthcare, consulting"],
  "languages_spoken": ["e.g. English, Mandarin Chinese"],
  "notable_achievements": ["awards, rankings, certifications — one string each"],
  "work_history": [
    {
      "company": "string",
      "title": "string",
      "duration": "string (e.g. Jul 2024 – Sep 2024)",
      "key_bullets": ["top 3 most impactful bullet points from this role"]
    }
  ],
  "strongest_metrics": ["every quantified number/percentage from the resume, e.g. '3.86 GPA', 'top 5% Kaggle', '50-100GB/day', '15% conversion lift'"]
}

Rules:
- Extract ALL technical skills, even if mentioned only once
- For strongest_metrics, capture EVERY number/percentage — this is critical
- For work_history key_bullets, pick the 3 most impressive bullets per role
- If a field cannot be determined, use null (not empty string)
- years_experience: sum up months from all work entries, convert to years (round to 1 decimal)
- degree_level: use the highest degree mentioned
- Do NOT invent information not present in the resume"""


def _mock_profile_from_text(raw_text: str) -> dict[str, Any]:
    """Fallback: regex-based extraction when API is unavailable. Good enough for dev/testing."""
    import re as _re
    email = (_re.findall(r'[\w.+-]+@[\w-]+\.[\w.]+', raw_text) or [None])[0]
    phone = (_re.findall(r'[\d\-()+ ]{10,}', raw_text) or [None])[0]
    if phone:
        phone = phone.strip()
    # Guess name from first non-empty line
    lines = [l.strip() for l in raw_text.split('\n') if l.strip()]
    name = lines[0] if lines else None
    # Skills: find common tech keywords
    tech_kw = ["Python","SQL","Java","JavaScript","R","Machine Learning","Deep Learning",
               "NLP","XGBoost","PyTorch","TensorFlow","scikit-learn","pandas","NumPy",
               "Docker","AWS","Flask","React","Power BI","Tableau","Git","A/B Testing",
               "Random Forest","RNN","SVM","PCA","DBSCAN","ARIMA","Sentence-BERT"]
    skills = [k for k in tech_kw if k.lower() in raw_text.lower()]
    # Metrics: find all numbers with % or GB or K+
    metrics = _re.findall(r'[\d.]+(?:%|K\+| GB| GB/day| AUPRC| GPA| entrants| projects| countries)', raw_text)
    # Also grab "top X%" patterns
    metrics += _re.findall(r'top \d+%', raw_text, _re.IGNORECASE)
    metrics += _re.findall(r'\d+\.\d+ GPA', raw_text)
    return {
        "name": name, "email": email, "phone": phone,
        "degree_level": "Master" if "M.S." in raw_text or "Master" in raw_text else "Bachelor",
        "degree_fields": [], "universities": [],
        "graduation_year": None, "gpa": None,
        "years_experience": 0.0, "skills": skills,
        "companies": [], "industries": [],
        "languages_spoken": ["English", "Mandarin Chinese"] if "bilingual" in raw_text.lower() else [],
        "notable_achievements": [], "work_history": [],
        "strongest_metrics": list(set(metrics)),
        "_mock": True,
    }


def structure_with_claude(raw_text: str) -> dict[str, Any]:
    """Send raw resume text to Claude for structured extraction."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key or api_key == "REPLACE_ME":
        # Fallback to mock extraction for dev/testing
        return _mock_profile_from_text(raw_text)

    client = anthropic.Anthropic(api_key=api_key)

    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": f"Parse this resume:\n\n{raw_text[:8000]}"}
            ],
        )
    except Exception as e:
        err_str = str(e).lower()
        if any(kw in err_str for kw in ["credit", "authentication", "401", "400", "api key"]):
            print(f"[parser] API unavailable ({type(e).__name__}), using mock extraction")
            return _mock_profile_from_text(raw_text)
        raise ParseError(f"Claude API error: {e}")

    response_text = message.content[0].text.strip()

    # Strip markdown fences if Claude adds them despite instructions
    if response_text.startswith("```"):
        response_text = re.sub(r"^```(?:json)?\s*", "", response_text)
        response_text = re.sub(r"\s*```$", "", response_text)

    try:
        profile = json.loads(response_text)
    except json.JSONDecodeError as e:
        raise ParseError(f"Claude returned invalid JSON: {e}\nRaw: {response_text[:500]}")

    return profile


# ── Step 3: Validation ─────────────────────────────────────

def validate_profile(profile: dict[str, Any]) -> dict[str, Any]:
    """Validate and fix extracted profile. Raises ParseError on critical failures."""
    warnings = []

    # Critical: name must exist
    if not profile.get("name"):
        raise ParseError("Could not extract name from resume")

    # Default degree_level
    if not profile.get("degree_level"):
        profile["degree_level"] = "Bachelor"
        warnings.append("degree_level not found, defaulted to Bachelor")

    # Ensure lists are lists
    for field in ["skills", "companies", "industries", "universities",
                  "degree_fields", "languages_spoken", "notable_achievements",
                  "work_history", "strongest_metrics"]:
        if not isinstance(profile.get(field), list):
            profile[field] = []

    # strongest_metrics should have at least 2
    if len(profile.get("strongest_metrics", [])) < 2:
        warnings.append(f"Only {len(profile.get('strongest_metrics', []))} metrics found — resume may lack quantified achievements")

    # work_history key_bullets should be populated
    for i, wh in enumerate(profile.get("work_history", [])):
        if not wh.get("key_bullets"):
            warnings.append(f"work_history[{i}] ({wh.get('company', '?')}) has no key_bullets")

    # Ensure numeric fields
    if profile.get("gpa") is not None:
        try:
            profile["gpa"] = float(profile["gpa"])
        except (ValueError, TypeError):
            profile["gpa"] = None

    if profile.get("years_experience") is not None:
        try:
            profile["years_experience"] = float(profile["years_experience"])
        except (ValueError, TypeError):
            profile["years_experience"] = 0.0

    profile["_warnings"] = warnings
    return profile


# ── Main entry point ───────────────────────────────────────

def parse_resume(file_bytes: bytes, filename: str) -> dict[str, Any]:
    """
    Parse a resume file into a structured profile.

    Args:
        file_bytes: Raw bytes of the uploaded file
        filename: Original filename (used to detect PDF vs DOCX)

    Returns:
        Structured profile dict with all extracted fields

    Raises:
        ParseError: On unrecoverable parsing failures
    """
    # Step 1: Extract raw text
    raw_text = extract_text(file_bytes, filename)

    # Step 2: Structure with Claude
    profile = structure_with_claude(raw_text)

    # Step 3: Validate
    profile = validate_profile(profile)

    return profile
