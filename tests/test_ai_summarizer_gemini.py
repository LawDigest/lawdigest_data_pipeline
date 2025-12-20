import sys
import os
import pandas as pd
from dotenv import load_dotenv

# 프로젝트 루트 경로 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from lawdigest_data_pipeline.DataFetcher import DataFetcher
from lawdigest_data_pipeline.AISummarizer import AISummarizer
from lawdigest_data_pipeline.DataProcessor import DataProcessor

def test_gemini_summarization():
    load_dotenv()
    
    # 1. 데이터 수집
    print("Fetching bill data...")
    fetcher = DataFetcher()
    # 최근 데이터가 있을만한 날짜로 설정 (22대 국회 시작일 이후)
    df_bills = fetcher.fetch_bills_data(age=22, pIndex=1, pSize=10, retry=3)
    
    if df_bills.empty:
        print("수집된 법안 데이터가 없습니다. 테스트를 종료합니다.")
        return
    
    print(f"Fetched {len(df_bills)} bills.")

    # 2. 데이터 전처리 (DataProcessor 활용)
    # process_congressman_bills는 '의원' 발의 법안만 처리하므로, 테스트 데이터가 이에 맞는지 확인 필요
    # 대부분의 최신 법안은 의원 발의이거나 위원장 대안임.
    
    processor = DataProcessor(fetcher)
    
    # 'proposerKind'가 없으면 기본값 '의원' 설정 (DataFetcher에서 가져오지만 안전장치)
    if 'proposerKind' not in df_bills.columns:
         df_bills['proposerKind'] = '의원'
    
    # 의원 발의 법안만 필터링하여 처리 (process_congressman_bills 내부 로직과 맞춤)
    # 만약 수집된 데이터에 의원 발의안이 없다면 테스트가 어려울 수 있으니 확인
    df_congressman = df_bills[df_bills['proposerKind'] == '의원'].copy()
    
    if df_congressman.empty:
        print("⚠️ 수집된 법안 중 '의원' 발의 법안이 없습니다. 위원장/정부 발의안일 수 있습니다.")
        print(f"발의자 종류 분포: {df_bills['proposerKind'].value_counts()}")
        print("테스트를 위해 첫 번째 법안을 강제로 '의원' 발의로 간주하고 처리합니다.")
        df_test = df_bills.head(1).copy()
        df_test['proposerKind'] = '의원'
    else:
        df_test = df_congressman.head(1).copy()

    print(f"Processing bill: {df_test.iloc[0]['billName']}")
    
    # DataProcessor를 통해 proposers 생성 및 발의자 정보 병합
    # process_congressman_bills는 내부적으로 fetch_bills_coactors를 호출함
    df_test = processor.process_congressman_bills(df_test)
    
    if df_test.empty:
        print("❌ DataProcessor 처리 후 데이터가 없습니다. (공동발의자 정보 매칭 실패 등)")
        return

    print(f"Processed columns: {df_test.columns.tolist()}")
    if 'proposers' in df_test.columns:
        print(f"Generated proposers: {df_test.iloc[0]['proposers']}")

    # 결과 저장을 위한 컬럼 생성 확인
    if 'briefSummary' not in df_test.columns:
        df_test['briefSummary'] = None
    if 'gptSummary' not in df_test.columns:
        df_test['gptSummary'] = None
        
    # 3. 요약기 초기화
    summarizer = AISummarizer()
    # 사용자가 요청한 gemini-3-flash-preview 모델 사용
    gemini_model = "gemini-3-flash-preview"
    
    print(f"Using Gemini model: {gemini_model}")

    # 4. 제목 요약 실행
    print("-" * 30)
    print("Testing AI_title_summarize...")
    df_result = summarizer.AI_title_summarize(df_test, model=gemini_model)
    print("Result Brief Summary:", df_result.iloc[0]['briefSummary'])

    # 5. 내용 요약 실행
    print("-" * 30)
    print("Testing AI_content_summarize...")
    # gptSummary가 비어있어야 실행되므로 명시적으로 None 설정 (DataFetcher에서 가져온 경우 이미 None일 수 있음)
    df_result['gptSummary'] = None
    df_result = summarizer.AI_content_summarize(df_result, model=gemini_model)
    print("Result Content Summary:\n", df_result.iloc[0]['gptSummary'])

    # 6. 결과 저장 전 데이터 정제 (extras 및 signature 필드 제외)
    def clean_ai_response(value):
        if isinstance(value, list) and len(value) > 0 and isinstance(value[0], dict):
            return value[0].get('text', value)
        if isinstance(value, dict):
            return value.get('text', value)
        return value

    df_result['briefSummary'] = df_result['briefSummary'].apply(clean_ai_response)
    df_result['gptSummary'] = df_result['gptSummary'].apply(clean_ai_response)

    # 7. 결과 저장
    result_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'result'))
    if not os.path.exists(result_dir):
        os.makedirs(result_dir)
    
    output_path = os.path.join(result_dir, 'gemini_test_result.json')
    df_result.to_json(output_path, orient='records', force_ascii=False, indent=4)
    print("-" * 30)
    print(f"결과가 다음 경로에 저장되었습니다: {output_path}")

if __name__ == "__main__":
    test_gemini_summarization()
