"""Infrastructure health check grid — checks all services in parallel."""

import asyncio
import socket
import subprocess
import json
from datetime import datetime

import httpx


async def check_all() -> dict:
    """Run all health checks in parallel and return a grid."""
    results = {}

    async with httpx.AsyncClient(timeout=5.0) as http:
        checks = await asyncio.gather(
            _check_url(http, "egc_study", "https://theartofsound.github.io/egcstudy/"),
            _check_url(http, "thegate", "https://theartofsound.github.io/thegate/"),
            _check_url(http, "egcrate", "https://theartofsound.github.io/egcstudy/egcrate/"),
            _check_url(http, "portfolio", "https://theartofsound.github.io/portfolio/"),
            _check_url(http, "codey_landing", "https://theartofsound.github.io/codey/"),
            _check_url(http, "zenodo", "https://zenodo.org/records/19242315"),
            _check_supabase(http),
            _check_sendgrid(),
            return_exceptions=True,
        )

    for check in checks:
        if isinstance(check, dict):
            results.update(check)

    # Local port checks
    for name, port in [("nfet", 8000), ("frontend", 3000), ("backend", 7777)]:
        results[name] = {
            "name": name,
            "type": "local",
            "port": port,
            "status": "up" if _port_open(port) else "down",
            "latency_ms": 0,
        }

    # GitHub — last push
    try:
        gh = subprocess.run(
            ["gh", "api", "/users/TheArtOfSound/events?per_page=1"],
            capture_output=True, text=True, timeout=5,
        )
        if gh.returncode == 0:
            events = json.loads(gh.stdout)
            if events:
                results["github"] = {
                    "name": "github",
                    "type": "api",
                    "status": "up",
                    "last_event": events[0].get("created_at", ""),
                    "event_type": events[0].get("type", ""),
                }
            else:
                results["github"] = {"name": "github", "type": "api", "status": "up", "last_event": ""}
        else:
            results["github"] = {"name": "github", "type": "api", "status": "degraded"}
    except Exception:
        results["github"] = {"name": "github", "type": "api", "status": "down"}

    results["timestamp"] = datetime.now().isoformat()
    results["total_up"] = sum(1 for k, v in results.items() if isinstance(v, dict) and v.get("status") == "up")
    results["total_checks"] = sum(1 for k, v in results.items() if isinstance(v, dict) and "status" in v)

    return results


async def _check_url(http: httpx.AsyncClient, name: str, url: str) -> dict:
    try:
        start = asyncio.get_event_loop().time()
        resp = await http.head(url, follow_redirects=True)
        latency = round((asyncio.get_event_loop().time() - start) * 1000)
        status = "up" if resp.status_code == 200 else "degraded" if resp.status_code < 500 else "down"
        return {name: {"name": name, "type": "web", "url": url, "status": status,
                       "http_code": resp.status_code, "latency_ms": latency}}
    except Exception as e:
        return {name: {"name": name, "type": "web", "url": url, "status": "down",
                       "error": str(e), "latency_ms": 0}}


async def _check_supabase(http: httpx.AsyncClient) -> dict:
    url = "https://wgzopjrdnyazvhpklzhw.supabase.co"
    key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Indnem9wanJkbnlhenZocGtsemh3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQzOTc4NzcsImV4cCI6MjA4OTk3Mzg3N30.8dx5xWljLDZa5PMvE0Ps5q4ZEyuZgx_5FHVnD0WfBjs"
    try:
        start = asyncio.get_event_loop().time()
        resp = await http.get(
            f"{url}/rest/v1/egc_responses?select=id&limit=1",
            headers={"apikey": key, "Authorization": f"Bearer {key}"},
        )
        latency = round((asyncio.get_event_loop().time() - start) * 1000)
        status = "up" if resp.status_code == 200 else "degraded"
        return {"supabase": {"name": "supabase", "type": "database", "status": status,
                             "latency_ms": latency, "http_code": resp.status_code}}
    except Exception as e:
        return {"supabase": {"name": "supabase", "type": "database", "status": "down",
                             "error": str(e), "latency_ms": 0}}


async def _check_sendgrid() -> dict:
    from pathlib import Path
    env_path = Path.home() / "qira" / "command_center" / ".env"
    has_key = False
    if env_path.exists():
        has_key = "SENDGRID_API_KEY=" in env_path.read_text()
    return {"sendgrid": {"name": "sendgrid", "type": "email",
                         "status": "configured" if has_key else "not_configured"}}


def _port_open(port: int) -> bool:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        s.connect(("localhost", port))
        s.close()
        return True
    except Exception:
        return False
