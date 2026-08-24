import requests

def test_get_apihealth_returns_service_status():
    base_url = "http://localhost:5001"
    url = f"{base_url}/api/health"
    headers = {
        "Accept": "application/json"
    }
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        assert False, f"Request to {url} failed: {e}"

    assert response.status_code == 200, f"Expected status code 200 but got {response.status_code}"

    try:
        data = response.json()
    except ValueError:
        assert False, "Response is not valid JSON"

    assert "status" in data, "Response JSON missing 'status' field"
    assert isinstance(data["status"], str), "'status' field is not a string"
    assert data["status"].lower() in ["up", "ok", "running", "healthy", "available", "online"], \
        f"Unexpected status string: {data['status']}"

test_get_apihealth_returns_service_status()