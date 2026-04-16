import requests

BASE_URL = "http://localhost:5001"
TIMEOUT = 30

def test_get_api_demo_verify():
    valid_url = "https://company.jobs/123"
    endpoint = f"{BASE_URL}/api/demo-verify"

    # Test case 1: valid url query returns 200 with verified_open (bool) and confidence (str)
    params = {'url': valid_url}
    try:
        response = requests.get(endpoint, params=params, timeout=TIMEOUT)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        json_data = response.json()
        assert isinstance(json_data, dict), "Response is not a JSON object"
        assert "verified_open" in json_data, "'verified_open' key missing in response"
        assert isinstance(json_data["verified_open"], bool), "'verified_open' is not boolean"
        assert "confidence" in json_data, "'confidence' key missing in response"
        assert isinstance(json_data["confidence"], str), "'confidence' is not string"
    except requests.RequestException as e:
        assert False, f"RequestException occurred: {e}"

    # Test case 2: missing url query param returns 400
    try:
        response = requests.get(endpoint, timeout=TIMEOUT)
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
    except requests.RequestException as e:
        assert False, f"RequestException occurred: {e}"

test_get_api_demo_verify()