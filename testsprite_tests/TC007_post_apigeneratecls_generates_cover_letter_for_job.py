import requests

BASE_URL = "http://localhost:5001"
TIMEOUT = 30

# Dummy auth token for testing, replace with valid token if necessary
AUTH_TOKEN = "Bearer valid_test_auth_token_example"

def test_post_api_generate_cls():
    headers = {
        "Authorization": AUTH_TOKEN,
        "Content-Type": "application/json"
    }

    # We need a valid job_id and resume_text for the happy path.
    # Since job_id is required and no direct endpoint provides it standalone,
    # we will create a job via /api/search to get one valid job_id.
    # Also, for resume_text, we provide a dummy string.

    # Step 1: Get a valid job_id via /api/search
    search_headers = {
        "Authorization": AUTH_TOKEN,
        "Content-Type": "application/json"
    }
    search_payload = {
        "direction": "Software",
        "region": "US",
        "degree": "MS",
        "visa_needed": False
    }

    valid_job_id = None
    try:
        search_resp = requests.post(f"{BASE_URL}/api/search", json=search_payload, headers=search_headers, timeout=TIMEOUT)
        assert search_resp.status_code == 200, f"Search failed with status {search_resp.status_code}"
        search_data = search_resp.json()
        jobs = search_data.get("jobs", [])
        assert isinstance(jobs, list), "Jobs not returned as a list"
        assert len(jobs) > 0, "No jobs returned from search"

        valid_job_id = jobs[0].get("id") or jobs[0].get("job_id") or jobs[0].get("jobId")
        assert valid_job_id is not None, "Job id not found on job item"

        resume_text = "Experienced software engineer with expertise in Python and backend development."

        # Happy Path: Valid job_id and resume_text
        payload = {
            "job_id": valid_job_id,
            "resume_text": resume_text
        }
        resp = requests.post(f"{BASE_URL}/api/generate-cls", json=payload, headers=headers, timeout=TIMEOUT)
        assert resp.status_code == 200, f"Expected 200 OK but got {resp.status_code}"
        data = resp.json()
        assert "cover_letter" in data, "Response JSON missing 'cover_letter'"
        assert isinstance(data["cover_letter"], str) and len(data["cover_letter"]) > 0, "'cover_letter' should be a non-empty string"

        # Error Case 1: Invalid job_id returns 400
        invalid_payload = {
            "job_id": 0,  # Assuming 0 is invalid job_id
            "resume_text": resume_text
        }
        resp_invalid = requests.post(f"{BASE_URL}/api/generate-cls", json=invalid_payload, headers=headers, timeout=TIMEOUT)
        assert resp_invalid.status_code == 400, f"Expected 400 Bad Request but got {resp_invalid.status_code}"

        # Error Case 2: Claude API error returns 500
        # To simulate Claude API error realistically might be hard,
        # but try sending a special payload that might trigger it (e.g., extremely long resume_text)
        error_payload = {
            "job_id": valid_job_id,
            "resume_text": "x" * 1000000  # Very long text to try to provoke an internal error
        }
        resp_error = requests.post(f"{BASE_URL}/api/generate-cls", json=error_payload, headers=headers, timeout=TIMEOUT)
        assert resp_error.status_code in (200, 500), "Expected 200 or 500 status for Claude API error simulation"
        if resp_error.status_code == 500:
            err_data = resp_error.json()
            assert "error" in err_data or "message" in err_data or "detail" in err_data, "Expected error message in 500 response"

    except Exception as e:
        raise
    # No resource creation/deletion necessary here for job_id since it's from search

test_post_api_generate_cls()
