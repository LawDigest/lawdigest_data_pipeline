
import unittest
import os
from dotenv import load_dotenv
import sys

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from lawdigest_data_pipeline.DatabaseManager import DatabaseManager

class TestIntegrationPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        load_dotenv()
        cls.host = os.environ.get("TEST_DB_HOST")
        cls.port = int(os.environ.get("TEST_DB_PORT", 3306))
        cls.user = os.environ.get("TEST_DB_USER")
        cls.password = os.environ.get("TEST_DB_PASSWORD")
        cls.database = os.environ.get("TEST_DB_NAME")
        
        if not all([cls.host, cls.port, cls.user, cls.password, cls.database]):
            raise  unittest.SkipTest("Test database credentials not found in .env")

        cls.db_manager = DatabaseManager(
            host=cls.host,
            port=cls.port,
            username=cls.user,
            password=cls.password,
            database=cls.database
        )
        
        # Verify connection
        if not cls.db_manager.connection:
             raise Exception("Failed to connect to Test Database")
        
        print(f"\n[Setup] Connected to Test DB: {cls.database} at {cls.host}:{cls.port}")
        
        # Schema Fix: Party.party_id should be AUTO_INCREMENT
        # This is required for _ensure_parties to work
        try:
            with cls.db_manager.transaction() as cursor:
                cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
                cursor.execute("ALTER TABLE Party MODIFY COLUMN party_id BIGINT AUTO_INCREMENT")
                cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
            print("[Setup] Applied Schema Fix: Party.party_id -> AUTO_INCREMENT")
        except Exception as e:
            print(f"[Setup] Schema Fix skipped or failed: {e}")

    def setUp(self):
        # Clean up tables before each test to ensure isolation
        # Order matters due to Foreign Keys
        tables_to_clean = [
            "VoteRecord", "VoteParty", "BillTimeline", "BillProposer", "RepresentativeProposer",
            "Bill", "Congressman", "Party"
        ]
        with self.db_manager.transaction() as cursor:
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
            for table in tables_to_clean:
                cursor.execute(f"TRUNCATE TABLE {table}")
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1")

    def test_pipeline_scenario(self):
        """
        End-to-End Scenario:
        1. Lawmaker Sync (Insert & Update)
        2. Bill Sync (Insert)
        3. Stage & Result Update
        4. Vote Sync
        5. Statistics Aggregation
        """
        
        # 1. Lawmaker Data Preparation
        # Party A: 2 Members (1 District, 1 Proportional)
        # Party B: 1 Member (District)
        lawmaker_data = [
            {
                "congressman_id": "CM001", "name": "의원1", "party_name": "정당A", 
                "district": "서울", "elect_sort": "지역구", "elected": "재선"
            },
            {
                "congressman_id": "CM002", "name": "의원2", "party_name": "정당A", 
                "district": "비례", "elect_sort": "비례대표", "elected": "초선"
            },
            {
                "congressman_id": "CM003", "name": "의원3", "party_name": "정당B", 
                "district": "부산", "elect_sort": "지역구", "elected": "3선"
            }
        ]
        
        print("\n[Step 1] Syncing Lawmakers...")
        self.db_manager.update_lawmaker_info(lawmaker_data)
        
        # Verify Lawmakers
        with self.db_manager.transaction() as cursor:
            cursor.execute("SELECT COUNT(*) as count FROM Congressman WHERE state=1")
            self.assertEqual(cursor.fetchone()['count'], 3)
            
            cursor.execute("SELECT COUNT(*) as count FROM Party")
            self.assertEqual(cursor.fetchone()['count'], 2) # Party A, Party B created

        # 2. Bill Data Preparation
        # Bill 1: Rep(CM001), Public(CM002) - Party A Only
        # Bill 2: Rep(CM003), Public(CM001) - Mixed Parties
        import datetime
        today = datetime.date.today().strftime('%Y-%m-%d')
        
        bill_data = [
            {
                "bill_id": "BILL001", "bill_name": "법안1", "propose_date": today,
                "committee": "법사위", "stage": "접수", "proposer_kind": "CONGRESSMAN",
                "rst_proposer_ids": ["CM001"], "public_proposer_ids": ["CM002"],
                "summary": "내용1", "gpt_summary": "요약1", "bill_pdf_url": "url1", "brief_summary": "짧은요약1", "bill_number": "001", "bill_link": "link1", "bill_result": None,
                "proposers": "의원1 외 1인"
            },
             {
                "bill_id": "BILL002", "bill_name": "법안2", "propose_date": "2024-01-01",
                "committee": "정무위", "stage": "위원회 심사", "proposer_kind": "CONGRESSMAN",
                "rst_proposer_ids": ["CM003"], "public_proposer_ids": ["CM001"],
                "summary": "내용2", "gpt_summary": "요약2", "bill_pdf_url": "url2", "brief_summary": "짧은요약2", "bill_number": "002", "bill_link": "link2", "bill_result": None,
                "proposers": "의원3 외 1인"
            }
        ]

        print("[Step 2] Inserting Bills...")
        self.db_manager.insert_bill_info(bill_data)
        
        # Verify Bills
        with self.db_manager.transaction() as cursor:
            cursor.execute("SELECT COUNT(*) as count FROM Bill")
            self.assertEqual(cursor.fetchone()['count'], 2)
            
            # Check Proposers
            cursor.execute("SELECT COUNT(*) as count FROM RepresentativeProposer")
            self.assertEqual(cursor.fetchone()['count'], 2)
             
            cursor.execute("SELECT COUNT(*) as count FROM BillProposer")
            self.assertEqual(cursor.fetchone()['count'], 2)

        # 3. Stage & Result Update
        stage_data = [
            {"bill_id": "BILL001", "stage": "본회의 심의", "status_update_date": today, "committee": "법사위"}
        ]
        
        print("[Step 3] Updating Bill Stage...")
        result = self.db_manager.update_bill_stage(stage_data)
        self.assertEqual(len(result['not_found_bill']), 0)
        
        # Result Update
        result_data = [
            {"bill_id": "BILL001", "bill_result": "원안가결"}
        ]
        print("          Updating Bill Result...")
        self.db_manager.update_bill_result(result_data)
        
        # Verify Stage & Result
        with self.db_manager.transaction() as cursor:
            cursor.execute("SELECT stage, bill_result FROM Bill WHERE bill_id='BILL001'")
            row = cursor.fetchone()
            self.assertEqual(row['stage'], "본회의 심의")
            self.assertEqual(row['bill_result'], "원안가결")
            
            cursor.execute("SELECT * FROM BillTimeline WHERE bill_id='BILL001'")
            timelines = cursor.fetchall()
            self.assertTrue(len(timelines) >= 1)
            # Find the one we inserted
            found = False
            for t in timelines:
                if t['bill_timeline_stage'] == "본회의 심의" and t['bill_result'] == "원안가결":
                    found = True
            self.assertTrue(found)

        # 4. Vote Data
        vote_data = [
            {
                "bill_id": "BILL001", 
                "votes_for_count": 100, "votes_againt_count": 50, "abstention_count": 10, "total_vote_count": 160
            }
        ]
        vote_party_data = [
            {"bill_id": "BILL001", "party_name": "정당A", "votes_for_count": 80},
            {"bill_id": "BILL001", "party_name": "정당B", "votes_for_count": 20}
        ]
        
        print("[Step 4] Inserting Vote Records...")
        self.db_manager.insert_vote_record(vote_data)
        self.db_manager.insert_vote_party(vote_party_data)
        
        # Verify Votes
        with self.db_manager.transaction() as cursor:
            cursor.execute("SELECT * FROM VoteRecord WHERE bill_id='BILL001'")
            self.assertIsNotNone(cursor.fetchone())
            
            cursor.execute("SELECT COUNT(*) as count FROM VoteParty WHERE bill_id='BILL001'")
            self.assertEqual(cursor.fetchone()['count'], 2)

        # 5. Statistics
        print("[Step 5] Aggregating Statistics...")
        self.db_manager.update_party_statistics()
        self.db_manager.update_congressman_statistics()
        
        # Verify Statistics
        with self.db_manager.transaction() as cursor:
            # Party Stats
            # 정당A: 지역구1, 비례1, 대표법안1(BILL001-CM001), 공동법안1(BILL002-CM001)
            # 정당B: 지역구1, 비례0, 대표법안1(BILL002-CM003), 공동법안1(BILL001-CM002 is PartyA?? Wait Bill1 public is CM02(PartyA))
            # Let's trace carefully:
            # CM001(PartyA) -> Rep: BILL001, Pub: BILL002
            # CM002(PartyA) -> Rep: None, Pub: BILL001
            # CM003(PartyB) -> Rep: BILL002, Pub: None
            
            # Party A Stats:
            # district_congressman_count = 1 (CM001)
            # proportional_congressman_count = 1 (CM002)
            # representative_bill_count = 1 (CM001)
            # public_bill_count = 1 (CM001) + 1 (CM002) = 2
            
            # Party B Stats:
            # district_congressman_count = 1 (CM003)
            # representative_bill_count = 1 (CM003)
            
            cursor.execute("SELECT * FROM Party WHERE name='정당A'")
            party_a = cursor.fetchone()
            self.assertEqual(party_a['district_congressman_count'], 1)
            self.assertEqual(party_a['proportional_congressman_count'], 1)
            self.assertEqual(party_a['representative_bill_count'], 1)
            self.assertEqual(party_a['public_bill_count'], 2)
            
            # Congressman Stats
            # CM001 latest propose date -> Bill 1 date (today) or Bill 2 (2024-01-01) -> NO, CM01 is Rep for Bill 1 only.
            # CM001 Rep date = today
            # CM003 Rep date = 2024-01-01
            
            cursor.execute("SELECT congressman_bill_propose_date FROM Congressman WHERE congressman_id='CM001'")
            # Depending on DB type, date might come as date object or string
            row = cursor.fetchone()
            # print(f"DEBUG: CM001 Propose Date: {row['congressman_bill_propose_date']} Type: {type(row['congressman_bill_propose_date'])}")
            
            # Compare as string
            self.assertEqual(str(row['congressman_bill_propose_date']), today)
            
            cursor.execute("SELECT congressman_bill_propose_date FROM Congressman WHERE congressman_id='CM003'")
            row = cursor.fetchone()
            self.assertEqual(str(row['congressman_bill_propose_date']), "2024-01-01")

        print("\n✅ All Integration Tests Passed!")

if __name__ == '__main__':
    unittest.main()
