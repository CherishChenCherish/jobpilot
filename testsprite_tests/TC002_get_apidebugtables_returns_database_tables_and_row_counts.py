import requests

def test_get_apidebugtables_returns_tables_and_row_counts():
    base_url = "http://localhost:5000"
    url = f"{base_url}/api/debug/tables"
    headers = {
        "Accept": "application/json"
    }
    try:
        response = requests.get(url, headers=headers, timeout=30)
        # Validate response status
        assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
        json_data = response.json()
        # Validate 'tables' key exists and is a dict
        assert "tables" in json_data, "'tables' key missing in response JSON"
        assert isinstance(json_data["tables"], dict), "'tables' is not an object/dictionary"
        # Each key-value pair in tables should have string key and a numeric row count
        for table_name, row_count in json_data["tables"].items():
            assert isinstance(table_name, str), "Table name is not a string"
            assert (isinstance(row_count, int) or isinstance(row_count, float)), f"Row count for table '{table_name}' is not numeric"
            assert row_count >= 0, f"Row count for table '{table_name}' is negative"
    except requests.RequestException as e:
        assert False, f"HTTP request failed: {e}"
    except ValueError as e:
        assert False, f"Response JSON decoding failed: {e}"

test_get_apidebugtables_returns_tables_and_row_counts()