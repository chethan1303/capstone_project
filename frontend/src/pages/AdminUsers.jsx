import AppShell from '../components/AppShell'
import AdminUserManagement from '../components/AdminUserManagement'
import { useAuth } from '../context/AuthContext'

export default function AdminUsers() {
  const { user } = useAuth()

  return (
    <AppShell>
      <div className="standard-page">
        <header className="page-header">
          <div>
            <p className="eyebrow">Administration</p>
            <h1>User and role management</h1>
          </div>
        </header>
        <AdminUserManagement currentUser={user} />
      </div>
    </AppShell>
  )
}
