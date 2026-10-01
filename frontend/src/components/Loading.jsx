export default function Loading({ label = 'Loading' }) {
  return <div className="loading-state"><span className="spinner" /> <span>{label}</span></div>
}
