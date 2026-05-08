# ScholarCheck Development History

이 문서는 ScholarCheck MVP가 어떤 순서로 확장되었는지 기록합니다. 릴리즈 검토나 회귀 테스트 범위를 정할 때 참고합니다.

## MVP 1: 논문 검색 MVP

초기 목표는 연구 주제를 입력하면 해외 논문 API에서 결과를 가져오고, 표 형태로 확인할 수 있는 최소 흐름을 만드는 것이었습니다.

주요 기능:

- Crossref, OpenAlex 기반 해외 논문 검색
- DOI와 기본 메타데이터 수집
- PDF URL 확인
- DOI/제목 기반 중복 제거
- CLI 표 출력
- CSV/JSON 저장

핵심 원칙:

- 존재하지 않는 논문 생성 금지
- 존재하지 않는 DOI 생성 금지
- API 실패 시 가짜 결과 생성 금지

## MVP 2: 검색 품질과 국내 DB 보조

단순 점수 기반 정렬을 개선하고 국내 DB 직접 확인 링크를 추가했습니다.

주요 기능:

- 필수 키워드 제목 포함 시 높은 가중치
- 필수 키워드 초록 포함 시 중간 가중치
- 도움 키워드 보조 점수
- 제외 키워드 필터
- DOI, PDF, 최근 5년 자료 우선
- 인용 수가 높은 고전 논문 별도 표시
- 검색 결과 부족 시 조건 완화 제안
- RISS, KCI, DBpia, KISS, e-Article 직접 확인 링크

## MVP 3: 상세 보기와 재검증

교수님이 논문을 실제로 검토할 수 있도록 개별 결과의 상세 정보를 확장했습니다.

주요 기능:

- 웹 UI 결과 상세 보기
- DOI 재검증
- 인용 전 체크리스트
- 국내 DB 수동 확인 기록
- 자동 검증 논문 목록과 수동 기록 분리

## MVP 3.5: 실사용 안정화

기능 확장보다 문서화와 표시 일관성을 정리했습니다.

주요 기능:

- 샘플 검색 시나리오 문서화
- DOI 재검증 상태값 문서화
- `UNKNOWN` 표시 규칙 통일
- 교수님용 안내 문구 추가
- 국내 DB 수동 기록 CSV/JSON 내보내기
- 국내 DB 수동 기록 백업

## MVP 4: 검색 세션과 HTML 리포트

검색 결과를 저장하고 다시 열어볼 수 있는 단위를 만들었습니다.

주요 기능:

- `data/sessions/` 기반 검색 세션 저장
- 저장 세션 목록 보기
- 저장 세션 불러오기
- 세션 기반 교수님 검토용 HTML 리포트
- 자동 검증 논문, 국내 DB 링크, 국내 수동 기록 분리 표시

## MVP 5: 참고문헌 후보

저장된 검색 결과를 바탕으로 참고문헌 후보안을 생성했습니다.

주요 기능:

- `scholarcheck/citations.py`
- 참고문헌 후보 화면
- 세션과 리포트의 Reference Candidates 섹션
- DOI가 있으면 DOI 링크 포함
- DOI가 없고 원문 URL이 있으면 원문 URL 포함
- 최종 확정 인용 아님 경고 유지

## MVP 5.5: 선행연구 매트릭스

교수님이 선행연구 검토표 초안으로 활용할 수 있는 매트릭스를 추가했습니다.

주요 기능:

- `scholarcheck/matrix.py`
- Literature Review Matrix Draft 화면
- 연구목적, 연구방법, 연구대상, 주요결과는 자동 추정하지 않음
- 확인되지 않은 값은 `[확인 필요]`로 표시
- 사용자 보완용 메모 칸 제공

## MVP 6: Excel 통합 파일

세션 기반 논문 작성 준비 자료를 Excel로 묶었습니다.

주요 기능:

- `scholarcheck/excel_export.py`
- 세션 기반 `.xlsx` 생성
- Summary, Verified Papers, Reference Candidates, Literature Matrix, Domestic DB Links, Manual Domestic Checks, Warnings 시트
- 참고문헌 후보와 선행연구 매트릭스를 분리된 시트로 제공

## MVP 6.5: Excel 안정화

Excel 파일을 실사용 가능한 수준으로 다듬었습니다.

주요 기능:

- 헤더 굵게 표시
- 첫 행 고정
- 자동 필터
- 열 너비 자동 조정
- 긴 텍스트 줄바꿈
- Warnings 시트 보강

## MVP 7: 연구 프로젝트

여러 검색 세션을 하나의 연구 프로젝트로 묶을 수 있게 했습니다.

주요 기능:

- `data/projects/` 기반 연구 프로젝트 JSON
- 프로젝트 생성, 목록, 상세 보기
- 저장 세션을 프로젝트에 연결
- 프로젝트는 세션 원본을 수정하지 않고 세션 ID만 참조
- 누락 세션 참조가 있어도 가짜 세션 생성 금지

## MVP 7.5: 프로젝트 통합 출력

프로젝트에 연결된 여러 검색 세션을 통합하여 프로젝트 단위 출력물을 생성했습니다.

주요 기능:

- `scholarcheck/project_exports.py`
- 프로젝트 통합 HTML 리포트
- 프로젝트 통합 Excel 파일
- 통합 논문 목록
- 중복 논문은 삭제하지 않고 `duplicate_candidate`로 표시
- 누락 세션은 Missing Sessions로 표시
- 국내 DB 수동 기록은 자동 검증 논문 목록과 분리

## MVP 8: 릴리즈 준비 문서화

사용자가 ScholarCheck를 이해하고 실행하고 검증할 수 있도록 문서 구조를 정리합니다.

문서:

- `docs/user_guide.md`
- `docs/architecture.md`
- `docs/development_history.md`
- `docs/release_checklist.md`
