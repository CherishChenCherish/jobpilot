import requests
import time

BASE_URL = "http://localhost:5001"
TIMEOUT = 30

# Helper function to sign in and get auth headers (simulate Google OAuth)
def get_auth_headers():
    """
    This function simulates obtaining an authenticated session.
    Currently, authentication simulation method is unsupported due to missing valid endpoint.
    """
    raise AssertionError("Authentication simulation unsupported: test environment must provide valid auth headers.")


def test_get_apigenerateclsstream():
    # Prepare auth headers and session
    try:
        auth_headers, session = get_auth_headers()
    except Exception as e:
        raise AssertionError(f"Auth setup failed: {e}")

    # Step 1: Obtain valid search_id and job_id by performing a search first
    # As no resource id is provided, create a new resource via search or other endpoints if needed
    # According to PRD and test instructions, likely job listings can be retrieved from /api/search
    # We must POST /api/search with required fields and auth to get a job_id and search_id
    search_url = f"{BASE_URL}/api/search"
    search_payload = {
        "direction": "Engineering",
        "region": "US",
        "degree": "Bachelor",
        "visa_needed": False
    }
    resp = session.post(search_url, json=search_payload, headers=auth_headers, timeout=TIMEOUT)
    assert resp.status_code == 200, f"/api/search responded with {resp.status_code}"
    search_results = resp.json()
    # The search response should contain a search_id and list of jobs.
    search_id = search_results.get("search_id")
    jobs = search_results.get("jobs", [])
    if not search_id or not jobs:
        # No jobs available (empty dev DB cache expected), skip stream test as no valid job_id
        raise AssertionError("No jobs available from /api/search to test cover letter generation streaming.")

    job_id = jobs[0].get("id")
    assert job_id is not None, "Job id missing in search results"

    # Step 2: Test GET /api/generate-cls/stream with auth and valid params
    stream_url = f"{BASE_URL}/api/generate-cls/stream"
    params = {
        "search_id": search_id,
        "job_id": job_id
    }

    # Make GET request with stream=True for SSE handling
    try:
        resp = session.get(stream_url, headers=auth_headers, params=params, stream=True, timeout=TIMEOUT)
    except requests.RequestException as e:
        raise AssertionError(f"Request to /api/generate-cls/stream failed: {e}")

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    content_type = resp.headers.get("Content-Type","")
    assert content_type.startswith("text/event-stream"), f"Expected Content-Type text/event-stream, got '{content_type}'"

    # Parse incremental tokens from the stream
    tokens = []
    # SSE sends data in chunks with "data:" prefix. Read line by line.
    try:
        for line in resp.iter_lines(decode_unicode=True, chunk_size=512):
            if line:
                line = line.strip()
                if line.startswith("data:"):
                    token = line[5:].strip()
                    if token:
                        tokens.append(token)
            # To avoid hanging test, limit read time or tokens count
            if len(tokens) >= 3:
                break
    finally:
        resp.close()

    assert len(tokens) > 0, "No tokens received from cover letter generation stream"

    # Step 3: Test GET /api/generate-cls/stream without auth returns 401
    unauth_session = requests.Session()
    resp_no_auth = unauth_session.get(stream_url, params=params, timeout=TIMEOUT)
    assert resp_no_auth.status_code == 401, f"Expected 401 Unauthorized without auth, got {resp_no_auth.status_code}"


test_get_apigenerateclsstream()
