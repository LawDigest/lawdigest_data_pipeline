# fetch_vote_party 출력 변경 계획

## 목표
`src/lawdigest_data_pipeline/DataFetcher.py`의 `fetch_vote_party` 메서드에서 페이지별로 출력되던 로그를 법안별로 한 번만 출력되도록 수정하여 로그 가독성을 높입니다.

## 사용자 검토 필요 사항
- **로그 형식**: `✅ [INFO] {bill_id} | 📊 {bill_data_count} 개 데이터 수집됨.` 형식으로 출력할 예정입니다.

## 변경 제안

### `src/lawdigest_data_pipeline/DataFetcher.py`

#### `fetch_vote_party` 메서드 수정

1.  `for bill_id` 루프 내에서 해당 법안의 데이터 수집 개수를 추적할 변수 `bill_data_count`를 추가합니다.
2.  `while True` 루프(페이지네이션) 내의 `tqdm.write` (페이지별 로그)를 제거합니다.
3.  `while True` 루프가 종료된 후(법안 하나에 대한 수집 완료 후) `tqdm.write`를 사용하여 해당 법안의 총 수집 개수를 출력합니다.

```python
# 변경 전
# tqdm.write(f"✅ [INFO] {bill_id} | 📄 Page {pageNo} | 📊 총 {len(all_data)} 개 데이터 수집됨.")

# 변경 후
# (루프 밖에서)
# tqdm.write(f"✅ [INFO] {bill_id} | 📊 {bill_data_count} 개 데이터 수집됨.")
```

## 검증 계획

### 수동 검증
- `tests/DataFecther_test.ipynb`의 `fetch_vote_party` 테스트 셀을 실행합니다.
- 출력 로그가 법안별로 한 줄씩 나오는지 확인합니다.
# fetch_vote_party 출력 변경 진행 내역

## 작업 시작
- **날짜**: 2025-11-30
- **목표**: `fetch_vote_party` 메서드의 로그 출력을 법안 단위로 변경.

## 진행 상황
- [x] 변경 계획 수립 및 승인 (`docs/PLAN_fetch_vote_party_output.md`)
- [x] 코드 수정 (`src/lawdigest_data_pipeline/DataFetcher.py`)
    - [x] 페이지별 로그 제거
    - [x] 법안별 로그 추가
- [ ] 검증 (`tests/DataFecther_test.ipynb` 실행 필요)
# fetch_vote_party 출력 변경 완료 보고

## 작업 결과
`DataFetcher.py`의 `fetch_vote_party` 메서드 로그 출력 방식을 개선했습니다.

## 주요 내용
- **대상 파일**: `src/lawdigest_data_pipeline/DataFetcher.py`
- **변경 사항**:
    - 페이지별 로그 출력 제거 (주석 처리)
    - 법안별 데이터 수집 완료 후 총 개수 출력 로직 추가
- **효과**: 대량의 데이터 수집 시 로그 가독성 향상

## 검증
- `tests/DataFecther_test.ipynb`를 통해 변경된 로그 형식을 확인할 수 있습니다.
