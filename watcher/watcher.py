"""Qira Command Center — Local Filesystem Watcher.

Watches Bryan's machine for file changes and auto-indexes them
into the command center database with project tagging, importance
scoring, and action item extraction.

Usage: python3 watcher.py
"""

import os
import time
import json
import sqlite3
import hashlib
import threading
from pathlib import Path
from datetime import datetime
from collections import deque

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

import anthropic
import httpx

# ── CONFIG ────────────────────────────────────────────────────
DB_PATH = Path.home() / "qira" / "command_center" / "data" / "nucleus.db"
API_URL = "http://localhost:7777"

# Load API key
env_path = Path.home() / "qira" / "command_center" / ".env"
API_KEY = ""
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if line.startswith("QIRA_API_KEY="):
            API_KEY = line.split("=", 1)[1].strip()

WATCH_PATHS = [
    Path.home() / "Downloads",
    Path.home() / "Desktop",
    Path.home() / "Documents",
    Path.home() / "qira",
    Path.home() / "egcstudy",
    Path.home() / "thegate",
    Path.home() / "nous",
    Path.home() / "BRYAN",
]

WATCH_EXTENSIONS = {
    '.py', '.js', '.ts', '.tsx', '.jsx', '.md', '.txt', '.json',
    '.yaml', '.yml', '.pdf', '.csv', '.ipynb', '.sh', '.sql',
    '.html', '.css', '.toml',
}

IGNORE_PATTERNS = {
    'node_modules', '.git', '__pycache__', '.DS_Store', 'venv',
    '.venv', 'dist', 'build', '.next', '.egg-info', 'wandb',
    'checkpoint', '.tmp', '.cache', 'Library',
}

PROJECT_SIGNATURES = {
    'EGC': ['egc', 'expression_gated', 't_drop', 'r_proxy', 'compressor',
            'suppressor', 'expander', 'aronson', 'thegate', 'egcstudy',
            'comfort_rating', 'consciousness'],
    'LOLM': ['lolm', 'torch_xla', 'tpu', 'xla_device', 'fsdp',
             'lolm_scale', 'trc', 'pjrt', 'lolm_config'],
    'Codey': ['codey', 'nfet_score', 'health_score', 'structural_health',
              'dependency_graph', 'cascade', 'coding_agent', 'credit_system'],
    'NFET': ['nfet', 'kuramoto', 'bpr_delay', 'monte_carlo', 'az511',
             'oscillator', 'traffic_state', 'free_flow'],
    'Qira': ['qira', 'brandyn', 'nous'],
}

client = anthropic.Anthropic()


# ── HELPERS ───────────────────────────────────────────────────
def should_ignore(path: Path) -> bool:
    parts = str(path)
    return any(p in parts for p in IGNORE_PATTERNS)


def detect_project(content: str, filepath: str) -> list:
    combined = (content + filepath).lower()
    projects = []
    for proj, keywords in PROJECT_SIGNATURES.items():
        if sum(1 for kw in keywords if kw in combined) >= 2:
            projects.append(proj)
    return projects or ['General']


def file_hash(path: Path) -> str:
    try:
        return hashlib.md5(path.read_bytes()).hexdigest()[:16]
    except:
        return ''


def file_id(path: Path) -> str:
    return hashlib.md5(str(path).encode()).hexdigest()[:12]


# ── DATABASE ──────────────────────────────────────────────────
def ensure_tables():
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS file_index (
        id TEXT PRIMARY KEY, path TEXT UNIQUE, filename TEXT,
        extension TEXT, project TEXT DEFAULT '[]', type TEXT DEFAULT 'document',
        summary TEXT, importance INTEGER DEFAULT 3, tags TEXT DEFAULT '[]',
        action_items TEXT DEFAULT '[]', content_preview TEXT,
        file_hash TEXT, last_seen TEXT, created_at TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS machine_events (
        id TEXT PRIMARY KEY, event_type TEXT, description TEXT,
        project TEXT, data TEXT DEFAULT '{}', timestamp TEXT
    )""")
    conn.commit()
    conn.close()


def save_to_db(fpath: Path, content: str, classification: dict):
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    fid = file_id(fpath)
    now = datetime.now().isoformat()

    c.execute("""INSERT OR REPLACE INTO file_index
        (id, path, filename, extension, project, type, summary, importance,
         tags, action_items, content_preview, file_hash, last_seen, created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (fid, str(fpath), fpath.name, fpath.suffix,
         json.dumps(classification.get('projects', [])),
         classification.get('type', 'document'),
         classification.get('summary', ''),
         classification.get('importance', 3),
         json.dumps(classification.get('tags', [])),
         json.dumps(classification.get('action_items', [])),
         content[:500], file_hash(fpath), now, now))

    # Auto-create tasks from action items
    for action in classification.get('action_items', []):
        tid = hashlib.md5((str(fpath) + action).encode()).hexdigest()[:12]
        c.execute("""INSERT OR IGNORE INTO tasks
            (id, title, project, status, priority, created_at, notes)
            VALUES (?,?,?,?,?,?,?)""",
            (tid, action,
             classification.get('projects', ['General'])[0],
             'pending', classification.get('importance', 3), now,
             f"Auto-detected from {fpath.name}"))

    conn.commit()
    conn.close()


def log_event(event_type: str, desc: str, project: str = '', data: dict = {}):
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    eid = hashlib.md5(f"{event_type}{desc}{time.time()}".encode()).hexdigest()[:12]
    c.execute("""INSERT INTO machine_events (id, event_type, description, project, data, timestamp)
        VALUES (?,?,?,?,?,?)""",
        (eid, event_type, desc, project, json.dumps(data), datetime.now().isoformat()))
    conn.commit()
    conn.close()


# ── CLASSIFICATION ────────────────────────────────────────────
def classify_fast(fpath: Path, content: str) -> dict:
    """Quick rule-based classification — no API call."""
    projects = detect_project(content, str(fpath))
    ext = fpath.suffix.lower()
    ftype = 'code' if ext in {'.py', '.js', '.ts', '.tsx'} else \
            'config' if ext in {'.json', '.yaml', '.toml'} else \
            'data' if ext in {'.csv', '.sql'} else 'document'

    return {
        'projects': projects,
        'type': ftype,
        'summary': content[:150].replace('\n', ' '),
        'importance': 5 if any(p != 'General' for p in projects) else 3,
        'tags': [],
        'action_items': [],
    }


def classify_deep(fpath: Path, content: str) -> dict:
    """Use Claude Haiku for substantive files."""
    projects = detect_project(content, str(fpath))

    try:
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            messages=[{"role": "user", "content": f"""Classify this file briefly for a command center.
File: {fpath.name} | Projects: {projects}
Content: {content[:800]}

JSON only:
{{"type":"code|research|note|config|data|draft","summary":"one sentence","importance":1-10,"tags":["tag"],"action_items":["if any"]}}"""}]
        )
        text = resp.content[0].text.strip()
        if '```' in text:
            text = text.split('```')[1]
            if text.startswith('json'):
                text = text[4:]
        result = json.loads(text)
        result['projects'] = projects
        return result
    except:
        return classify_fast(fpath, content)


# ── WATCHER ───────────────────────────────────────────────────
class QiraWatcher(FileSystemEventHandler):
    def __init__(self):
        self.queue = deque(maxlen=500)
        self.seen_hashes = set()
        self.lock = threading.Lock()

    def _enqueue(self, path: str, event: str):
        p = Path(path)
        if should_ignore(p) or p.suffix.lower() not in WATCH_EXTENSIONS:
            return
        try:
            if p.stat().st_size < 10 or p.stat().st_size > 5_000_000:
                return
        except:
            return

        h = file_hash(p)
        with self.lock:
            if h in self.seen_hashes:
                return
            self.seen_hashes.add(h)
            self.queue.append((p, event))

    def on_created(self, event):
        if not event.is_directory:
            self._enqueue(event.src_path, 'created')

    def on_modified(self, event):
        if not event.is_directory:
            self._enqueue(event.src_path, 'modified')

    def on_moved(self, event):
        if not event.is_directory:
            self._enqueue(event.dest_path, 'moved')

    def process(self):
        """Process one item from the queue."""
        with self.lock:
            if not self.queue:
                return False
            fpath, event = self.queue.popleft()

        try:
            content = fpath.read_text(errors='ignore')
        except:
            return True

        # Use fast classification for most files, deep for substantial ones
        use_deep = (fpath.suffix in {'.md', '.py', '.txt', '.ipynb'} and len(content) > 300)
        classification = classify_deep(fpath, content) if use_deep else classify_fast(fpath, content)

        save_to_db(fpath, content, classification)
        log_event(f'file_{event}', fpath.name, json.dumps(classification.get('projects', [])))

        projs = classification.get('projects', [])
        imp = classification.get('importance', 3)
        print(f"  [{'/'.join(projs)}] {fpath.name} (imp={imp})")

        if classification.get('action_items'):
            for a in classification['action_items']:
                print(f"    -> {a}")

        # Try to notify command center
        try:
            httpx.post(f"{API_URL}/internal/broadcast",
                json={'type': 'file_indexed', 'file': fpath.name, 'projects': projs},
                headers={'X-API-Key': API_KEY}, timeout=2.0)
        except:
            pass

        return True


def main():
    ensure_tables()

    handler = QiraWatcher()
    observer = Observer()

    watching = 0
    for wp in WATCH_PATHS:
        if wp.exists():
            observer.schedule(handler, str(wp), recursive=True)
            print(f"  Watching: {wp}")
            watching += 1

    observer.start()
    print(f"\n  Qira Watcher active — {watching} directories")
    print("  Press Ctrl+C to stop\n")

    try:
        while True:
            if not handler.process():
                time.sleep(1)
            else:
                time.sleep(0.1)  # Brief pause between processing
    except KeyboardInterrupt:
        observer.stop()
        print("\n  Watcher stopped.")

    observer.join()


if __name__ == "__main__":
    main()
