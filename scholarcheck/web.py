from __future__ import annotations

import argparse
import html
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from scholarcheck.models import DomesticSearchLink, PaperRecord, UNKNOWN
from scholarcheck.pipeline import build_query, search_papers


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765


class ScholarCheckHandler(BaseHTTPRequestHandler):
    server_version = "ScholarCheckWeb/0.1"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._send_html(render_home())
            return

        if parsed.path == "/search":
            params = parse_qs(parsed.query)
            topic = _first_param(params, "topic")
            if not topic:
                self._send_html(render_home(error="연구 주제를 입력해 주세요."), HTTPStatus.BAD_REQUEST)
                return

            limit = _int_param(params, "limit", default=10, minimum=1, maximum=50)
            year_from = _optional_int_param(params, "year_from")
            year_to = _optional_int_param(params, "year_to")
            query = build_query(topic, year_from=year_from, year_to=year_to, limit=limit)
            result = search_papers(query)
            self._send_html(render_results(query, result.records, result.domestic_links, result.warnings))
            return

        self._send_html(render_not_found(), HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args: object) -> None:
        return

    def _send_html(self, body: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        payload = body.encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def render_home(error: str = "") -> str:
    return _page(
        title="ScholarCheck",
        body=f"""
        <section class="search-band">
          <div class="inner">
            <div class="heading-block">
              <p class="eyebrow">논문나침반 MVP</p>
              <h1>ScholarCheck</h1>
              <p class="lead">검증 가능한 해외 논문 메타데이터와 국내 DB 직접 확인 링크를 분리해서 보여줍니다.</p>
            </div>
            {_render_search_form(error=error)}
          </div>
        </section>
        <section class="inner notes">
          <h2>검증 원칙</h2>
          <ul>
            <li>Crossref와 OpenAlex에서 받은 값만 자동 검증 논문 목록에 표시합니다.</li>
            <li>누락된 DOI, 링크, PDF 상태는 생성하지 않고 <code>UNKNOWN</code> 또는 확인 불가로 남깁니다.</li>
            <li>국내 DB는 자동 크롤링하지 않으며, 직접 확인용 검색 링크만 제공합니다.</li>
          </ul>
        </section>
        """,
    )


def render_results(
    query: object,
    records: list[PaperRecord],
    domestic_links: list[DomesticSearchLink],
    warnings: list[str],
) -> str:
    topic = getattr(query, "topic", "")
    return _page(
        title=f"ScholarCheck - {_escape(topic)}",
        body=f"""
        <section class="search-band compact">
          <div class="inner">
            <div class="heading-block">
              <p class="eyebrow">검색 결과</p>
              <h1>{_escape(topic)}</h1>
            </div>
            {_render_search_form(
                topic=topic,
                limit=getattr(query, "limit", 10),
                year_from=getattr(query, "year_from", None),
                year_to=getattr(query, "year_to", None),
            )}
          </div>
        </section>
        <main class="inner results">
          {_render_warnings(warnings)}
          <section class="result-section">
            <div class="section-title">
              <h2>자동 검증 논문 목록</h2>
              <span>{len(records)}건</span>
            </div>
            {_render_records_table(records)}
          </section>
          <section class="result-section domestic">
            <div class="section-title">
              <h2>국내 DB 직접 확인 필요</h2>
              <span>{len(domestic_links)}개 DB</span>
            </div>
            <p class="section-note">아래 링크는 검색어를 URL 인코딩한 직접 확인용 링크입니다. 검색 결과, 원문 접근, PDF 다운로드 가능 여부는 각 DB에서 확인해야 합니다.</p>
            {_render_domestic_table(domestic_links)}
          </section>
        </main>
        """,
    )


def render_not_found() -> str:
    return _page(
        title="ScholarCheck - Not Found",
        body="""
        <section class="inner notes">
          <h1>페이지를 찾을 수 없습니다.</h1>
          <p><a href="/">검색 화면으로 돌아가기</a></p>
        </section>
        """,
    )


def _render_search_form(
    *,
    topic: str = "",
    limit: int = 10,
    year_from: int | None = None,
    year_to: int | None = None,
    error: str = "",
) -> str:
    return f"""
    <form class="search-form" action="/search" method="get">
      {f'<p class="error">{_escape(error)}</p>' if error else ''}
      <label>
        <span>연구 주제</span>
        <input name="topic" value="{_escape(topic)}" placeholder="예: 인공지능 교육, 3D printed footwear lattice" required>
      </label>
      <div class="form-grid">
        <label>
          <span>결과 수</span>
          <input name="limit" type="number" min="1" max="50" value="{limit}">
        </label>
        <label>
          <span>시작 연도</span>
          <input name="year_from" type="number" min="1900" max="2100" value="{_escape(year_from) if year_from else ''}" placeholder="선택">
        </label>
        <label>
          <span>종료 연도</span>
          <input name="year_to" type="number" min="1900" max="2100" value="{_escape(year_to) if year_to else ''}" placeholder="선택">
        </label>
      </div>
      <button type="submit">검색</button>
    </form>
    """


def _render_warnings(warnings: list[str]) -> str:
    if not warnings:
        return ""
    items = "".join(f"<li>{_escape(warning)}</li>" for warning in warnings)
    return f"""
    <section class="warnings">
      <h2>API 조회 경고</h2>
      <ul>{items}</ul>
    </section>
    """


def _render_records_table(records: list[PaperRecord]) -> str:
    if not records:
        return '<p class="empty">자동 검증된 논문을 찾지 못했습니다.</p>'

    rows = []
    for record in records:
        rows.append(
            f"""
            <tr>
              <td class="title-cell">
                <strong>{_escape(record.title)}</strong>
                <span>{_escape(record.source_api)}</span>
              </td>
              <td>{_escape(record.authors_display)}</td>
              <td>{_escape(record.year_display)}</td>
              <td>{_escape(record.venue)}</td>
              <td>{_doi_link(record.doi)}</td>
              <td>{_page_link(record.landing_page_url)}</td>
              <td>{'가능' if record.pdf_available else '확인 불가'}</td>
              <td>{_escape(record.region)}</td>
              <td class="score">{record.total_score:.2f}</td>
              <td>{_escape(record.caution)}</td>
            </tr>
            """
        )

    return f"""
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>논문 제목</th>
            <th>저자</th>
            <th>연도</th>
            <th>학술지/기관</th>
            <th>DOI</th>
            <th>원문 페이지</th>
            <th>PDF</th>
            <th>구분</th>
            <th>점수</th>
            <th>주의사항</th>
          </tr>
        </thead>
        <tbody>{''.join(rows)}</tbody>
      </table>
    </div>
    """


def _render_domestic_table(links: list[DomesticSearchLink]) -> str:
    rows = []
    for link in links:
        rows.append(
            f"""
            <tr>
              <td><strong>{_escape(link.database_name)}</strong></td>
              <td>{_escape(link.search_keywords)}</td>
              <td>{_escape(link.result_status)}</td>
              <td>{_escape(link.download_status)}</td>
              <td><a href="{_escape(link.search_url)}" target="_blank" rel="noreferrer">검색 링크 열기</a></td>
            </tr>
            """
        )

    return f"""
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>DB</th>
            <th>검색어</th>
            <th>결과 상태</th>
            <th>다운로드</th>
            <th>링크</th>
          </tr>
        </thead>
        <tbody>{''.join(rows)}</tbody>
      </table>
    </div>
    """


def _doi_link(doi: str) -> str:
    if doi == UNKNOWN:
        return UNKNOWN
    url = f"https://doi.org/{html.escape(doi, quote=True)}"
    return f'<a href="{url}" target="_blank" rel="noreferrer">{_escape(doi)}</a>'


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
    :root {{
      --ink: #18212f;
      --muted: #657287;
      --line: #d7dde8;
      --surface: #f6f8fb;
      --accent: #0f766e;
      --accent-dark: #115e59;
      --warn-bg: #fff8e6;
      --warn-line: #e9c46a;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--ink);
      background: #ffffff;
      font-family: "Segoe UI", "Malgun Gothic", Arial, sans-serif;
      font-size: 15px;
      line-height: 1.5;
    }}
    a {{ color: var(--accent-dark); text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .inner {{
      width: min(1180px, calc(100% - 32px));
      margin: 0 auto;
    }}
    .search-band {{
      background: var(--surface);
      border-bottom: 1px solid var(--line);
      padding: 42px 0 34px;
    }}
    .search-band.compact {{ padding: 28px 0 24px; }}
    .heading-block {{ margin-bottom: 22px; }}
    .eyebrow {{
      margin: 0 0 4px;
      color: var(--accent-dark);
      font-weight: 700;
      font-size: 13px;
    }}
    h1 {{
      margin: 0;
      font-size: 34px;
      line-height: 1.15;
      letter-spacing: 0;
    }}
    h2 {{
      margin: 0;
      font-size: 20px;
      letter-spacing: 0;
    }}
    .lead {{
      max-width: 720px;
      margin: 10px 0 0;
      color: var(--muted);
    }}
    .search-form {{
      display: grid;
      gap: 14px;
      max-width: 920px;
    }}
    label span {{
      display: block;
      margin-bottom: 6px;
      color: var(--muted);
      font-size: 13px;
      font-weight: 700;
    }}
    input {{
      width: 100%;
      min-height: 42px;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 9px 11px;
      color: var(--ink);
      background: #fff;
      font: inherit;
    }}
    input:focus {{
      outline: 2px solid rgba(15, 118, 110, 0.18);
      border-color: var(--accent);
    }}
    .form-grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
    }}
    button {{
      justify-self: start;
      min-height: 42px;
      border: 0;
      border-radius: 6px;
      padding: 0 22px;
      color: white;
      background: var(--accent);
      font: inherit;
      font-weight: 700;
      cursor: pointer;
    }}
    button:hover {{ background: var(--accent-dark); }}
    .notes, .results {{ padding: 28px 0 44px; }}
    .notes ul {{ padding-left: 20px; color: var(--muted); }}
    .result-section {{ margin-top: 26px; }}
    .section-title {{
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 10px;
    }}
    .section-title span, .section-note, .empty {{ color: var(--muted); }}
    .section-note {{ margin: 0 0 12px; }}
    .table-wrap {{
      overflow-x: auto;
      border: 1px solid var(--line);
      border-radius: 6px;
    }}
    table {{
      width: 100%;
      min-width: 980px;
      border-collapse: collapse;
      background: #fff;
    }}
    th, td {{
      border-bottom: 1px solid var(--line);
      padding: 10px 12px;
      text-align: left;
      vertical-align: top;
    }}
    th {{
      color: #2b3748;
      background: #eef2f6;
      font-size: 13px;
      white-space: nowrap;
    }}
    td {{ color: #263244; }}
    tr:last-child td {{ border-bottom: 0; }}
    .title-cell strong {{
      display: block;
      min-width: 260px;
    }}
    .title-cell span {{
      display: block;
      margin-top: 4px;
      color: var(--muted);
      font-size: 12px;
    }}
    .score {{
      font-weight: 800;
      color: var(--accent-dark);
      white-space: nowrap;
    }}
    .warnings {{
      border: 1px solid var(--warn-line);
      border-radius: 6px;
      padding: 14px 16px;
      background: var(--warn-bg);
    }}
    .warnings h2 {{ font-size: 16px; }}
    .warnings ul {{ margin: 8px 0 0; padding-left: 20px; }}
    .error {{
      margin: 0;
      color: #b42318;
      font-weight: 700;
    }}
    code {{
      padding: 1px 5px;
      border-radius: 4px;
      background: #eef2f6;
    }}
    @media (max-width: 720px) {{
      .form-grid {{ grid-template-columns: 1fr; }}
      h1 {{ font-size: 28px; }}
      .section-title {{ display: block; }}
      table {{ min-width: 860px; }}
    }}
  </style>
</head>
<body>{body}</body>
</html>"""


def _first_param(params: dict[str, list[str]], name: str) -> str:
    values = params.get(name, [])
    if not values:
        return ""
    return values[0].strip()


def _int_param(
    params: dict[str, list[str]],
    name: str,
    *,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
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
