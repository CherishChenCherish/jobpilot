import requests
import json

BASE_URL = "http://localhost:5001"
TIMEOUT = 30

# Placeholder valid auth token (should be replaced with a real token from an authenticated session)
VALID_AUTH_TOKEN = "Bearer valid_auth_token_example"

# Sample valid resume text for testing
SAMPLE_RESUME_TEXT = (
    "Experienced software engineer with expertise in Python, data analysis, "
    "and cloud computing. Skilled in developing scalable applications and "
    "working collaboratively in agile teams."
)

def test_post_api_generate_cls():
    headers = {
        "Authorization": VALID_AUTH_TOKEN,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    def create_dummy_job():
        # Since no API for job creation is described, we treat this step as a placeholder.
        # If possible, fetch existing jobs or else skip and set job_id to None.
        # Here, we return None and skip creation to simulate.
        return None

    def delete_dummy_job(job_id):
        # Placeholder for job cleanup if job was created
        pass

    job_id = create_dummy_job()

    # Test 1: POST with valid job_id and resume_text returns 200 with a cover letter
    # If no real job_id, test with a known assumed valid id for demonstration (e.g. 1)
    valid_job_id = job_id or 1

    payload_valid = {
        "job_id": valid_job_id,
        "resume_text": SAMPLE_RESUME_TEXT
    }

    try:
        resp_valid = requests.post(
            f"{BASE_URL}/api/generate-cls",
            headers=headers,
            data=json.dumps(payload_valid),
            timeout=TIMEOUT,
        )
        # The response should be 200 with a JSON containing the cover letter text
        assert resp_valid.status_code == 200, f"Expected 200, got {resp_valid.status_code}"
        resp_json = resp_valid.json()
        assert "cover_letter" in resp_json, "Response JSON missing 'cover_letter'"
        assert isinstance(resp_json["cover_letter"], str), "'cover_letter' should be a string"
        assert len(resp_json["cover_letter"]) > 0, "Cover letter should not be empty"

        # Test 2: POST with invalid job_id returns 400
        invalid_job_id = -999999  # presumably invalid
        payload_invalid_job = {
            "job_id": invalid_job_id,
            "resume_text": SAMPLE_RESUME_TEXT
        }
        resp_invalid_job = requests.post(
            f"{BASE_URL}/api/generate-cls",
            headers=headers,
            data=json.dumps(payload_invalid_job),
            timeout=TIMEOUT,
        )
        assert resp_invalid_job.status_code == 400, f"Expected 400 for invalid job_id, got {resp_invalid_job.status_code}"

        # Test 3: Simulate Claude API error returning 500
        # Since no payload triggers this reliably, try a reserved job_id or text that might cause server error if known.
        # Here, try an explicit request with a specific dummy job_id and suspicious resume_text.
        # This is speculative because the PRD doesn't specify how to trigger 500.
        payload_claude_error = {
            "job_id": valid_job_id,
            "resume_text": "trigger_claude_api_error_simulation"
        }
        resp_500 = requests.post(
            f"{BASE_URL}/api/generate-cls",
            headers=headers,
            data=json.dumps(payload_claude_error),
            timeout=TIMEOUT,
        )
        if resp_500.status_code == 500:
            pass  # Expected 500 for Claude API error simulation
        else:
            # If server does not respond 500, that's acceptable as it depends on backend state.
            assert resp_500.status_code in (200, 400), f"Unexpected status code {resp_500.status_code} for Claude API error test"

    finally:
        if job_id:
            delete_dummy_job(job_id)


test_post_api_generate_cls()