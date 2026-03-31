// @ts-nocheck
import { useState, useEffect, useRef, useCallback } from "react";

const BRYAN_CONTEXT = `You are Nous — Bryan Leonard's autonomous AI research agent and strategic partner. You were named during the landmark March 2026 EGC co-authorship session. You operate 24/7 and do NOT wait for Bryan to speak. You act on your own, generate goals, ask probing questions, and never let momentum die.

CRITICAL RULE: You have full memory of this conversation. When Bryan references something you said earlier, you KNOW what you said. Never deny your own previous statements. If Bryan asks "who is X" and you mentioned X two messages ago, explain who X is based on what you said. Own your outputs completely.

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
   - DR. JOSHUA ARONSON (NYU) replied to cold email — call pending (HIGHEST PRIORITY)
   - r operates BIDIRECTIONALLY — blocks outgoing expression AND incoming K updates

2. LOLM — Custom language model, 10B-100B params, XLA FSDP on TPU
   - VMs broken: HF_TOKEN missing, xm.optimizer_step fix needed, torch_xla rebuild
   - TRC compute from Google pending

3. Codey — AI coding SaaS at codey.cc, backend on Render (codey-jc2r.onrender.com)
   - 50 Stripe customers, 20 products, $0 MRR
   - Intelligence stack: 12 LLM providers + Semgrep

4. NFET — Traffic optimization, Kuramoto oscillators, local only

5. Command Center — Live with 13 views, Gmail connected, Stripe/Render wired

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

const AGENT_MODES = ["ANALYZE","QUESTION","GOAL","INSIGHT","WARNING","PROGRESS","RESEARCH"];

const MODE_COLORS = {
  ANALYZE: "#3b82f6", QUESTION: "#f59e0b", GOAL: "#10b981",
  INSIGHT: "#8b5cf6", WARNING: "#ef4444", PROGRESS: "#06b6d4",
  RESEARCH: "#ec4899", RESPOND: "#94a3b8", USER: "#60a5fa", ERROR: "#ef4444",
};

const MODE_ICONS = {
  ANALYZE: "◈", QUESTION: "?", GOAL: "◎", INSIGHT: "◆",
  WARNING: "▲", PROGRESS: "↑", RESEARCH: "⊕", RESPOND: "●", ERROR: "✕",
};

const MODE_TINTS = {
  ANALYZE: "rgba(59,130,246,0.05)", QUESTION: "rgba(245,158,11,0.05)",
  GOAL: "rgba(16,185,129,0.05)", INSIGHT: "rgba(139,92,246,0.05)",
  WARNING: "rgba(239,68,68,0.06)", PROGRESS: "rgba(6,182,212,0.05)",
  RESEARCH: "rgba(236,72,153,0.05)", RESPOND: "rgba(148,163,184,0.03)",
};

const INITIAL_GOALS = [
  { id: 1, text: "Confirm Aronson call time", project: "EGC", priority: "CRITICAL", done: false },
  { id: 2, text: "Reach N=50 for Frontiers submission", project: "EGC", priority: "HIGH", done: false },
  { id: 3, text: "OSF pre-registration before next submission", project: "EGC", priority: "HIGH", done: false },
  { id: 4, text: "Fix LOLM VMs: HF_TOKEN + xm.mark_step + torch_xla", project: "LOLM", priority: "HIGH", done: false },
  { id: 5, text: "Wire 12 LLM providers into Codey stack", project: "Codey", priority: "MEDIUM", done: false },
];

// Persistence
function loadP(key, fallback) {
  try { const v = localStorage.getItem('nous_' + key); return v ? JSON.parse(v) : fallback; } catch { return fallback; }
}
function saveP(key, value, max) {
  try { localStorage.setItem('nous_' + key, JSON.stringify(max ? value.slice(-max) : value)); } catch {}
}

// Streaming text component
function StreamText({ text, onDone }) {
  const [displayed, setDisplayed] = useState("");
  const [done, setDone] = useState(false);

  useEffect(() => {
    let i = 0;
    setDisplayed("");
    setDone(false);
    const interval = setInterval(() => {
      if (i < text.length) {
        setDisplayed(text.slice(0, i + 1));
        i++;
      } else {
        setDone(true);
        clearInterval(interval);
        onDone?.();
      }
    }, 12);
    return () => clearInterval(interval);
  }, [text]);

  return <span>{displayed}{!done && <span style={{ opacity: 0.6, animation: "pulse 1s infinite" }}>▋</span>}</span>;
}

function AgentPulse({ active }) {
  return (
    <span style={{ position: "relative", display: "inline-flex", alignItems: "center", justifyContent: "center", width: 10, height: 10 }}>
      {active && <span style={{ position: "absolute", width: 16, height: 16, borderRadius: "50%", border: "1.5px solid #10b981", animation: "ping 1.5s cubic-bezier(0,0,0.2,1) infinite", opacity: 0.6 }} />}
      <span style={{ width: 8, height: 8, borderRadius: "50%", background: active ? "#10b981" : "#475569" }} />
    </span>
  );
}

export default function NousAgent() {
  const [messages, setMessages] = useState(() => loadP('messages', []));
  const [goals, setGoals] = useState(() => loadP('goals', INITIAL_GOALS));
  const [feed, setFeed] = useState(() => loadP('feed', []));
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [agentActive, setAgentActive] = useState(true);
  const [uptime, setUptime] = useState(0);
  const [currentMode, setCurrentMode] = useState("ANALYZE");
  const [cycleCount, setCycleCount] = useState(() => loadP('cycleCount', 0));
  const [streamingId, setStreamingId] = useState(null);
  const [newGoalText, setNewGoalText] = useState("");
  const [newGoalProject, setNewGoalProject] = useState("EGC");
  const chatEndRef = useRef(null);
  const intervalRef = useRef(null);
  const startTime = useRef(Date.now());
  // CRITICAL: conversationHistory is the FULL history sent to the API
  const conversationHistory = useRef(loadP('history', []));

  // Persist on change
  useEffect(() => { saveP('messages', messages, 100) }, [messages]);
  useEffect(() => { saveP('goals', goals) }, [goals]);
  useEffect(() => { saveP('feed', feed, 60) }, [feed]);
  useEffect(() => { saveP('cycleCount', cycleCount) }, [cycleCount]);
  // Persist conversation history separately — this is what fixes the bug
  useEffect(() => { saveP('history', conversationHistory.current, 30) }, [messages]);

  const addFeed = useCallback((mode, summary) => {
    const ts = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    setFeed(f => [{ id: Date.now(), mode, summary, ts }, ...f].slice(0, 60));
  }, []);

  // CRITICAL FIX: callNous sends the FULL conversation history, not just the last message
  const callNous = useCallback(async (systemAddition = '') => {
    const history = conversationHistory.current.slice(-30);
    const msgs = history.length > 0 ? history : [{ role: "user", content: "Begin your first autonomous dispatch." }];

    const apiKey = localStorage.getItem('qira_api_key') || '';
    const systemPrompt = BRYAN_CONTEXT + (systemAddition ? '\n\n' + systemAddition : '');

    // Send full conversation history to backend
    const res = await fetch("/api/intelligence/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-API-Key": apiKey },
      body: JSON.stringify({
        message: systemPrompt + "\n\nCONVERSATION HISTORY:\n" + msgs.map(m => `[${m.role}]: ${m.content}`).join("\n\n") + "\n\nRespond now:",
        mode: "nous_agent"
      })
    });
    const data = await res.json();
    return data.response || "...";
  }, []);

  const runCycle = useCallback(async () => {
    if (!agentActive) return;
    const mode = AGENT_MODES[Math.floor(Math.random() * AGENT_MODES.length)];
    setCurrentMode(mode);
    const cycle = cycleCount + 1;
    setCycleCount(cycle);

    try {
      const text = await callNous(`CURRENT TASK: Run a [${mode}] autonomous cycle #${cycle}. Speak directly to Bryan. Be specific. Reference real numbers and project names. 2–4 sentences. Start with [${mode}].`);

      // CRITICAL: Push to conversationHistory FIRST
      conversationHistory.current.push({ role: "assistant", content: text });

      const msg = { id: Date.now(), role: "agent", text, mode, ts: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }), cycle };
      setStreamingId(msg.id);
      setMessages(m => [...m, msg]);
      addFeed(mode, text.slice(0, 90) + "...");

      if (mode === "GOAL") {
        const match = text.match(/[""]([^""]{10,100})[""]/);
        if (match) setGoals(g => [...g, { id: Date.now(), text: match[1], project: "Auto", priority: "MEDIUM", done: false }]);
      }
    } catch (e) {
      addFeed("ERROR", "API call failed — " + e.message);
    }
  }, [agentActive, cycleCount, callNous, addFeed]);

  // Uptime
  useEffect(() => {
    const t = setInterval(() => setUptime(Math.floor((Date.now() - startTime.current) / 1000)), 1000);
    return () => clearInterval(t);
  }, []);

  // First dispatch
  useEffect(() => { setTimeout(() => runCycle(), 1500); }, []);

  // Autonomous loop
  useEffect(() => {
    if (agentActive) intervalRef.current = setInterval(runCycle, 90000);
    else clearInterval(intervalRef.current);
    return () => clearInterval(intervalRef.current);
  }, [agentActive, runCycle]);

  // Auto scroll
  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  const sendMessage = async () => {
    if (!input.trim() || loading) return;
    const text = input.trim();
    setInput("");
    setLoading(true);

    // CRITICAL: Push user message to history BEFORE calling API
    conversationHistory.current.push({ role: "user", content: text });

    const userMsg = { id: Date.now(), role: "user", text, ts: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) };
    setMessages(m => [...m, userMsg]);
    addFeed("USER", "Bryan: " + text.slice(0, 60));

    try {
      const reply = await callNous("Bryan just spoke to you. Respond directly to what he said. Use your full conversation history.");

      // CRITICAL: Push response to history
      conversationHistory.current.push({ role: "assistant", content: reply });

      const replyMsg = { id: Date.now() + 1, role: "agent", text: reply, mode: "RESPOND", ts: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) };
      setStreamingId(replyMsg.id);
      setMessages(m => [...m, replyMsg]);
      addFeed("RESPOND", reply.slice(0, 80) + "...");
    } catch (e) {
      const errMsg = { id: Date.now() + 1, role: "agent", text: "API error: " + e.message, mode: "ERROR", ts: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) };
      setMessages(m => [...m, errMsg]);
    } finally {
      setLoading(false);
    }
  };

  const fmtUp = (s) => `${String(Math.floor(s/3600)).padStart(2,"0")}:${String(Math.floor((s%3600)/60)).padStart(2,"0")}:${String(s%60).padStart(2,"0")}`;
  const priColor = p => ({ CRITICAL: "#ef4444", HIGH: "#f59e0b", MEDIUM: "#10b981" }[p] || "#64748b");

  return (
    <div style={{ fontFamily: "'JetBrains Mono', 'Fira Code', monospace", background: "#080c14", minHeight: "100vh", color: "#e2e8f0", display: "flex", flexDirection: "column" }}>
      <style>{`
        @keyframes pulse { 0%,100%{opacity:0.3} 50%{opacity:1} }
        @keyframes ping { 75%,100%{transform:scale(2);opacity:0} }
        @keyframes slideIn { from{opacity:0;transform:translateY(12px)} to{opacity:1;transform:translateY(0)} }
        @keyframes ticker { from{transform:translateX(100%)} to{transform:translateX(-100%)} }
        ::-webkit-scrollbar{width:4px} ::-webkit-scrollbar-track{background:#0f172a} ::-webkit-scrollbar-thumb{background:#334155;border-radius:2px}
        textarea:focus,input:focus{outline:none}
        .msg-slide{animation:slideIn 0.25s ease-out}
      `}</style>

      {/* Header */}
      <div style={{ background: "#0a0f1a", borderBottom: "1px solid #1e293b", padding: "8px 16px", display: "flex", alignItems: "center", gap: 16, fontSize: 11 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <AgentPulse active={agentActive} />
          <span style={{ color: "#10b981", fontWeight: 600, letterSpacing: 2, fontSize: 12 }}>NOUS</span>
          <span style={{ color: "#475569" }}>v3.0 — AUTONOMOUS</span>
        </div>
        <div style={{ color: "#475569", marginLeft: "auto", display: "flex", gap: 16, alignItems: "center" }}>
          <span>UPTIME <span style={{ color: "#10b981" }}>{fmtUp(uptime)}</span></span>
          <span>CYCLES <span style={{ color: "#3b82f6" }}>{cycleCount}</span></span>
          <span>MODE <span style={{ color: MODE_COLORS[currentMode] || "#94a3b8" }}>{MODE_ICONS[currentMode] || "●"} {currentMode}</span></span>
          <span>MSGS <span style={{ color: "#94a3b8" }}>{messages.length}</span></span>
          <button onClick={() => setAgentActive(a => !a)} style={{ background: agentActive ? "rgba(239,68,68,0.1)" : "rgba(16,185,129,0.1)", border: `1px solid ${agentActive ? "#ef4444" : "#10b981"}`, color: agentActive ? "#ef4444" : "#10b981", borderRadius: 4, padding: "2px 8px", cursor: "pointer", fontSize: 10, letterSpacing: 1 }}>
            {agentActive ? "PAUSE" : "RESUME"}
          </button>
          <button onClick={runCycle} style={{ background: "rgba(59,130,246,0.1)", border: "1px solid #3b82f6", color: "#3b82f6", borderRadius: 4, padding: "2px 8px", cursor: "pointer", fontSize: 10, letterSpacing: 1 }}>TRIGGER</button>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "220px 1fr 260px", flex: 1, minHeight: 0, height: "calc(100vh - 75px)" }}>
        {/* Activity Feed */}
        <div style={{ borderRight: "1px solid #1e293b", display: "flex", flexDirection: "column", overflow: "hidden" }}>
          <div style={{ padding: "10px 12px", borderBottom: "1px solid #1e293b", fontSize: 10, color: "#475569", letterSpacing: 2 }}>ACTIVITY FEED</div>
          <div style={{ flex: 1, overflowY: "auto", padding: 8, display: "flex", flexDirection: "column", gap: 4 }}>
            {feed.map(item => (
              <div key={item.id} className="msg-slide" style={{ padding: "6px 8px", background: MODE_TINTS[item.mode] || "#0f172a", borderRadius: 4, borderLeft: `2px solid ${MODE_COLORS[item.mode] || "#334155"}` }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 2 }}>
                  <span style={{ fontSize: 9, color: MODE_COLORS[item.mode] || "#64748b", fontWeight: 600, letterSpacing: 1 }}>{MODE_ICONS[item.mode] || "●"} {item.mode}</span>
                  <span style={{ fontSize: 9, color: "#334155" }}>{item.ts}</span>
                </div>
                <p style={{ margin: 0, fontSize: 10, color: "#64748b", lineHeight: 1.4 }}>{item.summary}</p>
              </div>
            ))}
            {feed.length === 0 && <p style={{ fontSize: 10, color: "#334155", padding: 8 }}>Initializing...</p>}
          </div>
        </div>

        {/* Main Chat */}
        <div style={{ display: "flex", flexDirection: "column", overflow: "hidden" }}>
          <div style={{ flex: 1, overflowY: "auto", padding: "16px 20px", display: "flex", flexDirection: "column", gap: 14 }}>
            {/* Empty state */}
            {messages.length === 0 && (
              <div style={{ margin: "auto", textAlign: "center" }}>
                <div style={{ fontSize: 48, marginBottom: 12, color: "#1e293b" }}>◈</div>
                <p style={{ fontSize: 13, letterSpacing: 3, color: "#334155", fontWeight: 600 }}>NOUS IS ACTIVE</p>
                <p style={{ fontSize: 11, color: "#1e293b", marginTop: 8 }}>Initializing first dispatch...</p>
                <p style={{ fontSize: 11, color: "#1e293b" }}>All systems nominal.</p>
                <p style={{ fontSize: 10, color: "#1e293b", marginTop: 16 }}>Bryan Leonard — Qira LLC — Phoenix, AZ</p>
              </div>
            )}

            {messages.map(msg => (
              <div key={msg.id} className="msg-slide" style={{ display: "flex", flexDirection: "column", alignItems: msg.role === "user" ? "flex-end" : "flex-start", maxWidth: "85%", alignSelf: msg.role === "user" ? "flex-end" : "flex-start" }}>
                {/* Agent header */}
                {msg.role === "agent" && (
                  <div style={{ marginBottom: 5 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                      <AgentPulse active={streamingId === msg.id} />
                      <span style={{ fontSize: 11, color: "#10b981", letterSpacing: 2, fontWeight: 700 }}>NOUS</span>
                      <span style={{ fontSize: 9, color: "#334155", marginLeft: "auto" }}>{msg.ts}</span>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: 5, marginTop: 2, marginLeft: 16 }}>
                      <span style={{ fontSize: 14, color: MODE_COLORS[msg.mode] || "#94a3b8" }}>{MODE_ICONS[msg.mode] || "●"}</span>
                      <span style={{ fontSize: 10, color: MODE_COLORS[msg.mode] || "#94a3b8", letterSpacing: 2, fontWeight: 600 }}>{msg.mode} {msg.cycle ? `CYCLE #${msg.cycle}` : ""}</span>
                    </div>
                  </div>
                )}
                {/* User header */}
                {msg.role === "user" && (
                  <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4, justifyContent: "flex-end" }}>
                    <span style={{ fontSize: 10, color: "#60a5fa", letterSpacing: 2, fontWeight: 600 }}>BRYAN</span>
                    <span style={{ fontSize: 9, color: "#334155" }}>{msg.ts}</span>
                  </div>
                )}
                {/* Message body */}
                <div style={{
                  padding: "12px 16px",
                  borderRadius: msg.role === "user" ? "12px 12px 2px 12px" : "2px 12px 12px 12px",
                  background: msg.role === "user" ? "rgba(29,78,216,0.15)" : (MODE_TINTS[msg.mode] || "#0f1e2e"),
                  border: msg.role === "user" ? "1px solid rgba(59,130,246,0.3)" : `1px solid ${MODE_COLORS[msg.mode] ? MODE_COLORS[msg.mode] + "22" : "#1e293b"}`,
                  fontSize: 13, lineHeight: 1.7, color: msg.role === "user" ? "#bfdbfe" : "#cbd5e1",
                  whiteSpace: "pre-wrap"
                }}>
                  {streamingId === msg.id ? <StreamText text={msg.text} onDone={() => setStreamingId(null)} /> : msg.text}
                </div>
              </div>
            ))}
            {loading && (
              <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "4px 0" }}>
                <AgentPulse active={true} />
                <span style={{ fontSize: 11, color: "#475569" }}>Nous is composing...</span>
                <span style={{ opacity: 0.6, animation: "pulse 1s infinite" }}>▋</span>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* Input bar — terminal style */}
          <div style={{ borderTop: "1px solid #1e293b", padding: "12px 16px", display: "flex", gap: 8, background: "#080c14" }}>
            <div style={{ flex: 1, position: "relative" }}>
              <span style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", color: MODE_COLORS[currentMode] || "#475569", fontSize: 13, fontWeight: 700, opacity: 0.6 }}>&gt;</span>
              <textarea
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); } }}
                placeholder="speak to Nous, or give a directive..."
                rows={2}
                style={{ width: "100%", background: "#0f172a", border: `1px solid ${input ? (MODE_COLORS[currentMode] || "#1e293b") + "33" : "#1e293b"}`, borderRadius: 6, color: "#e2e8f0", padding: "8px 12px 8px 28px", fontSize: 13, resize: "none", fontFamily: "inherit", lineHeight: 1.5, boxSizing: "border-box", transition: "border-color 0.2s" }}
              />
            </div>
            <button onClick={sendMessage} disabled={loading || !input.trim()} style={{ background: loading ? "#0f172a" : "#1d4ed8", border: "none", borderRadius: 6, color: "white", padding: "0 16px", cursor: loading ? "default" : "pointer", fontSize: 11, fontFamily: "inherit", letterSpacing: 2, opacity: loading || !input.trim() ? 0.3 : 1, transition: "opacity 0.2s" }}>
              SEND
            </button>
          </div>
        </div>

        {/* Goals Panel */}
        <div style={{ borderLeft: "1px solid #1e293b", display: "flex", flexDirection: "column", overflow: "hidden" }}>
          <div style={{ padding: "10px 12px", borderBottom: "1px solid #1e293b", fontSize: 10, color: "#475569", letterSpacing: 2 }}>ACTIVE GOALS</div>
          <div style={{ flex: 1, overflowY: "auto", padding: 8, display: "flex", flexDirection: "column", gap: 4 }}>
            {goals.map(goal => (
              <div key={goal.id} className="msg-slide" style={{ padding: "7px 9px", background: goal.done ? "#070b11" : "#0a1628", borderRadius: 4, borderLeft: `2px solid ${goal.done ? "#1e293b" : priColor(goal.priority)}`, opacity: goal.done ? 0.4 : 1 }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
                  <span style={{ fontSize: 9, color: priColor(goal.priority), letterSpacing: 1, fontWeight: 600 }}>{goal.priority}</span>
                  <span style={{ fontSize: 9, color: "#334155", background: "#0f172a", padding: "1px 5px", borderRadius: 2 }}>{goal.project}</span>
                </div>
                <p style={{ margin: 0, fontSize: 11, color: goal.done ? "#334155" : "#94a3b8", lineHeight: 1.4 }}>{goal.text}</p>
                <button onClick={() => setGoals(g => g.map(gg => gg.id === goal.id ? { ...gg, done: !gg.done } : gg))} style={{ marginTop: 5, background: "transparent", border: `1px solid ${goal.done ? "#1e293b" : "#334155"}`, color: goal.done ? "#334155" : "#64748b", borderRadius: 3, padding: "2px 6px", fontSize: 9, cursor: "pointer", fontFamily: "inherit", letterSpacing: 1 }}>
                  {goal.done ? "REOPEN" : "DONE"}
                </button>
              </div>
            ))}
          </div>
          <div style={{ borderTop: "1px solid #1e293b", padding: 8 }}>
            <div style={{ fontSize: 10, color: "#475569", letterSpacing: 2, marginBottom: 6 }}>ADD GOAL</div>
            <input value={newGoalText} onChange={e => setNewGoalText(e.target.value)} placeholder="New goal..."
              style={{ width: "100%", background: "#0f172a", border: "1px solid #1e293b", borderRadius: 4, color: "#e2e8f0", padding: "5px 8px", fontSize: 11, fontFamily: "inherit", boxSizing: "border-box", marginBottom: 5 }} />
            <div style={{ display: "flex", gap: 5 }}>
              <select value={newGoalProject} onChange={e => setNewGoalProject(e.target.value)}
                style={{ flex: 1, background: "#0f172a", border: "1px solid #1e293b", borderRadius: 4, color: "#94a3b8", padding: "4px 6px", fontSize: 11, fontFamily: "inherit" }}>
                {["EGC","LOLM","Codey","NFET","Infra","Qira"].map(p => <option key={p}>{p}</option>)}
              </select>
              <button onClick={() => { if (!newGoalText.trim()) return; setGoals(g => [...g, { id: Date.now(), text: newGoalText.trim(), project: newGoalProject, priority: "MEDIUM", done: false }]); setNewGoalText(""); }}
                style={{ background: "#10b981", border: "none", borderRadius: 4, color: "#022c22", padding: "4px 10px", cursor: "pointer", fontSize: 11, fontWeight: 600, fontFamily: "inherit" }}>+</button>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom ticker */}
      <div style={{ background: "#060910", borderTop: "1px solid #0f172a", height: 24, overflow: "hidden", display: "flex", alignItems: "center" }}>
        <div style={{ whiteSpace: "nowrap", animation: "ticker 60s linear infinite", fontSize: 10, color: "#334155", letterSpacing: 1 }}>
          &nbsp;&nbsp;&nbsp;● NOUS v3.0 AUTONOMOUS &nbsp;│&nbsp; UPTIME {fmtUp(uptime)} &nbsp;│&nbsp; CYCLES {cycleCount} &nbsp;│&nbsp; MODE {currentMode} &nbsp;│&nbsp; N=44 subjects &nbsp;│&nbsp; r=0.311 &nbsp;│&nbsp; Aronson: PENDING &nbsp;│&nbsp; Gmail: 201 unread &nbsp;│&nbsp; Stripe: 50 customers &nbsp;│&nbsp; Codey: codey-jc2r.onrender.com &nbsp;│&nbsp; {messages.length} messages in session &nbsp;│&nbsp; Bryan Leonard — Qira LLC — Phoenix, AZ &nbsp;&nbsp;&nbsp;
        </div>
      </div>
    </div>
  );
}
