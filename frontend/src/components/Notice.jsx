import Icon from './Icon'

export default function Notice({ tone = 'error', children, onRetry }) {
  return (
    <div className={`notice notice--${tone}`}>
      <Icon name={tone === 'error' ? 'warning' : 'sparkle'} size={19} />
      <div className="notice-copy">{children}</div>
      {onRetry && <button className="text-button" onClick={onRetry}>Try again</button>}
    </div>
  )
}
