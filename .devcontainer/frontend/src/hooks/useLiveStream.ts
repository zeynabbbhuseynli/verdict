import { useEffect, useRef, useState } from 'react'
import { LogEntry } from '../types'
import { WS_BASE } from '../api/client'

interface LiveStreamState {
  entries: LogEntry[]
  connected: boolean
  done: boolean
}

export function useLiveStream(caseId: string | null): LiveStreamState {
  const [entries, setEntries] = useState<LogEntry[]>([])
  const [connected, setConnected] = useState(false)
  const [done, setDone] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    if (!caseId) return
    setEntries([])
    setDone(false)

    const ws = new WebSocket(`${WS_BASE}/ws/cases/${caseId}/live`)
    wsRef.current = ws

    ws.onopen = () => setConnected(true)
    ws.onclose = () => { setConnected(false) }

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data)
        if (msg.type === 'ping') return
        const entry = msg as LogEntry
        setEntries(prev => [...prev, entry])
        if (entry.event_type === 'VERDICT_ISSUED') {
          setDone(true)
        }
      } catch {
        // ignore parse errors
      }
    }

    return () => {
      ws.close()
      wsRef.current = null
    }
  }, [caseId])

  return { entries, connected, done }
}
