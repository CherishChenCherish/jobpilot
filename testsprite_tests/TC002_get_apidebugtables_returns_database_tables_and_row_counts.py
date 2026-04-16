import requests

BASE_URL = "http://localhost:5001"
TIMEOUT = 30

def test_get_apidebugtables_returns_database_tables_and_row_counts():
    url = f"{BASE_URL}/api/debug/tables"
    try:
        response = requests.get(url, timeout=TIMEOUT)
    except requests.RequestException as e:
        assert False, f"Request failed: {e}"

    assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"

    try:
        data = response.json()
    except ValueError:
        assert False, "Response is not valid JSON"

    assert "tables" in data, "'tables' key not found in response JSON"
    assert isinstance(data["tables"], dict), "'tables' is not an object/dict"

    # Optionally verify that row counts are integers if present
    for table_name, row_count in data["tables"].items():
        assert isinstance(table_name, str), "Table name is not a string"
        assert isinstance(row_count, int), f"Row count for table '{table_name}' is not an integer"

test_get_apidebugtables_returns_database_tables_and_row_counts()