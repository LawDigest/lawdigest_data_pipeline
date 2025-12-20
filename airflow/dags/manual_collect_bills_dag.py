# -*- coding: utf-8 -*-
from __future__ import annotations

import pendulum

from airflow.models.dag import DAG
from airflow.operators.python import PythonOperator
from airflow.models.param import Param

# Airflow 환경에서 DAG 파일이 있는 디렉토리의 상위 디렉토리를
# 파이썬 경로에 추가하여 'tools' 모듈을 찾을 수 있도록 합니다.
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from project.tools.collect_bills import main as collect_bills_main

# --- Task Function ---
# Airflow의 context에서 파라미터를 받아 원래의 main 함수를 호출하는 래퍼 함수입니다.
def collect_bills_task(**context):
    """
    Airflow UI에서 전달된 파라미터를 사용하여 법안 데이터 수집 스크립트를 실행합니다.
    """
    start_date = context["params"]["start_date"]
    end_date = context["params"]["end_date"]
    age = context["params"]["age"]
    
    print(f"Airflow-triggered execution with params: start_date={start_date}, end_date={end_date}, age={age}")
    
    collect_bills_main(start_date=start_date, end_date=end_date, age=age)

# --- DAG Definition ---
with DAG(
    dag_id="manual_collect_bills",
    schedule=None,  # 수동 실행 전용
    start_date=pendulum.datetime(2024, 1, 1, tz="Asia/Seoul"),
    catchup=False,
    tags=["lawdigest", "manual-run", "tools"],
    doc_md="""
    ### 수동 법안 데이터 수집
    
    Airflow UI에서 직접 파라미터를 입력하여 특정 기간과 대수의 법안 데이터를 수집하는 DAG입니다.
    - **start_date**: 수집 시작일 (YYYY-MM-DD)
    - **end_date**: 수집 종료일 (YYYY-MM-DD)
    - **age**: 국회 대수 (예: 21)
    """,
    # Airflow UI에 표시될 파라미터 정의
    params={
        "start_date": Param(
            type="string",
            title="시작 날짜",
            description="데이터 수집을 시작할 날짜 (YYYY-MM-DD)",
            default=(pendulum.now("Asia/Seoul").subtract(days=7)).to_date_string(),
        ),
        "end_date": Param(
            type="string",
            title="종료 날짜",
            description="데이터 수집을 종료할 날짜 (YYYY-MM-DD)",
            default=(pendulum.now("Asia/Seoul")).to_date_string(),
        ),
        "age": Param(
            type="string",
            title="국회 대수",
            description="수집할 국회 대수 (예: 22)",
            default="22",
        ),
    },
) as dag:
    manual_collect_task = PythonOperator(
        task_id="collect_bills_with_params",
        python_callable=collect_bills_task,
    )
