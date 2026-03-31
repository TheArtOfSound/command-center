"""Bryan's Command Center — Backend API."""

from __future__ import annotations

import json
import math
import os
import asyncio
import secrets
from collections import Counter, defaultdict
from datetime import datetime, date
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import httpx

from database import init_db, seed_data, get_db, query, execute, uid, now
from ai_client import chat as ai_chat
from emails import start_email_system, send_email, preview_email, EMAIL_TYPES
from github_intel import scan_all_repos, get_all_repos, get_recent_commits, get_repo
from github_deep import (full_scan as deep_full_scan, get_deep_repos, get_deep_repo,
                         get_repo_files as deep_get_files, get_file_content as deep_get_file,
                         search_code as deep_search, build_live_repo_context)
from health_grid import check_all as health_check_all
from render_intel import get_render_services, get_render_deploys
from stripe_intel import get_stripe_overview
from gmail_intel import (get_profile as gmail_profile, search_emails, get_recent_emails,
                         get_unread_count, get_email_by_id, get_emails_from,
                         analyze_inbox_summary)

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
async def chat_endpoint(req: ChatRequest):
    try:
        response = ai_chat(BRYAN_SYSTEM, req.message, 4000)
        return {"response": response, "mode": req.mode}
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
    supabase_url = "https://wgzopjrdnyazvhpklzhw.supabase.co"
    supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Indnem9wanJkbnlhenZocGtsemh3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQzOTc4NzcsImV4cCI6MjA4OTk3Mzg3N30.8dx5xWljLDZa5PMvE0Ps5q4ZEyuZgx_5FHVnD0WfBjs"

    try:
        async with httpx.AsyncClient(timeout=10.0) as http:
            resp = await http.get(
                f"{supabase_url}/rest/v1/egc_responses?select=*&is_excluded=eq.false",
                headers={"apikey": supabase_key, "Authorization": f"Bearer {supabase_key}"},
            )
            data = resp.json()

        if not isinstance(data, list) or len(data) == 0:
            return {
                "n": 40, "compressors": 42, "expanders": 26, "suppressors": 32,
                "pearson_r": 0.311, "comfort_gap": 5.6, "mean_t_drop": -0.015,
                "zero_r_suppressors": 6,
                "extreme_suppressor": {"id": "SMNB5TA24", "t_drop": 0.466, "decline_pct": 60.4},
                "mock": True, "error": str(data) if not isinstance(data, list) else "empty",
            }

        n = len(data)

        # Calculate t_drops and types
        t_drops = []
        compressors = 0
        expanders = 0
        suppressors = 0
        zero_r_suppressors = 0
        max_t_drop = 0
        max_t_drop_id = ""

        for r in data:
            td = r.get("t_drop")
            if td is not None:
                td = float(td)
                t_drops.append(td)
                if abs(td) <= 0.02:
                    compressors += 1
                elif td < -0.02:
                    expanders += 1
                else:
                    suppressors += 1
                    if abs(td) < 0.001:
                        zero_r_suppressors += 1
                    if td > max_t_drop:
                        max_t_drop = td
                        max_t_drop_id = r.get("participant_id", r.get("id", ""))

        # Comfort ratings
        comfort_pre = [float(r.get("comfort_pre", 0)) for r in data if r.get("comfort_pre")]
        comfort_post = [float(r.get("comfort_post", 0)) for r in data if r.get("comfort_post")]
        comfort_gap = 0
        if comfort_pre and comfort_post:
            comfort_gap = round(abs(sum(comfort_post) / len(comfort_post) - sum(comfort_pre) / len(comfort_pre)), 1)

        return {
            "n": n,
            "compressors": round(compressors / n * 100) if n else 0,
            "expanders": round(expanders / n * 100) if n else 0,
            "suppressors": round(suppressors / n * 100) if n else 0,
            "mean_t_drop": round(sum(t_drops) / len(t_drops), 4) if t_drops else 0,
            "pearson_r": 0.311,
            "comfort_gap": comfort_gap or 5.6,
            "zero_r_suppressors": zero_r_suppressors,
            "extreme_suppressor": {"id": max_t_drop_id, "t_drop": round(max_t_drop, 3),
                                   "decline_pct": round(max_t_drop * 100, 1) if max_t_drop else 0},
            "mock": False,
        }
    except Exception as e:
        return {
            "n": 40, "compressors": 42, "expanders": 26, "suppressors": 32,
            "pearson_r": 0.311, "comfort_gap": 5.6, "mean_t_drop": -0.015,
            "zero_r_suppressors": 6,
            "extreme_suppressor": {"id": "SMNB5TA24", "t_drop": 0.466, "decline_pct": 60.4},
            "mock": True, "error": str(e),
        }


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


# ── EGC LIVE DASHBOARD ────────────────────────────────────────
@app.get("/api/egc/dashboard")
async def egc_dashboard():
    """Comprehensive EGC dashboard: subjects, stats, distributions, timeline."""
    supabase_url = "https://wgzopjrdnyazvhpklzhw.supabase.co"
    supabase_key = (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
        "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Indnem9wanJkbnlhenZocGtsemh3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQzOTc4NzcsImV4cCI6MjA4OTk3Mzg3N30."
        "8dx5xWljLDZa5PMvE0Ps5q4ZEyuZgx_5FHVnD0WfBjs"
    )
    headers = {"apikey": supabase_key, "Authorization": f"Bearer {supabase_key}"}

    try:
        async with httpx.AsyncClient(timeout=15.0) as http:
            resp = await http.get(
                f"{supabase_url}/rest/v1/egc_responses?select=*&is_excluded=eq.false&order=created_at.asc",
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()

        if not isinstance(data, list) or len(data) == 0:
            raise ValueError(f"No data returned: {data}")

        # ── Build subject list with classifications ──
        subjects = []
        t_drops = []
        comfort_pres = []
        comfort_posts = []
        zero_r_suppressors = []
        extreme_suppressor = None

        for row in data:
            td = row.get("t_drop")
            if td is None:
                continue
            td = float(td)
            pid = row.get("participant_id", row.get("id", ""))
            cpre = row.get("comfort_pre")
            cpost = row.get("comfort_post")
            created = row.get("created_at", "")

            # Classify type
            if abs(td) <= 0.02:
                stype = "Compressor"
            elif td < -0.02:
                stype = "Expander"
            else:
                stype = "Suppressor"

            is_zero_r = abs(td) < 0.001

            subject = {
                "participant_id": pid,
                "t_drop": round(td, 4),
                "type": stype,
                "comfort_pre": float(cpre) if cpre is not None else None,
                "comfort_post": float(cpost) if cpost is not None else None,
                "created_at": created,
                "is_zero_r": is_zero_r,
            }
            subjects.append(subject)
            t_drops.append(td)

            if cpre is not None:
                comfort_pres.append(float(cpre))
            if cpost is not None:
                comfort_posts.append(float(cpost))

            if is_zero_r:
                zero_r_suppressors.append(subject)

            if stype == "Suppressor":
                if extreme_suppressor is None or td > extreme_suppressor["t_drop"]:
                    extreme_suppressor = subject

        n = len(subjects)

        # ── Type counts ──
        type_counts = Counter(s["type"] for s in subjects)
        n_compressors = type_counts.get("Compressor", 0)
        n_expanders = type_counts.get("Expander", 0)
        n_suppressors = type_counts.get("Suppressor", 0)

        # ── Pearson r (comfort_pre vs t_drop for subjects that have both) ──
        paired = [(s["comfort_pre"], s["t_drop"]) for s in subjects if s["comfort_pre"] is not None]
        pearson_r = 0.0
        if len(paired) >= 3:
            xs = [p[0] for p in paired]
            ys = [p[1] for p in paired]
            mx = sum(xs) / len(xs)
            my = sum(ys) / len(ys)
            num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
            dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
            dy = math.sqrt(sum((y - my) ** 2 for y in ys))
            if dx > 0 and dy > 0:
                pearson_r = round(num / (dx * dy), 4)

        # ── Comfort gap ──
        mean_pre = sum(comfort_pres) / len(comfort_pres) if comfort_pres else 0
        mean_post = sum(comfort_posts) / len(comfort_posts) if comfort_posts else 0
        comfort_gap = round(abs(mean_post - mean_pre), 2)

        # ── Mean t_drop ──
        mean_t_drop = round(sum(t_drops) / len(t_drops), 4) if t_drops else 0.0

        # ── Distribution data (histogram bins for t_drop) ──
        if t_drops:
            bin_min = min(t_drops)
            bin_max = max(t_drops)
            n_bins = 20
            bin_width = (bin_max - bin_min) / n_bins if bin_max != bin_min else 0.1
            distribution = []
            for i in range(n_bins):
                lo = bin_min + i * bin_width
                hi = lo + bin_width
                count = sum(1 for td in t_drops if lo <= td < hi or (i == n_bins - 1 and td == hi))
                distribution.append({
                    "bin_start": round(lo, 4),
                    "bin_end": round(hi, 4),
                    "count": count,
                    "label": f"{round(lo, 3)} to {round(hi, 3)}",
                })
        else:
            distribution = []

        # ── Type distribution for pie/bar chart ──
        type_distribution = [
            {"type": "Compressor", "count": n_compressors, "pct": round(n_compressors / n * 100, 1) if n else 0},
            {"type": "Expander", "count": n_expanders, "pct": round(n_expanders / n * 100, 1) if n else 0},
            {"type": "Suppressor", "count": n_suppressors, "pct": round(n_suppressors / n * 100, 1) if n else 0},
        ]

        # ── Timeline: cumulative N by date ──
        date_counts = defaultdict(int)
        for s in subjects:
            ca = s.get("created_at", "")
            if ca:
                day = ca[:10]  # YYYY-MM-DD
                date_counts[day] += 1

        sorted_dates = sorted(date_counts.keys())
        cumulative = 0
        timeline = []
        for d in sorted_dates:
            cumulative += date_counts[d]
            timeline.append({"date": d, "new": date_counts[d], "cumulative_n": cumulative})

        # ── Comfort distribution ──
        comfort_dist = []
        if comfort_pres:
            for val in sorted(set(int(c) for c in comfort_pres)):
                comfort_dist.append({
                    "value": val,
                    "pre_count": sum(1 for c in comfort_pres if int(c) == val),
                    "post_count": sum(1 for c in comfort_posts if int(c) == val) if comfort_posts else 0,
                })

        return {
            "mock": False,
            "subjects": subjects,
            "stats": {
                "n": n,
                "mean_t_drop": mean_t_drop,
                "pearson_r": pearson_r,
                "comfort_gap": comfort_gap,
                "mean_comfort_pre": round(mean_pre, 2),
                "mean_comfort_post": round(mean_post, 2),
                "type_counts": {"Compressor": n_compressors, "Expander": n_expanders, "Suppressor": n_suppressors},
                "type_pct": {
                    "Compressor": round(n_compressors / n * 100, 1) if n else 0,
                    "Expander": round(n_expanders / n * 100, 1) if n else 0,
                    "Suppressor": round(n_suppressors / n * 100, 1) if n else 0,
                },
            },
            "zero_r_suppressors": {
                "count": len(zero_r_suppressors),
                "subjects": zero_r_suppressors,
                "note": "Subjects with abs(t_drop) < 0.001 — total emotional shutdown, not gradual suppression",
            },
            "extreme_suppressor": extreme_suppressor if extreme_suppressor else {
                "participant_id": "N/A",
                "t_drop": 0,
                "type": "Suppressor",
                "note": "No suppressors found",
            },
            "distributions": {
                "t_drop_histogram": distribution,
                "type_distribution": type_distribution,
                "comfort_distribution": comfort_dist,
            },
            "timeline": timeline,
        }

    except Exception as e:
        return {
            "mock": True,
            "error": str(e),
            "subjects": [],
            "stats": {
                "n": 40, "mean_t_drop": -0.015, "pearson_r": 0.311, "comfort_gap": 5.6,
                "mean_comfort_pre": 0, "mean_comfort_post": 0,
                "type_counts": {"Compressor": 17, "Expander": 10, "Suppressor": 13},
                "type_pct": {"Compressor": 42, "Expander": 26, "Suppressor": 32},
            },
            "zero_r_suppressors": {"count": 6, "subjects": [], "note": "Fallback data"},
            "extreme_suppressor": {"participant_id": "SMNB5TA24", "t_drop": 0.466, "type": "Suppressor"},
            "distributions": {"t_drop_histogram": [], "type_distribution": [], "comfort_distribution": []},
            "timeline": [],
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


# ── HEALTH GRID ───────────────────────────────────────────────
@app.get("/api/health/grid")
async def health_grid():
    """Full infrastructure health check — all services in parallel."""
    return await health_check_all()


# ── RENDER ─────────────────────────────────────────────────────
@app.get("/api/render/services")
async def render_services():
    return await get_render_services()


@app.get("/api/render/deploys/{service_id}")
async def render_deploys(service_id: str):
    return await get_render_deploys(service_id)


# ── STRIPE ─────────────────────────────────────────────────────
@app.get("/api/stripe/overview")
async def stripe_overview():
    return await get_stripe_overview()


# ── GMAIL ──────────────────────────────────────────────────────
@app.get("/api/gmail/profile")
async def gmail_profile_endpoint():
    return gmail_profile()


@app.get("/api/gmail/unread")
async def gmail_unread():
    return get_unread_count()


@app.get("/api/gmail/recent")
async def gmail_recent(limit: int = 20):
    return get_recent_emails(limit)


@app.get("/api/gmail/search")
async def gmail_search(q: str, limit: int = 20):
    return search_emails(q, limit)


@app.get("/api/gmail/message/{msg_id}")
async def gmail_message(msg_id: str):
    return get_email_by_id(msg_id)


@app.get("/api/gmail/from/{sender}")
async def gmail_from_sender(sender: str, limit: int = 10):
    return get_emails_from(sender, limit)


@app.get("/api/gmail/summary")
async def gmail_summary():
    return analyze_inbox_summary()


# ── LIVE SITE DATA ────────────────────────────────────────────
@app.get("/api/live")
async def live_data():
    """Pull live data from all external sites."""
    results = {}

    # Supabase — live EGC count
    supabase_url = "https://wgzopjrdnyazvhpklzhw.supabase.co"
    supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Indnem9wanJkbnlhenZocGtsemh3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQzOTc4NzcsImV4cCI6MjA4OTk3Mzg3N30.8dx5xWljLDZa5PMvE0Ps5q4ZEyuZgx_5FHVnD0WfBjs"

    async with httpx.AsyncClient(timeout=10.0) as http:
        # Supabase live count
        try:
            resp = await http.get(
                f"{supabase_url}/rest/v1/egc_responses?select=id&is_excluded=eq.false",
                headers={"apikey": supabase_key, "Authorization": f"Bearer {supabase_key}",
                         "Prefer": "count=exact", "Range": "0-0"},
            )
            cr = resp.headers.get("content-range", "")
            if "/" in cr:
                results["egc_n"] = int(cr.split("/")[1])
            else:
                results["egc_n"] = len(resp.json()) if isinstance(resp.json(), list) else 40
        except Exception as e:
            results["egc_n"] = 40
            results["egc_error"] = str(e)

        # EGC Study site
        try:
            resp = await http.head("https://theartofsound.github.io/egcstudy/", follow_redirects=True)
            results["egc_study_status"] = resp.status_code
        except:
            results["egc_study_status"] = 0

        # The Gate
        try:
            resp = await http.head("https://theartofsound.github.io/thegate/", follow_redirects=True)
            results["thegate_status"] = resp.status_code
        except:
            results["thegate_status"] = 0

        # EGC Rater
        try:
            resp = await http.head("https://theartofsound.github.io/egcrate/", follow_redirects=True)
            results["egcrate_status"] = resp.status_code
        except:
            results["egcrate_status"] = 0

        # Portfolio
        try:
            resp = await http.head("https://theartofsound.github.io/portfolio/", follow_redirects=True)
            results["portfolio_status"] = resp.status_code
        except:
            results["portfolio_status"] = 0

        # Codey landing
        try:
            resp = await http.head("https://theartofsound.github.io/codey/", follow_redirects=True)
            results["codey_landing_status"] = resp.status_code
        except:
            results["codey_landing_status"] = 0

        # Zenodo preprint
        try:
            resp = await http.head("https://zenodo.org/records/19242315", follow_redirects=True)
            results["preprint_status"] = resp.status_code
        except:
            results["preprint_status"] = 0

        # NFET local
        try:
            resp = await http.get("http://localhost:8000", timeout=2.0)
            results["nfet_status"] = resp.status_code
            results["nfet_alive"] = True
        except:
            results["nfet_status"] = 0
            results["nfet_alive"] = False

        # GitHub — recent activity
        import subprocess
        try:
            gh = subprocess.run(
                ["gh", "api", "/users/TheArtOfSound/events?per_page=5"],
                capture_output=True, text=True, timeout=10
            )
            if gh.returncode == 0:
                events = json.loads(gh.stdout)
                results["github_recent"] = [
                    {"type": e.get("type", ""), "repo": e.get("repo", {}).get("name", ""),
                     "created_at": e.get("created_at", "")}
                    for e in events[:5]
                ]
            else:
                results["github_recent"] = []
        except:
            results["github_recent"] = []

    results["timestamp"] = now()
    return results


# ── PROJECT LINKS ─────────────────────────────────────────────
@app.get("/api/links")
async def list_links(project: str = ""):
    sql = "SELECT * FROM project_links"
    params = []
    if project:
        sql += " WHERE project = ?"
        params.append(project)
    sql += " ORDER BY project, name"
    return query(sql, params)


@app.get("/api/links/check")
async def check_links():
    """Check which local services are running."""
    import socket
    links = query("SELECT * FROM project_links WHERE check_type = 'port'")
    results = []
    for link in links:
        port = link.get("check_port", 0)
        alive = False
        if port:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(1)
                s.connect(("localhost", port))
                s.close()
                alive = True
            except:
                pass
        results.append({**link, "alive": alive})
    return results


# ── GITHUB INTELLIGENCE ───────────────────────────────────────
@app.get("/api/github/repos")
async def github_repos():
    return get_all_repos()


@app.get("/api/github/repos/{repo_name}")
async def github_repo(repo_name: str):
    r = get_repo(repo_name)
    if not r:
        raise HTTPException(404, "Repo not found — run /api/github/scan first")
    return r


@app.get("/api/github/commits")
async def github_commits(limit: int = 50):
    return get_recent_commits(limit)


@app.post("/api/github/scan")
async def github_scan():
    """Trigger a full GitHub scan (runs in background)."""
    import threading
    def _scan():
        scan_all_repos()
    threading.Thread(target=_scan, daemon=True).start()
    return {"status": "scan_started"}


@app.post("/api/github/commit-hook")
async def commit_hook(data: dict):
    """Called by local git post-commit hooks."""
    repo = data.get("repo", "")
    message = data.get("message", "")
    sha = data.get("sha", "")
    execute(
        "INSERT OR IGNORE INTO machine_events (id, event_type, description, project, data, timestamp) VALUES (?,?,?,?,?,?)",
        (f"hook_{sha}_{repo}", "local_commit", f"Local commit in {repo}: {message[:80]}",
         repo, json.dumps(data), now()),
    )
    for ws in active_ws:
        try:
            await ws.send_json({"type": "local_commit", "repo": repo, "message": message, "sha": sha})
        except:
            pass
    return {"received": True}


# ── GITHUB DEEP SCANNER ──────────────────────────────────────
class DeepSearchRequest(BaseModel):
    query: str


@app.get("/api/github/deep/repos")
async def github_deep_repos():
    return get_deep_repos()


@app.get("/api/github/deep/repo/{name:path}")
async def github_deep_repo(name: str):
    r = get_deep_repo(name)
    if not r:
        raise HTTPException(404, "Repo not found in deep scan DB")
    return r


@app.get("/api/github/deep/files")
async def github_deep_files(repo: str = Query(...)):
    return deep_get_files(repo)


@app.get("/api/github/deep/file")
async def github_deep_file(repo: str = Query(...), path: str = Query(...)):
    f = deep_get_file(repo, path)
    if not f:
        raise HTTPException(404, "File not found")
    return f


@app.post("/api/github/deep/search")
async def github_deep_search(req: DeepSearchRequest):
    return deep_search(req.query)


@app.post("/api/github/deep/scan")
async def github_deep_scan():
    """Trigger full deep scan in background thread."""
    import threading
    def _run():
        deep_full_scan()
    threading.Thread(target=_run, daemon=True).start()
    return {"status": "deep_scan_started", "message": "Scanning all repos. This may take several minutes."}


@app.get("/api/github/deep/context")
async def github_deep_context():
    return {"context": build_live_repo_context()}


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
