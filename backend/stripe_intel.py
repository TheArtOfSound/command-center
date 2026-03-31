"""Stripe billing monitoring for Codey."""

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

STRIPE_KEY = os.environ.get("STRIPE_SECRET_KEY", _env.get("STRIPE_SECRET_KEY", ""))
STRIPE_BASE = "https://api.stripe.com/v1"


async def get_stripe_overview():
    if not STRIPE_KEY:
        return {"error": "No STRIPE_SECRET_KEY", "connected": False}

    headers = {"Authorization": f"Bearer {STRIPE_KEY}"}

    async with httpx.AsyncClient(timeout=10.0) as http:
        results = {"connected": True}

        # Balance
        try:
            resp = await http.get(f"{STRIPE_BASE}/balance", headers=headers)
            if resp.status_code == 200:
                bal = resp.json()
                available = bal.get("available", [])
                pending = bal.get("pending", [])
                results["balance"] = {
                    "available": sum(a.get("amount", 0) for a in available) / 100,
                    "pending": sum(p.get("amount", 0) for p in pending) / 100,
                    "currency": available[0].get("currency", "usd") if available else "usd",
                }
            else:
                results["balance"] = {"error": resp.status_code}
        except Exception as e:
            results["balance"] = {"error": str(e)}

        # Recent charges
        try:
            resp = await http.get(f"{STRIPE_BASE}/charges", headers=headers, params={"limit": 10})
            if resp.status_code == 200:
                charges = resp.json().get("data", [])
                results["recent_charges"] = [
                    {
                        "id": c["id"],
                        "amount": c.get("amount", 0) / 100,
                        "status": c.get("status", ""),
                        "customer": c.get("customer", ""),
                        "created": c.get("created", 0),
                        "description": c.get("description", ""),
                    }
                    for c in charges
                ]
                results["total_charges"] = len(charges)
            else:
                results["recent_charges"] = []
        except:
            results["recent_charges"] = []

        # Customers
        try:
            resp = await http.get(f"{STRIPE_BASE}/customers", headers=headers, params={"limit": 100})
            if resp.status_code == 200:
                customers = resp.json().get("data", [])
                results["total_customers"] = len(customers)
                results["recent_customers"] = [
                    {"id": c["id"], "email": c.get("email", ""), "name": c.get("name", ""),
                     "created": c.get("created", 0)}
                    for c in customers[:5]
                ]
            else:
                results["total_customers"] = 0
        except:
            results["total_customers"] = 0

        # Subscriptions
        try:
            resp = await http.get(f"{STRIPE_BASE}/subscriptions", headers=headers, params={"limit": 100})
            if resp.status_code == 200:
                subs = resp.json().get("data", [])
                results["subscriptions"] = {
                    "total": len(subs),
                    "active": sum(1 for s in subs if s.get("status") == "active"),
                    "trialing": sum(1 for s in subs if s.get("status") == "trialing"),
                    "canceled": sum(1 for s in subs if s.get("status") == "canceled"),
                }
                # MRR calculation
                mrr = sum(
                    s.get("plan", {}).get("amount", 0)
                    for s in subs
                    if s.get("status") in ("active", "trialing")
                ) / 100
                results["mrr"] = mrr
            else:
                results["subscriptions"] = {"total": 0}
                results["mrr"] = 0
        except:
            results["subscriptions"] = {"total": 0}
            results["mrr"] = 0

        # Products
        try:
            resp = await http.get(f"{STRIPE_BASE}/products", headers=headers, params={"limit": 20, "active": "true"})
            if resp.status_code == 200:
                products = resp.json().get("data", [])
                results["products"] = [
                    {"id": p["id"], "name": p.get("name", ""), "active": p.get("active", False)}
                    for p in products
                ]
            else:
                results["products"] = []
        except:
            results["products"] = []

        return results
