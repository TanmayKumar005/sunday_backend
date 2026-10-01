import { useState } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import Logo from './Logo'
import Icon from './Icon'
import { getLearner } from '../utils/storage'

export default function AppShell({ children }) {
  const [open, setOpen] = useState(false)
  const learner = getLearner()
  const navigate = useNavigate()

  const close = () => setOpen(false)
  const leave = () => { close(); navigate('/dashboard') }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="topbar-inner">
          <button className="mobile-menu" onClick={() => setOpen(v => !v)} aria-label="Open navigation"><Icon name="menu" /></button>
          <button className="brand-button" onClick={leave}><Logo compact /></button>
          <nav className={`nav ${open ? 'nav--open' : ''}`}>
            <NavLink to="/dashboard" onClick={close}>Learn</NavLink>
            <NavLink to="/progress" onClick={close}>Progress</NavLink>
          </nav>
          {learner && <button className="profile-chip" onClick={() => navigate('/progress')}><span className="avatar">{learner.name?.charAt(0)?.toUpperCase()}</span><span>{learner.name}</span></button>}
        </div>
      </header>
      <main>{children}</main>
      <footer className="footer"><span>S.U.N.D.A.Y.</span><span>Learning that adapts to you.</span></footer>
    </div>
  )
}
