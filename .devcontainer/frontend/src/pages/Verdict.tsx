import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { Scale, CheckCircle, XCircle, HelpCircle, AlertTriangle, ChevronRight, ArrowLeft } from 'lucide-react'
import { api } from '../api/client'
import { FinalVerdict, Finding } from '../types'

const CLASSIFICATION_STYLES: Record<string, { bg: string, border: string, text: string, label: string }> = {
  CONFIRMED_BREACH: { bg: 'bg-court-rejected/10', border: 'border-court-rejected', text: 'text-court-rejected', label: '⚠ CONFIRMED BREACH' },
  LIKELY_BREACH:    { bg: 'bg-court-deferred/10', border: 'border-court-deferred', text: 'text-court-deferred', label: '⚠ LIKELY BREACH' },
  SUSPICIOUS:       { bg: 'bg-court-gold/10',     border: 'border-court-gold',     text: 'text-court-gold',     label: '⚡ SUSPICIOUS' },
  BENIGN:           { bg: 'bg-court-admitted/10', border: 'border-court-admitted', text: 'text-court-admitted', label: '✓ BENIGN' },
}

const STATUS_STYLES: Record<string, { icon: React.ReactNode, color: string }> = {
  ADMITTED:            { icon: <CheckCircle size={14} />, color: 'text-court-admitted' },
  ADMITTED_WITH_CAVEAT:{ icon: <CheckCircle size={14} />, color: 'text-court-caveat' },
  REJECTED:            { icon: <XCircle size={14} />,     color: 'text-court-rejected' },
  DEFERRED:            { icon: <AlertTriangle size={14}/>, color: 'text-court-deferred' },
  INCONCLUSIVE:        { icon: <HelpCircle size={14} />,  color: 'text-court-muted' },
}

export default function VerdictPage() {
  const { caseId } = useParams<{ caseId: string }>()
  const [verdict, setVerdict] = useState<FinalVerdict | null>(null)
  const [findings, setFindings] = useState<Finding[]>([])
  const [loading, setLoading] = useState(true)
  const [retry, setRetry] = useState(0)

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        const [vRes, fRes] = await Promise.all([
          api.get(`/cases/${caseId}/verdict`),
          api.get(`/cases/${caseId}/findings`)
        ])
        if (!cancelled) {
          setVerdict(vRes.data)
          setFindings(fRes.data)
          setLoading(false)
        }
      } catch {
        // Retry if verdict not ready yet
        if (!cancelled && retry < 20) {
          setTimeout(() => setRetry(r => r + 1), 2000)
        }
      }
    }
    load()
    return () => { cancelled = true }
  }, [caseId, retry])

  if (loading) {
    return (
      <div className="min-h-screen bg-court-bg flex items-center justify-center">
        <div className="text-center">
          <Scale className="mx-auto text-court-gold animate-pulse mb-4" size={40} />
          <p className="text-court-gold font-mono text-lg">Court is deliberating…</p>
          <p className="text-court-muted font-mono text-sm mt-2">Verdict will appear momentarily</p>
        </div>
      </div>
    )
  }

  if (!verdict) return null

  const cls = CLASSIFICATION_STYLES[verdict.threat_classification] || CLASSIFICATION_STYLES.SUSPICIOUS
  const admittedSet = new Set(verdict.admitted_findings)
  const rejectedSet = new Set(verdict.rejected_findings)
  const inconclusiveSet = new Set(verdict.inconclusive_findings)

  const getFindingStatus = (f: Finding): string => {
    if (admittedSet.has(f.id)) return f.status === 'ADMITTED_WITH_CAVEAT' ? 'ADMITTED_WITH_CAVEAT' : 'ADMITTED'
    if (rejectedSet.has(f.id)) return 'REJECTED'
    if (inconclusiveSet.has(f.id)) return 'INCONCLUSIVE'
    return f.status
  }

  const confidenceColor = (c: number) =>
    c >= 0.8 ? 'text-court-admitted' : c >= 0.6 ? 'text-court-deferred' : 'text-court-rejected'

  return (
    <div className="min-h-screen bg-court-bg">
      {/* Header */}
      <header className="border-b border-court-border px-6 py-4 flex items-center gap-4">
        <Scale className="text-court-gold" size={20} />
        <span className="text-court-gold font-mono font-bold tracking-widest">VERDICT</span>
        <span className="text-court-muted font-mono text-sm">|</span>
        <span className="text-court-muted font-mono text-sm">Case #{caseId?.slice(0, 8).toUpperCase()}</span>
        <div className="ml-auto flex gap-3">
          <Link to="/" className="text-xs font-mono text-court-muted hover:text-court-text flex items-center gap-1 transition-colors">
            <ArrowLeft size={12} /> New Case
          </Link>
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-6 py-8 space-y-6">
        {/* Verdict Banner */}
        <div className={`${cls.bg} border-2 ${cls.border} rounded-2xl p-8 text-center`}>
          <div className={`text-4xl font-bold font-mono ${cls.text} mb-2`}>
            {cls.label}
          </div>
          <div className="flex items-center justify-center gap-6 mt-4 text-sm font-mono text-court-muted">
            <span>Confidence: <span className="text-court-text">{verdict.confidence_level}</span></span>
            <span>|</span>
            <span>Admission rate: <span className="text-court-admitted">{(verdict.admission_rate * 100).toFixed(0)}%</span>
              <span className="ml-1">({verdict.admitted_findings.length}/{findings.length} findings)</span>
            </span>
            <span>|</span>
            <span>{verdict.total_iterations} iter · {verdict.total_tools_run} tools · {verdict.duration_seconds.toFixed(1)}s</span>
          </div>
        </div>

        {/* Bench Opinion */}
        <div className="bg-court-surface border border-court-border rounded-xl p-6">
          <h2 className="text-court-gold font-mono text-sm uppercase tracking-wider mb-3 flex items-center gap-2">
            <Scale size={14} /> Bench Opinion
          </h2>
          <p className="text-court-text leading-relaxed italic">"{verdict.bench_opinion}"</p>
        </div>

        {/* Findings Table */}
        <div className="bg-court-surface border border-court-border rounded-xl overflow-hidden">
          <div className="border-b border-court-border px-6 py-4 flex items-center gap-4">
            <h2 className="text-court-text font-mono text-sm uppercase tracking-wider">Findings</h2>
            <span className="text-court-admitted text-xs font-mono">ADMITTED: {verdict.admitted_findings.length}</span>
            <span className="text-court-rejected text-xs font-mono">REJECTED: {verdict.rejected_findings.length}</span>
            <span className="text-court-muted text-xs font-mono">INCONCLUSIVE: {verdict.inconclusive_findings.length}</span>
          </div>
          <div className="divide-y divide-court-border">
            {findings.map(f => {
              const status = getFindingStatus(f)
              const s = STATUS_STYLES[status] || STATUS_STYLES.INCONCLUSIVE
              return (
                <div key={f.id}
                  className="px-6 py-4 flex items-start gap-4 hover:bg-court-bg/50 transition-colors">
                  <span className={`mt-0.5 shrink-0 ${s.color}`}>{s.icon}</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start gap-3 flex-wrap">
                      <span className="text-court-text text-sm font-medium">{f.title}</span>
                      <span className="text-court-muted text-xs font-mono shrink-0">{f.mitre_technique}</span>
                    </div>
                    {f.challenge?.argument && (
                      <p className="text-court-muted text-xs mt-1 line-clamp-1">
                        ⚔ {f.challenge.severity}: {f.challenge.argument.slice(0, 100)}…
                      </p>
                    )}
                  </div>
                  <div className="text-right shrink-0">
                    <div className={`text-sm font-mono font-bold ${confidenceColor(f.confidence)}`}>
                      {(f.confidence * 100).toFixed(0)}%
                    </div>
                    <div className={`text-xs font-mono ${s.color}`}>{status.replace('_', ' ')}</div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* Two column: containment + evidence gaps */}
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-court-surface border border-court-border rounded-xl p-6">
            <h3 className="text-court-rejected font-mono text-xs uppercase tracking-wider mb-3">
              Containment Actions
            </h3>
            <ul className="space-y-2">
              {verdict.containment_actions.map((a, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-court-text">
                  <ChevronRight size={14} className="text-court-rejected mt-0.5 shrink-0" />
                  {a}
                </li>
              ))}
              {verdict.containment_actions.length === 0 && (
                <li className="text-court-muted text-sm">No immediate containment required.</li>
              )}
            </ul>
          </div>

          <div className="bg-court-surface border border-court-border rounded-xl p-6">
            <h3 className="text-court-deferred font-mono text-xs uppercase tracking-wider mb-3">
              Evidence Gaps
            </h3>
            <ul className="space-y-2">
              {verdict.evidence_gaps.map((g, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-court-text">
                  <HelpCircle size={14} className="text-court-deferred mt-0.5 shrink-0" />
                  {g}
                </li>
              ))}
              {verdict.evidence_gaps.length === 0 && (
                <li className="text-court-muted text-sm">All significant evidence was resolved.</li>
              )}
            </ul>
          </div>
        </div>

        {/* Audit Stats */}
        <div className="bg-court-surface border border-court-border rounded-xl p-6">
          <h3 className="text-court-muted font-mono text-xs uppercase tracking-wider mb-4">Audit Trail</h3>
          <div className="grid grid-cols-4 gap-4 text-center">
            {[
              { label: 'Iterations', value: verdict.total_iterations },
              { label: 'Tools Run', value: verdict.total_tools_run },
              { label: 'Evidence Refs', value: verdict.total_evidence_refs },
              { label: 'Duration', value: `${verdict.duration_seconds.toFixed(1)}s` },
            ].map(({ label, value }) => (
              <div key={label}>
                <div className="text-2xl font-bold font-mono text-court-cyan">{value}</div>
                <div className="text-court-muted text-xs font-mono mt-1">{label}</div>
              </div>
            ))}
          </div>
          <div className="mt-4 text-center">
            <Link
              to={`/courtroom/${caseId}`}
              className="text-xs font-mono text-court-muted hover:text-court-cyan transition-colors"
            >
              ← Replay investigation log
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
