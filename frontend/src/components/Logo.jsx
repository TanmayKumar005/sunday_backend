import Icon from './Icon'

export default function Logo({ compact = false }) {
  return (
    <div className={`logo ${compact ? 'logo--compact' : ''}`}>
      <span className="logo-mark"><Icon name="sparkle" size={18} /></span>
      <span>S.U.N.D.A.Y.</span>
    </div>
  )
}
