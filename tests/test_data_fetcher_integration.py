import pytest
import pandas as pd
import sys
import os
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from datetime import datetime, timedelta
from lawdigest_data_pipeline.DataFetcher import DataFetcher
from test_utils import find_valid_date_and_data, save_test_result

@pytest.fixture
def fetcher():
    """DataFetcher 인스턴스를 생성하고 재시도를 비활성화하는 Fixture"""
    f = DataFetcher()
    # 세션 레벨의 재시도 비활성화
    no_retry_strategy = Retry(
        total=0,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
        raise_on_status=False
    )
    adapter = HTTPAdapter(max_retries=no_retry_strategy)
    f.session.mount("http://", adapter)
    f.session.mount("https://", adapter)
    return f

def test_fetch_lawmakers_data(fetcher):
    """국회의원 데이터 수집 테스트"""
    print("\n📌 [TEST] 국회의원 데이터 수집")
    # fetch_lawmakers_data 내부에서 fetch_data_generic을 호출하므로 max_retry 전달
    df = fetcher.fetch_lawmakers_data(max_retry=0)
    
    if df is None:
        pytest.fail("fetch_lawmakers_data returned None")
        
    assert isinstance(df, pd.DataFrame)
    save_test_result("fetch_lawmakers_data", df)
    
    if not df.empty:
        required_columns = ['HG_NM', 'MONA_CD', 'POLY_NM']
        for col in required_columns:
            assert col in df.columns, f"Missing column: {col}"
    else:
        print("⚠️ 국회의원 데이터가 비어있습니다 (API 문제 가능성)")

def test_fetch_bills_data_auto(fetcher):
    """최근 데이터가 존재하는 날짜를 자동으로 찾아 법안 데이터 수집 테스트"""
    print("\n📌 [TEST] 동적 날짜 탐색: 법안 데이터 수집")
    
    # retry=0 전달
    found_date, df = find_valid_date_and_data(fetcher.fetch_bills_data, age="22", max_days=30, retry=0)
    
    if found_date is None:
        pytest.skip("⚠️ 최근 30일간 법안 데이터를 찾을 수 없어 테스트를 건너뜁니다.")
        
    assert isinstance(df, pd.DataFrame)
    print(f"✅ 발견된 날짜: {found_date}, 수집된 법안 수: {len(df)}")
    save_test_result("fetch_bills_data", df)
    
    required_columns = ['billId', 'billName', 'proposeDate']
    for col in required_columns:
        assert col in df.columns, f"Missing column: {col}"

def test_fetch_bills_coactors_auto(fetcher):
    """공동발의자 정보 수집 테스트 (동적 날짜 사용)"""
    print("\n📌 [TEST] 동적 날짜 탐색: 공동발의자 정보 수집")
    
    # retry=0 전달
    found_date, bills_df = find_valid_date_and_data(fetcher.fetch_bills_data, age="22", max_days=30, retry=0)
    
    if bills_df is None or bills_df.empty:
        pytest.skip("법안 데이터가 없어 공동발의자 테스트를 건너뜁니다.")
    
    # 상위 3개만 테스트
    sample_bills = bills_df.head(3)
    
    # 공동발의자 수집 (DataFetcher에서 generic 호출 시 세션 사용)
    coactors_df = fetcher.fetch_bills_coactors(df_bills=sample_bills)
    
    assert isinstance(coactors_df, pd.DataFrame)
    save_test_result("fetch_bills_coactors", coactors_df)
    
    if coactors_df.empty:
         pytest.fail("⚠️ 공동발의자 정보가 수집되지 않았습니다. API 응답 로그를 확인하세요.")
        
    required_cols = ['billId', 'publicProposerIdList']
    for col in required_cols:
        assert col in coactors_df.columns

def test_fetch_bills_timeline_auto(fetcher):
    """의정활동 타임라인 수집 테스트 (동적 날짜 사용)"""
    print("\n📌 [TEST] 동적 날짜 탐색: 의정활동 타임라인 수집")
    
    # max_retry=0 전달
    found_date, df = find_valid_date_and_data(fetcher.fetch_bills_timeline, age="22", max_days=60, max_retry=0)
    
    if df is None:
        pytest.skip("⚠️ 최근 60일간 타임라인 데이터를 찾을 수 없어 테스트를 건너뜁니다.")
        
    assert isinstance(df, pd.DataFrame)
    print(f"✅ 발견된 날짜: {found_date}, 수집된 타임라인 건수: {len(df)}")
    save_test_result("fetch_bills_timeline", df)

def test_fetch_bills_result_auto(fetcher):
    """법안 결과 데이터 수집 테스트 (동적 날짜 사용)"""
    print("\n📌 [TEST] 동적 날짜 탐색: 법안 결과 데이터 수집")
    
    # max_retry=0 전달
    found_date, df = find_valid_date_and_data(fetcher.fetch_bills_result, age="22", max_days=90, max_retry=0)
    
    if df is None:
        pytest.skip("⚠️ 최근 90일간 법안 결과 데이터를 찾을 수 없어 테스트를 건너뜁니다.")
        
    assert isinstance(df, pd.DataFrame)
    print(f"✅ 발견된 날짜: {found_date}, 수집된 법안 결과 건수: {len(df)}")
    save_test_result("fetch_bills_result", df)
    
    required_cols = ['BILL_ID', 'PROC_RESULT_CD']
    for col in required_cols:
        assert col in df.columns, f"Missing column: {col}"

def test_fetch_bills_vote_auto(fetcher):
    """본회의 표결 데이터 수집 테스트 (동적 날짜 사용)"""
    print("\n📌 [TEST] 동적 날짜 탐색: 본회의 표결 데이터 수집")
    
    # max_retry=0 전달
    found_date, df = find_valid_date_and_data(fetcher.fetch_bills_vote, age="22", max_days=90, max_retry=0)
    
    if df is None:
        pytest.skip("⚠️ 최근 90일간 표결 데이터를 찾을 수 없어 테스트를 건너뜁니다.")
        
    assert isinstance(df, pd.DataFrame)
    print(f"✅ 발견된 날짜: {found_date}, 수집된 표결 데이터 건수: {len(df)}")
    save_test_result("fetch_bills_vote", df)
    
    required_cols = ['BILL_NO', 'VOTE_TCNT', 'YES_TCNT']
    for col in required_cols:
        assert col in df.columns, f"Missing column: {col}"

def test_fetch_vote_party_auto(fetcher):
    """정당별 표결 결과 집계 테스트 (동적 날짜 사용)"""
    print("\n📌 [TEST] 동적 날짜 탐색: 정당별 표결 결과 집계")
    
    # 1. 표결 데이터가 있는 날짜 찾기 (max_retry=0)
    found_date, vote_df = find_valid_date_and_data(fetcher.fetch_bills_vote, age="22", max_days=90, max_retry=0)
    
    if vote_df is None or vote_df.empty:
        pytest.skip("⚠️ 최근 90일간 표결 데이터를 찾을 수 없어 정당별 집계 테스트를 건너뜁니다.")
        
    # 2. 정당별 집계 수행 (상위 3개 법안, max_retry=0)
    sample_vote_df = vote_df.head(3)
    party_vote_df = fetcher.fetch_vote_party(df_vote=sample_vote_df, max_retry=0)
    
    assert isinstance(party_vote_df, pd.DataFrame)
    save_test_result("fetch_vote_party", party_vote_df)
    
    if not party_vote_df.empty:
        required_cols = ['billId', 'partyName', 'voteForCount']
        for col in required_cols:
            assert col in party_vote_df.columns
        assert party_vote_df['partyName'].nunique() > 0
    else:
        print("⚠️ 정당별 표결 데이터가 집계되지 않았습니다 (정당 정보 매칭 실패 등).")

def test_fetch_bills_alternatives_auto(fetcher):
    """대안 법안 데이터 수집 테스트 (동적 날짜 사용 - 대안 발의 찾기)"""
    print("\n📌 [TEST] 동적 날짜 탐색: 대안 법안 데이터 수집")

    # retry=0 전달
    found_date, df_bills = find_valid_date_and_data(
        fetcher.fetch_bills_data, 
        age="22", 
        max_days=180, 
        proposer_kind_cd='F02',
        retry=0
    )
    
    if df_bills is None or df_bills.empty:
        pytest.skip("⚠️ 최근 180일간 위원장 대안 발의 법안을 찾을 수 없어 테스트를 건너뜁니다.")

    # 상위 3개만 테스트
    target_bills = df_bills.head(3)
    print(f"👉 테스트 대상 법안 ID (발견된 날짜: {found_date}): {target_bills['billId'].tolist()}")

    df_alternatives = fetcher.fetch_bills_alternatives(df_bills=target_bills, max_retry=0)

    assert isinstance(df_alternatives, pd.DataFrame)
    save_test_result("fetch_bills_alternatives", df_alternatives)
    
    if df_alternatives.empty:
        pytest.fail("⚠️ 대안 데이터가 수집되지 않았습니다. API 키나 응답을 확인하세요.")
    
    required_cols = ['altBillId', 'billId']
    for col in required_cols:
        assert col in df_alternatives.columns, f"Missing column: {col}"
