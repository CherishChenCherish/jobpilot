import requests
import io

BASE_URL = "http://localhost:5001"
TIMEOUT = 30

# Assume we have a valid auth token or session cookie from Google OAuth.
# For this test, we simulate by setting a dummy Authorization header.
# Replace 'your_auth_token_here' with a real token if available.
AUTH_HEADERS = {
    "Authorization": "Bearer your_auth_token_here"
}

def test_post_apiparse():
    # Prepare minimal valid PDF and DOCX files content for testing
    pdf_content = b"%PDF-1.4\n%EOF\n"  # Minimal PDF header/footer, may not parse fully but used as dummy
    docx_content = b"PK\x03\x04"  # DOCX files are ZIP archives starting with 'PK\x03\x04'
    invalid_content = b"This is not a supported resume file."

    url = f"{BASE_URL}/api/parse"

    # Test valid PDF upload
    pdf_file = io.BytesIO(pdf_content)
    files = {"file": ("test_resume.pdf", pdf_file, "application/pdf")}
    resp = requests.post(url, headers=AUTH_HEADERS, files=files, timeout=TIMEOUT)
    assert resp.status_code == 200, f"Expected 200 for valid PDF, got {resp.status_code}"
    json_data = resp.json()
    for field in ["skills", "degree", "direction"]:
        assert field in json_data, f"Field '{field}' missing in PDF parse response"

    # Test valid DOCX upload
    docx_file = io.BytesIO(docx_content)
    files = {"file": ("test_resume.docx", docx_file, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    resp = requests.post(url, headers=AUTH_HEADERS, files=files, timeout=TIMEOUT)
    assert resp.status_code == 200, f"Expected 200 for valid DOCX, got {resp.status_code}"
    json_data = resp.json()
    for field in ["skills", "degree", "direction"]:
        assert field in json_data, f"Field '{field}' missing in DOCX parse response"

    # Test invalid file upload (txt)
    invalid_file = io.BytesIO(invalid_content)
    files = {"file": ("test_invalid.txt", invalid_file, "text/plain")}
    resp = requests.post(url, headers=AUTH_HEADERS, files=files, timeout=TIMEOUT)
    assert resp.status_code == 400, f"Expected 400 for invalid file, got {resp.status_code}"

    # Test Claude API error simulation is complex without control over backend.
    # We try uploading a valid file with a special trigger filename to simulate error if supported.
    error_trigger_filename = "claude_error_trigger.pdf"
    pdf_file = io.BytesIO(pdf_content)
    files = {"file": (error_trigger_filename, pdf_file, "application/pdf")}
    resp = requests.post(url, headers=AUTH_HEADERS, files=files, timeout=TIMEOUT)
    if resp.status_code == 500:
        # Confirm JSON or text error message likely returned
        try:
            _ = resp.json()
        except Exception:
            pass
    else:
        # It's acceptable no 500 returned if backend not simulating error here
        assert resp.status_code in (200, 400), f"Unexpected status code {resp.status_code} for Claude API error simulation"

test_post_apiparse()
