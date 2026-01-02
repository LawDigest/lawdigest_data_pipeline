from dotenv import load_dotenv
import os
import pymysql
import contextlib 
from typing import List, Tuple, Dict, Any, Optional, Generator, Set

class DatabaseManager:
    """MySQL RDS 연결 및 데이터베이스 관련 기능을 제공하는 클래스"""

    def __init__(self, host: Optional[str] = None, port: Optional[int] = None, username: Optional[str] = None, password: Optional[str] = None, database: Optional[str] = None):
        """
        DatabaseManager 클래스 초기화.

        Args:
            host (str, optional): 데이터베이스 서버 주소. (기본값: 환경 변수 `host`)
            port (int, optional): 데이터베이스 포트. (기본값: 환경 변수 `port` or 3306)
            username (str, optional): 데이터베이스 사용자명. (기본값: 환경 변수 `username`)
            password (str, optional): 데이터베이스 비밀번호. (기본값: 환경 변수 `password`)
            database (str, optional): 사용할 데이터베이스명. (기본값: 환경 변수 `database`)
        """
        load_dotenv()  # .env 파일 로드 (있을 경우)

        self.host = host or os.environ.get("host")
        self.port = int(port or os.environ.get("port", 3306))  # 기본값 3306
        self.username = username or os.environ.get("username")
        self.password = password or os.environ.get("password")
        self.database = database or os.environ.get("database")

        self.connection: Optional[pymysql.connections.Connection] = None
        self.connect()  # 클래스 생성 시 자동 연결

    def connect(self) -> None:
        """
        MySQL RDS 데이터베이스에 연결을 시도합니다.
        
        연결 성공 시 `self.connection`에 연결 객체가 저장되며, 실패 시 에러 로그를 출력하고 `None`으로 설정됩니다.
        `autocommit`은 False(트랜잭션 수동 관리)로 설정됩니다.
        """
        try:
            self.connection = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.username,
                password=self.password,
                db=self.database,
                charset="utf8mb4",
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=False  # 트랜잭션 수동 관리 (중요 변경)
            )
            print(f"✅ [INFO] Database connected successfully: {self.host}:{self.port} (DB: {self.database})")
        except pymysql.MySQLError as e:
            print(f"❌ [ERROR] Database connection failed: {e}")
            self.connection = None

    @contextlib.contextmanager
    def transaction(self) -> Generator[pymysql.cursors.Cursor, None, None]:
        """
        트랜잭션 처리를 위한 Context Manager.
        
        `with` 구문 내에서 사용하여 트랜잭션 범위를 지정합니다.
        블록 내부가 정상적으로 실행되면 `commit`을 수행하고, 예외가 발생하면 `rollback`을 수행합니다.

        Yields:
            pymysql.cursors.Cursor: 트랜잭션 내에서 사용할 커서 객체
        
        Raises:
            Exception: 트랜잭션 수행 중 발생한 모든 예외
        """
        if not self.connection or not self.connection.open:
             self.connect()

        try:
            # 트랜잭션 시작 (이미 autocommit=False지만 명시적으로)
            self.connection.begin()
            yield self.connection.cursor()
            self.connection.commit()
        except Exception as e:
            self.connection.rollback()
            print(f"❌ [ERROR] Transaction failed, rolled back: {e}")
            raise e

    def execute_query(self, query: str, params: Optional[Tuple] = None, fetch_one: bool = False) -> Optional[Any]:
        """
        데이터베이스에서 SQL 쿼리를 실행하고 결과를 반환합니다.

        주의: 트랜잭션 컨텍스트 외부에서 실행 시, INSERT/UPDATE는 커밋되지 않을 수 있습니다.
        단순 조회 용도로 사용하거나, 내부에서 `transaction()`을 호출하도록 변경하는 것을 권장합니다.

        Args:
            query (str): 실행할 SQL 쿼리문
            params (tuple, optional): SQL 쿼리의 파라미터
            fetch_one (bool): True이면 첫 번째 결과(dict)만 반환, False이면 전체 결과(list) 반환

        Returns:
            list or dict or None: 쿼리 실행 결과 (성공 시 데이터, 실패 시 None)
        """
        if not self.connection:
            print("❌ [ERROR] Database connection is not available.")
            return None

        # 연결이 끊어졌으면 재연결 시도
        if not self.connection.open:
            self.connect()

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, params or ())
                result = cursor.fetchone() if fetch_one else cursor.fetchall()
                return result
        except pymysql.MySQLError as e:
            print(f"❌ [ERROR] Query execution failed: {e}")
            return None

    def execute_batch(self, query: str, params_list: List[Tuple]) -> None:
        """
        대량의 데이터를 `executemany`를 사용하여 일괄 실행합니다.
        
        자동으로 `transaction()` 컨텍스트 내에서 실행되므로, 전체가 성공하거나 전체가 롤백됩니다.

        Args:
            query (str): 실행할 SQL 쿼리 (Parameter placeholder 포함)
            params_list (list): 쿼리에 바인딩할 파라미터 리스트
        """
        with self.transaction() as cursor:
            cursor.executemany(query, params_list)


    def get_latest_propose_date(self) -> Optional[str]:
        """
        RDS 데이터베이스에서 가장 최근의 법안 발의 날짜를 가져옵니다.

        Returns:
            str or None: 가장 최근 발의 날짜 (YYYY-MM-DD), 없거나 에러 시 None
        """
        try:
            query = "SELECT MAX(propose_date) AS latest_date FROM Bill"
            result = self.execute_query(query, fetch_one=True)
            return result["latest_date"] if result else None
        except Exception as e:
            print("❌ [ERROR] Failed to fetch the latest propose_date")
            print(e)
            return None

    def get_latest_timeline_date(self) -> Optional[str]:
        """
        RDS 데이터베이스에서 가장 최근의 법안 처리 날짜(status_update_date)를 가져옵니다.

        Returns:
            str or None: 가장 최근 처리 날짜 (YYYY-MM-DD), 없거나 에러 시 None
        """
        try:
            query = "SELECT MAX(status_update_date) AS latest_date FROM BillTimeline"
            result = self.execute_query(query, fetch_one=True)
            return result["latest_date"] if result else None
        except Exception as e:
            print("❌ [ERROR] Failed to fetch the latest status_update_date")
            print(e)
            return None
    
    def insert_bill_info(self, bills_data: List[Dict]) -> None:
        """
        법안 정보를 DB에 적재합니다. (기존 insertBillInfoDf 대체)

        이 메소드는 다음 작업을 수행합니다:
        1. 법안 정보 Upsert (INSERT ... ON DUPLICATE KEY UPDATE)
        2. 발의자 정보 연결 (BillProposer, RepresentativeProposer)

        Args:
            bills_data (List[Dict]): 적재할 법안 데이터 리스트. 각 항목은 다음 키를 포함해야 함:
                - bill_id, bill_name, prose_date, ... (Bill 테이블 컬럼)
                - public_proposer_ids (List[str]): 공동발의자 의원 ID 목록
                - rst_proposer_ids (List[str]): 대표발의자 의원 ID 목록
        """
        with self.transaction() as cursor:
            # 1. Bill 테이블 Upsert
            bill_query = """
                INSERT INTO Bill (
                    bill_id, bill_name, committee, gpt_summary, propose_date, 
                    summary, stage, proposers, bill_pdf_url, viewCount, 
                    brief_summary, bill_number, bill_link, bill_result, 
                    proposer_kind, created_date, modified_date
                ) VALUES (
                    %(bill_id)s, %(bill_name)s, %(committee)s, %(gpt_summary)s, %(propose_date)s,
                    %(summary)s, %(stage)s, %(proposers)s, %(bill_pdf_url)s, 0,
                    %(brief_summary)s, %(bill_number)s, %(bill_link)s, %(bill_result)s,
                    %(proposer_kind)s, NOW(), NOW()
                ) AS new
                ON DUPLICATE KEY UPDATE
                    summary = new.summary,
                    gpt_summary = new.gpt_summary,
                    bill_pdf_url = new.bill_pdf_url,
                    brief_summary = new.brief_summary,
                    bill_link = new.bill_link,
                    modified_date = NOW()
            """
            
            # bills_data에서 Bill 테이블용 데이터만 추출하여 실행할 수도 있지만,
            # 전체 Dict를 넘겨도 매칭되는 키만 사용되므로 그대로 사용 가능 (단, 키 이름 일치 필요)
            cursor.executemany(bill_query, bills_data)

            # 2. 발의자 정보 처리
            # 각 법안별로 발의자 연결 실행
            for bill in bills_data:
                bill_id = bill['bill_id']
                
                # 2-1. 공동발의자 (Public Proposer)
                if 'public_proposer_ids' in bill and bill['public_proposer_ids']:
                    self._link_proposers(cursor, bill_id, bill['public_proposer_ids'], is_representative=False)
                
                # 2-2. 대표발의자 (Representative Proposer)
                if 'rst_proposer_ids' in bill and bill['rst_proposer_ids']:
                    self._link_proposers(cursor, bill_id, bill['rst_proposer_ids'], is_representative=True)

    def _link_proposers(self, cursor: pymysql.cursors.Cursor, bill_id: str, proposer_ids: List[str], is_representative: bool = False) -> None:
        """
        법안과 의원(발의자) 간의 관계를 저장합니다.
        
        Args:
            cursor: 트랜잭션 커서
            bill_id: 법안 ID
            proposer_ids: 의원 ID 리스트
            is_representative: 대표발의자 여부 (True: RepresentativeProposer, False: BillProposer)
        """
        if not proposer_ids:
            return

        # 1. 유효한 의원 ID 및 소속 정당 ID 조회
        # 중복 제거를 위해 Set으로 변환
        unique_ids = list(set(proposer_ids))
        format_strings = ','.join(['%s'] * len(unique_ids))
        
        check_query = f"""
            SELECT congressman_id, party_id 
            FROM Congressman 
            WHERE congressman_id IN ({format_strings})
        """
        cursor.execute(check_query, tuple(unique_ids))
        valid_congressmen = cursor.fetchall()
        
        if not valid_congressmen:
            print(f"⚠️ [WARN] No valid congressmen found for bill {bill_id} among {proposer_ids}")
            return

        # 2. 관계 테이블 Insert
        # 기존 관계를 삭제하고 다시 넣는 것보다, INSERT IGNORE를 사용하여 기존 데이터 유지하면서 신규만 추가
        # (DataService.java 로직상으로는 기존 관계 유지 + 신규 추가 형태임)
        
        target_table = "RepresentativeProposer" if is_representative else "BillProposer"
        
        # INSERT IGNORE INTO Table (bill_id, congressman_id, party_id, created_date, modified_date) ...
        # 주의: 이 테이블들에 bill_id + congressman_id 복합 유니크 키가 있어야 중복 삽입 방지 가능
        # 스키마 확인 결과: RepProposer(rep_id PK), BillProposer(bill_public_id PK) 
        # 복합 유니크 키 여부는 확실치 않음. 중복 방지를 위해 먼저 delete 후 insert 하거나, NOT IN 조건 사용 필요.
        # 여기서는 안전하게 확인 후 삽입 (또는 DELETE 후 INSERT 전략 사용)
        
        # 간단한 전략: 일단 모두 삭제 후 재삽입 (관계 테이블이므로 가능)
        # 단, 대표발의자와 일반발의자가 겹치는 경우는 드물지만 로직상 구분되어 있음.
        
        # 기존 로직(Java)은 'update' 개념이 없으므로, 그냥 추가만 함.
        # 하지만 멱등성을 위해 기존 데이터 삭제 후 재삽입이 깔끔함.
        # delete_query = f"DELETE FROM {target_table} WHERE bill_id = %s"
        # cursor.execute(delete_query, (bill_id,))

        # **수정된 전략**: 기존 데이터를 건드리지 않고, 없는 데이터만 추가 (INSERT IGNORE 유사 효과)
        # 하지만 MySQL INSERT IGNORE는 PK 충돌시에만 동작.
        # 따라서 여기서는 명시적으로 중복 체크를 하지 않고 넣으면 계속 쌓이는 구조인지 확인 필요.
        # 스키마상 PK는 Auto Increment ID임. 따라서 중복 데이터가 계속 쌓일 수 있음.
        # -> 기존 데이터를 지우고 다시 넣는 것이 맞음.
        
        cursor.execute(f"DELETE FROM {target_table} WHERE bill_id = %s", (bill_id,))
        
        insert_query = f"""
            INSERT INTO {target_table} (bill_id, congressman_id, party_id, created_date, modified_date)
            VALUES (%s, %s, %s, NOW(), NOW())
        """
        
        insert_params = []
        for cm in valid_congressmen:
            insert_params.append((bill_id, cm['congressman_id'], cm['party_id']))
            
        cursor.executemany(insert_query, insert_params)

    def update_bill_stage(self, bills_stage_data: List[Dict]) -> Dict[str, List[str]]:
        """
        법안 단계(Stage) 정보를 업데이트하고 타임라인을 기록합니다. (기존 updateBillStageDf 대체)

        Args:
            bills_stage_data (List[Dict]): 업데이트할 단계 정보 리스트.
                - bill_id, stage, committee, status_update_date 등 포함

        Returns:
            Dict[str, List[str]]: 처리 결과 요약
                - "duplicate_bill": 이미 존재하는 타임라인이라 스킵된 건수 (List of info string)
                - "not_found_bill": 법안이 없어서 처리가 불가능한 bill_id 리스트
        """
        result_map = {
            "duplicate_bill": [],
            "not_found_bill": []
        }
        
        if not bills_stage_data:
            return result_map

        # 중복 체크를 위한 키 생성 (bill_id, stage, date)
        # committee는 nullable일 수 있으므로 주의
        
        bill_ids = [b['bill_id'] for b in bills_stage_data]
        
        with self.transaction() as cursor:
            # 1. 존재하는 법안 확인
            existing_ids = set(self.get_existing_bill_ids(bill_ids))
            
            # 2. 중복 타임라인 확인 (Bulk Check)
            # 입력된 데이터 조건(bill_id, stage, date)에 해당하는 Timeline이 있는지 조회
            # WHERE 절을 OR로 연결하여 구성하거나, 임시 테이블을 쓸 수 있지만
            # 여기서는 간단히 bill_id 리스트로 관련 타임라인을 모두 가져와서 메모리에서 체크 (데이터 양에 따라 최적화 필요)
            # 혹은 튜플 IN 쿼리 사용: (bill_id, bill_timeline_stage, status_update_date) IN (...)
            
            check_tuples = []
            for item in bills_stage_data:
                # date format matching needed? Assuming Input is string "YYYY-MM-DD"
                check_tuples.append((item['bill_id'], item['stage'], item['status_update_date']))
            
            if not check_tuples:
                return result_map

            format_strings = ','.join(['(%s, %s, %s)'] * len(check_tuples))
            timeline_check_query = f"""
                SELECT bill_id, bill_timeline_stage, status_update_date 
                FROM BillTimeline 
                WHERE (bill_id, bill_timeline_stage, status_update_date) IN ({format_strings})
            """
            
            # 튜플 리스트를 flat하게 펴서 파라미터로 전달
            flat_params = []
            for t in check_tuples:
                flat_params.extend(t)
                
            cursor.execute(timeline_check_query, tuple(flat_params))
            found_timelines = cursor.fetchall()
            
            # 검색 속도를 위해 Set으로 변환: (bill_id, stage, str(date))
            # DB에서 가져온 date는 datetime.date 객체일 수 있음 -> str로 변환
            existing_timelines = set()
            for row in found_timelines:
                existing_timelines.add((
                    row['bill_id'], 
                    row['bill_timeline_stage'], 
                    str(row['status_update_date'])
                ))
            
            # 3. 업데이트 대상 선별
            update_bill_params = []
            insert_timeline_params = []
            
            for item in bills_stage_data:
                bill_id = item['bill_id']
                stage = item['stage']
                update_date = item['status_update_date']
                committee = item.get('committee', None)
                
                # 법안 존재 여부 체크
                if bill_id not in existing_ids:
                    result_map["not_found_bill"].append(bill_id)
                    continue
                
                # 타임라인 중복 체크
                if (bill_id, stage, str(update_date)) in existing_timelines:
                    result_map["duplicate_bill"].append(f"{bill_id}-{stage}-{update_date}")
                    continue
                
                # 업데이트 대상 추가
                update_bill_params.append((stage, bill_id))
                insert_timeline_params.append((
                    bill_id, committee, stage, update_date, None # bill_result is null initially in logic
                ))
            
            # 4. Batch Execution
            if update_bill_params:
                # Bill 테이블 Stage 업데이트
                cursor.executemany(
                    "UPDATE Bill SET stage = %s, modified_date = NOW() WHERE bill_id = %s",
                    update_bill_params
                )
                
                # BillTimeline 테이블 Insert
                cursor.executemany(
                    """
                    INSERT INTO BillTimeline 
                    (bill_id, bill_timeline_committee, bill_timeline_stage, status_update_date, bill_result, created_date, modified_date)
                    VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
                    """,
                    insert_timeline_params
                )
                
        return result_map

    def get_existing_bill_ids(self, bill_ids: List[str]) -> List[str]:
            """
            주어진 법안 ID 목록 중 데이터베이스에 이미 존재하는 ID를 반환합니다.

            Args:
                bill_ids (list): 확인할 법안 ID 리스트

            Returns:
                list: DB에 존재하는 법안 ID 리스트
            """
            if not bill_ids:
                return []

            format_strings = ','.join(['%s'] * len(bill_ids)) 

            # **수정된 부분:** query를 문자열로만 만들고, bill_ids 튜플을 params로 전달
            query = f"SELECT {'bill_id'} FROM Bill WHERE {'bill_id'} IN ({format_strings})"
            params = tuple(bill_ids) # 매개변수를 별도의 변수로 분리

            result = self.execute_query(query, params=params, fetch_one=False) 
            
            if result is None:
                return []

            # 결과에서 ID 추출
            existing_ids = [row['bill_id'] for row in result]

            print(f"DB에 존재하는 법안 id 목록: {existing_ids}")

            return existing_ids

    def update_lawmaker_info(self, lawmaker_data: List[Dict]) -> None:
        """
        의원 정보를 DB에 동기화합니다. (기존 updateLawmakerDf 대체)

        Args:
            lawmaker_data (List[Dict]): 업데이트할 의원 정보 리스트.
                - congressman_id, name, party_name, district, elect_sort, ...
        """
        if not lawmaker_data:
            return

        with self.transaction() as cursor:
            # 1. 정당 ID 확보 (없으면 생성)
            party_names = {item['party_name'] for item in lawmaker_data if 'party_name' in item}
            party_map = self._ensure_parties(cursor, party_names)

            # 2. 존재하는 의원 ID 조회
            cursor.execute("SELECT congressman_id FROM Congressman")
            existing_rows = cursor.fetchall()
            existing_ids = {row['congressman_id'] for row in existing_rows}
            
            input_ids = {item['congressman_id'] for item in lawmaker_data}

            # 3. 비활성 처리 (Disable)
            # DB에는 있는데 입력 데이터에 없는 의원은 state=False 처리
            disable_ids = list(existing_ids - input_ids)
            if disable_ids:
                format_strings = ','.join(['%s'] * len(disable_ids))
                disable_query = f"UPDATE Congressman SET state = 0, modified_date = NOW() WHERE congressman_id IN ({format_strings})"
                cursor.execute(disable_query, tuple(disable_ids))

            # 4. Upsert (Insert or Update)
            upsert_query = """
                INSERT INTO Congressman (
                    congressman_id, name, party_id, district, elect_sort, 
                    commits, elected, homepage, congressman_image_url, 
                    email, sex, congressman_age, congressman_office, congressman_telephone,
                    brief_history, state, created_date, modified_date
                ) VALUES (
                    %(congressman_id)s, %(name)s, %(party_id)s, %(district)s, %(elect_sort)s,
                    %(commits)s, %(elected)s, %(homepage)s, %(congressman_image_url)s,
                    %(email)s, %(sex)s, %(congressman_age)s, %(congressman_office)s, %(congressman_telephone)s,
                    %(brief_history)s, 1, NOW(), NOW()
                ) AS new
                ON DUPLICATE KEY UPDATE
                    party_id = new.party_id,
                    district = new.district,
                    elect_sort = new.elect_sort,
                    commits = new.commits,
                    elected = new.elected,
                    homepage = new.homepage,
                    congressman_image_url = new.congressman_image_url,
                    email = new.email,
                    sex = new.sex,
                    congressman_age = new.congressman_age,
                    brief_history = new.brief_history,
                    state = 1,
                    modified_date = NOW()
            """
            
            upsert_params = []
            for item in lawmaker_data:
                item_party_id = party_map.get(item.get('party_name'))
                if item_party_id is None:
                    # Party creation failed or missing name, skip or handle error?
                    # _ensure_parties should have created it.
                    continue
                
                # Prepare params dict including party_id
                params = item.copy()
                params['party_id'] = item_party_id
                
                # Fill optional fields with defaults if missing
                # (executemany expects same keys, but DictCursor params matching uses keys)
                # Ensure all keys in SQL are present in params
                required_keys = [
                    'congressman_id', 'name', 'district', 'elect_sort', 
                    'commits', 'elected', 'homepage', 'congressman_image_url',
                    'email', 'sex', 'congressman_age', 'congressman_office', 'congressman_telephone',
                    'brief_history'
                ]
                for k in required_keys:
                    if k not in params:
                        params[k] = None
                
                upsert_params.append(params)

            if upsert_params:
                cursor.executemany(upsert_query, upsert_params)

    def _ensure_parties(self, cursor: pymysql.cursors.Cursor, party_names: Set[str]) -> Dict[str, int]:
        """
        정당 이름 목록에 해당하는 Party ID를 조회하고, 존재하지 않는 정당은 생성합니다.

        Args:
            cursor: 트랜잭션 커서
            party_names: 확인할 정당 이름 Set

        Returns:
            Dict[str, int]: { '정당명': party_id } 매핑
        """
        if not party_names:
            return {}

        # 1. 기존 정당 조회
        format_strings = ','.join(['%s'] * len(party_names))
        select_query = f"SELECT party_id, name FROM Party WHERE name IN ({format_strings})"
        cursor.execute(select_query, tuple(party_names))
        rows = cursor.fetchall()
        
        party_map = {row['name']: row['party_id'] for row in rows}
        
        # 2. 없는 정당 생성
        missing_parties = [name for name in party_names if name not in party_map]
        
        if missing_parties:
            insert_query = "INSERT INTO Party (name, created_date, modified_date) VALUES (%s, NOW(), NOW())"
            # Batch Insert
            cursor.executemany(insert_query, [(name,) for name in missing_parties])
            
            # 3. 생성된 정당 ID 다시 조회
            # party_id가 AUTO_INCREMENT라고 가정
            # MySQL에선 executemany 후 lastrowid는 첫 번째 ID만 반환하거나 드라이버에 따라 다름.
            # 가장 확실한 방법은 이름으로 다시 조회.
            missing_format = ','.join(['%s'] * len(missing_parties))
            reselect_query = f"SELECT party_id, name FROM Party WHERE name IN ({missing_format})"
            cursor.execute(reselect_query, tuple(missing_parties))
            new_rows = cursor.fetchall()
            
            for row in new_rows:
                party_map[row['name']] = row['party_id']
                
        return party_map

    def update_bill_result(self, bills_result_data: List[Dict]) -> None:
        """
        법안 처리 결과(bill_result)를 업데이트합니다. (기존 updateBillResultDf 대체)

        Args:
            bills_result_data (List[Dict]): 업데이트할 결과 정보.
                - bill_id (str): 법안 ID
                - bill_result (str): 처리 결과 (예: 원안가결, 수정가결 등)
        """
        if not bills_result_data:
            return

        with self.transaction() as cursor:
            # 파라미터 준비: (bill_result, bill_id)
            update_params = []
            for item in bills_result_data:
                if 'bill_result' in item and 'bill_id' in item:
                    update_params.append((item['bill_result'], item['bill_id']))

            if update_params:
                # 1. Bill 테이블 업데이트
                cursor.executemany(
                    "UPDATE Bill SET bill_result = %s, modified_date = NOW() WHERE bill_id = %s",
                    update_params
                )

                # 2. BillTimeline 테이블 업데이트
                # '본회의 심의' 단계이면서 아직 결과가 없는(NULL) 타임라인만 업데이트
                cursor.executemany(
                    """
                    UPDATE BillTimeline 
                    SET bill_result = %s, modified_date = NOW()
                    WHERE bill_id = %s AND bill_timeline_stage = '본회의 심의' AND bill_result IS NULL
                    """,
                    update_params
                )
    
                # 2. BillTimeline 테이블 업데이트
                # '본회의 심의' 단계이면서 아직 결과가 없는(NULL) 타임라인만 업데이트
                cursor.executemany(
                    """
                    UPDATE BillTimeline 
                    SET bill_result = %s, modified_date = NOW()
                    WHERE bill_id = %s AND bill_timeline_stage = '본회의 심의' AND bill_result IS NULL
                    """,
                    update_params
                )

    def insert_vote_record(self, vote_data: List[Dict]) -> None:
        """
        본회의 표결 결과(VoteRecord)를 적재합니다. (기존 insertAssemblyVote 대체)

        Args:
            vote_data (List[Dict]): 표결 정보 리스트
                - bill_id, vote_record_id(optional), votes_for_count, votes_againt_count, ...
        """
        if not vote_data:
            return

        with self.transaction() as cursor:
            # 1. 존재하는 법안 확인
            bill_ids = [item['bill_id'] for item in vote_data]
            existing_bills = set(self.get_existing_bill_ids(bill_ids))
            
            # 파라미터 준비
            upsert_params = []
            for item in vote_data:
                if item['bill_id'] not in existing_bills:
                    continue
                
                upsert_params.append({
                    'bill_id': item['bill_id'],
                    'votes_for_count': item.get('votes_for_count', 0),
                    'votes_againt_count': item.get('votes_againt_count', 0),
                    'abstention_count': item.get('abstention_count', 0),
                    'total_vote_count': item.get('total_vote_count', 0)
                })

            if upsert_params:
                # Upsert Query (bill_id가 UNIQUE라고 가정)
                upsert_query = """
                    INSERT INTO VoteRecord (
                        bill_id, votes_for_count, votes_againt_count, abstention_count, total_vote_count,
                        created_date, modified_date
                    ) VALUES (
                        %(bill_id)s, %(votes_for_count)s, %(votes_againt_count)s, %(abstention_count)s, %(total_vote_count)s,
                        NOW(), NOW()
                    ) AS new
                    ON DUPLICATE KEY UPDATE
                        votes_for_count = new.votes_for_count,
                        votes_againt_count = new.votes_againt_count,
                        abstention_count = new.abstention_count,
                        total_vote_count = new.total_vote_count,
                        modified_date = NOW()
                """
                cursor.executemany(upsert_query, upsert_params)

    def insert_vote_party(self, vote_party_data: List[Dict]) -> None:
        """
        정당별 투표 결과(VoteParty)를 적재합니다. (기존 insertVoteParty 대체)

        Args:
            vote_party_data (List[Dict]): 정당별 투표 정보 리스트
                - bill_id, party_name, votes_for_count, ...
        """
        if not vote_party_data:
            return

        with self.transaction() as cursor:
            # 1. 존재하는 법안 및 정당 확인
            bill_ids = {item['bill_id'] for item in vote_party_data}
            existing_bills = set(self.get_existing_bill_ids(list(bill_ids)))
            
            party_names = {item['party_name'] for item in vote_party_data}
            party_map = self._ensure_parties(cursor, party_names)
            
            # 2. 파라미터 준비
            upsert_params = []
            for item in vote_party_data:
                bill_id = item['bill_id']
                party_name = item['party_name']
                party_id = party_map.get(party_name)
                
                if bill_id not in existing_bills or party_id is None:
                    continue
                
                upsert_params.append({
                    'bill_id': bill_id,
                    'party_id': party_id,
                    'votes_for_count': item.get('votes_for_count', 0)
                })

            if upsert_params:
                # 3. 투표 결과 삭제 후 재삽입 (idempotency, bill_id + party_id 기준)
                # 복합 유니크 키가 없는 경우 중복 방지를 위해 삭제 후 삽입하는 것이 안전함.
                # 단, VoteParty ID가 바뀌는 단점 존재.
                
                # 삭제 대상 법안 ID 수집 (관련된 모든 정당 투표 정보를 업데이트한다고 가정)
                target_bills = {p['bill_id'] for p in upsert_params}
                format_strings = ','.join(['%s'] * len(target_bills))
                
                # 특정 법안에 대한 특정 정당의 투표만 업데이트하는 경우, 전체 삭제는 위험함.
                # 따라서 (bill_id, party_id) 조합으로 기존 데이터 확인 후 Update/Insert 필요 (Batch 처리가 까다로움).
                # 하지만 여기서는 "Batch Delete & Insert"가 대량 처리에 효율적.
                # Java 로직에서도 "foundVoteParty"를 찾아서 업데이트함.
                
                # 여기서는 안전한 'Check Existing & Separate Update/Insert' 방식을 배치로 구현
                # (bill_id, party_id) 튜플로 기존 데이터 조회
                
                check_tuples = [(p['bill_id'], p['party_id']) for p in upsert_params]
                # IN 절 생성을 위한 포맷팅
                check_format = ','.join(['(%s, %s)'] * len(check_tuples))
                check_query = f"SELECT vote_party_id, bill_id, party_id FROM VoteParty WHERE (bill_id, party_id) IN ({check_format})"
                
                # flat params
                flat_check_params = []
                for t in check_tuples:
                    flat_check_params.extend(t)
                
                cursor.execute(check_query, tuple(flat_check_params))
                existing_votes = cursor.fetchall() # [{'vote_party_id': 1, 'bill_id': 'A', 'party_id': 10}, ...]
                
                existing_map = {(row['bill_id'], row['party_id']): row['vote_party_id'] for row in existing_votes}
                
                insert_batch = []
                update_batch = []
                
                for p in upsert_params:
                    key = (p['bill_id'], p['party_id'])
                    if key in existing_map:
                        # Update
                        p['vote_party_id'] = existing_map[key]
                        update_batch.append(p)
                    else:
                        # Insert
                        insert_batch.append(p)
                
                # 실행
                if insert_batch:
                    cursor.executemany("""
                        INSERT INTO VoteParty (bill_id, party_id, votes_for_count, created_date, modified_date)
                        VALUES (%(bill_id)s, %(party_id)s, %(votes_for_count)s, NOW(), NOW())
                    """, insert_batch)
                    
                if update_batch:
                    cursor.executemany("""
                        UPDATE VoteParty 
                        SET votes_for_count = %(votes_for_count)s, modified_date = NOW()
                        WHERE vote_party_id = %(vote_party_id)s
                    """, update_batch)
    
    def close(self) -> None:
        """데이터베이스 연결을 종료합니다."""
        if self.connection:
            self.connection.close()
            print("✅ [INFO] Database connection closed.")