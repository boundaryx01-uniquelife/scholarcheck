# ScholarCheck Sample Search Scenarios

이 문서는 ScholarCheck MVP를 실제 연구 주제 검토에 사용할 때 바로 실행해 볼 수 있는 샘플 검색 시나리오입니다.

공통 원칙:

- 검색 결과는 Crossref/OpenAlex API 응답 기준입니다.
- 국내 DB는 자동 검증 결과에 포함하지 않고 직접 확인 링크만 제공합니다.
- 최종 인용 전에는 원문 페이지에서 서지정보를 다시 확인해야 합니다.
- 결과가 부족하면 가짜 논문을 만들지 않고 검색 조건 완화 제안을 확인합니다.

## 1. Artificial Intelligence Education

연구 의도: AI 교육 일반, 교사 교육, 교육과정 연구의 핵심 선행연구 확인

```powershell
python -m scholarcheck "artificial intelligence education" --required "artificial intelligence, education" --helpful "teacher, curriculum" --exclude "patent, news" --limit 10 --format csv
```

확인 포인트:

- 제목 또는 초록에 `artificial intelligence`, `education`이 실제로 포함되는지 확인
- 교사 또는 교육과정 관련 논문이 상위에 오는지 확인
- DOI와 PDF URL이 있는 결과를 우선 검토

## 2. Generative AI in Elementary Education

연구 의도: 초등교육 맥락에서 생성형 AI 활용 연구 확인

```powershell
python -m scholarcheck "generative AI in elementary education" --required "generative AI, elementary education" --helpful "student, teacher, classroom" --exclude "higher education, patent, news" --limit 10 --format csv
```

확인 포인트:

- `higher education` 결과가 섞이면 제외 키워드가 제대로 작동하는지 확인
- 초등교육이 아닌 일반 AI 교육 논문은 관련성 점수를 낮게 해석
- 최근 5년 자료를 우선 검토

## 3. Digital Literacy Teacher Education

연구 의도: 교사교육에서 디지털 리터러시 역량, 프로그램, 교육과정 연구 확인

```powershell
python -m scholarcheck "digital literacy teacher education" --required "digital literacy, teacher education" --helpful "competence, curriculum, professional development" --exclude "marketing, news" --limit 10 --format csv
```

확인 포인트:

- 교사 전문성 개발과 연결되는지 확인
- 학술지/기관 정보가 `UNKNOWN`인 결과는 원문 페이지에서 추가 확인
- 인용 수가 높은 고전 논문은 최신 논문과 분리해 배경 이론으로 검토

## 4. Computational Thinking Primary School

연구 의도: 초등학교 컴퓨팅 사고력 교육 관련 선행연구 확인

```powershell
python -m scholarcheck "computational thinking primary school" --required "computational thinking, primary school" --helpful "elementary, programming, curriculum" --exclude "university, patent, news" --limit 10 --format csv
```

확인 포인트:

- `primary school`과 `elementary`가 혼용되므로 도움 키워드 결과를 함께 확인
- 대학생 대상 연구가 섞이면 제외 키워드를 조정
- 국내 DB 링크에서 KCI/RISS 자료를 별도 확인

## 5. AI Literacy Curriculum

연구 의도: AI 리터러시 교육과정, 역량 모델, 평가 관련 연구 확인

```powershell
python -m scholarcheck "AI literacy curriculum" --required "AI literacy, curriculum" --helpful "competency, assessment, framework" --exclude "industry, patent, news" --limit 10 --format csv
```

확인 포인트:

- `AI literacy`가 제목에 직접 포함되는 논문을 우선 검토
- 초록에만 포함되는 논문은 중간 관련성으로 해석
- 결과가 적으면 `artificial intelligence literacy`로 검색 조건을 완화

## Web UI에서 실행하기

```powershell
python -m scholarcheck.web
```

브라우저에서 다음 주소를 엽니다.

```text
http://127.0.0.1:8765
```

각 시나리오의 주제, 필수 키워드, 도움 키워드, 제외 키워드를 입력한 뒤 검색합니다. 결과별 `상세 보기`에서 DOI 재검증과 인용 전 체크리스트를 확인할 수 있습니다.
