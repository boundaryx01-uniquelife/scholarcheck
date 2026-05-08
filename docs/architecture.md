# ScholarCheck Architecture

ScholarCheck는 외부 논문 API 응답을 수집하고, 메타데이터 검증 보조 자료를 CLI와 웹 UI로 제공하는 로컬 MVP입니다.

핵심 원칙은 다음과 같습니다.

- 없는 논문, DOI, 저자, 학술지, 링크를 생성하지 않습니다.
- 누락값은 `UNKNOWN`으로 유지합니다.
- 국내 DB는 자동 크롤링하지 않고 직접 확인 링크와 수동 기록으로 분리합니다.
- 세션 원본 데이터는 프로젝트 출력 과정에서 수정하지 않습니다.

## High-Level Flow

```text
User Query
  -> Query Builder
  -> Crossref / OpenAlex Sources
  -> Metadata Normalization
  -> Exclusion Filter
  -> Scoring and Ranking
  -> Deduplication for search result display
  -> Domestic DB Link Generation
  -> CLI / Web UI / CSV / JSON
  -> Session Save
  -> Session Reports / Excel
  -> Project Grouping
  -> Project Reports / Excel
```

## 주요 모듈

| Module | Responsibility |
| --- | --- |
| `scholarcheck/models.py` | 핵심 데이터 모델과 `UNKNOWN` 상수 |
| `scholarcheck/pipeline.py` | 검색 흐름 조립, API 실패 처리, 부족 결과 완화 제안 |
| `scholarcheck/sources.py` | Crossref, OpenAlex 조회와 API 응답 변환 |
| `scholarcheck/scoring.py` | 필수/도움/제외 키워드, DOI, PDF, 최신성, 고전 후보 점수 |
| `scholarcheck/domestic.py` | RISS, KCI, DBpia, KISS, e-Article 직접 확인 링크 생성 |
| `scholarcheck/verification.py` | Crossref 기반 DOI 재검증 |
| `scholarcheck/checklist.py` | 결과별 인용 전 체크리스트 |
| `scholarcheck/manual_checks.py` | 국내 DB 수동 확인 기록, 내보내기, 백업 |
| `scholarcheck/sessions.py` | 검색 세션 저장, 목록, 불러오기 |
| `scholarcheck/reports.py` | 세션 단위 HTML 리포트 |
| `scholarcheck/excel_export.py` | 세션 단위 Excel 통합 파일 |
| `scholarcheck/citations.py` | 참고문헌 후보 생성 |
| `scholarcheck/matrix.py` | 선행연구 매트릭스 초안 |
| `scholarcheck/projects.py` | 연구 프로젝트 생성, 목록, 세션 연결 |
| `scholarcheck/project_exports.py` | 프로젝트 통합 데이터, HTML 리포트, Excel 파일 |
| `scholarcheck/web.py` | 로컬 웹 UI와 다운로드 라우트 |
| `scholarcheck/cli.py` | CLI 진입점 |

## 데이터 저장 위치

| Path | Purpose |
| --- | --- |
| `outputs/` | CLI CSV/JSON 출력물 |
| `data/sessions/` | 저장된 검색 세션 JSON |
| `data/projects/` | 연구 프로젝트 JSON |
| `data/domestic_manual_checks.json` | 국내 DB 수동 확인 기록 |
| `data/backups/` | 수동 확인 기록 백업 |

## 데이터 모델 경계

`PaperRecord`는 자동 검증 논문 목록의 기본 단위입니다. DOI, PDF URL, 저자, 학술지 등이 없으면 기본값 또는 `UNKNOWN`으로 유지합니다.

`DomesticSearchLink`는 국내 DB 직접 확인 링크입니다. 자동 검증된 논문으로 취급하지 않습니다.

`DomesticManualCheck`는 사용자가 국내 DB를 직접 확인하고 입력한 기록입니다. 자동 검증 결과가 아니며, 프로젝트와 세션 리포트에서도 별도 영역으로 표시합니다.

`ResearchProject`는 세션 ID만 참조합니다. 세션 내용을 복사하거나 수정하지 않습니다.

## 중복 처리

검색 결과 내부에서는 DOI와 제목/연도 기준으로 중복 제거를 수행합니다.

프로젝트 통합 출력에서는 여러 세션의 결과를 합칠 때 중복 논문을 삭제하지 않습니다. 대신 DOI 또는 제목/연도 기준으로 `duplicate_candidate`를 표시합니다.

이 차이는 의도적입니다. 검색 세션은 사용자가 바로 읽는 결과를 정리해야 하고, 프로젝트는 여러 검색 맥락을 보존해야 하기 때문입니다.

## 출력 구조

세션 Excel 시트:

- Summary
- Verified Papers
- Reference Candidates
- Literature Matrix
- Domestic DB Links
- Manual Domestic Checks
- Warnings

프로젝트 Excel 시트:

- Summary
- Sessions
- Integrated Papers
- Duplicate Candidates
- Manual Domestic Checks
- Missing Sessions
- Warnings

## 실패 처리

API 실패 시 ScholarCheck는 빈 결과와 경고를 반환합니다. 가짜 논문이나 임의 DOI를 만들지 않습니다.

검색 결과가 부족하면 완화 제안을 출력합니다. 이 제안은 검색 조건을 넓히기 위한 안내일 뿐이며, 논문 데이터가 아닙니다.

누락 세션은 프로젝트 출력에서 Missing Sessions로 표시합니다.

## 테스트 전략

테스트는 `tests/test_guardrails.py`에 집중되어 있으며, 현재 guardrail 중심입니다.

검증 범위:

- DOI 누락 시 임의 생성 금지
- PDF URL 누락 시 PDF 가능 표시 금지
- 제외 키워드 필터링
- DOI/제목 기반 중복 처리
- 국내 DB 링크와 자동 검증 목록 분리
- API 실패 시 가짜 결과 생성 금지
- 세션/프로젝트 원본 데이터 보존
- HTML/Excel 출력 구조와 경고 문구

실행:

```powershell
python -m pytest
```
