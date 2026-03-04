# Bug: AI Summary 생성 실패 시 Fallback 로직 구현

**작성일**: 2026-01-25  
**관련 이슈**: [LawDigest-FE #266](https://github.com/LawDigest/LawDigest-FE/issues/266)  
**Linear 이슈**: [LAW-304](https://linear.app/lawdigest/issue/LAW-304)

---

## 1. 문제 정의

### 1.1 현상
- 메인피드에서 `gpt-summary` 필드가 누락된 콘텐츠가 있을 때 500 에러로 사이트 접속 불가
- 사용자 경험 저하 및 서비스 안정성 문제 발생

### 1.2 원인
- **Gemini API 일일 quota 초과**로 인한 API 호출 실패
- **Fallback 로직 부재**로 인해 결함 데이터가 DB에 그대로 업로드됨
- 현재 `AISummarizer.py`에서 예외 처리는 있으나, 대체 API로 재시도하는 로직 없음

### 1.3 영향 범위
- **데이터 파이프라인**: `src/lawdigest_data_pipeline/AISummarizer.py`
- **환경 변수**: `.env` 파일 (비상용 API 키 추가 필요)
- **데이터베이스**: 기존 결측치 복구 필요

---

## 2. 해결 방안

### 2.1 Fallback 로직 구현 (우선순위)

#### 2.1.1 다단계 Fallback 전략
```
1차 시도: Gemini API (Primary Key)
    ↓ 실패
2차 시도: Gemini API (Backup Key)
    ↓ 실패
3차 시도: OpenAI GPT API
    ↓ 실패
최종 처리: 해당 데이터 제외 (DB 업로드 안 함)
```

#### 2.1.2 구현 위치
- **파일**: `src/lawdigest_data_pipeline/AISummarizer.py`
- **메서드**: 
  - `AI_title_summarize()` - 제목 요약
  - `AI_content_summarize()` - 내용 요약

#### 2.1.3 필요한 환경 변수 추가
```bash
# .env 파일에 추가
GEMINI_API_KEY_BACKUP = "백업용_API_키"
```

### 2.2 기존 결측치 복구 (Linear LAW-304)

#### 2.2.1 복구 대상 확인
- DB에서 `gptSummary` 또는 `briefSummary`가 NULL인 레코드 조회
- 복구 가능한 데이터 목록 작성

#### 2.2.2 복구 스크립트 작성
- 결측치가 있는 데이터를 찾아서 AI 요약 재생성
- Fallback 로직을 적용하여 안정적으로 처리

---

## 3. 구현 계획

### Phase 1: Fallback 로직 구현 ✅ (진행 예정)

#### 3.1 AISummarizer 클래스 리팩토링
- [ ] `_invoke_llm_with_fallback()` 메서드 추가
  - Gemini Primary → Gemini Backup → OpenAI GPT 순서로 시도
  - 각 단계별 에러 로깅
  - 최종 실패 시 None 반환
  
- [ ] `AI_title_summarize()` 메서드 수정
  - 기존 `llm.invoke()` 호출을 `_invoke_llm_with_fallback()`으로 대체
  - 실패한 데이터는 DataFrame에서 제외
  
- [ ] `AI_content_summarize()` 메서드 수정
  - 기존 `llm.invoke()` 호출을 `_invoke_llm_with_fallback()`으로 대체
  - 실패한 데이터는 DataFrame에서 제외

#### 3.2 환경 변수 설정
- [ ] `.env` 파일에 `GEMINI_API_KEY_BACKUP` 추가
- [ ] 백업 API 키 발급 및 설정

#### 3.3 테스트 코드 작성
- [ ] Fallback 로직 단위 테스트
  - Gemini Primary 실패 시나리오
  - Gemini Backup 실패 시나리오
  - 모든 API 실패 시나리오
- [ ] 통합 테스트
  - 실제 데이터로 파이프라인 전체 테스트

### Phase 2: 기존 결측치 복구 (LAW-304)

#### 2.1 결측치 조회 스크립트
- [ ] `scripts/find_missing_summaries.py` 작성
  - DB 연결 및 결측치 조회
  - 결과를 CSV로 저장

#### 2.2 결측치 복구 스크립트
- [ ] `scripts/repair_missing_summaries.py` 작성
  - 결측치 데이터를 읽어서 AI 요약 재생성
  - Fallback 로직 적용
  - DB 업데이트

#### 2.3 검증
- [ ] 복구 전후 데이터 비교
- [ ] 프론트엔드에서 정상 표시 확인

---

## 4. 기술적 고려사항

### 4.1 API Rate Limiting
- Gemini API quota 모니터링 필요
- 필요시 요청 간 delay 추가 고려

### 4.2 에러 로깅
- 각 Fallback 단계별 실패 원인 상세 로깅
- Discord 알림으로 관리자에게 즉시 통보

### 4.3 성능
- Fallback으로 인한 처리 시간 증가 예상
- 배치 처리 시 타임아웃 설정 조정 필요

### 4.4 비용
- OpenAI API 사용 시 추가 비용 발생
- 월별 API 사용량 모니터링 필요

---

## 5. 예상 일정

| 단계 | 작업 | 예상 소요 시간 |
|------|------|----------------|
| Phase 1.1 | Fallback 로직 구현 | 2시간 |
| Phase 1.2 | 환경 변수 설정 | 30분 |
| Phase 1.3 | 테스트 코드 작성 | 1시간 |
| Phase 2.1 | 결측치 조회 스크립트 | 1시간 |
| Phase 2.2 | 결측치 복구 스크립트 | 1.5시간 |
| Phase 2.3 | 검증 및 문서화 | 1시간 |
| **총계** | | **약 7시간** |

---

## 6. 다음 단계

1. ✅ 문제 분석 및 계획 수립 (현재)
2. ⏳ Phase 1: Fallback 로직 구현
3. ⏳ Phase 2: 기존 결측치 복구
4. ⏳ 프론트엔드 팀과 협업하여 통합 테스트
5. ⏳ 프로덕션 배포 및 모니터링

---

## 7. 참고 자료

- [LawDigest-FE Issue #266](https://github.com/LawDigest/LawDigest-FE/issues/266)
- [Linear Issue LAW-304](https://linear.app/lawdigest/issue/LAW-304)
- 현재 코드: `src/lawdigest_data_pipeline/AISummarizer.py`
