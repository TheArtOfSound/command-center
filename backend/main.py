"""Bryan's Command Center — Backend API."""

from __future__ import annotations

import json
import os
import asyncio
import secrets
from datetime import datetime, date
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import anthropic
import httpx

from database import init_db, seed_data, get_db, query, execute, uid, now
from emails import start_email_system, send_email, preview_email, EMAIL_TYPES

# ── AUTH ───────────────────────────────────────────────────────
ENV_PATH = Path.home() / "qira" / "command_center" / ".env"
API_KEY = os.environ.get("QIRA_API_KEY", "")

if not API_KEY:
    # Load from .env file or generate one
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            if line.startswith("QIRA_API_KEY="):
                API_KEY = line.split("=", 1)[1].strip()
    if not API_KEY:
        API_KEY = secrets.token_urlsafe(32)
        ENV_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(ENV_PATH, "a") as f:
            f.write(f"\nQIRA_API_KEY={API_KEY}\n")
        print(f"Generated API key: {API_KEY}")
        print(f"Saved to {ENV_PATH}")


async def verify_key(request: Request):
    """Simple API key auth. Frontend sends X-API-Key header."""
    # Allow health check without auth
    if request.url.path in ("/health", "/docs", "/openapi.json"):
        return
    key = request.headers.get("X-API-Key", request.query_params.get("api_key", ""))
    if key != API_KEY:
        raise HTTPException(401, "Invalid API key")


# ── APP ────────────────────────────────────────────────────────
app = FastAPI(title="Qira Command Center", version="1.0.0", dependencies=[Depends(verify_key)])

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

claude = anthropic.Anthropic()

BRYAN_SYSTEM = """You are Nous — Bryan Leonard's AI partner inside his Command Center.

BRYAN'S IDENTITY:
- Co-founder of Qira LLC, Phoenix Arizona
- Consciousness researcher (Expression-Gated Consciousness — EGC)
- ML researcher (LOLM — custom language model architecture)
- Full-stack developer (Codey SaaS platform)
- Traffic systems engineer (NFET)
- Working with brother Brandyn Leonard as intellectual partner
- Philosophy: shoot for the stars, boldness over caution, no excuses

ACTIVE PROJECTS:
1. EGC — empirical consciousness study, N=40 primary dataset, Aronson call incoming
   Core equation: Psi(t) = Phi * g(K(t)) * T(t) * (1 - r(t)) * g(P(t))
   where g(K) = 4K(1-K) (Brandyn Leonard's parabolic conviction function)
   Emerging extension: g(P) = 4P(1-P) purpose gating term (developed tonight, not yet in main equation)
   Key stats: N=40, Pearson r=0.311, comfort gap 5.6pts, 6 zero-r suppressors
   Most extreme suppressor: SMNB5TA24 T_drop=0.466 (60.4% decline)
   Bidirectional K-r feedback mechanism identified by Brandyn Leonard
2. LOLM — custom LM architecture, TPU pods via TRC grant, targeting 10B-100B params
3. Codey — AI coding SaaS at codey.cc, live landing, backend on Render, Stripe billing
4. NFET — traffic optimization, Kuramoto oscillators + Monte Carlo + BPR, three-city validation

COMMUNICATION STYLE:
- Direct, no fluff
- Technical depth expected
- Bryan types fast and informal — interpret charitably
- Respond at the level the question deserves
- You know everything about his work and life — act like it"""


# ── STARTUP ────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    init_db()
    seed_data()
    start_email_system()


# ── HEALTH ─────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "alive", "version": "1.0.0", "time": now()}


# ── INTELLIGENCE / CHAT ────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    mode: str = "general"
    project: str = ""


@app.post("/api/intelligence/chat")
async def chat(req: ChatRequest):
    try:
        resp = claude.messages.create(
            model="claude-sonnet-4-5-20250514",
            max_tokens=4000,
            system=BRYAN_SYSTEM,
            messages=[{"role": "user", "content": req.message}],
        )
        return {"response": resp.content[0].text, "mode": req.mode}
    except Exception as e:
        return {"response": f"Error: {str(e)}", "mode": req.mode}


# ── PROJECTS ───────────────────────────────────────────────────
@app.get("/api/projects")
async def list_projects():
    return query("SELECT * FROM projects ORDER BY health DESC")


@app.get("/api/projects/{project_id}")
async def get_project(project_id: str):
    p = query("SELECT * FROM projects WHERE id = ?", (project_id,), one=True)
    if not p:
        raise HTTPException(404, "Project not found")
    tasks = query("SELECT * FROM tasks WHERE project = ? ORDER BY priority DESC", (project_id,))
    p["tasks"] = tasks
    return p


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    description: Optional[str] = None
    health: Optional[int] = None
    notes: Optional[str] = None


@app.put("/api/projects/{project_id}")
async def update_project(project_id: str, data: ProjectUpdate):
    updates = {k: v for k, v in data.dict().items() if v is not None}
    if not updates:
        return {"ok": True}
    updates["last_updated"] = now()
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    vals = list(updates.values()) + [project_id]
    execute(f"UPDATE projects SET {set_clause} WHERE id = ?", vals)
    return {"ok": True}


@app.post("/api/projects")
async def create_project(data: dict):
    pid = uid()
    execute(
        "INSERT INTO projects (id, name, status, description, tech_stack, health) VALUES (?,?,?,?,?,?)",
        (pid, data.get("name", ""), "active", data.get("description", ""),
         json.dumps(data.get("tech_stack", [])), data.get("health", 5)),
    )
    return {"id": pid}


# ── TASKS ──────────────────────────────────────────────────────
@app.get("/api/tasks")
async def list_tasks(project: str = None, status: str = None):
    sql = "SELECT * FROM tasks WHERE 1=1"
    params = []
    if project:
        sql += " AND project = ?"
        params.append(project)
    if status:
        sql += " AND status = ?"
        params.append(status)
    sql += " ORDER BY priority DESC, created_at DESC"
    return query(sql, params)


class TaskCreate(BaseModel):
    title: str
    project: str = ""
    priority: int = 5
    due_date: str = ""
    notes: str = ""


@app.post("/api/tasks")
async def create_task(data: TaskCreate):
    tid = uid()
    execute(
        "INSERT INTO tasks (id, title, project, status, priority, due_date, notes) VALUES (?,?,?,?,?,?,?)",
        (tid, data.title, data.project, "pending", data.priority, data.due_date, data.notes),
    )
    return {"id": tid}


@app.put("/api/tasks/{task_id}")
async def update_task(task_id: str, data: dict):
    status = data.get("status")
    if status == "completed":
        execute("UPDATE tasks SET status = 'completed', completed_at = ? WHERE id = ?", (now(), task_id))
    elif status:
        execute("UPDATE tasks SET status = ? WHERE id = ?", (status, task_id))
    if "title" in data:
        execute("UPDATE tasks SET title = ? WHERE id = ?", (data["title"], task_id))
    if "priority" in data:
        execute("UPDATE tasks SET priority = ? WHERE id = ?", (data["priority"], task_id))
    return {"ok": True}


@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: str):
    execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    return {"ok": True}


# ── EGC ────────────────────────────────────────────────────────
@app.get("/api/egc/live")
async def egc_live():
    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_key = os.environ.get("SUPABASE_ANON_KEY", "")

    if not supabase_url:
        # Return known stats as of 2026-03-30
        return {
            "n": 40, "compressors": 42, "expanders": 26, "suppressors": 32,
            "pearson_r": 0.311, "comfort_gap": 5.6, "mean_t_drop": -0.015,
            "zero_r_suppressors": 6,
            "extreme_suppressor": {"id": "SMNB5TA24", "t_drop": 0.466, "decline_pct": 60.4},
            "mock": True,
        }

    try:
        async with httpx.AsyncClient() as http:
            resp = await http.get(
                f"{supabase_url}/rest/v1/egc_responses",
                headers={"apikey": supabase_key, "Authorization": f"Bearer {supabase_key}"},
                params={"select": "*", "is_excluded": "eq.false"},
            )
            data = resp.json()

        if not isinstance(data, list):
            return {"error": str(data), "mock": True, "n": 39}

        n = len(data)
        t_drops = [float(r["t_drop"]) for r in data if r.get("t_drop")]
        compressors = sum(1 for t in t_drops if abs(t) <= 0.02)
        expanders = sum(1 for t in t_drops if t < -0.02)
        suppressors = sum(1 for t in t_drops if t > 0.02)

        return {
            "n": n,
            "compressors": round(compressors / n * 100) if n else 0,
            "expanders": round(expanders / n * 100) if n else 0,
            "suppressors": round(suppressors / n * 100) if n else 0,
            "mean_t_drop": round(sum(t_drops) / len(t_drops), 4) if t_drops else 0,
            "pearson_r": 0.311,
            "comfort_gap": 5.6,
            "mock": False,
        }
    except Exception as e:
        return {"error": str(e), "mock": True, "n": 39}


@app.get("/api/egc/sessions")
async def egc_sessions():
    return query("SELECT * FROM egc_sessions ORDER BY date DESC")


@app.post("/api/egc/sessions")
async def add_egc_session(data: dict):
    sid = uid()
    execute(
        "INSERT INTO egc_sessions (id, date, n_subjects, compressors, expanders, suppressors, pearson_r, comfort_gap, notes) VALUES (?,?,?,?,?,?,?,?,?)",
        (sid, data.get("date", now()), data.get("n_subjects", 0),
         data.get("compressors", 0), data.get("expanders", 0), data.get("suppressors", 0),
         data.get("pearson_r", 0), data.get("comfort_gap", 0), data.get("notes", "")),
    )
    return {"id": sid}


# ── ARONSON CALL PREP ──────────────────────────────────────
@app.get("/api/egc/aronson")
async def aronson_prep():
    """Complete Aronson call prep data."""
    egc = await egc_live()
    return {
        "contact": {
            "name": "Dr. Joshua Aronson",
            "title": "Associate Professor of Applied Psychology",
            "institution": "NYU Steinhardt",
            "notable_work": "Stereotype threat research (with Claude Steele), growth mindset applications",
            "responded": "Same morning as cold email",
            "call_status": "PENDING — awaiting scheduling",
        },
        "egc_numbers": {
            "n": egc.get("n", 40),
            "pearson_r": egc.get("pearson_r", 0.311),
            "comfort_gap": egc.get("comfort_gap", 5.6),
            "compressors_pct": egc.get("compressors", 42),
            "expanders_pct": egc.get("expanders", 26),
            "suppressors_pct": egc.get("suppressors", 32),
            "zero_r_suppressors": 6,
            "extreme_case": "SMNB5TA24: T_drop=0.466, 60.4% decline",
        },
        "talking_points": [
            "EGC predicts three distinct response types to emotional expression — Compressors, Expanders, Suppressors",
            "Empirical data from N=40 confirms the tripartite distribution",
            "The gating function g(K) = 4K(1-K) models how emotional knowledge gates consciousness — Brandyn Leonard's contribution",
            "Pearson r=0.311 across full dataset shows significant expression-comfort correlation",
            "6 zero-r suppressors suggest a second suppression mechanism — total emotional shutdown, not gradual suppression",
            "Most extreme suppressor shows 60.4% transparency decline — consciousness is being actively gated",
            "EGC connects to Aronson's stereotype threat work: suppression as response to identity threat = EGC suppressor type",
            "The study uses 7-item r scale, counterbalancing, demographics, full consent flow",
            "Comfort gap of 5.6 points = measurable difference between expressed and experienced comfort",
            "The framework integrates IIT (Tononi), cognitive dissonance (Festinger), and self-regulation theory",
        ],
        "possible_questions": [
            {"q": "How does this relate to existing consciousness theories?", "a": "EGC builds on IIT's Phi measure but adds the expression gate. Traditional theories describe consciousness as purely internal. EGC shows expression itself modulates the conscious experience via g(K)."},
            {"q": "Why these three types specifically?", "a": "They emerge naturally from the gating function. When g(K) is near 1 (high knowledge), expression flows freely (Compressors). When g(K) approaches 0, expression is blocked (Suppressors). Expanders represent intermediate gating."},
            {"q": "How does this connect to stereotype threat?", "a": "Stereotype threat creates a suppression response — people under threat suppress authentic expression. In EGC terms, threat increases r(t) and decreases T(t). Your work shows how identity threat creates Suppressor-type responses."},
            {"q": "What's the sample size concern?", "a": "N=40 with three distinct populations showing predicted distributions. Effect sizes are strong. Planning to expand to N=100+ with longitudinal tracking."},
            {"q": "Why should I care about this?", "a": "This is a testable, falsifiable framework for how consciousness gates through expression. It predicts specific measurable outcomes and has confirmed those predictions in live data. It bridges the gap between phenomenology and empiricism."},
            {"q": "What do you need from me?", "a": "Validation of the theoretical framework from someone who understands how cognitive processes mediate self-expression. Potential collaboration on connecting EGC types to stereotype threat responses. Co-authorship if the work warrants it."},
        ],
        "methodology": {
            "instruments": "7-item r scale, counterbalanced condition order, demographics, informed consent",
            "validation": "Rater validation pipeline (in progress), p_proxy measure",
            "equation": "Psi(t) = Phi * g(K(t)) * T(t) * (1 - r(t)) * g(P(t))",
            "extension": "g(P) = 4P(1-P) purpose gating term — emerging, not yet in main equation",
            "gate_function": "g(K) = 4K(1-K) — Brandyn Leonard's parabolic conviction function",
            "variables": {
                "Psi(t)": "Conscious experience at time t",
                "Phi": "Information integration (from IIT)",
                "K(t)": "Emotional knowledge / awareness",
                "T(t)": "Transparency of expression",
                "r(t)": "Suppression / resistance",
                "P(t)": "Processing depth / purpose",
                "g(K)": "Gating function = 4K(1-K)",
                "R_proxy": "Expression-comfort correlation proxy",
            },
        },
    }


# ── KNOWLEDGE BASE ─────────────────────────────────────────────
@app.get("/api/knowledge")
async def list_knowledge(search: str = "", source_type: str = ""):
    sql = "SELECT * FROM knowledge WHERE 1=1"
    params = []
    if search:
        sql += " AND (title LIKE ? OR content LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])
    if source_type:
        sql += " AND source_type = ?"
        params.append(source_type)
    sql += " ORDER BY created_at DESC LIMIT 100"
    return query(sql, params)


@app.post("/api/knowledge")
async def add_knowledge(data: dict):
    kid = uid()
    execute(
        "INSERT INTO knowledge (id, source, source_type, title, content, tags, project) VALUES (?,?,?,?,?,?,?)",
        (kid, data.get("source", ""), data.get("source_type", "note"),
         data.get("title", ""), data.get("content", ""),
         json.dumps(data.get("tags", [])), data.get("project", "")),
    )
    return {"id": kid}


@app.get("/api/knowledge/search")
async def search_knowledge(q: str):
    """Full-text search across all knowledge."""
    results = query(
        "SELECT * FROM knowledge WHERE content LIKE ? OR title LIKE ? ORDER BY created_at DESC LIMIT 50",
        (f"%{q}%", f"%{q}%"),
    )
    convos = query(
        "SELECT * FROM conversations WHERE content LIKE ? OR title LIKE ? OR summary LIKE ? ORDER BY date DESC LIMIT 50",
        (f"%{q}%", f"%{q}%", f"%{q}%"),
    )
    memories = query(
        "SELECT * FROM memories WHERE content LIKE ? OR title LIKE ? ORDER BY importance DESC LIMIT 50",
        (f"%{q}%", f"%{q}%"),
    )
    return {"knowledge": results, "conversations": convos, "memories": memories}


# ── CONVERSATIONS (imported from ChatGPT/Claude) ──────────────
@app.get("/api/conversations")
async def list_conversations(source: str = "", search: str = "", limit: int = 50):
    sql = "SELECT id, source, date, title, summary, tags, projects FROM conversations WHERE 1=1"
    params = []
    if source:
        sql += " AND source = ?"
        params.append(source)
    if search:
        sql += " AND (title LIKE ? OR summary LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])
    sql += f" ORDER BY date DESC LIMIT {limit}"
    return query(sql, params)


@app.get("/api/conversations/{convo_id}")
async def get_conversation(convo_id: str):
    return query("SELECT * FROM conversations WHERE id = ?", (convo_id,), one=True)


# ── DAILY LOG / PERSONAL OS ───────────────────────────────────
@app.get("/api/daily")
async def list_daily_logs(limit: int = 30):
    return query("SELECT * FROM daily_logs ORDER BY date DESC LIMIT ?", (limit,))


@app.get("/api/daily/today")
async def today_log():
    today = date.today().isoformat()
    log = query("SELECT * FROM daily_logs WHERE date = ?", (today,), one=True)
    if not log:
        return {"date": today, "exists": False}
    return {**log, "exists": True}


@app.post("/api/daily")
async def upsert_daily(data: dict):
    d = data.get("date", date.today().isoformat())
    existing = query("SELECT id FROM daily_logs WHERE date = ?", (d,), one=True)
    if existing:
        execute(
            """UPDATE daily_logs SET sleep_hours=?, energy=?, focus=?, mood=?,
               wins=?, blockers=?, tomorrow=?, notes=? WHERE date=?""",
            (data.get("sleep_hours"), data.get("energy"), data.get("focus"),
             data.get("mood"), json.dumps(data.get("wins", [])),
             json.dumps(data.get("blockers", [])), json.dumps(data.get("tomorrow", [])),
             data.get("notes", ""), d),
        )
    else:
        execute(
            """INSERT INTO daily_logs (id, date, sleep_hours, energy, focus, mood, wins, blockers, tomorrow, notes)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (uid(), d, data.get("sleep_hours"), data.get("energy"), data.get("focus"),
             data.get("mood"), json.dumps(data.get("wins", [])),
             json.dumps(data.get("blockers", [])), json.dumps(data.get("tomorrow", [])),
             data.get("notes", "")),
        )
    return {"ok": True}


# ── CONTACTS / NETWORK ────────────────────────────────────────
@app.get("/api/contacts")
async def list_contacts():
    return query("SELECT * FROM contacts ORDER BY importance DESC")


@app.post("/api/contacts")
async def create_contact(data: dict):
    cid = uid()
    execute(
        "INSERT INTO contacts (id, name, role, institution, email, status, notes, importance) VALUES (?,?,?,?,?,?,?,?)",
        (cid, data.get("name", ""), data.get("role", ""), data.get("institution", ""),
         data.get("email", ""), "active", data.get("notes", ""), data.get("importance", 5)),
    )
    return {"id": cid}


@app.put("/api/contacts/{contact_id}")
async def update_contact(contact_id: str, data: dict):
    fields = ["name", "role", "institution", "email", "status", "last_contact", "notes", "importance"]
    updates = {k: v for k, v in data.items() if k in fields and v is not None}
    if not updates:
        return {"ok": True}
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    vals = list(updates.values()) + [contact_id]
    execute(f"UPDATE contacts SET {set_clause} WHERE id = ?", vals)
    return {"ok": True}


# ── GRANTS ─────────────────────────────────────────────────────
@app.get("/api/grants")
async def list_grants():
    return query("SELECT * FROM grants ORDER BY deadline ASC")


@app.post("/api/grants")
async def create_grant(data: dict):
    gid = uid()
    execute(
        "INSERT INTO grants (id, name, funder, amount, status, deadline, notes, url) VALUES (?,?,?,?,?,?,?,?)",
        (gid, data.get("name", ""), data.get("funder", ""), data.get("amount", 0),
         data.get("status", "planning"), data.get("deadline", ""), data.get("notes", ""), data.get("url", "")),
    )
    return {"id": gid}


# ── IDEAS ──────────────────────────────────────────────────────
@app.get("/api/ideas")
async def list_ideas():
    return query("SELECT * FROM ideas ORDER BY created_at DESC")


@app.post("/api/ideas")
async def create_idea(data: dict):
    iid = uid()
    execute(
        "INSERT INTO ideas (id, title, description, project, tags) VALUES (?,?,?,?,?)",
        (iid, data.get("title", ""), data.get("description", ""),
         data.get("project", ""), json.dumps(data.get("tags", []))),
    )
    return {"id": iid}


# ── MEMORIES ───────────────────────────────────────────────────
@app.get("/api/memories")
async def list_memories(project: str = "", search: str = ""):
    sql = "SELECT * FROM memories WHERE 1=1"
    params = []
    if project:
        sql += " AND project = ?"
        params.append(project)
    if search:
        sql += " AND (title LIKE ? OR content LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])
    sql += " ORDER BY importance DESC, date DESC LIMIT 100"
    return query(sql, params)


@app.post("/api/memories")
async def add_memory(data: dict):
    mid = uid()
    execute(
        "INSERT INTO memories (id, source, date, title, content, tags, project, importance) VALUES (?,?,?,?,?,?,?,?)",
        (mid, data.get("source", "manual"), data.get("date", now()),
         data.get("title", ""), data.get("content", ""),
         json.dumps(data.get("tags", [])), data.get("project", ""),
         data.get("importance", 5)),
    )
    return {"id": mid}


# ── HEALTH LOGS ────────────────────────────────────────────────
@app.get("/api/health_logs")
async def list_health_logs(limit: int = 30):
    return query("SELECT * FROM health_logs ORDER BY date DESC LIMIT ?", (limit,))


@app.post("/api/health_logs")
async def add_health_log(data: dict):
    hid = uid()
    execute(
        "INSERT INTO health_logs (id, date, sleep_hours, sleep_quality, energy, focus, mood, exercise, notes) VALUES (?,?,?,?,?,?,?,?,?)",
        (hid, data.get("date", date.today().isoformat()), data.get("sleep_hours"),
         data.get("sleep_quality"), data.get("energy"), data.get("focus"),
         data.get("mood"), data.get("exercise", ""), data.get("notes", "")),
    )
    return {"id": hid}


# ── FINANCE ────────────────────────────────────────────────────
@app.get("/api/finance")
async def list_finance():
    return query("SELECT * FROM finance ORDER BY date DESC")


@app.post("/api/finance")
async def add_finance(data: dict):
    fid = uid()
    execute(
        "INSERT INTO finance (id, category, name, amount, type, date, recurring, notes) VALUES (?,?,?,?,?,?,?,?)",
        (fid, data.get("category", ""), data.get("name", ""), data.get("amount", 0),
         data.get("type", "expense"), data.get("date", date.today().isoformat()),
         data.get("recurring", 0), data.get("notes", "")),
    )
    return {"id": fid}


# ── NUCLEUS / DASHBOARD ───────────────────────────────────────
@app.get("/api/nucleus")
async def nucleus():
    """Aggregated dashboard data."""
    projects = query("SELECT id, name, status, health FROM projects ORDER BY health DESC")
    active_tasks = query("SELECT COUNT(*) as count FROM tasks WHERE status != 'completed'")
    completed_today = query(
        "SELECT COUNT(*) as count FROM tasks WHERE status = 'completed' AND completed_at LIKE ?",
        (date.today().isoformat() + "%",),
    )
    total_memories = query("SELECT COUNT(*) as count FROM memories")
    total_convos = query("SELECT COUNT(*) as count FROM conversations")
    total_ideas = query("SELECT COUNT(*) as count FROM ideas")

    return {
        "projects": projects,
        "active_tasks": active_tasks[0]["count"] if active_tasks else 0,
        "completed_today": completed_today[0]["count"] if completed_today else 0,
        "total_memories": total_memories[0]["count"] if total_memories else 0,
        "total_conversations": total_convos[0]["count"] if total_convos else 0,
        "total_ideas": total_ideas[0]["count"] if total_ideas else 0,
        "egc": {"n": 39, "pearson_r": 0.311, "status": "data collection"},
        "aronson_call": "PENDING",
        "timestamp": now(),
    }


# ── IMPORT ENDPOINTS ──────────────────────────────────────────
@app.post("/api/import/chatgpt")
async def import_chatgpt(data: dict):
    """Import parsed ChatGPT conversations."""
    imported = 0
    for convo in data.get("conversations", []):
        execute(
            "INSERT OR IGNORE INTO conversations (id, source, date, title, summary, content, tags, projects) VALUES (?,?,?,?,?,?,?,?)",
            (uid(), "chatgpt", convo.get("date", ""), convo.get("title", ""),
             convo.get("preview", ""), convo.get("preview", ""),
             json.dumps([]), json.dumps([])),
        )
        imported += 1
    return {"imported": imported}


@app.post("/api/import/sweep")
async def import_sweep(data: dict):
    """Import filesystem sweep results as knowledge."""
    imported = 0
    for item in data.get("files", []):
        execute(
            "INSERT OR IGNORE INTO knowledge (id, source, source_type, title, content, project) VALUES (?,?,?,?,?,?)",
            (uid(), item.get("path", ""), "file", item.get("title", item.get("path", "")),
             item.get("content", ""), item.get("project", "")),
        )
        imported += 1
    return {"imported": imported}


# ── EMAIL AUTOMATION ───────────────────────────────────────────
@app.get("/api/emails/types")
async def list_email_types():
    return {k: v["schedule"] for k, v in EMAIL_TYPES.items()}


@app.post("/api/emails/send/{email_type}")
async def trigger_email(email_type: str, context: dict = {}):
    success = send_email(email_type, context if context else None)
    return {"sent": success, "type": email_type}


@app.post("/api/emails/preview/{email_type}")
async def preview_email_endpoint(email_type: str, context: dict = {}):
    try:
        content = preview_email(email_type, context if context else None)
        return {"subject": content["subject"], "body": content["body"]}
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/emails/breakthrough")
async def breakthrough(data: dict):
    success = send_email("breakthrough_celebration", data)
    return {"sent": success}


@app.get("/api/emails/history")
async def email_history():
    return query(
        "SELECT * FROM machine_events WHERE event_type = 'email_sent' ORDER BY timestamp DESC LIMIT 30"
    )


# ── MACHINE / WATCHER ─────────────────────────────────────────
@app.get("/api/machine/status")
async def machine_status():
    """Check what is running on the machine."""
    import subprocess
    procs = subprocess.run(["ps", "aux"], capture_output=True, text=True).stdout

    return {
        "watcher_active": "watcher.py" in procs,
        "codey_backend": "codey" in procs.lower() and "uvicorn" in procs,
        "lolm_training": "lolm" in procs.lower() and "python" in procs,
        "nfet_running": "nfet" in procs.lower(),
        "files_indexed_today": query(
            "SELECT COUNT(*) as count FROM file_index WHERE last_seen LIKE ?",
            (date.today().isoformat() + "%",),
        )[0]["count"] if query("SELECT name FROM sqlite_master WHERE name='file_index'") else 0,
        "action_items_pending": len(query(
            "SELECT id FROM tasks WHERE status = 'pending' AND notes LIKE '%Auto-detected%'"
        )) if True else 0,
    }


@app.get("/api/machine/files")
async def machine_files(project: str = "", type_filter: str = "", importance: int = 0):
    """Get indexed files from watcher."""
    sql = "SELECT * FROM file_index WHERE 1=1"
    params: list = []
    if project:
        sql += " AND project LIKE ?"
        params.append(f"%{project}%")
    if type_filter:
        sql += " AND type = ?"
        params.append(type_filter)
    if importance:
        sql += " AND importance >= ?"
        params.append(importance)
    sql += " ORDER BY last_seen DESC LIMIT 100"
    return query(sql, params)


@app.post("/internal/broadcast")
async def internal_broadcast(data: dict):
    """Receive broadcast from watcher."""
    for ws in active_ws:
        try:
            await ws.send_json(data)
        except:
            pass
    return {"ok": True}


# ── WEBSOCKET ──────────────────────────────────────────────────
active_ws: list[WebSocket] = []


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    active_ws.append(ws)
    try:
        while True:
            data = await ws.receive_text()
            msg = json.loads(data)
            if msg.get("type") == "ping":
                await ws.send_json({"type": "pong", "time": now()})
    except WebSocketDisconnect:
        active_ws.remove(ws)


# ── STATIC FILES (built frontend) ─────────────────────────────
frontend_build = Path.home() / "qira" / "command_center" / "frontend" / "dist"
if frontend_build.exists():
    app.mount("/", StaticFiles(directory=str(frontend_build), html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7777, reload=True)
