import axios from 'axios'

// Same-origin (nginx proxy): VITE_API_URL unset → relative paths
// Cross-origin (Fly/Vercel): set VITE_API_URL=https://verdict-backend.fly.dev
const BASE = import.meta.env.VITE_API_URL || ''
export const api = axios.create({ baseURL: `${BASE}/api/v1` })

const wsBase = BASE
  ? BASE.replace(/^http/, 'ws')
  : `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}`
export const WS_BASE = wsBase
