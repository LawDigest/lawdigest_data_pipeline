import requests
import pandas as pd
from xml.etree import ElementTree
import time
from datetime import datetime, timedelta
import os
import ast
from typing import List
from dotenv import load_dotenv

from .DataFetcher import DataFetcher
from .DataProcessor import DataProcessor
from .AISummarizer import AISummarizer
from .APISender import APISender
from .DatabaseManager import DatabaseManager
from .Notifier import Notifier
from .constants import ProposerKindType


class WorkFlowManager:
    CHUNK_SIZE = 1000

    def __init__(self, mode):
        """Workflow manager initialization

        Parameters
        ----------
        mode: str, optional
            실행 모드.
            - remote: 운영 모드. AI 요약 및 DB 직접 적재.
            - ai_test: 테스트 모드. 상위 5건 AI 요약 수행 (DB 적재 없음).
            - dry-run: 데이터 수집 확인용 (요약/적재 생략).
            - db: (구) DB 직접 적재 모드 (remote와 동일하게 동작 가능).
        """
        self.mode_list = ['remote', 'local', 'test', 'save', 'fetch', 'ai_test', 'db', 'dry-run']
        if mode not in self.mode_list:
            raise ValueError(
                f"올바른 모드를 선택해주세요. {self.mode_list}"
            )
        self.mode = mode

        load_dotenv()

    @staticmethod
    def _to_local_url(url: str | None) -> str | None:
        if url is None:
            return None
        return url.replace("https://api.lawdigest.net", "http://localhost:8080")

    @staticmethod
    def _chunk_dataframe(df: pd.DataFrame, chunk_size: int = 1000):
        for start in range(0, len(df), chunk_size):
            yield df.iloc[start : start + chunk_size]

    @staticmethod
    def _safe_to_int(value: object, default: int = 0) -> int:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return default
        try:
            return int(str(value).replace(",", "").strip())
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _coerce_optional_text(value: object) -> object:
        if value is None:
            return None
        if isinstance(value, float) and pd.isna(value):
            return None
        text = str(value).strip()
        return text if text else None

    @staticmethod
    def _coerce_string_list(value: object) -> List[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(v).strip() for v in value if str(v).strip()]
        if isinstance(value, tuple):
            return [str(v).strip() for v in value if str(v).strip()]
        if isinstance(value, str):
            cleaned = value.strip()
            if not cleaned:
                return []
            try:
                parsed = ast.literal_eval(cleaned)
            except (ValueError, SyntaxError):
                parsed = None

            if isinstance(parsed, (list, tuple)):
                return [str(v).strip() for v in parsed if str(v).strip()]
            if isinstance(parsed, str):
                return [part.strip() for part in parsed.split(",") if part.strip()]
            return [cleaned]

        return [str(value).strip()] if str(value).strip() else []

    @staticmethod
    def _normalize_proposer_kind(proposer_kind: object) -> str:
        normalized = str(proposer_kind).strip()

        if not normalized:
            return ProposerKindType.CONGRESSMAN.name

        for kind in ProposerKindType:
            if normalized == kind.value:
                return kind.name

        if normalized in {kind.name for kind in ProposerKindType}:
            return normalized

        return ProposerKindType.CONGRESSMAN.name

    def _build_bill_row(self, row: pd.Series) -> dict:
        return {
            "bill_id": self._coerce_optional_text(row.get("bill_id")),
            "bill_name": self._coerce_optional_text(row.get("bill_name")),
            "committee": self._coerce_optional_text(row.get("committee")),
            "gpt_summary": self._coerce_optional_text(row.get("gpt_summary")),
            "propose_date": self._coerce_optional_text(row.get("proposeDate")),
            "summary": self._coerce_optional_text(row.get("summary")),
            "stage": self._coerce_optional_text(row.get("stage")),
            "proposers": self._coerce_optional_text(row.get("proposers")),
            "bill_pdf_url": self._coerce_optional_text(row.get("billPdfUrl"))
            or self._coerce_optional_text(row.get("bill_link")),
            "brief_summary": self._coerce_optional_text(row.get("brief_summary")),
            "bill_number": self._safe_to_int(row.get("billNumber")),
            "bill_link": self._coerce_optional_text(row.get("bill_link")),
            "bill_result": self._coerce_optional_text(row.get("billResult")),
            "proposer_kind": self._normalize_proposer_kind(row.get("proposer_kind")),
            "public_proposer_ids": self._coerce_string_list(row.get("publicProposerIdList")),
            "rst_proposer_ids": self._coerce_string_list(row.get("rstProposerIdList")),
        }

    def _build_lawmakers_rows(self, df_lawmakers: pd.DataFrame) -> List[dict]:
        rows = []

        for _, row in df_lawmakers.iterrows():
            assembly_number = self._safe_to_int(row.get("assemblyNumber"), default=22)
            congressman_id = self._coerce_optional_text(row.get("congressmanId"))

            if not congressman_id:
                continue

            rows.append(
                {
                    "congressman_id": congressman_id,
                    "name": self._coerce_optional_text(row.get("congressmanName")),
                    "party_name": self._coerce_optional_text(row.get("partyName")),
                    "district": self._coerce_optional_text(row.get("district")),
                    "elect_sort": self._coerce_optional_text(row.get("electSort")),
                    "commits": self._coerce_optional_text(row.get("commits")),
                    "elected": self._coerce_optional_text(row.get("elected")),
                    "homepage": self._coerce_optional_text(row.get("homepage")),
                    "congressman_image_url": self._coerce_optional_text(row.get("congressmanImage"))
                    or f"/congressman/{assembly_number}/{congressman_id}.jpg",
                    "email": self._coerce_optional_text(row.get("email")),
                    "sex": self._coerce_optional_text(row.get("sex")),
                    "congressman_age": self._coerce_optional_text(row.get("congressmanBirth")),
                    "congressman_office": self._coerce_optional_text(row.get("congressmanOffice")),
                    "congressman_telephone": self._coerce_optional_text(row.get("congressmanTelephone")),
                    "brief_history": self._coerce_optional_text(row.get("briefHistory")),
                }
            )

        return rows

    def _build_bill_stage_row(self, row: pd.Series) -> dict:
        return {
            "bill_id": self._coerce_optional_text(row.get("billId")) or self._coerce_optional_text(row.get("bill_id")),
            "stage": self._coerce_optional_text(row.get("stage")),
            "committee": self._coerce_optional_text(row.get("committee")),
            "status_update_date": (
                self._coerce_optional_text(row.get("statusUpdateDate"))
                or self._coerce_optional_text(row.get("status_update_date"))
                or self._coerce_optional_text(row.get("DT"))
            ),
        }

    def _build_bill_result_row(self, row: pd.Series) -> dict:
        return {
            "bill_id": self._coerce_optional_text(row.get("billId")) or self._coerce_optional_text(row.get("bill_id")),
            "bill_result": self._coerce_optional_text(row.get("billProposeResult")) or self._coerce_optional_text(row.get("bill_result")),
        }

    def _build_vote_row(self, row: pd.Series) -> dict:
        return {
            "bill_id": self._coerce_optional_text(row.get("billId")) or self._coerce_optional_text(row.get("bill_id")),
            "votes_for_count": self._safe_to_int(
                row.get("voteForCount") if row.get("voteForCount") is not None else row.get("votes_for_count")
            ),
            "votes_againt_count": self._safe_to_int(
                row.get("voteAgainstCount") if row.get("voteAgainstCount") is not None else row.get("votes_againt_count")
            ),
            "abstention_count": self._safe_to_int(
                row.get("abstentionCount") if row.get("abstentionCount") is not None else row.get("abstention_count")
            ),
            "total_vote_count": self._safe_to_int(
                row.get("totalVoteCount") if row.get("totalVoteCount") is not None else row.get("total_vote_count")
            ),
        }

    def _build_vote_party_row(self, row: pd.Series) -> dict:
        return {
            "bill_id": self._coerce_optional_text(row.get("billId")) or self._coerce_optional_text(row.get("bill_id")),
            "party_name": self._coerce_optional_text(row.get("partyName")),
            "votes_for_count": self._safe_to_int(
                row.get("voteForCount") if row.get("voteForCount") is not None else row.get("votes_for_count")
            ),
        }

    def update_statistics(self):
        db_conn = DatabaseManager()
        db_conn.update_party_statistics()
        db_conn.update_congressman_statistics()

    def fetch_bills_step(self, start_date=None, end_date=None, age=None):
        """데이터 수집 및 전처리 단계만 수행"""
        if start_date is None:
            start_date = self._get_bills_start_date(start_date)
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        if age is None:
            age = os.getenv("AGE")

        fetcher = DataFetcher()
        df_bills = fetcher.fetch_bills_data(start_date=start_date, end_date=end_date, age=age)
        
        if df_bills is None or df_bills.empty:
            return None

        processor = DataProcessor(fetcher)
        if self.mode not in {"fetch", "ai_test", "dry-run"}:
            df_bills = processor.remove_duplicates(df_bills, DatabaseManager())

        if df_bills is not None and not df_bills.empty:
            processor.add_AI_summary_columns(df_bills)
            df_bills = processor.process_congressman_bills(df_bills)
            if 'committee' not in df_bills.columns:
                df_bills['committee'] = None

        return df_bills

    def _get_bills_start_date(self, start_date=None):
        if start_date is not None:
            return start_date

        # ai_test/fetch/dry-run는 DB 조회 없이 최근 1일 데이터를 테스트/조회 대상으로 처리
        if self.mode in {"ai_test", "fetch", "dry-run"}:
            fallback_start_date = datetime.now().strftime('%Y-%m-%d')
            print(
                "[INFO] ai_test/fetch/dry-run 모드: 시작일이 지정되지 않았습니다. "
                f"{fallback_start_date}를 시작일로 사용합니다. (DB 조회 생략)"
            )
            return fallback_start_date

        # remote/db/test/full 모드는 기존 동작 유지: DB 최신일 기준
        db_conn = DatabaseManager()
        start_date = db_conn.get_latest_propose_date()
        if start_date is None:
            raise ValueError("DB에서 최신 법안 날짜를 가져올 수 없습니다.")
        return start_date

    def summarize_bill_step(self, bill_data: dict):
        """단일 법안 또는 소량의 법안에 대해 AI 요약 수행"""
        df_bill = pd.DataFrame([bill_data]) if isinstance(bill_data, dict) else pd.DataFrame(bill_data)
        summarizer = AISummarizer()
        summarizer.AI_title_summarize(df_bill)
        summarizer.AI_content_summarize(df_bill)
        return df_bill.to_dict('records')

    def upsert_bill_step(self, bill_data: dict | List[dict]):
        """단일 법안 또는 리스트를 DB에 직접 적재"""
        rows = bill_data if isinstance(bill_data, list) else [bill_data]
        db_conn = DatabaseManager()
        bill_rows = [self._build_bill_row(pd.Series(r)) for r in rows]
        if bill_rows:
            db_conn.insert_bill_info(bill_rows)
            return len(bill_rows)
        return 0

    def update_bills_data(self, start_date=None, end_date=None, age=None, run_stats: bool = True):
        """법안 데이터를 수집해 AI 요약 후 모드에 따라 적재/전송하는 함수

        Args:
            start_date (str, optional): 시작 날짜 (YYYY-MM-DD 형식). Defaults to None.
            end_date (str, optional): 종료 날짜 (YYYY-MM-DD 형식). Defaults to None.
            age (str, optional): 국회 데이터 수집 대수
            run_stats (bool, optional): ``db`` 및 ``remote`` 모드에서 적재 후 통계 갱신 여부. Defaults to True.
            
        Note:
            실행 모드는 클래스 생성 시 설정한 ``self.mode`` 값을 사용합니다.
            - remote: 운영 모드. AI 요약 및 DB 직접 적재.
            - ai_test: 테스트 모드. 상위 5건 AI 요약 수행 (DB 적재 없음).
            - dry-run: 수집 확인 모드. 요약 및 적재 모두 수행하지 않음.

        Returns:
            pd.DataFrame: 수집 및 처리된 데이터프레임
        """
        print(f"[법안 데이터 처리 시작] 실행 모드: {self.mode}")

        mode = self.mode
        
        # 데이터 수집 기간 설정
        if start_date is None:
            try:
                start_date = self._get_bills_start_date(start_date)
            except Exception as e:
                raise ConnectionError(f"데이터베이스 조회 중 오류가 발생했습니다: {e}")

        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')

        if age is None:
            age = os.getenv("AGE")

        # 1. 데이터 수집
        fetcher = DataFetcher()
        df_bills = fetcher.fetch_bills_data(start_date=start_date, end_date=end_date, age=age)

        # 2. 데이터 전처리
        processor = DataProcessor(fetcher)

        # 중복 데이터 제거 (fetch, ai_test, dry-run 모드에서는 수행하지 않음)
        if mode not in {"fetch", "ai_test", "dry-run"}:
            df_bills = processor.remove_duplicates(df_bills, DatabaseManager())

        if df_bills is None or len(df_bills) == 0:
            print("새로운 데이터가 없습니다. 처리를 종료합니다.")
            return None

        print(f"수집된 신규 법안 발의자 종류: {df_bills['proposer_kind'].value_counts()}")

        # AI 요약 컬럼 추가 (brief_summary, gpt_summary)
        processor.add_AI_summary_columns(df_bills)

        # 의원 데이터 처리
        df_bills = processor.process_congressman_bills(df_bills)
        
        # committee 컬럼 보완
        if 'committee' not in df_bills.columns:
            df_bills['committee'] = None

        if len(df_bills) == 0:
            print("처리 가능한 법안 데이터가 없습니다.")
            return None

        # 3. AI 요약 수행 (모드별 분기)
        summerizer = AISummarizer()
        
        if mode == 'remote':
            print("[운영 모드: AI 요약 진행]")
            all_summarized_bills = []
            for propose_date, group in df_bills.groupby('proposeDate'):
                print(f"\n--- 처리 날짜: {propose_date} ---")
                summerizer.AI_title_summarize(group)
                summerizer.AI_content_summarize(group)
                all_summarized_bills.append(group)
            df_bills = pd.concat(all_summarized_bills, ignore_index=True)

        elif mode == 'ai_test':
            print("[AI 테스트 모드: 상위 5건 요약 진행]")
            df_bills = df_bills[:5]
            summerizer.AI_title_summarize(df_bills)
            summerizer.AI_content_summarize(df_bills)

        elif mode == 'dry-run':
            print("[드라이 런 모드: 요약 및 적재를 생략합니다]")
        
        # 4. DB 적재 (모드별 분기)
        if mode in {'remote', 'db'}:
            print(f"[{mode.upper()} 모드: DB 직접 적재 진행]")
            db_conn = DatabaseManager()
            bill_rows = [
                self._build_bill_row(row)
                for _, row in df_bills.iterrows()
                if self._coerce_optional_text(row.get("billId"))
            ]
            if bill_rows:
                db_conn.insert_bill_info(bill_rows)
                if run_stats:
                    db_conn.update_party_statistics()
                    db_conn.update_congressman_statistics()
                    print("[DB 통계 갱신 완료]")
                print(f"[DB 적재 완료] 총 {len(bill_rows)}건")
            else:
                print("적재 대상 법안이 없습니다.")

        # 5. 알림 전송 (remote, dry-run 모드 등에서 실행 결과 알림)
        if mode in {'remote', 'dry-run'}:
            notifier = Notifier()
            print(f"\n--- 최종 '{mode}' 처리 결과 알림 ---")
            notifier.notify(
                subject="bills", 
                data=df_bills,
                custom_message=f"{mode} 모드로 법안 처리가 완료되었습니다."
            )

        return df_bills



    def update_lawmakers_data(self, run_stats: bool = True):
        """국회의원 데이터를 수집하고 모드에 따라 전송 또는 저장하는 메서드.

        Args:
            run_stats (bool, optional): ``db`` 모드에서 적재 후 통계 갱신 여부. Defaults to True.
        """

        print("\n[의원 데이터 수집 시작]")

        # 데이터 수집
        fetcher = DataFetcher()
        df_lawmakers = fetcher.fetch_lawmakers_data()

        if df_lawmakers is None or df_lawmakers.empty:
            print("❌ [ERROR] 수집된 의원 데이터가 없습니다.")
            return None

        # 필요 없는 컬럼 제거
        columns_to_drop = [
            'ENG_NM',       # 영문이름
            'HJ_NM',        # 한자이름
            'BTH_GBN_NM',   # 음력/양력 구분
            'ELECT_GBN_NM', # 선거구 구분(지역구/비례)
            'STAFF',        # 보좌관
            'CMITS',        # 소속위원회 목록
            'SECRETARY',    # 비서관
            'SECRETARY2',   # 비서
            'JOB_RES_NM',   # 직위
        ]

        df_lawmakers = df_lawmakers.drop(columns=columns_to_drop)

        # UNITS 컬럼에서 숫자만 추출하여 대수 정보로 사용
        df_lawmakers['UNITS'] = df_lawmakers['UNITS'].str.extract(r'(\d+)(?=\D*$)').astype(int)

        # 컬럼명 매핑
        column_mapping = {
            'MONA_CD': 'congressmanId',
            'HG_NM': 'congressmanName',
            'CMIT_NM': 'commits',
            'POLY_NM': 'partyName',
            'REELE_GBN_NM': 'elected',
            'HOMEPAGE': 'homepage',
            'ORIG_NM': 'district',
            'UNITS': 'assemblyNumber',
            'BTH_DATE': 'congressmanBirth',
            'SEX_GBN_NM': 'sex',
            'E_MAIL': 'email',
            'ASSEM_ADDR': 'congressmanOffice',
            'TEL_NO': 'congressmanTelephone',
            'MEM_TITLE': 'briefHistory',
        }

        df_lawmakers.rename(columns=column_mapping, inplace=True)

        # 모드별 처리
        payload_name = os.getenv("PAYLOAD_lawmakers")
        url = os.getenv("POST_URL_lawmakers")

        mode = self.mode

        if mode == 'remote':
            sender = APISender()
            sender.send_data(df_lawmakers, url, payload_name)

            print("[정당별 의원수 갱신 요청 중...]")
            post_url_party_bill_count = os.environ.get("POST_URL_party_bill_count")
            sender.request_post(post_url_party_bill_count)
            print("[정당별 의원수 갱신 요청 완료]")

        elif mode == 'db':
            print("[의원 데이터 DB 적재 시작]")
            db_conn = DatabaseManager()
            lawmaker_rows = self._build_lawmakers_rows(df_lawmakers)
            if lawmaker_rows:
                db_conn.update_lawmaker_info(lawmaker_rows)
                if run_stats:
                    db_conn.update_party_statistics()
                    print("[DB 통계 갱신 완료]")
                print(f"[DB 적재 완료] 총 {len(lawmaker_rows)}건")
            else:
                print("적재 대상 의원이 없어 DB 적재를 건너뜁니다.")

        elif mode == 'local':
            sender = APISender()
            url = self._to_local_url(url)
            sender.send_data(df_lawmakers, url, payload_name)
        
        elif mode == 'test':
            print("[테스트 모드 : DB에 데이터를 전송하지 않습니다.]")

        elif mode == 'save':
            df_lawmakers.to_csv('df_lawmakers.csv', index=False)

        return df_lawmakers

    def update_bills_timeline(self, start_date=None, end_date=None, age=None):
        """의정활동(법안 처리 단계) 데이터를 수집하고 모드에 따라 전송 또는 저장하는 메서드"""

        # 기본 날짜 설정: DB에 저장된 최신 날짜 다음 날부터 오늘까지
        if start_date is None:
            DBconn = DatabaseManager()
            latest_date = DBconn.get_latest_timeline_date()
            start_date = latest_date.strftime('%Y-%m-%d') if latest_date else (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')

        if age is None:
            age = os.getenv('AGE')

        # 데이터 수집
        fetcher = DataFetcher()
        df_stage = fetcher.fetch_bills_timeline(start_date=start_date, end_date=end_date, age=age)

        if df_stage is None or df_stage.empty:
            print("❌ [ERROR] 수집된 데이터가 없습니다.")
            return None

        # 필요한 컬럼만 선택
        df_stage = df_stage[['DT', 'BILL_ID', 'STAGE', 'COMMITTEE']]

        # 컬럼명 매핑
        column_mapping = {
            'DT': 'statusUpdateDate',
            'BILL_ID': 'billId',
            'STAGE': 'stage',
            'COMMITTEE': 'committee',
        }
        df_stage.rename(columns=column_mapping, inplace=True)

        print("데이터 개수 : ", len(df_stage))

        mode = self.mode

        payload_name = os.getenv('PAYLOAD_status')
        url = os.getenv('POST_URL_status')

        if mode == 'db':
            print("[타임라인 DB 적재 시작]")
            db_conn = DatabaseManager()
            bill_stage_rows = [
                self._build_bill_stage_row(row)
                for _, row in df_stage.iterrows()
                if self._coerce_optional_text(row.get("billId")) and self._coerce_optional_text(row.get("stage"))
            ]
            result = db_conn.update_bill_stage(bill_stage_rows)
            print(f"[DB 적재 완료] 총 {len(bill_stage_rows)}건")
            print(f"[타임라인 누락] {len(result['not_found_bill'])}건, [중복] {len(result['duplicate_bill'])}건")
            return df_stage

        sender = APISender()
        if mode == 'remote':
            chunks = list(self._chunk_dataframe(df_stage, self.CHUNK_SIZE))
            total_chunks = len(chunks)
            successful_chunks = 0
            failed_chunks = 0
            not_found_bill_count = 0

            for i, chunk in enumerate(chunks, 1):
                print(f"[청크 {i}/{total_chunks} 처리 중 (진행률: {i/total_chunks*100:.2f}%)]")
                try:
                    response = sender.send_data(chunk, url, payload_name)
                    response = response.json()
                    not_found_bill_count += len(response['data']['notFoundBill'])
                    print(f"[청크 {i} 데이터 전송 완료 (진행률: {i/total_chunks*100:.2f}%)]")
                    successful_chunks += 1
                except Exception as e:
                    print(f"[청크 {i} 처리 중 오류 발생: {e} (진행률: {i/total_chunks*100:.2f}%)]")
                    failed_chunks += 1

            print("[데이터 전송 완료]")
            print(f"전송 성공한 청크: {successful_chunks} / 전체 청크: {total_chunks} (성공률: {successful_chunks/total_chunks*100:.2f}%)")
            print(f"전송 실패한 청크: {failed_chunks} (실패율: {failed_chunks/total_chunks*100:.2f}%)")
            print(f"총 notFoundBill 항목의 개수: {not_found_bill_count}")

        elif mode == 'local':
            url = self._to_local_url(url)
            print(f'[로컬 모드 : {url}로 데이터 전송]')
            sender.send_data(df_stage, url, payload_name)

        elif mode == 'test':
            print('[테스트 모드 : 데이터 전송 생략]')

        elif mode == 'save':
            df_stage.to_csv('bills_status.csv', index=False)
            print('[데이터 저장 완료]')

        return df_stage

    def update_bills_result(self, start_date=None, end_date=None, age=None):
        """법안 처리 결과 데이터를 수집하고 모드에 따라 전송 또는 저장하는 메서드"""

        if start_date is None:
            start_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')

        if age is None:
            age = os.getenv('AGE')

        fetcher = DataFetcher()
        df_result = fetcher.fetch_bills_result(start_date=start_date, end_date=end_date, age=age)

        if df_result is None or df_result.empty:
            print("❌ [ERROR] 수집된 데이터가 없습니다.")
            return None

        df_result = df_result[['BILL_ID', 'PROC_RESULT_CD']]

        column_mapping = {
            'BILL_ID': 'billId',
            'PROC_RESULT_CD': 'billProposeResult'
        }

        df_result.rename(columns=column_mapping, inplace=True)

        print("데이터 개수 : ", len(df_result))

        mode = self.mode

        payload_name = os.getenv('PAYLOAD_result')
        url = os.getenv('POST_URL_result')
        if mode == 'db':
            print("[처리결과 DB 적재 시작]")
            db_conn = DatabaseManager()
            result_rows = [
                self._build_bill_result_row(row)
                for _, row in df_result.iterrows()
                if self._coerce_optional_text(row.get("billId"))
            ]
            if result_rows:
                db_conn.update_bill_result(result_rows)
                print(f"[DB 적재 완료] 총 {len(result_rows)}건")
            else:
                print("적재 대상 처리결과가 없어 DB 적재를 건너뜁니다.")

            return df_result

        sender = APISender()

        if mode == 'remote':
            chunks = list(self._chunk_dataframe(df_result, self.CHUNK_SIZE))
            total_chunks = len(chunks)

            for i, chunk in enumerate(chunks, 1):
                print(f"[청크 {i}/{total_chunks} 전송 중]")
                sender.send_data(chunk, url, payload_name)
                print(f"[청크 {i} 전송 완료]")

        elif mode == 'local':
            url = self._to_local_url(url)
            print(f'[로컬 모드 : {url}로 데이터 전송]')
            sender.send_data(df_result, url, payload_name)

        elif mode == 'test':
            print('[테스트 모드 : 데이터 전송 생략]')

        elif mode == 'save':
            df_result.to_csv('bills_result.csv', index=False)
            print('[데이터 저장 완료]')

        return df_result

    def update_bills_vote(self, start_date=None, end_date=None, age=None):
        """본회의 표결 결과 데이터를 수집하고 모드에 따라 전송 또는 저장하는 메서드"""

        if start_date is None:
            start_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')

        if age is None:
            age = os.getenv('AGE')

        fetcher = DataFetcher()
        df_vote = fetcher.fetch_bills_vote(start_date=start_date, end_date=end_date, age=age)

        if df_vote is None or df_vote.empty:
            print("❌ [ERROR] 수집된 표결 결과 데이터가 없습니다.")
            return None, None

        df_vote_party = fetcher.fetch_vote_party(start_date=start_date, end_date=end_date, age=age)

        columns_to_keep = [
            'BILL_ID',
            'VOTE_TCNT',
            'YES_TCNT',
            'NO_TCNT',
            'BLANK_TCNT'
        ]

        df_vote = df_vote[columns_to_keep]
        df_vote.dropna(subset=['VOTE_TCNT'], inplace=True)
        df_vote.fillna(0, inplace=True)

        column_mapping = {
            'BILL_ID': 'billId',
            'VOTE_TCNT': 'totalVoteCount',
            'YES_TCNT': 'voteForCount',
            'NO_TCNT': 'voteAgainstCount',
            'BLANK_TCNT': 'abstentionCount'
        }

        df_vote.rename(columns=column_mapping, inplace=True)

        mode = self.mode

        payload_vote = os.getenv('PAYLOAD_vote')
        url_vote = os.getenv('POST_URL_vote')

        if mode == 'db':
            print("[표결 데이터 DB 적재 시작]")
            db_conn = DatabaseManager()

            vote_rows = [
                self._build_vote_row(row)
                for _, row in df_vote.iterrows()
                if self._coerce_optional_text(row.get("billId"))
            ]
            if vote_rows:
                db_conn.insert_vote_record(vote_rows)
                print(f"[표결 집계 DB 적재 완료] 총 {len(vote_rows)}건")
            else:
                print("적재 대상 본회의 표결이 없어 DB 적재를 건너뜁니다.")

            if df_vote_party is not None and not df_vote_party.empty:
                vote_party_rows = [
                    self._build_vote_party_row(row)
                    for _, row in df_vote_party.iterrows()
                    if self._coerce_optional_text(row.get("billId")) and self._coerce_optional_text(row.get("partyName"))
                ]
                if vote_party_rows:
                    db_conn.insert_vote_party(vote_party_rows)
                    print(f"[정당별 표결 집계 DB 적재 완료] 총 {len(vote_party_rows)}건")
            else:
                print("[정당별 표결 집계 데이터가 없어 스킵]")

            return df_vote, df_vote_party

        sender = APISender()

        if mode == 'remote':
            chunks = list(self._chunk_dataframe(df_vote, self.CHUNK_SIZE))
            total_chunks = len(chunks)
            for i, df_chunk in enumerate(chunks, 1):
                print(f"[표결 데이터 청크 {i}/{total_chunks} 전송 중]")
                sender.send_data(df_chunk, url_vote, payload_vote)
        elif mode == 'local':
            url_vote = self._to_local_url(url_vote)
            print(f'[로컬 모드 : {url_vote}로 데이터 전송]')
            sender.send_data(df_vote, url_vote, payload_vote)
        elif mode == 'test':
            print('[테스트 모드 : 데이터 전송 생략]')
        elif mode == 'save':
            df_vote.to_csv('bills_vote.csv', index=False)
            print('[데이터 저장 완료]')

        if df_vote_party is None or df_vote_party.empty:
            print("❌ [ERROR] 정당별 표결 결과 데이터가 없습니다.")
            return df_vote, None

        payload_party = os.getenv('PAYLOAD_vote_party')
        url_party = os.getenv('POST_URL_vote_party')

        if mode == 'remote':
            chunks = list(self._chunk_dataframe(df_vote_party, self.CHUNK_SIZE))
            total_chunks = len(chunks)
            for i, df_chunk in enumerate(chunks, 1):
                print(f"[정당별 표결 청크 {i}/{total_chunks} 전송 중]")
                sender.send_data(df_chunk, url_party, payload_party)
        elif mode == 'local':
            url_party = self._to_local_url(url_party)
            print(f'[로컬 모드 : {url_party}로 데이터 전송]')
            sender.send_data(df_vote_party, url_party, payload_party)
        elif mode == 'test':
            print('[테스트 모드 : 데이터 전송 생략]')
        elif mode == 'save':
            df_vote_party.to_csv('vote_party.csv', index=False)
            print('[데이터 저장 완료]')

        return df_vote, df_vote_party

    def update_bills_alternatives(self, start_ord=None, end_ord=None):
        """대안-법안 관계 데이터를 수집하고 모드에 따라 저장 또는 전송하는 메서드"""

        fetch_mode = 'total'

        if fetch_mode != 'total':
            print("현재는 'total' 모드만 지원합니다.")
            return None

        api_key = os.environ.get("APIKEY_billsContent")
        url = 'http://apis.data.go.kr/9710000/BillInfoService2/getBillInfoList'

        params = {
            'serviceKey': api_key,
            'numOfRows': '100',
            'start_ord': start_ord or os.getenv('AGE'),
            'end_ord': end_ord or os.getenv('AGE'),
            'proposer_kind_cd': 'F02'
        }

        all_data = []
        pageNo = 1
        max_retry = 3
        start_time = time.time()

        while True:
            params.update({'pageNo': str(pageNo)})
            try:
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    root = ElementTree.fromstring(response.content)
                    items = root.find('body').find('items')
                    if items is None or len(items) == 0:
                        break
                    data = [{child.tag: child.text for child in item} for item in items]
                    all_data.extend(data)
                else:
                    print(f"❌ [ERROR] 응답 코드: {response.status_code} (Page {pageNo})")
                    max_retry -= 1
            except Exception as e:
                print(f"❌ [ERROR] 데이터 처리 중 오류 발생: {e}")
                max_retry -= 1

            if max_retry <= 0:
                print("🚨 [WARNING] 최대 재시도 횟수 초과! 데이터 수집 중단.")
                break

            pageNo += 1

        df_bills_content = pd.DataFrame(all_data)

        end_time = time.time()
        print(f"\n✅ [INFO] 모든 파일 다운로드 완료! ⏳ 전체 소요 시간: {end_time - start_time:.2f}초")
        print(f"📌 [INFO] 총 {len(df_bills_content)} 개의 법안 수집됨.")

        if df_bills_content.empty:
            print("❌ [ERROR] 수집한 데이터가 없습니다.")
            return None

        df_alt_ids = df_bills_content[['proposeDt', 'billId', 'proposerKind']]

        fetcher = DataFetcher()
        df_alternatives = fetcher.fetch_bills_alternatives(df_alt_ids)

        if df_alternatives is None or df_alternatives.empty:
            print("❌ [ERROR] 대안 데이터가 없습니다.")
            return None

        mode = self.mode

        payload_name = os.getenv('PAYLOAD_alternatives')
        url_post = os.getenv('POST_URL_alternatives')

        sender = APISender()

        if mode == 'remote' and url_post and payload_name:
            chunks = list(self._chunk_dataframe(df_alternatives, self.CHUNK_SIZE))
            total_chunks = len(chunks)
            for i, df_chunk in enumerate(chunks, 1):
                print(f"[대안 관계 청크 {i}/{total_chunks} 전송 중]")
                sender.send_data(df_chunk, url_post, payload_name)
        elif mode == 'local' and url_post and payload_name:
            url_post = self._to_local_url(url_post)
            print(f'[로컬 모드 : {url_post}로 데이터 전송]')
            sender.send_data(df_alternatives, url_post, payload_name)
        elif mode == 'test':
            print('[테스트 모드 : 데이터 전송 생략]')
        elif mode == 'save':
            df_alternatives.to_csv('bills_alternatives.csv', index=False)
            print('[데이터 저장 완료]')

        return df_alternatives

    def update_commitee_info(self):
        pass
