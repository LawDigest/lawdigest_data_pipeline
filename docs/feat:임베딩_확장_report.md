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
# HuggingFace 임베딩 기능 확장 완료

## 최종 결과
`lawdigest_ai/embedding_generator.py`에 HuggingFace `sentence-transformers` 모델을 사용한 임베딩 생성 기능이 성공적으로 추가되었습니다. 이제 `EmbeddingGenerator` 클래스는 기존의 OpenAI 모델뿐만 아니라, 사용자가 지정하는 HuggingFace 모델을 통해서도 텍스트 임베딩을 생성할 수 있습니다.

### 주요 변경 사항
- **라이브러리 추가**: `requirements.txt`에 `sentence-transformers`와 `torch`를 추가하여 HuggingFace 모델 지원에 필요한 의존성을 확보했습니다.
- **클래스 구조 변경**: `EmbeddingGenerator` 클래스는 이제 `model_type` 인자(`'openai'` 또는 `'huggingface'`)를 받아, 해당 타입에 맞는 모델을 동적으로 로드하고 초기화합니다.
- **유연성 확보**: HuggingFace 모델을 사용하고자 할 경우, 모델 이름(예: `jhgan/ko-sroberta-multitask`)을 지정하여 손쉽게 임베딩 모델을 교체하고 실험할 수 있는 환경이 마련되었습니다.
- **안정성 강화**: 모델 로딩 및 임베딩 생성 과정에서 발생할 수 있는 오류에 대한 예외 처리와 명확한 로그 메시지를 추가하여 안정성을 높였습니다.

## 사용자 주의사항
- **HuggingFace 모델 사용법**: `EmbeddingGenerator` 클래스를 `'huggingface'` 타입으로 인스턴스화할 때는, `model_name` 인자에 HuggingFace Hub에 등록된 모델 이름을 정확하게 전달해야 합니다. 모델 이름을 잘못 입력하면 모델 로딩에 실패할 수 있습니다.
  ```python
  # HuggingFace 모델 사용 예시
  hf_embedding_generator = EmbeddingGenerator(model_type='huggingface', model_name='jhgan/ko-sroberta-multitask')
  embedding = hf_embedding_generator.generate("임베딩할 텍스트입니다.")
  ```
- **의존성 설치**: 변경된 코드를 사용하기 전에, 새로 추가된 라이브러리를 설치해야 합니다. 아래 명령어를 사용하여 `requirements.txt`에 명시된 모든 의존성을 설치하십시오.
  ```bash
  pip install -r requirements.txt
  ```
- **초기 모델 로딩 시간**: HuggingFace 모델은 처음 사용할 때 모델 파일을 다운로드하고 캐싱하는 과정에서 시간이 소요될 수 있습니다. 이후 실행부터는 캐시된 모델을 사용하므로 로딩 시간이 단축됩니다.
