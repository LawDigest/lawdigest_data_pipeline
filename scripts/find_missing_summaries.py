"""
기존 DB에서 AI Summary가 누락된 데이터를 조회하는 스크립트

이 스크립트는 다음을 수행합니다:
1. lawDB 데이터베이스에서 gptSummary 또는 briefSummary가 NULL인 법안 조회
2. 조회 결과를 CSV 파일로 저장
3. 통계 정보 출력

사용법:
    python scripts/find_missing_summaries.py [--output OUTPUT_PATH]

인자:
    --output: JSON 파일 저장 경로 (기본값: data/missing_summaries.json)
"""

import sys
import os
import argparse
import pandas as pd
import json
from datetime import datetime

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from lawdigest_data_pipeline.DatabaseManager import DatabaseManager


def find_missing_summaries(output_path: str = "data/missing_summaries.json"):
    """
    DB에서 AI summary가 누락된 법안을 조회하여 JSON으로 저장
    
    Args:
        output_path: CSV 파일 저장 경로
    """
    print("=" * 80)
    print("📊 AI Summary 결측치 조회 스크립트")
    print("=" * 80)
    
    # DatabaseManager 인스턴스 생성
    print("\n[1/4] 데이터베이스 연결 중...")
    db_manager = DatabaseManager()
    db_manager.connect()
    
    if not db_manager.connection:
        print("❌ 데이터베이스 연결 실패")
        return
    
    print("✅ 데이터베이스 연결 성공")
    
    try:
        # 결측치 조회 쿼리
        print("\n[2/4] AI Summary 결측치 조회 중...")
        
        query = """
        SELECT 
            bill_id,
            bill_name,
            summary,
            proposers,
            proposer_kind,
            brief_summary,
            gpt_summary,
            propose_date,
            stage
        FROM Bill
        WHERE 
            (gpt_summary IS NULL OR gpt_summary = '' OR brief_summary IS NULL OR brief_summary = '')
            AND summary IS NOT NULL
            AND summary != ''
        ORDER BY propose_date DESC
        """
        
        result = db_manager.execute_query(query)
        
        if not result:
            print("✅ 결측치가 없습니다. 모든 법안에 AI Summary가 존재합니다.")
            return
        
        # DataFrame으로 변환
        df = pd.DataFrame(result)
        
        # 통계 정보 출력
        print(f"\n[3/4] 조회 결과 분석")
        print(f"✅ 총 {len(df)}건의 결측치 발견")
        
        # brief_summary 결측치
        brief_missing = df['brief_summary'].isnull() | (df['brief_summary'] == '')
        print(f"   - brief_summary 결측: {brief_missing.sum()}건")
        
        # gpt_summary 결측치
        gpt_missing = df['gpt_summary'].isnull() | (df['gpt_summary'] == '')
        print(f"   - gpt_summary 결측: {gpt_missing.sum()}건")
        
        # 둘 다 결측
        both_missing = brief_missing & gpt_missing
        print(f"   - 둘 다 결측: {both_missing.sum()}건")
        
        # 발의주체별 통계
        print(f"\n   📊 발의주체별 분포:")
        proposer_counts = df['proposer_kind'].value_counts()
        for proposer_kind, count in proposer_counts.items():
            print(f"      - {proposer_kind}: {count}건")
        
        # 연도별 통계
        df['year'] = pd.to_datetime(df['propose_date']).dt.year
        print(f"\n   📅 연도별 분포:")
        year_counts = df['year'].value_counts().sort_index(ascending=False)
        for year, count in year_counts.head(5).items():
            print(f"      - {int(year)}년: {count}건")
        if len(year_counts) > 5:
            print(f"      - 기타: {year_counts[5:].sum()}건")
        
        # JSON으로 저장
        print(f"\n[4/4] JSON 파일 저장 중...")
        
        # 디렉토리 생성 (존재하지 않는 경우)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # JSON 저장
        df.drop(columns=['year'], inplace=True)  # year 컬럼 제거
        
        # 날짜 컬럼을 문자열로 변환 (JSON serialization을 위해)
        if 'propose_date' in df.columns:
            df['propose_date'] = df['propose_date'].astype(str)
        
        # DataFrame을 JSON으로 변환 (orient='records'는 배열 형식)
        json_data = df.to_dict(orient='records')
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ JSON 파일 저장 완료: {output_path}")
        print(f"   - 파일 크기: {os.path.getsize(output_path) / 1024:.2f} KB")
        
        # 샘플 데이터 출력
        print(f"\n📋 샘플 데이터 (최근 5건):")
        print("-" * 80)
        for idx, row in df.head(5).iterrows():
            print(f"\n{idx + 1}. [{row['bill_id']}] {row['bill_name']}")
            print(f"   발의자: {row['proposers']} ({row['proposer_kind']})")
            print(f"   발의일: {row['propose_date']}")
            brief_status = "❌" if pd.isna(row['brief_summary']) or row['brief_summary'] == '' else "✅"
            gpt_status = "❌" if pd.isna(row['gpt_summary']) or row['gpt_summary'] == '' else "✅"
            print(f"   brief_summary: {brief_status} | gpt_summary: {gpt_status}")
        
        print("\n" + "=" * 80)
        print(f"✅ 작업 완료! 결측치 {len(df)}건을 {output_path}에 저장했습니다.")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ 에러 발생: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 연결 종료
        if db_manager.connection:
            db_manager.connection.close()
            print("\n🔌 데이터베이스 연결 종료")


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description="DB에서 AI Summary가 누락된 법안을 조회하여 JSON으로 저장"
    )
    parser.add_argument(
        '--output',
        type=str,
        default='data/missing_summaries.json',
        help='JSON 파일 저장 경로 (기본값: data/missing_summaries.json)'
    )
    
    args = parser.parse_args()
    
    find_missing_summaries(args.output)


if __name__ == "__main__":
    main()
