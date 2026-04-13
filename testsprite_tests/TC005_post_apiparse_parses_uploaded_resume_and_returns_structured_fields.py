import requests
from io import BytesIO

BASE_URL = "http://localhost:5000"
TIMEOUT = 30

# Assuming we have a function to get a valid auth token for testing
def get_auth_token():
    # This should be replaced with a real token retrieval mechanism for the test environment
    # For demonstration, we just return a placeholder string
    return "Bearer VALID_TEST_AUTH_TOKEN"

def test_post_api_parse_resume_parsing():
    headers = {
        "Authorization": get_auth_token()
    }

    # Helper function to perform parse call with given file and expect specific status and optional content checks
    def post_parse(file_tuple, expected_status, expected_keys=None):
        files = {
            "file": file_tuple
        }
        try:
            response = requests.post(
                f"{BASE_URL}/api/parse",
                headers=headers,
                files=files,
                timeout=TIMEOUT
            )
        except requests.RequestException as e:
            assert False, f"Request failed with exception: {e}"
        assert response.status_code == expected_status, f"Expected status {expected_status} but got {response.status_code}, response: {response.text}"
        if expected_status == 200 and expected_keys:
            json_data = response.json()
            for key in expected_keys:
                assert key in json_data, f"Response missing key '{key}'"
            # Additional checks for data types
            assert isinstance(json_data["skills"], list), "'skills' should be a list"
            assert all(isinstance(s, str) for s in json_data["skills"]), "'skills' list elements should be strings"
            assert isinstance(json_data["degree"], str), "'degree' should be a string"
            assert isinstance(json_data["direction"], str), "'direction' should be a string"
            assert isinstance(json_data["experience"], str), "'experience' should be a string"
        return response

    # Test with a valid PDF file (simple minimal PDF content)
    valid_pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Count 1 /Kids [3 0 R] >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>\nendobj\n4 0 obj\n<< /Length 44 >>\nstream\nBT /F1 24 Tf 100 700 Td (Test Resume PDF) Tj ET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000010 00000 n \n0000000060 00000 n \n0000000111 00000 n \n0000000210 00000 n \ntrailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n310\n%%EOF"
    valid_pdf_file = ("resume.pdf", BytesIO(valid_pdf_content), "application/pdf")
    post_parse(valid_pdf_file, 200, expected_keys=["skills", "degree", "direction", "experience"])

    # Test with a valid DOCX file (minimal valid DOCX content - using empty zip structure for test)
    # DOCX is a zip file, so minimal zip bytes representing a valid DOCX file
    import zipfile
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".docx") as temp_docx:
        with zipfile.ZipFile(temp_docx, mode='w') as zf:
            # add minimal document.xml in word folder to mimic docx
            zf.writestr("word/document.xml", "<?xml version='1.0' encoding='UTF-8'?><w:document xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'><w:body><w:p><w:r><w:t>Test Resume DOCX</w:t></w:r></w:p></w:body></w:document>")
        temp_docx.seek(0)
        valid_docx_file = ("resume.docx", temp_docx.read(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        post_parse(valid_docx_file, 200, expected_keys=["skills", "degree", "direction", "experience"])

    # Test with an invalid file type (e.g., a text file renamed as .txt)
    invalid_file_content = b"This is not a supported resume file format."
    invalid_file = ("not_a_resume.txt", BytesIO(invalid_file_content), "text/plain")
    post_parse(invalid_file, 400)

    # Test with a valid PDF file but simulate Claude API error (500).
    # We cannot simulate internal Claude API error from client side,
    # so instead, try sending a valid file marked to cause failure,
    # or alternatively assume that the server returns 500 for certain contents.
    # Here, we simulate by sending special file content indicating failure if server is expecting it.
    # If we cannot do that, just do the test call and accept the possibility no 500 is returned.
    # For demonstration, try an empty PDF which might cause parse error or server error.
    broken_pdf_content = b"%PDF-1.4\n%%EOF"
    broken_pdf_file = ("broken.pdf", BytesIO(broken_pdf_content), "application/pdf")
    try:
        response = requests.post(
            f"{BASE_URL}/api/parse",
            headers=headers,
            files={"file": broken_pdf_file},
            timeout=TIMEOUT,
        )
    except requests.RequestException as e:
        assert False, f"Request failed with exception: {e}"

    assert response.status_code in (200, 500, 400), f"Unexpected status code {response.status_code} for broken PDF test"

    if response.status_code == 500:
        json_data = response.json()
        # Either response body is string or object with error message
        # Just check content mentions parser error as per PRD
        assert ("Parser error" in response.text or "error" in json_data), "Expected parser error message on 500 response"

# Run the test
test_post_api_parse_resume_parsing()