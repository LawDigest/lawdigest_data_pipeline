# 데이터 파이프라인 로직 이관 현황 보고서

## 1. 이관 완료 (Completed)

다음 기능들은 Python `DatabaseManager` 및 `constants` 모듈로 이관이 완료되었으며, 단위 테스트 및 스키마 검증을 통과했습니다.

### 1.1 기반 구조 (Foundation)
- **`DatabaseManager` 리팩토링**:
    - Transaction Context Manager (`with transaction():`) 구현.
    - `autocommit=False` 기반의 안정적인 트랜잭션 처리.
    - `execute_batch` (Bulk Insert/Update) 구현.
- **상수/Enum 포팅**:
    - `BillStageType` (단계 정의 및 순서 검증 로직).
    - `ProposerKindType` (발의자 유형).

### 1.2 핵심 데이터 적재 (Core Logic)
- **법안 정보 적재 (`insert_bill_info`)**:
    - `insertBillInfoDf` (Java) 대응.
    - `Bill` 테이블 Upsert (`ON DUPLICATE KEY UPDATE`).
    - `BillProposer`, `RepresentativeProposer` 관계 테이블 자동 갱신.
- **법안 단계 업데이트 (`update_bill_stage`)**:
    - `updateBillStageDf` (Java) 대응.
    - `Bill` 테이블 Stage 갱신.
    - `BillTimeline` 이력 적재 (중복 타임라인 방지 로직 포함).

---

## 2. 남은 작업 (Remaining Tasks)

`DataService.java`에 존재하지만 아직 Python으로 이관되지 않은 로직들입니다. 추후 Phase 3 이후 진행이 필요합니다.

### 2.1 의원 정보 관리 (Lawmaker Management)
- **`updateLawmakerDf`**: 의원 정보 동기화 로직.
    - 신규 의원 추가 (API에만 존재).
    - 의원 정보 갱신 (API/DB 교집합).
    - 의원 상태 변경 (DB에만 존재 -> `state=False` 처리).

### 2.2 법안 결과 및 투표 (Bill Result & Votes)
- **`updateBillResultDf`**:
    - 법안 처리 결과(`bill_result`)를 `Bill` 및 `BillTimeline` ("본회의 심의" 단계)에 반영하는 로직.
- **`insertAssemblyVote`**:
    - 본회의 투표 결과(`VoteRecord`) 적재.
- **`insertVoteParty`**:
    - 정당별 투표 결과(`VoteParty`) 적재 및 갱신.

### 2.3 집계 및 통계 (Aggregation)
- **`updateCongressmanCountByParty`**: 정당별 의원 수 집계.
- **`updateBillCountByParty`**: 정당별 대표/공동 발의 법안 수 집계.
- **`updateProposeDateByCongressman`**: 의원별 마지막 발의일 갱신.

## 3. 향후 계획 (Next Steps)
1.  **Phase 3**: 의원 정보 동기화(`updateLawmakerDf`) 및 법안 결과 로직 이관.
2.  **Phase 4**: 투표 정보 및 통계 집계 로직 이관.
