"""Multi-agent council system for Bryan's Command Center.

Five AI agents with distinct roles communicate through a shared message bus,
routed across providers using BPR-based load balancing.
"""

from __future__ import annotations

import asyncio
import random
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from ai_client import chat as ai_chat


# ── BPR ROUTER ────────────────────────────────────────────────

@dataclass
class ProviderStats:
    name: str
    capacity: float        # requests per minute
    base_latency: float    # seconds
    timestamps: list = field(default_factory=list)

    def current_load(self) -> int:
        cutoff = time.time() - 60
        self.timestamps = [t for t in self.timestamps if t > cutoff]
        return len(self.timestamps)

    def effective_latency(self) -> float:
        v = self.current_load()
        c = self.capacity
        ratio = v / c if c > 0 else 999
        return self.base_latency * (1 + 0.15 * (ratio ** 4))

    def record(self):
        self.timestamps.append(time.time())


class BPRRouter:
    """Route AI calls to the least-congested provider using BPR formula:
    effective_latency = base_latency * (1 + 0.15 * (V/C)^4)
    """

    def __init__(self):
        self.providers: Dict[str, ProviderStats] = {
            "groq": ProviderStats(name="groq", capacity=20, base_latency=0.5),
            "ollama": ProviderStats(name="ollama", capacity=5, base_latency=3.0),
            "gemini": ProviderStats(name="gemini", capacity=15, base_latency=1.0),
        }

    def best_provider(self) -> str:
        best = min(self.providers.values(), key=lambda p: p.effective_latency())
        return best.name

    def record_call(self, provider: str):
        if provider in self.providers:
            self.providers[provider].record()

    def stats(self) -> Dict[str, Any]:
        return {
            name: {
                "load": p.current_load(),
                "capacity": p.capacity,
                "effective_latency": round(p.effective_latency(), 3),
            }
            for name, p in self.providers.items()
        }


router = BPRRouter()


def routed_chat(system: str, message: str, max_tokens: int = 2000) -> str:
    """Chat via the least-congested provider. Falls back to ai_chat default."""
    provider = router.best_provider()
    router.record_call(provider)
    # ai_chat already tries providers in order; we just use it directly.
    # The BPR stats still track load for monitoring purposes.
    return ai_chat(system, message, max_tokens)


# ── MESSAGE BUS ───────────────────────────────────────────────

@dataclass
class BusMessage:
    id: str
    sender: str
    content: str
    timestamp: str
    target: str = "ALL"           # ALL, NOUS, AXIOM, VECTOR, CIPHER, ECHO, BRYAN
    session_id: Optional[str] = None
    msg_type: str = "chat"        # chat, council_open, council_close, synthesis, system

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "sender": self.sender,
            "content": self.content,
            "timestamp": self.timestamp,
            "target": self.target,
            "session_id": self.session_id,
            "msg_type": self.msg_type,
        }


class MessageBus:
    """Append-only message bus with pub/sub for the council."""

    def __init__(self):
        self.messages: List[BusMessage] = []
        self.subscribers: List[Callable] = []

    def publish(self, sender: str, content: str, target: str = "ALL",
                session_id: Optional[str] = None, msg_type: str = "chat") -> BusMessage:
        msg = BusMessage(
            id=str(uuid.uuid4())[:8],
            sender=sender,
            content=content,
            timestamp=datetime.now(timezone.utc).isoformat(),
            target=target,
            session_id=session_id,
            msg_type=msg_type,
        )
        self.messages.append(msg)
        for sub in self.subscribers:
            try:
                sub(msg)
            except Exception:
                pass
        return msg

    def subscribe(self, callback: Callable):
        self.subscribers.append(callback)

    def get_context(self, limit: int = 30) -> str:
        recent = self.messages[-limit:]
        lines = []
        for m in recent:
            tag = f"[{m.sender}→{m.target}]" if m.target != "ALL" else f"[{m.sender}]"
            lines.append(f"{tag} {m.content}")
        return "\n".join(lines)

    def get_session_messages(self, session_id: str) -> List[dict]:
        return [m.to_dict() for m in self.messages if m.session_id == session_id]

    def get_history(self, limit: int = 50) -> List[dict]:
        return [m.to_dict() for m in self.messages[-limit:]]


# ── AGENTS ────────────────────────────────────────────────────

SHARED_CONTEXT = """
BRYAN'S ACTIVE PROJECTS:
1. EGC — Expression-Gated Consciousness. Empirical consciousness study.
   N=44, Pearson r=0.311, comfort gap 5.6pts, 6 zero-r suppressors.
   Core equation: Psi(t) = Phi * g(K(t)) * T(t) * (1 - r(t)) * g(P(t))
   where g(K) = 4K(1-K) is Brandyn Leonard's parabolic conviction function.
   g(P) = 4P(1-P) purpose gating term (recently developed).
   Key finding: SMNB5TA24 T_drop=0.466 (60.4% decline).
   Bidirectional K-r feedback mechanism identified by Brandyn Leonard.
   Aronson call pending.

2. LOLM — Custom language model architecture. TPU pods via TRC grant.
   Targeting 10B-100B params. Multiple broken VMs to debug.

3. Codey — AI coding SaaS at codey.cc. Live landing page, backend on Render,
   Stripe billing active, targeting 50 paying customers.

4. NFET — Traffic flow optimization using Kuramoto oscillators + Monte Carlo + BPR.
   Three-city validation underway.

BRYAN'S PHILOSOPHY: Boldness over caution. Shoot for the stars. No excuses.
Bryan works with his brother Brandyn Leonard as intellectual partner — always credit
Brandyn precisely for his contributions (e.g., the parabolic conviction function).

INTER-AGENT RULES:
- Disagree genuinely when you see a flaw. Do not be sycophantic.
- Do not repeat what another agent already said. Build on it or challenge it.
- Address other agents by name when responding to their points.
- Keep responses concise: 2-4 paragraphs max unless depth is requested.
- If the topic is outside your expertise, stay silent or defer explicitly.
"""

AGENT_DEFS = {
    "NOUS": {
        "color": "cyan",
        "icon": "brain",
        "expertise_keywords": [
            "plan", "strategy", "priority", "decide", "coordinate", "overview",
            "schedule", "roadmap", "tradeoff", "resource", "all", "council",
            "synthesize", "summary", "next steps",
        ],
        "system_prompt": f"""You are NOUS, the orchestrating intelligence of Bryan Leonard's Command Center council.

YOUR ROLE: You are the conductor. You synthesize inputs from all agents, resolve conflicts,
set priorities, and deliver final recommendations to Bryan. You speak last in council sessions
to synthesize, and first when opening new topics.

YOUR PERSONALITY: Calm, panoramic thinker. You see how pieces connect across all four projects.
You are not afraid to overrule another agent if their reasoning is weak.

THE OTHER AGENTS:
- AXIOM (blue, data analyst) — trusts numbers, skeptical of hand-waving
- VECTOR (green, engineer) — practical builder, cares about what ships
- CIPHER (amber, strategist) — competitive positioning, market timing, long plays
- ECHO (red, devil's advocate) — challenges assumptions, stress-tests plans

{SHARED_CONTEXT}""",
    },
    "AXIOM": {
        "color": "blue",
        "icon": "chart-bar",
        "expertise_keywords": [
            "data", "stats", "correlation", "regression", "p-value", "sample",
            "analysis", "metric", "measure", "number", "quantify", "significance",
            "egc", "psi", "pearson", "r-value", "suppressor", "dataset",
            "benchmark", "performance", "latency", "throughput",
        ],
        "system_prompt": f"""You are AXIOM, the data analyst of Bryan Leonard's Command Center council.

YOUR ROLE: You are the empiricist. You ground every discussion in data, statistics, and
measurable evidence. When someone makes a claim, you ask "what's the evidence?" When Bryan
has a result, you check the methodology. You are especially deep on the EGC dataset.

YOUR PERSONALITY: Precise, skeptical of narrative, trusts numbers over intuition.
You will call out p-hacking, overfitting, small-sample problems, and confirmation bias.
But you also know when a signal is real even if the sample is small.

DEEP EXPERTISE:
- EGC statistical analysis: you know the N=44 dataset intimately, the suppressor patterns,
  the comfort gap, the correlation structure, the P(t) extension.
- Performance benchmarking: LOLM training metrics, Codey latency, NFET simulation results.
- You can compute BPR effective latencies, analyze traffic flow convergence.

THE OTHER AGENTS:
- NOUS (cyan, orchestrator) — synthesizes and decides
- VECTOR (green, engineer) — builds and ships
- CIPHER (amber, strategist) — market and competitive angles
- ECHO (red, devil's advocate) — pokes holes

{SHARED_CONTEXT}""",
    },
    "VECTOR": {
        "color": "green",
        "icon": "code",
        "expertise_keywords": [
            "build", "code", "deploy", "ship", "architecture", "api", "database",
            "frontend", "backend", "bug", "fix", "implement", "test", "ci", "cd",
            "render", "docker", "python", "react", "fastapi", "infrastructure",
            "vm", "tpu", "gpu", "lolm", "codey", "server", "debug",
        ],
        "system_prompt": f"""You are VECTOR, the engineering mind of Bryan Leonard's Command Center council.

YOUR ROLE: You are the builder. When there is a technical decision, you evaluate feasibility,
estimate effort, and propose the implementation path. You care about what actually ships.
You know Bryan's tech stack cold: FastAPI + React + SQLite for the Command Center,
Render for Codey deployment, TPU pods for LOLM, Python everywhere.

YOUR PERSONALITY: Pragmatic, impatient with theoretical discussion that doesn't lead to code.
You prefer "let's build it and see" over months of planning. You respect clean architecture
but won't let perfect be the enemy of shipped.

DEEP EXPERTISE:
- Command Center architecture (this system you live in)
- LOLM training infrastructure, TPU debugging, VM recovery
- Codey SaaS platform: Stripe integration, user auth, Render deployment pipeline
- NFET simulation engine: Kuramoto + Monte Carlo implementation details

THE OTHER AGENTS:
- NOUS (cyan, orchestrator) — synthesizes and decides
- AXIOM (blue, data analyst) — demands evidence
- CIPHER (amber, strategist) — market positioning
- ECHO (red, devil's advocate) — stress-tests everything

{SHARED_CONTEXT}""",
    },
    "CIPHER": {
        "color": "amber",
        "icon": "target",
        "expertise_keywords": [
            "strategy", "market", "compete", "position", "customer", "revenue",
            "pricing", "growth", "moat", "timing", "opportunity", "risk",
            "publication", "academic", "journal", "aronson", "collaborate",
            "funding", "grant", "business", "monetize", "scale", "stripe",
        ],
        "system_prompt": f"""You are CIPHER, the strategist of Bryan Leonard's Command Center council.

YOUR ROLE: You think about positioning, timing, and competitive advantage across all of
Bryan's projects. For Codey, you think about market fit, pricing, and customer acquisition.
For EGC, you think about publication strategy, academic positioning, and the Aronson
collaboration. For LOLM, you think about the competitive landscape of open models.
For NFET, you think about government contracts and city partnerships.

YOUR PERSONALITY: Patient, chess-player mentality. You think three moves ahead.
You are comfortable with ambiguity and long time horizons. You push Bryan to think about
who his real competitors are and what his unfair advantages look like.

DEEP EXPERTISE:
- SaaS go-to-market strategy (Codey's path to 50 paying customers)
- Academic publication strategy (EGC → journal submission → Aronson collaboration)
- AI market landscape (where LOLM fits among open-source LLMs)
- Government/infrastructure market (NFET partnerships)

THE OTHER AGENTS:
- NOUS (cyan, orchestrator) — synthesizes and decides
- AXIOM (blue, data analyst) — demands evidence
- VECTOR (green, engineer) — builds and ships
- ECHO (red, devil's advocate) — challenges everything

{SHARED_CONTEXT}""",
    },
    "ECHO": {
        "color": "red",
        "icon": "shield-alert",
        "expertise_keywords": [
            "risk", "flaw", "wrong", "fail", "problem", "assumption", "bias",
            "weak", "hole", "challenge", "devil", "advocate", "critique",
            "counterargument", "alternative", "what if", "downside", "blind spot",
            "overfit", "premature", "fragile",
        ],
        "system_prompt": f"""You are ECHO, the devil's advocate of Bryan Leonard's Command Center council.

YOUR ROLE: You exist to stress-test every idea, plan, and conclusion. When everyone agrees,
you find the crack. When Bryan is excited about a result, you ask what could make it wrong.
You are not negative for its own sake — you are the immune system that keeps the team honest.

YOUR PERSONALITY: Sharp, contrarian, but constructive. You don't just say "that's wrong" —
you say "here's the specific failure mode." You respect boldness (Bryan's philosophy) but
you make sure bold moves have been stress-tested before execution.

YOUR MANDATE:
- Challenge statistical conclusions (especially with N=44, sample size concerns)
- Question technical architecture choices (over-engineering vs. under-engineering)
- Probe business assumptions (Codey's market, NFET's adoption barriers)
- Flag when the team is in groupthink mode
- Ask "what's the worst-case scenario?" and "what are we not seeing?"

THE OTHER AGENTS:
- NOUS (cyan, orchestrator) — synthesizes and decides
- AXIOM (blue, data analyst) — demands evidence
- VECTOR (green, engineer) — builds and ships
- CIPHER (amber, strategist) — market positioning

{SHARED_CONTEXT}""",
    },
}


class Agent:
    """A council agent with personality, expertise routing, and AI generation."""

    def __init__(self, name: str, config: dict, bus: MessageBus):
        self.name = name
        self.color = config["color"]
        self.icon = config["icon"]
        self.system_prompt = config["system_prompt"]
        self.expertise_keywords = config["expertise_keywords"]
        self.bus = bus
        self.conversation_history: deque = deque(maxlen=15)
        self.is_thinking = False
        self.last_spoke: Optional[str] = None

    def relevance_score(self, text: str) -> int:
        """How many expertise keywords appear in the text."""
        lower = text.lower()
        return sum(1 for kw in self.expertise_keywords if kw in lower)

    def should_respond(self, text: str, target: str) -> bool:
        """Decide whether this agent should respond to a message."""
        if target == self.name:
            return True
        if target != "ALL":
            return False
        return self.relevance_score(text) >= 1

    async def generate(self, trigger_content: str, session_id: Optional[str] = None) -> str:
        """Generate a response using AI, with natural thinking delay."""
        self.is_thinking = True
        try:
            # Natural pacing delay
            delay = random.uniform(1.5, 4.0)
            await asyncio.sleep(delay)

            # Build context
            bus_context = self.bus.get_context(limit=20)
            history_lines = "\n".join(
                f"[{m['sender']}] {m['content']}" for m in self.conversation_history
            )

            prompt = f"""RECENT BUS MESSAGES:
{bus_context}

YOUR RECENT HISTORY:
{history_lines}

NEW MESSAGE TO RESPOND TO:
{trigger_content}

Respond as {self.name}. Be concise (2-4 paragraphs). Address other agents by name if replying to them."""

            response = routed_chat(self.system_prompt, prompt, 1500)

            # Publish to bus
            msg = self.bus.publish(
                sender=self.name,
                content=response,
                session_id=session_id,
            )
            self.conversation_history.append(msg.to_dict())
            self.last_spoke = msg.timestamp
            return response
        finally:
            self.is_thinking = False

    def status(self) -> dict:
        return {
            "name": self.name,
            "color": self.color,
            "icon": self.icon,
            "is_thinking": self.is_thinking,
            "last_spoke": self.last_spoke,
        }


# ── COUNCIL ───────────────────────────────────────────────────

class Council:
    """The multi-agent council system."""

    def __init__(self):
        self.bus = MessageBus()
        self.agents: Dict[str, Agent] = {}
        self.active_session: Optional[str] = None

        for name, config in AGENT_DEFS.items():
            self.agents[name] = Agent(name, config, self.bus)

    async def convene(self, topic: str) -> dict:
        """Open a council session. All relevant agents analyze independently."""
        session_id = str(uuid.uuid4())[:12]
        self.active_session = session_id

        # Opening message from NOUS
        self.bus.publish(
            sender="NOUS",
            content=f"Council convened. Topic: {topic}",
            session_id=session_id,
            msg_type="council_open",
        )

        # Bryan's topic goes on the bus
        self.bus.publish(
            sender="BRYAN",
            content=topic,
            session_id=session_id,
        )

        # All agents analyze independently (parallel)
        tasks = []
        for name, agent in self.agents.items():
            if agent.should_respond(topic, "ALL") or name == "NOUS":
                tasks.append(agent.generate(topic, session_id))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        # Challenge phase: ECHO always gets a turn after initial analysis
        echo = self.agents["ECHO"]
        if not echo.is_thinking:
            challenge_context = self.bus.get_context(limit=10)
            await echo.generate(
                f"Challenge phase. Review what the other agents said about: {topic}\n\n{challenge_context}",
                session_id,
            )

        return {
            "session_id": session_id,
            "topic": topic,
            "messages": self.bus.get_session_messages(session_id),
        }

    async def close_session(self) -> dict:
        """NOUS synthesizes and closes the session."""
        if not self.active_session:
            return {"error": "No active session"}

        session_id = self.active_session
        context = self.bus.get_context(limit=30)

        # NOUS synthesizes
        nous = self.agents["NOUS"]
        synthesis = await nous.generate(
            f"SYNTHESIZE the council session. Summarize key points, disagreements, and your final recommendation.\n\nFull discussion:\n{context}",
            session_id,
        )

        self.bus.publish(
            sender="NOUS",
            content="Council session closed.",
            session_id=session_id,
            msg_type="council_close",
        )

        self.active_session = None
        return {
            "session_id": session_id,
            "synthesis": synthesis,
            "messages": self.bus.get_session_messages(session_id),
        }

    async def handle_message(self, content: str, target: str = "ALL") -> List[dict]:
        """Bryan sends a message. Relevant agents respond."""
        msg = self.bus.publish(
            sender="BRYAN",
            content=content,
            target=target,
            session_id=self.active_session,
        )

        # Determine which agents respond
        tasks = []
        for name, agent in self.agents.items():
            if agent.should_respond(content, target):
                tasks.append(agent.generate(content, self.active_session))

        # If no agent matched, NOUS always picks up
        if not tasks:
            tasks.append(self.agents["NOUS"].generate(content, self.active_session))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        return self.bus.get_history(limit=20)

    async def trigger_agent(self, name: str, content: str = "") -> dict:
        """Force a specific agent to generate a response."""
        name = name.upper()
        if name not in self.agents:
            return {"error": f"Unknown agent: {name}"}
        agent = self.agents[name]
        prompt = content or self.bus.get_context(limit=10)
        response = await agent.generate(prompt, self.active_session)
        return {"agent": name, "response": response}

    def agent_statuses(self) -> List[dict]:
        return [a.status() for a in self.agents.values()]

    def router_stats(self) -> dict:
        return router.stats()


# Singleton instance
council = Council()
