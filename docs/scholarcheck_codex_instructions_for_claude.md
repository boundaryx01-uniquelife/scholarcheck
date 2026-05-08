# ScholarCheck / 논문나침반 Codex 작업지시서 모음

이 문서는 ScholarCheck / 논문나침반 프로젝트를 Codex 또는 Claude에게 공유하기 위한 통합 Markdown 지시서입니다.

프로젝트의 핵심 원칙은 **할루시네이션 금지**입니다.

- 존재하지 않는 논문, 저자, DOI, 학술지, 링크를 생성하지 않습니다.
- 외부 API에서 확인된 메타데이터만 자동 검증 논문 목록에 표시합니다.
- 누락된 값은 `UNKNOWN`, `확인 불가`, `null` 등으로 남깁니다.
- 국내 DB는 자동 크롤링하지 않고 직접 확인용 검색 링크 또는 사용자 수동 기록으로만 다룹니다.
- 최종 인용 전에는 반드시 원문 페이지에서 제목, 저자, 연도, DOI, 학술지명, PDF 접근 가능 여부를 다시 확인해야 합니다.

---

# 0. 프로젝트 개요

## 프로젝트명

ScholarCheck / 논문나침반

## 목표

대학교 교수님들이 논문 작성, 연구계획서 작성, 선행연구 검토를 할 때 사용할 수 있는 **논문 자료 검색 및 검증 도구**를 제작한다.

이 도구는 단순히 논문 제목을 나열하는 것이 아니라 다음 항목을 가능한 범위에서 확인한다.

- 논문 제목
- 저자
- 출판연도
- 학술지/학회/기관
- DOI
- 원문 페이지 링크
- PDF 다운로드 가능 여부
- 국내/해외 자료 구분
- 관련성 점수
- 최신성
- 활용 가능성
- 주의사항

가장 중요한 원칙은 **할루시네이션 금지**이다.

존재하지 않는 논문, 저자, DOI, 학술지, 링크를 절대 생성하면 안 된다.

---

# 1. MVP 1 작업지시서

## 목표

사용자가 연구 주제를 입력하면 다음 흐름으로 작동한다.

```text
사용자 입력
↓
검색 조건 입력
↓
키워드 분류
↓
해외 논문 검색 API 조회
↓
DOI 및 메타데이터 확인
↓
PDF 다운로드 가능 여부 확인
↓
중복 제거
↓
관련성/최신성 기준 정렬
↓
결과를 표 형태로 출력
↓
CSV 또는 JSON 저장
```

---

## 1-1. 검색 요청 입력 폼

CLI 또는 간단한 웹 화면으로 시작해도 된다.

입력 항목은 다음과 같다.

```text
1. 연구 주제
2. 연구 대상
3. 반드시 포함할 키워드
4. 도움이 되는 확장 키워드
5. 제외할 키워드
6. 국내/해외 검색 범위
7. 연도 범위
8. 자료 유형
   - 학술논문
   - 학위논문
   - 보고서
   - 학술대회 자료
9. PDF 다운로드 가능한 자료만 볼 것인지
10. 결과 개수
```

입력이 부족하면 검색을 바로 진행하지 말고, 부족한 항목을 안내하는 메시지를 출력한다.

예:

```text
검색 조건이 부족합니다.
정확한 검색을 위해 연구 대상, 연도 범위, 제외 키워드를 추가로 입력해 주세요.
```

---

## 1-2. 키워드 분류 기능

사용자의 입력 키워드를 다음 구조로 정리한다.

```json
{
  "required_keywords": [],
  "optional_keywords": [],
  "english_keywords": [],
  "exclude_keywords": []
}
```

예시:

```text
연구 주제: 초등학교 생성형 AI 교육
반드시 포함: 초등학교, 생성형 AI, ChatGPT
도움 키워드: AI 리터러시, 디지털 리터러시, 프롬프트, 수업 설계
영문 키워드: elementary education, generative AI, ChatGPT, AI literacy
제외 키워드: higher education, medical AI, corporate training
```

검색식은 국내용과 해외용을 나눠 생성한다.

해외 검색식 예:

```text
("generative AI" OR ChatGPT) AND ("elementary education" OR "primary school") AND ("AI literacy" OR "digital literacy")
```

국내 검색식 예:

```text
("생성형 AI" OR "ChatGPT") AND ("초등학교" OR "초등학생") AND ("AI 리터러시" OR "디지털 리터러시")
```

---

## 1-3. 사용할 외부 API

MVP에서는 해외 논문 검색부터 구현한다.

### 필수 API

#### 1. OpenAlex

용도:

- 논문 검색
- 제목, 저자, 연도, 출처, 인용 수 확인
- 오픈액세스 여부 확인

공식 문서:

```text
https://docs.openalex.org/
```

#### 2. Crossref

용도:

- DOI 검증
- 출판사/저널 메타데이터 확인

공식 문서:

```text
https://www.crossref.org/documentation/retrieve-metadata/rest-api/
```

#### 3. Semantic Scholar

용도:

- 관련 논문 검색
- 초록, 인용 수, PDF 링크 확인

공식 문서:

```text
https://api.semanticscholar.org/api-docs/
```

#### 4. Unpaywall

용도:

- 합법적인 오픈액세스 PDF 확인
- PDF 직접 다운로드 가능 여부 확인

공식 문서:

```text
https://unpaywall.org/products/api
```

주의:

Unpaywall API는 이메일 파라미터가 필요할 수 있으므로 `.env`에 이메일을 저장한다.

```env
UNPAYWALL_EMAIL=your-email@example.com
```

---

## 1-4. 결과 데이터 구조

논문 검색 결과는 다음 구조로 저장한다.

```ts
type PaperResult = {
  title: string;
  authors: string[];
  year: number | null;
  source: string | null;
  journal: string | null;
  doi: string | null;
  url: string | null;
  pdf_url: string | null;
  download_status:
    | "PDF_DIRECT_AVAILABLE"
    | "LANDING_PAGE_AVAILABLE"
    | "PAID_OR_INSTITUTION_REQUIRED"
    | "NOT_FOUND"
    | "NEEDS_VERIFICATION";
  is_open_access: boolean | null;
  citation_count: number | null;
  abstract: string | null;
  source_type: "international" | "domestic" | "unknown";
  relevance_score: number;
  freshness_score: number;
  trust_score: number;
  final_score: number;
  notes: string[];
};
```

---

## 1-5. 다운로드 가능 여부 분류

반드시 아래 5단계로 표시한다.

```text
PDF_DIRECT_AVAILABLE
- PDF 직접 다운로드 가능

LANDING_PAGE_AVAILABLE
- 원문 페이지는 확인되지만 PDF 직접 링크는 없음

PAID_OR_INSTITUTION_REQUIRED
- 유료 또는 기관접속 필요

NOT_FOUND
- 원문 확인 불가

NEEDS_VERIFICATION
- 출처 또는 링크 추가 검증 필요
```

사용자 화면에서는 한국어로 표시한다.

```text
✅ PDF 직접 가능
🟡 원문 페이지 가능
🔒 유료 또는 기관접속 필요
❌ 확인 불가
⚠️ 추가 검증 필요
```

---

## 1-6. 정렬 기준

검색 결과는 다음 점수를 계산해서 정렬한다.

### 관련성 점수 relevance_score

필수 키워드가 제목, 초록, 키워드에 얼마나 포함되는지 계산한다.

우선순위:

```text
제목 포함 > 초록 포함 > 키워드 포함 > 출처명 포함
```

### 최신성 점수 freshness_score

최근 자료일수록 높은 점수.

예:

```text
최근 3년: 100점
최근 5년: 80점
최근 10년: 60점
10년 이상: 40점
```

### 신뢰도 점수 trust_score

```text
DOI 있음: +20
학술지명 있음: +20
Crossref 검증 성공: +20
OpenAlex/Semantic Scholar 양쪽 확인: +20
PDF 링크 확인: +20
```

### 최종 점수 final_score

```text
final_score =
  relevance_score * 0.45 +
  freshness_score * 0.25 +
  trust_score * 0.20 +
  download_score * 0.10
```

---

## 1-7. 중복 제거 기준

다음 순서로 중복을 제거한다.

```text
1. DOI가 같으면 같은 논문
2. DOI가 없으면 제목을 정규화해서 비교
3. 제목 유사도가 매우 높고 연도가 같으면 중복으로 판단
```

제목 정규화 규칙:

```text
- 소문자 변환
- 특수문자 제거
- 공백 정리
- 관사 제거 가능
```

---

## 1-8. 출력 형식

### 터미널 출력 예시

```text
검색 주제: 초등학교 생성형 AI 교육
검색 범위: 해외 논문
검색일: YYYY-MM-DD

[1] 논문 제목
저자: A, B, C
연도: 2024
출처: Journal of Educational Technology
DOI: 10.xxxx/xxxxx
원문: https://...
PDF: ✅ PDF 직접 가능
관련성: 92점
활용 가능성: 생성형 AI 수업 설계 이론 배경에 활용 가능
주의사항: 초등학생 대상 연구인지 초록 추가 확인 필요
```

### CSV 저장 컬럼

```text
rank,title,authors,year,source,journal,doi,url,pdf_url,download_status,is_open_access,citation_count,relevance_score,freshness_score,trust_score,final_score,notes
```

### JSON 저장

```text
results/search-results-YYYYMMDD-HHMM.json
```

### CSV 저장

```text
results/search-results-YYYYMMDD-HHMM.csv
```

---

## 1-9. 프로젝트 구조 제안

Python으로 시작한다.

```text
scholarcheck/
├─ README.md
├─ requirements.txt
├─ .env.example
├─ app/
│  ├─ main.py
│  ├─ config.py
│  ├─ models.py
│  ├─ keyword_builder.py
│  ├─ search/
│  │  ├─ openalex_client.py
│  │  ├─ crossref_client.py
│  │  ├─ semantic_scholar_client.py
│  │  └─ unpaywall_client.py
│  ├─ scoring.py
│  ├─ dedup.py
│  ├─ exporter.py
│  └─ utils.py
├─ data/
│  └─ sample_queries.json
├─ results/
└─ tests/
   ├─ test_scoring.py
   ├─ test_dedup.py
   └─ test_keyword_builder.py
```

---

## 1-10. 환경 변수

`.env.example` 파일 생성.

```env
UNPAYWALL_EMAIL=your-email@example.com
SEMANTIC_SCHOLAR_API_KEY=
REQUEST_TIMEOUT=20
MAX_RESULTS=30
```

Semantic Scholar API Key는 없어도 작동 가능하게 만들되, 있으면 헤더에 포함하도록 한다.

---

## 1-11. requirements.txt

우선 아래 정도로 시작한다.

```txt
requests
python-dotenv
pydantic
pandas
rapidfuzz
tabulate
```

---

## 1-12. 기본 실행 방식

```bash
python -m app.main
```

실행하면 CLI에서 입력을 받는다.

예:

```text
연구 주제를 입력하세요:
> 초등학교 생성형 AI 교육

반드시 포함할 키워드를 쉼표로 입력하세요:
> 초등학교, 생성형 AI, ChatGPT

도움이 되는 키워드를 입력하세요:
> AI 리터러시, 디지털 리터러시, 수업 설계

제외 키워드를 입력하세요:
> 대학생, 의학, 기업교육

검색 연도 시작:
> 2020

검색 연도 끝:
> 2026

결과 개수:
> 20
```

---

## 1-13. 중요한 개발 원칙

### 절대 금지

- 존재하지 않는 논문 생성 금지
- 임의 DOI 생성 금지
- 임의 저널명 생성 금지
- 확인되지 않은 PDF 링크 생성 금지
- API 실패 시 가짜 결과 생성 금지

### API 실패 시 처리

```text
OpenAlex 검색 실패: 오류 메시지 출력
Crossref 검증 실패: DOI 검증 실패로 표시
Unpaywall 실패: 다운로드 가능 여부 확인 불가로 표시
Semantic Scholar 실패: 해당 출처 결과 제외 또는 검증 필요로 표시
```

### 결과 없음 처리

검색 결과가 부족하면 다음 메시지를 출력한다.

```text
조건에 맞는 자료가 부족합니다.
다음 중 하나를 조정해 보세요.

1. 연도 범위 확대
2. 필수 키워드 축소
3. 영문 키워드 추가
4. 제외 키워드 완화
5. 보고서/학위논문 포함
```

---

## 1-14. README에 반드시 포함할 내용

README에는 다음을 작성한다.

```text
1. 프로젝트 목적
2. 할루시네이션 방지 원칙
3. 사용 API
4. 설치 방법
5. 실행 방법
6. 검색 입력 예시
7. 결과 파일 설명
8. 다운로드 가능 여부 분류 기준
9. 한계
10. 향후 개발 계획
```

한계에는 반드시 아래 내용을 포함한다.

```text
이 도구는 API 기반 검색 결과를 정리하는 보조 도구이다.
논문 존재 여부, DOI, PDF 링크는 API 응답을 기준으로 표시한다.
일부 유료 DB, 기관접속 논문, 국내 학술 DB 자료는 자동 확인이 제한될 수 있다.
최종 인용 전에는 사용자가 원문 페이지에서 한 번 더 확인해야 한다.
```

---

## 1-15. 1차 구현 완료 조건

다음이 되면 1차 완료로 본다.

- CLI에서 검색 조건 입력 가능
- OpenAlex 검색 가능
- Crossref DOI 검증 가능
- Unpaywall PDF 확인 가능
- 중복 제거 가능
- 관련성/최신성/신뢰도 점수 계산 가능
- 결과를 터미널 표로 출력 가능
- CSV 저장 가능
- JSON 저장 가능
- 결과 없음/오류 상황에서 가짜 결과를 만들지 않음
- README 작성 완료

---

## 1-16. 2차 개발 후보

1차 완료 후 다음을 검토한다.

```text
1. Streamlit 또는 Next.js 웹 화면 제작
2. 국내 DB 검색 보조 기능 추가
3. RISS/KCI 검색 링크 생성 기능
4. APA/KCI 인용 양식 자동 생성
5. 선행연구 매트릭스 자동 생성
6. 논문별 요약 카드 생성
7. 검색 히스토리 저장
8. 연구 주제별 프로젝트 저장
9. Excel 출력
10. Word 보고서 출력
```

---

# 2. MVP 2 작업지시서

## 목표

MVP 1단계의 논문 검색 도구를 개선한다.

2단계 범위는 다음 3가지다.

1. 검색 정확도 개선
2. 국내 논문 DB 검색 링크 생성
3. Streamlit 기반 간단한 웹 화면 추가

---

## 2-1. 검색 정확도 개선

다음 기준으로 `scoring.py`를 개선한다.

- 필수 키워드가 제목에 포함되면 높은 점수
- 필수 키워드가 초록에 포함되면 중간 점수
- 도움 키워드는 보조 점수
- 제외 키워드가 제목/초록에 있으면 결과 제외
- DOI가 있으면 가산점
- PDF 직접 가능하면 가산점
- 최근 5년 자료 가산점
- 10년 이상 오래된 자료는 감점하되, 인용 수가 높은 자료는 `classic_candidate`로 표시

결과가 부족할 경우 가짜 결과를 만들지 말고 검색 조건 완화 제안을 출력한다.

---

## 2-2. 국내 논문 DB 검색 링크 생성

국내 DB는 자동 크롤링하지 않는다.

대신 국내 검색용 키워드를 바탕으로 검색 링크를 생성한다.

대상:

- RISS
- KCI
- DBpia
- KISS
- e-Article

출력 영역 이름:

```text
국내 논문 DB 직접 검색 링크
```

주의:

- 국내 DB 결과를 자동 검증된 논문처럼 표시하지 않는다.
- 다운로드 가능 여부는 “직접 확인 필요”로 표시한다.
- 유료 또는 기관접속 가능성이 있음을 안내한다.

---

## 2-3. Streamlit 웹 화면 추가

`streamlit_app.py`를 생성한다.

화면 구성:

- 연구 주제 입력
- 필수 키워드 입력
- 도움 키워드 입력
- 제외 키워드 입력
- 검색 연도 범위
- 결과 개수
- PDF 가능 자료만 보기
- 검색 실행 버튼
- 키워드 분류 미리보기
- 검색 결과 표
- CSV 다운로드
- JSON 다운로드
- 국내 DB 검색 링크 영역

CLI 기능은 유지한다.

---

## 2-4. 완료 후 보고

작업 완료 후 다음을 알려준다.

```text
1. 수정한 파일 목록
2. 새로 추가한 파일 목록
3. 실행 방법
4. Streamlit 실행 명령
5. 현재 구현된 기능
6. 아직 제한되는 기능
7. 테스트 방법
```

---

# 3. MVP 2.5 안정화 작업지시서

## 현재 기능

- Crossref, OpenAlex 기반 해외 논문 검색
- DOI 및 메타데이터 확인
- PDF 다운로드 가능 여부 확인
- DOI/제목 기반 중복 제거
- 필수/도움/제외 키워드 기반 정렬
- 인용 수가 높은 고전 논문 별도 표시
- 검색 결과 부족 시 검색 조건 완화 제안 출력
- CLI 표 출력
- 로컬 웹 UI
- CSV/JSON 저장
- 국내 DB 직접 확인용 검색 링크 생성

---

## 3-1. 검수 테스트 추가

다음 상황을 테스트하는 pytest를 작성한다.

1. DOI가 없는 논문은 DOI를 임의 생성하지 않고 UNKNOWN 또는 null로 남긴다.
2. PDF URL이 없는 논문은 PDF 직접 가능으로 표시하지 않는다.
3. 제외 키워드가 제목 또는 초록에 포함된 결과는 제외된다.
4. 동일 DOI 논문은 중복 제거된다.
5. DOI가 없더라도 제목이 거의 같고 연도가 같으면 중복 제거된다.
6. 국내 DB 링크는 자동 검증 논문 목록에 포함되지 않는다.
7. 검색 결과가 부족할 때 relaxation suggestion 파일이 생성된다.
8. API 실패 시 가짜 결과를 생성하지 않는다.

---

## 3-2. README 보강

README에 다음 내용을 추가한다.

- 이 도구는 논문 존재 여부를 최종 보증하지 않는다.
- API 응답 기준의 메타데이터 검증 도구이다.
- 국내 DB는 직접 확인 링크만 제공한다.
- 최종 인용 전 원문 페이지 확인이 필요하다.
- 다운로드 가능 여부는 PDF URL 확인 여부 기준이다.

---

## 3-3. 샘플 실행 결과 추가

README에 예시 명령과 출력 예시를 추가한다.

예시 주제:

```text
artificial intelligence education
```

필수 키워드:

```text
artificial intelligence, education
```

도움 키워드:

```text
teacher, curriculum
```

제외 키워드:

```text
patent, news
```

---

## 3-4. 웹 UI 안정화

웹 UI에서 다음을 확인한다.

- 검색 중 로딩 표시
- 결과 없음 안내
- 오류 발생 시 오류 메시지 표시
- CSV 다운로드 버튼
- JSON 다운로드 버튼
- 국내 DB 링크 영역 분리 표시

---

## 3-5. 완료 후 보고

완료 후 다음을 알려준다.

```text
1. 수정한 파일 목록
2. 추가한 테스트 목록
3. 실행 테스트 결과
4. 실패하거나 제한되는 기능
5. 다음 개선 제안
```

---

# 4. MVP 3 작업지시서

## 목표

검색 결과를 교수님이 논문 작성에 바로 활용할 수 있도록 다음 기능을 추가한다.

1. 검색 결과 상세 보기 화면
2. DOI 재검증 전용 단계
3. 결과별 “인용 전 체크리스트”
4. 국내 DB 수동 확인 기록 기능

중요 원칙은 계속 유지한다.

- 없는 논문 생성 금지
- 없는 DOI 생성 금지
- PDF 링크 과장 금지
- 국내 DB는 자동 검증 논문 목록과 분리
- 확인되지 않은 값은 UNKNOWN 또는 확인 불가로 유지

---

## 4-1. 검색 결과 상세 보기 화면 추가

웹 UI에서 각 논문 결과를 클릭하거나 “상세 보기” 버튼을 누르면 상세 정보를 볼 수 있게 한다.

상세 보기에는 다음 항목을 표시한다.

- 제목
- 저자
- 출판연도
- 출처
- 학술지
- DOI
- 원문 URL
- PDF URL
- 다운로드 상태
- 오픈액세스 여부
- 인용 수
- 초록
- 관련성 점수
- 최신성 점수
- 신뢰도 점수
- 최종 점수
- notes
- classic_candidate 여부

주의:

- 초록이 없으면 UNKNOWN 또는 확인 불가로 표시한다.
- DOI가 없으면 빈 DOI를 생성하지 않는다.
- PDF URL이 없으면 PDF 직접 가능으로 표시하지 않는다.

---

## 4-2. DOI 재검증 전용 단계 추가

논문 결과별로 DOI를 다시 검증하는 함수를 추가한다.

파일 제안:

```text
scholarcheck/verification.py
```

기능:

```text
verify_doi_with_crossref(paper)
```

동작:

1. paper.doi가 있으면 Crossref에서 DOI 조회
2. Crossref 응답이 있으면 다음 항목 비교
   - 제목 유사도
   - 출판연도
   - 저널명 또는 출처
3. 일치도가 높으면 doi_verification_status = VERIFIED
4. 일부만 맞으면 doi_verification_status = PARTIAL_MATCH
5. 불일치하면 doi_verification_status = MISMATCH
6. DOI가 없으면 doi_verification_status = NO_DOI
7. API 실패 시 doi_verification_status = CHECK_FAILED

새 필드 제안:

```python
doi_verification_status: str
doi_verification_notes: list[str]
```

상태값:

```text
VERIFIED
PARTIAL_MATCH
MISMATCH
NO_DOI
CHECK_FAILED
```

주의:

- Crossref 실패 시 가짜 검증 결과를 만들지 않는다.
- DOI가 없는 논문에 DOI를 추정해서 넣지 않는다.

---

## 4-3. 결과별 “인용 전 체크리스트” 생성

각 논문 결과마다 사용자가 최종 인용 전에 확인해야 할 항목을 생성한다.

예:

```text
인용 전 체크리스트

□ 원문 페이지에서 제목 확인
□ 저자명 확인
□ 출판연도 확인
□ DOI 확인
□ 학술지명 확인
□ PDF 원문 열람 가능 여부 확인
□ 초록과 연구 주제 관련성 확인
□ 국내 DB 자료의 경우 기관접속 여부 확인
```

구현 방식:

파일 제안:

```text
scholarcheck/checklist.py
```

함수:

```python
build_citation_checklist(paper) -> list[str]
```

조건부 항목:

- DOI가 UNKNOWN이면 “DOI 없음 또는 확인 필요” 항목 추가
- PDF URL이 없으면 “PDF 직접 다운로드 불가, 원문 페이지 확인 필요” 추가
- source가 UNKNOWN이면 “출처명 확인 필요” 추가
- abstract가 UNKNOWN이면 “초록 확인 필요” 추가
- 국내 DB 링크 자료는 “국내 DB에서 직접 서지정보 확인 필요” 추가

---

## 4-4. 국내 DB 수동 확인 기록 기능

국내 DB는 자동 크롤링하지 않는다.

대신 사용자가 RISS/KCI/DBpia/KISS/e-Article에서 직접 확인한 결과를 웹 UI에서 수동으로 기록할 수 있게 한다.

수동 기록 항목:

- DB 이름
- 검색 링크
- 확인 여부
- 논문 제목
- 저자
- 연도
- 출처
- 원문 접근 상태
- 메모

원문 접근 상태:

```text
PDF 직접 가능
원문 페이지 가능
유료 또는 기관접속 필요
확인 불가
```

저장 형식:

```text
outputs/domestic_manual_checks_YYYYMMDD_HHMM.csv
```

주의:

- 이 수동 기록은 자동 검증 논문 목록과 분리한다.
- 사용자가 입력한 값은 “사용자 수동 기록”으로 표시한다.
- 자동 검증 완료로 표시하지 않는다.

---

## 4-5. 출력 개선

CSV/JSON 출력에 다음 필드를 추가한다.

- doi_verification_status
- doi_verification_notes
- citation_checklist
- classic_candidate

단, 기존 출력이 깨지지 않게 하위 호환성을 유지한다.

---

## 4-6. 테스트 추가

다음 테스트를 추가한다.

1. DOI가 없는 논문은 verify_doi 단계에서 NO_DOI가 된다.
2. Crossref API 실패 시 CHECK_FAILED가 되고 가짜 검증 결과를 만들지 않는다.
3. DOI 제목이 불일치하면 MISMATCH가 된다.
4. DOI 제목이 유사하고 연도가 맞으면 VERIFIED 또는 PARTIAL_MATCH가 된다.
5. PDF URL 없는 논문은 체크리스트에 원문 페이지 확인 필요 항목이 들어간다.
6. UNKNOWN 필드가 있는 논문은 체크리스트에 확인 필요 항목이 들어간다.
7. 국내 DB 수동 기록은 자동 검증 논문 목록에 섞이지 않는다.
8. CSV/JSON 출력에 새 필드가 포함된다.

---

## 4-7. 웹 UI 개선

웹 UI에 다음을 추가한다.

1. 결과별 상세 보기 버튼
2. DOI 검증 상태 표시
3. 인용 전 체크리스트 표시
4. 국내 DB 수동 확인 기록 입력 영역
5. 수동 기록 CSV 저장 버튼

UI에서 강조할 문구:

```text
이 결과는 외부 API 메타데이터 기준입니다.
최종 인용 전 원문 페이지에서 반드시 확인하세요.
```

국내 DB 영역 문구:

```text
국내 DB 검색 링크는 직접 확인용입니다.
자동 검증 논문 목록에 포함되지 않습니다.
사용자가 직접 확인한 내용은 수동 기록으로만 저장됩니다.
```

---

## 4-8. 완료 후 보고

작업 완료 후 다음을 알려준다.

```text
1. 수정한 파일 목록
2. 새로 추가한 파일 목록
3. 추가한 테스트 목록
4. pytest 결과
5. 웹 UI 확인 결과
6. CSV/JSON 출력 변경 사항
7. 현재 제한 사항
8. 다음 개선 제안
```

---

# 5. MVP 3.5 안정화 작업지시서

## 목표

MVP 3.5는 기능 확장보다 실사용 안정화 단계이다.

교수님들이 실제로 사용할 수 있도록 다음을 점검하고 보강한다.

---

## 5-1. 샘플 검색 시나리오 추가

README 또는 docs에 샘플 검색 시나리오를 추가한다.

샘플 주제는 다음 5개이다.

```text
1. artificial intelligence education
2. generative AI in elementary education
3. digital literacy teacher education
4. computational thinking primary school
5. AI literacy curriculum
```

각 샘플에는 다음을 포함한다.

- CLI 실행 명령
- 필수 키워드
- 도움 키워드
- 제외 키워드
- 기대 확인 항목

---

## 5-2. DOI 재검증 상태값 문서화

README에 DOI 재검증 상태값 설명을 추가한다.

상태값은 현재 코드에서 실제 사용하는 값에 맞춰 정리해야 한다.

예상 상태값:

```text
VERIFIED
- Crossref 메타데이터와 제목/연도/출처가 대체로 일치

PARTIAL_MATCH
- DOI는 조회되지만 일부 메타데이터가 다름

MISMATCH
- DOI 조회 결과와 현재 논문 정보가 크게 다름

NO_DOI 또는 missing
- DOI가 없어 재검증하지 않음

CHECK_FAILED
- Crossref API 오류 또는 네트워크 문제로 확인 실패
```

주의:

- 프로젝트 내부 상태값이 실제로 `missing`이면 README와 UI 표시도 같은 표현을 사용하거나, 사용자 표시용으로 “DOI 없음”으로 변환한다.
- README에는 개발자용 상태값과 사용자 화면 표시값을 구분해서 설명한다.

---

## 5-3. UNKNOWN 표시 통일

웹 UI, CSV, JSON, README에서 누락값 표시 방식을 통일한다.

목표 규칙:

```text
내부 데이터: UNKNOWN
CSV/JSON 출력: UNKNOWN
사용자 화면: 확인 불가
```

작업 내용:

1. 웹 UI에서 UNKNOWN이 그대로 노출되는 곳이 있는지 확인
2. 사용자 화면에서는 UNKNOWN 대신 “확인 불가”로 표시
3. CSV/JSON에는 UNKNOWN을 유지
4. README에 UNKNOWN 처리 기준 추가
5. 누락값을 임의로 채우거나 추정하지 않도록 유지

권장 헬퍼 함수:

```python
def display_unknown(value):
    if value is None:
        return "확인 불가"
    if isinstance(value, str) and value.strip().upper() == "UNKNOWN":
        return "확인 불가"
    if value == "":
        return "확인 불가"
    return value
```

중요:

- 이 변환은 웹 UI 표시용이다.
- CSV/JSON 저장값은 UNKNOWN을 유지해야 한다.
- 내부 데이터 자체를 “확인 불가”로 바꾸면 안 된다.

README 추가 문구:

```text
## UNKNOWN / 확인 불가 처리 기준

ScholarCheck는 외부 API 응답에 없는 값을 임의로 생성하지 않습니다.

내부 데이터와 CSV/JSON 출력에서는 누락값을 UNKNOWN으로 유지합니다.
웹 UI에서는 사용자가 이해하기 쉽도록 UNKNOWN, None, 빈 값을 “확인 불가”로 표시합니다.

“확인 불가”는 검증 완료를 뜻하지 않습니다.
최종 인용 전에는 원문 페이지에서 제목, 저자, 출판연도, DOI, 학술지명, PDF 접근 가능 여부를 다시 확인해야 합니다.
```

---

## 5-4. 교수님용 안내 문구 추가

ScholarCheck를 사용하는 교수님들이 이 도구의 역할과 한계를 명확히 이해하도록 웹 UI와 README에 안내 문구를 추가한다.

중요 메시지:

- ScholarCheck는 논문 검색과 메타데이터 검증을 돕는 보조 도구이다.
- 검색 결과는 외부 API 응답을 기반으로 한다.
- 최종 인용 전에는 반드시 원문 페이지에서 다시 확인해야 한다.
- 국내 DB 검색 링크는 직접 확인용이며, 자동 검증 논문 목록과 분리된다.
- 수동 기록은 사용자가 직접 확인한 메모이며, 자동 검증 결과가 아니다.

웹 UI 상단 권장 문구:

```text
ScholarCheck는 논문 검색과 메타데이터 검증을 돕는 보조 도구입니다.
검색 결과는 Crossref, OpenAlex 등 외부 API 응답을 기반으로 하며, 최종 인용 전에는 반드시 원문 페이지에서 제목, 저자, 출판연도, DOI, 학술지명, PDF 접근 가능 여부를 다시 확인해야 합니다.
```

상세 화면 권장 문구:

```text
이 상세 정보는 외부 API 메타데이터 기준입니다.
최종 인용 전 원문 페이지에서 서지정보를 다시 확인하세요.
```

DOI 재검증 화면 권장 문구:

```text
DOI 재검증은 Crossref 응답 기준의 보조 확인입니다.
DOI가 없거나 Crossref 조회가 실패한 경우 새 DOI를 추정하거나 생성하지 않습니다.
```

국내 DB 영역 권장 문구:

```text
국내 DB 검색 링크는 직접 확인용입니다.
자동 검증 논문 목록에 포함되지 않습니다.
사용자가 직접 확인한 내용은 수동 기록으로만 저장되며, 자동 검증 결과로 승격되지 않습니다.
```

README 섹션:

```markdown
## 사용 전 주의사항

ScholarCheck는 논문 검색과 메타데이터 검증을 돕는 보조 도구입니다.

검색 결과는 Crossref, OpenAlex 등 외부 API 응답을 기반으로 하며, ScholarCheck가 논문 존재 여부나 원문 접근 가능성을 최종 보증하지 않습니다.

최종 인용 전에는 반드시 원문 페이지에서 다음 항목을 다시 확인해야 합니다.

- 제목
- 저자
- 출판연도
- DOI
- 학술지명 또는 출처
- PDF 접근 가능 여부
- 기관접속 또는 유료 접근 여부

국내 DB 검색 링크는 직접 확인용입니다.
국내 DB 결과는 자동 검증 논문 목록에 포함되지 않으며, 사용자가 직접 입력한 수동 기록은 자동 검증 결과가 아닙니다.
```

---

## 5-5. 수동 기록 백업/내보내기 확인

국내 DB 수동 확인 기록을 안전하게 저장하고, 필요할 때 JSON/CSV로 백업할 수 있게 한다.

현재 국내 DB 수동 확인 기록은 다음 위치에 저장된다.

```text
data/domestic_manual_checks.json
```

이 기록은 사용자가 직접 입력한 자료이므로 GitHub에 올라가면 안 된다.

### 저장 경로 확인

확인할 것:

1. 수동 기록 저장 경로가 위 위치인지
2. 해당 파일이 `.gitignore`에 포함되어 있는지
3. `data/` 폴더 전체를 ignore하는지, 또는 해당 파일만 ignore하는지
4. 샘플 파일이 필요하다면 실제 기록 파일이 아니라 `.example` 파일로 분리하는지

### 수동 기록 JSON 다운로드

요구사항:

1. 기록이 있으면 JSON 다운로드 가능
2. 기록이 없으면 빈 배열 `[]` 또는 안내 메시지 반환
3. 다운로드 파일명 예시:

```text
domestic_manual_checks_YYYYMMDD_HHMM.json
```

4. 이 다운로드는 자동 검증 논문 결과 다운로드와 분리해야 함

### 수동 기록 CSV 다운로드

요구사항:

1. 기록이 있으면 CSV 다운로드 가능
2. 기록이 없으면 헤더만 있는 CSV 또는 안내 메시지 반환
3. 다운로드 파일명 예시:

```text
domestic_manual_checks_YYYYMMDD_HHMM.csv
```

권장 CSV 컬럼:

```text
created_at,db_name,search_link,checked,title,authors,year,source,access_status,notes
```

### 웹 UI 표시

국내 DB 수동 확인 기록 영역에 다음 버튼을 추가하거나 확인한다.

```text
수동 기록 JSON 다운로드
수동 기록 CSV 다운로드
```

안내 문구:

```text
수동 기록은 사용자가 직접 확인한 내용이며, 자동 검증 논문 목록과 분리되어 저장됩니다.
```

### 수동 기록 삭제/초기화 버튼 제외

이번 범위에서는 삭제 또는 초기화 버튼을 만들지 않는다.

이유:

- 실수로 기록을 삭제할 위험이 있음
- 백업 기능부터 먼저 안정화하는 것이 우선

README 추가 내용:

```markdown
## 국내 DB 수동 확인 기록 백업

국내 DB 수동 확인 기록은 사용자가 RISS, KCI, DBpia, KISS, e-Article 등에서 직접 확인한 내용을 저장하는 기능입니다.

이 기록은 자동 검증 논문 목록이 아니며, 사용자가 직접 확인한 메모입니다.

기본 저장 위치:

```text
data/domestic_manual_checks.json
```

수동 기록은 사용자 입력 데이터이므로 GitHub에 커밋하지 않습니다.

웹 UI에서 수동 기록을 JSON 또는 CSV로 다운로드하여 별도로 백업할 수 있습니다.
```

---

# 6. MVP 4 작업지시서

## 현재 상태

MVP 3.5 안정화 완료.

완료된 기능:

- 샘플 검색 시나리오 문서화
- DOI 재검증 상태값 문서화
- UNKNOWN 표시 규칙 통일
- 교수님용 안내 문구 추가
- 국내 DB 수동 확인 기록 CSV/JSON 내보내기
- 국내 DB 수동 확인 기록 백업
- 자동 검증 논문 목록과 국내 DB 수동 기록 분리

---

## 6-1. MVP 4 목표

MVP 4에서는 실제 교수님 사용성을 높이기 위해 다음 두 가지를 구현한다.

1. 검색 세션 저장/불러오기
2. 교수님 검토용 HTML 리포트 생성

중요 원칙은 계속 유지한다.

- 없는 논문 생성 금지
- 없는 DOI 생성 금지
- PDF 링크 과장 금지
- UNKNOWN 값을 임의로 보완하지 않음
- 국내 DB 수동 기록은 자동 검증 논문 목록과 분리
- 최종 인용 전 원문 확인 필요 문구 유지

---

## 6-2. 검색 세션 저장 기능

검색 실행 후 해당 검색을 하나의 세션으로 저장할 수 있게 한다.

저장 위치:

```text
data/sessions/
```

세션 파일 예시:

```text
data/sessions/20260508_1530_artificial_intelligence_education/session.json
```

세션에는 다음 정보를 포함한다.

```json
{
  "session_id": "20260508_1530_artificial_intelligence_education",
  "created_at": "2026-05-08T15:30:00",
  "topic": "artificial intelligence education",
  "required_keywords": [],
  "helpful_keywords": [],
  "exclude_keywords": [],
  "year_from": null,
  "year_to": null,
  "limit": 10,
  "papers": [],
  "domestic_links": [],
  "manual_checks": [],
  "notes": [],
  "warnings": []
}
```

주의:

- 세션 저장 시 자동 검증 논문 결과와 국내 DB 수동 확인 기록을 구분해서 저장한다.
- 논문 결과에 없는 값을 임의로 채우지 않는다.
- DOI가 없으면 UNKNOWN 또는 null 상태를 유지한다.

---

## 6-3. 검색 세션 목록 보기

웹 UI에 “저장된 검색 세션” 영역을 추가한다.

표시 항목:

```text
세션 ID
검색 주제
생성일
논문 수
국내 DB 수동 기록 수
열기
HTML 리포트 생성
```

세션이 없으면 다음 문구를 표시한다.

```text
저장된 검색 세션이 없습니다.
```

---

## 6-4. 검색 세션 불러오기

저장된 세션을 열면 다음을 볼 수 있게 한다.

- 검색 조건
- 자동 검증 논문 목록
- 국내 DB 검색 링크
- 국내 DB 수동 확인 기록
- DOI 재검증 결과
- 인용 전 체크리스트
- 제한 사항 안내

주의:

- 세션을 불러올 때 외부 API를 자동 재호출하지 않는다.
- 저장된 값을 그대로 보여준다.
- 새로 검색하려면 별도 버튼이나 기존 검색 화면을 사용한다.

---

## 6-5. 검색 결과 저장 버튼

웹 검색 결과 화면에 다음 버튼을 추가한다.

```text
현재 검색 결과를 세션으로 저장
```

저장 성공 시:

```text
검색 세션이 저장되었습니다.
```

저장 실패 시:

```text
검색 세션 저장에 실패했습니다.
```

---

## 6-6. 교수님 검토용 HTML 리포트 생성

세션 단위로 HTML 리포트를 생성한다.

저장 위치:

```text
outputs/reports/
```

파일명 예시:

```text
scholarcheck_report_20260508_1530_artificial_intelligence_education.html
```

HTML 리포트에는 다음 섹션을 포함한다.

```text
1. 리포트 제목
2. 생성일
3. 검색 주제
4. 검색 조건
5. 사용 키워드
   - 필수 키워드
   - 도움 키워드
   - 제외 키워드
6. 자동 검증 논문 목록
7. 논문별 상세 정보
8. DOI 재검증 상태
9. PDF 접근 가능 여부
10. 인용 전 체크리스트
11. 국내 DB 직접 확인 링크
12. 국내 DB 수동 확인 기록
13. 현재 제한 사항
14. 최종 인용 전 확인 안내
```

리포트 상단 안내 문구:

```text
이 리포트는 ScholarCheck가 외부 API 메타데이터와 사용자 수동 기록을 바탕으로 생성한 검토용 자료입니다.
최종 인용 전에는 반드시 원문 페이지에서 제목, 저자, 출판연도, DOI, 학술지명, PDF 접근 가능 여부를 다시 확인해야 합니다.
```

국내 DB 영역 안내 문구:

```text
국내 DB 수동 확인 기록은 사용자가 직접 확인해 입력한 내용이며, 자동 검증 논문 목록과 분리됩니다.
```

---

## 6-7. HTML 리포트 다운로드

웹 UI에서 세션별로 HTML 리포트를 생성하고 다운로드할 수 있게 한다.

버튼:

```text
HTML 리포트 생성
HTML 리포트 다운로드
```

주의:

- PDF 생성은 이번 MVP 4 범위에서 제외한다.
- PDF 변환은 MVP 4.5에서 검토한다.
- HTML은 브라우저 인쇄 기능으로 PDF 저장 가능하도록 구조를 단순하게 만든다.

---

## 6-8. 사용자 데이터 gitignore 확인

다음 경로가 GitHub에 올라가지 않도록 확인한다.

```text
data/sessions/
outputs/reports/
data/domestic_manual_checks.json
data/backups/
outputs/
```

필요하면 `.gitignore`에 추가한다.

---

## 6-9. 테스트 추가

다음 테스트를 추가한다.

1. 검색 세션 저장 시 session.json이 생성된다.
2. 세션 파일에 검색 조건과 논문 결과가 포함된다.
3. 국내 DB 수동 기록은 manual_checks 필드에 분리 저장된다.
4. 세션 목록 조회가 정상 작동한다.
5. 세션이 없을 때 빈 목록을 반환한다.
6. 세션 불러오기 시 외부 API를 자동 호출하지 않는다.
7. HTML 리포트 생성 시 파일이 생성된다.
8. HTML 리포트에 검색 주제와 키워드가 포함된다.
9. HTML 리포트에 자동 검증 논문 목록과 국내 DB 수동 기록이 분리 표시된다.
10. HTML 리포트에 최종 인용 전 확인 안내 문구가 포함된다.

기존 테스트가 깨지지 않아야 한다.

실행:

```bash
python -m compileall scholarcheck tests
python -m pytest
```

---

## 6-10. README 보강

README에 다음 내용을 추가한다.

```markdown
## 검색 세션 저장/불러오기

ScholarCheck는 검색 결과를 세션 단위로 저장할 수 있습니다.

세션에는 검색 조건, 자동 검증 논문 목록, 국내 DB 검색 링크, 국내 DB 수동 확인 기록이 포함됩니다.

기본 저장 위치:

```text
data/sessions/
```

세션 데이터는 사용자 작업 데이터이므로 GitHub에 커밋하지 않습니다.

## HTML 리포트 생성

저장된 검색 세션을 바탕으로 교수님 검토용 HTML 리포트를 생성할 수 있습니다.

리포트에는 검색 조건, 키워드, 자동 검증 논문 목록, DOI 재검증 상태, PDF 접근 가능 여부, 국내 DB 수동 확인 기록, 인용 전 체크리스트가 포함됩니다.

HTML 리포트는 검토용 자료이며, 최종 참고문헌으로 확정하기 전 원문 페이지 확인이 필요합니다.

PDF 파일은 직접 생성하지 않지만, 브라우저 인쇄 기능을 통해 PDF로 저장할 수 있습니다.
```

---

## 6-11. 완료 후 보고 형식

작업 완료 후 다음 형식으로 보고한다.

```text
ScholarCheck MVP 4 완료

커밋:
커밋 해시와 메시지

수정/추가 파일:
- ...

추가 기능:
- 검색 세션 저장
- 검색 세션 목록 보기
- 검색 세션 불러오기
- HTML 리포트 생성
- HTML 리포트 다운로드
- README 보강
- 테스트 추가

검증 결과:
- python -m compileall scholarcheck tests
- python -m pytest
- 웹 UI 주요 경로 HTTP 200 확인
- 세션 저장/불러오기 확인
- HTML 리포트 생성/다운로드 확인

현재 제한 사항:
- PDF 직접 생성은 아직 없음
- 로그인/사용자 계정 없음
- 클라우드 저장 없음
- 국내 DB 자동 크롤링 없음
- 논문 전문 자동 요약 없음

다음 개선 제안:
- MVP 4.5: PDF 리포트 생성
- MVP 5: APA/KCI 참고문헌 후보 생성
- MVP 5.5: 선행연구 매트릭스와 Excel 출력
```

---

# 7. MVP 5 작업지시서

## 현재 상태

MVP 4 완료.

현재 기능:

- 검색 결과를 data/sessions/에 JSON 세션으로 저장
- 저장된 세션 목록 보기
- 저장된 세션 불러오기
- 세션 기반 교수님 검토용 HTML 리포트 다운로드
- 자동 검증 논문, 국내 DB 직접 확인 링크, 국내 수동 기록 분리 표시
- UNKNOWN/확인 불가 값 임의 보완 없음

---

## 7-1. MVP 5 목표

저장된 세션 또는 검색 결과를 바탕으로 참고문헌 후보를 생성한다.

중요:

참고문헌은 “최종 확정”이 아니라 “후보안”이다.

ScholarCheck는 누락값을 임의로 보완하지 않는다.

최종 인용 전 원문 확인 안내 문구를 유지한다.

---

## 7-2. 참고문헌 후보 생성 모듈 추가

새 파일을 추가한다.

```text
scholarcheck/citations.py
```

주요 함수:

```python
build_apa_reference_candidate(paper) -> str
build_korean_reference_candidate(paper) -> str
build_reference_candidates(papers) -> list[dict]
```

---

## 7-3. APA 7th 후보 생성

가능한 범위에서 APA 7th 스타일 후보를 생성한다.

형식 예시:

```text
Author, A. A., & Author, B. B. (2024). Title of article. Journal Name. https://doi.org/xxxxx
```

필드 매핑:

```text
authors → 저자
year → 연도
title → 제목
journal/source → 학술지명 또는 출처
doi → DOI 링크
url → DOI가 없을 때 원문 URL 후보
```

주의:

- 저자 없음: [Author 확인 필요]
- 연도 없음: [Year 확인 필요]
- 제목 없음: [Title 확인 필요]
- 학술지 없음: [Source 확인 필요]
- DOI 없음: DOI 없이 생성
- DOI와 URL 모두 없음: 링크 생략 또는 [URL 확인 필요]
- APA를 완벽히 보장하지 말고 “APA 후보”로 표시

---

## 7-4. 국문 참고문헌 후보 생성

국내 연구자가 검토하기 쉬운 국문형 후보를 생성한다.

형식 예시:

```text
저자명. (연도). 논문 제목. 학술지명. DOI 또는 URL.
```

주의:

- 해외 논문도 국문형 참고문헌 후보로 변환 가능
- 누락값은 [확인 필요]로 표시
- 최종 KCI/학회 양식 확정은 사용자가 원문 기준으로 확인해야 함

---

## 7-5. 세션 상세 화면에 참고문헌 후보 표시

웹 UI에서 세션을 불러왔을 때 다음 영역을 추가한다.

```text
참고문헌 후보
```

표시 항목:

```text
1. APA 후보
2. 국문 참고문헌 후보
3. 확인 필요 항목
```

각 논문별로 표시한다.

---

## 7-6. HTML 리포트에 참고문헌 후보 포함

세션 기반 HTML 리포트에 다음 섹션을 추가한다.

```text
참고문헌 후보
```

포함 내용:

```text
- APA 후보
- 국문 참고문헌 후보
- 확인 필요 항목
```

안내 문구:

```text
아래 참고문헌은 자동 확정본이 아니라 후보안입니다.
최종 제출 전 원문 페이지에서 제목, 저자, 출판연도, 학술지명, DOI를 반드시 확인하세요.
```

---

## 7-7. CSV/JSON 출력 추가 여부

이번 MVP에서는 기존 검색 결과 CSV/JSON 구조를 깨지 않도록 한다.

가능하면 세션 리포트용 JSON에만 참고문헌 후보를 포함한다.

기존 출력 호환성을 깨지 않는다.

---

## 7-8. 테스트 추가

다음 테스트를 추가한다.

1. DOI가 있는 논문은 APA 후보에 DOI 링크가 포함된다.
2. DOI가 없는 논문은 DOI를 임의 생성하지 않는다.
3. 저자 UNKNOWN이면 [Author 확인 필요]가 표시된다.
4. 연도 UNKNOWN이면 [Year 확인 필요]가 표시된다.
5. 제목 UNKNOWN이면 [Title 확인 필요]가 표시된다.
6. 국문 참고문헌 후보가 생성된다.
7. 세션 HTML 리포트에 참고문헌 후보 섹션이 포함된다.
8. 참고문헌 후보 안내 문구가 리포트에 포함된다.
9. 기존 테스트가 깨지지 않는다.

실행:

```bash
python -m compileall scholarcheck tests
python -m pytest
```

---

## 7-9. README 보강

README에 다음 섹션을 추가한다.

```markdown
## 참고문헌 후보 생성

ScholarCheck는 검색 결과 또는 저장된 세션을 바탕으로 APA 후보와 국문 참고문헌 후보를 생성할 수 있습니다.

이 참고문헌은 자동 확정본이 아니라 후보안입니다.

누락된 값은 임의로 보완하지 않으며, [확인 필요]로 표시합니다.

최종 제출 전에는 반드시 원문 페이지에서 제목, 저자, 출판연도, 학술지명, DOI를 다시 확인해야 합니다.
```

---

## 7-10. 완료 후 보고 형식

작업 완료 후 다음 형식으로 보고한다.

```text
ScholarCheck MVP 5 완료

커밋:
커밋 해시와 메시지

수정/추가 파일:
- ...

추가 기능:
- APA 참고문헌 후보 생성
- 국문 참고문헌 후보 생성
- 세션 상세 화면 참고문헌 후보 표시
- HTML 리포트 참고문헌 후보 포함
- README 보강
- 테스트 추가

검증 결과:
- python -m compileall scholarcheck tests
- python -m pytest
- 세션 상세 화면 확인
- HTML 리포트 확인

현재 제한 사항:
- 참고문헌은 최종 확정본이 아니라 후보안
- APA/KCI 양식 완전 보증 아님
- 원문 확인 필수

다음 개선 제안:
- MVP 5.5: 선행연구 매트릭스 생성
- MVP 6: Excel 출력
- MVP 6.5: PDF 리포트 생성
```

---

# 8. 현재까지의 커밋 흐름 요약

사용자가 제공한 주요 커밋 정보 기준입니다.

```text
533b04c test: add guardrails and stabilize web UI
982cf94 feat: add paper detail verification workflow
0808508 docs: add sample search scenarios
93873a1 docs: document DOI verification statuses
7138929 fix: unify unknown display behavior
3acc0e4 docs: add professor guidance copy
754517c feat: export and backup manual checks
624e44c feat: add search sessions and professor reports
```

---

# 9. 현재 제한 사항

ScholarCheck의 현재 제한 사항은 다음과 같다.

- API 응답 기반 검증 도구이며 논문 존재 여부를 최종 보증하지 않는다.
- 국내 DB는 자동 크롤링하지 않고 직접 확인 링크/수동 기록만 제공한다.
- PDF 가능 여부는 PDF URL 확인 기준이며 기관접속 필요 가능성이 있다.
- DOI가 없는 논문에 DOI를 새로 생성하지 않는다.
- UNKNOWN 값을 임의로 보완하지 않는다.
- HTML 리포트는 검토용 자료이며 최종 인용 자료가 아니다.
- PDF 직접 생성은 아직 지원하지 않는다.
- 로그인/사용자 계정 기능은 없다.
- 클라우드 저장 기능은 없다.
- 논문 전문 자동 요약 기능은 없다.

---

# 10. 다음 개발 후보

우선순위 추천:

```text
1. MVP 5: APA/KCI 참고문헌 후보 생성
2. MVP 5.5: 선행연구 매트릭스 생성
3. MVP 6: Excel 출력
4. MVP 6.5: PDF 리포트 생성
5. MVP 7: 연구 프로젝트별 저장/관리
6. MVP 8: 로그인/클라우드 저장
```

핵심 원칙은 끝까지 유지한다.

```text
많이 찾는 도구보다 틀리지 않는 도구가 우선이다.
확인되지 않은 것은 확인 불가로 남긴다.
자동 검증 결과와 사용자 수동 기록은 끝까지 분리한다.
```
