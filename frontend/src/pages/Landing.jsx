import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Logo from '../components/Logo'
import Icon from '../components/Icon'
import Loading from '../components/Loading'
import Notice from '../components/Notice'
import { api, endpoints } from '../services/api'
import { saveLearner } from '../utils/storage'

export default function Landing() {
  const [name, setName] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  async function start() {
    const trimmed = name.trim()
    if (trimmed.length < 2) { setError('Please enter your name to begin.'); return }
    setError(''); setLoading(true)
    try {
      const learner = await api.post(endpoints.createLearner, { name: trimmed, grade: 'Class 6', subject: 'Mathematics' })
      saveLearner(learner)
      navigate('/dashboard')
    } catch (e) {
      setError(e.message || 'Could not connect to S.U.N.D.A.Y.')
    } finally { setLoading(false) }
  }

  return (
    <div className="landing">
      <div className="landing-grid" aria-hidden="true"><span>½</span><span>⅓</span><span>+</span><span>¾</span><span>2/5</span><span>=</span></div>
      <header className="landing-header"><Logo /></header>
      <section className="landing-content">
        <div className="eyebrow"><Icon name="sparkle" size={15} /> Adaptive learning</div>
        <h1>Learning that<br /><em>adapts to you.</em></h1>
        <p className="landing-copy">Build confidence in Mathematics with lessons and practice that respond to how you learn.</p>
        <div className="start-panel">
          <label htmlFor="name">What should we call you?</label>
          <div className="name-input"><Icon name="user" size={19} /><input id="name" value={name} onChange={e => setName(e.target.value)} onKeyDown={e => e.key === 'Enter' && start()} placeholder="Enter your name" autoComplete="name" /></div>
          <button className="primary-button primary-button--large" onClick={start} disabled={loading}>{loading ? <Loading label="Starting" /> : <>Start learning <Icon name="arrow" size={19} /></>}</button>
          {error && <Notice>{error}</Notice>}
        </div>
        <div className="landing-note"><Icon name="lock" size={15} /> Your learning journey is built from your actual practice.</div>
      </section>
      <div className="landing-footer">Class 6 · Mathematics · Ganita Prakash · Chapter 7</div>
    </div>
  )
}
