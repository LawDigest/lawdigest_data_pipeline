# 마이그레이션 전략 및 로드맵

## 1. 개요
본 문서는 `Lawbag` API 서버를 통한 간접 적재 방식에서 `lawdigest` 파이프라인의 직접 DB 적재 방식으로 이관하는 전체적인 전략과 로드맵을 정의합니다.

## 2. 마이그레이션 단계 (Phased Approach)

### Phase 1: 기반 구조 구축 (Foundation)
**목표**: 안전하고 효율적인 DB 작업을 위한 핵심 모듈 구현
- **트랜잭션 관리**: `autocommit=False` 기반의 명시적 트랜잭션(`commit`/`rollback`) 제어 구현
- **배치 처리**: `executemany`를 활용한 대량 데이터 일괄 삽입 최적화
- **공통 로직 포팅**: Java의 `BillStageType`, `ProposerKindType` 등 핵심 Enum 및 유틸리티 로직의 Python 포팅
- **테스트 환경**: 마이그레이션 된 로직을 검증할 단위 테스트 및 통합 테스트 환경 구성

### Phase 2: 핵심 데이터 적재 로직 이관 (Core Logic Migration)
**목표**: 가장 빈번하고 중요한 데이터 적재 로직의 이관
- **법안 정보 (`insertBillInfoDf`)**: `Bill` 테이블 적재 및 `BillProposer` 관계 설정
- **외래 키 검증**: DB 레벨의 제약조건 오류 방지를 위한 사전 검증 로직 구현
- **Dual Write 검증**: 기존 API 방식과 신규 직접 적재 방식을 병행하여 데이터 정합성 검증

### Phase 3: 고급 로직 및 통계 이관 (Expansion)
**목표**: 복잡한 비즈니스 로직 및 부가 기능의 완전한 이관
- **법안 단계 (`updateBillStageDf`)**: 단계 변경 순서 검증 및 `BillTimeline` 관리 로직 구현
- **의원 동기화 (`updateLawmakerDf`)**: 국회 API 기반 의원 정보 3-way 동기화(Insert/Update/Inactive) 구현
- **통계 업데이트**: 각종 카운트 집계 로직 이관

## 3. 리스크 매니지먼트 전략
| 리스크 | 대응 방안 |
|:---:|:---|
| **데이터 정합성 불일치** | Phase 2 기간 동안 Dual Write 및 데이터 전수 비교 모니터링 수행 |
| **트랜잭션 오류** | 철저한 예외 처리 및 `Context Manager` 패턴을 통한 자동 롤백 보장 |
| **운영 이슈** | 단계별 배포 및 문제 발생 시 즉시 API 방식으로 롤백 가능한 Feature Flag 도입 |

## 4. 성공 지표 (KPI)
- **안정성**: 파이프라인 에러율 < 0.1%
- **성능**: 데이터 적재 속도 30% 이상 향상
- **정합성**: 기존 시스템 데이터와 100% 일치
