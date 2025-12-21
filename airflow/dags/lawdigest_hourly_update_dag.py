# -*- coding: utf-8 -*-
from __future__ import annotations

import pendulum
import os
import sys

from airflow.models.dag import DAG
from airflow.operators.python import PythonOperator
from airflow.models.param import Param

# 프로젝트 루트 경로를 sys.path에 추가하여 src 모듈을 찾을 수 있도록 합니다.
sys.path.append('/opt/airflow/project')

from src.lawdigest_data_pipeline.WorkFlowManager import WorkFlowManager

def run_workflow_step(method_name, **context):
    """
    WorkFlowManager의 특정 메서드를 실행하는 함수.
    수동 실행 시 입력받은 params가 있으면 이를 우선적으로 사용합니다.
    """
    # UI에서 입력받은 params 가져오기
    params = context.get("params", {})
    start_date = params.get("start_date")
    end_date = params.get("end_date")
    age = params.get("age")

    print(f"--- Calling {method_name} ---")
    if start_date or end_date:
        print(f"Custom range detected: {start_date} ~ {end_date} (Age: {age})")
    else:
        print("No custom range detected. Using default scheduling/latest data logic.")

    wfm = WorkFlowManager(mode='remote')
    method = getattr(wfm, method_name)
    
    # 메서드별 인자 처리
    if method_name == "update_lawmakers_data":
        # 의원 정보는 보통 기간 필터 없이 전체 또는 변경분 수집
        method()
    else:
        # 법안, 타임라인, 결과, 표결 정보는 입력받은 날짜 정보를 전달
        # (날짜가 None이면 WorkFlowManager 내부에서 최신 날짜를 자동으로 계산함)
        method(start_date=start_date, end_date=end_date, age=age)
        
    print(f"--- Finished {method_name} ---")

with DAG(
    dag_id="lawdigest_hourly_update_dag",
    schedule="0 * * * *",  # 매 정시 실행
    start_date=pendulum.datetime(2024, 1, 1, tz="Asia/Seoul"),
    catchup=False,
    tags=["lawdigest", "hourly", "update"],
    # UI에서 입력받을 수 있는 파라미터 정의
    params={
        "start_date": Param(
            None, 
            type=["null", "string"], 
            title="시작 날짜", 
            description="데이터를 수집할 시작 날짜 (YYYY-MM-DD). 비워두면 최신 데이터부터 가져옵니다."
        ),
        "end_date": Param(
            None, 
            type=["null", "string"], 
            title="종료 날짜", 
            description="데이터를 수집할 종료 날짜 (YYYY-MM-DD). 비워두면 오늘 날짜까지 가져옵니다."
        ),
        "age": Param(
            "22", 
            type="string", 
            title="국회 대수", 
            description="수집할 국회 대수 (기본값: 22)"
        ),
    },
    doc_md="""
    ### 법안 및 의원 데이터 시간별 업데이트
    
    매 정시에 실행되어 실시간으로 의원 정보, 법안 정보, 타임라인, 결과 및 표결 데이터를 업데이트합니다.
    
    **💡 실행 가이드:**
    1. **자동 스케줄**: 매 시 정각에 자동으로 실행됩니다.
    2. **수동 실행 (짧은 기간)**: 
       - 최근 며칠간의 데이터가 누락되었거나 즉시 동기화가 필요할 때 사용합니다.
       - `Trigger DAG w/ Config`를 통해 `start_date`와 `end_date`를 입력하여 실행하세요.
       - 입력한 기간의 데이터를 **한 번의 Task**로 일괄 처리합니다.
    3. **과거 데이터 소급 (긴 기간)**:
       - 일주일 이상의 대량 데이터를 처리할 때는 **API 부하 분산**을 위해 `lawdigest_historical_update_dag` (Backfill용) 사용을 권장합니다.
    
    **입력 파라미터:**
    - `start_date`: 시작 날짜 (YYYY-MM-DD)
    - `end_date`: 종료 날짜 (YYYY-MM-DD)
    - `age`: 국회 대수 (기본값: 22)
    """,
) as dag:

    update_lawmakers = PythonOperator(
        task_id="update_lawmakers",
        python_callable=run_workflow_step,
        op_kwargs={"method_name": "update_lawmakers_data"},
    )

    update_bills = PythonOperator(
        task_id="update_bills",
        python_callable=run_workflow_step,
        op_kwargs={"method_name": "update_bills_data"},
    )

    update_timeline = PythonOperator(
        task_id="update_timeline",
        python_callable=run_workflow_step,
        op_kwargs={"method_name": "update_bills_timeline"},
    )

    update_results = PythonOperator(
        task_id="update_results",
        python_callable=run_workflow_step,
        op_kwargs={"method_name": "update_bills_result"},
    )

    update_votes = PythonOperator(
        task_id="update_votes",
        python_callable=run_workflow_step,
        op_kwargs={"method_name": "update_bills_vote"},
    )

    # 실행 순서 정의: 의원 -> 법안 -> [타임라인, 처리결과, 표결정보]
    update_lawmakers >> update_bills >> [update_timeline, update_results, update_votes]
