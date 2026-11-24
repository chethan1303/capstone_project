import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Trash2, MessageSquare, ArrowRight } from 'lucide-react'
import AppShell from '../components/AppShell'
import { getConversations, deleteConversation } from '../services/api'

export default function Conversations() {
  const [conversations, setConversations] = useState([])
  const [loading, setLoading] = useState(true)
  const [deletingSession, setDeletingSession] = useState(null)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  const load = async () => {
    setLoading(true)
    try {
      setConversations(await getConversations())
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const remove = async (sessionId) => {
    const confirmed = window.confirm(
      'Remove this chat from your history? Its messages and security analysis will be retained for administrators.',
    )
    if (!confirmed) return

    setError('')
    setDeletingSession(sessionId)
    try {
      await deleteConversation(sessionId)
      setConversations((current) => current.filter((item) => item.session_id !== sessionId))
      if (localStorage.getItem('activeSession') === sessionId) {
        localStorage.removeItem('activeSession')
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not remove this conversation. Please try again.')
    } finally {
      setDeletingSession(null)
    }
  }

  const open = (sessionId) => {
    localStorage.setItem('activeSession', sessionId)
    navigate('/chat')
  }

  return (
    <AppShell>
      <div className="standard-page">
        <header className="page-header">
          <div><p className="eyebrow">Session history</p><h1>Conversations</h1></div>
        </header>

        <p className="history-retention-note">
          Removing a chat hides it from your history. Its messages, risk analysis, and security events remain stored for administrators.
        </p>
        {error && <div className="form-error conversation-error" role="alert">{error}</div>}

        {loading ? (
          <div className="loading-card"><div className="spinner" /></div>
        ) : conversations.length === 0 ? (
          <div className="empty-state"><MessageSquare size={34} /><h2>No conversations yet</h2></div>
        ) : (
          <div className="conversation-list">
            {conversations.map((conversation) => (
              <article className="conversation-card" key={conversation.session_id}>
                <div className={`status-dot ${conversation.risk_level}`} />
                <div className="conversation-main">
                  <strong>Session {conversation.session_id.slice(0, 8)}</strong>
                  <span>{conversation.total_messages} messages · Updated {new Date(conversation.updated_at).toLocaleString()}</span>
                </div>
                <span className={`badge ${conversation.risk_level}`}>{conversation.risk_level}</span>
                <button className="icon-button" onClick={() => open(conversation.session_id)} title="Open"><ArrowRight size={17} /></button>
                <button
                  className="icon-button danger"
                  onClick={() => remove(conversation.session_id)}
                  title="Remove from my history"
                  aria-label={`Remove session ${conversation.session_id.slice(0, 8)} from my history`}
                  disabled={deletingSession === conversation.session_id}
                >
                  {deletingSession === conversation.session_id ? <span className="mini-spinner" /> : <Trash2 size={17} />}
                </button>
              </article>
            ))}
          </div>
        )}
      </div>
    </AppShell>
  )
}
