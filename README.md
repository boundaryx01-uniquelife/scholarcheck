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
- 검색 결과 상세 보기
- DOI 재검증
- 결과별 인용 전 체크리스트
- 국내 DB 수동 확인 기록

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

## 샘플 검색 시나리오

다음 5개 주제에 대한 실행 예시는 [docs/sample_search_scenarios.md](docs/sample_search_scenarios.md)에 정리되어 있습니다.

1. `artificial intelligence education`
2. `generative AI in elementary education`
3. `digital literacy teacher education`
4. `computational thinking primary school`
5. `AI literacy curriculum`

## DOI 재검증 상태값

ScholarCheck의 DOI 재검증은 `scholarcheck/verification.py`의 `verify_doi_with_crossref(paper)`가 반환하는 상태값을 사용합니다. 현재 실제 코드에서 사용하는 값은 다음과 같습니다.

| 상태값 | 의미 | 처리 원칙 |
| --- | --- | --- |
| `verified` | 현재 논문 DOI와 Crossref 조회 DOI가 일치함 | Crossref 메타데이터를 확인한 것으로 표시하되, 최종 인용 전 원문 페이지 대조는 필요 |
| `mismatch` | Crossref에서 DOI가 조회되었지만 현재 논문 DOI와 다름 | 현재 결과와 Crossref 결과가 다를 수 있으므로 원문 페이지와 DOI를 직접 확인 |
| `missing` | 현재 논문에 DOI가 없음 | DOI를 새로 만들지 않고 재검증을 수행하지 않음 |
| `not_found` | Crossref 응답에서 DOI 메타데이터 또는 DOI 값을 확인하지 못함 | DOI를 임의 생성하지 않고 확인 실패로 취급 |
| `error` | Crossref API 오류 또는 네트워크 문제로 확인 실패 | 검색 결과를 유지하되 DOI 재검증 결과는 실패로 표시 |

참고: `VERIFIED`, `PARTIAL_MATCH`, `MISMATCH`, `NO_DOI`, `CHECK_FAILED` 같은 대문자 상태명은 현재 코드의 반환값이 아닙니다. 사용자 화면과 저장 데이터에서는 위 소문자 상태값을 기준으로 해석합니다.

## 웹 UI 실행

```powershell
python -m scholarcheck.web
```

기본 주소는 다음과 같습니다.

```text
http://127.0.0.1:8765
```

웹 UI에서는 각 검색 결과의 `상세 보기` 링크를 통해 제목, 저자, 연도, DOI, 원문 URL, PDF URL, 오픈액세스 여부, 인용 수, 초록, 점수, notes, classic 후보 여부를 확인할 수 있습니다. 상세 화면의 `DOI 재검증`은 현재 DOI가 있을 때만 Crossref에서 다시 확인하며, DOI가 없으면 새 DOI를 만들지 않습니다.

국내 DB 영역에는 수동 확인 기록 폼이 있습니다. 이 기록은 자동 검증 논문 목록에 섞이지 않고 `data/domestic_manual_checks.json`에 별도로 저장됩니다.

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
