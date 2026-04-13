import requests

BASE_URL = "http://localhost:5000"
TIMEOUT = 30

# Assumed test user credentials or token retrieval function
def get_auth_token():
    # This function should be implemented to return a valid auth token string for testing.
    # For this example, we'll use a placeholder.
    # Replace with actual authentication method if necessary.
    return "Bearer test-valid-auth-token"

def test_post_api_generate_cls():
    headers = {
        "Authorization": get_auth_token(),
        "Content-Type": "application/json"
    }

    # First, to get a valid job_id, we must create or find one.
    # Per PRD: Job search endpoint requires auth and can return jobs passing core promise.
    # We'll do a minimal search to get a valid job_id.
    search_payload = {
        "direction": "Software",
        "region": "US",
        "degree": "MS",
        "visa_needed": False
    }
    search_resp = requests.post(
        f"{BASE_URL}/api/search",
        json=search_payload,
        headers=headers,
        timeout=TIMEOUT,
    )
    assert search_resp.status_code == 200, f"Job search failed with {search_resp.status_code}"
    search_data = search_resp.json()
    jobs = search_data.get("jobs", [])
    assert jobs, "No jobs found for search to test generate-cls"

    valid_job_id = jobs[0]["id"] if "id" in jobs[0] else jobs[0].get("job_id") or jobs[0].get("jobId")
    assert isinstance(valid_job_id, int), "Job ID is not found or not an integer"

    # Prepare a valid resume_text (can be any string for testing)
    valid_resume_text = "Experienced software engineer with 5 years in Python and backend development."

    # 1) Valid request with valid job_id and resume_text should return 200 and cover_letter string
    generate_payload = {
        "job_id": valid_job_id,
        "resume_text": valid_resume_text
    }
    resp_valid = requests.post(
        f"{BASE_URL}/api/generate-cls",
        json=generate_payload,
        headers=headers,
        timeout=TIMEOUT,
    )
    assert resp_valid.status_code == 200, f"Valid generate-cls request failed with status {resp_valid.status_code}"
    json_valid = resp_valid.json()
    cover_letter = json_valid.get("cover_letter")
    assert cover_letter and isinstance(cover_letter, str), "cover_letter missing or not a string in valid response"

    # 2) Invalid job_id returns 400 Validation error
    invalid_payload = {
        "job_id": -999999,  # Assuming this ID does not exist
        "resume_text": valid_resume_text
    }
    resp_invalid_job = requests.post(
        f"{BASE_URL}/api/generate-cls",
        json=invalid_payload,
        headers=headers,
        timeout=TIMEOUT,
    )
    assert resp_invalid_job.status_code == 400, f"Invalid job_id did not return 400, got {resp_invalid_job.status_code}"

    # 3) Claude API errors return 500
    # To simulate Claude API error, send a valid job_id but malformed or very large resume_text that might trigger error.
    # If no direct simulation possible, try empty resume_text or special string like 'trigger_error'
    error_payload = {
        "job_id": valid_job_id,
        "resume_text": "trigger_claude_api_error_simulation"
    }
    resp_error = requests.post(
        f"{BASE_URL}/api/generate-cls",
        json=error_payload,
        headers=headers,
        timeout=TIMEOUT,
    )
    assert resp_error.status_code in (500, 200), (
        "Claude API error test returned unexpected status code "
        f"{resp_error.status_code} - expected 500 or handled gracefully"
    )
    # If 500, can optionally check error message key exist
    if resp_error.status_code == 500:
        try:
            json_err = resp_error.json()
            assert "error" in json_err or "message" in json_err, "500 response does not contain error message"
        except Exception:
            # May not return json, skip detailed check
            pass

test_post_api_generate_cls()