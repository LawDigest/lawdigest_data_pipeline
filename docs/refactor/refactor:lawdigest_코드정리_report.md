# lawdigest 코드 정리 보고서

## 작업 계획
- 대상 파일: `src/lawdigest_data_pipeline/DataProcessor.py`, `src/lawdigest_data_pipeline/WorkFlowManager.py`
- 목표: 가독성 개선 및 반복 패턴 정리(청크 처리, 로컬 URL 치환, 모드 분기 조건)
- 범위 제한: 기능 동작 변경 없이 리팩터링 수준 정리만 수행

## 수정 내용
- `DataProcessor.py`
  - 상단 상수 패턴(`proposer` 추출 정규표현식)을 클래스 상수로 정리
  - `proposer` 이름 추출 로직을 전용 헬퍼 메서드로 분리
  - 문자열 처리 및 컬럼 삭제 로직의 스타일 정리(일관된 따옴표/조건식)
  - `proposerKind` 누락/빈 데이터 케이스에 대한 가드(방어적 처리) 추가

- `WorkFlowManager.py`
  - 공통 상수 `CHUNK_SIZE` 추가
  - `_to_local_url`, `_chunk_dataframe` 헬퍼 메서드 추가
  - 중복된 URL 로컬 치환 로직 통일
  - `1000` 단위 청크 반복 구간 일부를 공통 헬퍼 기반으로 정리
  - `fetch`/`ai_test` 모드 조건식을 간결화

## 진행 결과
- 위 변경은 동작 자체를 바꾸지 않고 가독성과 유지보수성을 높이는 방향으로 진행됨
- 기능 동작에 직접 관여하는 핵심 처리 로직은 유지
