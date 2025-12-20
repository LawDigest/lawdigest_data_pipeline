# -*- coding: utf-8 -*-
import argparse
import sys
import os
import traceback

# 프로젝트 루트 경로를 sys.path에 추가
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from src.lawdigest_data_pipeline.WorkFlowManager import WorkFlowManager
from src.lawdigest_data_pipeline.Notifier import Notifier

def main(start_ord: str, end_ord: str):
    """
    지정된 국회 대수 범위에 해당하는 대안-법안 관계 데이터를 수집합니다.
    """
    notifier = Notifier()
    job_name = "대안-법안 관계 데이터 수집"
    args_str = f"**범위**: {start_ord}대 ~ {end_ord}대"
    start_message = f"🚀 **[{job_name}]** 작업을 시작합니다.\n- {args_str}"
    print(start_message)
    notifier.send_discord_message(start_message)

    try:
        wfm = WorkFlowManager(mode='remote')
        
        result_df = wfm.update_bills_alternatives(start_ord=start_ord, end_ord=end_ord)
        
        data_count = len(result_df) if result_df is not None else 0
        
        success_message = f"✅ **[{job_name}]** 작업이 성공적으로 완료되었습니다.\n- {args_str}\n- **처리된 데이터**: {data_count}건"
        print(success_message)
        notifier.send_discord_message(success_message)

    except Exception as e:
        error_message = f"🚨 **[{job_name}]** 작업 중 오류 발생!\n- {args_str}\n\n- **오류 내용**: `{type(e).__name__}: {str(e)}`\n- **Traceback**:\n```\n{traceback.format_exc()}\n```"
        print(error_message)
        notifier.send_discord_message(error_message)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="특정 국회 대수 범위의 대안-법안 관계 데이터를 수집하는 스크립트")
    parser.add_argument("--start-ord", required=True, help="시작 국회 대수 (예: 21)")
    parser.add_argument("--end-ord", required=True, help="종료 국회 대수 (예: 21)")
    
    args = parser.parse_args()
    
    main(args.start_ord, args.end_ord)
