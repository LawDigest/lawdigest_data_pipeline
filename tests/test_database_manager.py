import pytest
import sys
import os
from lawdigest_data_pipeline.DatabaseManager import DatabaseManager

@pytest.fixture(scope="module")
def db_manager():
    """DatabaseManager fixture for the module."""
    manager = DatabaseManager()
    if not manager.connection:
        pytest.skip("Database connection failed. Skipping database tests.")
    yield manager
    manager.close()

def test_connection_success(db_manager):
    """Test that the database connection is established."""
    assert db_manager.connection is not None
    print(f"\nConnection successful: {db_manager.host}:{db_manager.port}")

def test_fetch_latest_bills(db_manager):
    """Test fetching the latest 5 bills."""
    query = "SELECT * FROM Bill ORDER BY propose_date DESC LIMIT 5;"
    results = db_manager.execute_query(query)
    
    assert results is not None
    assert isinstance(results, list)
    
    if results:
        print(f"\nFetched {len(results)} bills.")
        first_bill = results[0]
        assert isinstance(first_bill, dict)
        # Verify basic structure if data exists
        # We expect keys like 'bill_id' or 'propose_date' based on the query
        # Just printing keys for verification
        print(f"Bill keys: {first_bill.keys()}")
    else:
        print("\nNo bills found in the database.")

def test_execute_simple_query(db_manager):
    """Test executing a simple SELECT 1 query."""
    result = db_manager.execute_query("SELECT 1 as val", fetch_one=True)
    assert result is not None
    assert result['val'] == 1
