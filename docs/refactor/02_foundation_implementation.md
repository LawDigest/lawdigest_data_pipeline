# 구현 상세 문서: 1. 기반 구조 (Foundation)

## 1. 개요
Phase 1에서 진행할 `DatabaseManager` 리팩토링 및 공통 모듈 구현에 대한 상세 설계를 기술합니다.

## 2. Java -> Python 클래스 매핑

| Java Class (Lawbag) | Python Module (lawdigest) | 역할 |
|:---|:---|:---|
| `BillStageType.java` | `src/lawdigest_data_pipeline/constants.py` | 법안 단계 정의 및 순서 비교(`can_update_stage`) |
| `ProposerKindType.java` | `src/lawdigest_data_pipeline/constants.py` | 발의자 유형(의원, 정부, 위원장) 정의 |
| `DataService.java` | `src/lawdigest_data_pipeline/DatabaseManager.py` | DB 연결, 트랜잭션 관리, 쿼리 실행 담당 |

## 3. DatabaseManager 리팩토링 설계

### 3.1 트랜잭션 관리 (`Context Manager`)
기존의 `autocommit=True` 방식을 제거하고, Python의 `with` 구문을 사용한 트랜잭션 관리를 도입합니다.

```python
from contextlib import contextmanager

class DatabaseManager:
    # ... (init) ...
    
    @contextmanager
    def transaction(self):
        """
        트랜잭션 스코프를 관리하는 Context Manager.
        예외 발생 시 자동 롤백, 정상 종료 시 커밋을 수행합니다.
        """
        if not self.connection or not self.connection.open:
             self.connect()
             
        try:
            self.connection.begin()
            yield self.connection.cursor()
            self.connection.commit()
        except Exception as e:
            self.connection.rollback()
            # 로깅 추가 필요
            raise e
```

### 3.2 배치 처리 (`executemany`)
대량 데이터 삽입 시 성능 최적화를 위해 `executemany`를 사용하는 메소드를 추가합니다.

```python
    def execute_batch(self, query, params_list):
        """
        대량의 데이터를 일괄 삽입/수정합니다.
        
        Args:
            query (str): 실행할 SQL 쿼리 (Placeholder 포함)
            params_list (list of tuple): 쿼리에 바인딩할 파라미터 리스트
        """
        with self.transaction() as cursor:
            cursor.executemany(query, params_list)
```

## 4. 상수 및 유틸리티 구현 (`constants.py`)

### 4.1 BillStageType 구현
```python
from enum import Enum

class BillStageType(Enum):
    WITHDRAWAL = (0, "철회", "철회")
    RECEIPT = (1, "접수", "접수")
    # ... (나머지 단계) ...
    
    def __init__(self, order, key, value):
        self.order = order
        self.key = key
        self.value = value
        
    @classmethod
    def can_update_stage(cls, current_val, next_val):
        # Java의 canUpdateStage 로직 포팅
        # 순서 비교 등
        pass
```
