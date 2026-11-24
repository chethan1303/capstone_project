import { useCallback, useEffect, useState } from 'react'
import { Activity, AlertTriangle, ShieldCheck, MessagesSquare, RefreshCw, X } from 'lucide-react'
import { ArcElement, BarElement, CategoryScale, Chart as ChartJS, Legend, LinearScale, Tooltip } from 'chart.js'
import { Bar, Doughnut } from 'react-chartjs-2'
import AppShell from '../components/AppShell'
import {
  getAdminDashboard,
  getAnalytics,
  getAdminConversations,
  getAdminConversationDetail,
  getSecurityEvents,
} from '../services/api'

ChartJS.register(ArcElement, BarElement, CategoryScale, LinearScale, Tooltip, Legend)

export default function AdminDashboard() {
  const [dashboard, setDashboard] = useState(null)
  const [analytics, setAnalytics] = useState(null)
  const [conversations, setConversations] = useState([])
  const [events, setEvents] = useState([])
  const [selected, setSelected] = useState(null)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState('')
  const [conversationError, setConversationError] = useState('')
  const [sessionFilter, setSessionFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [riskFilter, setRiskFilter] = useState('')
  const [conversationRefresh, setConversationRefresh] = useState(0)

  const load = useCallback(async () => {
    try {
      const [dashboardData, analyticsData, eventData] = await Promise.all([
        getAdminDashboard(),
        getAnalytics(),
        getSecurityEvents({ limit: 50 }),
      ])
      setDashboard(dashboardData)
      setAnalytics(analyticsData)
      setEvents(eventData.events)
    } catch (requestError) {
      setLoadError(requestError.response?.data?.detail || 'Could not load dashboard data.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  useEffect(() => {
    let active = true
    getAdminConversations({
      limit: 50,
      session_id: sessionFilter.trim() || undefined,
      status: statusFilter || undefined,
      risk_level: riskFilter || undefined,
    })
      .then((data) => {
        if (active) setConversations(data.conversations)
      })
      .catch((requestError) => {
        if (active) {
          setConversationError(requestError.response?.data?.detail || 'Could not load conversations.')
        }
      })

    return () => { active = false }
  }, [sessionFilter, statusFilter, riskFilter, conversationRefresh])

  const openDetail = async (sessionId) => {
    setSelected(await getAdminConversationDetail(sessionId))
  }

  const stats = dashboard?.stats

  return (
    <AppShell>
      <div className="standard-page">
        <header className="page-header">
          <div><p className="eyebrow">Security monitoring</p><h1>Admin Dashboard</h1></div>
          <button
            className="secondary-button"
            onClick={() => {
              setLoading(true)
              setLoadError('')
              load()
              setConversationRefresh((refresh) => refresh + 1)
            }}
          >
            <RefreshCw size={16} /> Refresh
          </button>
        </header>

        {loading ? (
          <div className="loading-card"><div className="spinner" /></div>
        ) : (
          <>
            {loadError && <p className="form-error analyst-message" role="alert">{loadError}</p>}
            <div className="stat-grid">
              <Stat icon={<MessagesSquare />} label="Conversations" value={stats?.total_conversations} />
              <Stat icon={<ShieldCheck />} label="Flagged" value={stats?.flagged_sessions} />
              <Stat icon={<AlertTriangle />} label="Blocked" value={stats?.blocked_sessions} />
              <Stat icon={<Activity />} label="Average risk" value={stats?.average_risk_score?.toFixed(3)} />
            </div>

            <div className="admin-grid">
              <section className="data-card">
                <h2>Recent security events</h2>
                {dashboard?.recent_events?.length ? dashboard.recent_events.map((event) => (
                  <div className="event-row" key={event.id}>
                    <span className={`severity ${event.severity}`}>{event.severity}</span>
                    <div><strong>{event.event_type}</strong><span>{event.session_id.slice(0, 8)}</span></div>
                    <time>{new Date(event.timestamp).toLocaleTimeString()}</time>
                  </div>
                )) : <p className="muted">No security events recorded.</p>}
              </section>

              <section className="data-card">
                <h2>Detection analytics</h2>
                <dl className="analytics-list">
                  <div><dt>Total messages</dt><dd>{analytics?.total_messages}</dd></div>
                  <div><dt>Detections</dt><dd>{analytics?.total_detections}</dd></div>
                  <div><dt>Detection rate</dt><dd>{((analytics?.detection_rate || 0) * 100).toFixed(1)}%</dd></div>
                  {Object.entries(analytics?.risk_distribution || {}).map(([level, count]) => (
                    <div key={level}><dt>{level} risk</dt><dd>{count}</dd></div>
                  ))}
                </dl>
              </section>
            </div>

            <div className="chart-grid">
              <section className="data-card chart-card">
                <h2>Risk distribution</h2>
                <div className="chart-wrap">
                  <Doughnut
                    aria-label="Conversations by risk level"
                    data={{
                      labels: Object.keys(analytics?.risk_distribution || {}),
                      datasets: [{
                        data: Object.values(analytics?.risk_distribution || {}),
                        backgroundColor: ['#5dbe91', '#aaa251', '#c98a54', '#d36d69'],
                        borderColor: '#101816',
                        borderWidth: 3,
                      }],
                    }}
                    options={{
                      maintainAspectRatio: false,
                      plugins: { legend: { position: 'bottom', labels: { color: '#b8c5c0' } } },
                    }}
                  />
                </div>
              </section>
              <section className="data-card chart-card">
                <h2>Conversation status</h2>
                <div className="chart-wrap">
                  <Bar
                    aria-label="Conversations by status"
                    data={{
                      labels: Object.keys(analytics?.status_distribution || {}),
                      datasets: [{
                        label: 'Conversations',
                        data: Object.values(analytics?.status_distribution || {}),
                        backgroundColor: ['#5dbe91', '#aaa251', '#d36d69', '#78958a'],
                        borderRadius: 5,
                      }],
                    }}
                    options={{
                      maintainAspectRatio: false,
                      plugins: { legend: { display: false } },
                      scales: {
                        x: { ticks: { color: '#b8c5c0' }, grid: { display: false } },
                        y: { beginAtZero: true, ticks: { color: '#b8c5c0', precision: 0 }, grid: { color: '#26332f' } },
                      },
                    }}
                  />
                </div>
              </section>
            </div>

            <div className="admin-grid lower">
              <section className="data-card wide-data-card">
                <h2>All conversations</h2>
                <div className="admin-filters">
                  <label>Session ID
                    <input
                      type="search"
                      value={sessionFilter}
                      onChange={(event) => {
                        setConversationError('')
                        setSessionFilter(event.target.value)
                      }}
                      placeholder="Search session ID"
                    />
                  </label>
                  <label>Status
                    <select value={statusFilter} onChange={(event) => {
                      setConversationError('')
                      setStatusFilter(event.target.value)
                    }}>
                      <option value="">All statuses</option>
                      <option value="active">Active</option>
                      <option value="flagged">Flagged</option>
                      <option value="blocked">Blocked</option>
                      <option value="completed">Completed</option>
                    </select>
                  </label>
                  <label>Risk level
                    <select value={riskFilter} onChange={(event) => {
                      setConversationError('')
                      setRiskFilter(event.target.value)
                    }}>
                      <option value="">All risk levels</option>
                      <option value="low">Low</option>
                      <option value="medium">Medium</option>
                      <option value="high">High</option>
                      <option value="critical">Critical</option>
                    </select>
                  </label>
                </div>
                {conversationError && <p className="form-error" role="alert">{conversationError}</p>}
                <div className="admin-table">
                  {conversations.map((conversation) => (
                    <button
                      className="admin-table-row"
                      key={conversation.session_id}
                      onClick={() => openDetail(conversation.session_id)}
                    >
                      <strong>{conversation.session_id.slice(0, 8)}</strong>
                      <span>{conversation.total_messages} messages</span>
                      <span className={`badge ${conversation.risk_level}`}>{conversation.risk_level}</span>
                      <span>{conversation.status}</span>
                      <span>{conversation.user_deleted ? 'Hidden by user' : ''}</span>
                    </button>
                  ))}
                  {conversations.length === 0 && !conversationError && <p className="muted">No conversations found.</p>}
                </div>
              </section>

              <section className="data-card">
                <h2>Security events</h2>
                <div className="event-list">
                  {events.map((event) => (
                    <div className="event-row" key={event.id}>
                      <span className={`severity ${event.severity}`}>{event.severity}</span>
                      <div><strong>{event.event_type}</strong><span>{event.session_id.slice(0, 8)}</span></div>
                      <time>{new Date(event.timestamp).toLocaleString()}</time>
                    </div>
                  ))}
                  {events.length === 0 && <p className="muted">No security events found.</p>}
                </div>
              </section>
            </div>



            {selected && (
              <div className="detail-overlay" role="dialog" aria-modal="true">
                <section className="detail-panel">
                  <header>
                    <div>
                      <p className="eyebrow">Conversation detail</p>
                      <h2>{selected.session_id.slice(0, 8)}</h2>
                    </div>
                    <button className="icon-button" onClick={() => setSelected(null)} aria-label="Close detail"><X size={18} /></button>
                  </header>
                  <div className="detail-summary">
                    <span>Risk: <strong>{selected.risk_level}</strong></span>
                    <span>Score: <strong>{selected.current_risk_score.toFixed(3)}</strong></span>
                    <span>Status: <strong>{selected.status}</strong></span>
                    <span>History: <strong>{selected.user_deleted ? 'Hidden by user; data retained' : 'Visible to user'}</strong></span>
                  </div>
                  <div className="detail-messages">
                    {selected.messages.map((message, index) => (
                      <div className={`detail-message ${message.role}`} key={`${message.role}-${index}`}>
                        <strong>{message.role}</strong>
                        <p>{message.content}</p>
                        {message.risk_score_after !== null && <span>Risk after turn: {message.risk_score_after.toFixed(3)}</span>}
                      </div>
                    ))}
                  </div>
                </section>
              </div>
            )}
          </>
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
