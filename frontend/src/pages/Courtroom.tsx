import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Scale, Gavel, Sword, Search, RefreshCw } from 'lucide-react'
import { useLiveStream } from '../hooks/useLiveStream'
import { LogEntry } from '../types'
import { api } from '../api/client'

const NODE_COLORS: Record<string, string> = {
  investigator:   'text-court-cyan',
  challenger:     'text-court-rejected',
  judge:          'text-court-gold',
  self_correction:'text-court-deferred',
  system:         'text-court-muted',
}

const NODE_ICONS: Record<string, React.ReactNode> = {
  investigator:    <Search size={14} />,
  challenger:      <Sword size={14} />,
  judge:           <Gavel size={14} />,
  self_correction: <RefreshCw size={14} />,
  system:          <Scale size={14} />,
}

const EVENT_COLORS: Record<string, string> = {
  TOOL_INVOKED:     'text-court-muted',
  TOOL_COMPLETED:   'text-court-cyan/70',
  TOOL_FAILED:      'text-court-rejected',
  FINDINGS_CREATED: 'text-court-cyan',
  CHALLENGE_ISSUED: 'text-court-rejected',
  RULING_ISSUED:    'text-court-gold',
  ADMISSION_RATE:   'text-court-admitted',
  CORRECTION_STARTED:'text-court-deferred',
  CORRECTION_COMPLETED:'text-court-deferred',
  VERDICT_ISSUED:   'text-court-gold font-bold',
  AGENT_STARTED:    'text-court-text',
  AGENT_RUNNING:    'text-court-muted',
  ERROR:            'text-court-rejected',
}

interface AgentState {
  status: 'idle' | 'active' | 'complete'
  lastMessage: string
  findings: number
  iteration: number
}

export default function Courtroom() {
  const { caseId } = useParams<{ caseId: string }>()
  const navigate = useNavigate()
  const { entries, connected, done } = useLiveStream(caseId || null)
  const logRef = useRef<HTMLDivElement>(null)

  const [admissionRate, setAdmissionRate] = useState(0)
  const [admittedCount, setAdmittedCount] = useState(0)
  const [totalFindings, setTotalFindings] = useState(0)
  const [currentIteration, setCurrentIteration] = useState(0)
  const [agents, setAgents] = useState<Record<string, AgentState>>({
    investigator:    { status: 'idle', lastMessage: 'Awaiting case...', findings: 0, iteration: 0 },
    challenger:      { status: 'idle', lastMessage: 'Standing by...', findings: 0, iteration: 0 },
    judge:           { status: 'idle', lastMessage: 'Court not in session.', findings: 0, iteration: 0 },
    self_correction: { status: 'idle', lastMessage: 'No corrections pending.', findings: 0, iteration: 0 },
  })

  // Update agent states and stats from log entries
  useEffect(() => {
    if (entries.length === 0) return
    const last = entries[entries.length - 1]
    const node = last.node

    setCurrentIteration(last.iteration || 0)

    setAgents(prev => {
      const updated = { ...prev }
      if (node in updated) {
        const isComplete = last.event_type.includes('COMPLETE') || last.event_type === 'VERDICT_ISSUED'
        const isActive = last.event_type.includes('STARTED') || last.event_type.includes('RUNNING') || last.event_type.includes('INVOKED')
        updated[node] = {
          ...updated[node],
          status: isComplete ? 'complete' : isActive ? 'active' : 'active',
          lastMessage: last.message,
          iteration: last.iteration || 0
        }
        if (last.event_type === 'FINDINGS_CREATED') {
          const count = (last.payload?.count as number) || 0
          updated.investigator.findings = count
          setTotalFindings(count)
          updated.challenger.status = 'idle'
          updated.judge.status = 'idle'
          updated.self_correction.status = 'idle'
        }
        if (last.event_type === 'ADMISSION_RATE') {
          const rate = (last.payload?.rate as number) || 0
          setAdmissionRate(rate)
          const match = last.message.match(/\((\d+)\/(\d+)/)
          if (match) {
            setAdmittedCount(parseInt(match[1]))
            setTotalFindings(parseInt(match[2]))
          }
        }
      }
      return updated
    })

    // Auto-scroll log
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight
    }
  }, [entries])

  // Navigate to verdict when done
  useEffect(() => {
    if (done) {
      setTimeout(() => navigate(`/verdict/${caseId}`), 2000)
    }
  }, [done, caseId, navigate])

  const formatTime = (ts: string) => {
    try { return new Date(ts).toLocaleTimeString() } catch { return ts }
  }

  return (
    <div className="min-h-screen bg-court-bg flex flex-col">
      {/* Header */}
      <header className="border-b border-court-border px-6 py-4 flex items-center gap-4">
        <Scale className="text-court-gold" size={20} />
        <span className="text-court-gold font-mono font-bold tracking-widest">VERDICT</span>
        <span className="text-court-muted font-mono text-sm">|</span>
        <span className="text-court-muted font-mono text-sm">Case #{caseId?.slice(0, 8).toUpperCase()}</span>
        <span className="text-court-muted font-mono text-sm">Iter {currentIteration}/3</span>
        <div className="ml-auto flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${connected ? 'bg-court-admitted animate-pulse' : 'bg-court-muted'}`} />
          <span className="text-xs font-mono text-court-muted">{connected ? '● LIVE' : 'CONNECTING'}</span>
          {done && <span className="text-xs font-mono text-court-gold ml-2">→ Redirecting to Verdict...</span>}
        </div>
      </header>

      <div className="flex-1 flex flex-col p-4 gap-4 max-w-7xl mx-auto w-full">
        {/* Admission Meter */}
        <div className="bg-court-surface border border-court-border rounded-xl p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-mono text-court-muted uppercase tracking-wider">Admission Rate</span>
            <span className={`text-lg font-bold font-mono ${admissionRate >= 0.7 ? 'text-court-admitted' : 'text-court-deferred'}`}>
              {(admissionRate * 100).toFixed(0)}%
              <span className="text-court-muted text-sm font-normal ml-2">
                ({admittedCount}/{totalFindings} findings)
              </span>
            </span>
          </div>
          <div className="h-2 bg-court-bg rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-700"
              style={{
                width: `${admissionRate * 100}%`,
                background: admissionRate >= 0.7
                  ? 'linear-gradient(90deg, #22c55e, #39ff14)'
                  : 'linear-gradient(90deg, #f59e0b, #ffd700)'
              }}
            />
          </div>
        </div>

        {/* Agent panels + Evidence log */}
        <div className="flex gap-4 flex-1">
          {/* Agent panels */}
          <div className="flex flex-col gap-3 w-80 shrink-0">
            {Object.entries(agents).map(([nodeId, state]) => (
              <AgentPanel key={nodeId} nodeId={nodeId} state={state} />
            ))}
          </div>

          {/* Evidence log */}
          <div className="flex-1 bg-court-surface border border-court-border rounded-xl flex flex-col overflow-hidden">
            <div className="border-b border-court-border px-4 py-3 flex items-center gap-2">
              <span className="text-xs font-mono text-court-green uppercase tracking-wider">Evidence Log</span>
              <span className="ml-auto text-xs font-mono text-court-muted">{entries.length} entries</span>
              <span className="w-2 h-2 rounded-full bg-court-green animate-pulse" />
            </div>
            <div
              ref={logRef}
              className="flex-1 overflow-y-auto p-4 space-y-1 font-mono text-xs"
              style={{ background: '#070710' }}
            >
              {entries.length === 0 && (
                <p className="text-court-muted terminal-cursor">Awaiting investigation start</p>
              )}
              {entries.map((entry, i) => (
                <LogLine key={entry.id || i} entry={entry} formatTime={formatTime} />
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function AgentPanel({ nodeId, state }: { nodeId: string, state: AgentState }) {
  const LABELS: Record<string, string> = {
    investigator:    'INVESTIGATOR',
    challenger:      'CHALLENGER',
    judge:           'JUDGE',
    self_correction: 'SELF-CORRECT',
  }
  const color = NODE_COLORS[nodeId] || 'text-court-text'
  const icon = NODE_ICONS[nodeId]

  const statusDot = state.status === 'active'
    ? <span className="w-2 h-2 rounded-full bg-court-cyan animate-pulse" />
    : state.status === 'complete'
    ? <span className="w-2 h-2 rounded-full bg-court-admitted" />
    : <span className="w-2 h-2 rounded-full bg-court-muted/40" />

  return (
    <div className={`bg-court-surface border rounded-xl p-4 transition-all duration-300
      ${state.status === 'active' ? 'border-court-cyan/50' : 'border-court-border'}`}>
      <div className="flex items-center gap-2 mb-2">
        <span className={color}>{icon}</span>
        <span className={`font-mono text-xs font-bold ${color} tracking-wider`}>{LABELS[nodeId]}</span>
        <span className="ml-auto">{statusDot}</span>
      </div>
      <p className="text-court-text text-xs leading-relaxed line-clamp-3">{state.lastMessage}</p>
      {state.iteration > 0 && (
        <p className="text-court-muted text-xs mt-1 font-mono">iter {state.iteration}</p>
      )}
    </div>
  )
}

function LogLine({ entry, formatTime }: { entry: LogEntry, formatTime: (s: string) => string }) {
  const color = EVENT_COLORS[entry.event_type] || NODE_COLORS[entry.node] || 'text-court-text'
  const nodeColor = NODE_COLORS[entry.node] || 'text-court-muted'
  const icon = NODE_ICONS[entry.node]

  return (
    <div className="flex gap-2 items-start animate-slide-up group hover:bg-court-surface/30 rounded px-1 py-0.5">
      <span className="text-court-muted shrink-0 w-16">{formatTime(entry.ts)}</span>
      <span className={`${nodeColor} shrink-0 w-4`}>{icon}</span>
      <span className={`${color} flex-1`}>{entry.message}</span>
    </div>
  )
}
