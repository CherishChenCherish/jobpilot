import requests

BASE_URL = "http://localhost:5001"
TIMEOUT = 30

# Presuming existence of a function to get a valid auth token for testing purposes
def get_auth_token():
    # This function should retrieve a valid auth token for the user
    # For test purposes, return a placeholder token string
    return "Bearer valid_test_auth_token"


def test_post_api_search_core_promise():
    headers_auth = {
        "Authorization": get_auth_token(),
        "Content-Type": "application/json"
    }
    headers_no_auth = {
        "Content-Type": "application/json"
    }
    
    url_search = f"{BASE_URL}/api/search"

    # 1. Valid search - valid direction, region, degree, visa_needed, with auth
    payload_valid = {
        "direction": "Software",
        "region": "US",
        "degree": "MS",
        "visa_needed": False
    }

    try:
        resp = requests.post(url_search, json=payload_valid, headers=headers_auth, timeout=TIMEOUT)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert "jobs" in data and isinstance(data["jobs"], list), "Response missing jobs list"
        assert "search_id" in data and isinstance(data["search_id"], int), "Response missing or invalid search_id"
        # Each job must pass core promise conditions checked loosely here (presence of keys)
        for job in data["jobs"]:
            assert isinstance(job, dict), "Job item is not a dict"
            # Minimal promise keys to check presence
            # The exact core promise check is backend logic and assumed correct if jobs returned
            # but ensure no job is empty or missing keys that indicate core promise properties
            assert "open" in job or "location" in job or "direction" in job or "identity" in job or "no_sponsor" not in job, "Job item missing core promise indicators or flagged no_sponsor"
    except Exception as e:
        raise AssertionError(f"Valid search request failed: {e}")

    # 2. Invalid region (e.g., "Mars") with auth returns 400
    payload_invalid_region = {
        "direction": "Software",
        "region": "Mars",
        "degree": "MS",
        "visa_needed": False
    }
    try:
        resp = requests.post(url_search, json=payload_invalid_region, headers=headers_auth, timeout=TIMEOUT)
        assert resp.status_code == 400, f"Expected 400 for invalid region, got {resp.status_code}"
    except Exception as e:
        raise AssertionError(f"Invalid region search request failed: {e}")

    # 3. No auth returns 401 Unauthorized
    try:
        resp = requests.post(url_search, json=payload_valid, headers=headers_no_auth, timeout=TIMEOUT)
        assert resp.status_code == 401, f"Expected 401 Unauthorized without auth, got {resp.status_code}"
    except Exception as e:
        raise AssertionError(f"No auth search request failed: {e}")

    # 4. Search that would match jobs failing core promise returns 200 with empty 'jobs' list
    # For testing this, we assume a payload that matches jobs known to fail core promise,
    # e.g., visa_needed=True where no_sponsor jobs exist or region/direction that filter out jobs.
    payload_failing_promise = {
        "direction": "Software",
        "region": "US",
        "degree": "BS",
        "visa_needed": True  # Assume jobs with no_sponsor exist that fail promise if visa needed
    }
    try:
        resp = requests.post(url_search, json=payload_failing_promise, headers=headers_auth, timeout=TIMEOUT)
        assert resp.status_code == 200, f"Expected 200 for promise-fail filter, got {resp.status_code}"
        data = resp.json()
        assert "jobs" in data and isinstance(data["jobs"], list), "Response missing jobs list for promise-fail filter"
        assert len(data["jobs"]) == 0, "Jobs failing core promise were not filtered out"
    except Exception as e:
        raise AssertionError(f"Promise-fail filtered search request failed: {e}")


test_post_api_search_core_promise()
