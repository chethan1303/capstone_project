import { NavLink } from 'react-router-dom'
import { MessageSquareText, History, ShieldCheck, LogOut, FileBarChart, Users } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

export default function AppShell({ children }) {
  const { user, logout, isAdmin, isAnalyst } = useAuth()

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark"><ShieldCheck size={20} /></div>
          <div>
            <strong>PI-EWS</strong>
            <span>Security Console</span>
          </div>
        </div>

        <nav className="nav-list">
          {(!isAnalyst || isAdmin) && (
            <>
              <NavLink to="/chat" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
                <MessageSquareText size={18} />
                Honeypot Chat
              </NavLink>
              <NavLink to="/conversations" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
                <History size={18} />
                Conversations
              </NavLink>
            </>
          )}
          {(isAnalyst || isAdmin) && (
            <NavLink to="/analyst" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
              <FileBarChart size={18} />
              Analyst Reports
            </NavLink>
          )}
          {isAdmin && (
            <>
              <NavLink to="/admin" end className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
              <ShieldCheck size={18} />
              Admin Dashboard
              </NavLink>
              <NavLink to="/admin/users" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
                <Users size={18} />
                User Management
              </NavLink>
            </>
          )}
        </nav>

        <div className="user-card">
          <div className="avatar">{user?.username?.charAt(0).toUpperCase()}</div>
          <div className="user-info">
            <strong>{user?.username}</strong>
            <span>{user?.role}</span>
          </div>
          <button className="icon-button" onClick={logout} title="Sign out" aria-label="Sign out">
            <LogOut size={17} />
          </button>
        </div>
      </aside>
      <main className="main-content">{children}</main>
    </div>
  )
}
