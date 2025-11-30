# HuggingFace 모델 기반 임베딩 기능 확장 계획

## 목표
`lawdigest_ai/embedding_generator.py`에 HuggingFace의 `sentence-transformers` 모델을 사용하여 텍스트 임베딩을 생성하는 기능을 추가합니다. 이를 통해 기존의 OpenAI 모델 외에 다양한 오픈소스 모델을 활용할 수 있도록 유연성을 확보합니다.

## 개발 계획
1. **의존성 추가**:
   - `requirements.txt` 파일에 `sentence-transformers` 라이브러리를 추가하여 HuggingFace 모델을 사용할 수 있는 환경을 구성합니다.

2. **`EmbeddingGenerator` 클래스 수정**:
   - `__init__` 메서드를 수정하여 `model_type` ('openai' 또는 'huggingface')과 `model_name`을 인자로 받도록 변경합니다.
   - `model_type` 값에 따라 분기 처리를 구현합니다.
     - 'openai': 기존과 같이 OpenAI 클라이언트를 초기화합니다.
     - 'huggingface': `SentenceTransformer` 클래스를 사용하여 지정된 `model_name`의 HuggingFace 모델을 로드합니다.
   - `generate` 메서드를 수정하여 선택된 모델 타입에 맞는 임베딩 생성 로직을 수행하도록 변경합니다.

3. **오류 처리 및 로깅**:
   - 모델 로딩 또는 임베딩 생성 과정에서 발생할 수 있는 예외 상황에 대한 오류 처리 로직을 추가합니다.
   - 각 단계별 진행 상황과 오류를 사용자가 쉽게 파악할 수 있도록 로그 메시지를 추가합니다.

## 예상 결과
- `EmbeddingGenerator` 클래스에서 'openai' 또는 'huggingface' 모델을 선택하여 사용할 수 있게 됩니다.
- 다양한 임베딩 모델을 실험하고 프로젝트에 가장 적합한 모델을 선택할 수 있는 기반이 마련됩니다.
