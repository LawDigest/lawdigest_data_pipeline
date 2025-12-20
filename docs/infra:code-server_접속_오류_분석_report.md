# code-server 접속 오류 분석 보고서

## 문제 상황
- **증상**: `code-server` 컨테이너가 정상 실행 중임에도 불구하고, 도메인 접속 시 404 Not Found 에러 발생.
- **관측**: `docker ps` 상 컨테이너는 정상 (`Up`). 로컬 `curl` 테스트 시 로그인 페이지로 리다이렉트 정상.

## 원인 분석
1. **Nginx 설정 확인**: `/etc/nginx/sites-enabled/code-server.conf`
   ```nginx
   server {
       if ($host = lawdigest.cloud) {
           return 301 https://$host$request_uri;
       }
       listen 80;
       ...
       return 404;
   }
   ```
2. **로그 분석**: `/var/log/nginx/access.log` 확인 결과, 클라이언트가 `www.lawdigest.cloud`로 접속 시도.
3. **결론**: Nginx 설정 상 `lawdigest.cloud` (non-www) 호스트에 대해서만 HTTPS 리다이렉트가 설정되어 있으며, 그 외 도메인(예: `www` 포함)은 404를 반환하도록 되어 있음.

## 해결 방안
- **사용자 결정**: 설정 수정 없이 `www`를 제외한 `lawdigest.cloud`로 접속하기로 함.
- **조치 사항**: 별도의 설정 변경 없음.

## 참고 사항
- 향후 `www` 서브도메인 지원이 필요할 경우, Nginx 설정의 `if` 조건문을 제거하거나 `server_name`에 맞춰 리다이렉트 규칙을 수정해야 함.
