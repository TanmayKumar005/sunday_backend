import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import AppShell from '../components/AppShell'
import Loading from '../components/Loading'
import Notice from '../components/Notice'
import Icon from '../components/Icon'
import { api, endpoints } from '../services/api'
import { getLearner } from '../utils/storage'

function formatTime(seconds) { return `${Math.max(0, Math.floor(seconds))}s` }

export default function PracticePage() {
  const { unitId } = useParams()
  const learner = getLearner()
  const navigate = useNavigate()
  const [assessment, setAssessment] = useState(null)
  const [questions, setQuestions] = useState([])
  const [index, setIndex] = useState(0)
  const [selected, setSelected] = useState('')
  const [numeric, setNumeric] = useState('')
  const [submitted, setSubmitted] = useState(null)
  const [decision, setDecision] = useState(null)
  const [scaffold, setScaffold] = useState(null)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const startedAt = useRef(Date.now())

  useEffect(() => {
    if (!learner) { navigate('/'); return }
    api.post(endpoints.startAssessment, { learner_id: learner.id, unit_id: Number(unitId) }).then(async a => {
      const qs = await Promise.all(a.questions.map(id => api.get(endpoints.question(id))))
      setAssessment(a); setQuestions(qs.filter(q => q.unit_id === Number(unitId))); setLoading(false)
    }).catch(e => { setError(e.message); setLoading(false) })
  }, [learner?.id, unitId])

  const question = questions[index]
  const answer = question?.question_type === 'MCQ' || question?.options?.length ? selected : numeric
  const isLast = index === questions.length - 1

  function resetQuestion() { setSelected(''); setNumeric(''); setSubmitted(null); setDecision(null); setScaffold(null); startedAt.current = Date.now() }

  async function submit() {
    if (!question || !answer.trim()) return
    setSubmitting(true); setError('')
    try {
      const response = await api.post(endpoints.answer(assessment.assessment_id), { question_id: question.id, answer, response_time_seconds: (Date.now() - startedAt.current) / 1000 })
      setSubmitted(response)
      const d = await api.post(endpoints.evaluate, { assessment_id: assessment.assessment_id, question_id: question.id })
      setDecision(d)
    } catch (e) { setError(e.message) } finally { setSubmitting(false) }
  }

  async function showScaffold() {
    try { setScaffold(await api.post(endpoints.scaffold, { assessment_id: assessment.assessment_id, question_id: question.id })) } catch (e) { setError(e.message) }
  }

  async function finishBaseline() {
    navigate(`/result/${assessment.assessment_id}`)
  }

  async function nextAdaptive() {
    setSubmitting(true)
    try {
      const next = await api.post(endpoints.nextQuestion, { assessment_id: assessment.assessment_id, question_id: question.id })
      if (next.recommended_question && next.next_assessment_id) {
        setAssessment({ ...assessment, assessment_id: next.next_assessment_id, questions: [next.recommended_question.id], assessment_type: 'Adaptive' })
        setQuestions([next.recommended_question]); setIndex(0); resetQuestion();
      } else { navigate(`/result/${assessment.assessment_id}`) }
    } catch (e) { setError(e.message) } finally { setSubmitting(false) }
  }

  if (loading) return <AppShell><div className="page narrow"><Loading label="Preparing your practice" /></div></AppShell>
  if (error && !question) return <AppShell><div className="page narrow"><Notice>{error}</Notice></div></AppShell>
  if (!question) return <AppShell><div className="page narrow"><Notice tone="success">There are no questions available for this section yet.</Notice></div></AppShell>

  return <AppShell><div className="page practice-page">
    <div className="practice-top"><button className="back-button" onClick={() => navigate('/dashboard')}><Icon name="back" /> Leave practice</button><span className="practice-type">{assessment.assessment_type === 'Adaptive' ? 'Adaptive practice' : 'Practice'} · {index + 1}{questions.length > 1 ? ` / ${questions.length}` : ''}</span></div>
    {error && <Notice>{error}</Notice>}
    <div className="question-layout">
      <section className="question-card">
        <div className="question-meta"><span>{question.topic || 'Fractions'}</span><span className="difficulty-dot">{question.difficulty}</span></div>
        <h1>{question.question_text}</h1>
        {question.options?.length > 0 ? <div className="answer-options">{question.options.map(option => <button key={option} disabled={submitted !== null} className={`answer-option ${selected === option ? 'selected' : ''} ${submitted && selected === option ? (submitted.correct ? 'correct' : 'incorrect') : ''}`} onClick={() => setSelected(option)}><span className="option-marker">{String.fromCharCode(65 + question.options.indexOf(option))}</span><span>{option}</span>{submitted && selected === option && <Icon name={submitted.correct ? 'check' : 'close'} size={19} />}</button>)}</div> : <div className="numeric-answer"><label>Your answer</label><input inputMode="decimal" value={numeric} disabled={submitted !== null} onChange={e => setNumeric(e.target.value)} placeholder="Type your answer" /></div>}
        {!submitted ? <button className="primary-button primary-button--submit" disabled={!answer.trim() || submitting} onClick={submit}>{submitting ? <Loading label="Checking" /> : <>Check answer <Icon name="arrow" size={18} /></>}</button> : <div className={`feedback ${submitted.correct ? 'feedback--correct' : 'feedback--wrong'}`}><div className="feedback-title"><span className="feedback-icon"><Icon name={submitted.correct ? 'check' : 'lightbulb'} size={18} /></span>{submitted.correct ? 'Nice work.' : 'Let’s work through it.'}</div>{decision?.reason && <p>{submitted.correct ? decision.reason : 'A hint can help you get unstuck before seeing the full explanation.'}</p>}{!submitted.correct && <button className="secondary-button" onClick={showScaffold}><Icon name="lightbulb" size={17} /> {scaffold ? 'Show next step' : 'Get a hint'}</button>}{scaffold && <div className="scaffold"><div className="scaffold-label">{scaffold.title}</div><p>{scaffold.content}</p>{scaffold.steps?.length > 0 && <ol>{scaffold.steps.map(step => <li key={step}>{step}</li>)}</ol>}{scaffold.reveals_answer && <div className="answer-reveal">Answer: {scaffold.correct_answer}</div>}</div>}</div>}
      </section>
      <aside className="practice-side"><div className="side-note"><Icon name="target" size={20} /><div><strong>Your next step is based on your answers.</strong><p>S.U.N.D.A.Y. adapts practice from the learning data it actually receives.</p></div></div><div className="monitor-placeholder"><Icon name="sparkle" size={18} /><span>Learning support</span><p>Webcam-based learning signals can be connected here later. No monitoring is active yet.</p></div></aside>
    </div>
    {submitted && <div className="next-bar">{!isLast && assessment.assessment_type !== 'Adaptive' ? <button className="primary-button" onClick={() => { setIndex(i => i + 1); resetQuestion() }}>Next question <Icon name="arrow" size={18} /></button> : <><button className="ghost-button" onClick={finishBaseline}>See result <Icon name="arrow" size={18} /></button><button className="primary-button" onClick={nextAdaptive} disabled={submitting}>Continue adaptively <Icon name="sparkle" size={17} /></button></>}</div>}
  </div></AppShell>
}
