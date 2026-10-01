import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import AppShell from '../components/AppShell'
import Loading from '../components/Loading'
import Notice from '../components/Notice'
import Icon from '../components/Icon'
import { api, endpoints } from '../services/api'

export default function ResultPage() {
  const { assessmentId } = useParams(); const navigate = useNavigate(); const [result, setResult] = useState(null); const [error, setError] = useState('')
  useEffect(() => { api.get(endpoints.result(assessmentId)).then(setResult).catch(e => setError(e.message)) }, [assessmentId])
  if (error) return <AppShell><div className="page narrow"><Notice>{error}</Notice></div></AppShell>
  if (!result) return <AppShell><div className="page narrow"><Loading label="Building your result" /></div></AppShell>
  return <AppShell><div className="page result-page">
    <div className="result-header"><div className="result-badge"><Icon name="sparkle" size={17} /> Practice complete</div><h1>Here’s what your practice tells us.</h1><p>This summary uses the answers you actually submitted.</p></div>
    <div className="result-grid"><div className="result-score"><span>Accuracy</span><strong>{result.accuracy}%</strong><small>{result.questions_answered ?? 0} of {result.total_questions ?? 0} answered</small></div><div className="result-detail"><div><span>Mastery</span><strong>{result.mastery_level || 'Not yet assessed'}</strong></div><div><span>Next difficulty</span><strong>{result.next_difficulty || '—'}</strong></div><div><span>Current state</span><strong>{result.struggle_level || '—'}</strong></div></div></div>
    {result.weak_topics?.length > 0 && <section className="result-section"><div className="section-heading"><div><h2>Topics to revisit</h2><p>These are based on your recorded answers.</p></div></div><div className="weak-list">{result.weak_topics.map(topic => <div key={topic.unit_id}><span>{topic.section_code || 'Topic'}</span><strong>{topic.topic || 'Section'}</strong><small>{topic.accuracy}% accuracy · {topic.questions_attempted} attempted</small></div>)}</div></section>}
    {result.reason && <div className="result-recommendation"><Icon name="target" size={21} /><div><span>Suggested next step</span><strong>{result.recommended_action || 'Keep practicing'}</strong><p>{result.reason}</p></div></div>}
    <div className="result-actions"><button className="primary-button" onClick={() => navigate('/dashboard')}>Back to learning <Icon name="arrow" size={18} /></button><button className="ghost-button" onClick={() => navigate('/progress')}>View progress</button></div>
  </div></AppShell>
}
