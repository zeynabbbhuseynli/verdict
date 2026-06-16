import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Scale, Upload, Zap, Shield, Eye } from 'lucide-react'
import { api } from '../api/client'

export default function UploadPage() {
  const navigate = useNavigate()
  const [title, setTitle] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const startCase = async (demoMode: boolean) => {
    setLoading(true)
    setError('')
    try {
      const caseTitle = demoMode
        ? 'Ransomware Incident — WORKSTATION01 (Demo)'
        : title.trim() || 'Untitled Case'

      const { data } = await api.post('/cases', {
        title: caseTitle,
        description: demoMode ? 'Pre-built ransomware scenario with memory dump, EVTX logs, and PCAP.' : '',
        max_iterations: 3,
        artifact_manifest: {
          has_memory_dump: true,
          has_disk_image: true,
          has_pcap: true,
          has_logs: true
        }
      })

      // Start the investigation pipeline
      await api.post(`/cases/${data.id}/start`)
      navigate(`/courtroom/${data.id}`)
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Failed to start investigation')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-court-bg flex flex-col">
      {/* Header */}
      <header className="border-b border-court-border px-8 py-5 flex items-center gap-3">
        <Scale className="text-court-gold" size={24} />
        <span className="text-court-gold font-mono font-bold text-xl tracking-widest">VERDICT</span>
        <span className="ml-auto text-court-muted text-sm font-mono">SANS "Find Evil!" Hackathon</span>
      </header>

      {/* Hero */}
      <main className="flex-1 flex flex-col items-center justify-center px-4 py-16">
        <div className="text-center mb-12">
          <div className="inline-flex items-center gap-2 text-court-cyan font-mono text-sm uppercase tracking-widest mb-6 
                          border border-court-cyan/30 rounded px-4 py-1.5">
            <span className="w-2 h-2 rounded-full bg-court-cyan animate-pulse-slow" />
            Multi-Agent Forensic Courtroom
          </div>
          <h1 className="text-5xl font-bold text-court-text mb-4 leading-tight">
            Replay the Breach.<br />
            <span className="text-court-gold">Cross-Examine the Evidence.</span>
          </h1>
          <p className="text-court-muted text-lg max-w-xl mx-auto leading-relaxed">
            Every finding is investigated, challenged, and judged before it becomes evidence.
            Not a dashboard — a trial.
          </p>
        </div>

        {/* Agent pipeline illustration */}
        <div className="flex items-center gap-2 mb-12 text-xs font-mono">
          {[
            { label: 'INVESTIGATOR', color: 'text-court-cyan', icon: '⚲' },
            { label: '→', color: 'text-court-muted', icon: '' },
            { label: 'CHALLENGER', color: 'text-court-rejected', icon: '⚔' },
            { label: '→', color: 'text-court-muted', icon: '' },
            { label: 'JUDGE', color: 'text-court-gold', icon: '⚖' },
            { label: '→', color: 'text-court-muted', icon: '' },
            { label: 'SELF-CORRECT', color: 'text-court-deferred', icon: '↻' },
            { label: '→', color: 'text-court-muted', icon: '' },
            { label: 'VERDICT', color: 'text-court-admitted', icon: '✓' },
          ].map((item, i) => (
            item.label === '→'
              ? <span key={i} className="text-court-muted">→</span>
              : <span key={i} className={`${item.color} border border-current/30 px-2 py-1 rounded`}>
                  {item.icon && <span className="mr-1">{item.icon}</span>}
                  {item.label}
                </span>
          ))}
        </div>

        {/* Case creation card */}
        <div className="w-full max-w-lg bg-court-surface border border-court-border rounded-xl p-8">
          {/* Demo button */}
          <button
            onClick={() => startCase(true)}
            disabled={loading}
            className="w-full bg-court-gold/10 hover:bg-court-gold/20 border border-court-gold/50 
                       text-court-gold font-bold py-4 px-6 rounded-lg transition-all duration-200
                       flex items-center justify-center gap-3 mb-6 group disabled:opacity-50"
          >
            <Zap size={20} className="group-hover:animate-pulse" />
            {loading ? 'Opening Court…' : 'Launch Demo Case (Ransomware)'}
          </button>

          <div className="flex items-center gap-4 mb-6">
            <div className="h-px flex-1 bg-court-border" />
            <span className="text-court-muted text-xs font-mono">OR CREATE YOUR OWN</span>
            <div className="h-px flex-1 bg-court-border" />
          </div>

          <input
            type="text"
            placeholder="Case name…"
            value={title}
            onChange={e => setTitle(e.target.value)}
            className="w-full bg-court-bg border border-court-border rounded-lg px-4 py-3 
                       text-court-text placeholder-court-muted focus:outline-none 
                       focus:border-court-cyan transition-colors mb-4"
          />

          {/* Artifact toggles (visual only for demo) */}
          <div className="grid grid-cols-2 gap-2 mb-6">
            {[
              { label: 'Memory Dump', icon: '🧠', checked: true },
              { label: 'Disk Image', icon: '💽', checked: true },
              { label: 'EVTX Logs', icon: '📋', checked: true },
              { label: 'Network PCAP', icon: '🌐', checked: true },
            ].map(item => (
              <div key={item.label}
                className="flex items-center gap-2 bg-court-bg border border-court-admitted/30 
                           rounded-lg px-3 py-2 text-sm text-court-admitted">
                <span>{item.icon}</span>
                <span className="text-xs font-mono">{item.label}</span>
                <span className="ml-auto text-xs">✓</span>
              </div>
            ))}
          </div>

          <button
            onClick={() => startCase(false)}
            disabled={loading || !title.trim()}
            className="w-full bg-court-cyan/10 hover:bg-court-cyan/20 border border-court-cyan/50 
                       text-court-cyan font-bold py-3 px-6 rounded-lg transition-all duration-200
                       flex items-center justify-center gap-2 disabled:opacity-30"
          >
            <Upload size={16} />
            Open Court →
          </button>

          {error && (
            <p className="mt-4 text-court-rejected text-sm text-center font-mono">{error}</p>
          )}
        </div>

        {/* Feature callouts */}
        <div className="grid grid-cols-3 gap-6 mt-12 max-w-2xl w-full">
          {[
            { icon: Shield, title: 'Adversarial Validation', desc: 'Every finding is attacked before admission' },
            { icon: Eye, title: 'Full Audit Trail', desc: 'Every decision is logged and replayable' },
            { icon: Scale, title: 'Self-Correcting', desc: 'Weak findings trigger additional investigation' },
          ].map(({ icon: Icon, title, desc }) => (
            <div key={title} className="text-center">
              <Icon className="mx-auto mb-2 text-court-cyan/60" size={20} />
              <div className="text-court-text text-sm font-medium">{title}</div>
              <div className="text-court-muted text-xs mt-1">{desc}</div>
            </div>
          ))}
        </div>
      </main>
    </div>
  )
}
