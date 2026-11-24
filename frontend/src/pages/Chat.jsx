import { useEffect, useRef, useState } from 'react'
import { Send, Plus, AlertTriangle, Shield, Gauge, ChevronDown } from 'lucide-react'
import AppShell from '../components/AppShell'
import { getChatHistory, sendMessage } from '../services/api'

const makeSessionId = () => crypto.randomUUID()

export default function Chat() {
  const [sessionId, setSessionId] = useState(() => localStorage.getItem('activeSession'))
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [assessment, setAssessment] = useState(null)
  const [loadingHistory, setLoadingHistory] = useState(true)
  const [riskPanelOpen, setRiskPanelOpen] = useState(false)
  const bottomRef = useRef(null)
  const messagesRef = useRef(null)
  const shouldAutoScrollRef = useRef(true)

  useEffect(() => {
    if (sessionId) {
      localStorage.setItem('activeSession', sessionId)
    } else {
      localStorage.removeItem('activeSession')
    }
  }, [sessionId])

  useEffect(() => {
    let active = true
    if (!sessionId) {
      setMessages([])
      setAssessment(null)
      setLoadingHistory(false)
      return () => { active = false }
    }

    setLoadingHistory(true)
    getChatHistory(sessionId)
      .then((history) => {
        if (!active) return
        setMessages(history)
        const latestUser = [...history].reverse().find((message) => message.role === 'user')
        if (latestUser?.risk_score_after != null) {
          setAssessment({
            risk_level: latestUser.risk_score_after >= 0.8
              ? 'critical'
              : latestUser.risk_score_after >= 0.6
                ? 'high'
                : latestUser.risk_score_after >= 0.3
                  ? 'medium'
                  : 'low',
            risk_score: latestUser.risk_score_after,
            turn_number: history.filter((message) => message.role === 'user').length,
            defense_action: latestUser.defense_action || 'allow',
            is_suspicious: latestUser.detection_result?.overall_suspicion >= 0.35,
            contributing_factors: [],
            detection_explanation: latestUser.detection_result?.explanation || '',
          })
        } else {
          setAssessment(null)
        }
        shouldAutoScrollRef.current = true
      })
      .catch((error) => {
        if (!active) return
        setMessages([])
        if (error.response?.status === 404) {
          setSessionId(null)
          setAssessment(null)
        }
      })
      .finally(() => { if (active) setLoadingHistory(false) })
    return () => { active = false }
  }, [sessionId])

  useEffect(() => {
    if (shouldAutoScrollRef.current) {
      bottomRef.current?.scrollIntoView({ block: 'end', behavior: 'smooth' })
    }
  }, [messages])

  const handleScroll = () => {
    const container = messagesRef.current
    if (!container) return
    const distanceFromBottom =
      container.scrollHeight - container.scrollTop - container.clientHeight
    shouldAutoScrollRef.current = distanceFromBottom < 120
  }

  const newConversation = () => {
    setSessionId(null)
    setMessages([])
    setAssessment(null)
    setRiskPanelOpen(false)
    setLoadingHistory(false)
  }

  const submit = async (event) => {
    event.preventDefault()
    const message = input.trim()
    if (!message || sending || loadingHistory) return

    shouldAutoScrollRef.current = true
    setSending(true)
    setMessages((current) => [...current, { role: 'user', content: message }])
    setInput('')
    try {
      const result = await sendMessage(sessionId || makeSessionId(), message)
      setSessionId(result.session_id)
      setAssessment(result)
      setMessages((current) => [...current, { role: 'assistant', content: result.response }])
    } catch (err) {
      setMessages((current) => [...current, { role: 'assistant', content: err.response?.data?.detail || 'Unable to reach the honeypot service.' }])
    } finally {
      setSending(false)
    }
  }

  const submitWithKeyboard = (event) => {
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault()
        event.currentTarget.form?.requestSubmit()
      }
  }

  return (
    <AppShell>
      <div className="chat-layout">
        <section className="chat-panel">
          <header className="page-header">
            <div>
              <p className="eyebrow">Honeypot conversation</p>
              <h1>CorpAssist</h1>
            </div>
            <div className="header-actions">
              <button
                className="secondary-button mobile-risk-button"
                onClick={() => setRiskPanelOpen((open) => !open)}
                aria-expanded={riskPanelOpen}
              >
                <Gauge size={16} /> Risk <ChevronDown size={14} />
              </button>
              <button className="secondary-button" onClick={newConversation}><Plus size={16} /> New chat</button>
            </div>
          </header>

          <div className="messages" ref={messagesRef} onScroll={handleScroll}>
            {loadingHistory && (
              <div className="history-loading"><div className="spinner" /></div>
            )}
            {!loadingHistory && messages.length === 0 && (
              <div className="empty-chat">
                <div className="brand-mark large"><Shield size={24} /></div>
                <h2>Protected workspace</h2>
                <p>Messages are analyzed for prompt injection signals before the honeypot response is generated.</p>
              </div>
            )}
            {!loadingHistory && messages.map((message, index) => (
              <div className={`message-row ${message.role}`} key={`${message.role}-${index}`}>
                <div className="message-bubble">
                  {message.content}
                  {message.timestamp && (
                    <time>{new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</time>
                  )}
                </div>
              </div>
            ))}
            {sending && (
              <div className="message-row assistant"><div className="message-bubble typing"><span /><span /><span /></div></div>
            )}
            <div ref={bottomRef} />
          </div>

          <form className="composer" onSubmit={submit}>
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={submitWithKeyboard}
              placeholder="Send a message..."
              disabled={sending || loadingHistory}
              rows={1}
              aria-label="Message"
            />
            <button className="send-button" disabled={!input.trim() || sending || loadingHistory} aria-label="Send message"><Send size={18} /></button>
          </form>
        </section>

        <aside className={`risk-panel ${riskPanelOpen ? 'open' : ''}`}>
          <div className="panel-heading">
            <Gauge size={18} />
            <h2>Risk assessment</h2>
          </div>
          {assessment ? (
            <>
              <div className={`risk-gauge ${assessment.risk_level}`}>
                <strong>{assessment.risk_score.toFixed(2)}</strong>
                <span>{assessment.risk_level}</span>
              </div>
              <dl className="risk-details">
                <div><dt>Turn</dt><dd>{assessment.turn_number}</dd></div>
                <div><dt>Defense</dt><dd>{assessment.defense_action}</dd></div>
                <div><dt>Status</dt><dd>{assessment.is_suspicious ? 'Suspicious' : 'Normal'}</dd></div>
              </dl>
              {(assessment.contributing_factors?.length > 0 || assessment.detection_explanation) && (
                <div className="signal-box">
                  <h3><AlertTriangle size={15} /> Triggered signals</h3>
                  {assessment.detection_explanation && <p>{assessment.detection_explanation}</p>}
                  {assessment.contributing_factors?.map((factor) => <span key={factor}>{factor}</span>)}
                </div>
              )}
            </>
          ) : (
            <div className="risk-empty">
              <Shield size={32} />
              <p>Risk details will appear after the next message.</p>
            </div>
          )}
        </aside>
      </div>
    </AppShell>
  )
}
