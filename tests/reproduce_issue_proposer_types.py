
import sys
import os
import pandas as pd
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from datetime import datetime, timedelta

sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))
from lawdigest_data_pipeline.DataFetcher import DataFetcher

def reproduce_issue():
    """
    위원장안 및 정부법안 수집 및 대안(alternatives) 관계 정보 수집 검증 스크립트
    """
    print("🚀 [검증 시작] 위원장안 및 정부법안 기본 수집 및 대안 정보 확인")

    fetcher = DataFetcher()
    
    # 빠른 테스트를 위해 재시도 비활성화
    no_retry_strategy = Retry(total=0, status_forcelist=[500, 502, 503, 504], allowed_methods=["GET", "POST"])
    adapter = HTTPAdapter(max_retries=no_retry_strategy)
    fetcher.session.mount("http://", adapter)
    fetcher.session.mount("https://", adapter)

    # 1. 최근 데이터에서 위원장안/정부안 찾기
    print("\n🔍 1. 최근 법안 데이터에서 위원장안/정부안 검색 중...")
    
    found_bills = pd.DataFrame()
    age = "22" # 22대 국회
    
    try:
        # 최근 180일 검색
        end_date = datetime.now()
        start_date = end_date - timedelta(days=60)
        
        df_bills = fetcher.fetch_bills_data(
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
            age=age,
            retry=0
        )
        
        if df_bills.empty:
            print("⚠️ 법안 데이터가 없습니다. (API 이슈 혹은 휴회 기간)")
            return

        print(f"   - 수집된 총 법안 수: {len(df_bills)}")
        
        if 'proposerKind' not in df_bills.columns:
            print("❌ 'proposerKind' 컬럼이 없습니다.")
            return

        print(f"   - 발의자 종류 분포:\n{df_bills['proposerKind'].value_counts()}")

        targets = df_bills[df_bills['proposerKind'].isin(['위원장', '정부'])]
        
        if targets.empty:
             print("⚠️ 최근 기간 내 위원장안 또는 정부법안이 없습니다. 기간을 늘리거나 다른 대수를 시도해보세요.")
             return
             
        print(f"✅ 위원장안/정부법안 발견: {len(targets)}건")
        
        # 위원장안만 대안이 있을 확률이 높으므로 위원장안 우선 테스트
        chairman_bills = targets[targets['proposerKind'] == '위원장']
        if not chairman_bills.empty:
            print("\n👉 위원장안 샘플 5개에 대해 대안 정보(원안 목록) 수집을 시도합니다.")
            sample_targets = chairman_bills.head(5)
        else:
             print("\n👉 정부법안 샘플 5개에 대해 테스트합니다 (대안 정보가 없을 수 있음).")
             sample_targets = targets.head(5)

        print(sample_targets[['proposeDate', 'billName', 'proposerKind']])
        found_bills = sample_targets

    except Exception as e:
        print(f"❌ 법안 검색 중 오류 발생: {e}")
        return

    # 2. fetch_bills_alternatives 실행 및 결과 확인
    print("\n🔬 2. 대안 정보(alternatives) 수집 시도...")
    
    alternatives_df = fetcher.fetch_bills_alternatives(df_bills=found_bills, max_retry=0)
    
    print(f"\n📊 3. 결과 분석")
    print(f"   - 입력 법안 수: {len(found_bills)}")
    print(f"   - 결과(alternatives) 관계 수: {len(alternatives_df)}")
    
    if alternatives_df.empty:
         print("⚠️ 대안 정보가 수집되지 않았습니다. (해당 법안들이 대안이 아니거나, API 연동 문제일 수 있음)")
         # 추가 확인: 정말 대안이 아닌지? (법안 이름에 '대안'이 포함되는지 확인)
         alt_candidates = found_bills[found_bills['billName'].str.contains('대안')]
         if not alt_candidates.empty:
             print(f"   ⚠️ 이름에 '대안'이 포함된 법안이 {len(alt_candidates)}건 있었으나 데이터를 가져오지 못했습니다.")
             print(f"      - ID 예시: {alt_candidates['billId'].tolist()}")
    else:
        print("   - 수집된 데이터 샘플:")
        print(alternatives_df.head())
        print("✅ 대안 정보 수집 성공.")

if __name__ == "__main__":
    reproduce_issue()
