import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import Landing from './pages/Landing'
import Dashboard from './pages/Dashboard'
import SectionPage from './pages/SectionPage'
import PracticePage from './pages/PracticePage'
import ResultPage from './pages/ResultPage'
import ProgressPage from './pages/ProgressPage'

export default function App() {
  return <BrowserRouter><Routes>
    <Route path="/" element={<Landing />} />
    <Route path="/dashboard" element={<Dashboard />} />
    <Route path="/section/:code" element={<SectionPage />} />
    <Route path="/practice/:unitId" element={<PracticePage />} />
    <Route path="/result/:assessmentId" element={<ResultPage />} />
    <Route path="/progress" element={<ProgressPage />} />
    <Route path="*" element={<Navigate to="/" replace />} />
  </Routes></BrowserRouter>
}
