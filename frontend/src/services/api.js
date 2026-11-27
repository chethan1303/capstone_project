import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor — attach JWT token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor — redirect to login on 401
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      const requestUrl = error.config?.url || '';
      if (
        requestUrl.endsWith('/auth/login')
        || requestUrl.endsWith('/auth/admin/login')
        || requestUrl.endsWith('/auth/analyst/login')
        || requestUrl.endsWith('/auth/google')
      ) {
        return Promise.reject(error);
      }

      localStorage.removeItem('token');
      localStorage.removeItem('user');
      const path = window.location.pathname;
      const loginPath = path.startsWith('/admin')
        ? '/admin-login'
        : path.startsWith('/analyst')
          ? '/analyst-login'
          : '/login';
      if (path !== loginPath) {
        window.location.href = loginPath;
      }
    }
    return Promise.reject(error);
  }
);

// ─── Auth ────────────────────────────────────────────────────────────────────

export async function login(username, password, role = 'user') {
  const formData = new URLSearchParams();
  formData.append('username', username);
  formData.append('password', password);
  const endpoint = role === 'admin'
    ? '/auth/admin/login'
    : role === 'analyst'
      ? '/auth/analyst/login'
      : '/auth/login';
  const response = await api.post(endpoint, formData, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  });
  return response.data;
}

export async function googleLogin(credential) {
  const response = await api.post('/auth/google', { credential });
  return response.data;
}

export async function register(username, email, password) {
  const response = await api.post('/auth/register', { username, email, password });
  return response.data;
}

export async function getMe() {
  const response = await api.get('/auth/me');
  return response.data;
}

// ─── Chat ────────────────────────────────────────────────────────────────────

export async function sendMessage(sessionId, message) {
  const response = await api.post('/chat', { session_id: sessionId, message });
  return response.data;
}

export async function getChatHistory(sessionId) {
  const response = await api.get(`/chat/${sessionId}/history`);
  return response.data;
}

// ─── Conversations ───────────────────────────────────────────────────────────

export async function getConversations() {
  const response = await api.get('/conversations');
  return response.data;
}

export async function deleteConversation(sessionId) {
  const response = await api.delete(`/conversations/${sessionId}`);
  return response.data;
}

// ─── Admin ───────────────────────────────────────────────────────────────────

export async function getAdminDashboard() {
  const response = await api.get('/admin/dashboard');
  return response.data;
}

export async function getAdminConversations(params = {}) {
  const response = await api.get('/admin/conversations', { params });
  return response.data;
}

export async function getAdminConversationDetail(sessionId) {
  const response = await api.get(`/admin/conversations/${sessionId}`);
  return response.data;
}

export async function getSecurityEvents(params = {}) {
  const response = await api.get('/admin/security-events', { params });
  return response.data;
}

export async function getAnalytics() {
  const response = await api.get('/admin/analytics');
  return response.data;
}

export async function getAdminUsers() {
  const response = await api.get('/admin/users');
  return response.data;
}

export async function createAdminUser(user) {
  const response = await api.post('/admin/users', user);
  return response.data;
}

export async function updateAdminUserRole(username, role) {
  const response = await api.patch(`/admin/users/${encodeURIComponent(username)}/role`, { role });
  return response.data;
}

export async function setAdminUserActive(username, isActive) {
  const encodedUsername = encodeURIComponent(username);
  const response = isActive
    ? await api.patch(`/admin/users/${encodedUsername}/active`, { is_active: true })
    : await api.delete(`/admin/users/${encodedUsername}`);
  return response.data;
}

// ─── Analyst reports ─────────────────────────────────────────────────────────

export async function getAnalystDashboard() {
  const response = await api.get('/analyst/dashboard');
  return response.data;
}

export async function getAnalystConversations(params = {}) {
  const response = await api.get('/analyst/conversations', { params });
  return response.data;
}

export async function getAnalystConversationDetail(sessionId) {
  const response = await api.get(`/analyst/conversations/${sessionId}`);
  return response.data;
}

export async function getAnalystSecurityEvents(params = {}) {
  const response = await api.get('/analyst/security-events', { params });
  return response.data;
}

export async function getAnalystFlaggedConversations(params = {}) {
  const response = await api.get('/analyst/flagged-conversations', { params });
  return response.data;
}

export async function getAnalystProfiles(params = {}) {
  const response = await api.get('/analyst/profiles', { params });
  return response.data;
}

export async function getAnalystAnalytics() {
  const response = await api.get('/analyst/analytics');
  return response.data;
}

export async function emailAnalystReport(report) {
  const response = await api.post('/analyst/reports/email', report);
  return response.data;
}

export default api;
