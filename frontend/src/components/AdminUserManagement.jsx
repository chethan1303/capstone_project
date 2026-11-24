import { useCallback, useEffect, useState } from 'react'
import {
  createAdminUser,
  getAdminUsers,
  setAdminUserActive,
  updateAdminUserRole,
} from '../services/api'

const emptyAccount = { username: '', email: '', password: '', role: 'analyst' }

export default function AdminUserManagement({ currentUser }) {
  const [users, setUsers] = useState([])
  const [accountForm, setAccountForm] = useState(emptyAccount)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [savingAccount, setSavingAccount] = useState(false)
  const [updatingUsername, setUpdatingUsername] = useState('')

  const loadUsers = useCallback(async () => {
    try {
      setUsers(await getAdminUsers())
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Could not load user accounts.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    let active = true
    getAdminUsers()
      .then((userList) => {
        if (active) setUsers(userList)
      })
      .catch((requestError) => {
        if (active) {
          setError(requestError.response?.data?.detail || 'Could not load user accounts.')
        }
      })
      .finally(() => {
        if (active) setLoading(false)
      })

    return () => { active = false }
  }, [])

  const createAccount = async (event) => {
    event.preventDefault()
    setSavingAccount(true)
    setError('')
    setMessage('')
    try {
      await createAdminUser(accountForm)
      setMessage(`${accountForm.role} account created.`)
      setAccountForm({ ...emptyAccount })
      await loadUsers()
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Could not create account.')
    } finally {
      setSavingAccount(false)
    }
  }

  const changeRole = async (username, role) => {
    setUpdatingUsername(username)
    setError('')
    setMessage('')
    try {
      await updateAdminUserRole(username, role)
      await loadUsers()
      setMessage(`Updated ${username}'s role.`)
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Could not update account role.')
    } finally {
      setUpdatingUsername('')
    }
  }

  const changeActiveState = async (managedUser) => {
    const nextActive = !managedUser.is_active
    if (
      !nextActive
      && !window.confirm(
        `Deactivate ${managedUser.username}? Their conversation history will be retained.`,
      )
    ) {
      return
    }

    setUpdatingUsername(managedUser.username)
    setError('')
    setMessage('')
    try {
      await setAdminUserActive(managedUser.username, nextActive)
      await loadUsers()
      setMessage(
        `${managedUser.username} ${nextActive ? 'reactivated' : 'deactivated'}.`,
      )
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Could not update account status.')
    } finally {
      setUpdatingUsername('')
    }
  }

  return (
    <section className="data-card account-management">
      <h2>User and role management</h2>
      <p className="muted">
        Create accounts, assign roles, or deactivate access. Deactivation preserves
        conversation history and can be reversed by an administrator.
      </p>
      {error && <div className="form-error" role="alert">{error}</div>}
      {message && <div className="success-message" role="status">{message}</div>}
      <form className="account-form" onSubmit={createAccount}>
        <label>Username
          <input
            value={accountForm.username}
            onChange={(event) => setAccountForm({ ...accountForm, username: event.target.value })}
            minLength={3}
            maxLength={50}
            required
          />
        </label>
        <label>Email
          <input
            type="email"
            value={accountForm.email}
            onChange={(event) => setAccountForm({ ...accountForm, email: event.target.value })}
            required
          />
        </label>
        <label>Temporary password
          <input
            type="password"
            value={accountForm.password}
            onChange={(event) => setAccountForm({ ...accountForm, password: event.target.value })}
            minLength={12}
            maxLength={72}
            required
          />
        </label>
        <label>Role
          <select
            value={accountForm.role}
            onChange={(event) => setAccountForm({ ...accountForm, role: event.target.value })}
          >
            <option value="analyst">Analyst</option>
            <option value="user">User</option>
            <option value="admin">Admin</option>
          </select>
        </label>
        <button className="primary-button" disabled={savingAccount}>
          {savingAccount ? 'Creating...' : 'Create account'}
        </button>
      </form>

      <div className="managed-user-list">
        {loading && <p className="muted">Loading user accounts...</p>}
        {!loading && users.map((managedUser) => (
          <div className="managed-user-row" key={managedUser.username}>
            <div>
              <strong>{managedUser.username}</strong>
              <span>{managedUser.email}</span>
              <span className={managedUser.is_active ? 'account-state active' : 'account-state inactive'}>
                {managedUser.is_active ? 'Active' : 'Inactive'}
              </span>
            </div>
            <select
              aria-label={`Role for ${managedUser.username}`}
              value={managedUser.role}
              disabled={
                updatingUsername === managedUser.username
                || managedUser.username === currentUser?.username
              }
              onChange={(event) => changeRole(managedUser.username, event.target.value)}
            >
              <option value="user">User</option>
              <option value="analyst">Analyst</option>
              <option value="admin">Admin</option>
            </select>
            <button
              className="secondary-button user-action-button"
              type="button"
              disabled={
                updatingUsername === managedUser.username
                || managedUser.username === currentUser?.username
              }
              onClick={() => changeActiveState(managedUser)}
            >
              {managedUser.is_active ? 'Deactivate' : 'Reactivate'}
            </button>
          </div>
        ))}
        {!loading && users.length === 0 && !error && (
          <p className="muted">No accounts found.</p>
        )}
      </div>
    </section>
  )
}
