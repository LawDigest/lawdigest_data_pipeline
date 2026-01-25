import sys
import os
import unittest
from unittest.mock import MagicMock, call
import pymysql

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.lawdigest_data_pipeline.DatabaseManager import DatabaseManager

class TestDatabaseManagerStatistics(unittest.TestCase):
    def setUp(self):
        self.db_manager = DatabaseManager()
        self.mock_conn = MagicMock(spec=pymysql.connections.Connection)
        self.mock_cursor = MagicMock(spec=pymysql.cursors.DictCursor)
        self.db_manager.connection = self.mock_conn
        self.mock_conn.cursor.return_value = self.mock_cursor

    def test_update_party_statistics(self):
        # Mocking return values for each count query
        # 1. District counts
        self.mock_cursor.fetchall.side_effect = [
            [{'party_id': 1, 'count': 10}, {'party_id': 2, 'count': 5}], # District
            [{'party_id': 1, 'count': 2}, {'party_id': 2, 'count': 3}],  # Proportional
            [{'party_id': 1, 'count': 50}, {'party_id': 2, 'count': 30}], # Representative Bill
            [{'party_id': 1, 'count': 100}, {'party_id': 2, 'count': 50}] # Public Bill
        ]

        self.db_manager.update_party_statistics()

        # Verify executing 4 SELECT queries
        self.assertEqual(self.mock_cursor.execute.call_count, 4)
        
        # Verify batch update called once
        self.mock_cursor.executemany.assert_called_once()
        
        call_args = self.mock_cursor.executemany.call_args
        query, params = call_args[0]
        
        self.assertIn("UPDATE Party", query)
        self.assertEqual(len(params), 2)
        
        # Verify params for party 1
        party1_update = next(p for p in params if p['party_id'] == 1)
        self.assertEqual(party1_update['district_count'], 10)
        self.assertEqual(party1_update['proportional_count'], 2)
        self.assertEqual(party1_update['rep_bill_count'], 50)
        self.assertEqual(party1_update['pub_bill_count'], 100)

    def test_update_congressman_statistics(self):
        # Mocking return values
        self.mock_cursor.fetchall.return_value = [
            {'congressman_id': 'cm1', 'last_propose_date': '2024-01-01'},
            {'congressman_id': 'cm2', 'last_propose_date': '2023-12-31'}
        ]
        
        self.db_manager.update_congressman_statistics()
        
        # Verify SELECT query
        self.mock_cursor.execute.assert_called_once()
        
        # Verify batch update
        self.mock_cursor.executemany.assert_called_once()
        
        call_args = self.mock_cursor.executemany.call_args
        query, params = call_args[0]
        
        self.assertIn("UPDATE Congressman", query)
        self.assertEqual(len(params), 2)
        self.assertEqual(params[0]['congressman_id'], 'cm1')
        self.assertEqual(params[0]['last_date'], '2024-01-01')

if __name__ == '__main__':
    unittest.main()
