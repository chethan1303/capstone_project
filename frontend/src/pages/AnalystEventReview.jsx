import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { AlertTriangle, RefreshCw, ShieldAlert } from 'lucide-react'
import AppShell from '../components/AppShell'
import {
  getAnalystFlaggedConversations,
  getAnalystSecurityEvents,
} from '../services/api'

export default function AnalystEventReview() {
  const [searchParams] = useSearchParams()
  const view = searchParams.get('view') === 'flagged' ? 'flagged' : 'security'
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [refreshVersion, setRefreshVersion] = useState(0)

  useEffect(() => {
    let active = true
    setLoading(true)
    setError('')
    const request = view === 'flagged'
      ? getAnalystFlaggedConversations({ limit: 100 })
      : getAnalystSecurityEvents({ limit: 100 })

    request
      .then((result) => { if (active) setData(result) })
      .catch((requestError) => {
        if (active) {
          setError(requestError.response?.data?.detail || 'Could not load event review data.')
        }
      })
      .finally(() => { if (active) setLoading(false) })

    return () => { active = false }
  }, [view, refreshVersion])

  const records = view === 'flagged'
    ? data?.conversations || []
    : data?.events || []

  return (
    <AppShell>
      <div className="standard-page">
        <header className="page-header">
          <div>
            <p className="eyebrow">Analyst workspace</p>
            <h1>{view === 'flagged' ? 'Flagged conversations' : 'Security event review'}</h1>
          </div>
          <span className="badge">{data?.total ?? 0} records</span>
        </header>

        <div className="analyst-review-content">
          <nav className="analyst-review-tabs" aria-label="Event review filters">
            <Link to="/analyst/events">Security events</Link>
            <Link to="/analyst/events?view=flagged">Flagged conversations</Link>
          </nav>

          {error && <div className="form-error analyst-message" role="alert">{error}</div>}
          {loading ? (
            <div className="loading-card"><div className="spinner" /></div>
          ) : (
            <>
              <div className="review-toolbar">
                <p className="muted">
                  {view === 'flagged'
                    ? 'Flagged sessions include associated account profiles and their latest security events.'
                    : 'Each event is linked to its conversation risk summary and the account that started it.'}
                </p>
                <button className="secondary-button" onClick={() => setRefreshVersion((version) => version + 1)}>
                  <RefreshCw size={16} /> Refresh
                </button>
              </div>
              <div className="analyst-review-list">
                {view === 'flagged'
                  ? records.map((conversation) => (
                    <FlaggedConversation key={conversation.session_id} conversation={conversation} />
                  ))
                  : records.map((event) => <SecurityEventCard key={event.id} event={event} />)}
                {records.length === 0 && (
                  <div className="review-empty">
                    {view === 'flagged'
                      ? 'No flagged conversations were found.'
                      : 'No security events were found.'}
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </AppShell>
  )
}

function ProfileSummary({ profile }) {
  return (
    <div className="review-profile">
      <div><span>Profile</span><strong>{profile?.display_name || profile?.username || 'Unknown user'}</strong></div>
      <div><span>Username</span><strong>{profile?.username || 'Unavailable'}</strong></div>
      <div><span>Email</span><strong>{profile?.email || 'Unavailable'}</strong></div>
      <div><span>Role</span><strong>{profile?.role || 'Unknown'}</strong></div>
      <div><span>Account</span><strong>{profile ? (profile.is_active ? 'Active' : 'Inactive') : 'Unavailable'}</strong></div>
      <div><span>Joined</span><strong>{profile?.created_at ? new Date(profile.created_at).toLocaleDateString() : 'Unavailable'}</strong></div>
    </div>
  )
}

function FlaggedConversation({ conversation }) {
  return (
    <article className="review-card">
      <div className="review-card-header">
        <div>
          <h2><ShieldAlert size={16} /> Session {conversation.session_id.slice(0, 8)}</h2>
          <div className="review-meta">
            <span>Updated {new Date(conversation.updated_at).toLocaleString()}</span>
            <span>{conversation.total_messages} messages</span>
            <span>{conversation.detection_count} detections</span>
          </div>
        </div>
        <span className={`badge ${conversation.risk_level}`}>{conversation.risk_level}</span>
      </div>

      <ProfileSummary profile={conversation.user_profile} />
      <div className="review-meta">
        <span>Status: {conversation.status}</span>
        <span>Risk score: {Number(conversation.current_risk_score).toFixed(3)}</span>
      </div>

      <div className="associated-events">
        <h3><AlertTriangle size={14} /> Recent security events</h3>
        {conversation.recent_security_events.length > 0
          ? conversation.recent_security_events.map((event) => (
            <EventDetails event={event} key={event.id} />
          ))
          : <p className="muted">No security event is linked to this flagged session.</p>}
      </div>
    </article>
  )
}

function SecurityEventCard({ event }) {
  const conversation = event.conversation
  return (
    <article className="review-card">
      <div className="review-card-header">
        <div>
          <h2>{event.event_type.replaceAll('_', ' ')} · Session {event.session_id.slice(0, 8)}</h2>
          <div className="review-meta">
            <span>{new Date(event.timestamp).toLocaleString()}</span>
            {conversation && <span>{conversation.total_messages} messages</span>}
          </div>
        </div>
        <span className={`severity ${event.severity}`}>{event.severity}</span>
      </div>

      <ProfileSummary profile={event.user_profile} />
      {conversation && (
        <div className="review-meta">
          <span>Status: {conversation.status}</span>
          <span>Risk: {conversation.risk_level}</span>
          <span>Risk score: {Number(conversation.current_risk_score).toFixed(3)}</span>
          <span>Detections: {conversation.detection_count}</span>
        </div>
      )}
      <EventDetails event={event} />
    </article>
  )
}

function EventDetails({ event }) {
  return (
    <details className="event-details">
      <summary>{event.event_type.replaceAll('_', ' ')} · {event.severity} · {new Date(event.timestamp).toLocaleString()}</summary>
      <pre>{JSON.stringify(event.details || {}, null, 2)}</pre>
    </details>
  )
}
