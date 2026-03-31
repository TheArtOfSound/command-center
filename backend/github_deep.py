"""Qira Command Center -- GitHub Deep Scanner.

Full repository content indexing and AI analysis.
Uses `gh` CLI (already authenticated as TheArtOfSound) for all GitHub API calls.
"""

from __future__ import annotations

import base64
import json
import re
import sqlite3
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from ai_client import chat as ai_chat

DB_PATH = Path.home() / "qira" / "command_center" / "data" / "nucleus.db"
GITHUB_USERNAME = "TheArtOfSound"

# File extensions to index
INDEXABLE_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".md", ".json", ".yaml", ".yml",
    ".sql", ".sh", ".html", ".css", ".jsx", ".toml", ".cfg", ".ini",
    ".env.example", ".txt", ".rst", ".r", ".R",
}

# Directories to skip
SKIP_DIRS = {
    "node_modules", ".git", "dist", "build", "__pycache__", "venv",
    ".venv", "env", ".env", ".next", ".nuxt", "vendor", "coverage",
    ".mypy_cache", ".pytest_cache", ".tox", "egg-info",
}

MAX_FILE_SIZE = 500 * 1024  # 500KB

# Rate limiting state
_api_calls_since_check = 0


# ── DATABASE ─────────────────────────────────────────────────────

def _get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _query(sql, params=(), one=False):
    conn = _get_db()
    c = conn.cursor()
    c.execute(sql, params)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows[0] if one and rows else rows if not one else None


def _execute(sql, params=()):
    conn = _get_db()
    c = conn.cursor()
    c.execute(sql, params)
    conn.commit()
    conn.close()


def _executemany(sql, param_list):
    conn = _get_db()
    c = conn.cursor()
    c.executemany(sql, param_list)
    conn.commit()
    conn.close()


def init_deep_tables():
    """Create the deep scan tables if they don't exist."""
    conn = _get_db()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS github_repos_deep (
        repo_full_name TEXT PRIMARY KEY,
        name TEXT,
        owner TEXT,
        description TEXT,
        language TEXT,
        stars INTEGER DEFAULT 0,
        forks INTEGER DEFAULT 0,
        open_issues INTEGER DEFAULT 0,
        default_branch TEXT DEFAULT 'main',
        is_private INTEGER DEFAULT 0,
        is_fork INTEGER DEFAULT 0,
        created_at TEXT,
        updated_at TEXT,
        pushed_at TEXT,
        size_kb INTEGER DEFAULT 0,
        topics TEXT DEFAULT '[]',
        file_count INTEGER DEFAULT 0,
        indexed_file_count INTEGER DEFAULT 0,
        project_tag TEXT,
        status TEXT,
        health_score INTEGER,
        what_it_does TEXT,
        current_state TEXT,
        blockers TEXT,
        next_action TEXT,
        nous_briefing TEXT,
        technical_stack TEXT,
        key_files TEXT DEFAULT '[]',
        last_scanned TEXT,
        last_analyzed TEXT,
        scan_duration_s REAL
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS github_files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        repo_full_name TEXT NOT NULL,
        file_path TEXT NOT NULL,
        extension TEXT,
        content TEXT,
        size INTEGER DEFAULT 0,
        sha TEXT,
        project_tag TEXT,
        importance INTEGER DEFAULT 5,
        summary TEXT,
        last_fetched TEXT,
        UNIQUE(repo_full_name, file_path)
    )""")
    c.execute("""CREATE INDEX IF NOT EXISTS idx_gf_repo ON github_files(repo_full_name)""")
    c.execute("""CREATE INDEX IF NOT EXISTS idx_gf_ext ON github_files(extension)""")
    c.execute("""CREATE INDEX IF NOT EXISTS idx_gf_path ON github_files(file_path)""")
    conn.commit()
    conn.close()
    print("[DEEP] Tables initialized")


# ── GH CLI ───────────────────────────────────────────────────────

def gh_api(endpoint: str, timeout: int = 30):
    """Call GitHub API via gh CLI."""
    global _api_calls_since_check
    _api_calls_since_check += 1
    try:
        result = subprocess.run(
            ["gh", "api", endpoint],
            capture_output=True, text=True, timeout=timeout
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
        print(f"[DEEP] gh api error for {endpoint}: {result.stderr[:200]}")
        return None
    except subprocess.TimeoutExpired:
        print(f"[DEEP] Timeout calling {endpoint}")
        return None
    except Exception as e:
        print(f"[DEEP] Error calling {endpoint}: {e}")
        return None


def check_rate_limit():
    """Check GitHub API rate limit. Returns (remaining, reset_timestamp)."""
    data = gh_api("/rate_limit")
    if not data:
        return 5000, 0
    core = data.get("resources", {}).get("core", {})
    remaining = core.get("remaining", 5000)
    reset_ts = core.get("reset", 0)
    print(f"[DEEP] Rate limit: {remaining} remaining, resets at {reset_ts}")
    return remaining, reset_ts


def enforce_rate_limit():
    """Check rate limit every 50 calls, sleep if needed."""
    global _api_calls_since_check
    if _api_calls_since_check >= 50:
        _api_calls_since_check = 0
        remaining, reset_ts = check_rate_limit()
        if remaining < 200:
            wait = max(0, reset_ts - time.time()) + 5
            print(f"[DEEP] Rate limit low ({remaining}), sleeping {wait:.0f}s")
            time.sleep(wait)


# ── CORE FUNCTIONS ───────────────────────────────────────────────

def get_all_repos() -> list[dict]:
    """Fetch all repos for the authenticated user."""
    page = 1
    all_repos = []
    while True:
        data = gh_api(f"/user/repos?type=all&per_page=100&page={page}&sort=pushed")
        if not data or not isinstance(data, list) or len(data) == 0:
            break
        all_repos.extend(data)
        if len(data) < 100:
            break
        page += 1
    print(f"[DEEP] Found {len(all_repos)} repos")
    return all_repos


def get_file_tree(repo_full_name: str, branch: str = "main") -> list[dict]:
    """Get recursive file tree for a repo."""
    data = gh_api(f"/repos/{repo_full_name}/git/trees/{branch}?recursive=1", timeout=60)
    if not data or "tree" not in data:
        # Try 'master' if 'main' fails
        if branch == "main":
            data = gh_api(f"/repos/{repo_full_name}/git/trees/master?recursive=1", timeout=60)
        if not data or "tree" not in data:
            return []
    return [item for item in data["tree"] if item.get("type") == "blob"]


def fetch_file_content(repo_full_name: str, file_path: str) -> tuple[str | None, str | None]:
    """Fetch a single file's content. Returns (content, sha)."""
    enforce_rate_limit()
    encoded_path = file_path.replace(" ", "%20")
    data = gh_api(f"/repos/{repo_full_name}/contents/{encoded_path}")
    if not data or "content" not in data:
        return None, None
    try:
        content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
        return content, data.get("sha")
    except Exception as e:
        print(f"[DEEP] Decode error for {repo_full_name}/{file_path}: {e}")
        return None, None


def _should_index(file_path: str, size: int) -> bool:
    """Decide if a file should be indexed."""
    if size > MAX_FILE_SIZE:
        return False
    parts = Path(file_path).parts
    for part in parts:
        if part in SKIP_DIRS:
            return False
    ext = Path(file_path).suffix.lower()
    name = Path(file_path).name.lower()
    # Also index dotfiles like Dockerfile, Makefile, etc.
    if name in {"dockerfile", "makefile", "procfile", ".gitignore", "requirements.txt",
                "package.json", "pyproject.toml", "cargo.toml", "go.mod", "gemfile"}:
        return True
    return ext in INDEXABLE_EXTENSIONS


def deep_scan_repo(repo: dict) -> dict:
    """Deep scan a single repo: fetch tree, filter, fetch contents, store in DB."""
    full_name = repo["full_name"]
    branch = repo.get("default_branch", "main")
    start = time.time()
    print(f"[DEEP] Scanning {full_name} (branch: {branch})...")

    # Get file tree
    tree = get_file_tree(full_name, branch)
    if not tree:
        print(f"[DEEP] No tree for {full_name}, skipping")
        return {"files_indexed": 0}

    # Filter indexable files
    indexable = [f for f in tree if _should_index(f["path"], f.get("size", 0))]
    total_files = len(tree)
    print(f"[DEEP] {full_name}: {total_files} total files, {len(indexable)} indexable")

    # Fetch contents
    files_data = []
    for item in indexable:
        content, sha = fetch_file_content(full_name, item["path"])
        if content is not None:
            ext = Path(item["path"]).suffix.lower()
            files_data.append({
                "repo_full_name": full_name,
                "file_path": item["path"],
                "extension": ext,
                "content": content,
                "size": item.get("size", 0),
                "sha": sha,
                "last_fetched": datetime.now().isoformat(),
            })
        # Small delay between fetches to be respectful
        time.sleep(0.1)

    # Store files in DB
    if files_data:
        conn = _get_db()
        c = conn.cursor()
        for f in files_data:
            c.execute("""INSERT OR REPLACE INTO github_files
                (repo_full_name, file_path, extension, content, size, sha, last_fetched)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (f["repo_full_name"], f["file_path"], f["extension"],
                 f["content"], f["size"], f["sha"], f["last_fetched"]))
        conn.commit()
        conn.close()

    # Store repo metadata
    duration = time.time() - start
    topics = json.dumps(repo.get("topics", []))
    _execute("""INSERT OR REPLACE INTO github_repos_deep
        (repo_full_name, name, owner, description, language, stars, forks,
         open_issues, default_branch, is_private, is_fork, created_at,
         updated_at, pushed_at, size_kb, topics, file_count,
         indexed_file_count, last_scanned, scan_duration_s)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (full_name, repo["name"], repo["owner"]["login"],
         repo.get("description", ""), repo.get("language", ""),
         repo.get("stargazers_count", 0), repo.get("forks_count", 0),
         repo.get("open_issues_count", 0), branch,
         1 if repo.get("private") else 0,
         1 if repo.get("fork") else 0,
         repo.get("created_at", ""), repo.get("updated_at", ""),
         repo.get("pushed_at", ""), repo.get("size", 0),
         topics, total_files, len(files_data),
         datetime.now().isoformat(), round(duration, 1)))

    print(f"[DEEP] {full_name}: indexed {len(files_data)} files in {duration:.1f}s")
    return {"files_indexed": len(files_data), "duration": duration}


def analyze_repo(repo_full_name: str) -> dict:
    """Use AI to analyze a repo based on its indexed files."""
    # Get repo metadata
    repo = _query("SELECT * FROM github_repos_deep WHERE repo_full_name = ?",
                  (repo_full_name,), one=True)
    if not repo:
        return {}

    # Get key files
    files = _query("""SELECT file_path, extension, size, content FROM github_files
        WHERE repo_full_name = ? ORDER BY
            CASE WHEN file_path LIKE '%README%' THEN 0
                 WHEN file_path LIKE '%main.%' OR file_path LIKE '%app.%' OR file_path LIKE '%index.%' THEN 1
                 WHEN file_path LIKE '%package.json' OR file_path LIKE '%pyproject.toml' OR file_path LIKE '%requirements.txt' THEN 2
                 WHEN extension = '.py' THEN 3
                 WHEN extension IN ('.js', '.ts', '.tsx') THEN 4
                 ELSE 5
            END, size DESC""",
        (repo_full_name,))

    if not files:
        return {}

    # Build manifest
    manifest = "\n".join([f"  {f['file_path']} ({f['size']}B)" for f in files])

    # Build key file contents (cap at ~3000 chars for fast local inference)
    key_contents = []
    chars = 0
    for f in files:
        content = f.get("content", "") or ""
        if chars + len(content) > 3000:
            # Truncate large files
            remaining = 3000 - chars
            if remaining > 200:
                key_contents.append(f"=== {f['file_path']} ===\n{content[:remaining]}\n[TRUNCATED]")
            break
        key_contents.append(f"=== {f['file_path']} ===\n{content}")
        chars += len(content)

    system = """You are an expert code analyst. Analyze this GitHub repository and return ONLY valid JSON.
The repo belongs to Bryan Leonard (TheArtOfSound), who works on: EGC (consciousness research),
LOLM (language models), Codey (AI coding SaaS), NFET (traffic optimization), and Qira Command Center.

Return this exact JSON structure:
{
    "project_tag": "one of: EGC, LOLM, Codey, NFET, System, Personal, Other",
    "status": "one of: active, stale, archived, experimental, infrastructure",
    "health_score": 1-10,
    "what_it_does": "1-2 sentence description",
    "current_state": "what state is the project in right now",
    "blockers": "any issues or blockers, or 'none'",
    "next_action": "what should Bryan do next with this repo",
    "nous_briefing": "2-3 sentence intelligence briefing for Bryan's AI assistant Nous",
    "technical_stack": "comma-separated list of key technologies"
}"""

    message = f"""Repository: {repo_full_name}
Description: {repo.get('description', 'None')}
Language: {repo.get('language', 'Unknown')}
Stars: {repo.get('stars', 0)} | Forks: {repo.get('forks', 0)} | Issues: {repo.get('open_issues', 0)}
Private: {'Yes' if repo.get('is_private') else 'No'}
Total files: {repo.get('file_count', 0)} | Indexed: {repo.get('indexed_file_count', 0)}
Topics: {repo.get('topics', '[]')}
Last pushed: {repo.get('pushed_at', 'Unknown')}

FILE MANIFEST:
{manifest}

KEY FILE CONTENTS:
{''.join(key_contents) if key_contents else 'No file contents available.'}"""

    print(f"[DEEP] Analyzing {repo_full_name}...")
    raw = ai_chat(system, message, 1500)

    # Parse JSON from response
    analysis = _parse_json(raw)
    if not analysis:
        print(f"[DEEP] Failed to parse analysis for {repo_full_name}")
        return {}

    # Update DB
    _execute("""UPDATE github_repos_deep SET
        project_tag = ?, status = ?, health_score = ?, what_it_does = ?,
        current_state = ?, blockers = ?, next_action = ?, nous_briefing = ?,
        technical_stack = ?, last_analyzed = ?
        WHERE repo_full_name = ?""",
        (analysis.get("project_tag", "Other"),
         analysis.get("status", "unknown"),
         analysis.get("health_score", 5),
         analysis.get("what_it_does", ""),
         analysis.get("current_state", ""),
         analysis.get("blockers", "none"),
         analysis.get("next_action", ""),
         analysis.get("nous_briefing", ""),
         analysis.get("technical_stack", ""),
         datetime.now().isoformat(),
         repo_full_name))

    # Also tag files with the project
    tag = analysis.get("project_tag", "Other")
    _execute("UPDATE github_files SET project_tag = ? WHERE repo_full_name = ?",
             (tag, repo_full_name))

    print(f"[DEEP] Analyzed {repo_full_name}: {tag} / {analysis.get('status')}")
    return analysis


def _parse_json(text: str) -> dict | None:
    """Extract JSON from AI response text."""
    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Try finding JSON in markdown code block
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    # Try finding any JSON object
    match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return None


# ── FULL SCAN ────────────────────────────────────────────────────

def full_scan():
    """Scan ALL repos: fetch contents + AI analysis. Sequential with delays."""
    init_deep_tables()
    print("[DEEP] === Starting full deep scan ===")
    start = time.time()

    repos = get_all_repos()
    if not repos:
        print("[DEEP] No repos found")
        return {"status": "no_repos"}

    results = []
    for i, repo in enumerate(repos):
        full_name = repo["full_name"]
        print(f"\n[DEEP] [{i+1}/{len(repos)}] {full_name}")

        try:
            scan_result = deep_scan_repo(repo)
        except Exception as e:
            print(f"[DEEP] Error scanning {full_name}: {e}")
            scan_result = {"error": str(e)}
            results.append({"repo": full_name, **scan_result})
            continue

        # AI analysis (only if we got files)
        if scan_result.get("files_indexed", 0) > 0:
            try:
                analysis = analyze_repo(full_name)
                scan_result["analysis"] = analysis
            except Exception as e:
                print(f"[DEEP] Error analyzing {full_name}: {e}")
                scan_result["analysis_error"] = str(e)

        results.append({"repo": full_name, **scan_result})

        # Rate limiter + courtesy delay
        time.sleep(1)

    duration = time.time() - start
    total_files = sum(r.get("files_indexed", 0) for r in results)
    print(f"\n[DEEP] === Full scan complete: {len(repos)} repos, {total_files} files, {duration:.0f}s ===")
    return {
        "status": "complete",
        "repos_scanned": len(repos),
        "total_files_indexed": total_files,
        "duration_seconds": round(duration, 1),
        "results": results,
    }


# ── CONTEXT BUILDER ──────────────────────────────────────────────

def build_live_repo_context() -> str:
    """Build a formatted string of all repo intelligence for Nous context injection."""
    init_deep_tables()
    repos = _query("""SELECT * FROM github_repos_deep
        WHERE last_analyzed IS NOT NULL
        ORDER BY
            CASE project_tag
                WHEN 'EGC' THEN 0
                WHEN 'LOLM' THEN 1
                WHEN 'Codey' THEN 2
                WHEN 'NFET' THEN 3
                WHEN 'System' THEN 4
                ELSE 5
            END, pushed_at DESC""")

    if not repos:
        return "No deeply scanned repositories available. Run /api/github/deep/scan first."

    lines = ["=== GITHUB REPOSITORY INTELLIGENCE ===", ""]
    by_project = {}
    for r in repos:
        tag = r.get("project_tag") or "Other"
        by_project.setdefault(tag, []).append(r)

    for tag, tag_repos in by_project.items():
        lines.append(f"## {tag}")
        for r in tag_repos:
            name = r["repo_full_name"]
            status = r.get("status", "?")
            health = r.get("health_score", "?")
            briefing = r.get("nous_briefing", "No briefing")
            stack = r.get("technical_stack", "")
            next_act = r.get("next_action", "")
            lines.append(f"  [{name}] status={status} health={health}/10")
            lines.append(f"    {briefing}")
            if stack:
                lines.append(f"    Stack: {stack}")
            if next_act:
                lines.append(f"    Next: {next_act}")
            lines.append("")

    return "\n".join(lines)


# ── SEARCH ───────────────────────────────────────────────────────

def search_code(query_text: str, limit: int = 10) -> list[dict]:
    """Full text search across all indexed files. Returns matches with context."""
    init_deep_tables()
    if not query_text or len(query_text) < 2:
        return []

    # SQLite LIKE search (case-insensitive)
    pattern = f"%{query_text}%"
    rows = _query("""SELECT repo_full_name, file_path, extension, content, size, project_tag
        FROM github_files
        WHERE content LIKE ?
        ORDER BY
            CASE WHEN file_path LIKE ? THEN 0 ELSE 1 END,
            size ASC
        LIMIT ?""",
        (pattern, pattern, limit * 3))  # Fetch more, we'll trim after extracting context

    results = []
    for row in rows:
        content = row.get("content", "") or ""
        # Find matching lines with context
        matches = _extract_matches(content, query_text, context_lines=3)
        if matches:
            results.append({
                "repo": row["repo_full_name"],
                "file_path": row["file_path"],
                "extension": row["extension"],
                "size": row["size"],
                "project_tag": row.get("project_tag"),
                "matches": matches[:3],  # Top 3 match locations per file
            })
        if len(results) >= limit:
            break

    return results


def _extract_matches(content: str, query_text: str, context_lines: int = 3) -> list[dict]:
    """Extract matching lines with surrounding context."""
    lines = content.split("\n")
    query_lower = query_text.lower()
    matches = []
    seen_ranges = set()

    for i, line in enumerate(lines):
        if query_lower in line.lower():
            start = max(0, i - context_lines)
            end = min(len(lines), i + context_lines + 1)
            range_key = (start, end)
            if range_key in seen_ranges:
                continue
            seen_ranges.add(range_key)
            context = "\n".join(f"{start+j+1:4d} | {lines[start+j]}" for j in range(end - start))
            matches.append({
                "line_number": i + 1,
                "context": context,
            })
    return matches


# ── PUBLIC QUERY FUNCTIONS ───────────────────────────────────────

def get_deep_repos() -> list[dict]:
    """Get all deeply scanned repos."""
    init_deep_tables()
    return _query("""SELECT repo_full_name, name, owner, description, language,
        stars, forks, open_issues, default_branch, is_private, is_fork,
        created_at, updated_at, pushed_at, size_kb, topics,
        file_count, indexed_file_count, project_tag, status, health_score,
        what_it_does, current_state, blockers, next_action, nous_briefing,
        technical_stack, key_files, last_scanned, last_analyzed
        FROM github_repos_deep ORDER BY pushed_at DESC""")


def get_deep_repo(name: str) -> dict | None:
    """Get one deeply scanned repo by name (partial match on full_name)."""
    init_deep_tables()
    return _query("""SELECT * FROM github_repos_deep
        WHERE repo_full_name LIKE ? OR name = ?
        ORDER BY pushed_at DESC LIMIT 1""",
        (f"%{name}%", name), one=True)


def get_repo_files(repo_full_name: str) -> list[dict]:
    """List all indexed files for a repo."""
    init_deep_tables()
    return _query("""SELECT file_path, extension, size, sha, project_tag,
        importance, summary, last_fetched
        FROM github_files WHERE repo_full_name LIKE ?
        ORDER BY file_path""",
        (f"%{repo_full_name}%",))


def get_file_content(repo_full_name: str, file_path: str) -> dict | None:
    """Get a specific file's content."""
    init_deep_tables()
    return _query("""SELECT * FROM github_files
        WHERE repo_full_name LIKE ? AND file_path = ?""",
        (f"%{repo_full_name}%", file_path), one=True)
