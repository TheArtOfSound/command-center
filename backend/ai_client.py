"""Unified AI client for the Command Center.

Tries providers in order: Groq (free, fast) -> Ollama (local) -> Gemini.
All API keys read from .env only.
"""

import os
from pathlib import Path

# Load .env
_env_path = Path.home() / "qira" / "command_center" / ".env"
_env = {}
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            _env[k.strip()] = v.strip()

GROQ_KEY = os.environ.get("GROQ_API_KEY", _env.get("GROQ_API_KEY", ""))
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", _env.get("GEMINI_API_KEY", ""))
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", _env.get("ANTHROPIC_API_KEY", ""))


def chat(system: str, message: str, max_tokens: int = 2000) -> str:
    """Send a chat message using the best available AI provider."""

    # Try Groq first (free, fast)
    if GROQ_KEY:
        try:
            return _groq_chat(system, message, max_tokens)
        except Exception as e:
            print(f"[AI] Groq failed: {e}")

    # Try Ollama (local)
    try:
        return _ollama_chat(system, message)
    except Exception as e:
        print(f"[AI] Ollama failed: {e}")

    # Try Anthropic if available
    if ANTHROPIC_KEY:
        try:
            return _anthropic_chat(system, message, max_tokens)
        except Exception as e:
            print(f"[AI] Anthropic failed: {e}")

    # Try Gemini
    if GEMINI_KEY:
        try:
            return _gemini_chat(system, message, max_tokens)
        except Exception as e:
            print(f"[AI] Gemini failed: {e}")

    return "All AI providers unavailable. Check API keys in .env."


def chat_fast(system: str, message: str) -> str:
    """Fast classification call — Groq or Ollama only."""
    if GROQ_KEY:
        try:
            return _groq_chat(system, message, 500)
        except:
            pass
    try:
        return _ollama_chat(system, message)
    except:
        pass
    return "{}"


def _groq_chat(system: str, message: str, max_tokens: int = 2000) -> str:
    from groq import Groq
    client = Groq(api_key=GROQ_KEY)
    resp = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": message},
        ],
        max_tokens=max_tokens,
        temperature=0.7,
    )
    return resp.choices[0].message.content


def _ollama_chat(system: str, message: str) -> str:
    import httpx
    resp = httpx.post(
        "http://localhost:11434/api/chat",
        json={
            "model": "llama3.1",
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": message},
            ],
            "stream": False,
        },
        timeout=120.0,
    )
    return resp.json()["message"]["content"]


def _anthropic_chat(system: str, message: str, max_tokens: int = 2000) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
    resp = client.messages.create(
        model="claude-sonnet-4-5-20250514",
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": message}],
    )
    return resp.content[0].text


def _gemini_chat(system: str, message: str, max_tokens: int = 2000) -> str:
    import httpx
    resp = httpx.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}",
        json={
            "contents": [{"parts": [{"text": f"{system}\n\n{message}"}]}],
            "generationConfig": {"maxOutputTokens": max_tokens},
        },
        timeout=30.0,
    )
    data = resp.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]
