# n8n 워크플로우 Import 가이드(내부 서버, 레거시/보관)

> 상태: **Deprecated (2026-03-08)**  
> 운영 스케줄러는 Airflow로 복귀했습니다. 이 문서는 과거 n8n 자산 조회/복원 용도로만 유지합니다.

본 가이드는 내부에 배포된 self-hosted n8n에 workflow JSON을 넣고 등록하는 절차만 정리한다.

## 1) 기본 전제
- 워크플로우는 파일을 놓는 것만으로 UI에 자동 반영되지 않는다.
- `n8n import:workflow` CLI로 DB(`/home/node/.n8n`)에 등록해야 목록에 노출된다.
- 현재 배포 기준 기본 컨테이너명: `n8n`

## 2) 저장 위치 확인
```bash
docker inspect -f '{{range .Mounts}}{{if eq .Destination "/home/node/workflows"}}{{.Source}} => {{.Destination}} ({{.Mode}}){{end}}{{end}}' n8n
```

- 보통 읽기 전용 마운트: `/home/node/workflows` → 호스트 워크플로우 디렉터리
- 볼륨 DB 위치: `/home/node/.n8n`

## 3) Import 절차 (권장)
### A. 임시 파일 경유(가장 확실)
```bash
docker cp /home/ubuntu/project/lawdigest/n8n/lawdigest_db_pipeline_hourly.json n8n:/tmp/lawdigest_db_pipeline_hourly.json
docker exec n8n n8n import:workflow --input=/tmp/lawdigest_db_pipeline_hourly.json
```

### B. 디렉터리 일괄 임포트
```bash
docker compose -f /home/ubuntu/docker/compose/n8n/docker-compose.yml exec n8n \
  n8n import:workflow --separate --input=/home/node/workflows
```

## 4) 임포트 확인
```bash
docker exec n8n n8n list:workflow
```

정상 시 `workflow_id|name` 형식이 출력되어야 한다.  
UI에서는 `workflows` 목록에서 이름 검색으로도 확인한다.

### 반복 작업용 자동 임포트 스크립트
- 변경 후 바로 반영하려면 아래 스크립트를 실행한다.
```bash
scripts/import_lawdigest_bills_pipeline.sh
```

## 5) 실행/활성화
- 등록만으로는 비활성일 수 있다.
- UI에서 해당 워크플로우를 열어 `Active` 토글을 켜서 스케줄 실행을 시작한다.
- CLI 실행 검증이 필요하면 아래처럼 실행한다.
```bash
scripts/n8n_execute_with_safe_broker.sh --id=<workflow_id>
```

## 6) 재임포트와 기존 워크플로우 업데이트 (중요)
`n8n import:workflow` 명령은 기본적으로 JSON 파일에 `id` 필드가 없으면 **새로운 워크플로우**를 생성하여 추가한다. 기존 워크플로우를 수정(Update)하려면 아래 절차를 따른다.

### A. 기존 워크플로우 ID 확인
```bash
docker exec n8n n8n list:workflow
```
출력 예시: `VqZ4if5CN1vTtYhl|lawdigest-bills-pipeline-v2`  
여기서 앞부분인 `VqZ4if5CN1vTtYhl`이 고유 ID이다.

### B. JSON 파일에 ID 명시
수정하려는 JSON 파일 최상단에 확인한 `id` 필드를 추가한다.
```json
{
  "id": "VqZ4if5CN1vTtYhl",
  "name": "lawdigest-bills-pipeline-v2",
  ...
}
```

### C. 재임포트
이 상태에서 다시 `import:workflow`를 실행하면 n8n이 동일 ID가 있음을 감지하고 기존 워크플로우를 **덮어쓰기(Update)** 한다.

## 7) 중복 워크플로우 정리
실수로 ID 없이 임포트하여 중복이 생겼다면 UI에서 직접 삭제하거나, DB 수정을 통해 정리해야 한다. (현재 CLI에는 단일 워크플로우 삭제 명령이 없을 수 있음)

## 8) 자주 생기는 문제
1. **UI에 안 뜸**
   - `n8n list:workflow`에서 존재 여부 확인
   - import 명령이 에러 없이 끝났는지 확인
2. **Command 노드가 실패**
   - n8n 컨테이너 내 경로(`/home/ubuntu/project/lawdigest`)와 환경이 워크플로우 JSON의 `command`와 맞는지 점검
3. **호스트 파일 변경 반영 안 됨**
   - 마운트 경로가 바뀌었거나 읽기 권한이 다르면 `docker cp` + 직접 import 방식으로 우회
4. **`Task Broker's port 5679 is already in use` 에러**
   - 원인: 실행 중인 n8n 메인 프로세스가 이미 5679를 사용 중인데, `n8n execute`가 같은 포트로 별도 브로커를 띄우며 충돌
   - 해결: `execute` 호출 시 브로커 포트를 별도 지정
```bash
docker exec -e N8N_RUNNERS_BROKER_PORT=5689 n8n n8n execute --id=<workflow_id>
```
   - 재발 방지: `scripts/n8n_execute_with_safe_broker.sh` 사용
5. **`.env`를 바꿨는데 노드에서 새 환경변수를 못 읽음**
   - 원인: `docker compose`의 `.env`는 컨테이너 생성 시점에만 주입되며, `docker compose restart`만으로는 반영되지 않음
   - 해결: `n8n`/`runners` 컨테이너 재생성
```bash
cd /home/ubuntu/docker/compose/n8n
docker compose up -d --force-recreate n8n runners
```
   - 확인:
```bash
docker inspect n8n --format '{{range .Config.Env}}{{println .}}{{end}}' | grep '^DISCORD_WEBHOOK_URL='
```

## 9) 참고
- 기존 마이그레이션 가이드: `docs/n8n_pipeline_migration.md`
