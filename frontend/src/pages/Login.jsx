import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ShieldCheck } from 'lucide-react'
import GoogleSignInButton from '../components/GoogleSignInButton'
import { useAuth } from '../context/AuthContext'

function getPasswordStrength(password) {
  const characterCount = Array.from(password).length
  const rules = [
    { label: 'At least 12 characters', passed: characterCount >= 12 },
    { label: 'Lowercase letter', passed: /[a-z]/.test(password) },
    { label: 'Uppercase letter', passed: /[A-Z]/.test(password) },
    { label: 'Number', passed: /\d/.test(password) },
    { label: 'Symbol', passed: /[^A-Za-z0-9]/.test(password) },
  ]
  const score = rules.filter((rule) => rule.passed).length
  const passwordBytes = new TextEncoder().encode(password).length
  const label = passwordBytes > 72
    ? 'Too long'
    : characterCount < 12
      ? 'Too short'
      : score <= 2
        ? 'Weak'
        : score === 3
          ? 'Fair'
          : score === 4
            ? 'Good'
            : 'Strong'

  return { rules, score, label, passwordBytes }
}

export default function Login({ role = 'user' }) {
  const { login, googleLogin, register } = useAuth()
  const [mode, setMode] = useState('login')
  const [form, setForm] = useState({ username: '', email: '', password: '' })
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const passwordStrength = getPasswordStrength(form.password)
  const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID

  const submit = async (event) => {
    event.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      if (mode === 'login') {
        await login(form.username, form.password, role)
      } else {
        await register(form.username, form.email, form.password)
        await login(form.username, form.password, 'user')
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to authenticate')
    } finally {
      setSubmitting(false)
    }
  }

  const submitGoogle = async (response) => {
    if (!response.credential) {
      setError('Google did not return a sign-in credential.')
      return
    }

    setError('')
    setSubmitting(true)
    try {
      await googleLogin(response.credential)
    } catch (err) {
      setError(err.response?.data?.detail || 'Unable to authenticate with Google')
    } finally {
      setSubmitting(false)
    }
  }

  const portalName = role === 'admin' ? 'Administrator' : role === 'analyst' ? 'Analyst' : 'User'

  return (
    <div className="auth-page">
      <div className="auth-panel">
        <div className="auth-brand">
          <div className="brand-mark large"><ShieldCheck size={26} /></div>
          <div>
            <h1>PI-EWS {role !== 'user' && portalName}</h1>
            <p>Prompt Injection Early Warning System</p>
          </div>
        </div>

        <div className="auth-card">
          <h2>{mode === 'login' ? `${portalName} sign in` : 'Create a user account'}</h2>
          <p>{role === 'admin'
            ? 'Sign in to manage users and the full security console.'
            : role === 'analyst'
              ? 'Sign in to investigate activity and prepare stakeholder reports.'
              : mode === 'login'
                ? 'Sign in to continue to the honeypot console.'
                : 'Register to start protected conversations.'}</p>

          {role === 'user' && (
            <div className="mode-switch">
              <button type="button" className={mode === 'login' ? 'active' : ''} onClick={() => setMode('login')}>Sign in</button>
              <button type="button" className={mode === 'register' ? 'active' : ''} onClick={() => setMode('register')}>Register</button>
            </div>
          )}

          <form onSubmit={submit}>
            <label>Username
              <input
                autoComplete="username"
                value={form.username}
                onChange={(e) => setForm({ ...form, username: e.target.value })}
                required
              />
            </label>
            {mode === 'register' && (
              <label>Email
                <input
                  type="email"
                  autoComplete="email"
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                  required
                />
              </label>
            )}
            <label>Password
              <input
                type="password"
                autoComplete={mode === 'register' ? 'new-password' : 'current-password'}
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
                minLength={mode === 'register' ? 12 : undefined}
                maxLength={mode === 'register' ? 72 : undefined}
                aria-describedby={mode === 'register' ? 'password-strength' : undefined}
                required
              />
            </label>
            {mode === 'register' && (
              <div className={`password-strength ${passwordStrength.label.toLowerCase().replace(' ', '-')}`} id="password-strength" aria-live="polite">
                <div className="password-strength-heading">
                  <span>Password strength</span>
                  <strong>{passwordStrength.label}</strong>
                </div>
                <div className="password-strength-meter" role="meter" aria-label="Password strength" aria-valuemin="0" aria-valuemax="5" aria-valuenow={passwordStrength.score}>
                  {passwordStrength.rules.map((rule, index) => (
                    <span className={index < passwordStrength.score ? 'filled' : ''} key={rule.label} />
                  ))}
                </div>
                <ul>
                  {passwordStrength.rules.map((rule) => (
                    <li className={rule.passed ? 'passed' : ''} key={rule.label}>
                      {rule.label}
                    </li>
                  ))}
                </ul>
                {passwordStrength.passwordBytes > 72 && (
                  <span className="password-limit-error">Password must be at most 72 UTF-8 bytes.</span>
                )}
              </div>
            )}
            {error && <div className="form-error" role="alert">{error}</div>}
            <button className="primary-button" disabled={submitting || (mode === 'register' && passwordStrength.passwordBytes > 72)}>
              {submitting ? 'Please wait...' : mode === 'login' ? `Sign in as ${portalName}` : 'Create account'}
            </button>
          </form>
          {role === 'user' && googleClientId && (
            <div className="google-auth">
              <span className="google-auth-divider">or continue with</span>
              <GoogleSignInButton
                onSuccess={submitGoogle}
                onError={() => setError('Google sign-in was not completed.')}
                text={mode === 'register' ? 'signup_with' : 'signin_with'}
              />
            </div>
          )}
          <div className="portal-links">
            {role !== 'admin' && <Link to="/admin-login">Admin sign in</Link>}
            {role !== 'analyst' && <Link to="/analyst-login">Analyst sign in</Link>}
            {role !== 'user' && <Link to="/login">User sign in</Link>}
          </div>
        </div>
      </div>
    </div>
  )
}
