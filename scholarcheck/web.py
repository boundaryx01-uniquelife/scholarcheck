from __future__ import annotations

import argparse
import html
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

from scholarcheck.checklist import build_citation_checklist
from scholarcheck.citations import CITATION_NOTICE, build_reference_candidates
from scholarcheck.excel_export import build_excel_workbook
from scholarcheck.manual_checks import (
    add_manual_check,
    backup_manual_checks,
    load_manual_checks,
    manual_checks_to_csv,
    manual_checks_to_json,
)
from scholarcheck.matrix import MATRIX_NOTICE, build_literature_matrix
from scholarcheck.models import DomesticManualCheck, DomesticSearchLink, PaperRecord, SearchQuery, SearchResult, UNKNOWN
from scholarcheck.output import records_to_csv, records_to_json
from scholarcheck.pipeline import build_query, parse_keyword_argument, search_papers
from scholarcheck.reports import render_professor_report
from scholarcheck.sessions import list_search_sessions, load_search_session, resolve_session_path, save_search_session
from scholarcheck.verification import verify_doi_with_crossref


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
SCREEN_UNKNOWN = "확인 불가"
PDF_UNKNOWN = "확인 불가 / 기관접속 필요 가능성 있음"
PROFESSOR_GUIDANCE_ITEMS = [
    "ScholarCheck는 선행연구 후보를 빠르게 좁히는 보조 도구이며, 논문 존재 여부를 최종 보증하지 않습니다.",
    "최종 인용 전에는 원문 페이지에서 제목, 저자, 학술지, 연도, DOI, 권호, 페이지를 직접 대조해야 합니다.",
    "DOI, PDF, 오픈액세스 여부는 외부 API 응답 기준이며, 확인 불가는 임의로 보완하지 않은 값입니다.",
    "국내 DB 결과는 자동 검증 목록이 아니므로 기관 접속 또는 DB 원문 페이지에서 별도로 확인해야 합니다.",
]


class ScholarCheckHandler(BaseHTTPRequestHandler):
    server_version = "ScholarCheckWeb/0.5"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._send_html(render_home())
            return
        if parsed.path in {"/search", "/download.csv", "/download.json"}:
            self._handle_search_like(parsed)
            return
        if parsed.path in {"/manual-checks.csv", "/manual-checks.json", "/manual-checks-backup"}:
            self._handle_manual_check_download(parsed.path)
            return
        if parsed.path == "/save-session":
            self._handle_save_session(parsed)
            return
        if parsed.path == "/sessions":
            self._send_html(render_sessions())
            return
        if parsed.path == "/session":
            self._handle_session(parsed)
            return
        if parsed.path == "/report.html":
            self._handle_report(parsed)
            return
        if parsed.path == "/workbook.xlsx":
            self._handle_workbook(parsed)
            return
        if parsed.path == "/citations":
            self._handle_citations(parsed)
            return
        if parsed.path == "/matrix":
            self._handle_matrix(parsed)
            return
        if parsed.path == "/detail":
            self._handle_detail(parsed)
            return
        if parsed.path == "/verify-doi":
            self._handle_verify_doi(parsed)
            return
        self._send_html(render_not_found(), HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/manual-check":
            self._send_html(render_not_found(), HTTPStatus.NOT_FOUND)
            return

        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8")
        params = parse_qs(body)
        add_manual_check(
            DomesticManualCheck(
                database_name=_first_param(params, "database_name"),
                search_keywords=_first_param(params, "search_keywords"),
                title=_first_param(params, "title"),
                landing_page_url=_first_param(params, "landing_page_url") or UNKNOWN,
                doi=_first_param(params, "doi") or UNKNOWN,
                pdf_status=_first_param(params, "pdf_status") or PDF_UNKNOWN,
                notes=_first_param(params, "notes"),
            )
        )
        self._send_redirect(_first_param(params, "redirect_to") or "/")

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
            self._send_html(
                render_home(error=f"검색 중 오류가 발생했습니다: {exc}"),
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )
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
                query=query,
                records=result.records,
                domestic_links=result.domestic_links,
                warnings=result.warnings,
                suggestions=result.relaxation_suggestions,
                raw_query=parsed.query,
                manual_checks=load_manual_checks(),
            )
        )

    def _handle_save_session(self, parsed) -> None:
        params = parse_qs(parsed.query)
        topic = _first_param(params, "topic")
        if not topic:
            self._send_html(render_home(error="연구 주제를 입력해 주세요."), HTTPStatus.BAD_REQUEST)
            return
        query = _query_from_params(params)
        result = search_papers(query)
        path = save_search_session(query, result)
        self._send_redirect(f"/session?id={path.stem}")

    def _handle_session(self, parsed) -> None:
        params = parse_qs(parsed.query)
        session_id = _first_param(params, "id")
        try:
            metadata, query, result = load_search_session(resolve_session_path(session_id))
        except (FileNotFoundError, ValueError):
            self._send_html(render_not_found(), HTTPStatus.NOT_FOUND)
            return
        self._send_html(render_session(metadata, query, result, manual_checks=load_manual_checks()))

    def _handle_report(self, parsed) -> None:
        params = parse_qs(parsed.query)
        session_id = _first_param(params, "session")
        try:
            metadata, query, result = load_search_session(resolve_session_path(session_id))
        except (FileNotFoundError, ValueError):
            self._send_html(render_not_found(), HTTPStatus.NOT_FOUND)
            return
        self._send_download(
            render_professor_report(metadata, query, result, load_manual_checks()),
            f"scholarcheck_report_{metadata['session_id']}.html",
            "text/html; charset=utf-8",
        )

    def _handle_workbook(self, parsed) -> None:
        params = parse_qs(parsed.query)
        session_id = _first_param(params, "session")
        try:
            metadata, query, result = load_search_session(resolve_session_path(session_id))
        except (FileNotFoundError, ValueError):
            self._send_html(render_not_found(), HTTPStatus.NOT_FOUND)
            return
        self._send_binary_download(
            build_excel_workbook(metadata, query, result, load_manual_checks()),
            f"scholarcheck_workbook_{metadata['session_id']}.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    def _handle_citations(self, parsed) -> None:
        params = parse_qs(parsed.query)
        session_id = _first_param(params, "session")
        if session_id:
            try:
                metadata, query, result = load_search_session(resolve_session_path(session_id))
            except (FileNotFoundError, ValueError):
                self._send_html(render_not_found(), HTTPStatus.NOT_FOUND)
                return
            self._send_html(render_citations(query, result, session_id=metadata.get("session_id", session_id)))
            return

        topic = _first_param(params, "topic")
        if not topic:
            self._send_html(render_home(error="연구 주제를 입력해 주세요."), HTTPStatus.BAD_REQUEST)
            return
        query = _query_from_params(params)
        result = search_papers(query)
        self._send_html(render_citations(query, result, raw_query=parsed.query))

    def _handle_matrix(self, parsed) -> None:
        params = parse_qs(parsed.query)
        session_id = _first_param(params, "session")
        if session_id:
            try:
                metadata, query, result = load_search_session(resolve_session_path(session_id))
            except (FileNotFoundError, ValueError):
                self._send_html(render_not_found(), HTTPStatus.NOT_FOUND)
                return
            self._send_html(render_literature_matrix(query, result, session_id=metadata.get("session_id", session_id)))
            return

        topic = _first_param(params, "topic")
        if not topic:
            self._send_html(render_home(error="연구 주제를 입력해 주세요."), HTTPStatus.BAD_REQUEST)
            return
        query = _query_from_params(params)
        result = search_papers(query)
        self._send_html(render_literature_matrix(query, result, raw_query=parsed.query))

    def _handle_manual_check_download(self, path: str) -> None:
        checks = load_manual_checks()
        if path == "/manual-checks.csv":
            self._send_download(
                manual_checks_to_csv(checks),
                "domestic_manual_checks.csv",
                "text/csv; charset=utf-8",
            )
            return
        if path == "/manual-checks.json":
            self._send_download(
                manual_checks_to_json(checks),
                "domestic_manual_checks.json",
                "application/json; charset=utf-8",
            )
            return

        backup_path = backup_manual_checks()
        self._send_download(
            backup_path.read_text(encoding="utf-8"),
            backup_path.name,
            "application/json; charset=utf-8",
        )

    def _handle_detail(self, parsed) -> None:
        params = parse_qs(parsed.query)
        query = _query_from_params(params)
        index = _int_param(params, "index", default=0, minimum=0, maximum=999)
        result = search_papers(query)
        if index >= len(result.records):
            self._send_html(render_not_found(), HTTPStatus.NOT_FOUND)
            return
        self._send_html(render_detail(query, result.records[index], index, parsed.query))

    def _handle_verify_doi(self, parsed) -> None:
        params = parse_qs(parsed.query)
        query = _query_from_params(params)
        index = _int_param(params, "index", default=0, minimum=0, maximum=999)
        result = search_papers(query)
        if index >= len(result.records):
            self._send_html(render_not_found(), HTTPStatus.NOT_FOUND)
            return
        paper = result.records[index]
        verification = verify_doi_with_crossref(paper)
        self._send_html(render_detail(query, paper, index, parsed.query, verification_message=verification))

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
        self._send_binary_download(payload, filename, content_type)

    def _send_binary_download(self, payload: bytes, filename: str, content_type: str) -> None:
        self.send_response(HTTPStatus.OK.value)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _send_redirect(self, location: str) -> None:
        self.send_response(HTTPStatus.SEE_OTHER.value)
        self.send_header("Location", location)
        self.end_headers()


def render_home(error: str = "") -> str:
    return _page(
        "ScholarCheck",
        f"""
        <section class="search-band">
          <div class="inner">
            <p class="eyebrow">논문나침반 MVP</p>
            <h1>ScholarCheck</h1>
            <p class="lead">API 응답 기준의 논문 메타데이터를 검수하고, 인용 전 확인 절차와 국내 DB 직접 확인 기록을 분리해서 관리합니다.</p>
            {_render_search_form(error=error)}
          </div>
        </section>
        <section class="inner notes">
          <h2>검증 원칙</h2>
          <ul>
            <li>논문 존재 여부를 최종 보증하지 않습니다. 최종 인용 전 원문 페이지 확인이 필요합니다.</li>
            <li>내부 데이터와 CSV/JSON에서는 누락값을 <code>UNKNOWN</code>으로 유지합니다.</li>
            <li>사용자 화면에서는 누락값을 <code>{SCREEN_UNKNOWN}</code>로 표시합니다.</li>
          </ul>
        </section>
        {_render_professor_guidance()}
        """,
    )


def render_results(
    *,
    query: SearchQuery,
    records: list[PaperRecord],
    domestic_links: list[DomesticSearchLink],
    warnings: list[str],
    suggestions: list[str],
    raw_query: str,
    manual_checks: list[DomesticManualCheck],
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
            <a class="button-link secondary" href="/citations?{_escape(raw_query)}">참고문헌 후보 보기</a>
            <a class="button-link secondary" href="/matrix?{_escape(raw_query)}">선행연구 매트릭스</a>
            <a class="button-link secondary" href="/save-session?{_escape(raw_query)}">검색 세션 저장</a>
            <a class="button-link secondary" href="/sessions">저장 세션 보기</a>
          </div>
          <section class="result-section">
            <div class="section-title"><h2>자동 검증 논문 목록</h2><span>{len(records)}건</span></div>
            {_render_records_table(records, raw_query)}
          </section>
          {_render_suggestions(suggestions)}
          <section class="result-section domestic">
            <div class="section-title"><h2>국내 DB 직접 확인 필요</h2><span>{len(domestic_links)}개 DB</span></div>
            <p class="section-note">국내 DB는 자동 검증 논문 목록에 포함하지 않습니다. 검색 결과와 원문 접근 권한은 각 DB에서 직접 확인해야 합니다.</p>
            {_render_domestic_table(domestic_links)}
            {_render_manual_check_form(query, raw_query)}
            {_render_manual_export_actions(manual_checks)}
            {_render_manual_checks(manual_checks)}
          </section>
        </main>
        """,
    )


def render_session(
    metadata: dict[str, str],
    query: SearchQuery,
    result: SearchResult,
    manual_checks: list[DomesticManualCheck],
) -> str:
    raw_query = urlencode(
        {
            "topic": query.topic,
            "required": ", ".join(query.required_keywords),
            "helpful": ", ".join(query.helpful_keywords),
            "exclude": ", ".join(query.excluded_keywords),
            "limit": str(query.limit),
            "year_from": "" if query.year_from is None else str(query.year_from),
            "year_to": "" if query.year_to is None else str(query.year_to),
        }
    )
    session_id = metadata.get("session_id", UNKNOWN)
    return _page(
        f"ScholarCheck Session - {_escape(query.topic)}",
        f"""
        <section class="search-band compact">
          <div class="inner">
            <p class="eyebrow">저장된 검색 세션</p>
            <h1>{_escape(query.topic)}</h1>
            <p class="lead">저장 시각: {_screen(metadata.get("saved_at", UNKNOWN))}</p>
          </div>
        </section>
        <main class="inner results">
          <div class="download-actions">
            <a class="button-link" href="/report.html?session={_escape(session_id)}">교수님 검토용 HTML 리포트</a>
            <a class="button-link secondary" href="/workbook.xlsx?session={_escape(session_id)}">Excel 통합 파일</a>
            <a class="button-link secondary" href="/citations?session={_escape(session_id)}">참고문헌 후보 보기</a>
            <a class="button-link secondary" href="/matrix?session={_escape(session_id)}">선행연구 매트릭스</a>
            <a class="button-link secondary" href="/search?{_escape(raw_query)}">같은 조건으로 다시 검색</a>
            <a class="button-link secondary" href="/sessions">저장 세션 목록</a>
          </div>
          <section class="result-section">
            <div class="section-title"><h2>저장된 자동 검증 논문 목록</h2><span>{len(result.records)}건</span></div>
            {_render_records_table(result.records, raw_query)}
          </section>
          {_render_suggestions(result.relaxation_suggestions)}
          <section class="result-section domestic">
            <div class="section-title"><h2>국내 DB 직접 확인 필요</h2><span>{len(result.domestic_links)}개 DB</span></div>
            {_render_domestic_table(result.domestic_links)}
            {_render_manual_export_actions(manual_checks)}
            {_render_manual_checks(manual_checks)}
          </section>
        </main>
        """,
    )


def render_sessions() -> str:
    session_paths = list_search_sessions()
    if not session_paths:
        content = '<p class="empty">아직 저장된 검색 세션이 없습니다.</p>'
    else:
        rows = []
        for path in session_paths:
            try:
                metadata, query, result = load_search_session(path)
            except (OSError, ValueError):
                continue
            session_id = metadata.get("session_id", path.stem)
            rows.append(
                f"""
                <tr>
                  <td><strong>{_escape(query.topic)}</strong><span>{_screen(metadata.get("saved_at", UNKNOWN))}</span></td>
                  <td>{len(result.records)}건</td>
                  <td><a href="/session?id={_escape(session_id)}">불러오기</a></td>
                  <td><a href="/report.html?session={_escape(session_id)}">HTML 리포트</a></td>
                  <td><a href="/workbook.xlsx?session={_escape(session_id)}">Excel</a></td>
                  <td><a href="/citations?session={_escape(session_id)}">참고문헌 후보</a></td>
                  <td><a href="/matrix?session={_escape(session_id)}">매트릭스</a></td>
                </tr>
                """
            )
        content = f"""
        <div class="table-wrap"><table>
          <thead><tr><th>주제</th><th>논문 수</th><th>세션</th><th>리포트</th><th>Excel</th><th>참고문헌</th><th>매트릭스</th></tr></thead>
          <tbody>{''.join(rows)}</tbody>
        </table></div>
        """
    return _page(
        "ScholarCheck Sessions",
        f"""
        <section class="search-band compact">
          <div class="inner">
            <p class="eyebrow">검색 세션</p>
            <h1>저장된 검색 세션</h1>
            <p><a href="/">검색 화면으로 돌아가기</a></p>
          </div>
        </section>
        <main class="inner results">{content}</main>
        """,
    )


def render_literature_matrix(
    query: SearchQuery,
    result: SearchResult,
    *,
    raw_query: str = "",
    session_id: str = "",
) -> str:
    rows = build_literature_matrix(result.records)
    if not rows:
        body = '<p class="empty">선행연구 매트릭스를 만들 자동 검증 논문 결과가 없습니다. 가짜 행을 생성하지 않았습니다.</p>'
    else:
        table_rows = []
        for index, row in enumerate(rows, start=1):
            table_rows.append(
                f"""
                <tr>
                  <td>{index}</td>
                  <td><strong>{_screen(row.title)}</strong></td>
                  <td>{_screen(row.authors)}</td>
                  <td>{_screen(row.year)}</td>
                  <td>{_screen(row.venue)}</td>
                  <td>{_screen(row.doi)}</td>
                  <td>{_escape(row.research_purpose)}</td>
                  <td>{_escape(row.research_method)}</td>
                  <td>{_escape(row.research_subjects)}</td>
                  <td>{_escape(row.key_findings)}</td>
                  <td>{_screen(row.relevance_note)}</td>
                  <td class="memo-cell">{_escape(row.user_memo)}</td>
                  <td>{_screen(row.verification_note)}</td>
                </tr>
                """
            )
        body = f"""
        <div class="table-wrap"><table>
          <thead><tr><th>#</th><th>논문</th><th>저자</th><th>연도</th><th>학술지/기관</th><th>DOI</th><th>연구목적</th><th>연구방법</th><th>연구대상</th><th>주요결과</th><th>관련성 메모</th><th>사용자 메모</th><th>확인 상태</th></tr></thead>
          <tbody>{''.join(table_rows)}</tbody>
        </table></div>
        """
    back_link = f"/session?id={_escape(session_id)}" if session_id else f"/search?{_escape(raw_query)}"
    return _page(
        f"ScholarCheck Matrix - {_escape(query.topic)}",
        f"""
        <section class="search-band compact">
          <div class="inner">
            <p class="eyebrow">선행연구 검토표</p>
            <h1>{_escape(query.topic)}</h1>
            <p class="lead">{_escape(MATRIX_NOTICE)}</p>
            <p><a href="{back_link}">이전 화면으로 돌아가기</a></p>
          </div>
        </section>
        <main class="inner results">
          <section class="result-section">
            <div class="section-title"><h2>선행연구 매트릭스 초안</h2><span>{len(rows)}건</span></div>
            {body}
          </section>
        </main>
        """,
    )


def render_citations(
    query: SearchQuery,
    result: SearchResult,
    *,
    raw_query: str = "",
    session_id: str = "",
) -> str:
    candidates = build_reference_candidates(result.records)
    if not candidates:
        body = '<p class="empty">참고문헌 후보를 만들 자동 검증 논문 결과가 없습니다. 가짜 후보를 생성하지 않았습니다.</p>'
    else:
        rows = []
        for index, candidate in enumerate(candidates, start=1):
            warnings = "".join(f"<li>{_escape(item)}</li>" for item in candidate.warnings)
            rows.append(
                f"""
                <tr>
                  <td>{index}</td>
                  <td><strong>{_screen(candidate.title)}</strong></td>
                  <td>{_escape(candidate.reference)}</td>
                  <td><ul>{warnings}</ul></td>
                </tr>
                """
            )
        body = f"""
        <div class="table-wrap"><table>
          <thead><tr><th>#</th><th>논문</th><th>참고문헌 후보안</th><th>확인 필요</th></tr></thead>
          <tbody>{''.join(rows)}</tbody>
        </table></div>
        """
    back_link = f"/session?id={_escape(session_id)}" if session_id else f"/search?{_escape(raw_query)}"
    return _page(
        f"ScholarCheck Citations - {_escape(query.topic)}",
        f"""
        <section class="search-band compact">
          <div class="inner">
            <p class="eyebrow">참고문헌 후보</p>
            <h1>{_escape(query.topic)}</h1>
            <p class="lead">{_escape(CITATION_NOTICE)}</p>
            <p><a href="{back_link}">이전 화면으로 돌아가기</a></p>
          </div>
        </section>
        <main class="inner results">
          <section class="result-section">
            <div class="section-title"><h2>참고문헌 후보안</h2><span>{len(candidates)}건</span></div>
            {body}
          </section>
        </main>
        """,
    )


def render_detail(
    query: SearchQuery,
    paper: PaperRecord,
    index: int,
    raw_query: str,
    verification_message=None,
) -> str:
    checklist = build_citation_checklist(paper)
    verify_query = _merge_query(raw_query, {"index": str(index)})
    back_query = _strip_query_keys(raw_query, {"index"})
    return _page(
        f"ScholarCheck Detail - {_escape(paper.title)}",
        f"""
        <section class="search-band compact">
          <div class="inner">
            <p class="eyebrow">검색 결과 상세 보기</p>
            <h1>{_screen(paper.title)}</h1>
            <p><a href="/search?{_escape(back_query)}">검색 결과로 돌아가기</a></p>
          </div>
        </section>
        <main class="inner results">
          {render_verification_message(verification_message)}
          <div class="download-actions">
            <a class="button-link" href="/verify-doi?{_escape(verify_query)}">DOI 재검증</a>
          </div>
          <section class="result-section">
            <h2>상세 정보</h2>
            {_render_detail_table(paper)}
          </section>
          {_render_professor_guidance(compact=True)}
          <section class="result-section">
            <h2>인용 전 체크리스트</h2>
            {_render_checklist(checklist)}
          </section>
        </main>
        """,
    )


def render_verification_message(verification) -> str:
    if verification is None:
        return ""
    return f"""
    <section class="suggestions">
      <h2>DOI 재검증 결과</h2>
      <p><strong>{_screen(verification.status)}</strong>: {_screen(verification.message)}</p>
      <p>DOI: {_screen(verification.doi)} / Crossref 제목: {_screen(verification.title)}</p>
    </section>
    """


def render_not_found() -> str:
    return _page(
        "ScholarCheck - Not Found",
        '<section class="inner notes"><h1>페이지를 찾을 수 없습니다.</h1><p><a href="/">검색 화면으로 돌아가기</a></p></section>',
    )


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


def _render_records_table(records: list[PaperRecord], raw_query: str) -> str:
    if not records:
        return '<p class="empty">결과 없음: 자동 검증된 논문을 찾지 못했습니다.</p>'

    rows = []
    for index, record in enumerate(records):
        detail_query = _merge_query(raw_query, {"index": str(index)})
        rows.append(
            f"""
            <tr>
              <td><strong>{_screen(record.title)}</strong><span>{_screen(record.source_api)}</span></td>
              <td>{_screen(record.authors_display)}</td>
              <td>{_screen(record.year_display)}</td>
              <td>{_doi_link(record.doi)}</td>
              <td>{"가능" if record.pdf_available else SCREEN_UNKNOWN}</td>
              <td>{_screen(record.open_access_display)}</td>
              <td>{_screen(record.citation_display)}</td>
              <td>{"고전 고인용" if record.classic_highly_cited else "-"}</td>
              <td class="score">{record.total_score:.2f}</td>
              <td><a href="/detail?{_escape(detail_query)}">상세 보기</a></td>
            </tr>
            """
        )
    return f"""
    <div class="table-wrap"><table>
      <thead><tr><th>논문 제목</th><th>저자</th><th>연도</th><th>DOI</th><th>PDF</th><th>OA</th><th>인용</th><th>고전</th><th>점수</th><th>상세</th></tr></thead>
      <tbody>{''.join(rows)}</tbody>
    </table></div>
    """


def _render_professor_guidance(*, compact: bool = False) -> str:
    heading = "교수님용 인용 전 안내" if compact else "교수님용 사용 안내"
    items = "".join(f"<li>{_escape(item)}</li>" for item in PROFESSOR_GUIDANCE_ITEMS)
    section_class = "result-section professor-guidance" if compact else "inner notes professor-guidance"
    return f"""
    <section class="{section_class}">
      <h2>{heading}</h2>
      <ul>{items}</ul>
    </section>
    """


def _render_detail_table(paper: PaperRecord) -> str:
    rows = [
        ("제목", paper.title),
        ("저자", paper.authors_display),
        ("출판연도", paper.year_display),
        ("출처", paper.source_api),
        ("학술지", paper.venue),
        ("DOI", paper.doi),
        ("원문 URL", paper.landing_page_url),
        ("PDF URL", paper.pdf_url),
        ("다운로드 상태", "PDF 직접 가능" if paper.pdf_available else PDF_UNKNOWN),
        ("오픈액세스 여부", paper.open_access_display),
        ("인용 수", paper.citation_display),
        ("초록", paper.abstract),
        ("관련성 점수", f"{paper.relevance_score:.2f}"),
        ("최신성 점수", f"{paper.recency_score:.2f}"),
        ("신뢰도 점수", f"{paper.usability_score:.2f}"),
        ("최종 점수", f"{paper.total_score:.2f}"),
        ("notes", "; ".join(paper.ranking_notes) or UNKNOWN),
        ("classic_candidate 여부", "YES" if paper.classic_highly_cited else "NO"),
    ]
    body = "".join(f"<tr><th>{_escape(label)}</th><td>{_screen_link(value)}</td></tr>" for label, value in rows)
    return f'<div class="table-wrap detail"><table><tbody>{body}</tbody></table></div>'


def _render_checklist(items) -> str:
    rows = "".join(
        f"<tr><td>{_escape(item.label)}</td><td>{_escape(item.status)}</td><td>{_screen(item.detail)}</td></tr>"
        for item in items
    )
    return f'<div class="table-wrap"><table><thead><tr><th>항목</th><th>상태</th><th>내용</th></tr></thead><tbody>{rows}</tbody></table></div>'


def _render_domestic_table(links: list[DomesticSearchLink]) -> str:
    rows = [
        f'<tr><td><strong>{_escape(link.database_name)}</strong></td><td>{_screen(link.search_keywords)}</td><td>{_screen(link.result_status)}</td><td>{_screen(link.download_status)}</td><td><a href="{_escape(link.search_url)}" target="_blank" rel="noreferrer">검색 링크 열기</a></td></tr>'
        for link in links
    ]
    return f'<div class="table-wrap"><table><thead><tr><th>DB</th><th>검색어</th><th>상태</th><th>다운로드</th><th>링크</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div>'


def _render_manual_check_form(query: SearchQuery, raw_query: str) -> str:
    return f"""
    <section class="manual-form">
      <h2>국내 DB 수동 확인 기록</h2>
      <form method="post" action="/manual-check">
        <input type="hidden" name="redirect_to" value="/search?{_escape(raw_query)}">
        <div class="form-grid">
          <label><span>DB명</span><input name="database_name" placeholder="RISS" required></label>
          <label><span>검색어</span><input name="search_keywords" value="{_escape(' '.join(query.required_keywords or query.keywords))}" required></label>
          <label><span>PDF 상태</span><input name="pdf_status" value="{PDF_UNKNOWN}"></label>
        </div>
        <label><span>확인한 논문 제목</span><input name="title" required></label>
        <div class="form-grid">
          <label><span>원문 URL</span><input name="landing_page_url"></label>
          <label><span>DOI</span><input name="doi"></label>
          <label><span>메모</span><input name="notes"></label>
        </div>
        <button type="submit">수동 확인 기록 저장</button>
      </form>
    </section>
    """


def _render_manual_export_actions(checks: list[DomesticManualCheck]) -> str:
    count = len(checks)
    return f"""
    <div class="download-actions manual-downloads">
      <a class="button-link secondary" href="/manual-checks.csv">수동 기록 CSV 내보내기</a>
      <a class="button-link secondary" href="/manual-checks.json">수동 기록 JSON 내보내기</a>
      <a class="button-link secondary" href="/manual-checks-backup">수동 기록 백업 파일 받기</a>
      <span class="download-note">저장된 수동 기록 {count}건</span>
    </div>
    """


def _render_manual_checks(checks: list[DomesticManualCheck]) -> str:
    if not checks:
        return '<p class="empty">아직 저장된 국내 DB 수동 확인 기록이 없습니다.</p>'
    rows = "".join(
        f"<tr><td>{_screen(check.database_name)}</td><td>{_screen(check.title)}</td><td>{_screen(check.doi)}</td><td>{_screen(check.pdf_status)}</td><td>{_screen(check.checked_at)}</td><td>{_screen(check.notes)}</td></tr>"
        for check in reversed(checks[-20:])
    )
    return f'<div class="table-wrap"><table><thead><tr><th>DB</th><th>제목</th><th>DOI</th><th>PDF</th><th>확인일</th><th>메모</th></tr></thead><tbody>{rows}</tbody></table></div>'


def _render_warnings(warnings: list[str]) -> str:
    if not warnings:
        return ""
    return f'<section class="warnings"><h2>오류 또는 API 경고</h2><ul>{"".join(f"<li>{_escape(w)}</li>" for w in warnings)}</ul></section>'


def _render_suggestions(suggestions: list[str]) -> str:
    if not suggestions:
        return ""
    return f'<section class="suggestions"><h2>검색 조건 완화 제안</h2><ul>{"".join(f"<li>{_escape(s)}</li>" for s in suggestions)}</ul></section>'


def _doi_link(doi: str) -> str:
    if doi == UNKNOWN:
        return SCREEN_UNKNOWN
    return f'<a href="https://doi.org/{_escape(doi)}" target="_blank" rel="noreferrer">{_escape(doi)}</a>'


def _page_link(url: str) -> str:
    if url == UNKNOWN:
        return SCREEN_UNKNOWN
    return f'<a href="{_escape(url)}" target="_blank" rel="noreferrer">열기</a>'


def _screen_link(value: str) -> str:
    if value.startswith("http://") or value.startswith("https://"):
        return _page_link(value)
    return _screen(value)


def _screen(value: object) -> str:
    text = str(value).strip()
    if not text or text == UNKNOWN:
        return SCREEN_UNKNOWN
    return _escape(text)


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
    h2 {{ margin:0 0 10px; font-size:20px; letter-spacing:0; }}
    .lead {{ max-width:760px; color:var(--muted); }}
    .search-form,.manual-form form {{ display:grid; gap:14px; max-width:1040px; }}
    label span {{ display:block; margin-bottom:6px; color:var(--muted); font-size:13px; font-weight:700; }}
    input {{ width:100%; min-height:42px; border:1px solid var(--line); border-radius:6px; padding:9px 11px; font:inherit; }}
    .form-grid {{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:12px; }}
    button,.button-link {{ display:inline-flex; align-items:center; min-height:42px; border:0; border-radius:6px; padding:0 18px; color:#fff; background:var(--accent); font-weight:700; cursor:pointer; }}
    .button-link.secondary {{ background:#2f4858; }}
    .download-actions {{ display:flex; flex-wrap:wrap; gap:10px; margin-bottom:20px; }}
    .notes,.results {{ padding:28px 0 44px; }}
    .result-section,.manual-form {{ margin-top:26px; }}
    .section-title {{ display:flex; justify-content:space-between; gap:16px; margin-bottom:10px; }}
    .section-title span,.section-note,.empty {{ color:var(--muted); }}
    .table-wrap {{ overflow-x:auto; border:1px solid var(--line); border-radius:6px; margin-top:10px; }}
    table {{ width:100%; min-width:980px; border-collapse:collapse; }}
    .detail table {{ min-width:720px; }}
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
    @media (max-width:760px) {{ .form-grid {{ grid-template-columns:1fr; }} h1 {{ font-size:28px; }} .section-title {{ display:block; }} table {{ min-width:860px; }} }}
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


def _merge_query(raw_query: str, updates: dict[str, str]) -> str:
    params = parse_qs(raw_query, keep_blank_values=True)
    for key, value in updates.items():
        params[key] = [value]
    return urlencode(params, doseq=True)


def _strip_query_keys(raw_query: str, keys: set[str]) -> str:
    params = parse_qs(raw_query, keep_blank_values=True)
    for key in keys:
        params.pop(key, None)
    return urlencode(params, doseq=True)


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
