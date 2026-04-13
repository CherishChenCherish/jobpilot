import requests

BASE_URL = "http://localhost:5000"
TIMEOUT = 30

# Replace this with a valid auth token string (without 'Bearer ' prefix)
AUTH_TOKEN = "your_valid_auth_token_here"

def test_get_generate_cls_stream():
    headers_with_auth = {
        "Authorization": f"Bearer {AUTH_TOKEN}",
        "Accept": "text/event-stream"
    }
    headers_without_auth = {
        "Accept": "text/event-stream"
    }

    try:
        # Step 1: POST /api/search with valid params and auth
        search_payload = {
            "direction": "Software",
            "region": "US",
            "degree": "MS",
            "visa_needed": False
        }
        search_response = requests.post(
            f"{BASE_URL}/api/search",
            json=search_payload,
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
            timeout=TIMEOUT
        )
        assert search_response.status_code == 200, f"Expected 200 for /api/search but got {search_response.status_code}"
        search_data = search_response.json()
        assert "search_id" in search_data, "search_id missing in search response"
        assert "jobs" in search_data and isinstance(search_data["jobs"], list) and len(search_data["jobs"]) > 0, "Jobs list missing or empty in search response"

        search_id = search_data["search_id"]
        job_id = search_data["jobs"][0].get("id") or search_data["jobs"][0].get("job_id")
        assert isinstance(job_id, int), "job_id not found or invalid in jobs list"

        # Step 2: GET /api/generate-cls/stream with valid auth and params
        params = {
            "search_id": search_id,
            "job_id": job_id
        }
        stream_response = requests.get(
            f"{BASE_URL}/api/generate-cls/stream",
            headers=headers_with_auth,
            params=params,
            timeout=TIMEOUT,
            stream=True
        )
        assert stream_response.status_code == 200, f"Expected 200 for streaming endpoint but got {stream_response.status_code}"
        content_type = stream_response.headers.get("Content-Type", "")
        assert "text/event-stream" in content_type, f"Expected Content-Type 'text/event-stream' but got '{content_type}'"

        token_chunks = []
        for line in stream_response.iter_lines(decode_unicode=True):
            if line.strip():
                token_chunks.append(line.strip())
            if len(token_chunks) >= 3:
                break
        assert len(token_chunks) >= 1, "No tokens received in event stream."

        # Step 3: GET /api/generate-cls/stream without auth -> should get 401
        response_no_auth = requests.get(
            f"{BASE_URL}/api/generate-cls/stream",
            headers=headers_without_auth,
            params=params,
            timeout=TIMEOUT
        )
        assert response_no_auth.status_code == 401, f"Expected 401 Unauthorized without auth but got {response_no_auth.status_code}"

    except requests.RequestException as e:
        assert False, f"Request failed: {e}"


test_get_generate_cls_stream()
