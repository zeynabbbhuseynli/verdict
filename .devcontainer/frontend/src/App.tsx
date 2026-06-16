import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Upload from './pages/Upload'
import Courtroom from './pages/Courtroom'
import Verdict from './pages/Verdict'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Upload />} />
        <Route path="/courtroom/:caseId" element={<Courtroom />} />
        <Route path="/verdict/:caseId" element={<Verdict />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
