import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import AppShell from '../components/AppShell'
import Loading from '../components/Loading'
import Notice from '../components/Notice'
import Icon from '../components/Icon'
import { api, endpoints } from '../services/api'
import { getLearner } from '../utils/storage'

export default function ProgressPage() {
  const learner = getLearner(); const navigate = useNavigate(); const [summary, setSummary] = useState(null); const [topics, setTopics] = useState(null); const [error, setError] = useState('')
  useEffect(() => { if (!learner) { navigate('/'); return } Promise.all([api.get(endpoints.summary(learner.id)), api.get(endpoints.progress(learner.id))]).then(([s,p]) => { setSummary(s); setTopics(p.topics || []) }).catch(e => setError(e.message)) }, [learner?.id])
  if (!learner) return null
  if (error) return <AppShell><div className="page narrow"><Notice>{error}</Notice></div></AppShell>
  if (!summary) return <AppShell><div className="page narrow"><Loading label="Loading your progress" /></div></AppShell>
  return <AppShell><div className="page progress-page">
    <div className="page-heading"><div><div className="eyebrow">Your journey</div><h1>Progress</h1><p>Everything here comes from your actual practice.</p></div><button className="ghost-button" onClick={() => navigate('/dashboard')}><Icon name="back" size={17} /> Learning path</button></div>
    <section className="progress-overview"><div className="completion-ring" style={{ '--progress': `${Math.min(100, Math.max(0, summary.completion_percent))}%` }}><div><strong>{summary.completion_percent}%</strong><span>complete</span></div></div><div className="progress-stats"><div><span>Questions</span><strong>{summary.questions_attempted}</strong></div><div><span>Correct</span><strong>{summary.questions_correct}</strong></div><div><span>Accuracy</span><strong>{summary.accuracy}%</strong></div><div><span>Mastery</span><strong>{summary.mastery_level || '—'}</strong></div></div></section>
    <section className="progress-topics"><div className="section-heading"><div><h2>Section progress</h2><p>Topics become complete only when the backend records the required practice.</p></div></div>{topics.length === 0 ? <div className="empty-state"><Icon name="book" size={24} /><strong>Your path starts here.</strong><p>Complete some practice to see section-level progress.</p><button className="primary-button" onClick={() => navigate('/dashboard')}>Start learning</button></div> : <div className="topic-table">{topics.map(t => <div className="topic-row" key={t.unit_id}><div><span>{t.section_code || 'Section'}</span><strong>{t.topic || 'Fractions'}</strong></div><div className="topic-bar"><span style={{ width: `${Math.min(100, Math.max(0, t.accuracy))}%` }} /></div><div className="topic-value">{t.accuracy}%</div><div className="topic-status">{t.completed ? <><Icon name="check" size={15} /> Complete</> : `${t.questions_attempted} attempted`}</div></div>)}</div>}</section>
    {summary.recommended_topic && <section className="recommendation-line"><Icon name="target" size={20} /><div><span>Next suggested topic</span><strong>{summary.recommended_topic.title}</strong><p>{summary.reason}</p></div></section>}
  </div></AppShell>
}
