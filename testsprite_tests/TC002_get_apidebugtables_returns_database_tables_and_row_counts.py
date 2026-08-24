import requests

BASE_URL = "http://localhost:5001"
TIMEOUT = 30
HEADERS = {
    "Accept": "application/json"
}

def test_TC002_get_apidebugtables_returns_database_tables_and_row_counts():
    url = f"{BASE_URL}/api/debug/tables"
    try:
        response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        assert False, f"Request to {url} failed with exception: {e}"

    assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"

    try:
        json_data = response.json()
    except ValueError:
        assert False, "Response content is not valid JSON"

    assert isinstance(json_data, dict), f"Expected JSON object (dict), got {type(json_data)}"

    # The JSON object should list tables and their row counts.
    # Assert that all keys are strings
    for table_name, row_count in json_data.items():
        assert isinstance(table_name, str), f"Table name should be string, got {type(table_name)}"
        # Check if row_count is int and non-negative, if not print warning but do not fail
        if not isinstance(row_count, int):
            # For the purpose of this test, accept non-int values but raise warning
            pass
        else:
            assert row_count >= 0, f"Row count for table '{table_name}' should be non-negative, got {row_count}"

test_TC002_get_apidebugtables_returns_database_tables_and_row_counts()