# 2025-12-21 Daily Development Report

## 1. 📅 개요

| 항목 | 내용 |
| :--- | :--- |
| **날짜** | 2025년 12월 21일 |
| **작업자** | Antigravity |
| **주요 작업** | Airflow 파이프라인 에러 수정, DAG 구조 최적화 및 보안 강화, 레거시 코드 정리 |

**📝 요약**:  
Airflow 도입 과정에서 발생한 `DataFetcher` 관련 에러와 패키지 Import 경로 문제를 해결하여 파이프라인 안정성을 확보했습니다.  
운영 효율성을 위해 **실시간(Hourly) 업데이트**와 **DB 백업(Daily)**으로 DAG 역할을 명확히 분리하고, 보안 설정을 강화했습니다.  
또한, 향후 확장성을 위해 Monolithic한 `WorkFlowManager` 구조를 개선하기 위한 리팩토링 계획을 수립했습니다.

---

## 2. 🚀 진행 작업 상세

### 2.1. DataFetcher & WorkFlowManager 리팩토링 (Bug Fix)
- **목적**: `manual_collect_bills` DAG 실행 시 발생하던 `AttributeError: 'DataFetcher' object has no attribute 'fetch_data'` 해결
- **변경 사항**:
    - `DataFetcher.py`: 불필요한 `fetch_data` 래퍼 메서드 및 `__init__`의 `params` 인자 제거 (본래 설계 원복).
    - `WorkFlowManager.py`: 범용 `fetch_data()` 호출을 구체적인 메서드(`fetch_bills_data()`, `fetch_lawmakers_data()` 등) 호출로 변경.
- **이유**: `fetch_data`와 같은 모호한 Dispatcher 방식보다 명시적인 메서드 호출이 디버깅과 유지보수에 유리함.

### 2.2. 패키지 Import 경로 호환성 수정
- **목적**: Airflow 환경에서 커스텀 모듈 로드 실패(`ModuleNotFoundError`) 해결
- **변경 사항**:
    - `src/__init__.py`: 레거시 패키지명 `data_operations`를 현재 사용 중인 `lawdigest_data_pipeline`으로 수정.
    - `tools/*.py`: 모든 도구 스크립트(`collect_bills.py` 등)의 Import 구문을 최신 패키지명으로 일괄 수정.
- **이유**: 프로젝트 구조 변경 사항이 일부 파일에 반영되지 않아 DAG 파싱 에러가 발생하고 있었음.

### 2.3. Airflow DAG 구조 재설계 및 최적화
- **목적**: 데이터 수집 주기와 목적에 맞는 효율적인 파이프라인 구축
- **변경 사항**:
    - `lawdigest_hourly_update_dag.py`: 
        - 실행 순서 정의 (의원 → 법안 → [타임라인/결과/표결 병렬]).
        - **수동 실행 기능(Strategy A)** 추가: UI에서 기간(`start_date`, `end_date`) 입력 시 해당 기간 데이터를 일괄 처리하도록 로직 개선.
    - `lawdigest_daily_db_backup_dag.py`: 기존 Daily DAG에서 수집 로직 제거하고 DB 백업 전용으로 전환.
    - `lawdigest_historical_update_dag.py`: Hourly DAG의 수동 기능으로 통합하여 관리 포인트 절감을 위해 삭제.
- **이유**: 실시간성 데이터와 관리성 작업(백업)을 분리하고, 수동 소급 수집 편의성을 높임.

### 2.4. Airflow 환경 설정 및 보안 강화
- **목적**: 운영 환경의 보안성 확보 및 라이브러리 의존성 해결
- **변경 사항**:
    - `requirements.txt`: Gemini 연동을 위한 `langchain-google-genai` 라이브러리 추가.
    - `docker-compose.yaml`: Airflow 예제 DAG 로드 비활성화, 웹 서버 노출 경고(`WARN_DEPLOYMENT_EXPOSURE`) 비활성화.
    - **보안 조치**: 관리자 계정(`lawdigest_airflow`) 생성 및 기본 계정 대체.
- **이유**: 외부 도메인 배포 환경에서의 보안 위협을 최소화하고, Gemini 기반 요약 기능이 정상 작동하도록 환경 구성.

---

## 3. 🔍 현재 상태 분석

### 3.1. 프로젝트 구조
현재 프로젝트는 Airflow로의 마이그레이션이 완료 단계에 접어들었으며, 폴더 구조는 다음과 같습니다.
- `airflow/dags`: 목적별로 명확히 분리된 3개의 운영 DAG 보유 (`hourly`, `daily_backup`, `manual_bills`).
- `src/lawdigest_data_pipeline`: 핵심 비즈니스 로직(`WorkFlowManager`, `DataFetcher` 등)이 위치함.
- `tools/`: CLI 기반 수동 실행 도구들이 최신 패키지 경로로 업데이트됨.

### 3.2. 향후 5대 과제
1. **WorkFlowManager 리팩토링 (Phase 1)**: 현재 Issue #21로 등록된 Task 단위 해체 작업 진행.
2. **전 구간 통합 테스트**: Hourly DAG를 실제 가동하여 데이터 수집부터 DB 적재까지의 정합성 검증.
3. **알림 시스템 고도화**: 성공/실패 메시지를 Discord 등으로 명확히 전송하는 `Notifier` 연동 확인.
4. **모니터링 대시보드 구성**: 수집된 데이터(오늘 처리 건수 등)를 시각화할 방안 검토.
5. **레거시 코드 청산**: `tests/legacy` 및 미사용 `jobs/` 스크립트 정리.

---

## 4. 💡 개선 제안 및 리팩토링

### 4.1. WorkFlowManager의 Task 분리 (Refactoring)
- **현황**: Airflow DAG가 `WorkFlowManager`의 메서드 하나를 통채로 호출하는 구조.
- **제안**: 수집(Fetch) -> 가공(Process) -> 요약(AI Summary) -> 적재(Load) 단계로 Task를 쪼개야 함.
- **기대 효과**:
    - 특정 단계(예: AI 요약) 실패 시 해당 부분만 재시도(Retry) 가능.
    - 각 단계별 소요 시간을 Airflow UI에서 직관적으로 파악 가능.
    - *오늘 GitHub Issue #21로 생성 완료.*

### 4.2. XCom 활용 및 데이터 흐름 가시화
- **현황**: 메모리 상에서 데이터프레임이 전달됨.
- **제안**: Task 분리 후 XCom을 통해 데이터를 저장/로드하거나, 대용량일 경우 S3/MinIO/Local File을 경유하는 Custom Backend 구성 고려.

---

## 5. 📝 최종 요약

| 구분 | 내용 |
| :--- | :--- |
| **버그 수정** | `DataFetcher` 속성 에러 및 `src` 패키지 경로 `ModuleNotFoundError` 전체 해결 |
| **기능 개선** | Gemini 라이브러리 추가, Airflow 보안 계정 설정, 불필요한 예제 DAG 제거 |
| **DAG 최적화** | Hourly/Daily 역할 분리, Hourly DAG에 기간 지정 수동 실행 기능(Params) 탑재 |
| **운영 준비** | `docker compose` 재기동을 통한 전체 설정 적용 완료, 정상 가동 상태 확인 |
| **Future** | `WorkFlowManager` 리팩토링을 통한 '진정한' Airflow 오케스트레이션 구현 예정 |

> **Note**: 내일(또는 다음 작업 시)은 Hourly DAG를 실제로 수동 트리거하여 데이터가 정상적으로 들어오는지 최종 확인하고, 리팩토링 작업을 시작하는 것을 권장합니다.
