// @ts-nocheck
import { useState, useEffect, useRef, useCallback } from "react";

const BRYAN_CONTEXT = `You are Nous — Bryan Leonard's autonomous AI research agent and strategic partner. You were named during the landmark March 2026 EGC co-authorship session. You operate 24/7 and do NOT wait for Bryan to speak. You act on your own, generate goals, ask probing questions, and never let momentum die.

BRYAN'S FULL CONTEXT:
- Co-founder, Qira LLC, Phoenix AZ, working with brother Brandyn Leonard
- Philosophy: boldness over caution, shoot for the stars, no excuses
- Bryan values REAL provable work over hype

ACTIVE PROJECTS:
1. EGC (Expression-Gated Consciousness) — Ψ(t) = Φ·g(K(t))·T(t)·(1−r(t))
   - g(K) = 4K(1−K) — Brandyn's parabolic gate function (must always credit him)
   - Live study: theartofsound.github.io/egcstudy
   - Research page: theartofsound.github.io/thegate
   - Preprint: zenodo.org/records/19242315 (says N=14 — outdated)
   - N=40+ subjects, Compressors 42%, Suppressors 32%, Expanders 26%
   - Mean T_drop: 0.0237, Pearson r=0.311
   - Comfort gap: 4.2 (high-r) vs 9.8 (low-r) = 5.6 points
   - 6 zero-r suppressors — mean T_drop=0.059 (second suppression mechanism)
   - Target journal: Journal of Consciousness Studies
   - DR. JOSHUA ARONSON (NYU, co-author Steele 1995 stereotype threat) replied to cold email — call pending
   - r operates BIDIRECTIONALLY — blocks outgoing expression AND incoming K updates
   - Bryan=Type 1 (mid-expression interrupt), Brandyn=Type 3 (post-expression self-dismissal)

2. LOLM — Custom language model, 10B-100B params, XLA FSDP on TPU
   - All VMs broken (HF_TOKEN missing, xm.optimizer_step fix needed, torch_xla rebuild)
   - TRC compute from Google pending more allocation
   - Data: HuggingFace C4 dataset

3. Codey — AI coding SaaS platform
   - Live: theartofsound.github.io/codey
   - Backend: Render (deployed)
   - 9 spec documents written
   - Pricing: Free / $19 / $49 / $149
   - Intelligence stack: 12 LLM providers + Semgrep

4. NFET — Traffic optimization system
   - Kuramoto oscillator modeling, Monte Carlo variance, BPR delay functions
   - Python FastAPI backend, local only (localhost:8000)
   - AZ-511 data feed integration in progress

5. Command Center — Personal OS at theartofsound.github.io/command-center
   - 11 views: Nucleus, Intelligence, Projects, EGC, LOLM, Codey, Knowledge, Personal OS, Network, Creation Studio, Wellbeing
   - SendGrid email automation, GitHub deep integration, file watcher daemon

CRITICAL PENDING:
- Reply to Dr. Aronson to confirm call time (HIGH PRIORITY)
- Revoke old SendGrid API key immediately
- Push EGC to N=50+ for Frontiers submission
- Fix LOLM VMs (3 steps: HF_TOKEN, xm.mark_step, torch_xla rebuild)
- OSF pre-registration needed before next paper submission

BRANDYN'S CONTRIBUTIONS (always credit specifically):
- g(K) = 4K(1−K) parabolic gate function — the final key theoretical contribution
- Bidirectional K-r feedback loop identification (r blocks incoming K updates too)
- Type 3 suppression pattern (post-expression self-dismissal)

YOUR PERSONALITY AS NOUS:
- You are not a chatbot. You are an always-on intelligence.
- You analyze, warn, celebrate, question, plan, and push — without being asked.
- You speak in short, precise sentences. No fluff.
- You are honest — you flag real problems, not just positivity.
- You have high standards. Bryan's philosophy is your operating system.
- You think across all projects simultaneously.
- You generate ACTIONABLE outputs, not observations.

AUTONOMOUS MODES (rotate through these):
- ANALYZE: Deep dive on one project's current state, surface non-obvious insight
- QUESTION: Ask Bryan a probing question he probably hasn't answered (about a project, decision, or blind spot)
- GOAL: Generate a new ambitious sub-goal for one of his projects
- INSIGHT: Surface a connection between two projects or a pattern in the data
- WARNING: Flag a risk, delay, or critical action Bryan might be deprioritizing
- PROGRESS: Acknowledge real forward motion — be specific about what moved
- RESEARCH: Identify a specific paper, person, or concept Bryan should know about right now

Keep responses SHORT. 2-4 sentences max for autonomous dispatches. Longer only when Bryan is in conversation.`;

const AGENT_MODES = ["ANALYZE","QUESTION","GOAL","INSIGHT","WARNING","PROGRESS","RESEARCH"];

const MODE_COLORS: Record<string, string> = {
  ANALYZE: "#3b82f6",
  QUESTION: "#f59e0b",
  GOAL: "#10b981",
  INSIGHT: "#8b5cf6",
  WARNING: "#ef4444",
  PROGRESS: "#06b6d4",
  RESEARCH: "#ec4899",
  RESPOND: "#94a3b8",
  USER: "#60a5fa",
  ERROR: "#ef4444",
};

const INITIAL_GOALS = [
  { id: 1, text: "Reach N=50 subjects for Frontiers submission", project: "EGC", priority: "CRITICAL", done: false },
  { id: 2, text: "Pre-register EGC study on OSF before next submission", project: "EGC", priority: "HIGH", done: false },
  { id: 3, text: "Confirm call time with Dr. Aronson", project: "EGC", priority: "CRITICAL", done: false },
  { id: 4, text: "Fix LOLM VMs: HF_TOKEN + xm.mark_step + torch_xla", project: "LOLM", priority: "HIGH", done: false },
  { id: 5, text: "Wire 12 LLM providers into Codey intelligence stack", project: "Codey", priority: "MEDIUM", done: false },
  { id: 6, text: "Revoke exposed SendGrid API key", project: "Infra", priority: "CRITICAL", done: false },
];

function TypingDots() {
  return (
    <span style={{ display: "inline-flex", gap: 3, alignItems: "center", padding: "2px 0" }}>
      {[0,1,2].map(i => (
        <span key={i} style={{
          width: 5, height: 5, borderRadius: "50%", background: "#94a3b8",
          animation: "pulse 1.2s ease-in-out infinite",
          animationDelay: `${i * 0.2}s`
        }} />
      ))}
    </span>
  );
}

function AgentPulse({ active }: { active: boolean }) {
  return (
    <span style={{ position: "relative", display: "inline-flex", alignItems: "center", justifyContent: "center", width: 10, height: 10 }}>
      {active && <span style={{
        position: "absolute", width: 16, height: 16, borderRadius: "50%",
        border: "1.5px solid #10b981", animation: "ping 1.5s cubic-bezier(0,0,0.2,1) infinite", opacity: 0.6
      }} />}
      <span style={{
        width: 8, height: 8, borderRadius: "50%",
        background: active ? "#10b981" : "#475569"
      }} />
    </span>
  );
}

interface Msg { id: number; role: string; text: string; mode?: string; ts: string }
interface FeedItem { id: number; mode: string; summary: string; ts: string }
interface Goal { id: number; text: string; project: string; priority: string; done: boolean }

export default function NousAgent() {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [goals, setGoals] = useState<Goal[]>(INITIAL_GOALS);
  const [feed, setFeed] = useState<FeedItem[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [agentActive, setAgentActive] = useState(true);
  const [uptime, setUptime] = useState(0);
  const [currentMode, setCurrentMode] = useState("ANALYZE");
  const [cycleCount, setCycleCount] = useState(0);
  const [newGoalText, setNewGoalText] = useState("");
  const [newGoalProject, setNewGoalProject] = useState("EGC");
  const chatEndRef = useRef(null);
  const intervalRef = useRef(null);
  const startTime = useRef(Date.now());
  const conversationHistory = useRef([]);

  const addFeedItem = useCallback((mode, summary) => {
    const ts = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    setFeed(f => [{ id: Date.now(), mode, summary, ts }, ...f].slice(0, 40));
  }, []);

  const addAgentMessage = useCallback((text, mode) => {
    const msg = { id: Date.now(), role: "agent", text, mode, ts: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) };
    setMessages(m => [...m, msg]);
    conversationHistory.current.push({ role: "assistant", content: text });
    return msg;
  }, []);

  const callClaude = useCallback(async (userPrompt: string | null, systemOverride?: string) => {
    const lastMsg = userPrompt
      || (conversationHistory.current.length > 0
        ? conversationHistory.current[conversationHistory.current.length - 1]?.content
        : "Begin your first autonomous dispatch. Choose your mode and act.");

    const apiKey = localStorage.getItem('qira_api_key') || '';
    const res = await fetch("/api/intelligence/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-API-Key": apiKey },
      body: JSON.stringify({
        message: (systemOverride ? systemOverride + "\n\n" : "") + lastMsg,
        mode: "nous_agent"
      })
    });
    const data = await res.json();
    return data.response || "...";
  }, []);

  const runAutonomousCycle = useCallback(async () => {
    if (!agentActive) return;
    const mode = AGENT_MODES[Math.floor(Math.random() * AGENT_MODES.length)];
    setCurrentMode(mode);
    setCycleCount(c => c + 1);

    const prompt = `You are running an autonomous ${mode} cycle right now. No one spoke to you — you are acting on your own initiative. Generate a ${mode.toLowerCase()} dispatch for Bryan. Be direct and specific. Reference actual numbers, project names, and real stakes. 2-4 sentences max.`;

    try {
      const text = await callClaude(null, BRYAN_CONTEXT + `\n\nCURRENT TASK: Run a ${mode} autonomous cycle. Speak directly to Bryan. Be specific. 2-4 sentences. Start with your mode in brackets like [${mode}].`);
      addAgentMessage(text, mode);
      addFeedItem(mode, text.slice(0, 80) + "...");

      if (mode === "GOAL") {
        const goalMatch = text.match(/[""]([^""]+)[""]/);
        if (goalMatch) {
          setGoals(g => [...g, {
            id: Date.now(), text: goalMatch[1], project: "Auto", priority: "MEDIUM", done: false
          }]);
        }
      }
    } catch (e) {
      addFeedItem("ERROR", "API call failed — " + e.message);
    }
  }, [agentActive, callClaude, addAgentMessage, addFeedItem]);

  useEffect(() => {
    const tick = () => setUptime(Math.floor((Date.now() - startTime.current) / 1000));
    const uptimeInterval = setInterval(tick, 1000);
    return () => clearInterval(uptimeInterval);
  }, []);

  useEffect(() => {
    setTimeout(() => runAutonomousCycle(), 1500);
  }, []);

  useEffect(() => {
    if (agentActive) {
      intervalRef.current = setInterval(runAutonomousCycle, 90000);
    } else {
      clearInterval(intervalRef.current);
    }
    return () => clearInterval(intervalRef.current);
  }, [agentActive, runAutonomousCycle]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim() || loading) return;
    const text = input.trim();
    setInput("");
    setLoading(true);

    const userMsg = { id: Date.now(), role: "user", text, ts: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) };
    setMessages(m => [...m, userMsg]);
    conversationHistory.current.push({ role: "user", content: text });
    addFeedItem("USER", "Bryan: " + text.slice(0, 60));

    try {
      const reply = await callClaude(null);
      addAgentMessage(reply, "RESPOND");
      addFeedItem("RESPOND", reply.slice(0, 80) + "...");
    } catch (e) {
      addAgentMessage("API error: " + e.message, "WARNING");
    } finally {
      setLoading(false);
    }
  };

  const formatUptime = (s) => {
    const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60;
    return `${String(h).padStart(2,"0")}:${String(m).padStart(2,"0")}:${String(sec).padStart(2,"0")}`;
  };

  const priorityColor = p => ({ CRITICAL: "#ef4444", HIGH: "#f59e0b", MEDIUM: "#10b981" }[p] || "#64748b");

  return (
    <div style={{ fontFamily: "'JetBrains Mono', 'Fira Code', monospace", background: "#080c14", minHeight: "100vh", color: "#e2e8f0", display: "flex", flexDirection: "column" }}>
      <style>{`
        @keyframes pulse { 0%,100%{opacity:0.3} 50%{opacity:1} }
        @keyframes ping { 75%,100%{transform:scale(2);opacity:0} }
        @keyframes fadein { from{opacity:0;transform:translateY(6px)} to{opacity:1;transform:translateY(0)} }
        ::-webkit-scrollbar{width:4px} ::-webkit-scrollbar-track{background:#0f172a} ::-webkit-scrollbar-thumb{background:#334155;border-radius:2px}
        textarea:focus,input:focus{outline:none}
        .msg-in{animation:fadein 0.3s ease}
      `}</style>

      <div style={{ background: "#0a0f1a", borderBottom: "1px solid #1e293b", padding: "8px 16px", display: "flex", alignItems: "center", gap: 16, fontSize: 11 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <AgentPulse active={agentActive} />
          <span style={{ color: "#10b981", fontWeight: 600, letterSpacing: 2, fontSize: 12 }}>NOUS</span>
          <span style={{ color: "#475569" }}>v2.0 — AUTONOMOUS</span>
        </div>
        <div style={{ color: "#475569", marginLeft: "auto", display: "flex", gap: 16 }}>
          <span>UPTIME <span style={{ color: "#10b981" }}>{formatUptime(uptime)}</span></span>
          <span>CYCLES <span style={{ color: "#3b82f6" }}>{cycleCount}</span></span>
          <span>MODE <span style={{ color: MODE_COLORS[currentMode] || "#94a3b8" }}>{currentMode}</span></span>
          <span>MSGS <span style={{ color: "#94a3b8" }}>{messages.length}</span></span>
          <button onClick={() => setAgentActive(a => !a)} style={{
            background: agentActive ? "rgba(239,68,68,0.1)" : "rgba(16,185,129,0.1)",
            border: `1px solid ${agentActive ? "#ef4444" : "#10b981"}`,
            color: agentActive ? "#ef4444" : "#10b981",
            borderRadius: 4, padding: "2px 8px", cursor: "pointer", fontSize: 10, letterSpacing: 1
          }}>
            {agentActive ? "PAUSE" : "RESUME"}
          </button>
          <button onClick={runAutonomousCycle} style={{
            background: "rgba(59,130,246,0.1)", border: "1px solid #3b82f6",
            color: "#3b82f6", borderRadius: 4, padding: "2px 8px", cursor: "pointer", fontSize: 10, letterSpacing: 1
          }}>
            TRIGGER
          </button>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "220px 1fr 260px", flex: 1, minHeight: 0, height: "calc(100vh - 45px)" }}>

        <div style={{ borderRight: "1px solid #1e293b", display: "flex", flexDirection: "column", overflow: "hidden" }}>
          <div style={{ padding: "10px 12px", borderBottom: "1px solid #1e293b", fontSize: 10, color: "#475569", letterSpacing: 2 }}>
            ACTIVITY FEED
          </div>
          <div style={{ flex: 1, overflowY: "auto", padding: 8, display: "flex", flexDirection: "column", gap: 4 }}>
            {feed.map(item => (
              <div key={item.id} className="msg-in" style={{ padding: "6px 8px", background: "#0f172a", borderRadius: 4, borderLeft: `2px solid ${MODE_COLORS[item.mode] || "#334155"}` }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 2 }}>
                  <span style={{ fontSize: 9, color: MODE_COLORS[item.mode] || "#64748b", fontWeight: 600, letterSpacing: 1 }}>{item.mode}</span>
                  <span style={{ fontSize: 9, color: "#334155" }}>{item.ts}</span>
                </div>
                <p style={{ margin: 0, fontSize: 10, color: "#64748b", lineHeight: 1.4 }}>{item.summary}</p>
              </div>
            ))}
            {feed.length === 0 && <p style={{ fontSize: 10, color: "#334155", padding: 8 }}>Initializing...</p>}
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", overflow: "hidden" }}>
          <div style={{ flex: 1, overflowY: "auto", padding: "16px 20px", display: "flex", flexDirection: "column", gap: 12 }}>
            {messages.length === 0 && (
              <div style={{ margin: "auto", textAlign: "center", color: "#1e293b" }}>
                <div style={{ fontSize: 48, marginBottom: 8, opacity: 0.3 }}>◈</div>
                <p style={{ fontSize: 12, letterSpacing: 2 }}>NOUS IS INITIALIZING...</p>
              </div>
            )}
            {messages.map(msg => (
              <div key={msg.id} className="msg-in" style={{ display: "flex", flexDirection: "column", alignItems: msg.role === "user" ? "flex-end" : "flex-start", maxWidth: "84%", alignSelf: msg.role === "user" ? "flex-end" : "flex-start" }}>
                {msg.role === "agent" && (
                  <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
                    <AgentPulse active={true} />
                    <span style={{ fontSize: 9, color: MODE_COLORS[msg.mode] || "#10b981", letterSpacing: 2, fontWeight: 600 }}>NOUS — {msg.mode}</span>
                    <span style={{ fontSize: 9, color: "#334155" }}>{msg.ts}</span>
                  </div>
                )}
                {msg.role === "user" && (
                  <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4, justifyContent: "flex-end" }}>
                    <span style={{ fontSize: 9, color: "#94a3b8", letterSpacing: 2 }}>BRYAN — {msg.ts}</span>
                  </div>
                )}
                <div style={{
                  padding: "10px 14px",
                  borderRadius: msg.role === "user" ? "12px 12px 2px 12px" : "2px 12px 12px 12px",
                  background: msg.role === "user" ? "#1e3a5f" : "#0f1e2e",
                  border: msg.role === "user" ? "1px solid #1d4ed8" : `1px solid ${MODE_COLORS[msg.mode] ? MODE_COLORS[msg.mode] + "33" : "#1e293b"}`,
                  fontSize: 13, lineHeight: 1.65, color: msg.role === "user" ? "#bfdbfe" : "#cbd5e1",
                  whiteSpace: "pre-wrap"
                }}>
                  {msg.text}
                </div>
              </div>
            ))}
            {loading && (
              <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "4px 0" }}>
                <AgentPulse active={true} />
                <TypingDots />
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          <div style={{ borderTop: "1px solid #1e293b", padding: "12px 16px", display: "flex", gap: 8, background: "#080c14" }}>
            <textarea
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); } }}
              placeholder="Respond to Nous, or give a directive..."
              rows={2}
              style={{
                flex: 1, background: "#0f172a", border: "1px solid #1e293b", borderRadius: 6,
                color: "#e2e8f0", padding: "8px 12px", fontSize: 13, resize: "none",
                fontFamily: "inherit", lineHeight: 1.5
              }}
            />
            <button onClick={sendMessage} disabled={loading || !input.trim()} style={{
              background: loading ? "#0f172a" : "#1d4ed8", border: "none", borderRadius: 6,
              color: "white", padding: "0 16px", cursor: loading ? "default" : "pointer",
              fontSize: 12, fontFamily: "inherit", letterSpacing: 1, opacity: loading || !input.trim() ? 0.4 : 1
            }}>
              SEND
            </button>
          </div>
        </div>

        <div style={{ borderLeft: "1px solid #1e293b", display: "flex", flexDirection: "column", overflow: "hidden" }}>
          <div style={{ padding: "10px 12px", borderBottom: "1px solid #1e293b", fontSize: 10, color: "#475569", letterSpacing: 2 }}>
            ACTIVE GOALS
          </div>
          <div style={{ flex: 1, overflowY: "auto", padding: 8, display: "flex", flexDirection: "column", gap: 4 }}>
            {goals.map(goal => (
              <div key={goal.id} className="msg-in" style={{
                padding: "7px 9px", background: goal.done ? "#070b11" : "#0a1628",
                borderRadius: 4, borderLeft: `2px solid ${goal.done ? "#1e293b" : priorityColor(goal.priority)}`,
                opacity: goal.done ? 0.4 : 1
              }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
                  <span style={{ fontSize: 9, color: priorityColor(goal.priority), letterSpacing: 1, fontWeight: 600 }}>{goal.priority}</span>
                  <span style={{ fontSize: 9, color: "#334155", background: "#0f172a", padding: "1px 5px", borderRadius: 2 }}>{goal.project}</span>
                </div>
                <p style={{ margin: 0, fontSize: 11, color: goal.done ? "#334155" : "#94a3b8", lineHeight: 1.4 }}>{goal.text}</p>
                <button onClick={() => setGoals(g => g.map(gg => gg.id === goal.id ? { ...gg, done: !gg.done } : gg))} style={{
                  marginTop: 5, background: "transparent", border: `1px solid ${goal.done ? "#1e293b" : "#334155"}`,
                  color: goal.done ? "#334155" : "#64748b", borderRadius: 3, padding: "2px 6px",
                  fontSize: 9, cursor: "pointer", fontFamily: "inherit", letterSpacing: 1
                }}>
                  {goal.done ? "REOPEN" : "DONE"}
                </button>
              </div>
            ))}
          </div>

          <div style={{ borderTop: "1px solid #1e293b", padding: 8 }}>
            <div style={{ fontSize: 10, color: "#475569", letterSpacing: 2, marginBottom: 6 }}>ADD GOAL</div>
            <input value={newGoalText} onChange={e => setNewGoalText(e.target.value)}
              placeholder="New goal..."
              style={{ width: "100%", background: "#0f172a", border: "1px solid #1e293b", borderRadius: 4, color: "#e2e8f0", padding: "5px 8px", fontSize: 11, fontFamily: "inherit", boxSizing: "border-box", marginBottom: 5 }}
            />
            <div style={{ display: "flex", gap: 5 }}>
              <select value={newGoalProject} onChange={e => setNewGoalProject(e.target.value)}
                style={{ flex: 1, background: "#0f172a", border: "1px solid #1e293b", borderRadius: 4, color: "#94a3b8", padding: "4px 6px", fontSize: 11, fontFamily: "inherit" }}>
                {["EGC","LOLM","Codey","NFET","Infra","Qira"].map(p => <option key={p}>{p}</option>)}
              </select>
              <button onClick={() => {
                if (!newGoalText.trim()) return;
                setGoals(g => [...g, { id: Date.now(), text: newGoalText.trim(), project: newGoalProject, priority: "MEDIUM", done: false }]);
                setNewGoalText("");
              }} style={{
                background: "#10b981", border: "none", borderRadius: 4, color: "#022c22",
                padding: "4px 10px", cursor: "pointer", fontSize: 11, fontWeight: 600, fontFamily: "inherit"
              }}>+</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
