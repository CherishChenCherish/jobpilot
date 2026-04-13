import requests

BASE_URL = "http://localhost:5000"
TIMEOUT = 30

def test_get_apidemo_verify():
    # Test with valid url query param
    valid_url = "https://company.jobs/123"
    try:
        response = requests.get(
            f"{BASE_URL}/api/demo-verify",
            params={"url": valid_url},
            timeout=TIMEOUT
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "verified_open" in data and isinstance(data["verified_open"], bool), "Missing or invalid 'verified_open'"
        assert "confidence" in data and isinstance(data["confidence"], str), "Missing or invalid 'confidence'"
    except (requests.RequestException, AssertionError) as e:
        raise AssertionError(f"Failed valid url test: {e}")

    # Test with missing url query param
    try:
        response = requests.get(
            f"{BASE_URL}/api/demo-verify",
            timeout=TIMEOUT
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
    except requests.RequestException as e:
        raise AssertionError(f"Failed missing url test: {e}")

test_get_apidemo_verify()
