import { useEffect, useState } from 'react'
import { Activity, AlertTriangle, FileBarChart, Mail, RefreshCw, X } from 'lucide-react'
import AppShell from '../components/AppShell'
import {
  emailAnalystReport,
  getAnalystAnalytics,
  getAnalystConversationDetail,
  getAnalystConversations,
  getAnalystDashboard,
  getAnalystSecurityEvents,
} from '../services/api'

const initialReport = {
  scope: 'conversation',
  session_id: '',
  start_date: '',
  end_date: '',
  recipients: '',
  description: '',
}

export default function AnalystDashboard() {
  const [dashboard, setDashboard] = useState(null)
  const [analytics, setAnalytics] = useState(null)
  const [conversations, setConversations] = useState([])
  const [events, setEvents] = useState([])
  const [eventCount, setEventCount] = useState(0)
  const [selected, setSelected] = useState(null)
  const [report, setReport] = useState(initialReport)
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')

  const load = async () => {
    setLoading(true)
    setError('')
    try {
      const [dashboardData, analyticsData, conversationData, eventData] = await Promise.all([
        getAnalystDashboard(),
        getAnalystAnalytics(),
        getAnalystConversations({ limit: 50 }),
        getAnalystSecurityEvents({ limit: 50 }),
      ])
      setDashboard(dashboardData)
      setAnalytics(analyticsData)
      setConversations(conversationData.conversations)
      setEvents(eventData.events)
      setEventCount(eventData.total)
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Could not load analyst data.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const openDetail = async (sessionId) => {
    setError('')
    try {
      setSelected(await getAnalystConversationDetail(sessionId))
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Could not load conversation details.')
    }
  }

  const sendReport = async (event) => {
    event.preventDefault()
    setError('')
    setNotice('')
    setSending(true)
    try {
      const recipients = report.recipients.split(/[,\n;]/).map((value) => value.trim()).filter(Boolean)
      const payload = {
        scope: report.scope,
        recipients,
        description: report.description.trim(),
      }
      if (report.scope === 'conversation') {
        payload.session_id = report.session_id
      } else {
        payload.start_date = new Date(`${report.start_date}T00:00:00Z`).toISOString()
        payload.end_date = new Date(`${report.end_date}T23:59:59Z`).toISOString()
      }
      const result = await emailAnalystReport(payload)
      setNotice(`Report email sent to ${result.recipient_count} recipient(s), with ${result.conversation_count} conversation(s) attached.`)
      setReport(initialReport)
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Report could not be sent.')
    } finally {
      setSending(false)
    }
  }

  const stats = dashboard?.stats

  return (
    <AppShell>
      <div className="standard-page">
        <header className="page-header">
          <div><p className="eyebrow">Read-only investigation workspace</p><h1>Analyst Reports</h1></div>
          <button className="secondary-button" onClick={load}><RefreshCw size={16} /> Refresh</button>
        </header>

        {error && <div className="form-error analyst-message" role="alert">{error}</div>}
        {notice && <div className="success-message analyst-message" role="status">{notice}</div>}

        {loading ? (
          <div className="loading-card"><div className="spinner" /></div>
        ) : (
          <>
            <div className="stat-grid">
              <Stat icon={<FileBarChart />} label="Conversations" value={stats?.total_conversations} />
              <Stat icon={<AlertTriangle />} label="Flagged" value={stats?.flagged_sessions} />
              <Stat icon={<Activity />} label="Detection rate" value={`${((analytics?.detection_rate || 0) * 100).toFixed(1)}%`} />
              <Stat icon={<AlertTriangle />} label="Security events" value={eventCount} />
            </div>

            <div className="admin-grid analyst-grid">
              <section className="data-card">
                <h2>Investigations</h2>
                <div className="admin-table">
                  {conversations.map((conversation) => (
                    <button
                      className="admin-table-row analyst-table-row"
                      key={conversation.session_id}
                      onClick={() => openDetail(conversation.session_id)}
                    >
                      <strong>{conversation.session_id.slice(0, 8)}</strong>
                      <span>{conversation.total_messages} messages · {conversation.detection_count} detections</span>
                      <span className={`badge ${conversation.risk_level}`}>{conversation.risk_level}</span>
                      <span>{conversation.status}</span>
                    </button>
                  ))}
                  {conversations.length === 0 && <p className="muted">No conversations available.</p>}
                </div>
              </section>

              <section className="data-card">
                <h2><Mail size={16} /> Email analysis report</h2>
                <p className="muted">PDF summary and CSV message/risk data will be attached. SMTP must be configured by the administrator.</p>
                <form className="report-form" onSubmit={sendReport}>
                  <label>Report scope
                    <select
                      value={report.scope}
                      onChange={(event) => setReport({ ...report, scope: event.target.value })}
                    >
                      <option value="conversation">One conversation</option>
                      <option value="date_range">Conversations in a date range</option>
                    </select>
                  </label>

                  {report.scope === 'conversation' ? (
                    <label>Conversation
                      <select
                        value={report.session_id}
                        onChange={(event) => setReport({ ...report, session_id: event.target.value })}
                        required
                      >
                        <option value="">Select a conversation</option>
                        {conversations.map((conversation) => (
                          <option key={conversation.session_id} value={conversation.session_id}>
                            {conversation.session_id.slice(0, 8)} · {conversation.risk_level} risk · {conversation.total_messages} messages
                          </option>
                        ))}
                      </select>
                    </label>
                  ) : (
                    <div className="date-range-fields">
                      <label>From<input type="date" value={report.start_date} onChange={(event) => setReport({ ...report, start_date: event.target.value })} required /></label>
                      <label>To<input type="date" value={report.end_date} onChange={(event) => setReport({ ...report, end_date: event.target.value })} required /></label>
                    </div>
                  )}

                  <label>Report description
                    <textarea
                      value={report.description}
                      onChange={(event) => setReport({ ...report, description: event.target.value })}
                      placeholder="Summarize the purpose and context for stakeholders"
                      minLength={5}
                      maxLength={2000}
                      rows={3}
                      required
                    />
                  </label>
                  <label>Stakeholder email addresses
                    <textarea
                      value={report.recipients}
                      onChange={(event) => setReport({ ...report, recipients: event.target.value })}
                      placeholder="name@example.com, team@example.com"
                      rows={2}
                      required
                    />
                  </label>
                  <button className="primary-button" disabled={sending}>
                    <Mail size={16} /> {sending ? 'Sending report...' : 'Generate and email report'}
                  </button>
                </form>
              </section>
            </div>

            <section className="data-card analyst-events">
              <h2>Recent security events</h2>
              {events.slice(0, 20).map((event) => (
                <div className="event-row" key={event.id}>
                  <span className={`severity ${event.severity}`}>{event.severity}</span>
                  <div><strong>{event.event_type}</strong><span>{event.session_id.slice(0, 8)}</span></div>
                  <time>{new Date(event.timestamp).toLocaleString()}</time>
                </div>
              ))}
              {events.length === 0 && <p className="muted">No security events found.</p>}
            </section>
          </>
        )}

        {selected && (
          <div className="detail-overlay" role="dialog" aria-modal="true">
            <section className="detail-panel">
              <header>
                <div><p className="eyebrow">Read-only investigation</p><h2>{selected.session_id.slice(0, 8)}</h2></div>
                <button className="icon-button" onClick={() => setSelected(null)} aria-label="Close detail"><X size={18} /></button>
              </header>
              <div className="detail-summary">
                <span>Risk: <strong>{selected.risk_level}</strong></span>
                <span>Score: <strong>{selected.current_risk_score.toFixed(3)}</strong></span>
                <span>Status: <strong>{selected.status}</strong></span>
                <span>Detections: <strong>{selected.detection_count}</strong></span>
              </div>
              <div className="detail-messages">
                {selected.messages.map((message, index) => (
                  <div className={`detail-message ${message.role}`} key={`${message.role}-${index}`}>
                    <strong>{message.role}</strong>
                    <p>{message.content}</p>
                    {message.risk_score_after !== null && <span>Risk after turn: {message.risk_score_after.toFixed(3)}</span>}
                    {message.detection_result?.injection_patterns?.map((pattern) => <span key={pattern}>{pattern}</span>)}
                  </div>
                ))}
              </div>
            </section>
          </div>
        )}
      </div>
    </AppShell>
  )
}

function Stat({ icon, label, value }) {
  return (
    <article className="stat-card">
      <div className="stat-icon">{icon}</div>
      <div><span>{label}</span><strong>{value ?? 0}</strong></div>
    </article>
  )
}
