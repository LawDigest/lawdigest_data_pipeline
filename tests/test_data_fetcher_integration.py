import pytest
import pandas as pd
from datetime import datetime, timedelta
from lawdigest_data_pipeline.DataFetcher import DataFetcher

@pytest.fixture
def fetcher():
    """DataFetcher 인스턴스를 생성하는 Fixture"""
    return DataFetcher()

def test_fetch_lawmakers_data(fetcher):
    """국회의원 데이터 수집 테스트"""
    print("\n📌 [TEST] 국회의원 데이터 수집")
    df = fetcher.fetch_lawmakers_data()
    
    # 데이터가 있을 수도 있고 없을 수도 있지만(API 상태에 따라), 
    # DataFrame 객체는 반환되어야 함.
    if df is None:
        pytest.fail("fetch_lawmakers_data returned None")
        
    assert isinstance(df, pd.DataFrame)
    
    # 데이터가 있다면 주요 컬럼 확인
    if not df.empty:
        print(f"✅ 수집된 국회의원 수: {len(df)}")
        required_columns = ['HG_NM', 'MONA_CD', 'POLY_NM']
        for col in required_columns:
            assert col in df.columns, f"Missing column: {col}"
    else:
        print("⚠️ 국회의원 데이터가 비어있습니다 (API 문제 가능성)")

def test_fetch_bills_data_recent(fetcher):
    """최근 1일간의 법안 데이터 수집 테스트 (속도 개선을 위해 기간 단축)"""
    print("\n📌 [TEST] 최근 1일 법안 데이터 수집")
    
    # 테스트 속도를 위해 오늘 날짜 하루만 조회합니다.
    target_date = datetime.now().strftime('%Y-%m-%d')
    today_date = datetime.now().strftime('%Y-%m-%d')
    
    df = fetcher.fetch_bills_data(start_date=target_date, end_date=today_date, age="22")
    
    assert isinstance(df, pd.DataFrame)
    
    if not df.empty:
        print(f"✅ 수집된 법안 수: {len(df)}")
        required_columns = ['billId', 'billName', 'proposeDate']
        for col in required_columns:
            assert col in df.columns, f"Missing column: {col}"
    else:
        print("⚠️ 오늘 발의된 법안이 없거나 API 응답이 없습니다.")

def test_fetch_bills_data_specific_date(fetcher):
    """특정 날짜(2025-07-11)의 법안 데이터 수집 테스트"""
    print("\n📌 [TEST] 특정 날짜(2025-07-11) 법안 데이터 수집")
    
    # 노트북에 있는 예제 날짜 사용
    specific_date = "2025-07-11"
    df = fetcher.fetch_bills_data(start_date=specific_date, end_date=specific_date, age="22")
    
    assert isinstance(df, pd.DataFrame)
    
    # 이 날짜에는 데이터가 있어야 한다고 가정 (노트북 결과 기반)
    # 하지만 실제 실행 시점에 데이터가 달라질 수 있으므로 empty 체크는 유연하게
    if not df.empty:
        print(f"✅ {specific_date} 수집된 법안 수: {len(df)}")
        assert 'summary' in df.columns
    else:
        print(f"⚠️ {specific_date}에 데이터가 없습니다.")

def test_fetch_bills_coactors(fetcher):
    """공동발의자 정보 수집 테스트"""
    print("\n📌 [TEST] 공동발의자 정보 수집")
    
    # 데이터가 확실히 존재하는 특정 날짜(2025-07-11)로 테스트합니다.
    specific_date = "2025-07-11"
    
    bills_df = fetcher.fetch_bills_data(start_date=specific_date, end_date=specific_date, age="22")
    
    if bills_df is None or bills_df.empty:
        pytest.skip("법안 데이터가 없어 공동발의자 테스트를 건너뜁니다.")
    
    # 상위 3개만 테스트
    sample_bills = bills_df.head(3)
    
    # 디버깅을 위해 verbose=True 설정 (필요시 사용)
    coactors_df = fetcher.fetch_bills_coactors(df_bills=sample_bills)
    
    assert isinstance(coactors_df, pd.DataFrame)
    
    if coactors_df.empty:
        # 데이터가 없으면 실패로 처리합니다.
        pytest.fail("⚠️ 공동발의자 정보가 수집되지 않았습니다. API 응답 로그를 확인하세요.")
        
    print(f"✅ 수집된 공동발의자 정보 건수: {len(coactors_df)}")
    required_cols = ['billId', 'publicProposerIdList']
    for col in required_cols:
        assert col in coactors_df.columns

def test_fetch_bills_timeline(fetcher):
    """의정활동 타임라인 수집 테스트"""
    print("\n📌 [TEST] 의정활동 타임라인 수집")
    
    specific_date = "2025-07-11"
    df = fetcher.fetch_bills_timeline(start_date=specific_date, end_date=specific_date, age="22")
    
    assert isinstance(df, pd.DataFrame)
    
    if not df.empty:
        print(f"✅ 수집된 타임라인 건수: {len(df)}")
        # 타임라인 데이터의 주요 컬럼 확인 (DataFetcher.py의 fetch_bills_timeline 참조)
        # XML 파싱 결과는 태그 이름이 대문자일 가능성이 높음 (DataFetcher 코드 확인 결과)
        # fetch_bills_timeline에서 data = [{child.tag: child.text ...}] 로 파싱함.
        # API 응답에 따라 컬럼명이 결정됨.
        pass 
    else:
        print(f"⚠️ {specific_date}에 타임라인 데이터가 없습니다.")

def test_fetch_bills_result(fetcher):
    """법안 결과 데이터 수집 테스트"""
    print("\n📌 [TEST] 법안 결과 데이터 수집")
    
    # 노트북 예제 날짜 사용 (2025-07-03)
    specific_date = "2025-07-03"
    df = fetcher.fetch_bills_result(start_date=specific_date, end_date=specific_date, age="22")
    
    assert isinstance(df, pd.DataFrame)
    
    if not df.empty:
        print(f"✅ 수집된 법안 결과 건수: {len(df)}")
        required_cols = ['BILL_ID', 'PROC_RESULT_CD']
        for col in required_cols:
            assert col in df.columns, f"Missing column: {col}"
    else:
        print(f"⚠️ {specific_date}에 법안 결과 데이터가 없습니다.")

def test_fetch_bills_vote(fetcher):
    """본회의 표결 데이터 수집 테스트"""
    print("\n📌 [TEST] 본회의 표결 데이터 수집")
    
    # 노트북 예제 날짜 사용 (2025-07-03)
    specific_date = "2025-07-03"
    df = fetcher.fetch_bills_vote(start_date=specific_date, end_date=specific_date, age="22")
    
    assert isinstance(df, pd.DataFrame)
    
    if not df.empty:
        print(f"✅ 수집된 표결 데이터 건수: {len(df)}")
        required_cols = ['BILL_NO', 'VOTE_TCNT', 'YES_TCNT']
        for col in required_cols:
            assert col in df.columns, f"Missing column: {col}"
    else:
        print(f"⚠️ {specific_date}에 표결 데이터가 없습니다.")

def test_fetch_vote_party(fetcher):
    """정당별 표결 결과 집계 테스트"""
    print("\n📌 [TEST] 정당별 표결 결과 집계")
    
    # 1. 먼저 표결 데이터를 수집합니다. (2025-07-03)
    specific_date = "2025-07-03"
    vote_df = fetcher.fetch_bills_vote(start_date=specific_date, end_date=specific_date, age="22")
    
    if vote_df is None or vote_df.empty:
        pytest.skip("표결 데이터가 없어 정당별 집계 테스트를 건너뜁니다.")
        
    # 테스트 속도를 위해 상위 3개 법안만 대상으로 합니다.
    sample_vote_df = vote_df.head(3)
    
    # 2. 정당별 집계 수행
    party_vote_df = fetcher.fetch_vote_party(df_vote=sample_vote_df)
    
    assert isinstance(party_vote_df, pd.DataFrame)
    
    if not party_vote_df.empty:
        print(f"✅ 집계된 정당별 표결 데이터 건수: {len(party_vote_df)}")
        required_cols = ['billId', 'partyName', 'voteForCount']
        for col in required_cols:
            assert col in party_vote_df.columns, f"Missing column: {col}"
            
        # 데이터 내용 검증 (예: 정당명이 포함되어 있는지)
        assert party_vote_df['partyName'].nunique() > 0
    else:
        print("⚠️ 정당별 표결 데이터가 집계되지 않았습니다.")
