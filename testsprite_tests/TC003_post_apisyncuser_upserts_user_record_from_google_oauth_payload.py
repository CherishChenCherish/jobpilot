import requests

BASE_URL = "http://localhost:5000"
TIMEOUT = 30
HEADERS = {"Content-Type": "application/json"}


def test_post_api_sync_user_upsert_user():
    url = f"{BASE_URL}/api/sync-user"

    # Valid payload with email, name and image
    valid_payload = {
        "email": "user@example.com",
        "name": "User Name",
        "image": "https://example.com/image.jpg"
    }

    try:
        # Test valid request returns 200 with id and email
        response = requests.post(url, json=valid_payload, headers=HEADERS, timeout=TIMEOUT)
        assert response.status_code == 200, f"Expected 200 OK but got {response.status_code}"
        data = response.json()
        assert isinstance(data.get("id"), int), "Returned id should be an integer"
        assert data.get("email") == valid_payload["email"], "Returned email should match input email"
    except requests.RequestException as e:
        assert False, f"Request failed unexpectedly: {e}"

    # Invalid payload missing email
    invalid_payload = {
        "name": "NoEmail"
    }

    try:
        # Test invalid request returns 400 validation error
        response = requests.post(url, json=invalid_payload, headers=HEADERS, timeout=TIMEOUT)
        assert response.status_code == 400, f"Expected 400 Bad Request but got {response.status_code}"
        # Response body may contain validation error description; optional check
        error_data = response.json()
        assert isinstance(error_data, dict), "Error response should be a JSON object"
    except requests.RequestException as e:
        assert False, f"Request failed unexpectedly: {e}"


test_post_api_sync_user_upsert_user()