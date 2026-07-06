#!/usr/bin/env python3
"""
Test script to verify the API works with extract_load.py logic
"""
import requests
import json

def test_api():
    """Test that the API returns data in the expected format"""
    try:
        # Test the endpoint
        response = requests.get("http://localhost:8000/transactions", timeout=5)
        response.raise_for_status()

        data = response.json()

        # Verify we got a list
        assert isinstance(data, list), "Expected a list of transactions"
        assert len(data) > 0, "Expected at least one transaction"

        # Verify first item has required fields
        first_item = data[0]
        assert "id" in first_item, "Missing 'id' field"
        assert "date" in first_item, "Missing 'date' field"
        assert "amount" in first_item, "Missing 'amount' field"

        # Verify types
        assert isinstance(first_item["id"], str), "id should be string"
        assert isinstance(first_item["date"], str), "date should be string"
        assert isinstance(first_item["amount"], (int, float)), "amount should be numeric"

        # Verify date format (YYYY-MM-DD)
        date_parts = first_item["date"].split("-")
        assert len(date_parts) == 3, "Date should have YYYY-MM-DD format"
        assert len(date_parts[0]) == 4, "Year should be 4 digits"
        assert len(date_parts[1]) == 2, "Month should be 2 digits"
        assert len(date_parts[2]) == 2, "Day should be 2 digits"

        print(f"✓ API test passed! Received {len(data)} transactions")
        print(f"  First transaction: {first_item}")

        # Test that we can simulate the extract_load.py logic
        print("\n✓ Simulating extract_load.py logic:")
        for i, row in enumerate(data[:3]):  # Just test first 3 rows
            print(f"  Row {i+1}: id={row['id']}, date={row['date']}, amount={row['amount']}")

        return True

    except requests.exceptions.RequestException as e:
        print(f"✗ Failed to connect to API: {e}")
        return False
    except (json.JSONDecodeError, AssertionError) as e:
        print(f"✗ Invalid response format: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    test_api()