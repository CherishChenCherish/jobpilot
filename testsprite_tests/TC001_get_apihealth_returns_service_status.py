import requests

BASE_URL = "http://localhost:5000"
TIMEOUT = 30

def test_get_api_health_returns_service_status():
    url = f"{BASE_URL}/api/health"
    try:
        response = requests.get(url, timeout=TIMEOUT)
        # Assert status code is 200
        assert response.status_code == 200, f"Expected status code 200 but got {response.status_code}"
        json_data = response.json()
        # Assert response JSON has 'status' key with a non-empty string value
        assert "status" in json_data, "'status' key missing in response JSON"
        assert isinstance(json_data["status"], str), "'status' value is not a string"
        assert json_data["status"].strip() != "", "'status' value is empty"
    except requests.RequestException as e:
        assert False, f"Request failed: {e}"

test_get_api_health_returns_service_status()