import unittest
from unittest.mock import MagicMock, patch, call
from src.lawdigest_data_pipeline.DatabaseManager import DatabaseManager

class TestDatabaseManagerLawmaker(unittest.TestCase):
    def setUp(self):
        self.db_manager = DatabaseManager(host="fake", username="fake", password="fake", database="fake")
        # Mock connection and cursor
        self.db_manager.connection = MagicMock()
        self.cursor = MagicMock()
        self.db_manager.connection.cursor.return_value = self.cursor
        self.db_manager.connection.open = True

    def test_ensure_parties(self):
        """Test _ensure_parties handles existing and new parties"""
        party_names = {"Democratic", "Republican", "Green"}
        
        # Mock fetchall for existing parties (Democratic, Republican exist)
        self.cursor.fetchall.side_effect = [
            [{"party_id": 1, "name": "Democratic"}, {"party_id": 2, "name": "Republican"}], # First select
            [{"party_id": 3, "name": "Green"}] # Second select (after insert)
        ]
        
        result = self.db_manager._ensure_parties(self.cursor, party_names)
        
        # Check if insert was called for "Green"
        self.cursor.executemany.assert_called_once()
        args, _ = self.cursor.executemany.call_args
        self.assertIn("INSERT INTO Party", args[0])
        self.assertEqual(args[1], [("Green",)])
        
        # Check result map
        self.assertEqual(result["Democratic"], 1)
        self.assertEqual(result["Republican"], 2)
        self.assertEqual(result["Green"], 3)

    def test_update_lawmaker_info(self):
        """Test update_lawmaker_info handles upsert and disable logic"""
        # Input data
        lawmaker_data = [
            {"congressman_id": "C001", "name": "Alice", "party_name": "PartyA"}, # Existing, Update
            {"congressman_id": "C003", "name": "Charlie", "party_name": "PartyB"} # New, Insert
        ]
        
        # Mock transaction
        with patch.object(self.db_manager, 'transaction') as mock_transaction:
            mock_transaction.return_value.__enter__.return_value = self.cursor
            
            # Mock _ensure_parties
            with patch.object(self.db_manager, '_ensure_parties') as mock_ensure_parties:
                mock_ensure_parties.return_value = {"PartyA": 10, "PartyB": 20}
                
                # Mock existing lawmakers (C001, C002) -> C002 should be disabled
                self.cursor.fetchall.return_value = [{"congressman_id": "C001"}, {"congressman_id": "C002"}]
                
                self.db_manager.update_lawmaker_info(lawmaker_data)
                
                # Verify _ensure_parties called
                mock_ensure_parties.assert_called_once()
                
                # Verify Disable Query (C002)
                # Check for UPDATE Congressman SET state = 0
                update_calls = [c for c in self.cursor.execute.call_args_list if "UPDATE Congressman SET state = 0" in c[0][0]]
                self.assertTrue(update_calls)
                self.assertIn("C002", update_calls[0][0][1])
                
                # Verify Upsert Query (C001, C003)
                self.cursor.executemany.assert_called_once()
                args, _ = self.cursor.executemany.call_args
                query = args[0]
                params = args[1]
                
                self.assertIn("INSERT INTO Congressman", query)
                self.assertIn("ON DUPLICATE KEY UPDATE", query)
                self.assertEqual(len(params), 2)
                
                # Check IDs in params
                ids = {p['congressman_id'] for p in params}
                self.assertEqual(ids, {"C001", "C003"})
                # Check Party IDs
                party_ids = {p['party_id'] for p in params}
                self.assertEqual(party_ids, {10, 20})

    def test_update_bill_result(self):
        """Test update_bill_result updates Bill and BillTimeline tables"""
        # Input data
        result_data = [
            {"bill_id": "BILL_001", "bill_result": "원안가결"},
            {"bill_id": "BILL_002", "bill_result": "수정가결"}
        ]
        
        # Mock transaction
        with patch.object(self.db_manager, 'transaction') as mock_transaction:
            mock_transaction.return_value.__enter__.return_value = self.cursor
            
            self.db_manager.update_bill_result(result_data)
            
            # Verify specific calls exist
            bill_update_found = False
            timeline_update_found = False
            
            for call in self.cursor.executemany.call_args_list:
                args = call[0] # (query, params)
                query = args[0]
                params = args[1]
                
                if "UPDATE Bill SET bill_result" in query:
                    bill_update_found = True
                    self.assertEqual(len(params), 2)
                    self.assertEqual(params[0], ("원안가결", "BILL_001"))
                elif "UPDATE BillTimeline" in query:
                    timeline_update_found = True
                    self.assertIn("bill_timeline_stage = '본회의 심의'", query)
                    self.assertEqual(len(params), 2)
            
            self.assertTrue(bill_update_found, "Bill Update not found")
            self.assertTrue(timeline_update_found, "Timeline Update not found")

    def test_insert_vote_record(self):
        """Test insert_vote_record filters bills and upserts VoteRecord"""
        vote_data = [
            {"bill_id": "BILL_001", "votes_for_count": 100},
            {"bill_id": "BILL_MISSING", "votes_for_count": 0}
        ]
        
        with patch.object(self.db_manager, 'transaction') as mock_transaction:
            mock_transaction.return_value.__enter__.return_value = self.cursor
            
            # Mock get_existing_bill_ids
            with patch.object(self.db_manager, 'get_existing_bill_ids') as mock_get_bills:
                mock_get_bills.return_value = ["BILL_001"]
                
                self.db_manager.insert_vote_record(vote_data)
                
                self.cursor.executemany.assert_called_once()
                args = self.cursor.executemany.call_args[0]
                self.assertIn("INSERT INTO VoteRecord", args[0])
                self.assertEqual(len(args[1]), 1)
                self.assertEqual(args[1][0]['bill_id'], "BILL_001")

    def test_insert_vote_party(self):
        """Test insert_vote_party splits updates and inserts based on existence"""
        vote_party_data = [
            {"bill_id": "BILL_001", "party_name": "PartyA", "votes_for_count": 10}, # Existing -> Update
            {"bill_id": "BILL_001", "party_name": "PartyB", "votes_for_count": 5}   # Missing -> Insert
        ]
        
        with patch.object(self.db_manager, 'transaction') as mock_transaction:
            mock_transaction.return_value.__enter__.return_value = self.cursor
            
            with patch.object(self.db_manager, 'get_existing_bill_ids') as mock_get_bills, \
                 patch.object(self.db_manager, '_ensure_parties') as mock_ensure_parties:
                
                mock_get_bills.return_value = ["BILL_001"]
                mock_ensure_parties.return_value = {"PartyA": 1, "PartyB": 2}
                
                # Mock existence check: Only (BILL_001, PartyA) exists
                self.cursor.fetchall.return_value = [
                    {"vote_party_id": 999, "bill_id": "BILL_001", "party_id": 1}
                ]
                
                self.db_manager.insert_vote_party(vote_party_data)
                
                self.assertEqual(self.cursor.executemany.call_count, 2)
                
                insert_called = False
                update_called = False
                
                for call in self.cursor.executemany.call_args_list:
                    args = call[0]
                    query = args[0]
                    params = args[1]
                    
                    if "INSERT INTO VoteParty" in query:
                        insert_called = True
                        self.assertEqual(len(params), 1)
                        self.assertEqual(params[0]['party_id'], 2) # PartyB
                    elif "UPDATE VoteParty" in query:
                        update_called = True
                        self.assertEqual(len(params), 1)
                        self.assertEqual(params[0]['vote_party_id'], 999) # PartyA
                        
                self.assertTrue(insert_called, "Insert VoteParty not called")
                self.assertTrue(update_called, "Update VoteParty not called")

if __name__ == '__main__':
    unittest.main()
