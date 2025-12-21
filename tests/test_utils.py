from datetime import datetime, timedelta
import pandas as pd
import os
import io
import json
from typing import Callable, Optional, Tuple, Any

def save_test_result(test_name: str, df: pd.DataFrame):
    """
    테스트 결과를 tests/result 폴더에 JSON 및 Markdown 테이블 형식으로 저장하고,
    데이터프레임의 info() 정보를 출력합니다.
    """
    if df is None or not isinstance(df, pd.DataFrame):
        print(f"⚠️ [SAVE] {test_name}: 저장할 유효한 데이터프레임이 없습니다.")
        return

    # 1. 경로 설정 및 생성
    result_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "result")
    os.makedirs(result_dir, exist_ok=True)

    # 2. 파일명 설정 (타임스탬프 제거하여 덮어쓰기 유도)
    base_filename = f"{test_name}"

    # 3. JSON 저장
    json_path = os.path.join(result_dir, f"{base_filename}.json")
    df.to_json(json_path, orient="records", force_ascii=False, indent=4)
    print(f"💾 [SAVE] JSON 업데이트 완료: {json_path}")

    # 4. Markdown 저장
    md_path = os.path.join(result_dir, f"{base_filename}.md")
    # 너무 큰 데이터는 MD 표로 만들기에 부적합할 수 있으므로 상위 20개만 저장
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# Latest Test Result: {test_name}\n\n")
        f.write(f"- **Last Updated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"- **Total Rows**: {len(df)}\n\n")
        f.write("## Data Sample (Top 20)\n\n")
        try:
            f.write(df.head(20).to_markdown(index=False))
        except ImportError:
            # tabulate 패키지가 없는 경우 대비
            f.write(df.head(20).to_string(index=False))
            print("⚠️ [SAVE] 'tabulate' 패키지가 없어 MD 테이블 형식이 기본 텍스트로 저장되었습니다.")
            
    print(f"💾 [SAVE] MD 업데이트 완료: {md_path}")

    # 5. DataFrame info() 출력
    print("\nℹ️ [INFO] DataFrame Information:")
    buffer = io.StringIO()
    df.info(buf=buffer)
    print(buffer.getvalue())

def find_valid_date_and_data(
    fetch_method: Callable,
    age: str = "22",
    max_days: int = 60,
    **kwargs
) -> Tuple[Optional[str], Optional[pd.DataFrame]]:
    """
    오늘부터 과거로 하루씩 이동하며 fetch_method를 실행하여
    데이터가 존재하는 날짜와 데이터를 반환합니다.

    Args:
        fetch_method (Callable): 실행할 DataFetcher 메서드 (예: fetcher.fetch_bills_data)
        age (str): 국회 대수
        max_days (int): 최대 탐색 일수 (기본값: 60)
        **kwargs: fetch_method에 전달할 추가 인자 (예: proposer_kind_cd='F02')

    Returns:
        Tuple[str, pd.DataFrame]: (데이터가 있는 날짜 문자열 'YYYY-MM-DD', 데이터프레임)
        데이터를 찾지 못하면 (None, None) 반환
    """
    
    # 오늘 날짜부터 시작
    current_date = datetime.now()
    
    print(f"\n🔎 [TEST UTILS] 최근 {max_days}일 간 데이터 탐색 시작... (대상: {fetch_method.__name__})")
    
    for i in range(max_days):
        target_date_str = current_date.strftime('%Y-%m-%d')
        
        try:
            df = fetch_method(
                start_date=target_date_str, 
                end_date=target_date_str, 
                age=age, 
                **kwargs
            )
            
            if df is not None and not df.empty:
                print(f"✅ [TEST UTILS] 데이터 발견! 날짜: {target_date_str}, 건수: {len(df)}")
                return target_date_str, df
                
        except Exception as e:
            pass
        
        # 하루 전으로 이동
        current_date -= timedelta(days=1)
        
    print(f"❌ [TEST UTILS] 최근 {max_days}일 동안 데이터를 찾지 못했습니다.")
    return None, None
