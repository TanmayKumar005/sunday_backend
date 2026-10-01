import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import AppShell from '../components/AppShell'
import Loading from '../components/Loading'
import Notice from '../components/Notice'
import Icon from '../components/Icon'
import { api, endpoints } from '../services/api'
import { getLearner } from '../utils/storage'

export default function Dashboard() {
  const learner = getLearner()
  const navigate = useNavigate()
  const [curriculum, setCurriculum] = useState(null)
  const [summary, setSummary] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!learner) { navigate('/'); return }
    Promise.all([
      api.get(endpoints.curriculum),
      api.get(endpoints.summary(learner.id)).catch(() => null)
    ]).then(([c, s]) => { setCurriculum(c[0] || null); setSummary(s) }).catch(e => setError(e.message))
  }, [learner?.id])

  const sections = curriculum?.sections || []
  const progressByUnit = useMemo(() => new Map((summary?.weak_topics || []).map(x => [x.unit_id, x])), [summary])
  const completed = new Set((summary?.completed_topics || []).map(t => t))

  return <AppShell>
    <div className="page page--dashboard">
      <section className="welcome-row">
        <div>
          <div className="eyebrow">Your learning space</div>
          <h1>Hi, {learner?.name}. <span>Ready to learn?</span></h1>
          <p>Take it one concept at a time. S.U.N.D.A.Y. adjusts the practice around your real answers.</p>
        </div>
        {summary && <div className="summary-pill"><strong>{summary.completion_percent}%</strong><span>chapter completed</span></div>}
      </section>

      {error && <Notice onRetry={() => window.location.reload()}>{error}</Notice>}
      {!curriculum && !error && <Loading label="Loading your curriculum" />}
      {curriculum && <>
        <section className="chapter-hero">
          <div className="chapter-kicker">{curriculum.class_level} · {curriculum.subject}</div>
          <div className="chapter-title-row"><div><h2>{curriculum.chapter}</h2><p>{curriculum.book} · Chapter {curriculum.chapter_number}</p></div><div className="chapter-icon"><Icon name="book" size={28} /></div></div>
          <div className="chapter-meta"><span>{sections.length} sections</span><span>•</span><span>Real curriculum data</span></div>
        </section>

        <section className="section-list">
          <div className="section-heading"><div><h2>Your path</h2><p>Move through the chapter at your own pace.</p></div><button className="ghost-button" onClick={() => navigate('/progress')}>View progress <Icon name="arrow" size={17} /></button></div>
          <div className="section-grid">
            {sections.map((section, index) => {
              const weak = progressByUnit.get(section.unit_id)
              const done = completed.has(section.topic)
              return <button className={`section-card ${done ? 'section-card--done' : ''}`} key={section.unit_id} onClick={() => navigate(`/section/${encodeURIComponent(section.section_code)}`)}>
                <div className="section-number">{String(index + 1).padStart(2, '0')}</div>
                <div className="section-card-body"><div className="section-code">{section.section_code}</div><h3>{section.title}</h3><p>{section.learning_objective || section.topic || 'Explore this section.'}</p><div className="section-bottom"><span>{section.question_count} practice questions</span>{done ? <span className="done-label"><Icon name="check" size={14} /> Completed</span> : weak ? <span>{weak.accuracy}% accuracy</span> : <span>Not started</span>}</div></div>
                <Icon name="arrow" size={19} />
              </button>
            })}
          </div>
        </section>
      </>}
    </div>
  </AppShell>
}
