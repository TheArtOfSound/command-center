"""Qira Command Center — GitHub Intelligence Service.

Scans all of Bryan's GitHub repositories, analyzes them with Claude,
and stores intelligence in the command center database.

Uses the `gh` CLI (already authenticated) for API calls.
"""

import json
import sqlite3
import subprocess
import asyncio
from datetime import datetime
from pathlib import Path

import anthropic

DB_PATH = Path.home() / "qira" / "command_center" / "data" / "nucleus.db"
GITHUB_USERNAME = "TheArtOfSound"

claude = anthropic.Anthropic()

KNOWN_REPOS = {
    "egcstudy": "EGC", "thegate": "EGC",
    "codey": "Codey", "lolm": "LOLM", "nfet": "NFET",
    "command-center": "System", "portfolio": "System",
}


# ── GH CLI WRAPPER ────────────────────────────────────────────

def gh_api(endpoint: str, params: dict = None):
    """Call GitHub API via gh CLI (already authenticated)."""
    cmd = ["gh", "api", endpoint]
    if params:
        for k, v in params.items():
            cmd.extend(["-f", f"{k}={v}"])
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return json.loads(result.stdout)
        return {}
    except Exception as e:
        print(f"[GITHUB] Error calling {endpoint}: {e}")
        return {}


def gh_api_paginate(endpoint: str) -> list:
    """Paginate through GitHub API results."""
    cmd = ["gh", "api", endpoint, "--paginate"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            # gh --paginate may return concatenated JSON arrays
            text = result.stdout.strip()
            if text.startswith("["):
                # Try to parse; may need to handle multiple arrays
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    # Multiple arrays concatenated
                    items = []
                    for chunk in text.replace("][", "]\n[").split("\n"):
                        if chunk.strip():
                            items.extend(json.loads(chunk))
                    return items
            return []
        return []
    except Exception as e:
        print(f"[GITHUB] Paginate error {endpoint}: {e}")
        return []


# ── ENSURE TABLES ─────────────────────────────────────────────

def ensure_github_tables():
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS github_repos (
        id TEXT PRIMARY KEY, full_name TEXT UNIQUE, name TEXT,
        description TEXT, private INTEGER, language TEXT,
        tech_stack TEXT, project TEXT, status TEXT,
        health INTEGER DEFAULT 5, file_count INTEGER DEFAULT 0,
        commit_count INTEGER DEFAULT 0, open_issues INTEGER DEFAULT 0,
        last_commit TEXT, readme_preview TEXT, claude_md TEXT,
        ai_analysis TEXT, file_tree TEXT, key_files TEXT,
        workflows TEXT, scanned_at TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS github_commits (
        id TEXT PRIMARY KEY, repo TEXT, sha TEXT,
        message TEXT, author TEXT, date TEXT, project TEXT
    )""")
    conn.commit()
    conn.close()


# ── SCAN ──────────────────────────────────────────────────────

def scan_all_repos() -> list:
    """Scan every repo Bryan owns."""
    ensure_github_tables()
    print("[GITHUB] Starting full repository scan...")

    repos = gh_api_paginate(f"/users/{GITHUB_USERNAME}/repos?sort=updated&per_page=100")
    if not repos:
        # Try authenticated endpoint
        repos = gh_api_paginate("/user/repos?type=all&sort=updated&per_page=100")

    if not isinstance(repos, list):
        print("[GITHUB] No repos found")
        return []

    print(f"[GITHUB] Found {len(repos)} repositories")
    results = []

    for repo in repos:
        name = repo.get("name", "")
        full_name = repo.get("full_name", "")
        print(f"  Scanning: {full_name}")

        data = scan_single_repo(repo)
        save_repo_to_db(data)
        results.append(data)

    print(f"[GITHUB] Scan complete. {len(results)} repos analyzed.")
    return results


def scan_single_repo(repo: dict) -> dict:
    """Deep scan a single repo."""
    full_name = repo.get("full_name", "")
    name = repo.get("name", "")
    branch = repo.get("default_branch", "main")

    data = {
        "name": name,
        "full_name": full_name,
        "description": repo.get("description", "") or "",
        "private": repo.get("private", False),
        "language": repo.get("language", "") or "",
        "stars": repo.get("stargazers_count", 0),
        "size": repo.get("size", 0),
        "created_at": repo.get("created_at", ""),
        "updated_at": repo.get("updated_at", ""),
        "pushed_at": repo.get("pushed_at", ""),
        "default_branch": branch,
        "topics": repo.get("topics", []),
        "project": KNOWN_REPOS.get(name, "Unknown"),
        "tech_stack": [],
        "commits": [],
        "file_tree": [],
        "readme": "",
        "claude_md": "",
        "key_files": {},
        "issues": [],
        "workflows": [],
        "ai_analysis": {},
    }

    # Languages
    langs = gh_api(f"/repos/{full_name}/languages")
    if isinstance(langs, dict) and langs:
        total = sum(langs.values())
        data["tech_stack"] = [
            f"{lang} {round(b / total * 100)}%"
            for lang, b in sorted(langs.items(), key=lambda x: -x[1])[:5]
        ]

    # Recent commits
    commits = gh_api(f"/repos/{full_name}/commits?per_page=30")
    if isinstance(commits, list):
        data["commits"] = [
            {
                "sha": c["sha"][:8],
                "message": c["commit"]["message"].split("\n")[0][:100],
                "author": c["commit"]["author"]["name"],
                "date": c["commit"]["author"]["date"],
            }
            for c in commits[:30]
        ]

    # File tree
    tree = gh_api(f"/repos/{full_name}/git/trees/{branch}?recursive=1")
    if isinstance(tree, dict) and tree.get("tree"):
        data["file_tree"] = [
            item["path"] for item in tree["tree"]
            if item["type"] == "blob"
        ][:200]

    # README
    readme = gh_api(f"/repos/{full_name}/readme")
    if isinstance(readme, dict) and readme.get("content"):
        import base64
        try:
            data["readme"] = base64.b64decode(readme["content"]).decode("utf-8", errors="ignore")[:3000]
        except:
            pass

    # CLAUDE.md
    if "CLAUDE.md" in data["file_tree"]:
        cfile = gh_api(f"/repos/{full_name}/contents/CLAUDE.md?ref={branch}")
        if isinstance(cfile, dict) and cfile.get("content"):
            import base64
            try:
                data["claude_md"] = base64.b64decode(cfile["content"]).decode("utf-8", errors="ignore")[:2000]
            except:
                pass

    # Open issues
    issues = gh_api(f"/repos/{full_name}/issues?state=open&per_page=20")
    if isinstance(issues, list):
        data["issues"] = [
            {"number": i["number"], "title": i["title"], "state": i["state"],
             "created_at": i.get("created_at", "")}
            for i in issues[:20]
        ]

    # Workflows
    wf = gh_api(f"/repos/{full_name}/actions/workflows")
    if isinstance(wf, dict) and wf.get("workflows"):
        data["workflows"] = [{"name": w["name"], "state": w["state"]} for w in wf["workflows"]]

    # AI analysis (use Haiku for speed)
    data["ai_analysis"] = analyze_repo(data)

    return data


def analyze_repo(data: dict) -> dict:
    """Quick Claude analysis of a repo."""
    try:
        ctx = f"""Repo: {data['full_name']}
Desc: {data['description']}
Lang: {data['language']} | Stack: {', '.join(data['tech_stack'])}
Files: {len(data['file_tree'])} | Commits: {len(data['commits'])}
Open issues: {len(data['issues'])}
Recent commits: {'; '.join(c['message'] for c in data['commits'][:5])}
File sample: {', '.join(data['file_tree'][:15])}
README: {data['readme'][:500]}"""

        resp = claude.messages.create(
            model="claude-haiku-4-5-20251001", max_tokens=400,
            messages=[{"role": "user", "content": f"""Analyze this repo briefly. JSON only:
{ctx}
{{"purpose":"one sentence","status":"active|stale|complete","health":1-10,"next_action":"one sentence","project":"EGC|LOLM|Codey|NFET|System|Unknown","priority":1-10}}"""}]
        )
        text = resp.content[0].text.strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text)
    except:
        return {"purpose": data["description"], "status": "unknown", "health": 5,
                "next_action": "Review", "project": data["project"], "priority": 5}


def save_repo_to_db(data: dict):
    """Save repo intel to database."""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    a = data.get("ai_analysis", {})

    c.execute("""INSERT OR REPLACE INTO github_repos
        (id, full_name, name, description, private, language, tech_stack,
         project, status, health, file_count, commit_count, open_issues,
         last_commit, readme_preview, claude_md, ai_analysis, file_tree,
         key_files, workflows, scanned_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (data["full_name"].replace("/", "_"), data["full_name"], data["name"],
         data["description"], 1 if data["private"] else 0, data["language"],
         json.dumps(data["tech_stack"]),
         a.get("project", data["project"]), a.get("status", "unknown"),
         a.get("health", 5), len(data["file_tree"]), len(data["commits"]),
         len(data["issues"]),
         data["commits"][0]["date"] if data["commits"] else "",
         data["readme"][:500], data["claude_md"][:2000],
         json.dumps(a), json.dumps(data["file_tree"][:100]),
         json.dumps(data.get("key_files", {})),
         json.dumps(data["workflows"]), datetime.now().isoformat()))

    for commit in data["commits"]:
        cid = f"{data['full_name']}_{commit['sha']}"
        c.execute("INSERT OR IGNORE INTO github_commits VALUES (?,?,?,?,?,?,?)",
                  (cid, data["full_name"], commit["sha"], commit["message"],
                   commit["author"], commit["date"], a.get("project", "Unknown")))

    conn.commit()
    conn.close()


# ── QUERY FUNCTIONS ───────────────────────────────────────────

def get_all_repos():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM github_repos ORDER BY health DESC")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_recent_commits(limit=50):
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM github_commits ORDER BY date DESC LIMIT ?", (limit,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_repo(name):
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM github_repos WHERE name = ? OR full_name = ?", (name, name))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None
