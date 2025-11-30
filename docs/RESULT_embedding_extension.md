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
