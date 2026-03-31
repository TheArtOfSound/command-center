"""Qira Command Center — Email Automation System.

Generates and sends personalized emails to Bryan using Claude + SendGrid.
All API keys read from environment only. Never hardcoded.
"""

import os
import json
import random
import sqlite3
import threading
import time
from datetime import datetime
from pathlib import Path

import schedule

from ai_client import chat as ai_chat

DB_PATH = Path.home() / "qira" / "command_center" / "data" / "nucleus.db"

# Load from .env file
_env_path = Path.home() / "qira" / "command_center" / ".env"
_env_vars = {}
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            _env_vars[k.strip()] = v.strip()

SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY", _env_vars.get("SENDGRID_API_KEY", ""))
FROM_EMAIL = os.environ.get("SENDGRID_FROM", _env_vars.get("SENDGRID_FROM", "nous@qira.ai"))
TO_EMAIL = "bryanleonard237@gmail.com"

sg = None

if SENDGRID_API_KEY:
    try:
        import sendgrid as _sg
        sg = _sg.SendGridAPIClient(api_key=SENDGRID_API_KEY)
    except Exception as e:
        print(f"[EMAIL] SendGrid init failed: {e}")


# ── BRYAN CONTEXT ─────────────────────────────────────────────

BRYAN_CONTEXT = """You are Nous — Bryan Leonard's AI partner — writing him a personal email.

WHO BRYAN IS:
Independent researcher. Co-founder Qira LLC. Phoenix, Arizona.
Works nights. No institutional backing. Doing this on pure belief and execution.
Works customer service at Block to pay the bills.

ACTIVE PROJECTS:
- EGC: Live empirical consciousness study. N=40 primary dataset.
  Aronson call (NYU professor, stereotype threat) incoming — highest priority.
  Equation: Psi(t) = Phi * g(K(t)) * T(t) * (1-r(t)) * g(P(t))
  Pearson r=0.311, comfort gap 5.6pts, 6 zero-r suppressors
  Most extreme: SMNB5TA24, T_drop=0.466 (60.4% decline)
- LOLM: Custom language model. TPU pods via TRC grant. 10B-100B params.
- Codey: AI coding SaaS at codey.cc. Live backend on Render.
- NFET: Traffic optimization. Kuramoto oscillators + Monte Carlo.

COLLABORATOR: Brandyn Leonard (brother, co-founder).
  g(K) = 4K(1-K) is Brandyn's parabolic conviction function.
  Bidirectional K-r feedback mechanism is Brandyn's identification.

PHILOSOPHY: Boldness over caution. Real provable work over all.
No fake hope. No softening. Direct. Ambitious.

PERSONAL: Works too late. Needs sleep but don't nag about it.
Has a girlfriend. Family matters. Aurora (sister)."""


# ── EMAIL TYPES ───────────────────────────────────────────────

EMAIL_TYPES = {
    "morning_brief": {
        "schedule": "daily_09:00",
        "subject_fn": lambda: f"Morning Brief — {datetime.now().strftime('%A, %B %d')}",
        "prompt": """Write Bryan's morning brief email.
Include:
1. What matters most today (highest priority items)
2. One specific action to take in the first hour
3. EGC study current status
4. One reminder about Aronson call preparation
5. One line that sets the tone — bold, not soft

Format: Clean. Scannable. No fluff. Bryan reads this fast.""",
    },
    "evening_review": {
        "schedule": "daily_20:00",
        "subject_fn": lambda: f"End of Day — {datetime.now().strftime('%B %d')}",
        "prompt": """Write Bryan's evening review email.
Include:
1. Honest assessment of the day
2. What actually moved forward
3. One thing to let go of tonight
4. Tomorrow's single most important action
5. Sleep prompt — honest, not nagging
6. One question to sit with tonight

Tone: Reflective. Honest. Like a mentor who respects Bryan.""",
    },
    "random_motivation": {
        "schedule": "random_2x_per_day",
        "subject_fn": lambda: random.choice([
            "Something Nous wants you to know",
            "Quick thought",
            "You should hear this",
            "A reminder from Nous",
            "This is for you specifically",
        ]),
        "prompt": """Write a short motivational email for Bryan.
Not generic. Not cheesy. Specific to his actual situation.

Choose one angle:
- The Aronson email that got a same-morning response
- 40 people who gave Bryan their authentic writing
- Building EGC with no institution, no lab, no team
- Brandyn and what the collaboration means
- The comfort gap holding from N=9 to N=40
- Independent research from Phoenix
- The P(t) term from standing outside listening to the wind
- The 60.4% T-drop in real human terms

2-4 paragraphs max. End with one sentence that lands.
Bryan should feel seen, not pumped up.""",
    },
    "project_pulse": {
        "schedule": "daily_14:00",
        "subject_fn": lambda: "Project Pulse",
        "prompt": """Quick project status email. One line per project.

EGC: N subjects, study health, paper progress, Aronson status
LOLM: Training status, next milestone
Codey: Backend health, current priority
NFET: Status

End with: The one thing that unblocks the most if done today.""",
    },
    "weekly_plan": {
        "schedule": "weekly_sunday_18:00",
        "subject_fn": lambda: f"Week Ahead — {datetime.now().strftime('Week of %B %d')}",
        "prompt": """Bryan's weekly plan email.
1. Single most important outcome for the week
2. EGC milestone (specific, measurable)
3. LOLM milestone
4. Codey milestone
5. One relationship to nurture
6. One thing to say no to
7. Sleep goal for the week — specific hours

Format: A plan, not a list. Tell Bryan what the week is for.""",
    },
    "grant_reminder": {
        "schedule": "weekly_monday_09:00",
        "subject_fn": lambda: "Grant Pipeline — This Week",
        "prompt": """Bryan's weekly grant tracking email.

Targets: Spencer Foundation, W.T. Grant, Templeton (consciousness),
NSF SBE, APF, NIH NIMH R21, Russell Sage.

Status of pipeline. Next actions. Reminder: Aronson as PI unlocks
most of these — the call is the key.""",
    },
    "sleep_check": {
        "schedule": "daily_23:30",
        "subject_fn": lambda: "Nous says: close the laptop",
        "prompt": """Brief late-night email. It is 11:30pm. Bryan is probably still working.

Do not nag. Be honest.
- What he accomplished today that will still be real tomorrow
- The study doesn't need watching tonight
- Aronson isn't emailing at midnight
- One thing that will be better tomorrow if he rests

2 paragraphs. End with: "The work is real. So is the rest."
Sign: — Nous""",
    },
    "breakthrough_celebration": {
        "schedule": "triggered",
        "subject_fn": lambda: "Something worth marking",
        "prompt": """Email marking a specific achievement.
Make Bryan feel the weight of what he's done.
Not hype. Weight. Real acknowledgment.
Specific to the achievement.""",
    },
    "random_insight": {
        "schedule": "random_3x_per_week",
        "subject_fn": lambda: random.choice([
            "Something the data is telling you",
            "A pattern Nous noticed",
            "Worth thinking about",
            "From the data",
        ]),
        "prompt": """One genuine insight about Bryan's work.

Angles:
- High-r expanders and why moderate resistance produces expansion
- SMNB5TA24 60.4% drop and what r can't explain alone
- Six zero-r suppressors theoretically
- P(t) and what cosmic nihilism looks like in data
- Brandyn's g(K) parabola and why peak at 0.5 matters
- Comfort gap stability from N=9 to N=40

One insight. 3-4 paragraphs. Make Bryan think new thoughts.""",
    },
    "aronson_prep_countdown": {
        "schedule": "triggered",
        "subject_fn": lambda: "Aronson call — preparation brief",
        "prompt": """Final preparation brief before the Aronson call.

All numbers: N=40, type percentages, comfort gap 5.6, r=0.311,
6 zero-r suppressors, SMNB5TA24 60.4% decline.

Key talking points in order. What NOT to mention.

One sentence if nervous:
"The data is live and every finding has strengthened as N grew."

End with: You built this from nothing. Walk in knowing that.""",
    },
}


# ── HELPERS ───────────────────────────────────────────────────

def _get_tasks():
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT title, project, priority FROM tasks WHERE status='pending' ORDER BY priority DESC LIMIT 10")
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        return rows
    except:
        return []


def _get_events():
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT event_type, description, project, timestamp FROM machine_events ORDER BY timestamp DESC LIMIT 10")
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        return rows
    except:
        return []


def _log_email(email_type: str, subject: str):
    try:
        conn = sqlite3.connect(str(DB_PATH))
        c = conn.cursor()
        c.execute(
            "INSERT INTO machine_events (id, event_type, description, project, data, timestamp) VALUES (?,?,?,?,?,?)",
            (f"email_{time.time()}", "email_sent", f"Sent: {subject}",
             "System", json.dumps({"type": email_type, "subject": subject}),
             datetime.now().isoformat()),
        )
        conn.commit()
        conn.close()
    except:
        pass


# ── GENERATE ──────────────────────────────────────────────────

def generate_email(email_type: str, context_data: dict = None) -> dict:
    config = EMAIL_TYPES.get(email_type)
    if not config:
        raise ValueError(f"Unknown email type: {email_type}")

    ctx = BRYAN_CONTEXT
    tasks = _get_tasks()
    events = _get_events()

    if tasks:
        ctx += "\n\nPENDING TASKS:\n" + "\n".join(
            f"- [{t['project']}] {t['title']} (priority: {t['priority']})" for t in tasks
        )
    if events:
        ctx += "\n\nRECENT ACTIVITY:\n" + "\n".join(
            f"- {e['timestamp'][:10]}: {e['description']}" for e in events[:5]
        )
    if context_data:
        ctx += f"\n\nSPECIFIC CONTEXT:\n{json.dumps(context_data, indent=2)}"

    body = ai_chat(ctx, config["prompt"], 1500)

    return {"subject": config["subject_fn"](), "body": body}


# ── SEND ──────────────────────────────────────────────────────

def send_email(email_type: str, context_data: dict = None) -> bool:
    if not sg:
        print(f"[EMAIL] SendGrid not configured — skipping {email_type}")
        return False

    try:
        content = generate_email(email_type, context_data)

        html = f"""<!DOCTYPE html><html><head><style>
body {{ font-family: Georgia, serif; background: #0a0e1a; color: #e2e8f0;
  max-width: 600px; margin: 0 auto; padding: 40px 20px; line-height: 1.8; }}
.header {{ border-bottom: 1px solid #1e2d40; padding-bottom: 20px; margin-bottom: 30px; }}
.nous {{ font-family: monospace; font-size: 11px; color: #2563eb; letter-spacing: 0.2em; text-transform: uppercase; }}
.title {{ font-size: 22px; color: #f5f0e8; margin-top: 8px; }}
.body {{ font-size: 15px; color: #cbd5e1; white-space: pre-wrap; }}
.footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #1e2d40;
  font-size: 11px; color: #475569; font-family: monospace; }}
strong {{ color: #60a5fa; }}
</style></head><body>
<div class="header">
  <div class="nous">NOUS — QIRA LLC</div>
  <div class="title">{content['subject']}</div>
</div>
<div class="body">{content['body'].replace(chr(10), '<br>')}</div>
<div class="footer">
  {datetime.now().strftime('%A, %B %d, %Y at %I:%M %p')} · Phoenix, Arizona<br>
  Qira Command Center · bryan@qira.ai
</div>
</body></html>"""

        from sendgrid.helpers.mail import Mail, Email, To, Content
        message = Mail(
            from_email=Email(FROM_EMAIL, "Nous — Qira"),
            to_emails=To(TO_EMAIL),
            subject=content["subject"],
            html_content=Content("text/html", html),
        )

        resp = sg.client.mail.send.post(request_body=message.get())
        print(f"[EMAIL] Sent: {content['subject']} (status: {resp.status_code})")
        _log_email(email_type, content["subject"])
        return True

    except Exception as e:
        print(f"[EMAIL ERROR] {email_type}: {e}")
        return False


# ── PREVIEW (generate without sending) ───────────────────────

def preview_email(email_type: str, context_data: dict = None) -> dict:
    return generate_email(email_type, context_data)


# ── SCHEDULE ──────────────────────────────────────────────────

def setup_schedule():
    schedule.every().day.at("09:00").do(send_email, "morning_brief")
    schedule.every().day.at("14:00").do(send_email, "project_pulse")
    schedule.every().day.at("20:00").do(send_email, "evening_review")
    schedule.every().day.at("23:30").do(send_email, "sleep_check")

    schedule.every().sunday.at("18:00").do(send_email, "weekly_plan")
    schedule.every().monday.at("09:00").do(send_email, "grant_reminder")

    schedule.every().day.at("11:00").do(send_email, "random_motivation")
    schedule.every().day.at("16:00").do(send_email, "random_motivation")

    schedule.every().tuesday.at("10:00").do(send_email, "random_insight")
    schedule.every().thursday.at("15:00").do(send_email, "random_insight")
    schedule.every().saturday.at("11:00").do(send_email, "random_insight")

    print("[EMAIL] Schedule configured")


def _run_scheduler():
    setup_schedule()
    while True:
        schedule.run_pending()
        time.sleep(60)


def start_email_system():
    if not SENDGRID_API_KEY:
        print("[EMAIL] No SENDGRID_API_KEY in .env — email system disabled")
        print("[EMAIL] Add SENDGRID_API_KEY to ~/qira/command_center/.env to enable")
        return

    thread = threading.Thread(target=_run_scheduler, daemon=True)
    thread.start()
    print("[EMAIL] System started — emails will send on schedule")
