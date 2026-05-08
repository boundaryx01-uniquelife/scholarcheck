from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from scholarcheck.models import SearchQuery, SearchResult, UNKNOWN
from scholarcheck.sessions import DEFAULT_SESSION_DIR, load_search_session, resolve_session_path


DEFAULT_PROJECT_DIR = Path("data") / "projects"


@dataclass(slots=True)
class ResearchProject:
    project_id: str
    name: str
    description: str = ""
    session_ids: list[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""


def create_project(
    name: str,
    *,
    description: str = "",
    session_ids: list[str] | None = None,
    project_dir: Path = DEFAULT_PROJECT_DIR,
) -> Path:
    project_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat()
    project = ResearchProject(
        project_id=_build_project_id(name, timestamp),
        name=name.strip() or "Untitled Project",
        description=description.strip(),
        session_ids=_dedupe_session_ids(session_ids or []),
        created_at=timestamp,
        updated_at=timestamp,
    )
    path = project_dir / f"{project.project_id}.json"
    _write_project(project, path)
    return path


def load_project(path: Path) -> ResearchProject:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return ResearchProject(
        project_id=str(payload.get("project_id", path.stem)),
        name=str(payload.get("name", UNKNOWN)),
        description=str(payload.get("description", "")),
        session_ids=_dedupe_session_ids(payload.get("session_ids", [])),
        created_at=str(payload.get("created_at", UNKNOWN)),
        updated_at=str(payload.get("updated_at", UNKNOWN)),
    )


def list_projects(project_dir: Path = DEFAULT_PROJECT_DIR) -> list[Path]:
    if not project_dir.exists():
        return []
    return sorted(project_dir.glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True)


def resolve_project_path(project_id: str, project_dir: Path = DEFAULT_PROJECT_DIR) -> Path:
    safe_id = re.sub(r"[^0-9A-Za-z_.-]", "", project_id)
    if not safe_id:
        raise ValueError("Project id is required.")
    path = project_dir / f"{safe_id}.json"
    if not path.exists():
        raise FileNotFoundError(path)
    return path


def add_session_to_project(
    project_id: str,
    session_id: str,
    *,
    project_dir: Path = DEFAULT_PROJECT_DIR,
) -> ResearchProject:
    path = resolve_project_path(project_id, project_dir)
    project = load_project(path)
    session_ids = _dedupe_session_ids([*project.session_ids, session_id])
    project.session_ids = session_ids
    project.updated_at = datetime.now(timezone.utc).isoformat()
    _write_project(project, path)
    return project


def load_project_sessions(
    project: ResearchProject,
    session_dir: Path = DEFAULT_SESSION_DIR,
) -> list[tuple[dict[str, str], SearchQuery, SearchResult]]:
    sessions = []
    for session_id in project.session_ids:
        try:
            sessions.append(load_search_session(resolve_session_path(session_id, session_dir)))
        except (FileNotFoundError, ValueError, json.JSONDecodeError):
            continue
    return sessions


def project_to_json(project: ResearchProject) -> str:
    return json.dumps(
        {
            "schema_version": 1,
            **asdict(project),
            "data_policy": (
                "Project files reference saved search sessions. They do not mutate session source data "
                "or merge domestic manual records into verified paper records."
            ),
        },
        ensure_ascii=False,
        indent=2,
    )


def _write_project(project: ResearchProject, path: Path) -> None:
    path.write_text(project_to_json(project), encoding="utf-8")


def _build_project_id(name: str, timestamp: str) -> str:
    compact_time = timestamp.replace("-", "").replace(":", "").split(".")[0].replace("+", "Z")
    slug = re.sub(r"[^0-9A-Za-z]+", "-", name.strip().lower()).strip("-")[:48]
    return f"{compact_time}-{slug or 'project'}"


def _dedupe_session_ids(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    seen: set[str] = set()
    session_ids = []
    for item in value:
        session_id = re.sub(r"[^0-9A-Za-z_.-]", "", str(item))
        if session_id and session_id not in seen:
            seen.add(session_id)
            session_ids.append(session_id)
    return session_ids
