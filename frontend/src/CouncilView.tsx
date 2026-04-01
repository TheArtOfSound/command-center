// @ts-nocheck
import { useEffect, useState, useRef, useCallback } from 'react'

// ── AGENT DEFINITIONS ───────────────────────────────────────
const AGENTS = [
  { name: 'NOUS',   color: '#06b6d4', icon: '◈', role: 'Orchestrator',     offset: 0  },
  { name: 'AXIOM',  color: '#3b82f6', icon: '∑', role: 'Data Analyst',     offset: 16 },
  { name: 'VECTOR', color: '#10b981', icon: '⟁', role: 'Engineer',         offset: 32 },
  { name: 'CIPHER', color: '#f59e0b', icon: '◆', role: 'Strategist',       offset: 16 },
  { name: 'ECHO',   color: '#ef4444', icon: '∅', role: 'Devil\'s Advocate', offset: 0  },
]

const AGENT_MAP = Object.fromEntries(AGENTS.map(a => [a.name, a]))
const AGENT_NAMES = AGENTS.map(a => a.name)

function getApiBase() {
  const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  return isLocal ? '' : 'https://cc.autohustle.online'
}

function getApiKey() {
  return localStorage.getItem('qira_api_key') || ''
}

function apiHeaders() {
  return { 'Content-Type': 'application/json', 'X-API-Key': getApiKey() }
}

// ── PARTICLE CANVAS ─────────────────────────────────────────
function ParticleCanvas() {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    let animId: number
    let particles: { x: number; y: number; vx: number; vy: number; size: number; alpha: number }[] = []

    const resize = () => {
      canvas.width = canvas.offsetWidth
      canvas.height = canvas.offsetHeight
    }
    resize()
    window.addEventListener('resize', resize)

    for (let i = 0; i < 200; i++) {
      particles.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        vx: (Math.random() - 0.5) * 0.3,
        vy: (Math.random() - 0.5) * 0.3,
        size: Math.random() * 1.5 + 0.5,
        alpha: Math.random() * 0.3 + 0.05,
      })
    }

    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height)
      for (const p of particles) {
        p.x += p.vx
        p.y += p.vy
        if (p.x < 0) p.x = canvas.width
        if (p.x > canvas.width) p.x = 0
        if (p.y < 0) p.y = canvas.height
        if (p.y > canvas.height) p.y = 0
        ctx.beginPath()
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(6, 182, 212, ${p.alpha})`
        ctx.fill()
      }
      animId = requestAnimationFrame(draw)
    }
    draw()

    return () => {
      cancelAnimationFrame(animId)
      window.removeEventListener('resize', resize)
    }
  }, [])

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: 'absolute',
        inset: 0,
        width: '100%',
        height: '100%',
        pointerEvents: 'none',
        zIndex: 0,
      }}
    />
  )
}

// ── STREAM TEXT ──────────────────────────────────────────────
function StreamText({ text, onComplete }: { text: string; onComplete?: () => void }) {
  const [displayed, setDisplayed] = useState('')
  const indexRef = useRef(0)
  const completedRef = useRef(false)

  useEffect(() => {
    indexRef.current = 0
    completedRef.current = false
    setDisplayed('')

    const interval = setInterval(() => {
      indexRef.current++
      if (indexRef.current >= text.length) {
        setDisplayed(text)
        clearInterval(interval)
        if (!completedRef.current) {
          completedRef.current = true
          onComplete?.()
        }
        return
      }
      setDisplayed(text.slice(0, indexRef.current))
    }, 18)

    return () => clearInterval(interval)
  }, [text])

  return <span>{displayed}</span>
}

// ── PULSING DOT ─────────────────────────────────────────────
function PulsingDot({ color, size = 8 }: { color: string; size?: number }) {
  return (
    <span
      style={{
        display: 'inline-block',
        width: size,
        height: size,
        borderRadius: '50%',
        backgroundColor: color,
        animation: 'councilPulse 1.2s ease-in-out infinite',
        flexShrink: 0,
      }}
    />
  )
}

// ── THINKING INDICATOR ──────────────────────────────────────
function ThinkingIndicator({ agent }: { agent: typeof AGENTS[0] }) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        marginLeft: agent.offset,
        padding: '8px 12px',
        opacity: 0.7,
        animation: 'councilSlideIn 0.3s ease-out',
      }}
    >
      <PulsingDot color={agent.color} />
      <span style={{ fontFamily: 'monospace', fontSize: 12, color: agent.color }}>
        {agent.icon} {agent.name}
      </span>
      <span style={{ fontFamily: 'monospace', fontSize: 12, color: '#6b7280' }}>thinking...</span>
    </div>
  )
}

// ── TIME FORMATTING ─────────────────────────────────────────
function formatTime(ts: string) {
  try {
    const d = new Date(ts)
    return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })
  } catch {
    return ''
  }
}

function formatRelative(ts: string) {
  try {
    const diff = Date.now() - new Date(ts).getTime()
    if (diff < 60000) return 'just now'
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`
    return `${Math.floor(diff / 3600000)}h ago`
  } catch {
    return ''
  }
}

// ── MESSAGE COMPONENT ───────────────────────────────────────
function MessageBubble({
  msg,
  isNew,
  allMessages,
}: {
  msg: any
  isNew: boolean
  allMessages: any[]
}) {
  const isBryan = msg.sender === 'BRYAN' || msg.sender === 'USER'
  const agent = AGENT_MAP[msg.sender]

  const replyTarget = msg.replyTo
    ? allMessages.find((m) => m.id === msg.replyTo)
    : null

  if (isBryan) {
    return (
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'flex-end',
          marginBottom: 12,
          animation: isNew ? 'councilSlideIn 0.3s ease-out' : undefined,
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            marginBottom: 4,
          }}
        >
          <span style={{ fontFamily: 'monospace', fontSize: 11, color: '#6b7280' }}>
            {formatTime(msg.timestamp)}
          </span>
          <span style={{ fontFamily: 'monospace', fontSize: 12, fontWeight: 600, color: '#60a5fa' }}>
            BRYAN
          </span>
        </div>
        <div
          style={{
            maxWidth: '70%',
            padding: '10px 14px',
            borderRadius: 8,
            background: 'rgba(37, 99, 235, 0.1)',
            borderRight: '2px solid #3b82f6',
            fontFamily: 'monospace',
            fontSize: 13,
            color: '#e2e8f0',
            lineHeight: 1.5,
          }}
        >
          {msg.target && msg.target !== 'ALL' && (
            <span style={{ fontSize: 10, color: '#3b82f6', marginBottom: 4, display: 'block' }}>
              → {msg.target}
            </span>
          )}
          {isNew ? <StreamText text={msg.content} /> : msg.content}
        </div>
      </div>
    )
  }

  const color = agent?.color || '#6b7280'
  const icon = agent?.icon || '?'
  const offset = agent?.offset || 0

  return (
    <div
      style={{
        marginLeft: offset,
        marginBottom: 12,
        animation: isNew ? 'councilSlideIn 0.3s ease-out' : undefined,
        position: 'relative',
      }}
    >
      {replyTarget && (
        <div
          style={{
            position: 'absolute',
            left: -8,
            top: -10,
            width: 1,
            height: 20,
            background: `${color}33`,
          }}
        />
      )}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
        <span style={{ fontFamily: 'monospace', fontSize: 14, color }}>{icon}</span>
        <span style={{ fontFamily: 'monospace', fontSize: 12, fontWeight: 600, color }}>
          {msg.sender}
        </span>
        <span style={{ fontFamily: 'monospace', fontSize: 11, color: '#6b7280' }}>
          {formatTime(msg.timestamp)}
        </span>
        {msg.target && msg.target !== 'ALL' && (
          <span style={{ fontFamily: 'monospace', fontSize: 10, color: '#4b5563' }}>
            → {msg.target}
          </span>
        )}
      </div>
      <div
        style={{
          padding: '10px 14px',
          borderRadius: 8,
          background: `${color}0D`,
          borderLeft: `2px solid ${color}`,
          fontFamily: 'monospace',
          fontSize: 13,
          color: '#e2e8f0',
          lineHeight: 1.5,
          maxWidth: '85%',
        }}
      >
        {isNew ? <StreamText text={msg.content} /> : msg.content}
      </div>
    </div>
  )
}

// ── MAIN COUNCIL VIEW ───────────────────────────────────────
export default function CouncilView() {
  const [messages, setMessages] = useState<any[]>([])
  const [agentStatus, setAgentStatus] = useState<any[]>([])
  const [inputText, setInputText] = useState('')
  const [councilTopic, setCouncilTopic] = useState('')
  const [councilActive, setCouncilActive] = useState(false)
  const [topicInput, setTopicInput] = useState('')
  const [showTopicInput, setShowTopicInput] = useState(false)
  const [sessionStart, setSessionStart] = useState<number | null>(null)
  const [elapsed, setElapsed] = useState('00:00')
  const [newMsgIds, setNewMsgIds] = useState<Set<string>>(new Set())
  const seenIdsRef = useRef<Set<string>>(new Set())
  const scrollRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // ── FETCH HISTORY ─────────────────────────────────────────
  const fetchHistory = useCallback(async () => {
    try {
      const res = await fetch(getApiBase() + '/api/bus/history?limit=50', { headers: apiHeaders() })
      if (!res.ok) return
      const data = await res.json()
      const msgs = Array.isArray(data) ? data : data.messages || []
      const incoming = msgs.sort((a: any, b: any) =>
        new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
      )

      const freshIds = new Set<string>()
      for (const m of incoming) {
        if (!seenIdsRef.current.has(m.id)) {
          freshIds.add(m.id)
          seenIdsRef.current.add(m.id)
        }
      }

      if (freshIds.size > 0) {
        setNewMsgIds(freshIds)
        setTimeout(() => setNewMsgIds(new Set()), 3000)
      }

      setMessages(incoming)
    } catch {}
  }, [])

  // ── FETCH STATUS ──────────────────────────────────────────
  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(getApiBase() + '/api/agents/status', { headers: apiHeaders() })
      if (!res.ok) return
      const data = await res.json()
      setAgentStatus(data.agents || [])
    } catch {}
  }, [])

  // ── POLLING ───────────────────────────────────────────────
  useEffect(() => {
    fetchHistory()
    fetchStatus()
    const histInterval = setInterval(fetchHistory, 3000)
    const statInterval = setInterval(fetchStatus, 2000)
    return () => {
      clearInterval(histInterval)
      clearInterval(statInterval)
    }
  }, [fetchHistory, fetchStatus])

  // ── AUTO-SCROLL ───────────────────────────────────────────
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages, agentStatus])

  // ── ELAPSED TIMER ─────────────────────────────────────────
  useEffect(() => {
    if (!sessionStart) return
    const iv = setInterval(() => {
      const diff = Math.floor((Date.now() - sessionStart) / 1000)
      const m = String(Math.floor(diff / 60)).padStart(2, '0')
      const s = String(diff % 60).padStart(2, '0')
      setElapsed(`${m}:${s}`)
    }, 1000)
    return () => clearInterval(iv)
  }, [sessionStart])

  // ── SEND MESSAGE ──────────────────────────────────────────
  const sendMessage = async () => {
    const text = inputText.trim()
    if (!text) return

    let target = 'ALL'
    for (const name of AGENT_NAMES) {
      if (text.toUpperCase().startsWith(name + ' ') || text.toUpperCase().startsWith(name + ',') || text.toUpperCase() === name) {
        target = name
        break
      }
    }

    try {
      await fetch(getApiBase() + '/api/bus/publish', {
        method: 'POST',
        headers: apiHeaders(),
        body: JSON.stringify({ content: text, to: target }),
      })
    } catch {}

    setInputText('')
    setTimeout(fetchHistory, 500)
  }

  // ── TRIGGER AGENT ─────────────────────────────────────────
  const triggerAgent = async (name: string) => {
    try {
      await fetch(`${getApiBase()}/api/agents/${name}/trigger`, {
        method: 'POST',
        headers: apiHeaders(),
      })
    } catch {}
    setTimeout(fetchStatus, 500)
  }

  // ── CONVENE COUNCIL ───────────────────────────────────────
  const conveneCouncil = async () => {
    if (!topicInput.trim()) return
    try {
      await fetch(getApiBase() + '/api/council/convene', {
        method: 'POST',
        headers: apiHeaders(),
        body: JSON.stringify({ topic: topicInput.trim() }),
      })
      setCouncilTopic(topicInput.trim())
      setCouncilActive(true)
      setSessionStart(Date.now())
      setShowTopicInput(false)
      setTopicInput('')
    } catch {}
  }

  // ── CLOSE COUNCIL ─────────────────────────────────────────
  const closeCouncil = async () => {
    try {
      await fetch(getApiBase() + '/api/council/close', {
        method: 'POST',
        headers: apiHeaders(),
      })
      setCouncilActive(false)
      setSessionStart(null)
    } catch {}
  }

  // ── AGENT STATUS HELPERS ──────────────────────────────────
  const getAgentInfo = (name: string) => {
    return agentStatus.find((a: any) => a.name === name) || {}
  }

  const thinkingAgents = AGENTS.filter(a => getAgentInfo(a.name).is_thinking)

  // ── STYLES ────────────────────────────────────────────────
  const glassPanel = {
    backdropFilter: 'blur(16px)',
    WebkitBackdropFilter: 'blur(16px)',
    background: 'rgba(8, 12, 20, 0.7)',
    border: '1px solid rgba(255, 255, 255, 0.06)',
    borderRadius: 12,
  }

  return (
    <div
      style={{
        position: 'relative',
        width: '100%',
        height: '100%',
        background: '#080c14',
        fontFamily: '"SF Mono", "Fira Code", "Cascadia Code", monospace',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}
    >
      {/* KEYFRAMES */}
      <style>{`
        @keyframes councilPulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.4; transform: scale(0.85); }
        }
        @keyframes councilSlideIn {
          from { opacity: 0; transform: translateY(12px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes councilFade {
          from { opacity: 0; }
          to { opacity: 1; }
        }
      `}</style>

      <ParticleCanvas />

      {/* COUNCIL SESSION HEADER */}
      {councilActive && (
        <div
          style={{
            position: 'relative',
            zIndex: 2,
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            padding: '10px 20px',
            background: 'rgba(6, 182, 212, 0.08)',
            borderBottom: '1px solid rgba(6, 182, 212, 0.2)',
            fontFamily: 'monospace',
            animation: 'councilFade 0.5s ease-out',
          }}
        >
          <span style={{ color: '#06b6d4', fontSize: 16 }}>◈</span>
          <span style={{ color: '#06b6d4', fontSize: 12, fontWeight: 700, letterSpacing: 2 }}>
            COUNCIL IN SESSION
          </span>
          <span style={{ color: '#4b5563', fontSize: 12 }}>—</span>
          <span style={{ color: '#9ca3af', fontSize: 12 }}>TOPIC:</span>
          <span style={{ color: '#e2e8f0', fontSize: 12, fontWeight: 600 }}>{councilTopic}</span>
          <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 8 }}>
            {AGENTS.map(a => (
              <span key={a.name} title={a.name}>
                {getAgentInfo(a.name).is_thinking ? (
                  <PulsingDot color={a.color} size={6} />
                ) : (
                  <span
                    style={{
                      display: 'inline-block',
                      width: 6,
                      height: 6,
                      borderRadius: '50%',
                      backgroundColor: a.color,
                      opacity: 0.4,
                    }}
                  />
                )}
              </span>
            ))}
            <span style={{ color: '#06b6d4', fontSize: 12, marginLeft: 8, fontVariantNumeric: 'tabular-nums' }}>
              {elapsed}
            </span>
          </div>
        </div>
      )}

      {/* MAIN CONTENT — THREE PANELS */}
      <div
        style={{
          position: 'relative',
          zIndex: 1,
          flex: 1,
          display: 'flex',
          gap: 12,
          padding: 12,
          overflow: 'hidden',
        }}
      >
        {/* LEFT — AGENT STATUS (18%) */}
        <div
          style={{
            ...glassPanel,
            width: '18%',
            padding: 16,
            display: 'flex',
            flexDirection: 'column',
            gap: 4,
            overflowY: 'auto',
            flexShrink: 0,
          }}
        >
          <div
            style={{
              fontSize: 10,
              color: '#6b7280',
              letterSpacing: 2,
              marginBottom: 12,
              textTransform: 'uppercase',
            }}
          >
            Agents
          </div>
          {AGENTS.map(agent => {
            const info = getAgentInfo(agent.name)
            return (
              <div
                key={agent.name}
                onClick={() => triggerAgent(agent.name)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '10px 8px',
                  borderRadius: 8,
                  cursor: 'pointer',
                  transition: 'background 0.15s',
                }}
                onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.04)')}
                onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
              >
                {info.is_thinking ? (
                  <PulsingDot color='#22c55e' size={8} />
                ) : (
                  <span
                    style={{
                      display: 'inline-block',
                      width: 8,
                      height: 8,
                      borderRadius: '50%',
                      backgroundColor: agent.color,
                      opacity: 0.5,
                      flexShrink: 0,
                    }}
                  />
                )}
                <span style={{ color: agent.color, fontSize: 14 }}>{agent.icon}</span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: '#e2e8f0' }}>{agent.name}</div>
                  <div style={{ fontSize: 10, color: '#6b7280', marginTop: 1 }}>
                    {info.is_thinking
                      ? 'thinking...'
                      : info.last_spoke
                      ? formatRelative(info.last_spoke)
                      : agent.role}
                  </div>
                </div>
              </div>
            )
          })}
        </div>

        {/* CENTER — CONVERSATION (58%) */}
        <div
          style={{
            ...glassPanel,
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden',
          }}
        >
          <div
            ref={scrollRef}
            style={{
              flex: 1,
              overflowY: 'auto',
              padding: '16px 20px',
            }}
          >
            {messages.length === 0 && thinkingAgents.length === 0 ? (
              <div
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  height: '100%',
                  gap: 8,
                  animation: 'councilFade 1s ease-out',
                }}
              >
                <span style={{ fontSize: 32, color: '#06b6d4', marginBottom: 8 }}>◈</span>
                <span style={{ fontSize: 14, color: '#e2e8f0', fontWeight: 600, letterSpacing: 2 }}>
                  COUNCIL READY
                </span>
                <span style={{ fontSize: 12, color: '#6b7280' }}>5 agents standing by</span>
                <span style={{ fontSize: 11, color: '#4b5563', marginTop: 4 }}>
                  Speak or convene a council session
                </span>
              </div>
            ) : (
              <>
                {messages.map(msg => (
                  <MessageBubble
                    key={msg.id}
                    msg={msg}
                    isNew={newMsgIds.has(msg.id)}
                    allMessages={messages}
                  />
                ))}
                {thinkingAgents.map(a => (
                  <ThinkingIndicator key={a.name + '-thinking'} agent={a} />
                ))}
              </>
            )}
          </div>
        </div>

        {/* RIGHT — COUNCIL CONTROLS (24%) */}
        <div
          style={{
            ...glassPanel,
            width: '24%',
            padding: 16,
            display: 'flex',
            flexDirection: 'column',
            gap: 16,
            overflowY: 'auto',
            flexShrink: 0,
          }}
        >
          <div
            style={{
              fontSize: 10,
              color: '#6b7280',
              letterSpacing: 2,
              textTransform: 'uppercase',
            }}
          >
            Council Controls
          </div>

          {/* CONVENE / CLOSE */}
          {!councilActive ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {showTopicInput ? (
                <>
                  <input
                    value={topicInput}
                    onChange={e => setTopicInput(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && conveneCouncil()}
                    placeholder="Enter council topic..."
                    style={{
                      background: 'rgba(255,255,255,0.05)',
                      border: '1px solid rgba(6, 182, 212, 0.3)',
                      borderRadius: 6,
                      padding: '8px 12px',
                      color: '#e2e8f0',
                      fontFamily: 'monospace',
                      fontSize: 12,
                      outline: 'none',
                    }}
                    autoFocus
                  />
                  <div style={{ display: 'flex', gap: 8 }}>
                    <button
                      onClick={conveneCouncil}
                      style={{
                        flex: 1,
                        padding: '8px 0',
                        background: 'rgba(6, 182, 212, 0.15)',
                        border: '1px solid rgba(6, 182, 212, 0.4)',
                        borderRadius: 6,
                        color: '#06b6d4',
                        fontFamily: 'monospace',
                        fontSize: 11,
                        fontWeight: 700,
                        cursor: 'pointer',
                        letterSpacing: 1,
                      }}
                    >
                      BEGIN
                    </button>
                    <button
                      onClick={() => { setShowTopicInput(false); setTopicInput('') }}
                      style={{
                        padding: '8px 12px',
                        background: 'rgba(255,255,255,0.05)',
                        border: '1px solid rgba(255,255,255,0.1)',
                        borderRadius: 6,
                        color: '#6b7280',
                        fontFamily: 'monospace',
                        fontSize: 11,
                        cursor: 'pointer',
                      }}
                    >
                      CANCEL
                    </button>
                  </div>
                </>
              ) : (
                <button
                  onClick={() => setShowTopicInput(true)}
                  style={{
                    padding: '12px 0',
                    background: 'rgba(6, 182, 212, 0.1)',
                    border: '1px solid rgba(6, 182, 212, 0.3)',
                    borderRadius: 8,
                    color: '#06b6d4',
                    fontFamily: 'monospace',
                    fontSize: 12,
                    fontWeight: 700,
                    cursor: 'pointer',
                    letterSpacing: 2,
                    transition: 'all 0.15s',
                  }}
                  onMouseEnter={e => {
                    e.currentTarget.style.background = 'rgba(6, 182, 212, 0.2)'
                    e.currentTarget.style.borderColor = 'rgba(6, 182, 212, 0.5)'
                  }}
                  onMouseLeave={e => {
                    e.currentTarget.style.background = 'rgba(6, 182, 212, 0.1)'
                    e.currentTarget.style.borderColor = 'rgba(6, 182, 212, 0.3)'
                  }}
                >
                  ◈ CONVENE COUNCIL
                </button>
              )}
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div style={{ padding: 12, background: 'rgba(6, 182, 212, 0.06)', borderRadius: 8, border: '1px solid rgba(6, 182, 212, 0.15)' }}>
                <div style={{ fontSize: 10, color: '#6b7280', letterSpacing: 1, marginBottom: 6 }}>ACTIVE SESSION</div>
                <div style={{ fontSize: 12, color: '#e2e8f0', fontWeight: 600, marginBottom: 4 }}>{councilTopic}</div>
                <div style={{ fontSize: 11, color: '#06b6d4', fontVariantNumeric: 'tabular-nums' }}>Duration: {elapsed}</div>
                <div style={{ display: 'flex', gap: 4, marginTop: 8, flexWrap: 'wrap' }}>
                  {AGENTS.map(a => (
                    <span
                      key={a.name}
                      style={{
                        fontSize: 10,
                        padding: '2px 8px',
                        borderRadius: 4,
                        background: `${a.color}15`,
                        color: a.color,
                        border: `1px solid ${a.color}30`,
                      }}
                    >
                      {a.icon} {a.name}
                    </span>
                  ))}
                </div>
              </div>
              <button
                onClick={closeCouncil}
                style={{
                  padding: '10px 0',
                  background: 'rgba(239, 68, 68, 0.1)',
                  border: '1px solid rgba(239, 68, 68, 0.3)',
                  borderRadius: 8,
                  color: '#ef4444',
                  fontFamily: 'monospace',
                  fontSize: 11,
                  fontWeight: 700,
                  cursor: 'pointer',
                  letterSpacing: 2,
                }}
                onMouseEnter={e => {
                  e.currentTarget.style.background = 'rgba(239, 68, 68, 0.2)'
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.background = 'rgba(239, 68, 68, 0.1)'
                }}
              >
                CLOSE COUNCIL
              </button>
            </div>
          )}

          {/* DIVIDER */}
          <div style={{ height: 1, background: 'rgba(255,255,255,0.06)' }} />

          {/* TRIGGER AGENTS */}
          <div>
            <div style={{ fontSize: 10, color: '#6b7280', letterSpacing: 2, marginBottom: 10, textTransform: 'uppercase' }}>
              Trigger Agent
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {AGENTS.map(agent => {
                const info = getAgentInfo(agent.name)
                return (
                  <button
                    key={agent.name}
                    onClick={() => triggerAgent(agent.name)}
                    disabled={info.is_thinking}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 8,
                      padding: '8px 12px',
                      background: info.is_thinking ? `${agent.color}10` : 'rgba(255,255,255,0.03)',
                      border: `1px solid ${info.is_thinking ? agent.color + '40' : 'rgba(255,255,255,0.06)'}`,
                      borderRadius: 6,
                      color: agent.color,
                      fontFamily: 'monospace',
                      fontSize: 11,
                      cursor: info.is_thinking ? 'default' : 'pointer',
                      textAlign: 'left',
                      opacity: info.is_thinking ? 0.6 : 1,
                      transition: 'all 0.15s',
                    }}
                    onMouseEnter={e => {
                      if (!info.is_thinking) e.currentTarget.style.background = `${agent.color}15`
                    }}
                    onMouseLeave={e => {
                      if (!info.is_thinking) e.currentTarget.style.background = 'rgba(255,255,255,0.03)'
                    }}
                  >
                    <span style={{ fontSize: 14 }}>{agent.icon}</span>
                    <span style={{ fontWeight: 600 }}>{agent.name}</span>
                    <span style={{ color: '#4b5563', fontSize: 10, marginLeft: 'auto' }}>
                      {info.is_thinking ? 'thinking...' : agent.role}
                    </span>
                  </button>
                )
              })}
            </div>
          </div>
        </div>
      </div>

      {/* BOTTOM — COMMAND BAR */}
      <div
        style={{
          position: 'relative',
          zIndex: 2,
          padding: '12px 16px',
          borderTop: '1px solid rgba(255,255,255,0.06)',
        }}
      >
        <div
          style={{
            ...glassPanel,
            display: 'flex',
            alignItems: 'center',
            padding: '4px 4px 4px 16px',
          }}
        >
          <span style={{ color: '#06b6d4', fontSize: 14, marginRight: 8, fontWeight: 700 }}>&gt;</span>
          <input
            ref={inputRef}
            value={inputText}
            onChange={e => setInputText(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                sendMessage()
              }
            }}
            placeholder="speak to all agents, or address one: NOUS / AXIOM / VECTOR / CIPHER / ECHO"
            style={{
              flex: 1,
              background: 'transparent',
              border: 'none',
              outline: 'none',
              color: '#e2e8f0',
              fontFamily: 'monospace',
              fontSize: 13,
              padding: '10px 0',
            }}
          />
          <button
            onClick={sendMessage}
            style={{
              padding: '8px 16px',
              background: inputText.trim() ? 'rgba(6, 182, 212, 0.15)' : 'transparent',
              border: '1px solid',
              borderColor: inputText.trim() ? 'rgba(6, 182, 212, 0.3)' : 'rgba(255,255,255,0.06)',
              borderRadius: 8,
              color: inputText.trim() ? '#06b6d4' : '#4b5563',
              fontFamily: 'monospace',
              fontSize: 11,
              fontWeight: 700,
              cursor: inputText.trim() ? 'pointer' : 'default',
              letterSpacing: 1,
              transition: 'all 0.15s',
            }}
          >
            SEND
          </button>
        </div>
      </div>
    </div>
  )
}
