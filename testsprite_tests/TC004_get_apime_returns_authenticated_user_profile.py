import requests

BASE_URL = "http://localhost:5001"
TIMEOUT = 30

def test_get_apime_authenticated_and_unauthenticated():
    """
    Verify GET /api/me with valid auth returns 200 with full user profile,
    and without auth returns 401 unauthorized.
    """

    url = f"{BASE_URL}/api/me"

    # 1. Without auth, no google_id param - should return 401 Unauthorized
    try:
        resp_unauth = requests.get(url, timeout=TIMEOUT)
    except requests.RequestException as e:
        assert False, f"Request without auth failed unexpectedly: {e}"
    assert resp_unauth.status_code == 401, f"Expected 401 without auth but got {resp_unauth.status_code}"

    # 2. With auth - valid google_id param - expect 200 and full user profile
    # Since no auth mechanism or token is described, and the API fixes mention google_id param is required,
    # pass google_id as query parameter to simulate auth.
    # Assuming 'test-google-id-12345' is a valid google_id for test.
    params = {"google_id": "test-google-id-12345"}

    try:
        resp_auth = requests.get(url, params=params, timeout=TIMEOUT)
    except requests.RequestException as e:
        assert False, f"Request with auth failed unexpectedly: {e}"

    assert resp_auth.status_code == 200, f"Expected 200 with auth but got {resp_auth.status_code}"

    # Validate response content: full user profile expected JSON keys (based on standard user profile fields)
    try:
        profile = resp_auth.json()
    except ValueError:
        assert False, "Response is not valid JSON."

    # Minimum fields commonly expected in user profile for this product:
    expected_fields = {"id", "email", "name", "region", "degree", "direction", "visa_needs", "image"}
    missing_fields = expected_fields - profile.keys()
    assert not missing_fields, f"Missing expected profile fields: {missing_fields}"

test_get_apime_authenticated_and_unauthenticated()