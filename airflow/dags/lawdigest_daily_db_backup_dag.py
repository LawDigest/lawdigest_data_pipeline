# -*- coding: utf-8 -*-
from __future__ import annotations

import pendulum
import os
import sys

from airflow.models.dag import DAG
from airflow.operators.python import PythonOperator

# 프로젝트 루트 경로를 sys.path에 추가하여 module을 찾을 수 있도록 합니다.
sys.path.append('/opt/airflow/project')

# database_backup.py의 main 함수를 import
# airflow/dags 폴더 입장에서 상위 폴더인 project 루트를 기준으로 import
from jobs.database_backup import main as db_backup_main

with DAG(
    dag_id="lawdigest_daily_db_backup_dag",
    schedule="0 0 * * *",  # 매일 자정 실행
    start_date=pendulum.datetime(2024, 1, 1, tz="Asia/Seoul"),
    catchup=False,
    tags=["lawdigest", "daily", "backup"],
    doc_md="""
    ### 데이터베이스 일간 백업
    
    매일 자정에 실행되어 데이터베이스를 백업합니다.
    """,
) as dag:

    db_backup = PythonOperator(
        task_id="database_backup",
        python_callable=db_backup_main,
    )
