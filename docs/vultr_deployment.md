# ScholarCheck Vultr Deployment Guide

이 문서는 ScholarCheck 웹 UI를 Vultr Ubuntu 서버에 배포하기 위한 운영 준비 문서입니다.

기본 운영 구조:

```text
Internet
  -> Nginx :80/:443
  -> 127.0.0.1:8765
  -> python -m scholarcheck.web
```

ScholarCheck 자체 웹 서버는 인증, TLS, 접근 제어를 직접 제공하지 않습니다. 공개 서버에서는 Nginx 뒤에 두고, 최소한 Basic Auth 또는 IP 제한을 적용하는 것을 권장합니다.

## 1. 서버 준비

권장 환경:

- Vultr Ubuntu 22.04 또는 24.04
- Python 3.11 이상
- Nginx
- Git
- 최소 1 vCPU / 1GB RAM 이상

방화벽 예시:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

## 2. 자동 설치 스크립트

서버에서 다음처럼 실행합니다.

```bash
git clone https://github.com/boundaryx01-uniquelife/scholarcheck.git
cd scholarcheck
sudo bash deploy/vultr/install_ubuntu.sh
```

특정 릴리즈 태그로 설치하려면:

```bash
sudo env GIT_REF=v0.1.0 bash deploy/vultr/install_ubuntu.sh
```

설치 위치 기본값:

```text
/opt/scholarcheck/current
```

실행 사용자 기본값:

```text
scholarcheck
```

## 3. systemd 서비스

서비스 파일:

```text
deploy/vultr/scholarcheck.service
```

설치 후 상태 확인:

```bash
sudo systemctl status scholarcheck
sudo journalctl -u scholarcheck -f
```

수동 재시작:

```bash
sudo systemctl restart scholarcheck
```

서비스는 내부 주소에서만 실행됩니다.

```bash
python -m scholarcheck.web --host 127.0.0.1 --port 8765
```

서버 내부에서 확인:

```bash
curl http://127.0.0.1:8765/
```

## 4. Nginx 설정

템플릿:

```text
deploy/vultr/nginx_scholarcheck.conf
```

적용 예시:

```bash
sudo cp /opt/scholarcheck/current/deploy/vultr/nginx_scholarcheck.conf /etc/nginx/sites-available/scholarcheck
sudo nano /etc/nginx/sites-available/scholarcheck
sudo ln -s /etc/nginx/sites-available/scholarcheck /etc/nginx/sites-enabled/scholarcheck
sudo nginx -t
sudo systemctl reload nginx
```

`server_name example.com;`을 실제 도메인 또는 서버 IP로 바꿉니다.

## 5. HTTPS 적용

도메인을 연결했다면 Certbot 사용을 권장합니다.

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.example
```

도메인 없이 IP만으로 운영할 경우 HTTPS 인증서는 별도 구성이 필요합니다. 공개 운영은 도메인 연결 후 HTTPS 적용을 권장합니다.

## 6. Basic Auth 권장

ScholarCheck MVP는 교수님 검토용 로컬/소규모 운영 도구입니다. 공개 주소로 열 경우 최소한 Basic Auth를 적용하세요.

```bash
sudo apt install -y apache2-utils
sudo htpasswd -c /etc/nginx/.scholarcheck_htpasswd admin
```

Nginx 설정에서 다음 주석을 해제합니다.

```nginx
auth_basic "ScholarCheck";
auth_basic_user_file /etc/nginx/.scholarcheck_htpasswd;
```

적용:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

## 7. 데이터 디렉터리

운영 중 생성되는 데이터:

```text
data/sessions/
data/projects/
data/backups/
data/domestic_manual_checks.json
outputs/
```

이 데이터는 Git에 커밋하지 않습니다. 서버 백업 대상에는 포함해야 합니다.

백업 예시:

```bash
sudo tar -czf /opt/scholarcheck/scholarcheck-data-$(date +%Y%m%d).tar.gz \
  -C /opt/scholarcheck/current data outputs
```

## 8. 업데이트 절차

최신 main으로 업데이트:

```bash
cd /opt/scholarcheck/current
sudo git fetch --all --tags
sudo git checkout main
sudo git pull --ff-only
sudo .venv/bin/python -m pip install -e .
sudo systemctl restart scholarcheck
```

릴리즈 태그로 고정:

```bash
cd /opt/scholarcheck/current
sudo git fetch --all --tags
sudo git checkout v0.1.0
sudo .venv/bin/python -m pip install -e .
sudo systemctl restart scholarcheck
```

## 9. 배포 후 점검

서버 내부:

```bash
curl -I http://127.0.0.1:8765/
sudo systemctl status scholarcheck
```

Nginx:

```bash
sudo nginx -t
curl -I http://your-domain.example/
```

앱 기능:

- 홈 화면 접속
- 검색 실행
- 결과 없음 안내 확인
- CSV/JSON 다운로드
- 세션 저장/불러오기
- 세션 HTML/Excel 다운로드
- 프로젝트 생성
- 프로젝트 HTML/Excel 다운로드

## 10. 운영 제한 사항

ScholarCheck는 외부 API 메타데이터 기반 검증 보조 도구입니다.

- 논문 존재 여부를 최종 보증하지 않습니다.
- DOI, 저자, 학술지, 링크를 임의 생성하지 않습니다.
- `UNKNOWN` 값을 임의 보완하지 않습니다.
- 국내 DB는 자동 크롤링하지 않습니다.
- 국내 DB 수동 기록은 자동 검증 결과가 아닙니다.
- 최종 인용 전 원문 페이지 확인이 필요합니다.

공개 운영에서는 사용자 입력과 저장 데이터가 서버에 남을 수 있습니다. 민감한 연구 주제나 내부 검토 자료를 다룰 경우 접근 제한과 백업 정책을 먼저 정하세요.
