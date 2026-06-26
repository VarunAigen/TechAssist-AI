/**
 * API Client — Axios instance with JWT auth interceptors.
 * Supports multi-tenant architecture.
 */

import axios from 'axios';

const API_BASE = 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
});

// Request interceptor — attach JWT token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor — handle 401s (skip for login endpoint)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const isLoginRequest = error.config?.url?.includes('/auth/login');
    if (error.response?.status === 401 && !isLoginRequest) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// ── Auth API ──────────────────────────────────────────────
export const authAPI = {
  login: (email, password) => api.post('/auth/login', { email, password }),
  registerTenant: (data) => api.post('/auth/register/tenant', data),
  register: (data) => api.post('/auth/register', data),
  getProfile: () => api.get('/auth/me'),
};

// ── Chat API ──────────────────────────────────────────────
export const chatAPI = {
  sendMessage: (question, sessionId = null) =>
    api.post('/chat', { question, session_id: sessionId }),
  rateResponse: (queryId, rating) =>
    api.post(`/chat/${queryId}/rate`, { rating }),
  getHistory: () => api.get('/chat/history'),
  getSessionMessages: (sessionId) => api.get(`/chat/session/${sessionId}`),
};

// ── Admin API ─────────────────────────────────────────────
export const adminAPI = {
  // Documents
  uploadDocument: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/admin/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  listDocuments: () => api.get('/admin/documents'),
  deleteDocument: (docId) => api.delete(`/admin/documents/${docId}`),
  replaceDocument: (docId, file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.put(`/admin/documents/${docId}/replace`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  searchDocuments: (params) => api.get('/admin/documents/search', { params }),

  // Analytics
  getAnalytics: () => api.get('/admin/analytics'),
  getUnanswered: () => api.get('/admin/unanswered'),

  // User Management
  listUsers: () => api.get('/admin/users'),
  inviteUser: (data) => api.post('/admin/users/invite', data),
  updateUser: (userId, data) => api.put(`/admin/users/${userId}`, data),

  // Audit Log
  getAuditLog: (params) => api.get('/admin/audit-log', { params }),
  exportAuditLog: (params) => api.get('/admin/audit-log/export', { params, responseType: 'blob' }),

  // Feedback Loop
  getLowRated: (params) => api.get('/admin/feedback/low-rated', { params }),
  getKnowledgeGaps: () => api.get('/admin/feedback/knowledge-gaps'),

  // Query Browser
  listQueries: (params) => api.get('/admin/queries', { params }),

  // Resolve Knowledge Gap
  resolveQuery: (queryId, resolvedAnswer) =>
    api.post(`/admin/queries/${queryId}/resolve`, { resolved_answer: resolvedAnswer }),
};

// ── Chat API (extended) ───────────────────────────────────
export const chatExportAPI = {
  exportSessionPDF: (sessionId) =>
    api.get(`/chat/session/${sessionId}/export`, { responseType: 'blob' }),
};

// ── Super Admin API ─────────────────────────────────────────
export const superadminAPI = {
  getStats: () => api.get('/superadmin/stats'),
  listTenants: () => api.get('/superadmin/tenants'),
  updateTenant: (tenantId, data) => api.put(`/superadmin/tenants/${tenantId}`, data),
};

export default api;
