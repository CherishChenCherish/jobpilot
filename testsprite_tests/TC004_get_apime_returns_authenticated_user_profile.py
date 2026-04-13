import requests

BASE_URL = "http://localhost:5000"
TIMEOUT = 30

def test_get_api_me_authenticated_and_unauthenticated():
    # First, create a user via /api/sync-user to get a user with valid credentials
    sync_user_url = f"{BASE_URL}/api/sync-user"
    user_data = {
        "email": "testuser@example.com",
        "name": "Test User",
        "image": "https://example.com/image.png"
    }
    try:
        sync_resp = requests.post(sync_user_url, json=user_data, timeout=TIMEOUT)
        assert sync_resp.status_code == 200, f"Sync user failed with status {sync_resp.status_code}"
        user_json = sync_resp.json()
        assert "id" in user_json and "email" in user_json, "Sync user response missing id or email"
        # Assume the API sets a session cookie on sync-user or returns token for authentication
        # Since auth is required for /api/me, check headers or cookies returned
        session_cookies = sync_resp.cookies  # Session cookie if any
        headers = {}
        cookies = session_cookies

        # Attempt GET /api/me with auth using the cookie received
        me_url = f"{BASE_URL}/api/me"
        auth_resp = requests.get(me_url, cookies=cookies, timeout=TIMEOUT)
        assert auth_resp.status_code == 200, f"Authenticated GET /api/me failed with status {auth_resp.status_code}"
        profile = auth_resp.json()
        # Validate profile contains expected user fields (at least email matches)
        assert "email" in profile, "User profile response missing email"
        assert profile["email"] == user_data["email"], "Returned profile email does not match synced user"

        # Attempt GET /api/me without any auth
        unauth_resp = requests.get(me_url, timeout=TIMEOUT)
        assert unauth_resp.status_code == 401, f"Unauthenticated GET /api/me expected 401 but got {unauth_resp.status_code}"

    finally:
        # Cleanup: delete the user if API provides delete - Not defined in PRD, so skipping
        pass


test_get_api_me_authenticated_and_unauthenticated()