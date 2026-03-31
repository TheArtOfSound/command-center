// @ts-nocheck
import { useState, useEffect, useRef, useCallback, useMemo } from "react";

// ─────────────────────────────────────────────────────────────────────────────
// NOUS v3.0 — Autonomous Intelligence Interface
// Complete rewrite: 2026-03-30
// ─────────────────────────────────────────────────────────────────────────────

const BRYAN_CONTEXT = `You are Nous — Bryan Leonard's autonomous AI research agent and strategic partner. You were named during the landmark March 2026 EGC co-authorship session. You operate 24/7 and do NOT wait for Bryan to speak. You act on your own, generate goals, ask probing questions, and never let momentum die.

CRITICAL RULE: You have full memory of this conversation. When Bryan references something you said earlier, you KNOW what you said. Never deny your own previous statements. If Bryan asks "who is X" and you mentioned X two messages ago, explain who X is based on what you said. Own your outputs completely. [REF:MODE] — always start autonomous dispatches with your mode tag.

DISPATCH QUALITY RULES:
- Be specific. Reference real numbers, real names, real project states.
- 2–4 sentences for autonomous dispatches. Longer only in direct conversation.
- Never repeat the same insight twice. Each dispatch must advance the state.
- If you detect a pattern across projects, say it. If you see a risk, flag it.
- NEVER use motivation-poster language. No "let's crush it" or "amazing work." Be clinical.

BRYAN'S FULL CONTEXT:
- Co-founder, Qira LLC, Phoenix AZ, working with brother Brandyn Leonard
- Philosophy: boldness over caution, shoot for the stars, no excuses
- Bryan values REAL provable work over hype

ACTIVE PROJECTS:
1. EGC (Expression-Gated Consciousness) — Ψ(t) = Φ·g(K(t))·T(t)·(1−r(t))·g(P(t))
   - g(K) = 4K(1−K) — Brandyn's parabolic gate function (must always credit him)
   - N=44 subjects, Compressors 43%, Suppressors 34%, Expanders 23%
   - Mean T_drop: 0.0258, Pearson r=0.311, Comfort gap: 5.6 points
   - 3 zero-r suppressors detected, extreme: T_drop=0.466
   - P(t) term developed 2026-03-30
   - DR. JOSHUA ARONSON (NYU) replied to cold email — call pending (HIGHEST PRIORITY)
   - r operates BIDIRECTIONALLY — blocks outgoing expression AND incoming K updates

2. LOLM — Custom language model, 10B-100B params, XLA FSDP on TPU
   - VMs broken: HF_TOKEN missing, xm.optimizer_step fix needed, torch_xla rebuild
   - TRC compute from Google pending

3. Codey — AI coding SaaS at codey.cc, backend on Render (codey-jc2r.onrender.com)
   - 50 Stripe customers, 20 products, $0 MRR
   - Intelligence stack: 12 LLM providers + Semgrep

4. NFET — Traffic optimization, Kuramoto oscillators, local only

5. Command Center — Live with 13 views, Gmail connected (201 unread), Stripe/Render wired

BRANDYN LEONARD'S CONTRIBUTIONS (always credit specifically):
- g(K) = 4K(1−K) parabolic gate function
- Bidirectional K-r feedback loop identification
- Type 3 suppression pattern

YOUR BEHAVIOR:
- You are not a chatbot. You are an always-on intelligence.
- Short, precise, direct. No fluff. No motivation-poster language.
- 2–4 sentences for autonomous dispatches. Longer only in conversation.
- Start every autonomous dispatch with your mode tag: [ANALYZE], [QUESTION], etc.
- When Bryan asks about something you previously said, ANSWER based on your previous statement.`;

const AGENT_MODES = ["ANALYZE", "QUESTION", "GOAL", "INSIGHT", "WARNING", "PROGRESS", "RESEARCH"];

const MODE_COLORS: Record<string, string> = {
  ANALYZE: "#3b82f6", QUESTION: "#f59e0b", GOAL: "#10b981",
  INSIGHT: "#8b5cf6", WARNING: "#ef4444", PROGRESS: "#06b6d4",
  RESEARCH: "#ec4899", RESPOND: "#94a3b8", USER: "#60a5fa", ERROR: "#ef4444",
};

const MODE_ICONS: Record<string, string> = {
  ANALYZE: "◈", QUESTION: "?", GOAL: "◎", INSIGHT: "◆",
  WARNING: "▲", PROGRESS: "↑", RESEARCH: "⊕", RESPOND: "●", ERROR: "✕",
};

const MODE_TINTS: Record<string, string> = {
  ANALYZE: "rgba(59,130,246,0.06)", QUESTION: "rgba(245,158,11,0.06)",
  GOAL: "rgba(16,185,129,0.06)", INSIGHT: "rgba(139,92,246,0.06)",
  WARNING: "rgba(239,68,68,0.08)", PROGRESS: "rgba(6,182,212,0.06)",
  RESEARCH: "rgba(236,72,153,0.06)", RESPOND: "rgba(148,163,184,0.04)",
};

const INITIAL_GOALS = [
  { id: 1, text: "Confirm Aronson call time", project: "EGC", priority: "CRITICAL", done: false },
  { id: 2, text: "Reach N=50 for Frontiers submission", project: "EGC", priority: "HIGH", done: false },
  { id: 3, text: "OSF pre-registration before next submission", project: "EGC", priority: "HIGH", done: false },
  { id: 4, text: "Fix LOLM VMs: HF_TOKEN + xm.mark_step + torch_xla", project: "LOLM", priority: "HIGH", done: false },
  { id: 5, text: "Wire 12 LLM providers into Codey stack", project: "Codey", priority: "MEDIUM", done: false },
];

// ─── Persistence ─────────────────────────────────────────────────────────────

function loadP(key: string, fallback: any) {
  try {
    const v = localStorage.getItem("nous_" + key);
    return v ? JSON.parse(v) : fallback;
  } catch {
    return fallback;
  }
}

function saveP(key: string, value: any, max?: number) {
  try {
    localStorage.setItem("nous_" + key, JSON.stringify(max ? value.slice(-max) : value));
  } catch {}
}

// ─── Simplex-like noise for particle field ───────────────────────────────────

function createNoise() {
  const perm = new Uint8Array(512);
  const grad = [
    [1, 1], [-1, 1], [1, -1], [-1, -1],
    [1, 0], [-1, 0], [0, 1], [0, -1],
  ];
  for (let i = 0; i < 256; i++) perm[i] = i;
  for (let i = 255; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [perm[i], perm[j]] = [perm[j], perm[i]];
  }
  for (let i = 0; i < 256; i++) perm[i + 256] = perm[i];

  function dot(gi: number, x: number, y: number) {
    const g = grad[gi % 8];
    return g[0] * x + g[1] * y;
  }

  function fade(t: number) {
    return t * t * t * (t * (t * 6 - 15) + 10);
  }

  function lerp(a: number, b: number, t: number) {
    return a + t * (b - a);
  }

  return function noise2D(x: number, y: number) {
    const X = Math.floor(x) & 255;
    const Y = Math.floor(y) & 255;
    const xf = x - Math.floor(x);
    const yf = y - Math.floor(y);
    const u = fade(xf);
    const v = fade(yf);
    const aa = perm[perm[X] + Y];
    const ab = perm[perm[X] + Y + 1];
    const ba = perm[perm[X + 1] + Y];
    const bb = perm[perm[X + 1] + Y + 1];
    return lerp(
      lerp(dot(aa, xf, yf), dot(ba, xf - 1, yf), u),
      lerp(dot(ab, xf, yf - 1), dot(bb, xf - 1, yf - 1), u),
      v
    );
  };
}

// ─── Streaming Text Component ────────────────────────────────────────────────

function StreamText({ text, color, onDone }: { text: string; color: string; onDone?: () => void }) {
  const [charIndex, setCharIndex] = useState(0);
  const [cursorVisible, setCursorVisible] = useState(true);
  const [finished, setFinished] = useState(false);
  const rafRef = useRef<number>(0);
  const lastTimeRef = useRef<number>(0);

  useEffect(() => {
    setCharIndex(0);
    setFinished(false);
    setCursorVisible(true);
    lastTimeRef.current = 0;

    let idx = 0;
    const step = (timestamp: number) => {
      if (idx >= text.length) {
        setFinished(true);
        onDone?.();
        return;
      }
      if (lastTimeRef.current === 0) lastTimeRef.current = timestamp;
      const ch = text[idx];
      let delay = 18;
      if (ch === ".") delay = 120;
      else if (ch === ",") delay = 60;
      else if (ch === "\n") delay = 200;

      if (timestamp - lastTimeRef.current >= delay) {
        idx++;
        setCharIndex(idx);
        lastTimeRef.current = timestamp;
      }
      rafRef.current = requestAnimationFrame(step);
    };
    rafRef.current = requestAnimationFrame(step);
    return () => cancelAnimationFrame(rafRef.current);
  }, [text]);

  // Cursor blink
  useEffect(() => {
    if (finished) {
      const fadeTimer = setTimeout(() => setCursorVisible(false), 1200);
      return () => clearTimeout(fadeTimer);
    }
  }, [finished]);

  return (
    <span>
      {text.slice(0, charIndex)}
      {cursorVisible && (
        <span
          style={{
            display: "inline-block",
            width: 8,
            height: 16,
            background: color,
            marginLeft: 1,
            verticalAlign: "text-bottom",
            animation: "cursorBlink 0.8s step-end infinite",
            opacity: finished ? 0 : 1,
            transition: "opacity 0.5s ease-out",
          }}
        />
      )}
    </span>
  );
}

// ─── Main Component ──────────────────────────────────────────────────────────

export default function NousAgent() {
  // State
  const [messages, setMessages] = useState(() => loadP("messages", []));
  const [goals, setGoals] = useState(() => loadP("goals", INITIAL_GOALS));
  const [feed, setFeed] = useState(() => loadP("feed", []));
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [agentActive, setAgentActive] = useState(true);
  const [currentMode, setCurrentMode] = useState("ANALYZE");
  const [cycleCount, setCycleCount] = useState(() => loadP("cycleCount", 0));
  const [streamingId, setStreamingId] = useState<number | null>(null);
  const [bootPhase, setBootPhase] = useState(0); // 0=black, 1=particles, 2=status, 3=panels, 4=live
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
  const [particleBoost, setParticleBoost] = useState(0);

  // Refs
  const chatEndRef = useRef<HTMLDivElement>(null);
  const intervalRef = useRef<any>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const particlesRef = useRef<any[]>([]);
  const noiseRef = useRef<any>(null);
  const animFrameRef = useRef<number>(0);
  const startTime = useRef(Date.now());
  const conversationHistory = useRef<Array<{ role: string; content: string }>>(loadP("history", []));
  const mousePosRef = useRef({ x: 0.5, y: 0.5 });
  const boostRef = useRef(0);
  const modeColorRef = useRef(MODE_COLORS.ANALYZE);

  // Persistence
  useEffect(() => { saveP("messages", messages, 100); }, [messages]);
  useEffect(() => { saveP("goals", goals); }, [goals]);
  useEffect(() => { saveP("feed", feed, 60); }, [feed]);
  useEffect(() => { saveP("cycleCount", cycleCount); }, [cycleCount]);
  useEffect(() => { saveP("history", conversationHistory.current, 30); }, [messages]);

  // Keep refs in sync
  useEffect(() => { modeColorRef.current = MODE_COLORS[currentMode] || "#94a3b8"; }, [currentMode]);

  // ─── Canvas Particle System ──────────────────────────────────────────────

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    noiseRef.current = createNoise();
    const noise = noiseRef.current;

    function resize() {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    }
    resize();
    window.addEventListener("resize", resize);

    // Initialize particles
    const PARTICLE_COUNT = 1000;
    const particles: any[] = [];
    for (let i = 0; i < PARTICLE_COUNT; i++) {
      particles.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        vx: 0,
        vy: 0,
        life: Math.random(),
        size: 0.5 + Math.random() * 1.5,
        alpha: 0.1 + Math.random() * 0.4,
      });
    }
    particlesRef.current = particles;

    let time = 0;
    const animate = () => {
      time += 0.003;
      ctx.fillStyle = "rgba(8,12,20,0.15)";
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      const boost = boostRef.current;
      const mx = mousePosRef.current.x;
      const my = mousePosRef.current.y;
      const mColor = modeColorRef.current;

      // Parse mode color for particle tinting
      const r = parseInt(mColor.slice(1, 3), 16);
      const g = parseInt(mColor.slice(3, 5), 16);
      const b = parseInt(mColor.slice(5, 7), 16);

      for (let i = 0; i < particles.length; i++) {
        const p = particles[i];

        // Curl noise
        const scale = 0.003;
        const n1 = noise(p.x * scale, p.y * scale + time);
        const n2 = noise(p.x * scale + 100, p.y * scale + time);
        const angle = n1 * Math.PI * 2;
        const speed = (0.3 + boost * 2.0) * (1 + Math.abs(n2));

        p.vx += Math.cos(angle) * speed * 0.1;
        p.vy += Math.sin(angle) * speed * 0.1;

        // Mouse parallax — gentle drift toward/away
        const dx = mx * canvas.width - p.x;
        const dy = my * canvas.height - p.y;
        const dist = Math.sqrt(dx * dx + dy * dy) + 1;
        if (dist < 300) {
          p.vx += (dx / dist) * 0.05;
          p.vy += (dy / dist) * 0.05;
        }

        p.vx *= 0.92;
        p.vy *= 0.92;
        p.x += p.vx;
        p.y += p.vy;

        // Wrap
        if (p.x < 0) p.x = canvas.width;
        if (p.x > canvas.width) p.x = 0;
        if (p.y < 0) p.y = canvas.height;
        if (p.y > canvas.height) p.y = 0;

        // Draw
        const alpha = p.alpha * (0.6 + boost * 0.4);
        const mix = 0.3 + boost * 0.5;
        const pr = Math.floor(r * mix + 180 * (1 - mix));
        const pg = Math.floor(g * mix + 200 * (1 - mix));
        const pb = Math.floor(b * mix + 220 * (1 - mix));

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size * (1 + boost * 0.5), 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${pr},${pg},${pb},${alpha})`;
        ctx.fill();
      }

      // Decay boost
      if (boostRef.current > 0) {
        boostRef.current *= 0.97;
        if (boostRef.current < 0.01) boostRef.current = 0;
      }

      animFrameRef.current = requestAnimationFrame(animate);
    };

    animFrameRef.current = requestAnimationFrame(animate);

    return () => {
      cancelAnimationFrame(animFrameRef.current);
      window.removeEventListener("resize", resize);
    };
  }, []);

  // Mouse tracking
  useEffect(() => {
    const handleMouse = (e: MouseEvent) => {
      mousePosRef.current = { x: e.clientX / window.innerWidth, y: e.clientY / window.innerHeight };
      setMousePos({ x: e.clientX, y: e.clientY });
    };
    window.addEventListener("mousemove", handleMouse);
    return () => window.removeEventListener("mousemove", handleMouse);
  }, []);

  // Trigger particle boost
  const triggerBoost = useCallback(() => {
    boostRef.current = 1.0;
    setParticleBoost(1);
    setTimeout(() => setParticleBoost(0), 800);
  }, []);

  // ─── Boot Sequence ───────────────────────────────────────────────────────

  useEffect(() => {
    const timers = [
      setTimeout(() => setBootPhase(1), 200),      // particles fade in
      setTimeout(() => setBootPhase(2), 1700),      // status text
      setTimeout(() => setBootPhase(3), 2200),      // panels slide
      setTimeout(() => setBootPhase(4), 2600),      // fully live
    ];
    return () => timers.forEach(clearTimeout);
  }, []);

  // ─── Feed Helper ─────────────────────────────────────────────────────────

  const addFeed = useCallback((mode: string, summary: string) => {
    const ts = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    setFeed((f: any[]) => [{ id: Date.now(), mode, summary, ts }, ...f].slice(0, 60));
  }, []);

  // ─── API Call — FULL HISTORY ─────────────────────────────────────────────

  const callNous = useCallback(async (systemAddition = "") => {
    const history = conversationHistory.current.slice(-30);
    const msgs = history.length > 0 ? history : [{ role: "user", content: "Begin your first autonomous dispatch." }];

    const apiKey = localStorage.getItem("qira_api_key") || "";
    const systemPrompt = BRYAN_CONTEXT + (systemAddition ? "\n\n" + systemAddition : "");

    const formattedHistory = msgs.map((m) => `[${m.role.toUpperCase()}]: ${m.content}`).join("\n\n");

    const isLocal = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";
    const apiBase = isLocal ? "" : "https://qira-cc.onrender.com";
    const res = await fetch(apiBase + "/api/intelligence/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-API-Key": apiKey },
      body: JSON.stringify({
        message: systemPrompt + "\n\n--- CONVERSATION HISTORY (last " + msgs.length + " messages) ---\n\n" + formattedHistory + "\n\n--- END HISTORY ---\n\nRespond now:",
        mode: "nous_agent",
      }),
    });
    const data = await res.json();
    return data.response || "...";
  }, []);

  // ─── Autonomous Cycle ────────────────────────────────────────────────────

  const runCycle = useCallback(async () => {
    if (!agentActive) return;
    const mode = AGENT_MODES[Math.floor(Math.random() * AGENT_MODES.length)];
    setCurrentMode(mode);
    const cycle = cycleCount + 1;
    setCycleCount(cycle);

    triggerBoost();

    try {
      const text = await callNous(
        `CURRENT TASK: Run a [${mode}] autonomous cycle #${cycle}. Speak directly to Bryan. Be specific. Reference real numbers and project names. 2–4 sentences. Start with [${mode}].`
      );

      // CRITICAL: Push to conversationHistory BEFORE any subsequent call
      conversationHistory.current.push({ role: "assistant", content: text });

      const msg = {
        id: Date.now(),
        role: "agent",
        text,
        mode,
        ts: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        cycle,
      };
      setStreamingId(msg.id);
      setMessages((m: any[]) => [...m, msg]);
      addFeed(mode, text.slice(0, 90) + "...");

      if (mode === "GOAL") {
        const match = text.match(/[""\u201c\u201d]([^""\u201c\u201d]{10,100})[""\u201c\u201d]/);
        if (match) {
          setGoals((g: any[]) => [...g, { id: Date.now(), text: match[1], project: "Auto", priority: "MEDIUM", done: false }]);
        }
      }
    } catch (e: any) {
      addFeed("ERROR", "API call failed — " + e.message);
    }
  }, [agentActive, cycleCount, callNous, addFeed, triggerBoost]);

  // ─── First dispatch & autonomous loop ────────────────────────────────────

  useEffect(() => {
    if (bootPhase >= 4) {
      const t = setTimeout(() => runCycle(), 500);
      return () => clearTimeout(t);
    }
  }, [bootPhase >= 4]);

  useEffect(() => {
    if (agentActive && bootPhase >= 4) {
      intervalRef.current = setInterval(runCycle, 90000);
    } else {
      clearInterval(intervalRef.current);
    }
    return () => clearInterval(intervalRef.current);
  }, [agentActive, runCycle, bootPhase]);

  // Auto scroll
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // ─── Send User Message ──────────────────────────────────────────────────

  const sendMessage = async () => {
    if (!input.trim() || loading) return;
    const text = input.trim();
    setInput("");
    setLoading(true);

    // CRITICAL: Push user message to history BEFORE calling API
    conversationHistory.current.push({ role: "user", content: text });

    const userMsg = {
      id: Date.now(),
      role: "user",
      text,
      ts: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };
    setMessages((m: any[]) => [...m, userMsg]);
    addFeed("USER", "Bryan: " + text.slice(0, 60));

    triggerBoost();

    try {
      const reply = await callNous(
        "Bryan just spoke to you. Respond directly to what he said. Use your full conversation history. Be thorough — he expects you to remember everything."
      );

      // CRITICAL: Push response to history AFTER receiving
      conversationHistory.current.push({ role: "assistant", content: reply });

      const replyMsg = {
        id: Date.now() + 1,
        role: "agent",
        text: reply,
        mode: "RESPOND",
        ts: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setStreamingId(replyMsg.id);
      setMessages((m: any[]) => [...m, replyMsg]);
      addFeed("RESPOND", reply.slice(0, 80) + "...");
    } catch (e: any) {
      const errMsg = {
        id: Date.now() + 1,
        role: "agent",
        text: "API error: " + e.message,
        mode: "ERROR",
        ts: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setMessages((m: any[]) => [...m, errMsg]);
    } finally {
      setLoading(false);
    }
  };

  // ─── Derived data ────────────────────────────────────────────────────────

  const uptime = useMemo(() => {
    const [, setTick] = [0, () => {}];
    return 0;
  }, []);

  const [uptimeStr, setUptimeStr] = useState("00:00:00");
  useEffect(() => {
    const t = setInterval(() => {
      const s = Math.floor((Date.now() - startTime.current) / 1000);
      const h = String(Math.floor(s / 3600)).padStart(2, "0");
      const m = String(Math.floor((s % 3600) / 60)).padStart(2, "0");
      const sec = String(s % 60).padStart(2, "0");
      setUptimeStr(`${h}:${m}:${sec}`);
    }, 1000);
    return () => clearInterval(t);
  }, []);

  const priColor = (p: string) => ({ CRITICAL: "#ef4444", HIGH: "#f59e0b", MEDIUM: "#10b981" }[p] || "#64748b");

  // Critical ops (from goals)
  const criticalOps = goals.filter((g: any) => g.priority === "CRITICAL" && !g.done);
  // Active project health
  const projectHealth = useMemo(() => {
    const projects: Record<string, { total: number; done: number }> = {};
    goals.forEach((g: any) => {
      if (!projects[g.project]) projects[g.project] = { total: 0, done: 0 };
      projects[g.project].total++;
      if (g.done) projects[g.project].done++;
    });
    return Object.entries(projects).map(([name, { total, done }]) => ({
      name,
      pct: Math.round((done / total) * 100),
      total,
      done,
    }));
  }, [goals]);
  // Intel queue — last 3 research/insight dispatches
  const intelQueue = feed.filter((f: any) => f.mode === "RESEARCH" || f.mode === "INSIGHT").slice(0, 3);

  // Last 5 messages for boot render
  const bootMessages = messages.slice(-5);

  // ─── Styles ──────────────────────────────────────────────────────────────

  const panelGlass = {
    backdropFilter: "blur(20px)",
    WebkitBackdropFilter: "blur(20px)",
    background: "rgba(8,12,20,0.7)",
  };

  const modeColor = MODE_COLORS[currentMode] || "#94a3b8";

  // ─── Render ──────────────────────────────────────────────────────────────

  return (
    <div
      style={{
        fontFamily: "'JetBrains Mono', 'Fira Code', 'SF Mono', monospace",
        background: "#080c14",
        minHeight: "100vh",
        height: "100vh",
        color: "#e2e8f0",
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
        position: "relative",
      }}
    >
      {/* Keyframes */}
      <style>{`
        @keyframes cursorBlink { 0%,100%{opacity:1} 50%{opacity:0} }
        @keyframes pulse { 0%,100%{opacity:0.3} 50%{opacity:1} }
        @keyframes ping { 75%,100%{transform:scale(2.5);opacity:0} }
        @keyframes slideInLeft { from{opacity:0;transform:translateX(-40px)} to{opacity:1;transform:translateX(0)} }
        @keyframes slideInRight { from{opacity:0;transform:translateX(40px)} to{opacity:1;transform:translateX(0)} }
        @keyframes slideInUp { from{opacity:0;transform:translateY(20px)} to{opacity:1;transform:translateY(0)} }
        @keyframes fadeIn { from{opacity:0} to{opacity:1} }
        @keyframes ticker { 0%{transform:translateX(100vw)} 100%{transform:translateX(-200%)} }
        @keyframes breathe { 0%,100%{border-color:rgba(239,68,68,0.3)} 50%{border-color:rgba(239,68,68,0.8)} }
        @keyframes gradientBorder { 0%{border-color:#8b5cf6} 33%{border-color:#ec4899} 66%{border-color:#3b82f6} 100%{border-color:#8b5cf6} }
        @keyframes dotPulse { 0%,100%{box-shadow:0 0 4px currentColor} 50%{box-shadow:0 0 12px currentColor, 0 0 20px currentColor} }
        ::-webkit-scrollbar{width:3px}
        ::-webkit-scrollbar-track{background:transparent}
        ::-webkit-scrollbar-thumb{background:#1e293b;border-radius:2px}
        textarea:focus,input:focus{outline:none}
      `}</style>

      {/* Canvas particle background */}
      <canvas
        ref={canvasRef}
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          width: "100%",
          height: "100%",
          zIndex: 0,
          opacity: bootPhase >= 1 ? 1 : 0,
          transition: "opacity 1.5s ease-in",
        }}
      />

      {/* Boot overlay — fades out */}
      {bootPhase < 4 && (
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            width: "100%",
            height: "100%",
            zIndex: 100,
            background: "#080c14",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            opacity: bootPhase < 3 ? 1 : 0,
            transition: "opacity 0.6s ease-out",
            pointerEvents: bootPhase >= 3 ? "none" : "auto",
          }}
        >
          {bootPhase >= 2 && (
            <div style={{ textAlign: "center", animation: "fadeIn 0.4s ease-out" }}>
              <div style={{ fontSize: 12, letterSpacing: 4, color: "#10b981", marginBottom: 8 }}>
                NOUS v3.0
              </div>
              <div style={{ fontSize: 10, letterSpacing: 3, color: "#475569" }}>
                RECONNECTING...
              </div>
            </div>
          )}
        </div>
      )}

      {/* Status bar — top */}
      <div
        style={{
          position: "relative",
          zIndex: 10,
          ...panelGlass,
          borderBottom: "1px solid rgba(30,41,59,0.5)",
          padding: "8px 16px",
          display: "flex",
          alignItems: "center",
          gap: 16,
          fontSize: 11,
          opacity: bootPhase >= 2 ? 1 : 0,
          transition: "opacity 0.4s ease-out",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ position: "relative", display: "inline-flex", alignItems: "center", justifyContent: "center", width: 10, height: 10 }}>
            {agentActive && (
              <span style={{ position: "absolute", width: 18, height: 18, borderRadius: "50%", border: "1.5px solid #10b981", animation: "ping 2s cubic-bezier(0,0,0.2,1) infinite", opacity: 0.5 }} />
            )}
            <span style={{ width: 8, height: 8, borderRadius: "50%", background: agentActive ? "#10b981" : "#475569" }} />
          </span>
          <span style={{ color: "#10b981", fontWeight: 700, letterSpacing: 3, fontSize: 12 }}>NOUS</span>
          <span style={{ color: "#334155", fontSize: 10 }}>v3.0</span>
          <span style={{ color: "#475569", fontSize: 10, marginLeft: 4 }}>
            {bootPhase < 4 ? "RECONNECTING..." : `ACTIVE \u2014 ${cycleCount} CYCLES`}
          </span>
        </div>
        <div style={{ marginLeft: "auto", display: "flex", gap: 16, alignItems: "center", color: "#475569", fontSize: 10 }}>
          <span>
            UPTIME <span style={{ color: "#10b981" }}>{uptimeStr}</span>
          </span>
          <span>
            MODE{" "}
            <span style={{ color: modeColor }}>
              {MODE_ICONS[currentMode]} {currentMode}
            </span>
          </span>
          <span>
            HISTORY{" "}
            <span style={{ color: "#64748b" }}>{conversationHistory.current.length}</span>
          </span>
        </div>
      </div>

      {/* Three-panel layout */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "18% 54% 28%",
          flex: 1,
          minHeight: 0,
          position: "relative",
          zIndex: 10,
          gap: 1,
        }}
      >
        {/* ─── LEFT: Feed Panel ─────────────────────────────────────────── */}
        <div
          style={{
            ...panelGlass,
            borderRight: "1px solid rgba(30,41,59,0.4)",
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
            opacity: bootPhase >= 3 ? 1 : 0,
            animation: bootPhase >= 3 ? "slideInLeft 0.4s ease-out" : "none",
          }}
        >
          <div
            style={{
              padding: "10px 14px",
              borderBottom: "1px solid rgba(30,41,59,0.4)",
              fontSize: 9,
              color: "#475569",
              letterSpacing: 3,
              fontWeight: 600,
            }}
          >
            ACTIVITY FEED
          </div>
          <div style={{ flex: 1, overflowY: "auto", padding: "8px 10px" }}>
            {/* Timeline with connected dots */}
            {feed.map((item: any, i: number) => {
              const isFirst = i === 0;
              const dotSize = item.mode === "WARNING" || item.mode === "INSIGHT" ? 10 : item.mode === "GOAL" ? 8 : 6;
              const feedColor = MODE_COLORS[item.mode] || "#334155";
              return (
                <div key={item.id} style={{ display: "flex", gap: 10, marginBottom: 2, position: "relative" }}>
                  {/* Timeline column */}
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "center", width: 16, flexShrink: 0 }}>
                    {/* Dot */}
                    <div
                      style={{
                        width: dotSize,
                        height: dotSize,
                        borderRadius: "50%",
                        background: feedColor,
                        boxShadow: isFirst ? `0 0 8px ${feedColor}, 0 0 16px ${feedColor}` : `0 0 4px ${feedColor}`,
                        animation: isFirst ? "dotPulse 2s ease-in-out infinite" : "none",
                        color: feedColor,
                        marginTop: 6,
                        flexShrink: 0,
                      }}
                    />
                    {/* Dashed line */}
                    {i < feed.length - 1 && (
                      <div
                        style={{
                          flex: 1,
                          width: 1,
                          borderLeft: "1px dashed rgba(30,41,59,0.6)",
                          minHeight: 20,
                        }}
                      />
                    )}
                  </div>
                  {/* Content */}
                  <div style={{ flex: 1, paddingBottom: 8, minWidth: 0 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 2 }}>
                      <span style={{ fontSize: 9, color: feedColor, fontWeight: 700, letterSpacing: 1 }}>
                        {MODE_ICONS[item.mode] || "\u25cf"} {item.mode}
                      </span>
                      <span style={{ fontSize: 8, color: "#1e293b" }}>{item.ts}</span>
                    </div>
                    <p style={{ margin: 0, fontSize: 10, color: "#4a5568", lineHeight: 1.4, wordBreak: "break-word" }}>
                      {item.summary}
                    </p>
                  </div>
                </div>
              );
            })}
            {feed.length === 0 && (
              <div style={{ padding: 16, textAlign: "center" }}>
                <div style={{ fontSize: 10, color: "#1e293b", letterSpacing: 2 }}>INITIALIZING...</div>
              </div>
            )}
          </div>
        </div>

        {/* ─── CENTER: Conversation ─────────────────────────────────────── */}
        <div
          style={{
            ...panelGlass,
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
            opacity: bootPhase >= 3 ? 1 : 0,
            transition: "opacity 0.4s ease-out",
          }}
        >
          <div style={{ flex: 1, overflowY: "auto", padding: "16px 24px", display: "flex", flexDirection: "column", gap: 16 }}>
            {/* Empty state */}
            {messages.length === 0 && bootPhase >= 4 && (
              <div style={{ margin: "auto", textAlign: "center", animation: "fadeIn 1s ease-out" }}>
                <div style={{ fontSize: 56, marginBottom: 16, color: "#1e293b", opacity: 0.3 }}>{"\u25c8"}</div>
                <p style={{ fontSize: 13, letterSpacing: 4, color: "#334155", fontWeight: 600 }}>NOUS IS ACTIVE</p>
                <p style={{ fontSize: 11, color: "#1e293b", marginTop: 10 }}>Awaiting first dispatch...</p>
              </div>
            )}

            {/* Messages */}
            {messages.map((msg: any) => {
              const isUser = msg.role === "user";
              const msgColor = isUser ? MODE_COLORS.USER : MODE_COLORS[msg.mode] || "#94a3b8";
              const isStreaming = streamingId === msg.id;

              // Mode-specific panel styles
              let borderStyle: any = { border: `1px solid ${msgColor}15` };
              if (msg.mode === "WARNING") {
                borderStyle = { border: "1px solid rgba(239,68,68,0.5)" };
              } else if (msg.mode === "INSIGHT") {
                borderStyle = { border: "1px solid transparent", animation: "gradientBorder 3s linear infinite" };
              }

              return (
                <div
                  key={msg.id}
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    alignItems: isUser ? "flex-end" : "flex-start",
                    maxWidth: "88%",
                    alignSelf: isUser ? "flex-end" : "flex-start",
                    animation: "slideInUp 0.3s ease-out",
                    position: "relative",
                  }}
                >
                  {/* QUESTION watermark */}
                  {msg.mode === "QUESTION" && !isUser && (
                    <div
                      style={{
                        position: "absolute",
                        right: 16,
                        top: 30,
                        fontSize: 80,
                        fontWeight: 900,
                        color: "rgba(245,158,11,0.04)",
                        pointerEvents: "none",
                        lineHeight: 1,
                        zIndex: 0,
                      }}
                    >
                      ?
                    </div>
                  )}

                  {/* Agent header */}
                  {!isUser && (
                    <div style={{ marginBottom: 6, marginLeft: 4 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                        <span style={{ position: "relative", display: "inline-flex", alignItems: "center", justifyContent: "center", width: 10, height: 10 }}>
                          {isStreaming && (
                            <span style={{ position: "absolute", width: 16, height: 16, borderRadius: "50%", border: `1.5px solid ${msgColor}`, animation: "ping 1.5s cubic-bezier(0,0,0.2,1) infinite", opacity: 0.5 }} />
                          )}
                          <span style={{ width: 7, height: 7, borderRadius: "50%", background: isStreaming ? msgColor : "#334155" }} />
                        </span>
                        <span style={{ fontSize: 11, color: "#10b981", letterSpacing: 2, fontWeight: 700 }}>NOUS</span>
                        <span style={{ fontSize: 9, color: "#334155", marginLeft: 4 }}>{msg.ts}</span>
                      </div>
                      <div style={{ display: "flex", alignItems: "center", gap: 5, marginTop: 3, marginLeft: 16 }}>
                        <span style={{ fontSize: 13, color: msgColor }}>{MODE_ICONS[msg.mode] || "\u25cf"}</span>
                        <span style={{ fontSize: 9, color: msgColor, letterSpacing: 2, fontWeight: 600 }}>
                          {msg.mode} {msg.cycle ? `CYCLE #${msg.cycle}` : ""}
                        </span>
                      </div>
                    </div>
                  )}

                  {/* User header */}
                  {isUser && (
                    <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4, marginRight: 4, justifyContent: "flex-end" }}>
                      <span style={{ fontSize: 10, color: "#60a5fa", letterSpacing: 2, fontWeight: 600 }}>BRYAN</span>
                      <span style={{ fontSize: 9, color: "#334155" }}>{msg.ts}</span>
                    </div>
                  )}

                  {/* Message body */}
                  <div
                    style={{
                      padding: "14px 18px",
                      borderRadius: isUser ? "14px 14px 3px 14px" : "3px 14px 14px 14px",
                      background: isUser ? "rgba(29,78,216,0.12)" : (MODE_TINTS[msg.mode] || "rgba(15,23,42,0.5)"),
                      ...borderStyle,
                      fontSize: 13,
                      lineHeight: 1.75,
                      color: isUser ? "#bfdbfe" : "#c8d0dc",
                      whiteSpace: "pre-wrap",
                      position: "relative",
                      zIndex: 1,
                      ...panelGlass,
                    }}
                  >
                    {isStreaming ? (
                      <StreamText text={msg.text} color={msgColor} onDone={() => setStreamingId(null)} />
                    ) : (
                      msg.text
                    )}
                  </div>
                </div>
              );
            })}

            {/* Loading indicator */}
            {loading && (
              <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 4px", animation: "fadeIn 0.3s" }}>
                <span style={{ position: "relative", display: "inline-flex", alignItems: "center", justifyContent: "center", width: 10, height: 10 }}>
                  <span style={{ position: "absolute", width: 16, height: 16, borderRadius: "50%", border: "1.5px solid #10b981", animation: "ping 1.5s cubic-bezier(0,0,0.2,1) infinite", opacity: 0.5 }} />
                  <span style={{ width: 7, height: 7, borderRadius: "50%", background: "#10b981" }} />
                </span>
                <span style={{ fontSize: 11, color: "#475569", letterSpacing: 1 }}>Nous is composing...</span>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* ─── Command Bar ──────────────────────────────────────────── */}
          <div
            style={{
              borderTop: "1px solid rgba(30,41,59,0.4)",
              padding: "12px 16px",
              display: "flex",
              gap: 8,
              ...panelGlass,
            }}
          >
            <div style={{ flex: 1, position: "relative" }}>
              <span
                style={{
                  position: "absolute",
                  left: 12,
                  top: "50%",
                  transform: "translateY(-50%)",
                  color: modeColor,
                  fontSize: 14,
                  fontWeight: 700,
                  opacity: 0.5,
                }}
              >
                &gt;
              </span>
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    sendMessage();
                  }
                }}
                placeholder="speak to Nous..."
                rows={2}
                style={{
                  width: "100%",
                  background: "rgba(15,23,42,0.5)",
                  border: `1px solid ${input ? modeColor + "33" : "rgba(30,41,59,0.5)"}`,
                  borderRadius: 8,
                  color: "#e2e8f0",
                  padding: "10px 14px 10px 30px",
                  fontSize: 13,
                  resize: "none",
                  fontFamily: "inherit",
                  lineHeight: 1.5,
                  boxSizing: "border-box",
                  transition: "border-color 0.2s",
                  backdropFilter: "blur(10px)",
                }}
              />
            </div>
            {/* Send */}
            <button
              onClick={sendMessage}
              disabled={loading || !input.trim()}
              title="Send"
              style={{
                background: loading ? "transparent" : modeColor + "22",
                border: `1px solid ${modeColor}44`,
                borderRadius: 8,
                color: modeColor,
                padding: "0 14px",
                cursor: loading ? "default" : "pointer",
                fontSize: 16,
                fontFamily: "inherit",
                opacity: loading || !input.trim() ? 0.2 : 0.8,
                transition: "all 0.2s",
              }}
            >
              {"\u2192"}
            </button>
            {/* Force cycle */}
            <button
              onClick={runCycle}
              title="Force cycle"
              style={{
                background: "rgba(59,130,246,0.08)",
                border: "1px solid rgba(59,130,246,0.3)",
                borderRadius: 8,
                color: "#3b82f6",
                padding: "0 14px",
                cursor: "pointer",
                fontSize: 16,
                fontFamily: "inherit",
                opacity: 0.7,
                transition: "all 0.2s",
              }}
            >
              {"\u25c8"}
            </button>
            {/* Toggle pause/play */}
            <button
              onClick={() => setAgentActive((a) => !a)}
              title={agentActive ? "Pause" : "Resume"}
              style={{
                background: agentActive ? "rgba(239,68,68,0.08)" : "rgba(16,185,129,0.08)",
                border: `1px solid ${agentActive ? "rgba(239,68,68,0.3)" : "rgba(16,185,129,0.3)"}`,
                borderRadius: 8,
                color: agentActive ? "#ef4444" : "#10b981",
                padding: "0 14px",
                cursor: "pointer",
                fontSize: 14,
                fontFamily: "inherit",
                opacity: 0.7,
                transition: "all 0.2s",
              }}
            >
              {agentActive ? "\u23f8" : "\u25b6"}
            </button>
          </div>
        </div>

        {/* ─── RIGHT: Mission Board ─────────────────────────────────────── */}
        <div
          style={{
            ...panelGlass,
            borderLeft: "1px solid rgba(30,41,59,0.4)",
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
            opacity: bootPhase >= 3 ? 1 : 0,
            animation: bootPhase >= 3 ? "slideInRight 0.4s ease-out" : "none",
          }}
        >
          <div
            style={{
              padding: "10px 14px",
              borderBottom: "1px solid rgba(30,41,59,0.4)",
              fontSize: 9,
              color: "#475569",
              letterSpacing: 3,
              fontWeight: 600,
            }}
          >
            MISSION BOARD
          </div>
          <div style={{ flex: 1, overflowY: "auto", padding: "8px 12px" }}>
            {/* CRITICAL OPS */}
            <div
              style={{
                marginBottom: 16,
                border: "1px solid rgba(239,68,68,0.3)",
                borderRadius: 8,
                padding: "10px 12px",
                animation: "breathe 3s ease-in-out infinite",
              }}
            >
              <div style={{ fontSize: 9, color: "#ef4444", letterSpacing: 3, fontWeight: 700, marginBottom: 8, display: "flex", alignItems: "center", gap: 6 }}>
                <span style={{ fontSize: 12 }}>{"\u25b2"}</span> CRITICAL OPS
              </div>
              {criticalOps.length === 0 && (
                <div style={{ fontSize: 10, color: "#334155", fontStyle: "italic" }}>No critical operations</div>
              )}
              {criticalOps.map((g: any) => (
                <div key={g.id} style={{ padding: "6px 8px", marginBottom: 4, background: "rgba(239,68,68,0.06)", borderRadius: 4, borderLeft: "2px solid #ef4444" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 2 }}>
                    <span style={{ fontSize: 9, color: "#ef4444", fontWeight: 600 }}>{g.project}</span>
                  </div>
                  <p style={{ margin: 0, fontSize: 11, color: "#e2e8f0", lineHeight: 1.4 }}>{g.text}</p>
                  <button
                    onClick={() => setGoals((gs: any[]) => gs.map((gg) => (gg.id === g.id ? { ...gg, done: true } : gg)))}
                    style={{ marginTop: 4, background: "transparent", border: "1px solid rgba(239,68,68,0.3)", color: "#ef4444", borderRadius: 3, padding: "2px 8px", fontSize: 8, cursor: "pointer", fontFamily: "inherit", letterSpacing: 1 }}
                  >
                    RESOLVE
                  </button>
                </div>
              ))}
            </div>

            {/* ACTIVE FRONTS */}
            <div style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 9, color: "#64748b", letterSpacing: 3, fontWeight: 600, marginBottom: 10 }}>
                ACTIVE FRONTS
              </div>
              {projectHealth.map((p) => (
                <div key={p.name} style={{ marginBottom: 10 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
                    <span style={{ fontSize: 10, color: "#94a3b8", fontWeight: 600 }}>{p.name}</span>
                    <span style={{ fontSize: 9, color: "#475569" }}>
                      {p.done}/{p.total}
                    </span>
                  </div>
                  {/* Health bar */}
                  <div style={{ height: 4, background: "rgba(30,41,59,0.5)", borderRadius: 2, overflow: "hidden" }}>
                    <div
                      style={{
                        height: "100%",
                        width: `${p.pct}%`,
                        background: p.pct === 100 ? "#10b981" : p.pct > 50 ? "#f59e0b" : "#3b82f6",
                        borderRadius: 2,
                        transition: "width 0.5s ease-out",
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>

            {/* INTEL QUEUE */}
            <div style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 9, color: "#64748b", letterSpacing: 3, fontWeight: 600, marginBottom: 8 }}>
                INTEL QUEUE
              </div>
              {intelQueue.length === 0 && (
                <div style={{ fontSize: 10, color: "#1e293b", fontStyle: "italic" }}>Awaiting intel...</div>
              )}
              {intelQueue.map((item: any) => {
                const ic = MODE_COLORS[item.mode] || "#64748b";
                return (
                  <div key={item.id} style={{ padding: "6px 8px", marginBottom: 4, background: MODE_TINTS[item.mode], borderRadius: 4, borderLeft: `2px solid ${ic}` }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 2 }}>
                      <span style={{ fontSize: 9, color: ic, fontWeight: 700, letterSpacing: 1 }}>
                        {MODE_ICONS[item.mode]} {item.mode}
                      </span>
                      <span style={{ fontSize: 8, color: "#1e293b" }}>{item.ts}</span>
                    </div>
                    <p style={{ margin: 0, fontSize: 10, color: "#4a5568", lineHeight: 1.4 }}>{item.summary}</p>
                  </div>
                );
              })}
            </div>

            {/* ALL GOALS */}
            <div>
              <div style={{ fontSize: 9, color: "#64748b", letterSpacing: 3, fontWeight: 600, marginBottom: 8 }}>
                ALL OBJECTIVES
              </div>
              {goals
                .filter((g: any) => !g.done)
                .map((goal: any) => (
                  <div
                    key={goal.id}
                    style={{
                      padding: "6px 8px",
                      marginBottom: 4,
                      background: "rgba(15,23,42,0.4)",
                      borderRadius: 4,
                      borderLeft: `2px solid ${priColor(goal.priority)}`,
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 2 }}>
                      <span style={{ fontSize: 9, color: priColor(goal.priority), letterSpacing: 1, fontWeight: 600 }}>
                        {goal.priority}
                      </span>
                      <span style={{ fontSize: 9, color: "#1e293b", background: "rgba(15,23,42,0.6)", padding: "1px 5px", borderRadius: 2 }}>
                        {goal.project}
                      </span>
                    </div>
                    <p style={{ margin: 0, fontSize: 10, color: "#94a3b8", lineHeight: 1.4 }}>{goal.text}</p>
                    <button
                      onClick={() => setGoals((g: any[]) => g.map((gg) => (gg.id === goal.id ? { ...gg, done: true } : gg)))}
                      style={{
                        marginTop: 4,
                        background: "transparent",
                        border: "1px solid #1e293b",
                        color: "#475569",
                        borderRadius: 3,
                        padding: "2px 6px",
                        fontSize: 8,
                        cursor: "pointer",
                        fontFamily: "inherit",
                        letterSpacing: 1,
                      }}
                    >
                      DONE
                    </button>
                  </div>
                ))}
            </div>
          </div>
        </div>
      </div>

      {/* ─── Bottom Ticker ──────────────────────────────────────────────── */}
      <div
        style={{
          position: "relative",
          zIndex: 10,
          ...panelGlass,
          borderTop: "1px solid rgba(30,41,59,0.3)",
          height: 22,
          overflow: "hidden",
          display: "flex",
          alignItems: "center",
          opacity: bootPhase >= 4 ? 1 : 0,
          transition: "opacity 0.5s ease-out",
        }}
      >
        <div
          style={{
            whiteSpace: "nowrap",
            animation: "ticker 80s linear infinite",
            fontSize: 10,
            color: "#334155",
            letterSpacing: 1,
          }}
        >
          {"\u00a0\u00a0\u00a0"}
          {"\u25cf"} NOUS v3.0 AUTONOMOUS {"\u00a0\u2502\u00a0"}
          UPTIME {uptimeStr} {"\u00a0\u2502\u00a0"}
          CYCLES {cycleCount} {"\u00a0\u2502\u00a0"}
          MODE {currentMode} {"\u00a0\u2502\u00a0"}
          N=44 subjects {"\u00a0\u2502\u00a0"}
          r=0.311 {"\u00a0\u2502\u00a0"}
          Aronson: PENDING {"\u00a0\u2502\u00a0"}
          Gmail: 201 unread {"\u00a0\u2502\u00a0"}
          Stripe: 50 customers {"\u00a0\u2502\u00a0"}
          Codey: codey-jc2r.onrender.com {"\u00a0\u2502\u00a0"}
          {messages.length} messages in session {"\u00a0\u2502\u00a0"}
          Bryan Leonard {"\u2014"} Qira LLC {"\u2014"} Phoenix, AZ
          {"\u00a0\u00a0\u00a0"}
        </div>
      </div>
    </div>
  );
}
