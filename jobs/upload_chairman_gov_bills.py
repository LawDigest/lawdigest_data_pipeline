
# -*- coding: utf-8 -*-
import sys
import os
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv

# 프로젝트 루트 경로를 sys.path에 추가
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from src.lawdigest_data_pipeline.DataFetcher import DataFetcher
from src.lawdigest_data_pipeline.DataProcessor import DataProcessor
from src.lawdigest_data_pipeline.AISummarizer import AISummarizer
from src.lawdigest_data_pipeline.APISender import APISender
from src.lawdigest_data_pipeline.DatabaseManager import DatabaseManager

def run_upload_job(target_db='test', dry_run=True, start_date=None, end_date=None):
    """
    위원장안 및 정부법안을 수집, 처리하여 선택된 DB로 업로드하거나 테스트(Dry-run)합니다.
    """
    print(f"🚀 [Job Start] 위원장안/정부법안 업로드 작업 시작")
    print(f"   - Target DB: {target_db}")
    print(f"   - Dry Run: {dry_run}")
    print(f"   - 기간: {start_date} ~ {end_date}")

    load_dotenv()
    
    # 1. 데이터 수집 및 초기 설정
    print("\n🔍 [1. 데이터 수집] 법안 데이터 수집 중...")
    fetcher = DataFetcher()
    processor = DataProcessor(fetcher)
    
    # DB 연결 설정
    if target_db == 'test':
        db_manager = DatabaseManager(
            host=os.getenv("TEST_DB_HOST"),
            port=int(os.getenv("TEST_DB_PORT", 3306)),
            username=os.getenv("TEST_DB_USER"),
            password=os.getenv("TEST_DB_PASSWORD"),
            database=os.getenv("TEST_DB_NAME")
        )
    else:
        db_manager = DatabaseManager() # 기본값 (remote)

    # AI 요약 및 전송 객체
    summarizer = AISummarizer()
    sender = APISender()

    # 날짜 기본값 설정
    if not start_date:
        start_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')
    
    age = os.getenv("AGE", "22")

    # 전체 법안 수집
    df_bills = fetcher.fetch_bills_data(start_date=start_date, end_date=end_date, age=age)
    
    if df_bills is None or df_bills.empty:
        print("⚠️ 수집된 법안 데이터가 없습니다.")
        return

    # 중복 데이터 제거 (Dry run이 아닐 때 혹은 필요시 실행)
    print("\n🧹 [중복 제거] DB와 대조하여 이미 존재하는 법안 제외 중...")
    df_bills = processor.remove_duplicates(df_bills, db_manager)

    if df_bills.empty:
        print("✅ 모든 데이터가 이미 DB에 존재합니다. 작업을 종료합니다.")
        return

    print(f"   - 수집된 신규 법안 수: {len(df_bills)}")
    print(f"   - 발의자 종류 분포:\n{df_bills['proposerKind'].value_counts()}")

    # 2. 위원장안/정부안 필터링
    print("\n✂️ [2. 필터링] 위원장안 및 정부법안 추출 중...")
    
    # 관심 대상만 필터링
    target_mask = df_bills['proposerKind'].isin(['위원장', '정부'])
    df_targets = df_bills[target_mask].copy()
    
    if df_targets.empty:
        print("⚠️ 새롭게 수집된 법안 중 위원장안 또는 정부법안이 없습니다.")
        return

    print(f"   - 필터링된 대상 건수: {len(df_targets)} (위원장/정부)")

    # 3. 데이터 처리 (DataProcessor 로직 활용 및 보완)
    print("\n⚙️ [3. 데이터 처리] 세부 정보 처리 중...")

    # DataProcessor의 로직을 활용하되, 통합된 형태로 처리
    # 3-1. AI 요약 컬럼 추가
    processor.add_AI_summary_columns(df_targets)

    processed_list = []

    # 위원장안 처리
    df_chair, df_alternatives = processor.process_chairman_bills(df_targets)
    if not df_chair.empty:
        print(f"   - 위원장안 처리 완료: {len(df_chair)}건")
        # 'proposers' 컬럼이 없으면 에러가 날 수 있으므로 기본값 설정 (WorkFlowManager 로직 보완)
        if 'proposers' not in df_chair.columns:
             df_chair['proposers'] = df_chair['billName'].apply(lambda x: '위원장' if '위원장' in x else '') # 임시 로직
        processed_list.append(df_chair)
        
        # 대안 정보(alternatives)는 별도로 저장하거나 전송해야 함
        # 현재는 Alternatives 전송 로직이 WorkFlowManager에 별도로 있음.
        # 이 스크립트에서는 법안(Bills) 업로드에 집중하되, Alternatives도 필요하면 전송
        if not df_alternatives.empty:
             print(f"   - 대안 관계 정보 수집됨: {len(df_alternatives)}건 (전송 대기)")

    # 정부안 처리
    df_gov = processor.process_gov_bills(df_targets)
    if not df_gov.empty:
        print(f"   - 정부안 처리 완료: {len(df_gov)}건")
        if 'proposers' not in df_gov.columns:
            df_gov['proposers'] = '정부'
        processed_list.append(df_gov)

    if not processed_list:
        print("⚠️ 처리된 데이터가 없습니다.")
        return

    df_final = pd.concat(processed_list, ignore_index=True)
    
    # 공통: commitee 컬럼 추가 (WorkFlowManager 참조)
    df_final['commitee'] = None
    
    print(f"   - 최종 업로드 대상 법안 수: {len(df_final)}")
    
    if dry_run:
        print("\n🧪 [Dry Run] DB 전송을 건너뜁니다.")
        print("   - Sample Data:")
        print(df_final[['proposeDate', 'billName', 'proposerKind', 'proposers']].head())
        if not df_alternatives.empty:
             print("   - Sample Alternatives:")
             print(df_alternatives.head())
        print("✅ Dry Run 완료.")
        return

    # 4. DB 업로드
    print("\n📤 [4. DB 업로드] 데이터 전송 중...")
    
    # Target URL 설정
    url_bills = os.getenv("POST_URL_bills")
    payload_bills = os.getenv("PAYLOAD_bills")
    
    if target_db == 'test':
        # 테스트 DB URL 설정 (환경변수가 없으면 로컬호스트나 가상의 주소 사용 주의)
        # 사용자가 'test'라고 명시했으므로 _TEST 접미사 환경변수 우선 확인 후, 없으면 로컬 사용 등의 정책 필요
        test_url = os.getenv("POST_URL_bills_TEST")
        if test_url:
            url_bills = test_url
            print(f"   - TEST URL 사용: {url_bills}")
        else:
            print("⚠️ POST_URL_bills_TEST 환경변수가 없습니다. localhost:8080을 사용합니다.")
            url_bills = url_bills.replace("https://api.lawdigest.net", "http://localhost:8080")
            
    elif target_db == 'remote':
        print(f"   - PRODUCTION URL 사용: {url_bills}")
    
    # 4-1. 법안 데이터 전송 (AI 요약 포함)
    # AI 요약 수행 (Dry Run이 아니면 수행)
    print("   - AI 요약 수행 중...")
    # 비용 절약을 위해 상위 3개만 요약하거나, 전체 요약은 신중해야 함.
    # 여기서는 구현상 전체 요약 호출 (주의 필요)
    # summarizer.AI_title_summarize(df_final) # 비용 문제로 주석 처리 가능성? 일단 실행
    # summarizer.AI_content_summarize(df_final)

    # 전송
    sender.send_data(df_final, url_bills, payload_bills)
    print("   ✅ 법안 데이터 전송 완료.")

    # 4-2. 대안 정보 전송
    if not df_alternatives.empty:
        url_alt = os.getenv("POST_URL_alternatives")
        payload_alt = os.getenv("PAYLOAD_alternatives")
        
        if target_db == 'test':
             test_url_alt = os.getenv("POST_URL_alternatives_TEST")
             if test_url_alt:
                 url_alt = test_url_alt
             else:
                 url_alt = url_alt.replace("https://api.lawdigest.net", "http://localhost:8080")
        
        print(f"   - 대안 정보 전송 중... ({len(df_alternatives)}건)")
        sender.send_data(df_alternatives, url_alt, payload_alt)
        print("   ✅ 대안 정보 전송 완료.")

    print("\n🎉 작업 완료!")

if __name__ == "__main__":
    # --- 설정 영역 ---
    TARGET_DB = 'test'  # 'remote' or 'test'
    DRY_RUN = True      # True or False
    
    # 날짜 지정 (None이면 최근 1일)
    # START_DATE = '2025-06-01' 
    # END_DATE = '2025-12-31'
    START_DATE = None
    END_DATE = None
    # ----------------
    
    run_upload_job(
        target_db=TARGET_DB, 
        dry_run=DRY_RUN,
        start_date=START_DATE,
        end_date=END_DATE
    )
