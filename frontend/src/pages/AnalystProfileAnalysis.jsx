import { useEffect, useState } from 'react'
import { RefreshCw, UserRound } from 'lucide-react'
import AppShell from '../components/AppShell'
import { getAnalystProfiles } from '../services/api'

export default function AnalystProfileAnalysis() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = async () => {
    setLoading(true)
    setError('')
    try {
      setData(await getAnalystProfiles({ limit: 100 }))
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Could not load profile analysis.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  return (
    <AppShell>
      <div className="standard-page">
        <header className="page-header">
          <div>
            <p className="eyebrow">Analyst workspace</p>
            <h1>Profile analysis</h1>
          </div>
          <button className="secondary-button" onClick={load} disabled={loading}>
            <RefreshCw size={16} /> Refresh
          </button>
        </header>

        {error && <div className="form-error analyst-message" role="alert">{error}</div>}
        {loading ? (
          <div className="loading-card"><div className="spinner" /></div>
        ) : (
          <>
            <p className="profile-analysis-intro">
              Profiles are ordered by their most recent security event. Event counts summarize up to the latest {data?.scanned_events ?? 0} events.
            </p>
            <div className="profile-analysis-list">
              {(data?.profiles || []).map((entry) => (
                <ProfileCard entry={entry} key={entry.user_profile.id} />
              ))}
              {(data?.profiles || []).length === 0 && (
                <div className="review-empty">No user profiles are associated with recent security events.</div>
              )}
            </div>
          </>
        )}
      </div>
    </AppShell>
  )
}

function ProfileCard({ entry }) {
  const profile = entry.user_profile
  const event = entry.latest_event
  const conversation = entry.latest_conversation

  return (
    <article className="profile-analysis-card">
      <div className="profile-analysis-header">
        <div>
          <h2><UserRound size={16} /> {profile.display_name || profile.username}</h2>
          <div className="profile-meta">
            <span>{profile.role}</span>
            <span>{entry.security_event_count} recent events</span>
            <span>Last event {new Date(event.timestamp).toLocaleString()}</span>
          </div>
        </div>
        <span className={`severity ${event.severity}`}>{event.severity}</span>
      </div>

      <div className="profile-facts">
        <div><span>Username</span><strong>{profile.username}</strong></div>
        <div><span>Email</span><strong>{profile.email}</strong></div>
        <div><span>Account status</span><strong>{profile.is_active ? 'Active' : 'Inactive'}</strong></div>
        <div><span>Account created</span><strong>{new Date(profile.created_at).toLocaleDateString()}</strong></div>
      </div>

      <div className="profile-latest-event">
        <div className="profile-meta">
          <span>{event.event_type.replaceAll('_', ' ')}</span>
          <span>Session {event.session_id.slice(0, 8)}</span>
          {conversation && <span>{conversation.risk_level} risk · {conversation.detection_count} detections</span>}
        </div>
        <p>{event.details?.detection_explanation || event.details?.defense_action || 'Security event recorded for this profile.'}</p>
      </div>
    </article>
  )
}
