# Phase 4 완료 보고서: 통계 집계 로직 이관 (Statistics Aggregation Logic Migration)

## 개요
Phase 4 작업의 목표는 `DataService.java`에 존재하는 정당별 의원/법안 수 집계 및 의원별 최신 발의일 업데이트 로직을 Python `DatabaseManager`로 이관하는 것이었습니다. 이 과정에서 SQL `GROUP BY`와 배치 처리를 활용하여 성능과 유지보수성을 크게 향상시켰습니다.

## 구현 상세

### 1. 정당별 통계 집계 (`update_party_statistics`)
- **기존 방식 (Java)**:
    - 정당 목록을 순회하며 의원 수(지역구, 비례대표)와 법안 수(대표, 공동)를 각각 별도의 쿼리로 카운트.
    - Loop 내에서 `save()` 반복 호출로 인한 성능 저하.
- **개선 방식 (Python)**:
    - **쿼리 통합**: `GROUP BY party_id`를 사용하여 한 번의 쿼리로 모든 정당의 카운트를 집계.
    - **메모리 병합**: 4가지 통계(지역구 의원, 비례 의원, 대표 법안, 공동 법안)를 메모리(`Dictionary`)에서 병합.
    - **Batch Update**: `executemany`를 사용하여 모든 `Party` 테이블 레코드를 단 한 번의 네트워크 통신으로 일괄 업데이트.
    - **코드**:
        ```python
        def update_party_statistics(self) -> None:
            # ... (GROUP BY 쿼리로 각 카운트 집계) ...
            cursor.executemany(update_query, update_params)
        ```

### 2. 의원별 최신 발의일 업데이트 (`update_congressman_statistics`)
- **기존 방식 (Java)**:
    - 의원 목록을 순회하며 개별적으로 최신 발의 법안 조회 및 업데이트.
- **개선 방식 (Python)**:
    - **Join & Group By**: `RepresentativeProposer`와 `Bill`을 조인하여 의원별 `MAX(propose_date)`를 한 번에 조회.
    - **Batch Update**: 조회된 결과로 `Congressman` 테이블을 일괄 업데이트.

## 검증 (Verification)
- **단위 테스트 (`tests/test_database_manager_statistics.py`)**:
    - Mock 객체를 활용하여 집계 쿼리 실행 횟수 및 배치 업데이트 파라미터 검증 완료.
    - 정당별 4가지 카운트 항목이 정확히 매핑되는지 확인.
    - 의원별 최신 발의일이 올바르게 업데이트 쿼리로 변환되는지 확인.

## 성능 향상 분석 (Performance Analysis)

### 1. 정당 통계 집계 (`update_party_statistics`)
- **기존 (Java)**: Loop 방식 (정당 수 N개 × Query 5회)
    - 예상 비용: 20개 정당 기준 약 **100회** DB 호출
- **개선 (Python)**: Batch 방식 (전체 집계 3회 + Update 1회)
    - 예상 비용: 정당 수와 무관하게 **4회** DB 호출
    - **효과**: 약 **25배 이상** 속도 향상 예상

### 2. 의원 발의일 업데이트 (`update_congressman_statistics`)
- **기존 (Java)**: Loop 방식 (의원 수 N명 × Query 2회)
    - 예상 비용: 300명 의원 기준 약 **600회** DB 호출
- **개선 (Python)**: Batch 방식 (전체 집계 1회 + Update 1회)
    - 예상 비용: 의원 수와 무관하게 **2회** DB 호출
    - **효과**: 약 **300배 이상** 속도 향상 예상

## 결론 및 제안
- **성능**: N+1 문제가 발생하던 로직을 집합 처리(Set-based operation)로 변경하여 데이터량이 증가해도 안정적인 성능 보장.
- **안정성**: `Transaction` 내에서 읽기와 쓰기가 이루어지므로 데이터 일관성 유지.
- **향후 계획**: 다음 단계인 Airflow DAG 연동 시, 데이터 적재 작업이 끝난 후 이 통계 메소드들을 순차적으로 호출하도록 구성하면 됩니다.
