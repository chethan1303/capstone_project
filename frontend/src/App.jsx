import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './context/AuthContext'
import Login from './pages/Login'
import Chat from './pages/Chat'
import Conversations from './pages/Conversations'
import AdminDashboard from './pages/AdminDashboard'
import AdminUsers from './pages/AdminUsers'
import AnalystDashboard from './pages/AnalystDashboard'
import AnalystEventReview from './pages/AnalystEventReview'
import AnalystProfileAnalysis from './pages/AnalystProfileAnalysis'
import AnalystReports from './pages/AnalystReports'

function homeForRole(role) {
  if (role === 'admin') return '/admin'
  if (role === 'analyst') return '/analyst'
  return '/chat'
}

function ProtectedRoute({ children, roles }) {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="spinner" />
      </div>
    )
  }

  if (!user) return <Navigate to="/login" replace />
  if (roles && !roles.includes(user.role)) return <Navigate to={homeForRole(user.role)} replace />
  return children
}

function PublicRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) {
    return (
      <div className="loading-screen">
        <div className="spinner" />
      </div>
    )
  }
  if (user) return <Navigate to={homeForRole(user.role)} replace />
  return children
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<PublicRoute><Login key="user" role="user" /></PublicRoute>} />
      <Route path="/admin-login" element={<PublicRoute><Login key="admin" role="admin" /></PublicRoute>} />
      <Route path="/analyst-login" element={<PublicRoute><Login key="analyst" role="analyst" /></PublicRoute>} />
      <Route path="/chat" element={<ProtectedRoute roles={['user', 'analyst', 'admin']}><Chat /></ProtectedRoute>} />
      <Route path="/conversations" element={<ProtectedRoute roles={['user', 'analyst', 'admin']}><Conversations /></ProtectedRoute>} />
      <Route path="/analyst" element={<ProtectedRoute roles={['analyst', 'admin']}><AnalystDashboard /></ProtectedRoute>} />
      <Route path="/analyst/events" element={<ProtectedRoute roles={['analyst', 'admin']}><AnalystEventReview /></ProtectedRoute>} />
      <Route path="/analyst/profiles" element={<ProtectedRoute roles={['analyst', 'admin']}><AnalystProfileAnalysis /></ProtectedRoute>} />
      <Route path="/analyst/reports" element={<ProtectedRoute roles={['analyst', 'admin']}><AnalystReports /></ProtectedRoute>} />
      <Route path="/admin" element={<ProtectedRoute roles={['admin']}><AdminDashboard /></ProtectedRoute>} />
      <Route path="/admin/users" element={<ProtectedRoute roles={['admin']}><AdminUsers /></ProtectedRoute>} />
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  )
}
