# -*- coding: utf-8 -*-
from __future__ import annotations

import pendulum
import os
import sys

from airflow.models.dag import DAG
from airflow.operators.python import PythonOperator

# 프로젝트 루트 경로를 sys.path에 추가하여 src 모듈을 찾을 수 있도록 합니다.
sys.path.append('/opt/airflow/project')

from src.lawdigest_data_pipeline.WorkFlowManager import WorkFlowManager

def run_workflow_step(method_name, **kwargs):
    """WorkFlowManager의 특정 메서드를 실행하는 데코레이터 함수"""
    print(f"Starting {method_name}...")
    wfm = WorkFlowManager(mode='remote')
    method = getattr(wfm, method_name)
    method(**kwargs)
    print(f"Finished {method_name}.")

with DAG(
    dag_id="lawdigest_hourly_update_dag",
    schedule="0 * * * *",  # 매 정시 실행
    start_date=pendulum.datetime(2024, 1, 1, tz="Asia/Seoul"),
    catchup=False,
    tags=["lawdigest", "hourly", "update"],
    doc_md="""
    ### 법안 및 의원 데이터 시간별 업데이트
    
    매 정시에 실행되어 다음 순서로 데이터를 업데이트합니다:
    1. 의원 정보 (lawmakers)
    2. 법안 정보 (bills)
    3. 타임라인(timeline), 처리 결과(results), 표결 정보(votes) - 동시 실행
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
