# Tools 디렉토리 스크립트 사용법

이 문서에는 `tools` 디렉토리에 포함된 각 Python 스크립트의 사용법이 정리되어 있습니다.

## 목차
1.  [`collect_alternatives.py`](#collect_alternativespy)
2.  [`collect_bills.py`](#collect_billspy)
3.  [`collect_lawmakers.py`](#collect_lawmakerspy)
4.  [`collect_results.py`](#collect_resultspy)
5.  [`collect_timeline.py`](#collect_timelinepy)
6.  [`collect_votes.py`](#collect_votespy)
7.  [`run_n8n_db_pipeline.py` (레거시)](#run_n8n_db_pipelinepy-레거시)
8.  [Airflow 운영 명령(권장)](#airflow-운영-명령권장)

---

### `collect_alternatives.py`

특정 국회 대수 범위의 대안-법안 관계 데이터를 수집합니다.

**사용법:**
```bash
python tools/collect_alternatives.py --start-ord <시작_국회_대수> --end-ord <종료_국회_대수>
```

**인자:**
-   `--start-ord`: 데이터 수집을 시작할 국회 대수 (예: `21`)
-   `--end-ord`: 데이터 수집을 종료할 국회 대수 (예: `21`)

**예시:**
```bash
python tools/collect_alternatives.py --start-ord 21 --end-ord 21
```

---

### `collect_bills.py`

지정된 기간과 국회 대수에 해당하는 법안 데이터를 수집합니다.

**사용법:**
```bash
python tools/collect_bills.py --start-date <시작_날짜> --end-date <종료_날짜> --age <국회_대수>
```

**인자:**
-   `--start-date`: 데이터 수집 시작 날짜 (형식: `YYYY-MM-DD`)
-   `--end-date`: 데이터 수집 종료 날짜 (형식: `YYYY-MM-DD`)
-   `--age`: 국회 대수 (예: `21`)

**예시:**
```bash
python tools/collect_bills.py --start-date 2024-01-01 --end-date 2024-01-31 --age 21
```

---

### `collect_lawmakers.py`

전체 국회의원 데이터를 수집합니다. 이 스크립트는 별도의 인자를 받지 않습니다.

**사용법:**
```bash
python tools/collect_lawmakers.py
```

---

### `collect_results.py`

지정된 기간과 국회 대수에 해당하는 법안 처리 결과 데이터를 수집합니다.

**사용법:**
```bash
python tools/collect_results.py --start-date <시작_날짜> --end-date <종료_날짜> --age <국회_대수>
```

**인자:**
-   `--start-date`: 데이터 수집 시작 날짜 (형식: `YYYY-MM-DD`)
-   `--end-date`: 데이터 수집 종료 날짜 (형식: `YYYY-MM-DD`)
-   `--age`: 국회 대수 (예: `21`)

**예시:**
```bash
python tools/collect_results.py --start-date 2024-01-01 --end-date 2024-01-31 --age 21
```

---

### `collect_timeline.py`

지정된 기간과 국회 대수에 해당하는 법안 타임라인 데이터를 수집합니다.

**사용법:**
```bash
python tools/collect_timeline.py --start-date <시작_날짜> --end-date <종료_날짜> --age <국회_대수>
```

**인자:**
-   `--start-date`: 데이터 수집 시작 날짜 (형식: `YYYY-MM-DD`)
-   `--end-date`: 데이터 수집 종료 날짜 (형식: `YYYY-MM-DD`)
-   `--age`: 국회 대수 (예: `21`)

**예시:**
```bash
python tools/collect_timeline.py --start-date 2024-01-01 --end-date 2024-01-31 --age 21
```

---

### `collect_votes.py`

지정된 기간과 국회 대수에 해당하는 법안 표결 정보를 수집합니다.

**사용법:**
```bash
python tools/collect_votes.py --start-date <시작_날짜> --end-date <종료_날짜> --age <국회_대수>
```

**인자:**
-   `--start-date`: 데이터 수집 시작 날짜 (형식: `YYYY-MM-DD`)
-   `--end-date`: 데이터 수집 종료 날짜 (형식: `YYYY-MM-DD`)
-   `--age`: 국회 대수 (예: `21`)

**예시:**
```bash
python tools/collect_votes.py --start-date 2024-01-01 --end-date 2024-01-31 --age 21
```

---

### `run_n8n_db_pipeline.py` (레거시)

과거 n8n 연동용 DB 직접 적재 실행 스크립트입니다. API 호출 없이 `mode='db'`로 동작합니다.  
현재 운영 기준은 Airflow이며, 본 스크립트는 디버깅/실험 목적에서만 사용하세요.

**사용법:**
```bash
python scripts/run_n8n_db_pipeline.py --step all --start-date <시작_날짜> --end-date <종료_날짜> --age <국회_대수>
python scripts/run_n8n_db_pipeline.py --step lawmakers
python scripts/run_n8n_db_pipeline.py --step bills --start-date <시작_날짜> --end-date <종료_날짜> --age <국회_대수>
python scripts/run_n8n_db_pipeline.py --step stats
```

**인자:**
-   `--step`: 실행 단계 (`all|lawmakers|bills|timeline|result|vote|stats`, 기본 `all`)
-   `--start-date`: `bills/timeline/result/vote`에 사용할 시작 날짜
-   `--end-date`: `bills/timeline/result/vote`에 사용할 종료 날짜
-   `--age`: 국회 대수
-   `--skip-stats`: `all` 실행 시 통계 업데이트 건너뜀

**예시:**
```bash
python scripts/run_n8n_db_pipeline.py --step all --start-date 2024-01-01 --end-date 2024-01-31 --age 22
```

---

### Airflow 운영 명령(권장)

운영/정기 실행은 Airflow DAG를 기준으로 수행합니다.

**사용법:**
```bash
./scripts/airflow_control.sh up
./scripts/airflow_control.sh list-dags
./scripts/airflow_control.sh unpause-main
./scripts/airflow_control.sh trigger-hourly 2026-03-01 2026-03-08 22
```

**세부 명령:**
- `up`: Airflow 스택 시작(init 포함)
- `status`: 컨테이너 상태 확인
- `list-dags`: 등록 DAG 목록 조회
- `unpause-main`: 주요 DAG(`lawdigest_hourly_update_dag`, `lawdigest_daily_db_backup_dag`) 활성화
- `pause-main`: 주요 DAG 일시중지
- `trigger-hourly [start_date] [end_date] [age]`: 시간별 DAG 수동 실행
