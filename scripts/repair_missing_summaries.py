"""
DB에 있는 AI Summary 결측치를 Fallback 로직으로 복구하는 스크립트

이 스크립트는 다음을 수행합니다:
1. CSV 파일에서 결측치 데이터 로드
2. AISummarizer의 Fallback 로직을 사용하여 AI 요약 재생성
3. 생성된 요약을 DB에 업데이트
4. 복구 결과 리포트 출력

사용법:
    python scripts/repair_missing_summaries.py [--input INPUT_PATH] [--dry-run]

인자:
    --input: 결측치 JSON 파일 경로 (기본값: data/missing_summaries.json)
    --dry-run: 실제 DB 업데이트 없이 시뮬레이션만 수행
    --batch-size: 한 번에 처리할 법안 개수 (기본값: 10)
"""

import sys
import os
import argparse
import pandas as pd
import json
from datetime import datetime
from typing import List, Dict

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from lawdigest_data_pipeline.DatabaseManager import DatabaseManager
from lawdigest_data_pipeline.AISummarizer import AISummarizer


def repair_missing_summaries(
    input_path: str = "data/missing_summaries.json",
    dry_run: bool = False,
    batch_size: int = 10
):
    """
    결측치 데이터에 대해 AI 요약을 재생성하고 DB 업데이트
    
    Args:
        input_path: 결측치 JSON 파일 경로
        dry_run: True이면 DB 업데이트하지 않고 시뮬레이션만 수행
        batch_size: 한 번에 처리할 법안 개수
    """
    print("=" * 80)
    print("🔧 AI Summary 결측치 복구 스크립트")
    if dry_run:
        print("⚠️  DRY-RUN 모드: 실제 DB 업데이트는 수행하지 않습니다.")
    print("=" * 80)
    
    # JSON 파일 로드
    print(f"\n[1/5] JSON 파일 로드 중: {input_path}")
    
    if not os.path.exists(input_path):
        print(f"❌ 파일을 찾을 수 없습니다: {input_path}")
        print(f"먼저 'python scripts/find_missing_summaries.py'를 실행하세요.")
        return
    
    with open(input_path, 'r', encoding='utf-8') as f:
        json_data = json.load(f)
    
    df = pd.DataFrame(json_data)
    print(f"✅ {len(df)}건의 결측치 데이터 로드 완료")
    
    if len(df) == 0:
        print("📝 복구할 데이터가 없습니다.")
        return
    
    # 결측치 타입 분류
    df['needs_brief'] = df['brief_summary'].isnull() | (df['brief_summary'] == '')
    df['needs_gpt'] = df['gpt_summary'].isnull() | (df['gpt_summary'] == '')
    
    brief_count = df['needs_brief'].sum()
    gpt_count = df['needs_gpt'].sum()
    
    print(f"\n   복구 대상:")
    print(f"   - brief_summary: {brief_count}건")
    print(f"   - gpt_summary: {gpt_count}건")
    
    # 배치 처리 계획
    total_batches = (len(df) + batch_size - 1) // batch_size
    print(f"\n   처리 계획: {total_batches}개 배치 (배치당 최대 {batch_size}건)")
    
    # AISummarizer 초기화
    print(f"\n[2/5] AISummarizer 초기화 중...")
    summarizer = AISummarizer()
    print("✅ AISummarizer 초기화 완료")
    
    # DB 연결
    print(f"\n[3/5] 데이터베이스 연결 중...")
    db_manager = DatabaseManager()
    db_manager.connect()
    
    if not db_manager.connection:
        print("❌ 데이터베이스 연결 실패")
        return
    
    print("✅ 데이터베이스 연결 성공")
    
    # 복구 통계
    stats = {
        'brief_success': 0,
        'brief_failed': 0,
        'gpt_success': 0,
        'gpt_failed': 0,
        'total_processed': 0
    }
    
    failed_bills = []
    
    try:
        print(f"\n[4/5] AI Summary 재생성 및 DB 업데이트 중...")
        print("-" * 80)
        
        # 배치 처리
        for batch_idx in range(total_batches):
            start_idx = batch_idx * batch_size
            end_idx = min((batch_idx + 1) * batch_size, len(df))
            batch_df = df.iloc[start_idx:end_idx].copy()
            
            print(f"\n📦 배치 {batch_idx + 1}/{total_batches} 처리 중 ({start_idx + 1}~{end_idx}번째)")
            
            # briefSummary 복구
            brief_to_repair = batch_df[batch_df['needs_brief']].copy()
            if len(brief_to_repair) > 0:
                print(f"   - brief_summary {len(brief_to_repair)}건 처리 중...")
                brief_result_df = summarizer.AI_title_summarize(brief_to_repair)
                
                # 성공한 건수 계산
                brief_success = brief_result_df['brief_summary'].notna().sum()
                stats['brief_success'] += brief_success
                stats['brief_failed'] += len(brief_to_repair) - brief_success
                
                print(f"     ✅ 성공: {brief_success}건, ❌ 실패: {len(brief_to_repair) - brief_success}건")
                
                # DB 업데이트
                if not dry_run:
                    for _, row in brief_result_df.iterrows():
                        if pd.notna(row['brief_summary']) and row['brief_summary'] != '':
                            update_query = """
                            UPDATE Bill 
                            SET brief_summary = %s 
                            WHERE bill_id = %s
                            """
                            db_manager.execute_query(update_query, (row['brief_summary'], row['bill_id']))
            
            # gpt_summary 복구
            gpt_to_repair = batch_df[batch_df['needs_gpt']].copy()
            if len(gpt_to_repair) > 0:
                print(f"   - gpt_summary {len(gpt_to_repair)}건 처리 중...")
                gpt_result_df = summarizer.AI_content_summarize(gpt_to_repair)
                
                # 성공한 건수 계산
                gpt_success = gpt_result_df['gpt_summary'].notna().sum()
                stats['gpt_success'] += gpt_success
                stats['gpt_failed'] += len(gpt_to_repair) - gpt_success
                
                print(f"     ✅ 성공: {gpt_success}건, ❌ 실패: {len(gpt_to_repair) - gpt_success}건")
                
                # DB 업데이트
                if not dry_run:
                    for _, row in gpt_result_df.iterrows():
                        if pd.notna(row['gpt_summary']) and row['gpt_summary'] != '':
                            update_query = """
                            UPDATE Bill 
                            SET gpt_summary = %s 
                            WHERE bill_id = %s
                            """
                            db_manager.execute_query(update_query, (row['gpt_summary'], row['bill_id']))
            
            stats['total_processed'] += len(batch_df)
            
            # 실패한 법안 기록
            if len(summarizer.failed_bills) > 0:
                failed_bills.extend(summarizer.failed_bills)
                summarizer.failed_bills = []  # 초기화
        
        # 커밋
        if not dry_run:
            db_manager.connection.commit()
            print("\n✅ DB 업데이트 커밋 완료")
        
        # 결과 리포트
        print(f"\n[5/5] 복구 결과 리포트")
        print("=" * 80)
        print(f"📊 총 처리: {stats['total_processed']}건")
        print(f"\n   brief_summary:")
        print(f"   - ✅ 성공: {stats['brief_success']}건")
        print(f"   - ❌ 실패: {stats['brief_failed']}건")
        print(f"\n   gpt_summary:")
        print(f"   - ✅ 성공: {stats['gpt_success']}건")
        print(f"   - ❌ 실패: {stats['gpt_failed']}건")
        
        # 실패한 법안 출력
        if len(failed_bills) > 0:
            print(f"\n⚠️  API 호출 실패로 복구하지 못한 법안: {len(failed_bills)}건")
            print("\n   실패 목록 (최대 10건 표시):")
            for i, failed in enumerate(failed_bills[:10], 1):
                print(f"   {i}. {failed['bill_name']} (ID: {failed['bill_id']})")
                print(f"      에러: {failed['error'][:100]}...")
            
            if len(failed_bills) > 10:
                print(f"   ... 외 {len(failed_bills) - 10}건")
            
            # 실패 목록 JSON 저장
            failed_path = input_path.replace('.json', '_failed.json')
            with open(failed_path, 'w', encoding='utf-8') as f:
                json.dump(failed_bills, f, ensure_ascii=False, indent=2)
            print(f"\n   실패 목록 JSON 저장: {failed_path}")
        
        print("\n" + "=" * 80)
        if dry_run:
            print("✅ DRY-RUN 완료! 실제 DB는 업데이트되지 않았습니다.")
        else:
            total_success = stats['brief_success'] + stats['gpt_success']
            print(f"✅ 복구 완료! 총 {total_success}건의 AI Summary를 복구했습니다.")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ 에러 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # 롤백
        if not dry_run and db_manager.connection:
            db_manager.connection.rollback()
            print("🔄 DB 롤백 완료")
    
    finally:
        # 연결 종료
        if db_manager.connection:
            db_manager.connection.close()
            print("\n🔌 데이터베이스 연결 종료")


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description="DB에 있는 AI Summary 결측치를 Fallback 로직으로 복구"
    )
    parser.add_argument(
        '--input',
        type=str,
        default='data/missing_summaries.json',
        help='결측치 JSON 파일 경로 (기본값: data/missing_summaries.json)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='실제 DB 업데이트 없이 시뮬레이션만 수행'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=10,
        help='한 번에 처리할 법안 개수 (기본값: 10)'
    )
    
    args = parser.parse_args()
    
    # 사용자 확인 (dry-run이 아닐 때만)
    if not args.dry_run:
        print("\n⚠️  주의: 이 작업은 실제 DB를 업데이트합니다.")
        response = input("계속 진행하시겠습니까? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print("작업이 취소되었습니다.")
            return
    
    repair_missing_summaries(args.input, args.dry_run, args.batch_size)


if __name__ == "__main__":
    main()
