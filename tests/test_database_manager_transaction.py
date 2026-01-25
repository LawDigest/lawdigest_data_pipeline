import pytest
from lawdigest_data_pipeline.DatabaseManager import DatabaseManager

@pytest.fixture(scope="module")
def db_manager():
    """DatabaseManager fixture for the module."""
    manager = DatabaseManager()
    if not manager.connection:
        pytest.skip("Database connection failed. Skipping database tests.")
    yield manager
    manager.close()

def test_transaction_commit(db_manager):
    """Test successful transaction commit."""
    # Setup: Create a temporary table
    create_table_query = """
    CREATE TEMPORARY TABLE IF NOT EXISTS test_transaction (
        id INT PRIMARY KEY,
        val VARCHAR(50)
    )
    """
    db_manager.execute_query(create_table_query)

    # Test Transaction
    with db_manager.transaction() as cursor:
        cursor.execute("INSERT INTO test_transaction (id, val) VALUES (%s, %s)", (1, "commit_test"))
    
    # Verify
    result = db_manager.execute_query("SELECT val FROM test_transaction WHERE id=1", fetch_one=True)
    assert result is not None
    assert result['val'] == "commit_test"

def test_transaction_rollback(db_manager):
    """Test transaction rollback on exception."""
    # Setup
    create_table_query = """
    CREATE TEMPORARY TABLE IF NOT EXISTS test_transaction (
        id INT PRIMARY KEY,
        val VARCHAR(50)
    )
    """
    db_manager.execute_query(create_table_query)

    # Test Rollback
    try:
        with db_manager.transaction() as cursor:
            cursor.execute("INSERT INTO test_transaction (id, val) VALUES (%s, %s)", (2, "rollback_test"))
            # Force error
            raise Exception("Force Rollback")
    except Exception:
        pass
    
    # Verify data does NOT exist
    result = db_manager.execute_query("SELECT val FROM test_transaction WHERE id=2", fetch_one=True)
    assert result is None

def test_execute_batch(db_manager):
    """Test execute_batch method."""
    create_table_query = """
    CREATE TEMPORARY TABLE IF NOT EXISTS test_batch (
        id INT,
        val VARCHAR(50)
    )
    """
    db_manager.execute_query(create_table_query)

    data = [(1, "batch1"), (2, "batch2"), (3, "batch3")]
    query = "INSERT INTO test_batch (id, val) VALUES (%s, %s)"
    
    db_manager.execute_batch(query, data)

    result = db_manager.execute_query("SELECT COUNT(*) as cnt FROM test_batch", fetch_one=True)
    assert result['cnt'] == 3
