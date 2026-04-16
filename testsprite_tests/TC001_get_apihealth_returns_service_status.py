import requests

BASE_URL = "http://localhost:5001"
TIMEOUT = 30

def test_get_api_health_returns_service_status():
    url = f"{BASE_URL}/api/health"
    headers = {
        "Accept": "application/json"
    }
    try:
        response = requests.get(url, headers=headers, timeout=TIMEOUT)
        # Assert status code 200
        assert response.status_code == 200, f"Unexpected status code: {response.status_code}"
        # Assert response JSON has key 'status' of type string and value non-empty
        json_resp = response.json()
        assert "status" in json_resp, "Response JSON missing 'status' key"
        assert isinstance(json_resp["status"], str), "'status' is not a string"
        assert json_resp["status"].strip() != "", "'status' string is empty"
    except requests.RequestException as e:
        assert False, f"Request to /api/health failed: {e}"

test_get_api_health_returns_service_status()