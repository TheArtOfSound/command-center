from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

import server as core

HERE = Path(__file__).resolve().parent
CONFIG_DIR = Path.home() / ".qira-grok-ops"
CONFIG_FILE = CONFIG_DIR / "config.json"


def load_config() -> dict[str, Any]:
    if not CONFIG_FILE.exists():
        return {"workspace_root": "", "project_paths": {}}
    try:
        data = json.loads(CONFIG_FILE.read_text())
        if not isinstance(data, dict):
            raise ValueError("config must be an object")
        data.setdefault("workspace_root", "")
        data.setdefault("project_paths", {})
        return data
    except Exception:
        return {"workspace_root": "", "project_paths": {}}


def save_config(config: dict[str, Any]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    temporary = CONFIG_FILE.with_suffix(".tmp")
    temporary.write_text(json.dumps(config, indent=2) + "\n")
    temporary.replace(CONFIG_FILE)


def folder_names() -> set[str]:
    names: set[str] = set()
    for project in core.defs():
        names.update(str(name) for name in project.get("folder_candidates", []) if name)
    return names


def candidate_roots() -> list[Path]:
    config = load_config()
    raw = [
        os.getenv("QIRA_WORKSPACE_ROOT", ""),
        config.get("workspace_root", ""),
        str(HERE.parent.parent),
        str(Path.cwd()),
        str(Path.cwd().parent),
        str(Path.cwd().parent.parent),
        "~/Documents/GitHub",
        "~/GitHub",
        "~/Developer",
        "~/Projects",
        "~/Documents/Projects",
        "~/Desktop/GitHub",
    ]
    output: list[Path] = []
    seen: set[str] = set()
    for value in raw:
        if not value:
            continue
        path = Path(value).expanduser().resolve()
        if str(path) not in seen:
            output.append(path)
            seen.add(str(path))
    return output


def project_matches(root: Path) -> int:
    if not root.is_dir():
        return 0
    expected = {name.lower() for name in folder_names()}
    matches = 0
    try:
        children = [path for path in root.iterdir() if path.is_dir() and not path.name.startswith(".")]
    except OSError:
        return 0
    for child in children:
        if child.name.lower() in expected:
            matches += 1
        try:
            nested = [path for path in child.iterdir() if path.is_dir() and not path.name.startswith(".")]
        except OSError:
            nested = []
        matches += sum(1 for path in nested if path.name.lower() in expected)
    return matches


def workspace_root() -> Path:
    config = load_config()
    explicit = [os.getenv("QIRA_WORKSPACE_ROOT", ""), config.get("workspace_root", "")]
    for value in explicit:
        if value:
            path = Path(value).expanduser().resolve()
            if path.is_dir():
                return path
    existing = [path for path in candidate_roots() if path.is_dir()]
    if not existing:
        return Path("~/Documents/GitHub").expanduser().resolve()
    return max(existing, key=lambda path: (project_matches(path), path == HERE.parent.parent))


def resolve_project(root: Path, choices: list[str]) -> Path | None:
    if not root.is_dir():
        return None
    expected = {choice.lower() for choice in choices}
    try:
        children = [path for path in root.iterdir() if path.is_dir() and not path.name.startswith(".")]
    except OSError:
        return None
    for child in children:
        if child.name.lower() in expected:
            return child.resolve()
    for parent in children:
        try:
            nested = [path for path in parent.iterdir() if path.is_dir() and not path.name.startswith(".")]
        except OSError:
            continue
        for child in nested:
            if child.name.lower() in expected:
                return child.resolve()
    return None


def project_path(project: dict[str, Any]) -> Path:
    environment_name = project.get("path_env")
    if environment_name and os.getenv(environment_name):
        return Path(os.environ[environment_name]).expanduser().resolve()

    config = load_config()
    override = config.get("project_paths", {}).get(project["id"])
    if override:
        return Path(override).expanduser().resolve()

    root = workspace_root()
    if project.get("workspace_root"):
        return root
    choices = [str(value) for value in (project.get("folder_candidates") or [project.get("folder")]) if value]
    resolved = resolve_project(root, choices)
    return resolved or (root / (choices[0] if choices else project["id"])).resolve()


# Replace the first version's fixed path resolver without disturbing its ACP runtime.
core.project_path = project_path
core.ROOT = workspace_root()
app = core.app

# Replace the original index route so first run can configure the local workspace.
app.router.routes = [
    route
    for route in app.router.routes
    if not (getattr(route, "path", None) == "/" and "GET" in getattr(route, "methods", set()))
]


class ConfigUpdate(BaseModel):
    workspace_root: str = Field(min_length=1, max_length=4096)


class ProjectPathUpdate(BaseModel):
    path: str = Field(min_length=1, max_length=4096)


def config_payload() -> dict[str, Any]:
    root = workspace_root()
    candidates = [
        {
            "path": str(path),
            "exists": path.is_dir(),
            "project_matches": project_matches(path),
            "selected": path == root,
        }
        for path in candidate_roots()
    ]
    return {
        "workspace_root": str(root),
        "workspace_exists": root.is_dir(),
        "project_matches": project_matches(root),
        "config_file": str(CONFIG_FILE),
        "candidates": candidates,
        "project_paths": load_config().get("project_paths", {}),
    }


@app.get("/")
async def configured_index():
    config = load_config()
    root = workspace_root()
    if not config.get("workspace_root") and project_matches(root) == 0:
        return FileResponse(HERE / "setup.html")
    return FileResponse(HERE / "index.html")


@app.get("/api/config")
async def get_config():
    return config_payload()


@app.post("/api/config")
async def update_config(data: ConfigUpdate):
    if core.SESSIONS:
        raise HTTPException(409, "Stop active Grok sessions before changing the workspace")
    root = Path(data.workspace_root).expanduser().resolve()
    if not root.is_dir():
        raise HTTPException(400, f"Folder does not exist: {root}")
    config = load_config()
    config["workspace_root"] = str(root)
    save_config(config)
    core.ROOT = root
    return config_payload()


@app.post("/api/projects/{project_id}/path")
async def update_project_path(project_id: str, data: ProjectPathUpdate):
    if core.SESSIONS:
        raise HTTPException(409, "Stop active Grok sessions before changing project paths")
    if not any(project["id"] == project_id for project in core.defs()):
        raise HTTPException(404, "Unknown project")
    path = Path(data.path).expanduser().resolve()
    if not path.is_dir():
        raise HTTPException(400, f"Folder does not exist: {path}")
    config = load_config()
    config.setdefault("project_paths", {})[project_id] = str(path)
    save_config(config)
    return {"ok": True, "project_id": project_id, "path": str(path)}


@app.delete("/api/projects/{project_id}/path")
async def clear_project_path(project_id: str):
    if core.SESSIONS:
        raise HTTPException(409, "Stop active Grok sessions before changing project paths")
    config = load_config()
    config.setdefault("project_paths", {}).pop(project_id, None)
    save_config(config)
    return {"ok": True}
