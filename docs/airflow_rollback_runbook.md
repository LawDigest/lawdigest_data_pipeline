# Airflow 복귀 운영 Runbook

## 목적
- n8n 병행/대체 운영을 종료하고 Airflow를 단일 오케스트레이터로 복귀한다.
- 중복 적재를 방지하고 운영 경로를 단순화한다.

## 적용 기준일
- 2026-03-08

## 1) 사전 점검
- Airflow DAG 파일 존재 확인:
```bash
ls -1 airflow/dags
```
- 주요 DAG 식별:
  - `lawdigest_hourly_update_dag`
  - `lawdigest_daily_db_backup_dag`
  - `manual_collect_bills`

## 2) n8n 스케줄 중지
- n8n UI에서 활성(Active) 워크플로우를 모두 비활성화한다.
- Airflow와 n8n을 동시에 스케줄링하지 않는다.
- 레거시 n8n 문서는 조회용으로만 유지한다:
  - `docs/n8n_pipeline_migration.md`
  - `docs/n8n_import_guide.md`

## 3) Airflow 기동/활성화
```bash
./scripts/airflow_control.sh up
./scripts/airflow_control.sh status
./scripts/airflow_control.sh list-dags
./scripts/airflow_control.sh unpause-main
```

## 4) 수동 스모크 실행
- 시간별 DAG를 제한 기간으로 1회 수동 실행:
```bash
./scripts/airflow_control.sh trigger-hourly 2026-03-07 2026-03-08 22
```
- Airflow UI 또는 로그에서 태스크 성공 여부 확인:
  - `update_lawmakers`
  - `update_bills`
  - `update_timeline`
  - `update_results`
  - `update_votes`

## 5) 운영 체크리스트
- 스케줄 충돌 없음 (n8n 비활성 + Airflow 활성)
- 시간별 DAG가 정시에 실행됨
- 백업 DAG가 일일 1회 실행됨
- 누락/중복 적재 모니터링 지표 정상

## 6) 장애 대응
- 긴급 중지:
```bash
./scripts/airflow_control.sh pause-main
```
- Airflow 스택 상태 점검:
```bash
./scripts/airflow_control.sh status
```
- 필요 시 수동 재실행:
```bash
./scripts/airflow_control.sh trigger-hourly <start_date> <end_date> <age>
```
