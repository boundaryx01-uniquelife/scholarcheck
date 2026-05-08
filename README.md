# ScholarCheck / 논문나침반

논문 자료 검색, 수집, 검증을 돕는 MVP CLI입니다.

이 MVP의 원칙은 간단합니다.

- 외부 API에서 확인된 메타데이터만 출력합니다.
- 없는 제목, 저자, DOI, 학술지, 링크를 생성하지 않습니다.
- 누락된 값은 `UNKNOWN` 또는 빈 값으로 남깁니다.
- 검색 결과마다 출처 API와 검증 상태를 함께 표시합니다.

## 현재 지원 범위

- 해외 논문 API 조회: Crossref, OpenAlex
- DOI 및 메타데이터 확인
- PDF 다운로드 가능 여부 확인
- DOI/제목 기반 중복 제거
- 관련성, 최신성, 활용 가능성 점수 계산
- 표 출력
- CSV 또는 JSON 저장
- 국내 DB 직접 확인용 검색 링크 생성: RISS, KCI, DBpia, KISS, e-Article

## 실행

```powershell
python -m scholarcheck "3D printed footwear lattice midsole" --limit 10 --format csv
```

Python이 PATH에 없다면 Codex 번들 Python으로 실행할 수 있습니다.

```powershell
C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m scholarcheck "3D printed footwear lattice midsole"
```

## 출력 위치

기본 저장 위치는 `outputs/`입니다.

## 주의

국내 논문 전용 DB(RISS/KCI/DBpia/KISS/e-Article)는 자동 크롤링하지 않습니다. ScholarCheck는 검색어를 URL 인코딩한 직접 확인 링크만 생성하며, 이 링크들은 검증된 논문 목록에 섞지 않습니다.

국내 DB 링크의 다운로드 가능 여부는 항상 `확인 불가 / 기관접속 필요 가능성 있음`으로 표시합니다. 사용자는 각 DB에서 논문 존재 여부, 서지정보, 원문 접근 권한을 직접 확인해야 합니다.
