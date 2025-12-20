# -*- coding: utf-8 -*-
import argparse
import sys
import os
import traceback

# 프로젝트 루트 경로를 sys.path에 추가
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from src.lawdigest_data_pipeline.WorkFlowManager import WorkFlowManager
from src.lawdigest_data_pipeline.Notifier import Notifier

def main(start_date: str, end_date: str, age: str):
    """
    지정된 기간과 국회 대수에 해당하는 법안 표결 정보를 수집합니다.
    """
    notifier = Notifier()
    job_name = "법안 표결 정보 수집"
    args_str = f"**기간**: {start_date} ~ {end_date}, **대수**: {age}"
    start_message = f"🚀 **[{job_name}]** 작업을 시작합니다.\n- {args_str}"
    print(start_message)
    notifier.send_discord_message(start_message)

    try:
        wfm = WorkFlowManager(mode='remote')
        
        df_vote, df_vote_party = wfm.update_bills_vote(start_date=start_date, end_date=end_date, age=age)
        
        vote_count = len(df_vote) if df_vote is not None else 0
        party_vote_count = len(df_vote_party) if df_vote_party is not None else 0
        
        success_message = (
            f"✅ **[{job_name}]** 작업이 성공적으로 완료되었습니다.\n"
            f"- {args_str}\n"
            f"- **처리된 데이터**: \n"
            f"  - 표결 정보: {vote_count}건\n"
            f"  - 정당별 표결 정보: {party_vote_count}건"
        )
        print(success_message)
        notifier.send_discord_message(success_message)

    except Exception as e:
        error_message = f"🚨 **[{job_name}]** 작업 중 오류 발생!\n- {args_str}\n\n- **오류 내용**: `{type(e).__name__}: {str(e)}`\n- **Traceback**:\n```\n{traceback.format_exc()}\n```"
        print(error_message)
        notifier.send_discord_message(error_message)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="특정 기간의 법안 표결 정보를 수집하는 스크립트")
    parser.add_argument("--start-date", required=True, help="시작 날짜 (YYYY-MM-DD)")
    parser.add_argument("--end-date", required=True, help="종료 날짜 (YYYY-MM-DD)")
    parser.add_argument("--age", required=True, help="국회 대수 (예: 21)")
    
    args = parser.parse_args()
    
    main(args.start_date, args.end_date, args.age)
