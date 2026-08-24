import requests

BASE_URL = "http://localhost:5001"
TIMEOUT = 30

def test_get_apidemoverify_verifies_job_url_open_status():
    session = requests.Session()
    headers = {
        "Accept": "application/json"
    }

    # Test case 1: valid url query returns 200 with verified_open and confidence
    valid_url = "https://example.com/job-posting"
    params = {"url": valid_url}

    try:
        resp = session.get(f"{BASE_URL}/api/demo-verify", headers=headers, params=params, timeout=TIMEOUT)
        assert resp.status_code == 200, f"Expected 200 OK, got {resp.status_code}"
        data = resp.json()
        assert isinstance(data, dict), "Response is not a JSON object"
        assert "verified_open" in data, "'verified_open' key missing in response"
        assert isinstance(data["verified_open"], bool), "'verified_open' is not boolean"
        assert "confidence" in data, "'confidence' key missing in response"
        assert isinstance(data["confidence"], str), "'confidence' is not string"
    except requests.RequestException as e:
        assert False, f"RequestException during valid url test: {e}"
    except ValueError as e:
        assert False, f"JSON decode error for valid url test: {e}"

    # Test case 2: missing url query returns 400
    try:
        resp = session.get(f"{BASE_URL}/api/demo-verify", headers=headers, timeout=TIMEOUT)
        assert resp.status_code == 400, f"Expected 400 Bad Request for missing url, got {resp.status_code}"
    except requests.RequestException as e:
        assert False, f"RequestException during missing url test: {e}"

test_get_apidemoverify_verifies_job_url_open_status()