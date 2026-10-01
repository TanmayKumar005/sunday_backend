import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import AppShell from '../components/AppShell'
import Loading from '../components/Loading'
import Notice from '../components/Notice'
import Icon from '../components/Icon'
import { api, endpoints } from '../services/api'

export default function SectionPage() {
  const { code } = useParams()
  const navigate = useNavigate()
  const [section, setSection] = useState(null)
  const [questions, setQuestions] = useState([])
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([
      api.get(endpoints.section(code)),
    ]).then(async ([data]) => {
      setSection(data)
      const qs = await api.get(endpoints.unitQuestions(data.unit_id))
      setQuestions(qs)
    }).catch(e => setError(e.message))
  }, [code])

  if (error) return <AppShell><div className="page narrow"><button className="back-button" onClick={() => navigate('/dashboard')}><Icon name="back" /> Back</button><Notice>{error}</Notice></div></AppShell>
  if (!section) return <AppShell><div className="page narrow"><Loading label="Opening section" /></div></AppShell>

  return <AppShell><div className="page narrow section-page">
    <button className="back-button" onClick={() => navigate('/dashboard')}><Icon name="back" /> All sections</button>
    <div className="content-kicker">{section.section_code} · {section.chapter}</div>
    <h1>{section.title}</h1>
    <p className="lead">{section.learning_objective}</p>
    <div className="learning-content">
      <div className="concept-label">What you’ll learn</div>
      <h2>{section.concept}</h2>
      <div className="explanation">{section.explanation}</div>
    </div>
    <div className="practice-cta"><div><span>{questions.length} questions available</span><strong>Ready to practice?</strong><p>Start with questions from this section. Your next steps will respond to your actual answers.</p></div><button className="primary-button" onClick={() => navigate(`/practice/${section.unit_id}`)}>Start practice <Icon name="arrow" size={18} /></button></div>
  </div></AppShell>
}
