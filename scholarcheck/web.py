from __future__ import annotations

import argparse
import html
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

from scholarcheck.models import DomesticSearchLink, PaperRecord, SearchQuery, UNKNOWN
from scholarcheck.output import records_to_csv, records_to_json
from scholarcheck.pipeline import build_query, parse_keyword_argument, search_papers


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765


class ScholarCheckHandler(BaseHTTPRequestHandler):
    server_version = "ScholarCheckWeb/0.3"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._send_html(render_home())
            return
        if parsed.path in {"/search", "/download.csv", "/download.json"}:
            self._handle_search_like(parsed)
            return
        self._send_html(render_not_found(), HTTPStatus.NOT_FOUND)

    def _handle_search_like(self, parsed) -> None:
        params = parse_qs(parsed.query)
        topic = _first_param(params, "topic")
        if not topic:
            self._send_html(render_home(error="연구 주제를 입력해 주세요."), HTTPStatus.BAD_REQUEST)
            return

        query = _query_from_params(params)
        try:
            result = search_papers(query)
        except Exception as exc:
            self._send_html(render_home(error=f"검색 중 오류가 발생했습니다: {exc}"), HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        if parsed.path == "/download.csv":
            self._send_download(records_to_csv(result.records), "scholarcheck_results.csv", "text/csv; charset=utf-8")
            return
        if parsed.path == "/download.json":
            payload = records_to_json(
                result.records,
                result.domestic_links,
                result.relaxation_suggestions,
            )
            self._send_download(payload, "scholarcheck_results.json", "application/json; charset=utf-8")
            return

        self._send_html(
            render_results(
                query,
                result.records,
                result.domestic_links,
                result.warnings,
                result.relaxation_suggestions,
                parsed.query,
            )
        )

    def log_message(self, format: str, *args: object) -> None:
        return

    def _send_html(self, body: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        payload = body.encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _send_download(self, body: str, filename: str, content_type: str) -> None:
        payload = body.encode("utf-8-sig")
        self.send_response(HTTPStatus.OK.value)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def render_home(error: str = "") -> str:
    return _page(
        "ScholarCheck",
        f"""
        <section class="search-band">
          <div class="inner">
            <p class="eyebrow">논문나침반 MVP</p>
            <h1>ScholarCheck</h1>
            <p class="lead">API 응답 기준의 논문 메타데이터를 검수하고, 국내 DB 직접 확인 링크를 분리해서 보여줍니다.</p>
            {_render_search_form(error=error)}
          </div>
        </section>
        <section class="inner notes">
          <h2>검증 원칙</h2>
          <ul>
            <li>논문 존재 여부를 최종 보증하지 않으며 최종 인용 전 원문 페이지 확인이 필요합니다.</li>
            <li>PDF 가능 여부는 API가 제공한 PDF URL 확인 여부 기준입니다.</li>
            <li>국내 DB는 자동 크롤링하지 않고 직접 확인 링크만 제공합니다.</li>
          </ul>
        </section>
        """,
    )


def render_results(
    query: SearchQuery,
    records: list[PaperRecord],
    domestic_links: list[DomesticSearchLink],
    warnings: list[str],
    suggestions: list[str],
    raw_query: str,
) -> str:
    return _page(
        f"ScholarCheck - {_escape(query.topic)}",
        f"""
        <section class="search-band compact">
          <div class="inner">
            <p class="eyebrow">검색 결과</p>
            <h1>{_escape(query.topic)}</h1>
            {_render_search_form(
                topic=query.topic,
                required=", ".join(query.required_keywords),
                helpful=", ".join(query.helpful_keywords),
                exclude=", ".join(query.excluded_keywords),
                limit=query.limit,
                year_from=query.year_from,
                year_to=query.year_to,
            )}
          </div>
        </section>
        <main class="inner results">
          {_render_warnings(warnings)}
          <div class="download-actions">
            <a class="button-link" href="/download.csv?{_escape(raw_query)}">CSV 다운로드</a>
            <a class="button-link secondary" href="/download.json?{_escape(raw_query)}">JSON 다운로드</a>
          </div>
          <section class="result-section">
            <div class="section-title"><h2>자동 검증 논문 목록</h2><span>{len(records)}건</span></div>
            {_render_records_table(records)}
          </section>
          {_render_suggestions(suggestions)}
          <section class="result-section domestic">
            <div class="section-title"><h2>국내 DB 직접 확인 필요</h2><span>{len(domestic_links)}개 DB</span></div>
            <p class="section-note">국내 DB는 자동 검증 논문 목록에 포함하지 않습니다. 검색 결과와 원문 접근 권한은 각 DB에서 직접 확인해야 합니다.</p>
            {_render_domestic_table(domestic_links)}
          </section>
        </main>
        """,
    )


def render_not_found() -> str:
    return _page("ScholarCheck - Not Found", '<section class="inner notes"><h1>페이지를 찾을 수 없습니다.</h1><p><a href="/">검색 화면으로 돌아가기</a></p></section>')


def _render_search_form(
    *,
    topic: str = "",
    required: str = "",
    helpful: str = "",
    exclude: str = "",
    limit: int = 10,
    year_from: int | None = None,
    year_to: int | None = None,
    error: str = "",
) -> str:
    return f"""
    <form class="search-form" action="/search" method="get" onsubmit="document.body.classList.add('loading')">
      {f'<p class="error">{_escape(error)}</p>' if error else ''}
      <div class="loading-note">검색 중입니다. API 응답을 확인하고 있습니다.</div>
      <label><span>연구 주제</span><input name="topic" value="{_escape(topic)}" placeholder="예: artificial intelligence education" required></label>
      <div class="form-grid">
        <label><span>필수 키워드</span><input name="required" value="{_escape(required)}" placeholder="artificial intelligence, education"></label>
        <label><span>도움 키워드</span><input name="helpful" value="{_escape(helpful)}" placeholder="teacher, curriculum"></label>
        <label><span>제외 키워드</span><input name="exclude" value="{_escape(exclude)}" placeholder="patent, news"></label>
      </div>
      <div class="form-grid small">
        <label><span>결과 수</span><input name="limit" type="number" min="1" max="50" value="{limit}"></label>
        <label><span>시작 연도</span><input name="year_from" type="number" min="1900" max="2100" value="{_escape(year_from) if year_from else ''}" placeholder="선택"></label>
        <label><span>종료 연도</span><input name="year_to" type="number" min="1900" max="2100" value="{_escape(year_to) if year_to else ''}" placeholder="선택"></label>
      </div>
      <button type="submit">검색</button>
    </form>
    """


def _render_warnings(warnings: list[str]) -> str:
    if not warnings:
        return ""
    return f'<section class="warnings"><h2>오류 또는 API 경고</h2><ul>{"".join(f"<li>{_escape(w)}</li>" for w in warnings)}</ul></section>'


def _render_suggestions(suggestions: list[str]) -> str:
    if not suggestions:
        return ""
    return f'<section class="suggestions"><h2>검색 조건 완화 제안</h2><ul>{"".join(f"<li>{_escape(s)}</li>" for s in suggestions)}</ul></section>'


def _render_records_table(records: list[PaperRecord]) -> str:
    if not records:
        return '<p class="empty">결과 없음: 자동 검증된 논문을 찾지 못했습니다.</p>'

    rows = []
    for record in records:
        rows.append(
            f"""
            <tr>
              <td><strong>{_escape(record.title)}</strong><span>{_escape(record.source_api)}</span></td>
              <td>{_escape(record.authors_display)}</td>
              <td>{_escape(record.year_display)}</td>
              <td>{_escape(record.venue)}</td>
              <td>{_doi_link(record.doi)}</td>
              <td>{_page_link(record.landing_page_url)}</td>
              <td>{"가능" if record.pdf_available else "확인 불가"}</td>
              <td>{_escape(record.citation_display)}</td>
              <td>{"고전 고인용" if record.classic_highly_cited else "-"}</td>
              <td class="score">{record.total_score:.2f}</td>
              <td>{_escape("; ".join(record.ranking_notes) or "근거 없음")}</td>
              <td>{_escape(record.caution)}</td>
            </tr>
            """
        )
    return f"""
    <div class="table-wrap"><table>
      <thead><tr><th>논문 제목</th><th>저자</th><th>연도</th><th>학술지/기관</th><th>DOI</th><th>원문</th><th>PDF</th><th>인용</th><th>고전</th><th>점수</th><th>정렬 근거</th><th>주의사항</th></tr></thead>
      <tbody>{''.join(rows)}</tbody>
    </table></div>
    """


def _render_domestic_table(links: list[DomesticSearchLink]) -> str:
    rows = [
        f'<tr><td><strong>{_escape(link.database_name)}</strong></td><td>{_escape(link.search_keywords)}</td><td>{_escape(link.result_status)}</td><td>{_escape(link.download_status)}</td><td><a href="{_escape(link.search_url)}" target="_blank" rel="noreferrer">검색 링크 열기</a></td></tr>'
        for link in links
    ]
    return f'<div class="table-wrap"><table><thead><tr><th>DB</th><th>검색어</th><th>상태</th><th>다운로드</th><th>링크</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div>'


def _doi_link(doi: str) -> str:
    if doi == UNKNOWN:
        return UNKNOWN
    return f'<a href="https://doi.org/{_escape(doi)}" target="_blank" rel="noreferrer">{_escape(doi)}</a>'


def _page_link(url: str) -> str:
    if url == UNKNOWN:
        return UNKNOWN
    return f'<a href="{_escape(url)}" target="_blank" rel="noreferrer">열기</a>'


def _page(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{_escape(title)}</title>
  <style>
    :root {{ --ink:#18212f; --muted:#657287; --line:#d7dde8; --surface:#f6f8fb; --accent:#0f766e; --accent-dark:#115e59; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; color:var(--ink); font-family:"Segoe UI","Malgun Gothic",Arial,sans-serif; font-size:15px; line-height:1.5; }}
    a {{ color:var(--accent-dark); text-decoration:none; }}
    a:hover {{ text-decoration:underline; }}
    .inner {{ width:min(1180px, calc(100% - 32px)); margin:0 auto; }}
    .search-band {{ background:var(--surface); border-bottom:1px solid var(--line); padding:34px 0; }}
    .compact {{ padding:24px 0; }}
    .eyebrow {{ margin:0 0 4px; color:var(--accent-dark); font-weight:700; font-size:13px; }}
    h1 {{ margin:0 0 18px; font-size:34px; line-height:1.15; letter-spacing:0; }}
    h2 {{ margin:0; font-size:20px; letter-spacing:0; }}
    .lead {{ max-width:760px; color:var(--muted); }}
    .search-form {{ display:grid; gap:14px; max-width:1040px; }}
    label span {{ display:block; margin-bottom:6px; color:var(--muted); font-size:13px; font-weight:700; }}
    input {{ width:100%; min-height:42px; border:1px solid var(--line); border-radius:6px; padding:9px 11px; font:inherit; }}
    .form-grid {{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:12px; }}
    button,.button-link {{ display:inline-flex; align-items:center; min-height:42px; border:0; border-radius:6px; padding:0 18px; color:#fff; background:var(--accent); font-weight:700; cursor:pointer; }}
    .button-link.secondary {{ background:#2f4858; }}
    .download-actions {{ display:flex; gap:10px; margin-bottom:20px; }}
    .notes,.results {{ padding:28px 0 44px; }}
    .result-section {{ margin-top:26px; }}
    .section-title {{ display:flex; justify-content:space-between; gap:16px; margin-bottom:10px; }}
    .section-title span,.section-note,.empty {{ color:var(--muted); }}
    .table-wrap {{ overflow-x:auto; border:1px solid var(--line); border-radius:6px; }}
    table {{ width:100%; min-width:1120px; border-collapse:collapse; }}
    th,td {{ border-bottom:1px solid var(--line); padding:10px 12px; text-align:left; vertical-align:top; }}
    th {{ background:#eef2f6; font-size:13px; white-space:nowrap; }}
    td strong {{ display:block; min-width:250px; }}
    td span {{ display:block; margin-top:4px; color:var(--muted); font-size:12px; }}
    .score {{ font-weight:800; color:var(--accent-dark); }}
    .warnings,.suggestions {{ border-radius:6px; padding:14px 16px; margin-bottom:22px; }}
    .warnings {{ border:1px solid #e9c46a; background:#fff8e6; }}
    .suggestions {{ border:1px solid #8fc7bd; background:#edf7f5; margin-top:24px; }}
    .error {{ margin:0; color:#b42318; font-weight:700; }}
    .loading-note {{ display:none; color:var(--accent-dark); font-weight:700; }}
    body.loading .loading-note {{ display:block; }}
    body.loading button {{ opacity:.7; pointer-events:none; }}
    @media (max-width:760px) {{ .form-grid {{ grid-template-columns:1fr; }} h1 {{ font-size:28px; }} .section-title {{ display:block; }} table {{ min-width:980px; }} }}
  </style>
</head>
<body>{body}</body>
</html>"""


def _query_from_params(params: dict[str, list[str]]) -> SearchQuery:
    return build_query(
        _first_param(params, "topic"),
        required_keywords=parse_keyword_argument(_first_param(params, "required")),
        helpful_keywords=parse_keyword_argument(_first_param(params, "helpful")),
        excluded_keywords=parse_keyword_argument(_first_param(params, "exclude")),
        year_from=_optional_int_param(params, "year_from"),
        year_to=_optional_int_param(params, "year_to"),
        limit=_int_param(params, "limit", default=10, minimum=1, maximum=50),
    )


def _first_param(params: dict[str, list[str]], name: str) -> str:
    values = params.get(name, [])
    return values[0].strip() if values else ""


def _int_param(params: dict[str, list[str]], name: str, *, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(_first_param(params, name))
    except ValueError:
        value = default
    return min(max(value, minimum), maximum)


def _optional_int_param(params: dict[str, list[str]], name: str) -> int | None:
    raw = _first_param(params, name)
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def run_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    server = ThreadingHTTPServer((host, port), ScholarCheckHandler)
    print(f"ScholarCheck web server running at http://{host}:{port}")
    server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the ScholarCheck local web UI.")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()
    run_server(args.host, args.port)


if __name__ == "__main__":
    main()
