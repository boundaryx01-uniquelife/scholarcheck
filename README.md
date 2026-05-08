# ScholarCheck / 논문나침반

논문 자료 검색, 수집, 검증을 돕는 MVP입니다.

핵심 원칙은 할루시네이션 금지입니다.

- 외부 API에서 확인된 메타데이터만 자동 검증 논문 목록에 표시합니다.
- 없는 제목, 저자, DOI, 학술지, 링크를 생성하지 않습니다.
- 누락된 값은 `UNKNOWN` 또는 확인 불가로 남깁니다.
- 국내 DB는 자동 크롤링하지 않고 직접 확인용 검색 링크만 생성합니다.

## 중요한 한계

ScholarCheck는 논문 존재 여부를 최종 보증하지 않습니다. 이 도구는 Crossref, OpenAlex 등 API 응답 기준의 메타데이터 검증 도구입니다.

국내 DB는 직접 확인 링크만 제공합니다. 최종 인용 전에는 반드시 원문 페이지에서 제목, 저자, 학술지, 연도, DOI, 권호, 페이지를 다시 확인해야 합니다.

다운로드 가능 여부는 PDF URL 확인 여부 기준입니다. PDF URL이 없으면 다운로드 가능으로 표시하지 않으며, 기관 접속이나 별도 권한이 필요할 수 있습니다.

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
python -m scholarcheck "artificial intelligence education" --required "artificial intelligence, education" --helpful "teacher, curriculum" --exclude "patent, news" --limit 10 --format csv
```

Python이 PATH에 없다면 Codex 번들 Python으로 실행할 수 있습니다.

```powershell
C:\Users\user\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m scholarcheck "artificial intelligence education" --required "artificial intelligence, education" --helpful "teacher, curriculum" --exclude "patent, news"
```

## 샘플 출력

아래는 `artificial intelligence education` 검색의 출력 형태 예시입니다. 실제 결과는 API 응답 시점에 따라 달라질 수 있습니다.

```text
Topic: artificial intelligence education
Keywords: artificial, intelligence, education
Required: artificial intelligence, education
Helpful: teacher, curriculum
Excluded: patent, news

# | Title                                      | Authors                  | Year | DOI                         | PDF | Cites | Classic | Score | Why
- | ------------------------------------------ | ------------------------ | ---- | --------------------------- | --- | ----- | ------- | ----- | --------------------------------------
1 | Teaching Machine Learning in K-12 Class... | Matti Tedre; Tapani...   | 2021 | 10.1109/access.2021.3097962 | Y   | 237   | N       | 99.87 | required title hit; DOI verified
2 | Artificial Intelligence Education Progr... | Rebecca Charow; ...      | 2021 | 10.2196/31043               | Y   | 229   | N       | 96.62 | required title hit; direct PDF available

국내 DB 직접 확인 필요
RISS / KCI / DBpia / KISS / e-Article 검색 링크가 별도 표시됩니다.
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

## 테스트

```powershell
python -m pytest
```
