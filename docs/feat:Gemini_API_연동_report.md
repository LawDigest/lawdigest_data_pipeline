# Gemini API 연동 및 요약 가속화 작업 보고서

## 1. 개요
기존 OpenAI GPT 모델 기반의 법안 요약 기능을 Google Gemini API로 확장하여 비용 절감 및 처리 속도 향상을 도모하고, 안정적인 데이터 파이프라인 구축을 위한 리팩토링을 수행했습니다.

## 2. 작업 목표
- Langchain을 활용한 Gemini API (`gemini-3-flash-preview`) 연동
- OpenAI API와의 호환성 유지 및 모델 선택 유연성 확보
- 공공데이터포털 API의 간헐적 타임아웃/연결 오류 해결
- 테스트 자동화 및 데이터 전처리 로직 검증

## 3. 상세 구현 내용

### 3.1 의존성 및 환경 설정
- **라이브러리 추가**: `langchain-google-genai` 패키지 추가
- **버전 호환성 해결**: `langchain`, `langchain-community`, `langchain-core` 등 관련 패키지 일괄 업데이트로 의존성 충돌 해결
- **환경 변수**: `.env` 파일에 `GEMINI_API_KEY`, `GEMINI_MODEL` 추가 및 기본 요약 모델(`TITLE_SUMMARIZATION_MODEL`, `CONTENT_SUMMARIZATION_MODEL`)을 `gemini-3-flash-preview`로 변경

### 3.2 AISummarizer 리팩토링
- **Gemini 지원 추가**: 모델명이 `gemini`로 시작할 경우 `ChatGoogleGenerativeAI`를, 그 외에는 `ChatOpenAI`를 사용하도록 조건부 로직 구현
- **API Key 처리**: Gemini용 API Key 로드 로직 추가

### 3.3 DataFetcher 안정성 강화
- **Session & Retry 도입**: `requests.Session`과 `HTTPAdapter`를 도입하여 연결 재사용 및 지수 백오프(Exponential Backoff) 기반의 재시도 로직 구현
- **Timeout 연장**: 공공데이터포털의 느린 응답에 대비해 타임아웃을 10초에서 30초로 연장
- 이를 통해 `HTTPConnectionPool Read timed out` 오류를 근본적으로 해결했습니다.

### 3.4 테스트 및 검증
- **테스트 스크립트 작성**: `tests/test_ai_summarizer_gemini.py`
- **DataProcessor 통합**: 단순 API 호출만으로는 `proposers`(발의자) 등의 파생 컬럼이 생성되지 않는 문제를 파악하여, 테스트 코드에 `DataProcessor` 로직을 통합해 실제 파이프라인과 동일한 환경 구성
- **결과 저장**: 테스트 결과를 `tests/result/gemini_test_result.json`에 저장하도록 구현 (불필요한 메타데이터 제거 및 순수 텍스트 요약만 추출)

## 4. 문제 해결 (Troubleshooting)

### 4.1 의존성 충돌
- **문제**: `pip install langchain-google-genai` 시 기존 `langchain` 버전과의 충돌 발생
- **해결**: 관련 패키지 전체를 최신 버전으로 업그레이드하여 해결

### 4.2 API 타임아웃
- **문제**: 데이터 수집 시 첫 번째 요청에서 빈번하게 `Read timed out` 오류 발생
- **해결**: `requests`의 기본 타임아웃을 늘리고, Connection Pool 및 Retry 전략을 적용하여 안정성 확보

### 4.3 데이터 컬럼 누락
- **문제**: `DataFetcher`는 Raw Data만 가져오므로 `AISummarizer`가 필요로 하는 `proposers` 컬럼이 부재
- **해결**: `DataProcessor`의 `process_congressman_bills` 메서드를 활용하여 발의자 정보를 파싱하고 병합하는 로직을 테스트에 적용

## 5. 결론
Gemini API 연동이 성공적으로 완료되었으며, 이를 기본 모델로 설정하여 운영 비용 절감 및 성능 개선이 기대됩니다. 또한 데이터 수집 모듈의 안정성이 대폭 강화되었습니다.
