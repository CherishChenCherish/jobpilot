import requests

BASE_URL = "http://localhost:5001"
TIMEOUT = 30

def test_post_apisyncuser_upserts_user_record():
    url = f"{BASE_URL}/api/sync-user"
    headers = {
        "Content-Type": "application/json",
    }

    # Valid payload
    valid_payload = {
        "email": "testuser@example.com",
        "name": "Test User",
        "image": "https://example.com/avatar.png"
    }

    # Test valid request
    try:
        response = requests.post(url, json=valid_payload, headers=headers, timeout=TIMEOUT)
    except requests.RequestException as e:
        assert False, f"Request failed: {e}"

    assert response.status_code == 200, f"Expected status 200 but got {response.status_code}"
    try:
        data = response.json()
    except ValueError:
        assert False, "Response is not valid JSON"

    assert "id" in data, "Response JSON missing 'id'"
    assert data.get("email") == valid_payload["email"], f"Response email {data.get('email')} does not match request email {valid_payload['email']}"

    # Test invalid request missing email
    invalid_payload = {
        "name": "No Email User",
        "image": "https://example.com/avatar.png"
    }

    try:
        response_invalid = requests.post(url, json=invalid_payload, headers=headers, timeout=TIMEOUT)
    except requests.RequestException as e:
        assert False, f"Request failed: {e}"

    assert response_invalid.status_code == 400, f"Expected status 400 but got {response_invalid.status_code}"

test_post_apisyncuser_upserts_user_record()