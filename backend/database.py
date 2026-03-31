"""Database models and initialization for Command Center."""

import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

DB_PATH = Path.home() / "qira" / "command_center" / "data" / "nucleus.db"

TABLES = [
    """CREATE TABLE IF NOT EXISTS memories (
        id TEXT PRIMARY KEY,
        source TEXT NOT NULL DEFAULT 'unknown',
        date TEXT,
        title TEXT,
        content TEXT,
        tags TEXT DEFAULT '[]',
        project TEXT,
        importance INTEGER DEFAULT 5,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS projects (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        status TEXT DEFAULT 'active',
        description TEXT,
        tech_stack TEXT DEFAULT '[]',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        last_updated TEXT,
        health INTEGER DEFAULT 7,
        notes TEXT,
        links TEXT DEFAULT '[]'
    )""",
    """CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        project TEXT,
        status TEXT DEFAULT 'pending',
        priority INTEGER DEFAULT 5,
        due_date TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        completed_at TEXT,
        notes TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS daily_logs (
        id TEXT PRIMARY KEY,
        date TEXT UNIQUE,
        sleep_hours REAL,
        energy INTEGER,
        focus INTEGER,
        mood INTEGER,
        wins TEXT DEFAULT '[]',
        blockers TEXT DEFAULT '[]',
        tomorrow TEXT DEFAULT '[]',
        notes TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS conversations (
        id TEXT PRIMARY KEY,
        source TEXT DEFAULT 'claude',
        date TEXT,
        title TEXT,
        summary TEXT,
        content TEXT,
        tags TEXT DEFAULT '[]',
        projects TEXT DEFAULT '[]'
    )""",
    """CREATE TABLE IF NOT EXISTS grants (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        funder TEXT,
        amount INTEGER DEFAULT 0,
        status TEXT DEFAULT 'planning',
        deadline TEXT,
        submitted_date TEXT,
        notes TEXT,
        url TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS contacts (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        role TEXT,
        institution TEXT,
        email TEXT,
        status TEXT DEFAULT 'active',
        last_contact TEXT,
        notes TEXT,
        importance INTEGER DEFAULT 5
    )""",
    """CREATE TABLE IF NOT EXISTS ideas (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        description TEXT,
        project TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'new',
        tags TEXT DEFAULT '[]'
    )""",
    """CREATE TABLE IF NOT EXISTS knowledge (
        id TEXT PRIMARY KEY,
        source TEXT,
        source_type TEXT DEFAULT 'note',
        title TEXT,
        content TEXT,
        tags TEXT DEFAULT '[]',
        project TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS egc_sessions (
        id TEXT PRIMARY KEY,
        date TEXT,
        n_subjects INTEGER DEFAULT 0,
        compressors REAL DEFAULT 0,
        expanders REAL DEFAULT 0,
        suppressors REAL DEFAULT 0,
        pearson_r REAL DEFAULT 0,
        comfort_gap REAL DEFAULT 0,
        notes TEXT
    )""",
    """CREATE TABLE IF NOT EXISTS health_logs (
        id TEXT PRIMARY KEY,
        date TEXT,
        sleep_hours REAL,
        sleep_quality INTEGER,
        energy INTEGER,
        focus INTEGER,
        mood INTEGER,
        exercise TEXT,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS finance (
        id TEXT PRIMARY KEY,
        category TEXT,
        name TEXT,
        amount REAL DEFAULT 0,
        type TEXT DEFAULT 'expense',
        date TEXT,
        recurring INTEGER DEFAULT 0,
        notes TEXT
    )""",
]


def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_db()
    c = conn.cursor()
    for table_sql in TABLES:
        c.execute(table_sql)
    conn.commit()
    conn.close()


def uid():
    return str(uuid.uuid4())[:12]


def now():
    return datetime.now().isoformat()


def query(sql, params=(), one=False):
    conn = get_db()
    c = conn.cursor()
    c.execute(sql, params)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows[0] if one and rows else rows if not one else None


def execute(sql, params=()):
    conn = get_db()
    c = conn.cursor()
    c.execute(sql, params)
    conn.commit()
    conn.close()


# Seed known projects on first run
def seed_data():
    existing = query("SELECT id FROM projects LIMIT 1")
    if existing:
        return

    projects = [
        ("egc", "EGC Research", "active",
         "Expression-Gated Consciousness - empirical consciousness study, N=40 primary dataset. Core equation: Psi(t) = Phi*g(K(t))*T(t)*(1-r(t))*g(P(t)). g(K)=4K(1-K) is Brandyn Leonard's parabolic conviction function.",
         '["python","supabase","postgresql","statistics"]',
         8, '["https://egcstudy.com"]'),
        ("lolm", "LOLM", "active",
         "Custom language model architecture targeting 10B-100B params on TPU pods via TRC grant",
         '["python","pytorch","xla","tpu","jax"]',
         6, '[]'),
        ("codey", "Codey SaaS", "active",
         "AI coding assistant SaaS platform. Live landing page, backend on Render, Stripe billing",
         '["python","fastapi","react","stripe","render"]',
         7, '["https://codey.cc"]'),
        ("nfet", "NFET Traffic", "active",
         "Network Flow Equilibrium Traffic optimization system. Three-city validation. Kuramoto oscillators + Monte Carlo + BPR functions",
         '["python","traffic","kuramoto","monte-carlo"]',
         5, '[]'),
        ("qira", "Qira LLC", "active",
         "Bryan and Brandyn Leonard's company. Umbrella for all projects.",
         '["business","llc","phoenix-az"]',
         7, '[]'),
    ]

    conn = get_db()
    c = conn.cursor()
    for p in projects:
        c.execute(
            "INSERT INTO projects (id, name, status, description, tech_stack, health, links) VALUES (?,?,?,?,?,?,?)",
            p,
        )

    # Seed contacts
    contacts = [
        ("aronson", "Elliot Aronson", "Professor Emeritus", "UC Santa Cruz", "", "pending", "", "Key collaborator for EGC validation. Call pending.", 10),
        ("brandyn", "Brandyn Leonard", "Co-founder", "Qira LLC", "", "active", "", "Brother and intellectual partner", 10),
    ]
    for ct in contacts:
        c.execute(
            "INSERT INTO contacts (id, name, role, institution, email, status, last_contact, notes, importance) VALUES (?,?,?,?,?,?,?,?,?)",
            ct,
        )

    # Seed grants
    grants = [
        ("trc", "Google TRC", "Google", 0, "active", "", "", "TPU Research Cloud grant for LOLM training", ""),
    ]
    for g in grants:
        c.execute(
            "INSERT INTO grants (id, name, funder, amount, status, deadline, submitted_date, notes, url) VALUES (?,?,?,?,?,?,?,?,?)",
            g,
        )

    conn.commit()
    conn.close()
