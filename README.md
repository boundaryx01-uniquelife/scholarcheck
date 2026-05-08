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
- 검색 세션 저장/불러오기
- 교수님 검토용 HTML 리포트 생성
- 참고문헌 후보안 생성
- 선행연구 매트릭스 초안 생성
- 저장 세션 기반 Excel 통합 파일 생성
- 여러 검색 세션을 연구 프로젝트로 묶어 관리

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

## 누락값 표시 규칙

ScholarCheck는 확인되지 않은 값을 임의로 채우지 않습니다. 누락값은 출력 위치에 따라 다음처럼 표시합니다.

| 위치 | 표시값 |
| --- | --- |
| 내부 데이터 | `UNKNOWN` |
| CSV/JSON 출력 | `UNKNOWN` |
| 웹 사용자 화면 | 확인 불가 |

PDF URL을 자동 확인하지 못한 경우 웹 화면에서는 `확인 불가 / 기관접속 필요 가능성 있음`으로 표시하며, CSV/JSON에서는 원본 필드의 `UNKNOWN` 값을 유지합니다.

## 교수님용 사용 안내

ScholarCheck는 선행연구 후보를 빠르게 좁히는 보조 도구입니다. 논문 존재 여부, DOI의 최종 정확성, 원문 접근 가능성을 최종 보증하지 않습니다.

검색 결과를 실제 논문, 연구계획서, 강의자료에 인용하기 전에는 다음을 반드시 확인해 주세요.

- 원문 페이지에서 제목, 저자, 학술지/학회/기관, 출판연도, DOI, 권호, 페이지를 대조합니다.
- DOI 재검증 결과가 `verified`여도 최종 인용 전 원문 페이지 확인은 필요합니다.
- PDF 다운로드 가능 여부는 PDF URL 확인 여부 기준이며, 기관 접속이나 별도 권한이 필요할 수 있습니다.
- `UNKNOWN` 또는 `확인 불가`는 확인되지 않은 값을 임의로 채우지 않았다는 의미입니다.
- 국내 DB 링크는 자동 검증 결과가 아니며, RISS/KCI/DBpia/KISS/e-Article에서 직접 확인해야 합니다.

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

수동 확인 기록은 웹 UI에서 별도로 내보낼 수 있습니다.

- `수동 기록 CSV 내보내기`: 저장된 국내 DB 수동 확인 기록을 CSV로 다운로드합니다.
- `수동 기록 JSON 내보내기`: 저장된 국내 DB 수동 확인 기록을 JSON으로 다운로드합니다.
- `수동 기록 백업 파일 받기`: `data/backups/`에 시점별 JSON 백업을 만들고 같은 파일을 다운로드합니다.

백업과 내보내기는 자동 검증 논문 목록을 만들지 않습니다. 사용자가 직접 확인해 저장한 국내 DB 수동 기록만 대상으로 합니다.

## 검색 세션과 HTML 리포트

웹 UI에서 검색 결과를 확인한 뒤 `검색 세션 저장`을 누르면 현재 검색 조건, 자동 검증 논문 목록, 국내 DB 직접 확인 링크, 경고, 검색 조건 완화 제안이 `data/sessions/`에 JSON으로 저장됩니다.

저장된 세션은 `저장 세션 보기`에서 다시 불러올 수 있습니다. 세션을 불러올 때는 저장된 스냅샷을 표시하므로, API를 다시 호출해 다른 결과를 섞지 않습니다.

각 세션에서는 `교수님 검토용 HTML 리포트`를 생성할 수 있습니다. 리포트에는 다음 내용이 포함됩니다.

- 검색 조건
- 자동 검증된 해외 API 논문 목록
- 국내 DB 직접 확인 링크 영역
- 국내 DB 수동 확인 기록
- API 경고와 검색 조건 완화 제안
- 최종 인용 전 원문 확인 필요 안내

HTML 리포트도 논문 존재 여부를 최종 보증하지 않습니다. `UNKNOWN` 또는 `확인 불가` 값은 임의로 보완하지 않고 그대로 표시합니다.

## 참고문헌 후보안

검색 결과 화면 또는 저장된 세션 화면에서 `참고문헌 후보 보기`를 누르면 자동 검증 논문 목록을 바탕으로 참고문헌 후보안을 생성합니다.

참고문헌 후보안은 최종 확정 인용이 아닙니다.

- 저자, 연도, 학술지, DOI, 원문 URL이 없으면 임의로 보완하지 않고 `UNKNOWN` 또는 확인 필요 경고를 남깁니다.
- DOI가 있으면 DOI 링크를 후보안에 포함합니다.
- DOI가 없고 원문 URL이 있으면 원문 URL을 후보안에 포함합니다.
- DOI와 원문 URL이 모두 없으면 둘 다 만들지 않습니다.
- 국내 DB 수동 기록은 자동 검증 논문 목록과 분리되며 참고문헌 후보로 자동 변환하지 않습니다.

최종 제출 전에는 반드시 원문 페이지에서 서지정보를 직접 대조해야 합니다.

## 선행연구 매트릭스 초안

검색 결과 화면 또는 저장된 세션 화면에서 `선행연구 매트릭스`를 누르면 교수님이 선행연구 검토표로 활용할 수 있는 초안 표를 생성합니다.

매트릭스는 논문 내용을 임의로 요약하지 않습니다.

- 제목, 저자, 연도, 학술지/기관, DOI, 원문 URL은 API 메타데이터 기준으로 표시합니다.
- 연구목적, 연구방법, 연구대상, 주요결과는 자동 확정하지 않고 `[확인 필요]`로 표시합니다.
- 관련성 메모는 자동 점수/랭킹 notes가 있을 때만 보조 정보로 표시합니다.
- 사용자가 직접 보완할 수 있도록 `사용자 메모` 칸을 둡니다.
- 최종 논문 작성 전에는 원문을 직접 확인해야 합니다.

## Excel 통합 파일

저장된 세션 화면 또는 세션 목록에서 `Excel 통합 파일`을 누르면 교수님 검토용 `.xlsx` 파일을 다운로드할 수 있습니다.

Excel 파일은 저장된 세션 스냅샷을 기준으로 생성되며, API를 다시 호출해 결과를 바꾸지 않습니다. 포함 시트는 다음과 같습니다.

- `Summary`: 검색 조건, 세션 ID, 저장 시각, 검토 안내
- `Verified Papers`: 자동 검증 논문 목록
- `Reference Candidates`: 참고문헌 후보안
- `Literature Matrix`: 선행연구 매트릭스 초안
- `Domestic DB Links`: 국내 DB 직접 확인 링크
- `Manual Domestic Checks`: 국내 DB 수동 확인 기록
- `Warnings`: API 경고와 검색 조건 완화 제안

참고문헌 후보는 확정본이 아니며, 선행연구 매트릭스의 연구목적/연구방법/연구대상/주요결과는 자동 추정하지 않고 `[확인 필요]`로 남깁니다. 국내 DB 수동 기록은 자동 검증 논문 목록과 별도 시트로 분리됩니다.

Excel 파일은 첫 행 고정, 자동 필터, 기본 열 너비 조정, 긴 텍스트 줄바꿈을 적용합니다. `Warnings` 시트에는 최종 인용 전 원문 확인, 참고문헌 후보/매트릭스의 한계, 국내 DB 비크롤링 원칙, PDF 가능 여부 기준을 별도 안내로 포함합니다.

## 연구 프로젝트 관리

`저장 세션 보기`에서 세션을 연구 프로젝트에 추가하거나, `프로젝트 보기`에서 새 프로젝트를 만들 수 있습니다.

프로젝트 파일은 `data/projects/`에 저장되며 저장된 검색 세션 ID만 참조합니다. 세션 원본 JSON을 임의로 수정하지 않고, 국내 DB 수동 기록을 자동 검증 논문 목록에 합치지 않습니다.

프로젝트 화면에서는 연결된 세션, 자동 검증 논문 수, 국내 DB 직접 확인 링크 수를 확인할 수 있습니다. 프로젝트별 통합 HTML/Excel 출력은 이후 단계에서 이 프로젝트 참조 구조를 기반으로 확장합니다.

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
