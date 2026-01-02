# 구현 상세 문서: 2. 데이터 적재 로직 (Logic Migration)

## 1. 개요
`DataService.java`의 비즈니스 로직을 Python `DatabaseManager` 내의 메소드로 이관하는 상세 계획입니다.

## 2. 법안 정보 적재 (`insertBillInfoDf`)

### 2.1 로직 분석 (AS-IS)
1.  입력된 `BillDfRequest` 리스트를 순회.
2.  `billId`로 기존 법안 조회.
    -   존재 시: `updateContent` (내용 업데이트)
    -   미존재 시: `Bill` 생성 및 Insert
3.  **발의자 연결 (`BillProposer`)**:
    -   `publicProposerIdList` (공동발의자 ID 목록) 순회.
    -   `Congressman` 테이블에서 ID로 조회 (존재 확인).
    -   존재 시 `BillProposer` 객체 생성 및 저장.
    -   미존재 시 `CongressmanNotFoundException` 발생.
4.  **대표발의자 연결 (`RepresentativeProposer`)**:
    -   `rstProposerIdList` 순회 및 유사 로직 수행.

### 2.2 구현 설계 (TO-BE)

```python
def insert_bill_info(self, bills_data: List[Dict]):
    """
    법안 정보를 DB에 적재합니다. (insertBillInfoDf 대응)
    """
    with self.transaction() as cursor:
        for bill in bills_data:
            # 1. Bill 테이블 Upsert (INSERT ... ON DUPLICATE KEY UPDATE 활용 고려)
            self._upsert_bill(cursor, bill)
            
            # 2. 발의자 정보 처리 (기존 연결 삭제 후 재삽입 또는 변경분 반영 전략 결정 필요)
            # 여기서는 편의상 기존 관계를 유지하며 추가하는 방식 등을 고려해야 함.
            # Java 로직: "기존 것 update" + "새로운 관계 add" (상세 로직 재확인 필요)
            
            # 3. 외래 키 검증 및 매핑
            self._link_proposers(cursor, bill['bill_id'], bill['public_proposer_ids'])
            self._link_rep_proposers(cursor, bill['bill_id'], bill['rst_proposer_ids'])
```

### 2.3 주요 이슈 및 해결 방안
-   **N+1 문제 해결**: Java는 Loop를 돌며 하나씩 쿼리를 날리지만(`save`), Python에서는 `executemany`를 사용하여 Bill 데이터를 한 번에 넣도록 최적화합니다.
-   **FK 검증**: DB에 쿼리를 날려 존재하는 의원 ID 목록을 미리 가져온 후(`Set` 활용), 유효한 ID에 대해서만 `BillProposer`를 Insert 합니다. 없는 ID는 에러 로그를 남깁니다.

## 3. 의원 정보 동기화 (`updateLawmakerDf`)

### 3.1 로직 분석 (AS-IS)
-   `API 데이터`와 `DB 데이터`의 교집합, 차집합을 구하여 처리.
    -   **Insert**: API에만 있는 데이터 (신규 의원)
    -   **Update State(False)**: DB에만 있는 데이터 (사퇴/제명 등)
    -   **Update Info**: 둘 다 있는 데이터 (정보 갱신 및 State True 유지)

### 3.2 구현 설계 (TO-BE)
Python의 `set` 자료형을 활용하여 매우 효율적으로 구현 가능합니다.

```python
def update_lawmaker_info(self, new_lawmakers: List[Dict]):
    # 1. DB에서 전체 의원 ID 로드 -> Set
    # 2. API 데이터의 의원 ID -> Set
    # 3. Set 연산 (Insert 대상, Disable 대상, Update 대상 분류)
    # 4. 각 그룹별 Batch Query 실행
```
