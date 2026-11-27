import { useEffect, useState } from 'react'
import { Mail } from 'lucide-react'
import AppShell from '../components/AppShell'
import { emailAnalystReport, getAnalystConversations } from '../services/api'

const initialReport = {
  scope: 'conversation',
  session_id: '',
  start_date: '',
  end_date: '',
  recipients: '',
  description: '',
}

export default function AnalystReports() {
  const [conversations, setConversations] = useState([])
  const [report, setReport] = useState(initialReport)
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    getAnalystConversations({ limit: 200 })
      .then((result) => { if (active) setConversations(result.conversations) })
      .catch((requestError) => {
        if (active) {
          setError(requestError.response?.data?.detail || 'Could not load conversations for reporting.')
        }
      })
      .finally(() => { if (active) setLoading(false) })

    return () => { active = false }
  }, [])

  const sendReport = async (event) => {
    event.preventDefault()
    setError('')
    setNotice('')
    setSending(true)
    try {
      const recipients = report.recipients
        .split(/[,\n;]/)
        .map((value) => value.trim())
        .filter(Boolean)
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
      setNotice(
        `Report email sent to ${result.recipient_count} recipient(s), with ${result.conversation_count} conversation(s) attached.`,
      )
      setReport(initialReport)
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Report could not be sent.')
    } finally {
      setSending(false)
    }
  }

  return (
    <AppShell>
      <div className="standard-page">
        <header className="page-header">
          <div>
            <p className="eyebrow">Analyst workspace</p>
            <h1>Reports</h1>
          </div>
        </header>

        {error && <div className="form-error analyst-message" role="alert">{error}</div>}
        {notice && <div className="success-message analyst-message" role="status">{notice}</div>}

        <div className="report-page-content">
          <section className="data-card report-page-card">
            <h2><Mail size={16} /> Email analysis report</h2>
            <p className="muted">
              A PDF summary and CSV message/risk data will be attached. SMTP must be configured by the administrator.
            </p>
            {loading ? (
              <div className="loading-card"><div className="spinner" /></div>
            ) : (
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
                    <label>From
                      <input
                        type="date"
                        value={report.start_date}
                        onChange={(event) => setReport({ ...report, start_date: event.target.value })}
                        required
                      />
                    </label>
                    <label>To
                      <input
                        type="date"
                        value={report.end_date}
                        onChange={(event) => setReport({ ...report, end_date: event.target.value })}
                        required
                      />
                    </label>
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
                <button className="primary-button" disabled={sending || conversations.length === 0}>
                  <Mail size={16} /> {sending ? 'Sending report...' : 'Generate and email report'}
                </button>
                {conversations.length === 0 && (
                  <p className="muted">No conversations are available for a report.</p>
                )}
              </form>
            )}
          </section>
        </div>
      </div>
    </AppShell>
  )
}
