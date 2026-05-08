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

국내 논문 전용 API(RISS/KCI/DBpia/KISS 등)는 인증키나 기관 권한이 필요한 경우가 많아 MVP에는 아직 직접 연동하지 않았습니다. 현재는 메타데이터의 출판사, 기관, 링크, 제목 정보를 바탕으로 국내/해외를 보수적으로 구분합니다.
