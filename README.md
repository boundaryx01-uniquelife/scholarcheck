# ScholarCheck / 논문나침반

논문 자료 검색, 수집, 검증을 돕는 MVP입니다.

핵심 원칙은 할루시네이션 금지입니다.

- 외부 API에서 확인된 메타데이터만 자동 검증 논문 목록에 표시합니다.
- 없는 제목, 저자, DOI, 학술지, 링크를 생성하지 않습니다.
- 누락된 값은 `UNKNOWN` 또는 확인 불가로 남깁니다.
- 국내 DB는 자동 크롤링하지 않고 직접 확인용 검색 링크만 생성합니다.

## 현재 지원 범위

- 해외 논문 API 조회: Crossref, OpenAlex
- DOI 및 메타데이터 확인
- PDF 다운로드 가능 여부 확인
- DOI/제목 기반 중복 제거
- 필수/도움/제외 키워드 기반 정렬
- 제목 키워드, 초록 키워드, DOI, PDF, 최근 5년, 인용 수 반영
- 인용 수가 높은 고전 논문 별도 표시
- 검색 결과 부족 시 검색 조건 완화 제안 출력
- CLI 표 출력
- 로컬 웹 UI
- CSV 또는 JSON 저장
- 국내 DB 직접 확인용 검색 링크 생성: RISS, KCI, DBpia, KISS, e-Article

## CLI 실행

```powershell
python -m scholarcheck "artificial intelligence education" --required "artificial intelligence,education" --helpful "teacher,curriculum" --exclude "patent,news" --limit 10 --format csv
```

Python이 PATH에 없다면 Codex 번들 Python으로 실행할 수 있습니다.

```powershell
C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m scholarcheck "artificial intelligence education"
```

## 웹 UI 실행

```powershell
python -m scholarcheck.web
```

기본 주소는 다음과 같습니다.

```text
http://127.0.0.1:8765
```

포트를 바꾸려면:

```powershell
python -m scholarcheck.web --port 8770
```

## 출력 위치

CLI의 기본 저장 위치는 `outputs/`입니다. CSV 저장 시 국내 DB 직접 확인 링크는 별도 `_domestic_links.csv` 파일로 저장됩니다. 검색 조건 완화 제안이 있으면 `_relaxation_suggestions.txt` 파일도 함께 저장됩니다.

## 국내 DB 주의

국내 논문 전용 DB(RISS/KCI/DBpia/KISS/e-Article)는 자동 크롤링하지 않습니다. ScholarCheck는 검색어를 URL 인코딩한 직접 확인 링크만 생성하며, 이 링크들은 자동 검증 논문 목록에 섞지 않습니다.

국내 DB 링크의 다운로드 가능 여부는 항상 `확인 불가 / 기관접속 필요 가능성 있음`으로 표시합니다. 사용자는 각 DB에서 논문 존재 여부, 서지정보, 원문 접근 권한을 직접 확인해야 합니다.
