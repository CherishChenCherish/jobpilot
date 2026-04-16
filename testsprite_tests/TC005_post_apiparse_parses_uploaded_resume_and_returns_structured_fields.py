import requests
import io

BASE_URL = "http://localhost:5001"
TIMEOUT = 30

# Preset valid user credentials for authentication (simulate getting auth token)
AUTH_EMAIL = "testuser@example.com"
AUTH_NAME = "Test User"
AUTH_IMAGE = "https://example.com/avatar.png"


def get_auth_token():
    """
    Sync a user to get a user id and emulate auth token.
    Assumes server returns a token in response header or cookie (if this API doesn't return token, 
    modify this function to match actual auth method).
    This is a placeholder to simulate authenticated requests by fetching user profile or 
    setting auth header accordingly.
    """
    # This API does not explicitly state token issuance, so we simulate auth by syncing user and then calling /api/me for session
    # We will assume Bearer token auth with a fixed token or no token needed but "auth required" means we pass header with user info

    # For this test, we assume the backend uses a Bearer token issued externally; so here we simulate an auth token placeholder
    # If real token is required, adapt fetching it accordingly.
    # Here, just re-sync user and see if API requires cookies/session or headers - we simulate with header 'Authorization'

    # Sync user to assure user exists
    sync_resp = requests.post(
        f"{BASE_URL}/api/sync-user",
        json={"email": AUTH_EMAIL, "name": AUTH_NAME, "image": AUTH_IMAGE},
        timeout=TIMEOUT,
    )
    if sync_resp.status_code != 200:
        raise RuntimeError("Failed to sync user for auth token simulation")

    # Since no token mechanism is described, return a dummy token pretending auth is required; 
    # if API requires cookies or other mechanism, adjust accordingly.
    return "testauthtoken"


def test_post_apiparse_parses_resume():
    auth_token = get_auth_token()
    headers = {
        "Authorization": f"Bearer {auth_token}"
    }

    parse_url = f"{BASE_URL}/api/parse"

    # Valid PDF file content (minimal PDF header + dummy content)
    valid_pdf_content = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\nstartxref\n0\n%%EOF\n"
    valid_docx_content = (
        b"PK\x03\x04"  # DOCX files are ZIP archives; minimal ZIP file header
        b"\x14\x00\x06\x00"
        b"\x00\x00\x00\x00"
        b"\x00\x00\x00\x00"
    )

    # Malformed file content (not PDF or DOCX)
    invalid_file_content = b"This is not a supported resume format file."

    # Helper to do POST /api/parse with given file content and filename
    def post_parse(file_content, filename):
        files = {
            "file": (filename, io.BytesIO(file_content), "application/octet-stream")
        }
        resp = requests.post(parse_url, headers=headers, files=files, timeout=TIMEOUT)
        return resp

    # Test 1: Valid PDF file, expect 200 and correct fields
    resp_pdf = post_parse(valid_pdf_content, "resume.pdf")
    assert resp_pdf.status_code == 200, f"Expected 200 for valid PDF, got {resp_pdf.status_code}"
    json_pdf = resp_pdf.json()
    assert isinstance(json_pdf.get("skills"), list), "Expected 'skills' to be a list"
    assert isinstance(json_pdf.get("degree"), str), "Expected 'degree' to be a string"
    assert isinstance(json_pdf.get("direction"), str), "Expected 'direction' to be a string"
    assert isinstance(json_pdf.get("experience"), str), "Expected 'experience' to be a string"

    # Test 2: Valid DOCX file, expect 200 and correct fields
    resp_docx = post_parse(valid_docx_content, "resume.docx")
    assert resp_docx.status_code == 200, f"Expected 200 for valid DOCX, got {resp_docx.status_code}"
    json_docx = resp_docx.json()
    assert isinstance(json_docx.get("skills"), list), "Expected 'skills' to be a list"
    assert isinstance(json_docx.get("degree"), str), "Expected 'degree' to be a string"
    assert isinstance(json_docx.get("direction"), str), "Expected 'direction' to be a string"
    assert isinstance(json_docx.get("experience"), str), "Expected 'experience' to be a string"

    # Test 3: Invalid file format, expect 400
    resp_invalid = post_parse(invalid_file_content, "resume.txt")
    assert resp_invalid.status_code == 400, f"Expected 400 for invalid file, got {resp_invalid.status_code}"

    # Test 4: Simulate Claude API error resulting in 500
    # Since we cannot mock the server here, try sending a file known to cause Claude error (simulate with empty PDF)
    # Alternatively, send an empty file possibly triggering server error
    resp_error = post_parse(b"", "empty.pdf")
    # Allowing 200 if server doesn't error but checking 500 case allowed
    assert resp_error.status_code in (200, 500), f"Expected 200 or 500 on error simulation, got {resp_error.status_code}"
    if resp_error.status_code == 500:
        # Validate error message in response
        json_err = resp_error.json()
        assert "Parser error" in str(json_err), "Expected Parser error message in 500 response"


test_post_apiparse_parses_resume()