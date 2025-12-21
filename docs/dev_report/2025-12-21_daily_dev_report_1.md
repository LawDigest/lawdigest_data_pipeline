# 2025-12-21 개발 일지 (Gemini 연동 및 안정화)

## 1. 개요

| 항목 | 내용 |
| :--- | :--- |
| **날짜** | 2025년 12월 21일 |
| **주요 작업** | Gemini API 연동, DataFetcher 연결 안정성 강화, 통합 테스트 및 문서화 |
| **작업자** | Minjae Park (Assistant: Antigravity) |

### 📝 요약
기존 OpenAI 중심의 요약 기능을 확장하여 Google Gemini API를 도입하고, 공공데이터포털 API의 간헐적 타임아웃 문제를 해결하기 위해 데이터 수집 모듈의 안정성을 대폭 강화했습니다. 또한 이를 검증하기 위한 통합 테스트 스크립트를 작성하고 문서화를 완료했습니다.

### 💻 커밋 내역
- `8699323` docs: Gemini API 연동 결과 보고서 추가 및 의존성 업데이트
- `d7343b8` test: Gemini 통합 테스트 코드 추가
- `ba45d98` feat: 데이터 수집 API 연결 불안정 해소를 위해 재시도 로직 추가, timeout 30초로 증가
- `97aeaa2` feat: Gemini API 연결 기능 추가

<br>

## 2. 진행 작업

### 📌 작업 1: Gemini API 통합 (Langchain 기반)

#### 🎯 목적
- 운영 비용 절감 및 모델 선택의 유연성 확보를 위해 Google Gemini 모델(`gemini-3-flash-preview`)을 요약 엔진으로 도입.

#### 🛠 상세 변경 사항
- **`AISummarizer.py` 리팩토링**: 
  - `langchain-google-genai` 패키지를 도입하여 `ChatGoogleGenerativeAI` 클래스 활용.
  - 모델명이 `gemini`로 시작할 경우 자동으로 Gemini API를 호출하고, 그렇지 않으면 기존 OpenAI 로직을 타도록 분기 처리 구현.
- **환경 변수 및 의존성 관리**:
  - `.env`에 `GEMINI_API_KEY`, `GEMINI_MODEL` 추가 및 기본 모델 설정 변경.
  - `requirements.txt`에 `langchain-google-genai` 추가 및 `langchain` 관련 패키지 버전 호환성 해결.

#### 📂 변경 파일
- `src/lawdigest_data_pipeline/AISummarizer.py`
- `.env`
- `requirements.txt`

#### 🚀 후속 작업 (Next Steps)
1. **모델 성능 비교 분석**: 동일 법안에 대해 GPT-4o와 Gemini-flash의 요약 품질 및 소요 시간 비교 테스트 진행.
2. **에러 핸들링 고도화**: Gemini API의 Quota Limit 도달 시 자동으로 OpenAI로 Fallback하는 로직 추가 고려.
3. **프롬프트 튜닝**: Gemini 모델 특성에 맞춰 요약 프롬프트(System Message) 미세 조정.
4. **스트리밍 지원**: 긴 응답에 대한 사용자 경험 개선을 위해 스트리밍 응답 처리 검토.
5. **비용 모니터링**: Gemini API 사용량 및 비용 로깅 시스템 구축.

<br>

### 📌 작업 2: DataFetcher 안정성 강화 (Session & Retry)

#### 🎯 목적
- 공공데이터포털 API 호출 시 빈번하게 발생하는 `HTTPConnectionPool Read timed out` 오류를 해결하여 데이터 파이프라인의 신뢰성 확보.

#### 🛠 상세 변경 사항
- **Session & Retry 전략 도입**:
  - `requests.Session` 객체를 생성하고 `HTTPAdapter`를 마운트하여 연결을 재사용하도록 개선.
  - `urllib3.util.retry.Retry`를 사용하여 연결 오류 및 500/502/503/504 에러 시 지수 백오프(Exponential Backoff) 방식으로 최대 3회 재시도하도록 설정.
- **Timeout 연장**:
  - 기존 10초였던 타임아웃 설정을 30초로 늘려 느린 서버 응답에 충분히 대기하도록 수정.
- **`src/lawdigest_data_pipeline/DataFetcher.py`**: `fetch_bills_data` 및 `fetch_data_generic` 메서드 수정.

#### 📂 변경 파일
- `src/lawdigest_data_pipeline/DataFetcher.py`

#### 🚀 후속 작업 (Next Steps)
1. **재시도 로그 모니터링**: 실제 운영 환경에서 재시도가 얼마나 자주 발생하는지 로그 분석 파이프라인 구축.
2. **동적 타임아웃 설정**: 서버 상태에 따라 타임아웃 값을 동적으로 조절하는 기능 검토.
3. **비동기 수집 전환**: 대량 데이터 수집 속도 향상을 위해 `aiohttp` 기반의 비동기 수집 모듈 도입 검토.
4. **프록시 서버 도입**: IP 차단 방지 및 안정성 확보를 위한 로테이팅 프록시 서버 연동 고려.
5. **Circuit Breaker 패턴 적용**: 장애 지속 시 불필요한 재시도를 막기 위한 Circuit Breaker 도입 검토.

<br>

### 📌 작업 3: 통합 테스트 및 검증

#### 🎯 목적
- 변경된 코드의 정상 동작 여부를 확인하고, 실제 데이터 처리 흐름과 동일한 테스트 환경 구축.

#### 🛠 상세 변경 사항
- **테스트 스크립트 작성 (`tests/test_ai_summarizer_gemini.py`)**:
  - 실제 데이터 수집 -> 전처리(`DataProcessor`) -> 요약(`AISummarizer`) -> 결과 저장의 전체 흐름 테스트.
  - 특히 `DataProcessor`를 활용하여 `proposers`(발의자) 컬럼 생성 로직을 테스트에 포함시킴으로써 실제 파이프라인과의 정합성 확보.
- **결과 저장 포맷 개선**:
  - 테스트 결과를 JSON으로 저장하되, AI 응답의 메타데이터를 제거하고 순수 텍스트만 저장하도록 정제 로직 추가.

#### 📂 변경 파일
- `tests/test_ai_summarizer_gemini.py`
- `tests/result/gemini_test_result.json`

#### 🚀 후속 작업 (Next Steps)
1. **CI 파이프라인 연동**: 해당 테스트 스크립트를 GitHub Actions 등 CI/CD 파이프라인에 포함하여 자동 테스트 수행.
2. **테스트 커버리지 확대**: 다양한 법안 유형(정부안, 위원장안 등)에 대한 테스트 케이스 추가.
3. **Mocking 도입**: 공공데이터포털 API 의존성을 줄이기 위해 `unittest.mock`을 활용한 API 응답 Mocking 테스트 추가.
4. **결과 검증 자동화**: 생성된 요약문의 길이, 필수 키워드 포함 여부 등을 검증하는 Assertion 로직 추가.
5. **대시보드 시각화**: 테스트 성공률 및 요약 품질 지표를 시각화하여 모니터링.

<br>

## 3. 현재 상태 (Current Status)

### 📊 프로젝트 상태 분석
- **완성도**: Gemini API 통합이 완료되어 멀티 모델(GPT, Gemini) 요약 시스템이 구축되었습니다. 데이터 수집 모듈 또한 타임아웃 이슈가 해결되어 매우 안정적입니다.
- **폴더 구조**: `tests/` 디렉토리에 통합 테스트 코드가 추가되었고, `docs/`에 기능 명세 및 리포트가 체계적으로 관리되고 있습니다.
- **방향성**: 이제 안정된 데이터 수집 및 요약 엔진을 바탕으로 자동화된 Airflow DAG와의 연동(이미 진행 중인 것으로 보임) 및 운영 배포 단계로 나아가야 합니다.

### 🔭 향후 프로젝트 목표 (Top 5)
1. **Airflow DAG 최적화**: 새로 구축된 모듈을 Airflow 파이프라인에 완벽하게 통합하고 스케줄링 최적화.
2. **운영 배포 및 모니터링**: 수정된 코드를 프로덕션 서버에 배포하고 ELK Stack 등을 활용한 로그 모니터링 구축.
3. **벡터 DB 파이프라인 고도화**: Qdrant를 활용한 법안 검색 및 추천 기능의 정확도 개선.
4. **사용자 피드백 루프**: 요약문에 대한 사용자 피드백(좋아요/싫어요)을 수집하여 프롬프트 개선에 활용.
5. **비용 효율화**: 토큰 사용량 분석을 통해 최적의 모델 선택 전략 수립 (간단한 법안은 저렴한 모델, 복잡한 법안은 고성능 모델 사용).

<br>

## 4. 개선사항 (Improvements)

### ⚠️ 잠재적 문제점 및 버그
- **API 키 관리**: `.env` 파일에 API 키가 관리되고 있으나, 배포 시 Secret Manager 등을 활용하는 것이 보안상 안전합니다.
- **의존성 복잡도**: Langchain 버전 업그레이드로 인해 기존 코드가 영향을 받을 수 있으므로 회귀 테스트(Regression Test)가 필요할 수 있습니다.

### ♻️ 리팩토링 제안
- **AISummarizer 추상화**: `AISummarizer` 클래스 내부의 모델 선택 로직을 별도의 `LLMFactory` 클래스로 분리하여 유지보수성 향상.
- **DataProcessor 통합**: `WorkFlowManager` 외에도 테스트 코드에서 `DataProcessor`가 중복적으로 사용되는데, 이를 더 쉽게 호출할 수 있도록 유틸리티 함수화 고려.

### 🏗 구조적 개선
- **테스트 디렉토리 구조화**: `tests/unit`, `tests/integration` 등으로 테스트 코드를 분리하여 목적에 맞게 관리.

<br>

## 5. 최종 요약

| 구분 | 내용 |
| :--- | :--- |
| **성과** | Gemini API 성공적 도입, 데이터 수집 모듈의 타임아웃 문제 근본적 해결 |
| **품질** | Retry 로직 도입으로 데이터 파이프라인의 견고함(Robustness) 향상 |
| **비용** | Gemini-flash 모델 도입으로 AI 요약 비용 절감 기반 마련 |
| **향후 과제** | Airflow 연동 최적화 및 운영 환경 모니터링 구축 |
