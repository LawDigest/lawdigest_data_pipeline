# -*- coding: utf-8 -*-
from prefect import flow, task
import sys
import os
import traceback
from datetime import datetime

# 프로젝트 루트 경로를 sys.path에 추가
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from src.lawdigest_data_pipeline.WorkFlowManager import WorkFlowManager
from src.lawdigest_data_pipeline.Notifier import Notifier

@task(name="알림 전송 (시작)")
def notify_start(job_name: str, args_str: str):
    notifier = Notifier()
    start_message = f"🚀 **[{job_name} (Prefect)]** 작업을 시작합니다.\n- {args_str}"
    print(start_message)
    notifier.send_discord_message(start_message)
    return start_message

@task(name="법안 데이터 업데이트", retries=2, retry_delay_seconds=60)
def update_bills_data(mode: str, start_date: str, end_date: str, age: str):
    wfm = WorkFlowManager(mode=mode)
    result_df = wfm.update_bills_data(start_date=start_date, end_date=end_date, age=age)
    return len(result_df) if result_df is not None else 0

@task(name="알림 전송 (성공)")
def notify_success(job_name: str, args_str: str, data_count: int):
    notifier = Notifier()
    success_message = f"✅ **[{job_name} (Prefect)]** 작업이 성공적으로 완료되었습니다.\n- {args_str}\n- **처리된 데이터**: {data_count}건"
    print(success_message)
    notifier.send_discord_message(success_message)
    return success_message

@task(name="알림 전송 (실패)")
def notify_failure(job_name: str, args_str: str, error_msg: str, tb: str):
    notifier = Notifier()
    error_message = f"🚨 **[{job_name} (Prefect)]** 작업 중 오류 발생!\n- {args_str}\n\n- **오류 내용**: `{error_msg}`\n- **Traceback**:\n```\n{tb}\n```"
    print(error_message)
    notifier.send_discord_message(error_message)
    return error_message

@flow(name="국회 법안 데이터 수집 Flow")
def collect_bills_flow(start_date: str, end_date: str, age: str, mode: str = "remote"):
    job_name = "법안 데이터 수집"
    args_str = f"**기간**: {start_date} ~ {end_date}, **대수**: {age}, **모드**: {mode}"
    
    # 1. 시작 알림
    notify_start(job_name, args_str)
    
    try:
        # 2. 데이터 업데이트 실행
        data_count = update_bills_data(mode, start_date, end_date, age)
        
        # 3. 성공 알림
        notify_success(job_name, args_str, data_count)
        
    except Exception as e:
        # 4. 실패 알림
        error_msg = f"{type(e).__name__}: {str(e)}"
        tb = traceback.format_exc()
        notify_failure(job_name, args_str, error_msg, tb)
        raise e

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Prefect를 이용한 법안 데이터 수집 Flow")
    parser.add_argument("--start-date", help="시작 날짜 (YYYY-MM-DD)")
    parser.add_argument("--end-date", help="종료 날짜 (YYYY-MM-DD)")
    parser.add_argument("--age", help="국회 대수 (예: 21)")
    parser.add_argument("--mode", default="remote", help="실행 모드 (remote|local|db|test)")
    
    args = parser.parse_args()
    
    # 날짜 기본값 설정 (오늘 기준)
    today = datetime.now().strftime('%Y-%m-%d')
    start = args.start_date if args.start_date else today
    end = args.end_date if args.end_date else today
    age = args.age if args.age else os.getenv("AGE", "22")
    
    collect_bills_flow(start_date=start, end_date=end, age=age, mode=args.mode)
