# HuggingFace 임베딩 기능 확장 진행 내역

## 완료된 작업
- **`requirements.txt` 수정**:
  - `sentence-transformers` 및 `torch` 라이브러리를 의존성에 추가하여 HuggingFace 모델을 사용할 수 있는 환경을 구축했습니다.

- **`lawdigest_ai/embedding_generator.py` 수정**:
  - `EmbeddingGenerator` 클래스의 `__init__` 메서드를 수정하여 `model_type`과 `model_name`을 인자로 받도록 변경했습니다.
  - `model_type` 값에 따라 OpenAI 또는 HuggingFace 모델을 선택적으로 초기화하는 로직을 구현했습니다.
    - `openai`: 기존 OpenAI 클라이언트 초기화 로직 유지
    - `huggingface`: `SentenceTransformer`를 사용하여 지정된 `model_name`의 모델 로드
  - `generate` 메서드를 수정하여 선택된 모델 타입에 따라 적절한 임베딩 생성 로직을 수행하도록 구현했습니다.
  - 모델 로딩 및 임베딩 생성 과정에서 발생할 수 있는 예외 처리를 추가하고, 사용자에게 명확한 상태 메시지를 제공하도록 로깅을 개선했습니다.

## 다음 단계
- 변경된 `EmbeddingGenerator` 클래스를 사용하는 다른 코드 부분에서 새로운 기능을 올바르게 활용하는지 확인하고 필요시 수정합니다.
- 실제 HuggingFace 모델(예: `jhgan/ko-sroberta-multitask`)을 사용하여 임베딩 생성 기능이 정상적으로 동작하는지 테스트합니다.
