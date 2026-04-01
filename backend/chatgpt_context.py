"""Build ChatGPT conversation context for injection into Nous and Council agents."""

import sqlite3
import json
from pathlib import Path

DB_PATH = Path.home() / "qira" / "command_center" / "data" / "nucleus.db"


def build_chatgpt_context(limit=30):
    """Build a context string from ChatGPT conversations for Nous injection."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Get most substantial ChatGPT conversations
    c.execute("""SELECT title, summary, content FROM conversations 
        WHERE source = 'chatgpt' AND content != '' 
        ORDER BY date DESC LIMIT ?""", (limit,))
    convos = [dict(r) for r in c.fetchall()]

    # Get recent ChatGPT prompts with substance
    c.execute("""SELECT title, content FROM knowledge 
        WHERE source = 'chatgpt' AND length(content) > 100 
        ORDER BY created_at DESC LIMIT 50""")
    prompts = [dict(r) for r in c.fetchall()]

    conn.close()

    if not convos and not prompts:
        return ""

    ctx = "\n\nCHATGPT HISTORY CONTEXT (329 conversations, 4870 prompts from Aug 2023 - Mar 2026):\n"
    ctx += "Bryan used ChatGPT heavily before switching to Claude. Key patterns: writing (41%), building (29%), learning (25%), debugging (17%).\n"
    ctx += "Top tech: API, Python, Linux, OpenAI, JSON, JavaScript, React.\n"
    ctx += "Domains: creative (58%), personal (46%), AI/ML (41%), EGC (40%), psychology (36%), Codey (26%), NFET (20%).\n\n"

    ctx += "RECENT CHATGPT CONVERSATIONS (reference these when relevant):\n"
    for convo in convos[:15]:
        ctx += f"- {convo['title']}: {convo['summary'][:100]}\n"

    ctx += "\nSAMPLE PROMPTS (Bryan's actual questions/requests to ChatGPT):\n"
    for p in prompts[:10]:
        ctx += f"- [{p['title']}]: {p['content'][:150]}...\n"

    return ctx


def search_chatgpt(query, limit=10):
    """Search ChatGPT conversations and prompts."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("""SELECT 'conversation' as type, title, summary as content FROM conversations 
        WHERE source = 'chatgpt' AND (title LIKE ? OR summary LIKE ?)
        UNION ALL
        SELECT 'prompt' as type, title, content FROM knowledge 
        WHERE source = 'chatgpt' AND content LIKE ?
        LIMIT ?""", (f"%{query}%", f"%{query}%", f"%{query}%", limit))

    results = [dict(r) for r in c.fetchall()]
    conn.close()
    return results
