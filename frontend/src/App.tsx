import { useEffect, useState, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useStore, setApiKey } from './store'
import NousAgent from './NousAgent'

// ── ICONS (inline SVG to avoid dep issues) ──────────────────
const Icon = ({ d, className = '' }: { d: string; className?: string }) => (
  <svg className={`w-4 h-4 ${className}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
    <path strokeLinecap="round" strokeLinejoin="round" d={d} />
  </svg>
)
const icons = {
  brain: 'M12 2a7 7 0 0 0-7 7c0 2.38 1.19 4.47 3 5.74V17a2 2 0 0 0 2 2h4a2 2 0 0 0 2-2v-2.26c1.81-1.27 3-3.36 3-5.74a7 7 0 0 0-7-7z M9 21h6',
  zap: 'M13 2L3 14h9l-1 8 10-12h-9l1-8z',
  folder: 'M3 7v10a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-6l-2-2H5a2 2 0 0 0-2 2z',
  flask: 'M9 3h6 M12 3v7.4a2 2 0 0 0 .3 1l4.5 6.7a1 1 0 0 1-.8 1.4H8a1 1 0 0 1-.9-1.4l4.6-6.7a2 2 0 0 0 .3-1V3',
  cpu: 'M9 3h6v6H9zM4 9h4M16 9h4M4 15h4M16 15h4M9 21h6v-6H9z',
  code: 'M16 18l6-6-6-6M8 6l-6 6 6 6',
  book: 'M4 19.5A2.5 2.5 0 0 1 6.5 17H20 M4 4v16M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z',
  user: 'M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2 M12 3a4 4 0 1 0 0 8 4 4 0 0 0 0-8z',
  users: 'M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2 M23 21v-2a4 4 0 0 0-3-3.87 M9 3a4 4 0 1 0 0 8 4 4 0 0 0 0-8z M16 3.13a4 4 0 0 1 0 7.75',
  pen: 'M12 20h9M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z',
  heart: 'M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z',
  plus: 'M12 5v14M5 12h14',
  check: 'M20 6L9 17l-5-5',
  clock: 'M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20z M12 6v6l4 2',
  search: 'M21 21l-6-6m2-5a7 7 0 1 0-14 0 7 7 0 0 0 14 0z',
  send: 'M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z',
  x: 'M18 6L6 18M6 6l12 12',
  star: 'M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z',
  target: 'M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20z M12 6a6 6 0 1 0 0 12 6 6 0 0 0 0-12z M12 10a2 2 0 1 0 0 4 2 2 0 0 0 0-4z',
  bulb: 'M9 21h6M12 2a7 7 0 0 0-4 12.7V17h8v-2.3A7 7 0 0 0 12 2z',
  moon: 'M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z',
  activity: 'M22 12h-4l-3 9L9 3l-3 9H2',
  msg: 'M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z',
  file: 'M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z M14 2v6h6',
  dollar: 'M12 1v22M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6',
  phone: 'M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72',
  play: 'M5 3l14 9-14 9V3z',
  pause: 'M6 4h4v16H6zM14 4h4v16h-4z',
}

const VIEWS = [
  { key: 'nucleus', label: 'NUCLEUS', icon: 'brain' },
  { key: 'nous', label: 'NOUS AGENT', icon: 'brain' },
  { key: 'intelligence', label: 'INTELLIGENCE', icon: 'zap' },
  { key: 'projects', label: 'PROJECTS', icon: 'folder' },
  { key: 'egc', label: 'EGC RESEARCH', icon: 'flask' },
  { key: 'aronson', label: 'ARONSON PREP', icon: 'phone' },
  { key: 'lolm', label: 'LOLM', icon: 'cpu' },
  { key: 'codey', label: 'CODEY', icon: 'code' },
  { key: 'knowledge', label: 'KNOWLEDGE', icon: 'book' },
  { key: 'personal', label: 'PERSONAL OS', icon: 'user' },
  { key: 'network', label: 'NETWORK', icon: 'users' },
  { key: 'studio', label: 'STUDIO', icon: 'pen' },
  { key: 'health', label: 'WELLBEING', icon: 'heart' },
]

// ── REUSABLE COMPONENTS ──────────────────────────────────────
function Card({ children, className = '', onClick }: { children: React.ReactNode; className?: string; onClick?: () => void }) {
  return (
    <div className={`bg-surface border border-border rounded-lg p-5 ${className}`} onClick={onClick}>
      {children}
    </div>
  )
}

function Stat({ label, value, sub, color = 'text-accent-bright' }: { label: string; value: string | number; sub?: string; color?: string }) {
  return (
    <div>
      <div className="text-[10px] text-muted uppercase tracking-widest mb-1">{label}</div>
      <div className={`text-2xl font-bold ${color}`}>{value}</div>
      {sub && <div className="text-xs text-muted mt-1">{sub}</div>}
    </div>
  )
}

function Badge({ text, color = 'bg-[#2563eb]/20 text-[#60a5fa]' }: { text: string; color?: string }) {
  return <span className={`text-[10px] px-2 py-0.5 rounded-full ${color} uppercase tracking-wider`}>{text}</span>
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <h2 className="text-sm text-muted uppercase tracking-[0.2em] mb-4">{children}</h2>
}

function HealthBar({ value, max = 10 }: { value: number; max?: number }) {
  const pct = (value / max) * 100
  const color = pct >= 70 ? 'bg-[#10b981]' : pct >= 40 ? 'bg-[#f59e0b]' : 'bg-[#ef4444]'
  return (
    <div className="w-full h-1.5 bg-[#1e2d40] rounded-full overflow-hidden">
      <div className={`h-full ${color} rounded-full transition-all`} style={{ width: `${pct}%` }} />
    </div>
  )
}

// ── AUTH SCREEN ──────────────────────────────────────────────
function AuthScreen() {
  const [key, setKey] = useState('')
  const { setAuthenticated } = useStore()

  const submit = () => {
    if (key.trim()) {
      setApiKey(key.trim())
      setAuthenticated(true)
    }
  }

  return (
    <div className="min-h-screen bg-[#0a0e1a] flex items-center justify-center">
      <div className="bg-[#111827] border border-[#1e2d40] rounded-xl p-8 w-[400px]">
        <div className="text-[10px] text-[#64748b] tracking-[0.3em] uppercase mb-1">QIRA COMMAND CENTER</div>
        <div className="text-xl text-[#60a5fa] font-semibold mb-6">Authentication Required</div>
        <div className="text-xs text-[#64748b] mb-4">Enter the API key from ~/qira/command_center/.env</div>
        <input value={key} onChange={e => setKey(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && submit()}
          type="password" placeholder="QIRA_API_KEY"
          className="w-full bg-[#0a0e1a] border border-[#1e2d40] rounded-lg px-4 py-3 text-sm text-[#e2e8f0] outline-none focus:border-[#2563eb] mb-4" />
        <button onClick={submit}
          className="w-full bg-[#2563eb] text-white py-3 rounded-lg text-sm hover:bg-[#2563eb]/80 transition-colors">
          Enter Command Center
        </button>
      </div>
    </div>
  )
}

// ── NUCLEUS VIEW ─────────────────────────────────────────────
function NucleusView() {
  const { nucleus, fetchNucleus, egc, fetchEGC, projects, fetchProjects, tasks, fetchTasks,
          links, fetchLinks, linkChecks, fetchLinkChecks, githubRepos, fetchGithubRepos,
          liveData, fetchLiveData } = useStore()

  useEffect(() => {
    fetchNucleus(); fetchEGC(); fetchProjects(); fetchTasks()
    fetchLinks(); fetchLinkChecks(); fetchGithubRepos(); fetchLiveData()
  }, [])

  const pendingTasks = tasks.filter((t: any) => t.status === 'pending')
  const inProgress = tasks.filter((t: any) => t.status === 'in_progress')

  // Group links by project
  const linksByProject: Record<string, any[]> = {}
  links.forEach((l: any) => {
    if (!linksByProject[l.project]) linksByProject[l.project] = []
    linksByProject[l.project].push(l)
  })

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-xs text-[#64748b] uppercase tracking-[0.3em]">QIRA COMMAND CENTER</div>
          <h1 className="text-3xl font-bold text-[#e2e8f0] mt-1">
            Good {new Date().getHours() < 12 ? 'morning' : new Date().getHours() < 17 ? 'afternoon' : 'evening'}, Bryan
          </h1>
        </div>
        <div className="text-right text-xs text-[#64748b]">
          <div>{new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}</div>
          <div className="text-[#10b981] mt-1">Systems operational</div>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <Card><Stat label="Active Projects" value={projects.filter((p: any) => p.status === 'active').length} /></Card>
        <Card><Stat label="Open Tasks" value={nucleus?.active_tasks ?? pendingTasks.length} /></Card>
        <Card><Stat label="Done Today" value={nucleus?.completed_today ?? 0} color="text-[#10b981]" /></Card>
        <Card><Stat label="EGC N" value={liveData?.egc_n ?? egc?.n ?? 40} color="text-[#f59e0b]" /></Card>
        <Card><Stat label="Pearson r" value={egc?.pearson_r?.toFixed(3) ?? '0.311'} /></Card>
        <Card><Stat label="Aronson" value="PENDING" color="text-[#ef4444]" /></Card>
      </div>

      {/* Live Site Status */}
      <SectionTitle>Live Sites & Services</SectionTitle>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
        {liveData && <>
          <a href="https://theartofsound.github.io/egcstudy/" target="_blank" rel="noopener noreferrer">
            <Card className="!p-3 hover:border-[#2563eb] cursor-pointer">
              <div className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${liveData.egc_study_status === 200 ? 'bg-[#10b981]' : 'bg-[#ef4444]'}`} />
                <span className="text-xs">EGC Study</span>
                <span className="text-[10px] text-[#10b981] ml-auto">N={liveData.egc_n}</span>
              </div>
            </Card>
          </a>
          <a href="https://theartofsound.github.io/thegate/" target="_blank" rel="noopener noreferrer">
            <Card className="!p-3 hover:border-[#2563eb] cursor-pointer">
              <div className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${liveData.thegate_status === 200 ? 'bg-[#10b981]' : 'bg-[#ef4444]'}`} />
                <span className="text-xs">The Gate</span>
              </div>
            </Card>
          </a>
          <a href="https://theartofsound.github.io/egcrate/" target="_blank" rel="noopener noreferrer">
            <Card className="!p-3 hover:border-[#2563eb] cursor-pointer">
              <div className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${liveData.egcrate_status === 200 ? 'bg-[#10b981]' : 'bg-[#ef4444]'}`} />
                <span className="text-xs">EGC Rater</span>
              </div>
            </Card>
          </a>
          <a href="https://theartofsound.github.io/portfolio/" target="_blank" rel="noopener noreferrer">
            <Card className="!p-3 hover:border-[#2563eb] cursor-pointer">
              <div className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${liveData.portfolio_status === 200 ? 'bg-[#10b981]' : 'bg-[#ef4444]'}`} />
                <span className="text-xs">Portfolio</span>
              </div>
            </Card>
          </a>
          <a href="https://theartofsound.github.io/codey/" target="_blank" rel="noopener noreferrer">
            <Card className="!p-3 hover:border-[#2563eb] cursor-pointer">
              <div className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${liveData.codey_landing_status === 200 ? 'bg-[#10b981]' : 'bg-[#ef4444]'}`} />
                <span className="text-xs">Codey Landing</span>
              </div>
            </Card>
          </a>
          <a href="https://zenodo.org/records/19242315" target="_blank" rel="noopener noreferrer">
            <Card className="!p-3 hover:border-[#2563eb] cursor-pointer">
              <div className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${liveData.preprint_status === 200 ? 'bg-[#10b981]' : liveData.preprint_status > 0 ? 'bg-[#f59e0b]' : 'bg-[#ef4444]'}`} />
                <span className="text-xs">Preprint (Zenodo)</span>
              </div>
            </Card>
          </a>
          <Card className="!p-3">
            <div className="flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full ${liveData.nfet_alive ? 'bg-[#10b981]' : 'bg-[#64748b]'}`} />
              <span className="text-xs">NFET Local</span>
              <span className="text-[10px] text-[#64748b] ml-auto">{liveData.nfet_alive ? 'RUNNING' : 'offline'}</span>
            </div>
          </Card>
        </>}
        {linkChecks.map((c: any) => (
          <Card key={c.id} className="!p-3">
            <div className="flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full ${c.alive ? 'bg-[#10b981]' : 'bg-[#ef4444]'}`} />
              <span className="text-xs">{c.name}</span>
              <span className="text-[10px] text-[#64748b] ml-auto">:{c.check_port}</span>
            </div>
          </Card>
        ))}
      </div>

      {/* GitHub Recent Activity */}
      {liveData?.github_recent?.length > 0 && (
        <>
          <SectionTitle>GitHub Activity</SectionTitle>
          <Card className="!p-4">
            <div className="space-y-2">
              {liveData.github_recent.map((e: any, i: number) => (
                <div key={i} className="flex items-center gap-3 text-xs">
                  <span className={`w-1.5 h-1.5 rounded-full ${e.type === 'PushEvent' ? 'bg-[#10b981]' : 'bg-[#60a5fa]'}`} />
                  <span className="text-[#64748b]">{e.type.replace('Event', '')}</span>
                  <span className="text-[#e2e8f0]">{e.repo.replace('TheArtOfSound/', '')}</span>
                  <span className="text-[#64748b] ml-auto">{new Date(e.created_at).toLocaleTimeString()}</span>
                </div>
              ))}
            </div>
          </Card>
        </>
      )}

      {/* Project Health with Links */}
      <SectionTitle>Project Health</SectionTitle>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {projects.map((p: any) => {
          const pLinks = linksByProject[p.name] || linksByProject[p.id?.toUpperCase()] || []
          return (
            <Card key={p.id} className="hover:border-[#2563eb] transition-colors">
              <div className="flex items-center justify-between mb-2">
                <span className="font-semibold text-sm">{p.name}</span>
                <Badge text={p.status} color={p.status === 'active' ? 'bg-[#10b981]/20 text-[#10b981]' : 'bg-[#64748b]/20 text-[#64748b]'} />
              </div>
              <div className="text-xs text-[#64748b] mb-2 line-clamp-2">{p.description}</div>
              <HealthBar value={p.health} />
              <div className="text-[10px] text-[#64748b] mt-1 mb-2">Health: {p.health}/10</div>
              {pLinks.length > 0 && (
                <div className="border-t border-[#1e2d40] pt-2 mt-2 space-y-1">
                  {pLinks.slice(0, 4).map((l: any) => (
                    <a key={l.id} href={l.url} target="_blank" rel="noopener noreferrer"
                      className="flex items-center gap-2 text-[10px] text-[#60a5fa] hover:text-[#2563eb] transition-colors">
                      <span className="text-[#64748b]">&rarr;</span> {l.name}
                    </a>
                  ))}
                </div>
              )}
            </Card>
          )
        })}
      </div>

      {/* EGC Live */}
      {egc && (
        <>
          <SectionTitle>EGC Research — Live</SectionTitle>
          <Card>
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
              <Stat label="Subjects" value={`N=${egc.n}`} />
              <Stat label="Compressors" value={`${egc.compressors}%`} color="text-[#10b981]" />
              <Stat label="Expanders" value={`${egc.expanders}%`} color="text-[#60a5fa]" />
              <Stat label="Suppressors" value={`${egc.suppressors}%`} color="text-[#f59e0b]" />
              <Stat label="Pearson r" value={egc.pearson_r?.toFixed(3)} />
              <Stat label="Comfort Gap" value={`${egc.comfort_gap}pts`} />
              <Stat label="Zero-r Supp." value={egc.zero_r_suppressors ?? 6} color="text-[#ef4444]" />
            </div>
          </Card>
        </>
      )}

      {/* GitHub Repos */}
      {githubRepos.length > 0 && (
        <>
          <SectionTitle>GitHub Repositories ({githubRepos.length})</SectionTitle>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
            {githubRepos.map((r: any) => (
              <a key={r.id} href={`https://github.com/${r.full_name}`} target="_blank" rel="noopener noreferrer">
                <Card className="!p-3 hover:border-[#2563eb] transition-colors cursor-pointer">
                  <div className="text-xs font-semibold">{r.name}</div>
                  <div className="flex items-center gap-2 mt-1">
                    <Badge text={r.project || 'Unknown'} />
                    {r.language && <span className="text-[10px] text-[#64748b]">{r.language}</span>}
                  </div>
                </Card>
              </a>
            ))}
          </div>
        </>
      )}

      {/* Quick Links */}
      <SectionTitle>Quick Links</SectionTitle>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {Object.entries(linksByProject).map(([project, pLinks]) => (
          <Card key={project} className="!p-4">
            <div className="text-xs text-[#60a5fa] uppercase tracking-wider mb-2">{project}</div>
            <div className="space-y-1">
              {(pLinks as any[]).map((l: any) => (
                <a key={l.id} href={l.url} target="_blank" rel="noopener noreferrer"
                  className="flex items-center justify-between text-xs hover:text-[#60a5fa] transition-colors group">
                  <span>{l.name}</span>
                  <span className="text-[10px] text-[#64748b] group-hover:text-[#60a5fa] truncate max-w-[200px]">{l.url.replace('https://', '').replace('http://', '')}</span>
                </a>
              ))}
            </div>
          </Card>
        ))}
      </div>

      {/* Active Work */}
      <SectionTitle>Active Work</SectionTitle>
      <Card>
        {inProgress.length === 0 && pendingTasks.length === 0 ? (
          <div className="text-[#64748b] text-sm">No tasks yet. Add tasks from the Projects view.</div>
        ) : (
          <div className="space-y-2">
            {inProgress.map((t: any) => (
              <div key={t.id} className="flex items-center gap-3 text-sm">
                <Icon d={icons.activity} className="text-[#60a5fa]" />
                <span className="text-[#60a5fa]">{t.title}</span>
                <Badge text="in progress" />
              </div>
            ))}
            {pendingTasks.slice(0, 8).map((t: any) => (
              <div key={t.id} className="flex items-center gap-3 text-sm text-[#64748b]">
                <Icon d={icons.clock} />
                <span>{t.title}</span>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  )
}

// ── INTELLIGENCE VIEW ────────────────────────────────────────
function IntelligenceView() {
  const { chatResponse, chatLoading, sendChat } = useStore()
  const [msg, setMsg] = useState('')
  const [history, setHistory] = useState<{ role: string; text: string }[]>(() => {
    const saved = localStorage.getItem('nous_chat_history')
    return saved ? JSON.parse(saved) : []
  })
  const [mode, setMode] = useState('general')
  const endRef = useRef<HTMLDivElement>(null)
  const modes = ['general', 'research', 'code', 'writing', 'analysis', 'brainstorm']

  useEffect(() => { localStorage.setItem('nous_chat_history', JSON.stringify(history.slice(-100))) }, [history])
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [history])
  useEffect(() => {
    if (chatResponse && !chatLoading) setHistory(h => [...h, { role: 'assistant', text: chatResponse }])
  }, [chatResponse, chatLoading])

  const send = async () => {
    if (!msg.trim()) return
    setHistory(h => [...h, { role: 'user', text: msg }])
    const m = msg; setMsg('')
    await sendChat(m, mode)
  }

  return (
    <div className="flex flex-col h-[calc(100vh-64px)]">
      <div className="flex items-center gap-4 mb-4">
        <SectionTitle>Nous Intelligence</SectionTitle>
        <div className="flex gap-2 ml-auto">
          {modes.map(m => (
            <button key={m} onClick={() => setMode(m)}
              className={`text-[10px] uppercase tracking-wider px-3 py-1 rounded-full border transition-colors ${mode === m ? 'border-[#2563eb] bg-[#2563eb]/20 text-[#60a5fa]' : 'border-[#1e2d40] text-[#64748b] hover:text-[#e2e8f0]'}`}>
              {m}
            </button>
          ))}
        </div>
      </div>
      <Card className="flex-1 overflow-y-auto mb-4">
        {history.length === 0 && (
          <div className="text-[#64748b] text-sm text-center py-20">
            <div className="text-4xl mb-4 opacity-20">&#x2726;</div>
            <div className="text-lg text-[#e2e8f0]/40 mb-2">Nous is ready</div>
            <div>Full context loaded. Ask anything about EGC, LOLM, Codey, NFET, or anything else.</div>
          </div>
        )}
        <div className="space-y-4">
          {history.map((h, i) => (
            <div key={i} className={`flex ${h.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[80%] rounded-lg p-3 text-sm whitespace-pre-wrap ${h.role === 'user' ? 'bg-[#2563eb]/20 text-[#60a5fa]' : 'bg-[#1a2332] text-[#e2e8f0]'}`}>
                {h.text}
              </div>
            </div>
          ))}
          {chatLoading && <div className="flex justify-start"><div className="bg-[#1a2332] rounded-lg p-3 text-sm text-[#64748b] animate-pulse">Thinking...</div></div>}
          <div ref={endRef} />
        </div>
      </Card>
      <div className="flex gap-2">
        <input value={msg} onChange={e => setMsg(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), send())}
          placeholder="Ask Nous anything..."
          className="flex-1 bg-[#111827] border border-[#1e2d40] rounded-lg px-4 py-3 text-sm text-[#e2e8f0] outline-none focus:border-[#2563eb]" />
        <button onClick={send} disabled={chatLoading}
          className="bg-[#2563eb] text-white px-5 py-3 rounded-lg text-sm disabled:opacity-50">
          <Icon d={icons.send} />
        </button>
      </div>
    </div>
  )
}

// ── PROJECTS VIEW ────────────────────────────────────────────
function ProjectsView() {
  const { projects, fetchProjects, tasks, fetchTasks, createTask, updateTask, deleteTask } = useStore()
  const [selected, setSelected] = useState<string | null>(null)
  const [newTask, setNewTask] = useState('')

  useEffect(() => { fetchProjects(); fetchTasks() }, [])
  const projectTasks = selected ? tasks.filter((t: any) => t.project === selected) : tasks

  return (
    <div className="space-y-6">
      <SectionTitle>Projects Hub</SectionTitle>
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="space-y-2">
          <button onClick={() => setSelected(null)}
            className={`w-full text-left text-xs px-3 py-2 rounded ${!selected ? 'bg-[#2563eb]/20 text-[#60a5fa]' : 'text-[#64748b] hover:text-[#e2e8f0]'}`}>
            All Projects
          </button>
          {projects.map((p: any) => (
            <button key={p.id} onClick={() => setSelected(p.id)}
              className={`w-full text-left px-3 py-2 rounded ${selected === p.id ? 'bg-[#2563eb]/20 text-[#60a5fa]' : 'text-[#64748b] hover:text-[#e2e8f0]'}`}>
              <div className="text-xs font-semibold">{p.name}</div>
              <div className="flex items-center gap-2 mt-1">
                <HealthBar value={p.health} /><span className="text-[10px]">{p.health}/10</span>
              </div>
            </button>
          ))}
        </div>
        <div className="lg:col-span-3 space-y-4">
          <div className="flex gap-2">
            <input value={newTask} onChange={e => setNewTask(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && newTask.trim()) { createTask({ title: newTask, project: selected || '', priority: 5 }); setNewTask('') } }}
              placeholder="Add task... (Enter)"
              className="flex-1 bg-[#111827] border border-[#1e2d40] rounded-lg px-4 py-2 text-sm text-[#e2e8f0] outline-none focus:border-[#2563eb]" />
          </div>
          {projectTasks.length === 0 && <div className="text-[#64748b] text-sm">No tasks.</div>}
          <div className="space-y-1">
            {projectTasks.map((t: any) => (
              <div key={t.id} className="flex items-center gap-3 bg-[#111827] border border-[#1e2d40] rounded-lg px-4 py-2.5 group">
                <button onClick={() => updateTask(t.id, { status: t.status === 'completed' ? 'pending' : 'completed' })}
                  className={`w-4 h-4 rounded border flex items-center justify-center ${t.status === 'completed' ? 'bg-[#10b981] border-[#10b981]' : 'border-[#64748b] hover:border-[#2563eb]'}`}>
                  {t.status === 'completed' && <Icon d={icons.check} className="w-3 h-3 text-[#0a0e1a]" />}
                </button>
                <span className={`flex-1 text-sm ${t.status === 'completed' ? 'line-through text-[#64748b]' : ''}`}>{t.title}</span>
                {t.project && <Badge text={t.project} />}
                <button onClick={() => deleteTask(t.id)} className="text-[#64748b] hover:text-[#ef4444] opacity-0 group-hover:opacity-100">
                  <Icon d={icons.x} className="w-3.5 h-3.5" />
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

// ── EGC RESEARCH VIEW ────────────────────────────────────────
function EGCView() {
  const { egc, fetchEGC } = useStore()
  useEffect(() => { fetchEGC() }, [])
  if (!egc) return <div className="text-[#64748b]">Loading EGC data...</div>

  return (
    <div className="space-y-6">
      <SectionTitle>Expression-Gated Consciousness Research</SectionTitle>

      {/* Aronson banner */}
      <Card className="border-[#f59e0b]/30 cursor-pointer hover:border-[#f59e0b]" onClick={() => useStore.getState().setView('aronson')}>
        <div className="flex items-center gap-3">
          <Icon d={icons.star} className="text-[#f59e0b] w-5 h-5" />
          <div className="flex-1">
            <div className="text-sm font-semibold">Aronson Call Prep</div>
            <div className="text-xs text-[#64748b]">Click to open the full prep module with talking points, Q&A, and practice mode</div>
          </div>
          <Badge text="priority" color="bg-[#f59e0b]/20 text-[#f59e0b]" />
          <span className="text-xs text-[#64748b]">&rarr;</span>
        </div>
      </Card>

      {/* Core Equation */}
      <Card className="border-[#2563eb]/30">
        <div className="text-xs text-[#64748b] uppercase tracking-widest mb-2">Core Equation</div>
        <div className="text-lg text-[#60a5fa] font-mono">{'Psi(t) = Phi * g(K(t)) * T(t) * (1 - r(t)) * g(P(t))'}</div>
        <div className="text-xs text-[#64748b] mt-2">where g(K) = 4K(1-K) — Brandyn Leonard's parabolic conviction function</div>
      </Card>

      {/* Emerging Extension */}
      <Card className="border-[#f59e0b]/20">
        <div className="text-xs text-[#f59e0b] uppercase tracking-widest mb-2">Emerging Extension — P(t) Purpose Term</div>
        <div className="text-sm text-[#60a5fa] font-mono mb-2">g(P) = 4P(1-P)</div>
        <div className="text-xs text-[#64748b]">The purpose gating function. Developed tonight. Models how purpose/meaning gates conscious processing. NOT yet integrated into the main equation — pending further validation.</div>
      </Card>

      {/* Live Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
        <Card><Stat label="Total N" value={egc.n} /></Card>
        <Card><Stat label="Compressors" value={`${egc.compressors}%`} color="text-[#10b981]" sub="Comfort rises w/ expression" /></Card>
        <Card><Stat label="Expanders" value={`${egc.expanders}%`} color="text-[#60a5fa]" sub="Comfort drops w/ expression" /></Card>
        <Card><Stat label="Suppressors" value={`${egc.suppressors}%`} color="text-[#f59e0b]" sub="Expression blocked" /></Card>
        <Card><Stat label="Pearson r" value={egc.pearson_r?.toFixed(3)} /></Card>
        <Card><Stat label="Comfort Gap" value={`${egc.comfort_gap}pts`} /></Card>
        <Card><Stat label="Zero-r Supp." value={egc.zero_r_suppressors ?? 6} color="text-[#ef4444]" sub="Total shutdown" /></Card>
      </div>

      {/* Distribution */}
      <Card>
        <div className="text-xs text-[#64748b] uppercase tracking-widest mb-3">Type Distribution</div>
        <div className="flex h-8 rounded-lg overflow-hidden">
          <div className="bg-[#10b981] flex items-center justify-center text-[10px] text-[#0a0e1a] font-bold" style={{ width: `${egc.compressors}%` }}>C {egc.compressors}%</div>
          <div className="bg-[#60a5fa] flex items-center justify-center text-[10px] text-[#0a0e1a] font-bold" style={{ width: `${egc.expanders}%` }}>E {egc.expanders}%</div>
          <div className="bg-[#f59e0b] flex items-center justify-center text-[10px] text-[#0a0e1a] font-bold" style={{ width: `${egc.suppressors}%` }}>S {egc.suppressors}%</div>
        </div>
      </Card>

      {/* Extreme Suppressor */}
      {egc.extreme_suppressor && (
        <Card className="border-[#ef4444]/20">
          <div className="text-xs text-[#ef4444] uppercase tracking-widest mb-2">Most Extreme Suppressor</div>
          <div className="text-sm">
            <span className="text-[#60a5fa] font-mono">{egc.extreme_suppressor.id}</span>
            <span className="text-[#64748b] mx-2">|</span>
            T_drop = {egc.extreme_suppressor.t_drop}
            <span className="text-[#64748b] mx-2">|</span>
            <span className="text-[#ef4444]">{egc.extreme_suppressor.decline_pct}% decline</span>
          </div>
          <div className="text-xs text-[#64748b] mt-1">Second suppression mechanism confirmed real — total emotional shutdown, not gradual suppression</div>
        </Card>
      )}

      {/* Variable Reference */}
      <Card>
        <div className="text-xs text-[#64748b] uppercase tracking-widest mb-3">Variable Reference</div>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-sm">
          {[
            ['Psi(t)', 'Conscious experience at time t'],
            ['Phi', 'Information integration (IIT)'],
            ['K(t)', 'Emotional knowledge / awareness'],
            ['T(t)', 'Transparency of expression'],
            ['r(t)', 'Suppression / resistance'],
            ['P(t)', 'Processing depth / purpose (emerging)'],
            ['g(K)', "Gate function = 4K(1-K) — Brandyn's contribution"],
            ['R_proxy', 'Expression-comfort correlation proxy'],
            ['T-drop', 'Change in transparency'],
          ].map(([v, desc]) => (
            <div key={v}><span className="text-[#60a5fa] font-mono">{v}</span> — {desc}</div>
          ))}
        </div>
      </Card>

      {/* Key Predictions */}
      <Card>
        <div className="text-xs text-[#64748b] uppercase tracking-widest mb-3">Key Predictions</div>
        <div className="space-y-2 text-sm">
          {[
            { text: 'Three distinct response types emerge from consciousness gating', confirmed: true },
            { text: 'Compressors show comfort rise with increased expression', confirmed: true },
            { text: 'g(K) = 4K(1-K) models the gating function', confirmed: true },
            { text: 'Bidirectional K-r feedback mechanism (Brandyn)', confirmed: true },
            { text: 'Second suppression mechanism exists (zero-r suppressors)', confirmed: true },
            { text: 'Suppressors have higher trait anxiety', confirmed: false },
            { text: 'Longitudinal stability of EGC types over 6 months', confirmed: false },
          ].map((p, i) => (
            <div key={i} className="flex items-start gap-2">
              <Icon d={p.confirmed ? icons.check : icons.target} className={`mt-0.5 shrink-0 ${p.confirmed ? 'text-[#10b981]' : 'text-[#f59e0b]'}`} />
              <span>{p.text}</span>
            </div>
          ))}
        </div>
      </Card>

      {egc.mock && <div className="text-xs text-[#64748b] text-center">Using cached data. Connect Supabase for live updates.</div>}
    </div>
  )
}

// ── ARONSON PREP VIEW ────────────────────────────────────────
function AronsonView() {
  const { aronson, fetchAronson, fetchEGC } = useStore()
  const [timer, setTimer] = useState(0)
  const [timerRunning, setTimerRunning] = useState(false)
  const timerRef = useRef<any>(null)

  useEffect(() => { fetchAronson(); fetchEGC() }, [])

  useEffect(() => {
    if (timerRunning) {
      timerRef.current = setInterval(() => setTimer(t => t + 1), 1000)
    } else {
      clearInterval(timerRef.current)
    }
    return () => clearInterval(timerRef.current)
  }, [timerRunning])

  const formatTime = (s: number) => `${Math.floor(s / 60).toString().padStart(2, '0')}:${(s % 60).toString().padStart(2, '0')}`

  if (!aronson) return <div className="text-[#64748b]">Loading Aronson prep data...</div>

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <SectionTitle>Aronson Call Preparation</SectionTitle>
        <Badge text="highest priority" color="bg-[#ef4444]/20 text-[#ef4444]" />
      </div>

      {/* Contact Card */}
      <Card className="border-[#f59e0b]/30">
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <div>
            <div className="text-xs text-[#64748b] uppercase tracking-widest mb-1">Contact</div>
            <div className="text-lg font-semibold">{aronson.contact.name}</div>
            <div className="text-sm text-[#64748b]">{aronson.contact.title}</div>
            <div className="text-sm text-[#60a5fa]">{aronson.contact.institution}</div>
          </div>
          <div>
            <div className="text-xs text-[#64748b] uppercase tracking-widest mb-1">Notable Work</div>
            <div className="text-sm">{aronson.contact.notable_work}</div>
          </div>
          <div>
            <div className="text-xs text-[#64748b] uppercase tracking-widest mb-1">Status</div>
            <Badge text={aronson.contact.call_status} color="bg-[#f59e0b]/20 text-[#f59e0b]" />
            <div className="text-xs text-[#64748b] mt-2">Responded: {aronson.contact.responded}</div>
          </div>
        </div>
      </Card>

      {/* Live Numbers */}
      <Card>
        <div className="flex items-center justify-between mb-3">
          <div className="text-xs text-[#64748b] uppercase tracking-widest">Your Numbers — Know These Cold</div>
          <button onClick={() => fetchEGC()} className="text-xs text-[#60a5fa] hover:text-[#2563eb]">Refresh from Supabase</button>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
          <Stat label="N" value={aronson.egc_numbers.n} color="text-[#e2e8f0]" />
          <Stat label="r" value={aronson.egc_numbers.pearson_r} color="text-[#60a5fa]" />
          <Stat label="Gap" value={`${aronson.egc_numbers.comfort_gap}pts`} />
          <Stat label="Compressors" value={`${aronson.egc_numbers.compressors_pct}%`} color="text-[#10b981]" />
          <Stat label="Expanders" value={`${aronson.egc_numbers.expanders_pct}%`} color="text-[#60a5fa]" />
          <Stat label="Suppressors" value={`${aronson.egc_numbers.suppressors_pct}%`} color="text-[#f59e0b]" />
          <Stat label="Zero-r" value={aronson.egc_numbers.zero_r_suppressors} color="text-[#ef4444]" />
        </div>
        <div className="text-xs text-[#64748b] mt-3">Extreme case: {aronson.egc_numbers.extreme_case}</div>
      </Card>

      {/* Practice Timer */}
      <Card className="border-[#2563eb]/30">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-xs text-[#64748b] uppercase tracking-widest mb-1">Practice Run Timer</div>
            <div className="text-3xl font-mono text-[#60a5fa]">{formatTime(timer)}</div>
          </div>
          <div className="flex gap-2">
            <button onClick={() => setTimerRunning(!timerRunning)}
              className={`px-4 py-2 rounded text-sm ${timerRunning ? 'bg-[#ef4444] text-white' : 'bg-[#10b981] text-white'}`}>
              {timerRunning ? 'Pause' : 'Start'}
            </button>
            <button onClick={() => { setTimer(0); setTimerRunning(false) }}
              className="px-4 py-2 rounded text-sm bg-[#1e2d40] text-[#64748b]">Reset</button>
          </div>
        </div>
        <div className="text-xs text-[#64748b] mt-2">Aim for 3-5 minutes for the core pitch. 15-20 minutes total including Q&A.</div>
      </Card>

      {/* Talking Points */}
      <Card>
        <div className="text-xs text-[#64748b] uppercase tracking-widest mb-3">Talking Points — In Order</div>
        <div className="space-y-3">
          {aronson.talking_points.map((point: string, i: number) => (
            <div key={i} className="flex items-start gap-3 text-sm">
              <span className="text-[10px] text-[#64748b] font-mono bg-[#1e2d40] rounded px-1.5 py-0.5 mt-0.5">{i + 1}</span>
              <span>{point}</span>
            </div>
          ))}
        </div>
      </Card>

      {/* Q&A */}
      <Card>
        <div className="text-xs text-[#64748b] uppercase tracking-widest mb-3">Possible Questions & Answers</div>
        <div className="space-y-4">
          {aronson.possible_questions.map((qa: any, i: number) => (
            <div key={i} className="border-b border-[#1e2d40] pb-4 last:border-0">
              <div className="text-sm font-semibold text-[#f59e0b] mb-1">Q: {qa.q}</div>
              <div className="text-sm text-[#e2e8f0]">A: {qa.a}</div>
            </div>
          ))}
        </div>
      </Card>

      {/* Methodology Quick Ref */}
      <Card>
        <div className="text-xs text-[#64748b] uppercase tracking-widest mb-3">Methodology Quick Reference</div>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div><span className="text-[#64748b]">Instruments:</span> {aronson.methodology.instruments}</div>
          <div><span className="text-[#64748b]">Validation:</span> {aronson.methodology.validation}</div>
          <div><span className="text-[#64748b]">Core equation:</span> <span className="font-mono text-[#60a5fa]">{aronson.methodology.equation}</span></div>
          <div><span className="text-[#64748b]">Gate function:</span> {aronson.methodology.gate_function}</div>
        </div>
      </Card>

      {/* Credits */}
      <Card>
        <div className="text-xs text-[#64748b] uppercase tracking-widest mb-2">Attribution</div>
        <div className="text-sm space-y-1">
          <div><span className="text-[#60a5fa]">Bryan Leonard</span> — EGC framework, empirical study design, data analysis</div>
          <div><span className="text-[#60a5fa]">Brandyn Leonard</span> — g(K) = 4K(1-K) parabolic conviction function, bidirectional K-r feedback mechanism identification</div>
        </div>
      </Card>
    </div>
  )
}

// ── LOLM VIEW ────────────────────────────────────────────────
function LOLMView() {
  return (
    <div className="space-y-6">
      <SectionTitle>LOLM — Custom Language Model</SectionTitle>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card><Stat label="Target Scale" value="10B-100B" sub="parameters" /></Card>
        <Card><Stat label="Compute" value="TPU Pods" sub="via TRC grant" color="text-[#10b981]" /></Card>
        <Card><Stat label="Status" value="Infrastructure" sub="fix VMs before scaling" color="text-[#f59e0b]" /></Card>
      </div>
      <Card>
        <div className="text-xs text-[#64748b] uppercase tracking-widest mb-3">Priority: Fix Infrastructure</div>
        <div className="text-sm text-[#f59e0b]">VMs are broken. Fix the infrastructure before scaling. Do not modify the model architecture — wrap it.</div>
      </Card>
      <Card>
        <div className="text-xs text-[#64748b] uppercase tracking-widest mb-3">Tech Stack</div>
        <div className="flex flex-wrap gap-2">
          {['Python', 'PyTorch', 'XLA', 'JAX', 'TPU', 'Transformers', 'CUDA', 'NumPy'].map(t => <Badge key={t} text={t} />)}
        </div>
      </Card>
      <Card>
        <div className="text-xs text-[#64748b] uppercase tracking-widest mb-3">Milestones</div>
        <div className="space-y-2">
          {[
            { name: 'Architecture design', done: true },
            { name: 'TRC grant secured', done: true },
            { name: 'Fix VM infrastructure', done: false },
            { name: 'Data pipeline', done: false },
            { name: 'Initial training run', done: false },
            { name: 'Evaluation benchmarks', done: false },
          ].map((m, i) => (
            <div key={i} className="flex items-center gap-3 text-sm">
              <Icon d={m.done ? icons.check : icons.clock} className={m.done ? 'text-[#10b981]' : 'text-[#64748b]'} />
              <span className={m.done ? '' : 'text-[#64748b]'}>{m.name}</span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}

// ── CODEY VIEW ───────────────────────────────────────────────
function CodeyView() {
  return (
    <div className="space-y-6">
      <SectionTitle>Codey — AI Coding SaaS</SectionTitle>
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card><Stat label="Status" value="Live" color="text-[#10b981]" sub="codey.cc" /></Card>
        <Card><Stat label="Backend" value="Render" sub="FastAPI" /></Card>
        <Card><Stat label="Payments" value="Stripe" sub="billing" /></Card>
        <Card><Stat label="Specs" value="9 docs" sub="complete" color="text-[#60a5fa]" /></Card>
      </div>
      <Card>
        <div className="text-xs text-[#64748b] uppercase tracking-widest mb-3">Build Progress</div>
        <div className="space-y-3">
          {[
            { name: 'Landing page', pct: 100 },
            { name: 'User authentication', pct: 100 },
            { name: 'Intelligence stack mapped', pct: 100 },
            { name: 'Stripe billing', pct: 70 },
            { name: 'Code generation engine', pct: 40 },
            { name: 'Credits system', pct: 30 },
            { name: 'User dashboard', pct: 20 },
            { name: 'Competitive analysis', pct: 0 },
          ].map((m) => (
            <div key={m.name}>
              <div className="flex items-center justify-between text-sm mb-1">
                <span>{m.name}</span>
                <span className="text-xs text-[#64748b]">{m.pct}%</span>
              </div>
              <HealthBar value={m.pct / 10} />
            </div>
          ))}
        </div>
      </Card>
      <Card>
        <div className="text-xs text-[#f59e0b] uppercase tracking-widest mb-2">Priority</div>
        <div className="text-sm">Ship the product. The backend is on Render. 9 spec documents exist. The intelligence stack is mapped. Make it real, not just specced.</div>
      </Card>
    </div>
  )
}

// ── KNOWLEDGE VIEW ───────────────────────────────────────────
function KnowledgeView() {
  const { knowledge, fetchKnowledge, conversations, fetchConversations, searchKnowledge } = useStore()
  const [search, setSearch] = useState('')
  const [results, setResults] = useState<any>(null)

  useEffect(() => { fetchKnowledge(); fetchConversations() }, [])

  const doSearch = async () => {
    if (!search.trim()) return
    const r = await searchKnowledge(search)
    setResults(r)
  }

  return (
    <div className="space-y-6">
      <SectionTitle>Knowledge Base</SectionTitle>
      <div className="flex gap-2">
        <div className="relative flex-1">
          <input value={search} onChange={e => setSearch(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && doSearch()}
            placeholder="Search conversations, memories, knowledge..."
            className="w-full bg-[#111827] border border-[#1e2d40] rounded-lg pl-4 pr-4 py-2.5 text-sm text-[#e2e8f0] outline-none focus:border-[#2563eb]" />
        </div>
        <button onClick={doSearch} className="bg-[#2563eb] text-white px-4 py-2 rounded-lg text-sm">Search</button>
      </div>

      {results && (
        <Card>
          <div className="text-xs text-[#64748b] uppercase tracking-widest mb-3">
            Results — {(results.knowledge?.length || 0) + (results.conversations?.length || 0) + (results.memories?.length || 0)} found
          </div>
          <div className="space-y-2">
            {results.knowledge?.map((k: any) => (
              <div key={k.id} className="text-sm border-b border-[#1e2d40] pb-2"><span className="font-semibold">{k.title}</span> <Badge text="knowledge" /><div className="text-xs text-[#64748b] mt-1 line-clamp-2">{k.content}</div></div>
            ))}
            {results.conversations?.map((c: any) => (
              <div key={c.id} className="text-sm border-b border-[#1e2d40] pb-2"><span className="font-semibold">{c.title}</span> <Badge text={c.source} /><div className="text-xs text-[#64748b] mt-1 line-clamp-2">{c.summary}</div></div>
            ))}
            {results.memories?.map((m: any) => (
              <div key={m.id} className="text-sm border-b border-[#1e2d40] pb-2"><span className="font-semibold">{m.title}</span> <Badge text="memory" /><div className="text-xs text-[#64748b] mt-1 line-clamp-2">{m.content}</div></div>
            ))}
          </div>
        </Card>
      )}

      <Card>
        <div className="text-xs text-[#64748b] uppercase tracking-widest mb-3">Knowledge ({knowledge.length} entries)</div>
        {knowledge.length === 0 ? (
          <div className="text-[#64748b] text-sm">Knowledge base empty. Import from ChatGPT export or filesystem sweep to populate.</div>
        ) : (
          <div className="space-y-2">{knowledge.map((k: any) => (
            <div key={k.id} className="text-sm border-b border-[#1e2d40] pb-2 last:border-0"><div className="font-semibold">{k.title}</div><div className="text-xs text-[#64748b] mt-1 line-clamp-2">{k.content}</div></div>
          ))}</div>
        )}
      </Card>

      <Card>
        <div className="text-xs text-[#64748b] uppercase tracking-widest mb-3">Conversations ({conversations.length})</div>
        {conversations.length === 0 ? (
          <div className="text-[#64748b] text-sm">No conversations imported yet. Complete ChatGPT export to populate.</div>
        ) : (
          <div className="space-y-2">{conversations.map((c: any) => (
            <div key={c.id} className="text-sm border-b border-[#1e2d40] pb-2 last:border-0">
              <span className="font-semibold">{c.title}</span> <Badge text={c.source} />
              <div className="text-xs text-[#64748b] mt-1">{c.summary}</div>
            </div>
          ))}</div>
        )}
      </Card>
    </div>
  )
}

// ── PERSONAL OS VIEW ─────────────────────────────────────────
function PersonalOSView() {
  const { today, fetchToday, saveDaily, ideas, fetchIdeas, createIdea } = useStore()
  const [newIdea, setNewIdea] = useState({ title: '', description: '' })
  const [dailyForm, setDailyForm] = useState({ sleep_hours: '', energy: '', focus: '', mood: '', notes: '' })

  // Session tracking
  const sessionStart = useStore(s => s.sessionStart)
  const setSessionStart = useStore(s => s.setSessionStart)
  useEffect(() => {
    if (!sessionStart) setSessionStart(new Date().toISOString())
    fetchToday(); fetchIdeas()
  }, [])

  const sessionMinutes = sessionStart ? Math.floor((Date.now() - new Date(sessionStart).getTime()) / 60000) : 0
  const sessionHours = Math.floor(sessionMinutes / 60)
  const sessionMins = sessionMinutes % 60

  return (
    <div className="space-y-6">
      <SectionTitle>Personal Operating System</SectionTitle>

      {/* Session Awareness */}
      <Card className="border-[#2563eb]/20">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-xs text-[#64748b] uppercase tracking-widest mb-1">Current Session</div>
            <div className="text-lg text-[#60a5fa]">{sessionHours}h {sessionMins}m</div>
            <div className="text-xs text-[#64748b]">Started: {sessionStart ? new Date(sessionStart).toLocaleTimeString() : 'now'}</div>
          </div>
          {sessionMinutes > 180 && (
            <div className="text-right">
              <div className="text-xs text-[#f59e0b]">Long session</div>
              <div className="text-[10px] text-[#64748b]">Consider a break when you hit a natural pause</div>
            </div>
          )}
        </div>
      </Card>

      {/* Daily Check-in */}
      <Card>
        <div className="text-xs text-[#64748b] uppercase tracking-widest mb-3">Daily Check-in — {new Date().toLocaleDateString()}</div>
        {today?.exists ? (
          <div className="grid grid-cols-4 gap-4">
            <Stat label="Sleep" value={`${today.sleep_hours || '-'}h`} />
            <Stat label="Energy" value={`${today.energy || '-'}/10`} />
            <Stat label="Focus" value={`${today.focus || '-'}/10`} />
            <Stat label="Mood" value={`${today.mood || '-'}/10`} />
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            {(['sleep_hours', 'energy', 'focus', 'mood'] as const).map(field => (
              <div key={field}>
                <label className="text-[10px] text-[#64748b] uppercase">{field.replace('_', ' ')}{field === 'sleep_hours' ? ' (hrs)' : ' (1-10)'}</label>
                <input type="number" value={(dailyForm as any)[field]} onChange={e => setDailyForm({ ...dailyForm, [field]: e.target.value })}
                  className="w-full bg-[#0a0e1a] border border-[#1e2d40] rounded px-3 py-1.5 text-sm text-[#e2e8f0] outline-none mt-1" />
              </div>
            ))}
            <div className="flex items-end">
              <button onClick={() => {
                saveDaily({ date: new Date().toISOString().split('T')[0], sleep_hours: parseFloat(dailyForm.sleep_hours) || null, energy: parseInt(dailyForm.energy) || null, focus: parseInt(dailyForm.focus) || null, mood: parseInt(dailyForm.mood) || null, notes: dailyForm.notes })
              }} className="bg-[#2563eb] text-white px-4 py-1.5 rounded text-sm w-full">Save</button>
            </div>
          </div>
        )}
      </Card>

      {/* Ideas */}
      <Card>
        <div className="flex items-center justify-between mb-3">
          <div className="text-xs text-[#64748b] uppercase tracking-widest">Idea Vault ({ideas.length})</div>
        </div>
        <div className="flex gap-2 mb-4">
          <input value={newIdea.title} onChange={e => setNewIdea({ ...newIdea, title: e.target.value })} placeholder="Idea title..."
            className="flex-1 bg-[#0a0e1a] border border-[#1e2d40] rounded px-3 py-2 text-sm text-[#e2e8f0] outline-none" />
          <input value={newIdea.description} onChange={e => setNewIdea({ ...newIdea, description: e.target.value })} placeholder="Description..."
            className="flex-[2] bg-[#0a0e1a] border border-[#1e2d40] rounded px-3 py-2 text-sm text-[#e2e8f0] outline-none" />
          <button onClick={() => { if (newIdea.title) { createIdea(newIdea); setNewIdea({ title: '', description: '' }) } }}
            className="bg-[#2563eb] text-white px-4 py-2 rounded text-sm">Add</button>
        </div>
        <div className="space-y-2">
          {ideas.map((idea: any) => (
            <div key={idea.id} className="flex items-start gap-3 text-sm border-b border-[#1e2d40] pb-2 last:border-0">
              <Icon d={icons.bulb} className="text-[#f59e0b] mt-0.5 shrink-0" />
              <div><div className="font-semibold">{idea.title}</div><div className="text-xs text-[#64748b]">{idea.description}</div></div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}

// ── NETWORK VIEW ─────────────────────────────────────────────
function NetworkView() {
  const { contacts, fetchContacts, grants, fetchGrants, createContact } = useStore()
  const [nc, setNc] = useState({ name: '', role: '', institution: '' })
  const [showForm, setShowForm] = useState(false)
  useEffect(() => { fetchContacts(); fetchGrants() }, [])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <SectionTitle>Network & Grants</SectionTitle>
        <button onClick={() => setShowForm(!showForm)} className="text-xs text-[#60a5fa]">+ Add Contact</button>
      </div>
      {showForm && (
        <Card>
          <div className="flex gap-3">
            <input value={nc.name} onChange={e => setNc({ ...nc, name: e.target.value })} placeholder="Name" className="flex-1 bg-[#0a0e1a] border border-[#1e2d40] rounded px-3 py-2 text-sm text-[#e2e8f0] outline-none" />
            <input value={nc.role} onChange={e => setNc({ ...nc, role: e.target.value })} placeholder="Role" className="flex-1 bg-[#0a0e1a] border border-[#1e2d40] rounded px-3 py-2 text-sm text-[#e2e8f0] outline-none" />
            <input value={nc.institution} onChange={e => setNc({ ...nc, institution: e.target.value })} placeholder="Institution" className="flex-1 bg-[#0a0e1a] border border-[#1e2d40] rounded px-3 py-2 text-sm text-[#e2e8f0] outline-none" />
            <button onClick={() => { createContact(nc); setNc({ name: '', role: '', institution: '' }); setShowForm(false) }} className="bg-[#2563eb] text-white px-4 py-2 rounded text-sm">Add</button>
          </div>
        </Card>
      )}
      <Card>
        <div className="text-xs text-[#64748b] uppercase tracking-widest mb-3">Key Contacts</div>
        <div className="space-y-3">
          {contacts.map((c: any) => (
            <div key={c.id} className="flex items-center gap-4 border-b border-[#1e2d40] pb-3 last:border-0">
              <div className="w-8 h-8 rounded-full bg-[#2563eb]/20 flex items-center justify-center text-xs text-[#60a5fa] font-bold">
                {c.name.split(' ').map((w: string) => w[0]).join('')}
              </div>
              <div className="flex-1">
                <div className="text-sm font-semibold">{c.name}</div>
                <div className="text-xs text-[#64748b]">{c.role}{c.institution ? ` — ${c.institution}` : ''}</div>
              </div>
              <Badge text={c.status} color={c.status === 'active' ? 'bg-[#10b981]/20 text-[#10b981]' : 'bg-[#f59e0b]/20 text-[#f59e0b]'} />
            </div>
          ))}
        </div>
      </Card>
      <Card>
        <div className="text-xs text-[#64748b] uppercase tracking-widest mb-3">Grant Pipeline</div>
        <div className="space-y-3">
          {grants.map((g: any) => (
            <div key={g.id} className="flex items-center justify-between border-b border-[#1e2d40] pb-3 last:border-0">
              <div><div className="text-sm font-semibold">{g.name}</div><div className="text-xs text-[#64748b]">{g.funder}</div></div>
              <Badge text={g.status} color={g.status === 'active' ? 'bg-[#10b981]/20 text-[#10b981]' : 'bg-[#64748b]/20 text-[#64748b]'} />
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}

// ── CREATION STUDIO VIEW ─────────────────────────────────────
function CreationStudioView() {
  const { sendChat, chatResponse, chatLoading } = useStore()
  const [template, setTemplate] = useState('')
  const [prompt, setPrompt] = useState('')
  const [output, setOutput] = useState('')

  const templates = [
    { key: 'email', label: 'Email' },
    { key: 'paper', label: 'Research Paper' },
    { key: 'linkedin', label: 'LinkedIn Post' },
    { key: 'pitch', label: 'Pitch Deck' },
    { key: 'spec', label: 'Technical Spec' },
    { key: 'grant', label: 'Grant Proposal' },
  ]

  useEffect(() => { if (chatResponse && !chatLoading) setOutput(chatResponse) }, [chatResponse, chatLoading])

  return (
    <div className="space-y-6">
      <SectionTitle>Creation Studio</SectionTitle>
      <div className="flex flex-wrap gap-2">
        {templates.map(t => (
          <button key={t.key} onClick={() => setTemplate(t.key)}
            className={`text-xs px-3 py-1.5 rounded-full border ${template === t.key ? 'border-[#2563eb] bg-[#2563eb]/20 text-[#60a5fa]' : 'border-[#1e2d40] text-[#64748b]'}`}>
            {t.label}
          </button>
        ))}
      </div>
      <div className="flex gap-2">
        <textarea value={prompt} onChange={e => setPrompt(e.target.value)} placeholder="What would you like to create?" rows={3}
          className="flex-1 bg-[#111827] border border-[#1e2d40] rounded-lg px-4 py-3 text-sm text-[#e2e8f0] outline-none focus:border-[#2563eb] resize-none" />
        <button onClick={() => { if (prompt.trim()) sendChat(`[${template || 'general'}] ${prompt}`, 'writing') }} disabled={chatLoading}
          className="bg-[#2563eb] text-white px-6 rounded-lg text-sm disabled:opacity-50 self-end py-3">
          {chatLoading ? 'Creating...' : 'Generate'}
        </button>
      </div>
      {output && (
        <Card>
          <div className="text-xs text-[#64748b] uppercase tracking-widest mb-3">Output</div>
          <div className="text-sm whitespace-pre-wrap leading-relaxed">{output}</div>
        </Card>
      )}
    </div>
  )
}

// ── WELLBEING VIEW ───────────────────────────────────────────
function WellbeingView() {
  const { healthLogs, fetchHealthLogs, addHealthLog } = useStore()
  const [form, setForm] = useState({ sleep_hours: '', sleep_quality: '', energy: '', mood: '', exercise: '', notes: '' })

  const sessionStart = useStore(s => s.sessionStart)
  const sessionMinutes = sessionStart ? Math.floor((Date.now() - new Date(sessionStart).getTime()) / 60000) : 0

  useEffect(() => { fetchHealthLogs() }, [])

  return (
    <div className="space-y-6">
      <SectionTitle>Health & Wellbeing</SectionTitle>

      {/* Session Length Awareness */}
      <Card className={sessionMinutes > 240 ? 'border-[#f59e0b]/30' : 'border-[#1e2d40]'}>
        <div className="flex items-center justify-between">
          <div>
            <div className="text-xs text-[#64748b] uppercase tracking-widest mb-1">Session Length</div>
            <div className={`text-2xl font-mono ${sessionMinutes > 240 ? 'text-[#f59e0b]' : 'text-[#60a5fa]'}`}>
              {Math.floor(sessionMinutes / 60)}h {sessionMinutes % 60}m
            </div>
          </div>
          <div className="text-right text-xs text-[#64748b]">
            <div>Started: {sessionStart ? new Date(sessionStart).toLocaleTimeString() : '-'}</div>
            <div>Now: {new Date().toLocaleTimeString()}</div>
          </div>
        </div>
      </Card>

      {/* Quick Log */}
      <Card>
        <div className="text-xs text-[#64748b] uppercase tracking-widest mb-3">Log Today</div>
        <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
          {[
            { key: 'sleep_hours', label: 'Sleep (hrs)', type: 'number', step: '0.5' },
            { key: 'sleep_quality', label: 'Quality (1-10)', type: 'number' },
            { key: 'energy', label: 'Energy (1-10)', type: 'number' },
            { key: 'mood', label: 'Mood (1-10)', type: 'number' },
            { key: 'exercise', label: 'Exercise', type: 'text' },
          ].map(f => (
            <div key={f.key}>
              <label className="text-[10px] text-[#64748b] uppercase">{f.label}</label>
              <input type={f.type} step={f.step} value={(form as any)[f.key]}
                onChange={e => setForm({ ...form, [f.key]: e.target.value })}
                className="w-full bg-[#0a0e1a] border border-[#1e2d40] rounded px-3 py-1.5 text-sm text-[#e2e8f0] outline-none mt-1" />
            </div>
          ))}
          <div className="flex items-end">
            <button onClick={() => {
              addHealthLog({ sleep_hours: parseFloat(form.sleep_hours) || null, sleep_quality: parseInt(form.sleep_quality) || null, energy: parseInt(form.energy) || null, mood: parseInt(form.mood) || null, exercise: form.exercise, notes: form.notes })
              setForm({ sleep_hours: '', sleep_quality: '', energy: '', mood: '', exercise: '', notes: '' })
            }} className="bg-[#2563eb] text-white px-4 py-1.5 rounded text-sm w-full">Log</button>
          </div>
        </div>
      </Card>

      {/* History */}
      <Card>
        <div className="text-xs text-[#64748b] uppercase tracking-widest mb-3">Recent Logs</div>
        {healthLogs.length === 0 ? (
          <div className="text-[#64748b] text-sm">No health logs yet. Start tracking above.</div>
        ) : (
          <div className="space-y-2">
            {healthLogs.map((log: any) => (
              <div key={log.id} className="flex items-center gap-4 text-sm border-b border-[#1e2d40] pb-2 last:border-0">
                <span className="text-[#64748b] w-24">{log.date}</span>
                <span>Sleep: {log.sleep_hours || '-'}h</span>
                <span>Energy: {log.energy || '-'}/10</span>
                <span>Mood: {log.mood || '-'}/10</span>
                {log.exercise && <Badge text={log.exercise} />}
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Gentle Reminders */}
      <Card>
        <div className="text-xs text-[#64748b] uppercase tracking-widest mb-3">Visibility</div>
        <div className="text-sm text-[#64748b] space-y-2">
          <div>Target: 7-8 hours of sleep</div>
          <div>You work nights consistently. This isn't a judgment — just make it visible.</div>
          <div>Breaks every 90 minutes help focus sustainability.</div>
          <div>Water. Stand up. Move.</div>
        </div>
      </Card>
    </div>
  )
}

// ── MAIN APP ─────────────────────────────────────────────────
export default function App() {
  const { view, setView, authenticated, sendChat, chatResponse, chatLoading } = useStore()
  const [chatOpen, setChatOpen] = useState(false)
  const [chatMsg, setChatMsg] = useState('')
  const [chatHistory, setChatHistory] = useState<{ role: string; text: string }[]>(() => {
    const saved = localStorage.getItem('nous_quick_chat')
    return saved ? JSON.parse(saved) : []
  })

  useEffect(() => { localStorage.setItem('nous_quick_chat', JSON.stringify(chatHistory.slice(-50))) }, [chatHistory])
  useEffect(() => {
    if (chatResponse && !chatLoading) setChatHistory(h => [...h, { role: 'assistant', text: chatResponse }])
  }, [chatResponse, chatLoading])

  // Track session start
  const setSessionStart = useStore(s => s.setSessionStart)
  const sessionStart = useStore(s => s.sessionStart)
  useEffect(() => { if (!sessionStart) setSessionStart(new Date().toISOString()) }, [])

  if (!authenticated) return <AuthScreen />

  const quickChat = async () => {
    if (!chatMsg.trim()) return
    setChatHistory(h => [...h, { role: 'user', text: chatMsg }])
    const m = chatMsg; setChatMsg('')
    await sendChat(m)
  }

  const renderView = () => {
    switch (view) {
      case 'nucleus': return <NucleusView />
      case 'nous': return <NousAgent />
      case 'intelligence': return <IntelligenceView />
      case 'projects': return <ProjectsView />
      case 'egc': return <EGCView />
      case 'aronson': return <AronsonView />
      case 'lolm': return <LOLMView />
      case 'codey': return <CodeyView />
      case 'knowledge': return <KnowledgeView />
      case 'personal': return <PersonalOSView />
      case 'network': return <NetworkView />
      case 'studio': return <CreationStudioView />
      case 'health': return <WellbeingView />
      default: return <NucleusView />
    }
  }

  return (
    <div className="flex h-screen">
      {/* Sidebar */}
      <nav className="w-[220px] bg-[#111827] border-r border-[#1e2d40] flex flex-col shrink-0">
        <div className="px-5 py-6 border-b border-[#1e2d40]">
          <div className="text-[10px] text-[#64748b] tracking-[0.3em] uppercase">QIRA COMMAND</div>
          <div className="text-lg text-[#60a5fa] mt-1 font-semibold">Bryan Leonard</div>
        </div>
        <div className="flex-1 py-2 overflow-y-auto">
          {VIEWS.map(({ key, label, icon }) => (
            <button key={key} onClick={() => setView(key)}
              className={`w-full flex items-center gap-3 px-5 py-2.5 text-left transition-colors ${view === key ? 'bg-[#2563eb]/10 text-[#60a5fa] border-l-2 border-[#2563eb]' : 'text-[#64748b] hover:text-[#e2e8f0] border-l-2 border-transparent'}`}>
              <Icon d={(icons as any)[icon] || icons.folder} className="shrink-0" />
              <span className="text-[11px] tracking-[0.1em] uppercase">{label}</span>
              {key === 'aronson' && <span className="ml-auto w-1.5 h-1.5 rounded-full bg-[#ef4444]" />}
            </button>
          ))}
        </div>
        <div className="px-5 py-4 border-t border-[#1e2d40]">
          <div className="text-[#10b981] text-[10px] font-semibold flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-[#10b981] animate-pulse" /> EGC LIVE
          </div>
          <div className="text-[10px] text-[#64748b] mt-1">N = 40 subjects</div>
          <div className="text-[10px] text-[#64748b]">r = 0.311</div>
          <div className="text-[10px] text-[#64748b]">Aronson: PENDING</div>
        </div>
      </nav>

      {/* Main */}
      <main className="flex-1 overflow-y-auto p-8">
        <AnimatePresence mode="wait">
          <motion.div key={view} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.15 }}>
            {renderView()}
          </motion.div>
        </AnimatePresence>
      </main>

      {/* Floating Chat */}
      <button onClick={() => setChatOpen(!chatOpen)}
        className="fixed bottom-6 right-6 w-14 h-14 rounded-full bg-[#2563eb] text-white flex items-center justify-center shadow-lg shadow-[#2563eb]/30 hover:bg-[#2563eb]/80 z-50 text-xl">
        {chatOpen ? <Icon d={icons.x} className="w-5 h-5" /> : <Icon d={icons.zap} className="w-5 h-5" />}
      </button>

      {chatOpen && (
        <div className="fixed bottom-24 right-6 w-[460px] bg-[#111827] border border-[#1e2d40] rounded-xl p-5 shadow-2xl shadow-black/50 z-40">
          <div className="text-xs text-[#60a5fa] tracking-[0.1em] mb-3">NOUS — QUICK CHAT</div>
          <div className="max-h-[300px] overflow-y-auto mb-3 space-y-2">
            {chatHistory.map((h, i) => (
              <div key={i} className={`text-sm rounded-lg p-2 ${h.role === 'user' ? 'bg-[#2563eb]/20 text-[#60a5fa] ml-8' : 'bg-[#1a2332] text-[#e2e8f0] mr-8'}`}>
                {h.text.length > 500 ? h.text.slice(0, 500) + '...' : h.text}
              </div>
            ))}
            {chatLoading && <div className="text-sm text-[#64748b] animate-pulse">Thinking...</div>}
          </div>
          <div className="flex gap-2">
            <input value={chatMsg} onChange={e => setChatMsg(e.target.value)} onKeyDown={e => e.key === 'Enter' && quickChat()}
              placeholder="Quick question..."
              className="flex-1 bg-[#0a0e1a] border border-[#1e2d40] rounded-lg px-3 py-2 text-sm text-[#e2e8f0] outline-none focus:border-[#2563eb]" />
            <button onClick={quickChat} disabled={chatLoading} className="bg-[#2563eb] text-white px-4 py-2 rounded-lg text-sm disabled:opacity-50">
              <Icon d={icons.send} />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
