# n8n 전환 실행 가이드

이 프로젝트는 `WorkFlowManager`의 `mode='db'` 경로를 이용해 API 서버를 거치지 않고 MySQL에 직접 적재할 수 있습니다.  
`n8n`에서는 아래 엔트리포인트를 실행하면 Airflow DAG를 대체할 수 있습니다.

## 실행 엔트리포인트
- `scripts/run_n8n_db_pipeline.py`

- `--step all`: 의원/법안/타임라인/처리결과/표결/통계를 순차 실행
- `--step lawmakers`: 의원 수집만 실행
- `--step bills`: 법안 수집만 실행
- `--step timeline`: 법안 처리 단계 수집만 실행
- `--step result`: 처리 결과 수집만 실행
- `--step vote`: 본회의/정당별 표결 수집만 실행
- `--step stats`: 통계만 재계산

## n8n 추천 스케줄
- 트리거: 1시간 단위 크론 (`everyHour`)
- 공통 기간 파라미터:
  - `start_date`: `{{$moment().subtract(1, 'day').format('YYYY-MM-DD')}}`
  - `end_date`: `{{$moment().format('YYYY-MM-DD')}}`
  - `age`: 운영 환경 값(예: `"22"`)
- 각 단계는 `n8n-nodes-base.executeCommand`에서 `scripts/run_n8n_db_pipeline.py`를 호출.

## 템플릿 워크플로우
- `n8n/lawdigest_db_pipeline_hourly.json`  
  - 의원 → 법안 → 타임라인 → 결과 → 표결 → 통계 순으로 실행
  - 프로젝트 경로는 `/home/ubuntu/project/lawdigest` 기준으로 작성됨

## 운영 시 주의
- Airflow DAG(`airflow/dags/lawdigest_hourly_update_dag.py`)와 병행 실행하면 중복 적재 위험이 있습니다.
- DB 적재 단계(`db` 모드)는 기존 API 호출(`remote`)보다 빠르지만, 동일한 기간이 겹치지 않도록 스케줄 충돌 방지를 권장합니다.
- `--skip-stats`는 `all` 모드에서 통계 단계를 생략할 때만 사용합니다.
