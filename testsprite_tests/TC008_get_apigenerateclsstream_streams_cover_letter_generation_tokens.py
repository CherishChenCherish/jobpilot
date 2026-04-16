import requests

BASE_URL = "http://localhost:5001"
TIMEOUT = 30


def test_get_api_generate_cls_stream():
    # First, we need a valid auth token, search_id, and job_id.
    # Since the test description requires auth, we should create a user, perform a search to get search_id, job_id.
    # We'll do minimal setup: sync user, do a search with auth, then stream with auth and without auth.
    # Clean up is not needed here as these are just API calls with no persistent side-effects for this test case.

    try:
        # Step 1: Sync user to get auth - POST /api/sync-user
        user_payload = {
            "email": "testuser@example.com",
            "name": "Test User",
            "image": "https://example.com/avatar.png"
        }
        sync_resp = requests.post(
            f"{BASE_URL}/api/sync-user", json=user_payload, timeout=TIMEOUT
        )
        assert sync_resp.status_code == 200, f"Sync user failed: {sync_resp.text}"
        user_data = sync_resp.json()
        assert "id" in user_data and "email" in user_data, "Invalid user sync response"

        # Step 2: Get auth token by simulating login (GET /api/me requires auth)
        # Assuming auth token is session cookie or bearer token in real scenario.
        # However, no auth endpoint provided for token generation.
        # Since no explicit auth token generation endpoint exists, we assume the user sync gives a cookie or header.
        # We'll assume the server uses cookies and the sync-user sets session cookie.
        session = requests.Session()
        session.cookies.update(sync_resp.cookies)

        # Step 3: Perform a job search to get search_id and job_id
        search_payload = {
            "direction": "Software",
            "region": "US",
            "degree": "MS",
            "visa_needed": False
        }
        search_resp = session.post(
            f"{BASE_URL}/api/search", json=search_payload, timeout=TIMEOUT
        )
        assert search_resp.status_code == 200, f"Job search failed: {search_resp.text}"
        search_data = search_resp.json()
        assert "search_id" in search_data and "jobs" in search_data, "Invalid search response"
        assert isinstance(search_data["jobs"], list) and len(search_data["jobs"]) > 0, "No jobs found"

        search_id = search_data["search_id"]
        # Pick first job_id from job list
        job_id = search_data["jobs"][0].get("id") or search_data["jobs"][0].get("job_id")
        assert job_id is not None, "Job ID missing in search results"

        # Step 4: Test GET /api/generate-cls/stream with auth and valid search_id, job_id
        params = {"search_id": search_id, "job_id": job_id}
        stream_headers = {
            "Accept": "text/event-stream"
        }
        stream_resp = session.get(
            f"{BASE_URL}/api/generate-cls/stream",
            params=params,
            headers=stream_headers,
            timeout=TIMEOUT,
            stream=True,
        )
        assert stream_resp.status_code == 200, f"Stream request failed with auth: {stream_resp.text}"
        assert stream_resp.headers.get("Content-Type", "").startswith("text/event-stream"), \
            f"Expected text/event-stream Content-Type, got: {stream_resp.headers.get('Content-Type')}"

        # Read at least some tokens from the stream incrementally
        tokens_received = 0
        for line in stream_resp.iter_lines(decode_unicode=True, chunk_size=1024):
            if line.strip() == "":
                continue
            if line.startswith("data:"):
                tokens_received += 1
            if tokens_received >= 3:
                break
        assert tokens_received > 0, "No tokens received from stream"

        # Step 5: Test GET /api/generate-cls/stream without auth returns 401
        no_auth_resp = requests.get(
            f"{BASE_URL}/api/generate-cls/stream",
            params=params,
            headers=stream_headers,
            timeout=TIMEOUT,
            stream=True,
        )
        assert no_auth_resp.status_code == 401, f"Expected 401 without auth, got {no_auth_resp.status_code}"

    except requests.RequestException as e:
        assert False, f"Request failed: {e}"


test_get_api_generate_cls_stream()