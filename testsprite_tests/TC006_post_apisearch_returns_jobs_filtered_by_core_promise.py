import requests

BASE_URL = "http://localhost:5000"
TIMEOUT = 30

# This test assumes existence of a valid auth token. 
# Replace 'your_valid_auth_token_here' with a real token for actual testing.
AUTH_TOKEN = "your_valid_auth_token_here"
HEADERS_AUTH = {"Authorization": f"Bearer {AUTH_TOKEN}", "Content-Type": "application/json"}
HEADERS_NO_AUTH = {"Content-Type": "application/json"}

def test_post_api_search_core_promise():
    url = f"{BASE_URL}/api/search"
    valid_payload = {
        "direction": "Software",
        "region": "US",
        "degree": "MS",
        "visa_needed": False
    }
    invalid_region_payload = {
        "direction": "Software",
        "region": "Mars",
        "degree": "MS",
        "visa_needed": False
    }
    # 1. Test valid request with auth returns 200 and jobs all pass core promise
    resp = requests.post(url, json=valid_payload, headers=HEADERS_AUTH, timeout=TIMEOUT)
    assert resp.status_code == 200, f"Expected 200 for valid request, got {resp.status_code}"
    data = resp.json()
    assert "jobs" in data and isinstance(data["jobs"], list), "Response missing or invalid 'jobs' key"
    assert "search_id" in data and isinstance(data["search_id"], int), "Response missing or invalid 'search_id' key"
    # Each job should pass core promise conditions: open, location, direction, identity (degree or visa)
    for job in data["jobs"]:
        assert isinstance(job, dict), "Job item is not a dictionary"
        # Core Promise checks (based on PRD - typical keys, adjust if keys differ):
        # 'open' true
        assert job.get("open") is True, f"Job id {job.get('id')} does not have open=true"
        # location matches requested region (US)
        job_region = job.get("region")
        assert job_region == valid_payload["region"], f"Job id {job.get('id')} region mismatch: {job_region} != {valid_payload['region']}"
        # direction matches requested direction
        job_direction = job.get("direction")
        assert job_direction == valid_payload["direction"], f"Job id {job.get('id')} direction mismatch: {job_direction} != {valid_payload['direction']}"
        # identity condition: degree or visa sponsorship
        # Prefer checking degree_required vs user degree or visa_sponsorship and visa_needed
        degree_required = job.get("degree_required")
        visa_sponsorship = job.get("visa_sponsorship", False)
        user_degree = valid_payload["degree"]
        user_visa_needed = valid_payload["visa_needed"]
        # Degree requirement check: if job requires degree, user's degree should satisfy or be higher,
        # but just check equality or compatibility in test (could be string equality)
        # For simplicity: degree_required must be in ['BS','MS','PhD'] or None/empty means no degree required
        if degree_required:
            # Simple check that given user degree matches job required degree
            assert degree_required in ["BS","MS","PhD"], f"Invalid degree required value in job id {job.get('id')}"
            # Assuming degrees same string equality satisfies requirement for test
            assert degree_required == user_degree, f"Job id {job.get('id')} degree_required {degree_required} != user degree {user_degree}"
        # Visa check: if user needs visa, job must sponsor visa
        if user_visa_needed:
            assert visa_sponsorship is True, f"Job id {job.get('id')} does not sponsor visas but user needs visa"
        # If user visa_needed false, no restriction on visa_sponsorship
    # 2. Test invalid region returns 400 with auth
    resp_invalid_region = requests.post(url, json=invalid_region_payload, headers=HEADERS_AUTH, timeout=TIMEOUT)
    assert resp_invalid_region.status_code == 400, f"Expected 400 for invalid region, got {resp_invalid_region.status_code}"
    # It's a validation error; response body likely contains error message (optional to assert)
    data_invalid = resp_invalid_region.json()
    assert isinstance(data_invalid, dict), "Invalid region response is not JSON object"
    # 3. Test no auth returns 401 Unauthorized
    resp_no_auth = requests.post(url, json=valid_payload, headers=HEADERS_NO_AUTH, timeout=TIMEOUT)
    assert resp_no_auth.status_code == 401, f"Expected 401 without auth, got {resp_no_auth.status_code}"
    # 4. Test body that matches jobs failing core promise returns empty jobs list (filtered out)
    # We simulate by sending a payload that likely matches jobs failing core promise, for example:
    # direction consistent, region valid, degree valid, but visa_needed True where jobs do not sponsor visa
    fail_promise_payload = {
        "direction": "Software",
        "region": "US",
        "degree": "MS",
        "visa_needed": True  # Some jobs may not sponsor visa and thus be filtered out
    }
    resp_fail_promise = requests.post(url, json=fail_promise_payload, headers=HEADERS_AUTH, timeout=TIMEOUT)
    assert resp_fail_promise.status_code == 200, f"Expected 200 for filtered search, got {resp_fail_promise.status_code}"
    data_fail = resp_fail_promise.json()
    jobs_fail = data_fail.get("jobs")
    assert isinstance(jobs_fail, list), "'jobs' key missing or not list in filtered response"
    # All jobs here should pass core promise, so jobs failing promise filtered out, so non-empty or empty allowed
    # The requirement states jobs failing core promise filtered out, so assert no job fails core promise
    for job in jobs_fail:
        assert job.get("open") is True, "Job failing Open condition found after filter"
        assert job.get("region") == fail_promise_payload["region"], "Job failing region condition found after filter"
        assert job.get("direction") == fail_promise_payload["direction"], "Job failing direction condition found after filter"
        degree_required = job.get("degree_required")
        if degree_required:
            assert degree_required == fail_promise_payload["degree"], "Job failing degree condition found after filter"
        if fail_promise_payload["visa_needed"]:
            assert job.get("visa_sponsorship", False) is True, "Job failing visa sponsorship condition found after filter"
    # If no jobs match the filter, jobs list may be empty - that is a valid filtered result
    # So no additional assertion for > 0 jobs

test_post_api_search_core_promise()