from __future__ import annotations

import asyncio
import os
import shutil
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from fastapi.responses import FileResponse

import workspace_server as workspace

HERE = Path(__file__).resolve().parent
MANAGED_ROOT = Path.home() / ".qira-grok-ops" / "workspace"
MANAGED_ROOT.mkdir(parents=True, exist_ok=True)

_base_workspace_root = workspace.workspace_root


def active_workspace_root() -> Path:
    """Use a real detected workspace when it contains projects; otherwise use our managed root."""
    configured = workspace.load_config().get("workspace_root", "")
    if configured:
        configured_path = Path(configured).expanduser().resolve()
        if configured_path.is_dir():
            return configured_path

    detected = _base_workspace_root()
    if detected.is_dir() and workspace.project_matches(detected) > 0:
        return detected
    return MANAGED_ROOT


# Make all existing path resolution use the managed fallback.
workspace.workspace_root = active_workspace_root
workspace.core.project_path = workspace.project_path
workspace.core.ROOT = active_workspace_root()
app = workspace.app


def project_by_id(project_id: str) -> dict[str, Any]:
    project = next((item for item in workspace.core.defs() if item["id"] == project_id), None)
    if not project:
        raise HTTPException(404, "Unknown project")
    return project


def destination_for(project: dict[str, Any]) -> Path:
    existing = workspace.project_path(project)
    if existing.exists():
        return existing

    repo = project.get("repo")
    if repo:
        repo_name = repo.rsplit("/", 1)[-1]
        return (active_workspace_root() / repo_name).resolve()

    candidates = project.get("folder_candidates") or [project["id"]]
    return (active_workspace_root() / candidates[0]).resolve()


async def execute(command: list[str], timeout: int = 1200) -> tuple[int, str]:
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        env=env,
    )
    try:
        output, _ = await asyncio.wait_for(process.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
        return 124, f"Timed out after {timeout} seconds: {' '.join(command)}"
    return process.returncode or 0, output.decode(errors="replace").strip()


def safe_remove_partial(destination: Path) -> None:
    if not destination.exists() or (destination / ".git").exists():
        return
    allowed_roots = {active_workspace_root().resolve(), MANAGED_ROOT.resolve()}
    resolved = destination.resolve()
    if not any(root == resolved.parent or root in resolved.parents for root in allowed_roots):
        raise RuntimeError(f"Refusing to remove partial clone outside managed workspace: {resolved}")
    shutil.rmtree(destination)


async def ensure_checkout(project: dict[str, Any]) -> tuple[Path, bool, str]:
    """Return a usable local directory, cloning a GitHub repository when necessary."""
    destination = destination_for(project)
    if destination.is_dir() and (destination / ".git").exists():
        return destination, False, "Repository already available"

    if project.get("workspace_root"):
        destination.mkdir(parents=True, exist_ok=True)
        return destination, False, "Managed portfolio workspace ready"

    repo = project.get("repo")
    if not repo:
        raise HTTPException(
            409,
            f"{project['name']} has no GitHub repository mapping yet. Use its exact local folder path in workspace settings.",
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and any(destination.iterdir()):
        raise HTTPException(409, f"Clone destination already exists and is not an empty Git repository: {destination}")

    attempts: list[tuple[str, list[str]]] = []
    if shutil.which("gh"):
        attempts.append(("GitHub CLI", ["gh", "repo", "clone", repo, str(destination), "--", "--depth", "1"]))
    attempts.extend(
        [
            ("SSH", ["git", "clone", "--depth", "1", f"git@github.com:{repo}.git", str(destination)]),
            ("HTTPS", ["git", "clone", "--depth", "1", f"https://github.com/{repo}.git", str(destination)]),
        ]
    )

    failures: list[str] = []
    for method, command in attempts:
        safe_remove_partial(destination)
        code, output = await execute(command)
        if code == 0 and (destination / ".git").exists():
            config = workspace.load_config()
            config.setdefault("project_paths", {})[project["id"]] = str(destination)
            if not config.get("workspace_root"):
                config["workspace_root"] = str(active_workspace_root())
            workspace.save_config(config)
            workspace.core.ROOT = active_workspace_root()
            return destination, True, f"Cloned with {method}"
        failures.append(f"{method}: {output[-1200:] if output else f'exit {code}'}")

    safe_remove_partial(destination)
    raise HTTPException(
        500,
        "Unable to clone the repository. Private repositories require GitHub authentication on this Mac. "
        + " | ".join(failures),
    )


# Replace the first-run setup redirect. The managed workspace means the control board can always open.
app.router.routes = [
    route
    for route in app.router.routes
    if not (getattr(route, "path", None) == "/" and "GET" in getattr(route, "methods", set()))
]


@app.get("/")
async def managed_index():
    return FileResponse(HERE / "managed_index.html")


@app.post("/api/projects/{project_id}/clone")
async def clone_project(project_id: str):
    if workspace.core.SESSIONS:
        raise HTTPException(409, "Stop active Grok sessions before cloning another project")
    project = project_by_id(project_id)
    path, cloned, message = await ensure_checkout(project)
    return {"ok": True, "path": str(path), "cloned": cloned, "message": message}


# Replace POST /api/sessions so checkout preparation happens before ACP startup.
app.router.routes = [
    route
    for route in app.router.routes
    if not (
        getattr(route, "path", None) == "/api/sessions"
        and "POST" in getattr(route, "methods", set())
    )
]


@app.post("/api/sessions")
async def new_managed_session(data: workspace.core.NewSession):
    project = project_by_id(data.project_id)
    path, cloned, preparation = await ensure_checkout(project)

    agent = workspace.core.Agent(project, data.approval_mode, data.model, data.effort)
    workspace.core.SESSIONS[agent.id] = agent
    try:
        await agent.start()
    except Exception as exc:
        await agent.stop()
        workspace.core.SESSIONS.pop(agent.id, None)
        raise HTTPException(500, str(exc)) from exc

    return {
        "id": agent.id,
        "state": agent.state,
        "project_id": project["id"],
        "root": str(path),
        "cloned": cloned,
        "preparation": preparation,
    }
