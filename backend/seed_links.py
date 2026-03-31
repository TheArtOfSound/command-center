"""Seed all known project URLs into the command center database."""

import sqlite3
import json
from pathlib import Path

DB_PATH = Path.home() / "qira" / "command_center" / "data" / "nucleus.db"


def seed_links():
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()

    # Create links table
    c.execute("""CREATE TABLE IF NOT EXISTS project_links (
        id TEXT PRIMARY KEY,
        project TEXT NOT NULL,
        name TEXT NOT NULL,
        url TEXT NOT NULL,
        type TEXT DEFAULT 'web',
        check_type TEXT DEFAULT 'none',
        check_port INTEGER DEFAULT 0,
        description TEXT DEFAULT '',
        is_public INTEGER DEFAULT 1
    )""")

    # Clear and reseed
    c.execute("DELETE FROM project_links")

    links = [
        # EGC
        ("egc_study", "EGC", "Live Study", "https://theartofsound.github.io/egcstudy/", "web", "http", 0, "Live EGC study for participants", 1),
        ("egc_gate", "EGC", "Research Page (The Gate)", "https://theartofsound.github.io/thegate/", "web", "http", 0, "Public research page with live stats", 1),
        ("egc_rater", "EGC", "Rater Interface", "https://theartofsound.github.io/egcstudy/egcrate/", "web", "http", 0, "Rater validation interface", 1),
        ("egc_preprint", "EGC", "Preprint (Zenodo)", "https://zenodo.org/records/19242315", "web", "none", 0, "EGC preprint — note: says N=14, current N=40+", 1),
        ("egc_repo_study", "EGC", "GitHub: egcstudy", "https://github.com/TheArtOfSound/egcstudy", "github", "none", 0, "Study site source code", 1),
        ("egc_repo_gate", "EGC", "GitHub: thegate", "https://github.com/TheArtOfSound/thegate", "github", "none", 0, "Research page source code", 1),

        # Codey
        ("codey_landing", "Codey", "Landing Page", "https://theartofsound.github.io/codey/", "web", "http", 0, "Public landing page", 1),
        ("codey_repo", "Codey", "GitHub: codey", "https://github.com/TheArtOfSound/codey", "github", "none", 0, "Codey source code", 1),
        ("codey_render", "Codey", "Backend (Render)", "https://render.com/dashboard", "web", "none", 0, "Render deployment dashboard", 0),
        ("codey_stripe", "Codey", "Stripe Dashboard", "https://dashboard.stripe.com", "web", "none", 0, "Billing and payments", 0),

        # NFET
        ("nfet_local", "NFET", "Local Dashboard", "http://localhost:8000", "local", "port", 8000, "NFET server — only active when running", 0),

        # LOLM
        ("lolm_trc", "LOLM", "TRC Application", "https://sites.research.google/trc/", "web", "none", 0, "Google TPU Research Cloud", 1),
        ("lolm_hf", "LOLM", "HuggingFace C4 Dataset", "https://huggingface.co/datasets/allenai/c4", "web", "none", 0, "Training data source", 1),
        ("lolm_gcloud", "LOLM", "Google Cloud Console", "https://console.cloud.google.com", "web", "none", 0, "TPU VM management", 0),
        ("lolm_repo", "LOLM", "GitHub: lolm", "https://github.com/TheArtOfSound/lolm", "github", "none", 0, "LOLM source code", 1),

        # Command Center / System
        ("cc_portfolio", "System", "Public Portfolio", "https://theartofsound.github.io/portfolio/", "web", "http", 0, "5-act immersive portfolio", 1),
        ("cc_private", "System", "Private Command Center", "https://theartofsound.github.io/command-center", "web", "http", 0, "Password-protected command center", 0),
        ("cc_local_fe", "System", "Local Frontend", "http://localhost:3000", "local", "port", 3000, "Local command center frontend", 0),
        ("cc_local_be", "System", "Local Backend", "http://localhost:7777", "local", "port", 7777, "Local FastAPI backend", 0),
        ("cc_repo", "System", "GitHub: command-center", "https://github.com/TheArtOfSound/command-center", "github", "none", 0, "Command center source", 1),
        ("cc_portfolio_repo", "System", "GitHub: portfolio", "https://github.com/TheArtOfSound/portfolio", "github", "none", 0, "Portfolio source", 1),

        # Qira LLC
        ("qira_github", "Qira", "GitHub Organization", "https://github.com/TheArtOfSound", "github", "none", 0, "All repositories", 1),
        ("qira_linkedin", "Qira", "LinkedIn", "https://www.linkedin.com/in/bryan-leonard-54155218a/", "web", "none", 0, "Bryan's LinkedIn profile", 1),

        # External Services
        ("svc_supabase", "System", "Supabase Dashboard", "https://supabase.com/dashboard", "web", "none", 0, "EGC database — table: egc_responses", 0),
        ("svc_render", "System", "Render Dashboard", "https://render.com/dashboard", "web", "none", 0, "Codey backend hosting", 0),
        ("svc_sendgrid", "System", "SendGrid", "https://app.sendgrid.com", "web", "none", 0, "Email automation", 0),
        ("svc_anthropic", "System", "Anthropic Console", "https://console.anthropic.com", "web", "none", 0, "Claude API", 0),
    ]

    for link in links:
        c.execute("INSERT OR REPLACE INTO project_links VALUES (?,?,?,?,?,?,?,?,?)", link)

    conn.commit()
    conn.close()
    print(f"Seeded {len(links)} project links")


if __name__ == "__main__":
    seed_links()
