import requests

BASE_URL = "http://localhost:5001"
TIMEOUT = 30

def test_get_apime_authenticated_user_profile():
    """
    Test GET /api/me endpoint:
    - with valid authentication returns 200 with full user profile
    - without authentication returns 401 Unauthorized
    """

    # Step 1: Create a user by syncing via /api/sync-user (no auth required)
    sync_user_url = f"{BASE_URL}/api/sync-user"
    user_data = {
        "email": "testuser@example.com",
        "name": "Test User",
        "image": "https://example.com/avatar.png"
    }
    try:
        resp_sync = requests.post(sync_user_url, json=user_data, timeout=TIMEOUT)
        assert resp_sync.status_code == 200, f"Sync user failed with status {resp_sync.status_code}"
        user_resp = resp_sync.json()
        assert "id" in user_resp and "email" in user_resp
        user_id = user_resp["id"]

        # Normally auth token or session cookie is needed.
        # Since the PRD doesn't specify auth mechanism,
        # assume the API issues a session cookie or auth token on sync-user or login.
        # Since sync-user has no auth, assume it may not set cookie; we simulate auth by fetching a token.
        # The PRD doesn't mention login or token endpoint.
        # For test, assume that sync-user returns a Set-Cookie or token in header or body.
        # No explicit token given, so we try to use the session cookie from the sync-user request if set.
        # Otherwise, we simulate a Bearer token header with email as token (common in test).
        session_cookies = resp_sync.cookies

        headers_auth = {}
        if session_cookies:
            # Use session cookie for auth
            headers_auth["Cookie"] = "; ".join([f"{c.name}={c.value}" for c in session_cookies])
        else:
            # Fallback: use Authorization header with fake token matching email, as no real auth provided
            headers_auth["Authorization"] = f"Bearer {user_data['email']}"

        # Step 2: Access /api/me with auth
        me_url = f"{BASE_URL}/api/me"
        resp_auth = requests.get(me_url, headers=headers_auth, timeout=TIMEOUT)
        assert resp_auth.status_code == 200, f"Authenticated /api/me returned status {resp_auth.status_code}"
        profile = resp_auth.json()
        # Check that profile contains expected keys: id, email, name, possibly image (user model)
        assert profile.get("email") == user_data["email"], "Email mismatch in user profile"
        assert "id" in profile and profile["id"] == user_id, "User ID mismatch in profile"
        assert "name" in profile and profile["name"] == user_data["name"], "Name mismatch in user profile"

        # Step 3: Access /api/me without auth
        resp_no_auth = requests.get(me_url, timeout=TIMEOUT)
        assert resp_no_auth.status_code == 401, f"Unauthorized /api/me returned status {resp_no_auth.status_code}"

    finally:
        # Cleanup user resource if API supported delete - no delete user endpoint documented, so skip cleanup
        pass

test_get_apime_authenticated_user_profile()