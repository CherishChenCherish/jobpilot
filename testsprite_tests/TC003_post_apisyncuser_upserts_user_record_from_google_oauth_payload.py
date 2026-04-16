import requests

BASE_URL = "http://localhost:5001"
TIMEOUT = 30
HEADERS = {
    "Content-Type": "application/json"
}

def test_post_api_sync_user():
    url = f"{BASE_URL}/api/sync-user"

    # Test 1: Valid request with email, name, and image
    valid_payload = {
        "email": "testuser@example.com",
        "name": "Test User",
        "image": "https://example.com/image.png"
    }
    try:
        response = requests.post(url, json=valid_payload, headers=HEADERS, timeout=TIMEOUT)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert isinstance(data.get("id"), int), "Response missing valid 'id'"
        assert data.get("email") == valid_payload["email"], "Response email does not match request email"
    except requests.RequestException as e:
        assert False, f"RequestException occurred: {e}"

    # Test 2: Invalid request missing email - expect 400 validation error
    invalid_payload = {
        "name": "No Email User"
        # email missing
    }
    try:
        response = requests.post(url, json=invalid_payload, headers=HEADERS, timeout=TIMEOUT)
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        # Optionally check validation error message in response content
    except requests.RequestException as e:
        assert False, f"RequestException occurred: {e}"

test_post_api_sync_user()