"""Render deployment monitoring."""

import os
from pathlib import Path
import httpx

_env = {}
_env_path = Path.home() / "qira" / "command_center" / ".env"
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            _env[k.strip()] = v.strip()

RENDER_KEY = os.environ.get("RENDER_API_KEY", _env.get("RENDER_API_KEY", ""))


async def get_render_services():
    if not RENDER_KEY:
        return {"error": "No RENDER_API_KEY", "services": []}

    async with httpx.AsyncClient(timeout=10.0) as http:
        resp = await http.get(
            "https://api.render.com/v1/services",
            headers={"Authorization": f"Bearer {RENDER_KEY}", "Accept": "application/json"},
            params={"limit": 20},
        )
        if resp.status_code != 200:
            return {"error": f"Render API {resp.status_code}", "services": []}

        data = resp.json()
        services = []
        for item in data:
            svc = item.get("service", item)
            services.append({
                "id": svc.get("id", ""),
                "name": svc.get("name", ""),
                "type": svc.get("type", ""),
                "status": svc.get("suspended", "unknown"),
                "url": svc.get("serviceDetails", {}).get("url", "")
                       or f"https://{svc.get('slug', '')}.onrender.com",
                "repo": svc.get("repo", ""),
                "branch": svc.get("branch", ""),
                "created_at": svc.get("createdAt", ""),
                "updated_at": svc.get("updatedAt", ""),
                "region": svc.get("region", ""),
            })

        return {"services": services, "count": len(services)}


async def get_render_deploys(service_id: str):
    if not RENDER_KEY:
        return {"error": "No RENDER_API_KEY", "deploys": []}

    async with httpx.AsyncClient(timeout=10.0) as http:
        resp = await http.get(
            f"https://api.render.com/v1/services/{service_id}/deploys",
            headers={"Authorization": f"Bearer {RENDER_KEY}", "Accept": "application/json"},
            params={"limit": 10},
        )
        if resp.status_code != 200:
            return {"error": f"Render API {resp.status_code}", "deploys": []}

        data = resp.json()
        deploys = []
        for item in data:
            d = item.get("deploy", item)
            deploys.append({
                "id": d.get("id", ""),
                "status": d.get("status", ""),
                "commit_message": d.get("commit", {}).get("message", ""),
                "created_at": d.get("createdAt", ""),
                "finished_at": d.get("finishedAt", ""),
            })

        return {"deploys": deploys}
