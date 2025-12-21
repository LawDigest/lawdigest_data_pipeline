# test: 대안 데이터 수집 테스트 코드 작성

## 목적
`DataFetcher` 클래스의 `fetch_bills_alternatives` 메서드가 실제 API 호출을 통해 대안(Alternative) 법안 데이터를 올바르게 수집하는지 검증하는 통합 테스트 코드를 작성합니다. 현재 해당 로직이 메인 파이프라인에서는 비활성화되어 있으나, 기능 자체의 정상 동작 여부를 주기적으로 확인하기 위함입니다.

## 세부 작업 계획
1. **테스트 파일 작성/수정**:
   - `tests/test_data_fetcher_integration.py` 파일에 테스트 함수 추가.
   - 함수명: `test_fetch_bills_alternatives_integration` (가칭)

2. **테스트 시나리오 구성**:
   - **Step 1**: `DataFetcher` 인스턴스를 초기화합니다.
   - **Step 2**: 대안이 존재한다고 알려진 특정 법안의 ID를 포함하는 Mock `df_bills` 데이터프레임을 생성합니다.
     - 실제 데이터 예시를 찾아 활용 (예: 21대 국회 가결/대안반영폐기 법안 등).
   - **Step 3**: `fetch_bills_alternatives` 메서드를 호출합니다.
   - **Step 4**: 반환된 결과가 기대하는 형식(DataFrame)이고, 데이터가 비어있지 않은지 검증합니다.
     - 필수 컬럼 존재 여부 확인: `billId` (원안), `altBillId` (대안) 등.

3. **검증 및 실행**:
   - `pytest`를 사용하여 해당 테스트 케이스를 실행하고 통과 여부를 확인합니다.

## 완료 내역 (2025-12-21)
1. **테스트 함수 구현**: `tests/test_data_fetcher_integration.py` 내 `test_fetch_bills_alternatives_auto` 추가.
2. **동적 탐색 연동**: `test_utils.find_valid_date_and_data`를 사용하여 실제 대안 발의가 있는 날짜를 자동 탐색.
3. **안정성 강화**:
   - API 타임아웃 30초 상향.
   - 세션(`session.get`) 기반 요청 및 재시도 로직 적용.
4. **결과 검증**: `tests/result/fetch_bills_alternatives.md` 파일을 통해 실제 관계 데이터 수집 확인.

## 완료 조건 충족 여부
- [x] 테스트 함수 구현 완료
- [x] `pytest` 오류 없이 통과 (PASSED)
- [x] 올바른 관계 데이터(`altBillId`, `billId`) 포함 확인
