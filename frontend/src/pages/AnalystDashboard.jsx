import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Activity, AlertTriangle, FileBarChart, RefreshCw, X } from 'lucide-react'
import { BarElement, CategoryScale, Chart as ChartJS, Legend, LinearScale, Tooltip } from 'chart.js'
import { Bar } from 'react-chartjs-2'
import AppShell from '../components/AppShell'
import {
  getAnalystAnalytics,
  getAnalystConversationDetail,
  getAnalystConversations,
  getAnalystDashboard,
  getAnalystSecurityEvents,
} from '../services/api'

ChartJS.register(BarElement, CategoryScale, LinearScale, Tooltip, Legend)

export default function AnalystDashboard() {
  const navigate = useNavigate()
  const [dashboard, setDashboard] = useState(null)
  const [analytics, setAnalytics] = useState(null)
  const [conversations, setConversations] = useState([])
  const [events, setEvents] = useState([])
  const [eventCount, setEventCount] = useState(0)
  const [selected, setSelected] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = async () => {
    setLoading(true)
    setError('')
    try {
      const [dashboardData, analyticsData, conversationData, eventData] = await Promise.all([
        getAnalystDashboard(),
        getAnalystAnalytics(),
        getAnalystConversations({ limit: 200 }),
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

  const stats = dashboard?.stats
  const tokenUsageConversations = [...conversations]
    .filter((conversation) => conversation.token_usage_complete && conversation.total_tokens !== null)
    .sort((a, b) => b.total_tokens - a.total_tokens)
    .slice(0, 10)
    .reverse()
  const largestConversations = [...conversations]
    .sort((a, b) => b.message_text_bytes - a.message_text_bytes)
    .slice(0, 10)
    .reverse()

  return (
    <AppShell>
      <div className="standard-page">
        <header className="page-header">
          <div><p className="eyebrow">Read-only investigation workspace</p><h1>Analyst Overview</h1></div>
          <button className="secondary-button" onClick={load}><RefreshCw size={16} /> Refresh</button>
        </header>

        {error && <div className="form-error analyst-message" role="alert">{error}</div>}
        {loading ? (
          <div className="loading-card"><div className="spinner" /></div>
        ) : (
          <>
            <div className="stat-grid">
              <Stat icon={<FileBarChart />} label="Conversations" value={stats?.total_conversations} />
              <Stat
                icon={<AlertTriangle />}
                label="Flagged conversations"
                value={stats?.flagged_sessions}
                onClick={() => navigate('/analyst/events?view=flagged')}
              />
              <Stat icon={<Activity />} label="Detection rate" value={`${((analytics?.detection_rate || 0) * 100).toFixed(1)}%`} />
              <Stat
                icon={<AlertTriangle />}
                label="Security events"
                value={eventCount}
                onClick={() => navigate('/analyst/events')}
              />
            </div>

            <div className="chart-grid">
              <section className="data-card chart-card">
                <h2>Provider-reported tokens by session</h2>
                <div className="chart-wrap">
                  {tokenUsageConversations.length > 0 ? (
                    <Bar
                      aria-label="Provider-reported LLM tokens by conversation"
                      data={{
                        labels: tokenUsageConversations.map((conversation) => conversation.session_id.slice(0, 8)),
                        datasets: [{
                          label: 'LLM tokens',
                          data: tokenUsageConversations.map((conversation) => conversation.total_tokens),
                          backgroundColor: '#5dbe91',
                          borderRadius: 5,
                        }],
                      }}
                      options={{
                        indexAxis: 'y',
                        maintainAspectRatio: false,
                        plugins: { legend: { display: false } },
                        scales: {
                          x: { beginAtZero: true, ticks: { color: '#b8c5c0', precision: 0 }, grid: { color: '#26332f' } },
                          y: { ticks: { color: '#b8c5c0' }, grid: { display: false } },
                        },
                      }}
                    />
                  ) : (
                    <p className="muted">Provider usage is not fully tracked for these conversations yet.</p>
                  )}
                </div>
              </section>

              <section className="data-card chart-card">
                <h2>Message text size by session</h2>
                <div className="chart-wrap">
                  {largestConversations.length > 0 ? (
                    <Bar
                      aria-label="UTF-8 message text size by conversation"
                      data={{
                        labels: largestConversations.map((conversation) => conversation.session_id.slice(0, 8)),
                        datasets: [{
                          label: 'Message text (KB)',
                          data: largestConversations.map((conversation) => conversation.message_text_bytes / 1024),
                          backgroundColor: '#7895d1',
                          borderRadius: 5,
                        }],
                      }}
                      options={{
                        indexAxis: 'y',
                        maintainAspectRatio: false,
                        plugins: { legend: { display: false } },
                        scales: {
                          x: { beginAtZero: true, ticks: { color: '#b8c5c0' }, grid: { color: '#26332f' } },
                          y: { ticks: { color: '#b8c5c0' }, grid: { display: false } },
                        },
                      }}
                    />
                  ) : (
                    <p className="muted">No conversation text has been recorded yet.</p>
                  )}
                </div>
              </section>
            </div>

            <div className="admin-grid analyst-grid analyst-overview-grid">
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
                      <span>
                        {conversation.total_messages} messages · {conversation.detection_count} detections ·{' '}
                        {formatTokens(conversation)} · {formatBytes(conversation.message_text_bytes)}
                      </span>
                      <span className={`badge ${conversation.risk_level}`}>{conversation.risk_level}</span>
                      <span>{conversation.status}</span>
                    </button>
                  ))}
                  {conversations.length === 0 && <p className="muted">No conversations available.</p>}
                </div>
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
                <span>Prompt tokens: <strong>{selected.prompt_tokens?.toLocaleString() ?? 'Not tracked'}</strong></span>
                <span>Completion tokens: <strong>{selected.completion_tokens?.toLocaleString() ?? 'Not tracked'}</strong></span>
                <span>Total tokens: <strong>{formatTokens(selected)}</strong></span>
                <span>Message text size: <strong>{formatBytes(selected.message_text_bytes)}</strong></span>
              </div>
              <div className="detail-messages">
                {selected.messages.map((message, index) => (
                  <div className={`detail-message ${message.role}`} key={`${message.role}-${index}`}>
                    <strong>{message.role}</strong>
                    <p>{message.content}</p>
                    {message.risk_score_after !== null && <span>Risk after turn: {message.risk_score_after.toFixed(3)}</span>}
                    {message.detection_result?.injection_patterns?.map((pattern) => <span key={pattern}>{pattern}</span>)}
                    {(message.prompt_tokens !== null && message.prompt_tokens !== undefined)
                      || (message.completion_tokens !== null && message.completion_tokens !== undefined) ? (
                      <span>
                        LLM usage: {message.prompt_tokens?.toLocaleString() ?? 'Not tracked'} prompt +{' '}
                        {message.completion_tokens?.toLocaleString() ?? 'Not tracked'} completion tokens
                      </span>
                    ) : null}
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

function Stat({ icon, label, value, onClick }) {
  const content = (
    <>
      <div className="stat-icon">{icon}</div>
      <div><span>{label}</span><strong>{value ?? 0}</strong></div>
    </>
  )

  if (onClick) {
    return <button className="stat-card stat-card-button" onClick={onClick}>{content}</button>
  }

  return (
    <article className="stat-card">
      {content}
    </article>
  )
}

function formatTokens(conversation) {
  if (!conversation.token_usage_complete || conversation.total_tokens === null) {
    return 'Tokens not fully tracked'
  }
  return `${conversation.total_tokens.toLocaleString()} tokens`
}

function formatBytes(bytes = 0) {
  if (bytes < 1024) return `${bytes} B`
  return `${(bytes / 1024).toFixed(1)} KB`
}
