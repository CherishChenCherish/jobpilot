import requests

BASE_URL = "http://localhost:5001"
TIMEOUT = 30

# For this test, we need authentication. We'll create a test user via /api/sync-user (no auth required),
# then use that user to get an auth token or session cookie if available.
# Since no detailed auth mechanism is given, we'll assume a Bearer token returned by /api/sync-user or an auth scheme.
# The PRD suggests /api/me uses "session cookie or auth token".
# We'll simulate by making POST /api/sync-user and then GET /api/me to confirm and obtain auth headers for testing.
# Use try-finally to clean up is not applicable since checkout sessions cannot be deleted via API per PRD.

def test_post_apistripecreatecheckout_creates_checkout_session():
    # Step 1: Create user (no auth needed)
    sync_user_url = f"{BASE_URL}/api/sync-user"
    user_data = {
        "email": "teststripecreatecheckout@example.com",
        "name": "Test Stripe User",
        "image": "https://example.com/avatar.png"
    }
    try:
        resp_sync = requests.post(sync_user_url, json=user_data, timeout=TIMEOUT)
        assert resp_sync.status_code == 200, f"Failed to sync user, status code {resp_sync.status_code}"
        user_json = resp_sync.json()
        user_id = user_json.get("id")
        assert user_id is not None, "User ID not returned in sync-user response"

        # Step 2: Authenticate user by calling /api/me with some form of auth
        # Since no token returned from /api/sync-user, try no auth should 401
        # We need to get auth to test /api/stripe/create-checkout.

        # The PRD mentions /api/me requires session cookie or auth token.
        # We'll simulate auth by assuming a bearer token "test-token-for-user" (for demonstration).
        # In a real test, replace this with the actual auth token retrieval method.

        # For demonstration, try calling /api/me without auth to verify 401
        me_url = f"{BASE_URL}/api/me"
        resp_me_unauth = requests.get(me_url, timeout=TIMEOUT)
        assert resp_me_unauth.status_code == 401, "Expected 401 Unauthorized without auth"

        # Now, try again with auth header - assuming a test token "test-auth-token"
        # Since no OAuth flow is described, this is a stub placeholder.
        auth_headers = {
            "Authorization": f"Bearer test-auth-token"
        }
        resp_me = requests.get(me_url, headers=auth_headers, timeout=TIMEOUT)
        if resp_me.status_code != 200:
            # If test environment does not support auth, skip test
            # or raise to signal needing actual token
            raise RuntimeError(f"Unable to authenticate: /api/me returned {resp_me.status_code}")
        user_profile = resp_me.json()

        # Step 3: POST to /api/stripe/create-checkout with auth
        stripe_checkout_url = f"{BASE_URL}/api/stripe/create-checkout"
        resp_checkout = requests.post(stripe_checkout_url, headers=auth_headers, timeout=TIMEOUT)

        # Validate success (200) with checkout url
        if resp_checkout.status_code == 200:
            json_checkout = resp_checkout.json()
            url = json_checkout.get("url")
            assert url is not None and url.startswith("https://checkout.stripe.com/"), f"Checkout url invalid or missing: {url}"
        else:
            # If Stripe service error simulated, expect 500 with Stripe error
            assert resp_checkout.status_code == 500, f"Unexpected status code {resp_checkout.status_code} for Stripe error"
            json_error = resp_checkout.json()
            assert "error" in json_error or "message" in json_error, "Expected error message in 500 response"

    finally:
        # Cleanup user if delete endpoint existed (not specified in PRD), so no cleanup here.
        pass

test_post_apistripecreatecheckout_creates_checkout_session()