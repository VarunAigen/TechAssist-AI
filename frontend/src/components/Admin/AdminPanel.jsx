/**
 * AdminPanel — Document management, analytics, user management, audit log, feedback.
 * Phase 4 — Compliance & Advanced Features
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { adminAPI } from '../../api/client';
import {
  Upload, FileText, BarChart3, AlertCircle,
  Trash2, RefreshCw, Database, MessageSquare,
  TrendingUp, FileQuestion, Users, UserPlus, Shield, Check, X,
  Search, Download, ClipboardList, ThumbsDown, Eye, ChevronLeft, ChevronRight,
  Replace, Filter
} from 'lucide-react';
import './AdminPanel.css';

export default function AdminPanel() {
  const [analytics, setAnalytics] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [unanswered, setUnanswered] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);
  const [dragging, setDragging] = useState(false);
  const fileInputRef = useRef(null);

  // User Management State
  const [activeTab, setActiveTab] = useState('overview');
  const [users, setUsers] = useState([]);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteName, setInviteName] = useState('');
  const [invitePassword, setInvitePassword] = useState('');
  const [inviteRole, setInviteRole] = useState('bd_rep');
  const [inviteError, setInviteError] = useState('');
  const [inviteSuccess, setInviteSuccess] = useState('');
  const [isInviteModalOpen, setIsInviteModalOpen] = useState(false);

  // Audit Log State
  const [auditLogs, setAuditLogs] = useState([]);
  const [auditTotal, setAuditTotal] = useState(0);
  const [auditPage, setAuditPage] = useState(1);
  const [auditFilter, setAuditFilter] = useState('');

  // Feedback State
  const [lowRated, setLowRated] = useState([]);
  const [lowRatedTotal, setLowRatedTotal] = useState(0);
  const [lowRatedPage, setLowRatedPage] = useState(1);
  const [knowledgeGaps, setKnowledgeGaps] = useState(null);

  // Document search
  const [docSearch, setDocSearch] = useState('');

  // Replace document
  const [replacingDocId, setReplacingDocId] = useState(null);
  const replaceInputRef = useRef(null);

  // Resolve Knowledge Gap State
  const [resolvingQuery, setResolvingQuery] = useState(null);
  const [resolutionAnswer, setResolutionAnswer] = useState('');
  const [resolvingError, setResolvingError] = useState('');
  const [resolvingSuccess, setResolvingSuccess] = useState('');
  const [isResolvingSubmitting, setIsResolvingSubmitting] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadUsers = async () => {
    try {
      const res = await adminAPI.listUsers();
      setUsers(res.data);
    } catch (err) {
      console.error('Failed to load users:', err);
    }
  };

  const loadAuditLogs = useCallback(async () => {
    try {
      const params = { page: auditPage, limit: 20 };
      if (auditFilter) params.action = auditFilter;
      const res = await adminAPI.getAuditLog(params);
      setAuditLogs(res.data.logs);
      setAuditTotal(res.data.total);
    } catch (err) {
      console.error('Failed to load audit logs:', err);
    }
  }, [auditPage, auditFilter]);

  const loadFeedback = useCallback(async () => {
    try {
      const [lowRatedRes, gapsRes] = await Promise.all([
        adminAPI.getLowRated({ page: lowRatedPage, limit: 10 }),
        adminAPI.getKnowledgeGaps(),
      ]);
      setLowRated(lowRatedRes.data.items);
      setLowRatedTotal(lowRatedRes.data.total);
      setKnowledgeGaps(gapsRes.data);
    } catch (err) {
      console.error('Failed to load feedback:', err);
    }
  }, [lowRatedPage]);

  useEffect(() => {
    if (activeTab === 'users') loadUsers();
    else if (activeTab === 'audit') loadAuditLogs();
    else if (activeTab === 'feedback') loadFeedback();
  }, [activeTab, loadAuditLogs, loadFeedback]);

  const handleInviteUser = async (e) => {
    e.preventDefault();
    setInviteError('');
    setInviteSuccess('');

    if (!inviteEmail || !inviteName || !invitePassword) {
      setInviteError('All fields are required');
      return;
    }

    try {
      await adminAPI.inviteUser({
        email: inviteEmail,
        full_name: inviteName,
        password: invitePassword,
        role: inviteRole,
      });
      setInviteSuccess('User invited successfully!');
      setInviteEmail('');
      setInviteName('');
      setInvitePassword('');
      setIsInviteModalOpen(false);
      loadUsers();
    } catch (err) {
      setInviteError(err.response?.data?.detail || 'Failed to invite user');
    }
  };

  const handleToggleUserStatus = async (userId, currentStatus) => {
    try {
      await adminAPI.updateUser(userId, { is_active: !currentStatus });
      loadUsers();
    } catch (err) {
      console.error('Failed to update user status:', err);
    }
  };

  const handleChangeUserRole = async (userId, newRole) => {
    try {
      await adminAPI.updateUser(userId, { role: newRole });
      loadUsers();
    } catch (err) {
      console.error('Failed to update user role:', err);
    }
  };

  const loadData = async () => {
    try {
      const [analyticsRes, docsRes, unansweredRes] = await Promise.all([
        adminAPI.getAnalytics(),
        adminAPI.listDocuments(),
        adminAPI.getUnanswered(),
      ]);
      setAnalytics(analyticsRes.data);
      setDocuments(docsRes.data);
      setUnanswered(unansweredRes.data);
    } catch (err) {
      console.error('Failed to load admin data:', err);
    }
  };

  const handleUpload = async (file) => {
    if (!file) return;
    setUploading(true);
    setUploadResult(null);

    try {
      const res = await adminAPI.uploadDocument(file);
      setUploadResult({ success: true, message: res.data.message });
      loadData();
    } catch (err) {
      setUploadResult({
        success: false,
        message: err.response?.data?.detail || 'Upload failed',
      });
    } finally {
      setUploading(false);
    }
  };

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) handleUpload(file);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleUpload(file);
  };

  const handleDelete = async (docId) => {
    if (!confirm('Delete this document and all its chunks?')) return;
    try {
      await adminAPI.deleteDocument(docId);
      loadData();
    } catch (err) {
      console.error('Delete failed:', err);
    }
  };

  const handleReplaceDocument = async (docId, file) => {
    if (!file) return;
    try {
      const res = await adminAPI.replaceDocument(docId, file);
      setUploadResult({ success: true, message: res.data.message });
      setReplacingDocId(null);
      loadData();
    } catch (err) {
      setUploadResult({
        success: false,
        message: err.response?.data?.detail || 'Replace failed',
      });
    }
  };

  const handleResolveQuery = async (e) => {
    e.preventDefault();
    if (!resolutionAnswer.trim() || !resolvingQuery) return;

    setIsResolvingSubmitting(true);
    setResolvingError('');
    setResolvingSuccess('');

    try {
      await adminAPI.resolveQuery(resolvingQuery.id, resolutionAnswer.trim());
      setResolvingSuccess('Knowledge base updated and query resolved!');
      setResolutionAnswer('');
      
      // Reload overview and feedback tab data
      await loadData();
      await loadFeedback();
      
      setTimeout(() => {
        setResolvingQuery(null);
        setResolvingSuccess('');
      }, 1500);
    } catch (err) {
      setResolvingError(err.response?.data?.detail || 'Failed to resolve query');
    } finally {
      setIsResolvingSubmitting(false);
    }
  };

  const handleExportAuditLog = async () => {
    try {
      const params = {};
      if (auditFilter) params.action = auditFilter;
      const res = await adminAPI.exportAuditLog(params);
      const url = URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement('a');
      a.href = url;
      a.download = `audit_log_${new Date().toISOString().slice(0, 10)}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Export failed:', err);
    }
  };

  const formatBytes = (bytes) => {
    if (!bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const formatTime = (dateStr) => {
    if (!dateStr) return '—';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
      month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
    });
  };

  const totalQueries = analytics?.total_queries || 0;
  const confDist = analytics?.confidence_distribution || {};
  const maxConf = Math.max(confDist.HIGH || 0, confDist.MEDIUM || 0, confDist.LOW || 0, 1);

  const filteredDocs = docSearch
    ? documents.filter(d => d.filename.toLowerCase().includes(docSearch.toLowerCase()))
    : documents;

  const auditTotalPages = Math.ceil(auditTotal / 20);
  const lowRatedTotalPages = Math.ceil(lowRatedTotal / 10);

  return (
    <div className="admin-page">
      <div className="admin-header">
        <h1>Admin Dashboard</h1>
        <p>Manage knowledge base, monitor queries, and track system performance</p>
      </div>

      {/* Tabs Menu */}
      <div className="admin-tabs">
        <button
          className={`admin-tab-btn ${activeTab === 'overview' ? 'active' : ''}`}
          onClick={() => setActiveTab('overview')}
        >
          <BarChart3 size={16} /> Overview
        </button>
        <button
          className={`admin-tab-btn ${activeTab === 'users' ? 'active' : ''}`}
          onClick={() => setActiveTab('users')}
        >
          <Users size={16} /> Users
        </button>
        <button
          className={`admin-tab-btn ${activeTab === 'audit' ? 'active' : ''}`}
          onClick={() => setActiveTab('audit')}
        >
          <ClipboardList size={16} /> Audit Log
        </button>
        <button
          className={`admin-tab-btn ${activeTab === 'feedback' ? 'active' : ''}`}
          onClick={() => setActiveTab('feedback')}
        >
          <ThumbsDown size={16} /> Feedback
        </button>
      </div>

      {/* ═══ OVERVIEW TAB ═══ */}
      {activeTab === 'overview' && (
        <>
          {/* Stats Grid */}
          <div className="stats-grid">
            <div className="stat-card glass-card">
              <span className="stat-label">Total Queries</span>
              <span className="stat-value gradient">{totalQueries}</span>
            </div>
            <div className="stat-card glass-card">
              <span className="stat-label">Documents</span>
              <span className="stat-value">{analytics?.total_documents || 0}</span>
            </div>
            <div className="stat-card glass-card">
              <span className="stat-label">Total Chunks</span>
              <span className="stat-value">{analytics?.total_chunks || 0}</span>
            </div>
            <div className="stat-card glass-card">
              <span className="stat-label">Avg Rating</span>
              <span className="stat-value">
                {analytics?.average_rating ? `${analytics.average_rating > 0 ? '👍' : '👎'}` : '—'}
              </span>
            </div>
          </div>

          {/* Upload Section */}
          <div className="admin-section">
            <div className="section-header">
              <h2 className="section-title"><Upload size={20} /> Upload Document</h2>
            </div>

            <div
              className={`upload-zone ${dragging ? 'dragging' : ''}`}
              onClick={() => fileInputRef.current?.click()}
              onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
              onDragLeave={() => setDragging(false)}
              onDrop={handleDrop}
            >
              <div className="upload-icon">
                <Upload size={24} color="white" />
              </div>
              <div className="upload-text">
                {uploading ? 'Uploading & Ingesting...' : 'Drop a file here or click to browse'}
              </div>
              <div className="upload-hint">Supports PDF, DOCX, MD, TXT</div>

              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.docx,.md,.txt"
                style={{ display: 'none' }}
                onChange={handleFileSelect}
              />
            </div>

            {uploadResult && (
              <div className="upload-progress" style={{
                background: uploadResult.success ? 'var(--confidence-high-bg)' : 'var(--confidence-low-bg)',
                borderColor: uploadResult.success ? 'rgba(34,197,94,0.3)' : 'rgba(239,68,68,0.3)',
                color: uploadResult.success ? 'var(--confidence-high)' : 'var(--confidence-low)',
              }}>
                {uploadResult.message}
              </div>
            )}
          </div>

          {/* Two-column grid */}
          <div className="admin-grid">
            {/* Documents List */}
            <div className="admin-section">
              <div className="section-header">
                <h2 className="section-title"><Database size={20} /> Knowledge Base</h2>
                <button className="btn btn-ghost btn-sm" onClick={loadData}>
                  <RefreshCw size={14} /> Refresh
                </button>
              </div>

              {/* Document Search */}
              <div className="filter-bar">
                <div className="search-input-wrapper">
                  <Search size={16} />
                  <input
                    type="text"
                    className="search-input"
                    placeholder="Search documents..."
                    value={docSearch}
                    onChange={(e) => setDocSearch(e.target.value)}
                  />
                </div>
              </div>

              <div className="glass-card" style={{ overflow: 'hidden' }}>
                {filteredDocs.length === 0 ? (
                  <div className="empty-state">
                    <div className="empty-state-icon">
                      <Database size={24} color="var(--accent-blue)" />
                    </div>
                    <div className="empty-state-text">
                      {docSearch ? 'No documents match your search' : 'No documents ingested yet'}
                    </div>
                  </div>
                ) : (
                  <table className="docs-table">
                    <thead>
                      <tr>
                        <th>Document</th>
                        <th>Chunks</th>
                        <th>Size</th>
                        <th>Ver</th>
                        <th></th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredDocs.map((doc) => (
                        <tr key={doc.id}>
                          <td>
                            <div className="doc-name">
                              <FileText size={16} style={{ color: 'var(--accent-blue)' }} />
                              {doc.filename}
                              <span className="doc-type-badge">{doc.file_type}</span>
                            </div>
                          </td>
                          <td>{doc.chunk_count}</td>
                          <td>{formatBytes(doc.file_size)}</td>
                          <td style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>v{doc.version || 1}</td>
                          <td style={{ display: 'flex', gap: 6 }}>
                            <button
                              className="btn-icon"
                              onClick={() => {
                                setReplacingDocId(doc.id);
                                setTimeout(() => replaceInputRef.current?.click(), 100);
                              }}
                              title="Replace with new version"
                            >
                              <Replace size={14} style={{ color: 'var(--accent-cyan)' }} />
                            </button>
                            <button
                              className="btn-icon"
                              onClick={() => handleDelete(doc.id)}
                              title="Delete"
                            >
                              <Trash2 size={14} style={{ color: 'var(--confidence-low)' }} />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>

              {/* Hidden replace file input */}
              <input
                ref={replaceInputRef}
                type="file"
                accept=".pdf,.docx,.md,.txt"
                style={{ display: 'none' }}
                onChange={(e) => {
                  if (e.target.files[0] && replacingDocId) {
                    handleReplaceDocument(replacingDocId, e.target.files[0]);
                  }
                  e.target.value = '';
                }}
              />
            </div>

            {/* Confidence Distribution + Knowledge Gaps */}
            <div className="admin-section">
              <div className="section-header">
                <h2 className="section-title"><BarChart3 size={20} /> Confidence Distribution</h2>
              </div>
              <div className="glass-card confidence-bars">
                <div className="conf-bar-row">
                  <span className="conf-bar-label" style={{ color: 'var(--confidence-high)' }}>HIGH</span>
                  <div className="conf-bar-track">
                    <div className="conf-bar-fill" style={{
                      width: `${((confDist.HIGH || 0) / maxConf) * 100}%`,
                      background: 'var(--confidence-high)',
                    }} />
                  </div>
                  <span className="conf-bar-count">{confDist.HIGH || 0}</span>
                </div>
                <div className="conf-bar-row">
                  <span className="conf-bar-label" style={{ color: 'var(--confidence-medium)' }}>MEDIUM</span>
                  <div className="conf-bar-track">
                    <div className="conf-bar-fill" style={{
                      width: `${((confDist.MEDIUM || 0) / maxConf) * 100}%`,
                      background: 'var(--confidence-medium)',
                    }} />
                  </div>
                  <span className="conf-bar-count">{confDist.MEDIUM || 0}</span>
                </div>
                <div className="conf-bar-row">
                  <span className="conf-bar-label" style={{ color: 'var(--confidence-low)' }}>LOW</span>
                  <div className="conf-bar-track">
                    <div className="conf-bar-fill" style={{
                      width: `${((confDist.LOW || 0) / maxConf) * 100}%`,
                      background: 'var(--confidence-low)',
                    }} />
                  </div>
                  <span className="conf-bar-count">{confDist.LOW || 0}</span>
                </div>
              </div>

              {/* Unanswered Queries */}
              <div style={{ marginTop: 24 }}>
                <div className="section-header">
                  <h2 className="section-title"><FileQuestion size={20} /> Knowledge Gaps</h2>
                </div>
                <div className="glass-card" style={{ padding: 16 }}>
                  {unanswered.length === 0 ? (
                    <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 20, fontSize: '0.88rem' }}>
                      ✅ No knowledge gaps detected
                    </div>
                  ) : (
                    <div className="recent-queries">
                      {unanswered.slice(0, 8).map((q) => (
                        <div key={q.id} className="recent-query-item" style={{ justifyContent: 'space-between', alignItems: 'flex-start' }}>
                          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, flex: 1, minWidth: 0 }}>
                            {q.is_resolved ? (
                              <Check size={16} style={{ color: 'var(--confidence-high)', flexShrink: 0, marginTop: 2 }} />
                            ) : (
                              <AlertCircle size={16} style={{ color: 'var(--confidence-low)', flexShrink: 0, marginTop: 2 }} />
                            )}
                            <div style={{ minWidth: 0, flex: 1 }}>
                              <div className="recent-query-text" style={{
                                textDecoration: q.is_resolved ? 'line-through' : 'none',
                                color: q.is_resolved ? 'var(--text-muted)' : 'var(--text-bright)',
                              }}>{q.question}</div>
                              {q.is_resolved && (
                                <div style={{ fontSize: '0.78rem', color: 'var(--accent-cyan)', marginTop: 4 }}>
                                  💡 Resolved: {q.resolved_answer}
                                </div>
                              )}
                            </div>
                          </div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginLeft: 16, flexShrink: 0 }}>
                            <span className="recent-query-time">{formatTime(q.created_at)}</span>
                            {!q.is_resolved && (
                              <button
                                className="btn btn-primary"
                                style={{ padding: '2px 8px', fontSize: '0.72rem', height: 'auto', minHeight: 0 }}
                                onClick={() => setResolvingQuery(q)}
                              >
                                Resolve
                              </button>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Recent Queries */}
          <div className="admin-section">
            <div className="section-header">
              <h2 className="section-title"><MessageSquare size={20} /> Recent Queries</h2>
            </div>
            <div className="glass-card" style={{ padding: 16 }}>
              {analytics?.recent_queries?.length > 0 ? (
                <div className="recent-queries">
                  {analytics.recent_queries.slice(0, 10).map((q, i) => (
                    <div key={i} className="recent-query-item">
                      <span className={`confidence-badge ${q.confidence_tier.toLowerCase()}`} style={{ flexShrink: 0 }}>
                        {q.confidence_tier}
                      </span>
                      <span className="recent-query-text">{q.question}</span>
                      <span className="recent-query-time">{formatTime(q.created_at)}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 20, fontSize: '0.88rem' }}>
                  No queries yet — start chatting to see data here!
                </div>
              )}
            </div>
          </div>
        </>
      )}

      {/* ═══ USERS TAB ═══ */}
      {activeTab === 'users' && (
        <div className="admin-section animate-fade-in">
          <div className="section-header">
            <h2 className="section-title"><Users size={20} /> User Directory</h2>
            <button
              className="btn btn-primary btn-sm"
              onClick={() => {
                const autoPass = Math.random().toString(36).slice(-8);
                setInvitePassword(autoPass);
                setIsInviteModalOpen(true);
              }}
            >
              <UserPlus size={14} /> Invite User
            </button>
          </div>

          <div className="glass-card" style={{ overflow: 'hidden' }}>
            {users.length === 0 ? (
              <div className="empty-state">
                <div className="empty-state-icon"><Users size={24} color="var(--accent-blue)" /></div>
                <div className="empty-state-text">No other users in this organization yet</div>
              </div>
            ) : (
              <table className="docs-table">
                <thead>
                  <tr>
                    <th>User</th>
                    <th>Role</th>
                    <th>Status</th>
                    <th>Last Login</th>
                    <th>Created</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => (
                    <tr key={u.id}>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                          <div style={{
                            width: 32, height: 32, borderRadius: '50%',
                            background: u.role === 'tenant_admin' ? 'var(--accent-gradient)' : 'rgba(6, 182, 212, 0.15)',
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            fontSize: '0.78rem', fontWeight: 'bold', color: u.role === 'tenant_admin' ? '#fff' : 'var(--accent-cyan)'
                          }}>
                            {u.full_name?.split(' ').map(n => n[0]).join('').toUpperCase() || '?'}
                          </div>
                          <div>
                            <div style={{ fontWeight: 500, color: 'var(--text-bright)' }}>{u.full_name}</div>
                            <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>{u.email}</div>
                          </div>
                        </div>
                      </td>
                      <td>
                        <select
                          className="role-select"
                          value={u.role}
                          onChange={(e) => handleChangeUserRole(u.id, e.target.value)}
                        >
                          <option value="bd_rep">BD Rep</option>
                          <option value="tenant_admin">Admin</option>
                        </select>
                      </td>
                      <td>
                        <span className={`user-status-badge ${u.is_active ? 'active' : 'inactive'}`}>
                          {u.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </td>
                      <td>{u.last_login ? formatTime(u.last_login) : 'Never'}</td>
                      <td>{formatTime(u.created_at)}</td>
                      <td>
                        <button
                          className="btn btn-ghost btn-sm"
                          style={{
                            color: u.is_active ? 'var(--confidence-low)' : 'var(--confidence-high)',
                            borderColor: u.is_active ? 'rgba(239, 68, 68, 0.2)' : 'rgba(34, 197, 94, 0.2)'
                          }}
                          onClick={() => handleToggleUserStatus(u.id, u.is_active)}
                        >
                          {u.is_active ? 'Deactivate' : 'Activate'}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}

      {/* ═══ AUDIT LOG TAB ═══ */}
      {activeTab === 'audit' && (
        <div className="admin-section animate-fade-in">
          <div className="section-header">
            <h2 className="section-title"><ClipboardList size={20} /> Compliance Audit Trail</h2>
            <button className="btn-export" onClick={handleExportAuditLog}>
              <Download size={14} /> Export CSV
            </button>
          </div>

          {/* Filter Bar */}
          <div className="filter-bar">
            <select
              className="filter-select"
              value={auditFilter}
              onChange={(e) => { setAuditFilter(e.target.value); setAuditPage(1); }}
            >
              <option value="">All Actions</option>
              <option value="login">Login</option>
              <option value="register">Register</option>
              <option value="register_tenant">Register Tenant</option>
              <option value="upload">Upload</option>
              <option value="delete">Delete</option>
              <option value="replace_document">Replace Doc</option>
              <option value="invite_user">Invite User</option>
              <option value="update_user">Update User</option>
              <option value="rate">Rate</option>
              <option value="export">Export</option>
            </select>
            <span style={{ color: 'var(--text-muted)', fontSize: '0.82rem' }}>
              {auditTotal} total entries
            </span>
          </div>

          <div className="glass-card" style={{ overflow: 'hidden' }}>
            {auditLogs.length === 0 ? (
              <div className="empty-state">
                <div className="empty-state-icon"><ClipboardList size={24} color="var(--accent-blue)" /></div>
                <div className="empty-state-text">No audit logs found</div>
                <div className="empty-state-hint">Actions will be recorded as users interact with the system</div>
              </div>
            ) : (
              <table className="audit-log-table">
                <thead>
                  <tr>
                    <th>Timestamp</th>
                    <th>User</th>
                    <th>Action</th>
                    <th>Resource</th>
                    <th>Details</th>
                  </tr>
                </thead>
                <tbody>
                  {auditLogs.map((log) => (
                    <tr key={log.id}>
                      <td style={{ whiteSpace: 'nowrap', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                        {formatTime(log.created_at)}
                      </td>
                      <td style={{ fontWeight: 500 }}>{log.user_name}</td>
                      <td>
                        <span className={`action-badge ${log.action}`}>
                          {log.action.replace(/_/g, ' ')}
                        </span>
                      </td>
                      <td style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                        {log.resource_type ? `${log.resource_type} #${log.resource_id || ''}` : '—'}
                      </td>
                      <td style={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                        {log.details && Object.keys(log.details).length > 0
                          ? Object.entries(log.details).map(([k, v]) => `${k}: ${v}`).join(', ')
                          : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          {/* Pagination */}
          {auditTotalPages > 1 && (
            <div className="pagination">
              <button
                className="pagination-btn"
                disabled={auditPage <= 1}
                onClick={() => setAuditPage(p => p - 1)}
              >
                <ChevronLeft size={14} /> Prev
              </button>
              <span className="pagination-info">
                Page {auditPage} of {auditTotalPages}
              </span>
              <button
                className="pagination-btn"
                disabled={auditPage >= auditTotalPages}
                onClick={() => setAuditPage(p => p + 1)}
              >
                Next <ChevronRight size={14} />
              </button>
            </div>
          )}
        </div>
      )}

      {/* ═══ FEEDBACK TAB ═══ */}
      {activeTab === 'feedback' && (
        <div className="admin-section animate-fade-in">
          <div className="section-header">
            <h2 className="section-title"><ThumbsDown size={20} /> Improvement Opportunities</h2>
          </div>

          {/* Knowledge Gaps Summary */}
          {knowledgeGaps && (
            <div style={{ marginBottom: 28 }}>
              <div className="stat-summary-row">
                <div className="stat-summary-item">
                  <div className="label">Low-Rated Queries</div>
                  <div className="value" style={{ color: 'var(--confidence-low)' }}>{lowRatedTotal}</div>
                </div>
                <div className="stat-summary-item">
                  <div className="label">Knowledge Gaps</div>
                  <div className="value violet">{knowledgeGaps.total_gaps}</div>
                </div>
                <div className="stat-summary-item">
                  <div className="label">Top Topics</div>
                  <div className="value">{knowledgeGaps.top_topics?.length || 0}</div>
                </div>
              </div>

              {/* Topic Pills */}
              {knowledgeGaps.top_topics?.length > 0 && (
                <div>
                  <h3 style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-bright)', marginBottom: 12 }}>
                    Recurring Topics in Unanswered Questions
                  </h3>
                  <div className="topic-pills">
                    {knowledgeGaps.top_topics.map((t) => (
                      <span key={t.keyword} className="topic-pill">
                        {t.keyword}
                        <span className="freq">{t.frequency}×</span>
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Unanswered Queries (Knowledge Gaps) List */}
              {knowledgeGaps.recent_gaps?.length > 0 && (
                <div style={{ marginTop: 24 }}>
                  <h3 style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-bright)', marginBottom: 12 }}>
                    Unanswered Queries (Knowledge Gaps)
                  </h3>
                  <div className="glass-card" style={{ padding: 16 }}>
                    <div className="recent-queries">
                      {knowledgeGaps.recent_gaps.map((q) => (
                        <div key={q.id} className="recent-query-item" style={{ justifyContent: 'space-between', alignItems: 'flex-start' }}>
                          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, flex: 1, minWidth: 0 }}>
                            {q.is_resolved ? (
                              <Check size={16} style={{ color: 'var(--confidence-high)', flexShrink: 0, marginTop: 2 }} />
                            ) : (
                              <AlertCircle size={16} style={{ color: 'var(--confidence-low)', flexShrink: 0, marginTop: 2 }} />
                            )}
                            <div style={{ minWidth: 0, flex: 1 }}>
                              <span className="recent-query-text" style={{
                                textDecoration: q.is_resolved ? 'line-through' : 'none',
                                color: q.is_resolved ? 'var(--text-muted)' : 'var(--text-bright)',
                              }}>{q.question}</span>
                              {q.is_resolved && (
                                <div style={{ fontSize: '0.78rem', color: 'var(--accent-cyan)', marginTop: 4 }}>
                                  💡 Resolved: {q.resolved_answer}
                                </div>
                              )}
                            </div>
                          </div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginLeft: 16, flexShrink: 0 }}>
                            <span className="recent-query-time">{formatTime(q.created_at)}</span>
                            {!q.is_resolved && (
                              <button
                                className="btn btn-primary"
                                style={{ padding: '2px 8px', fontSize: '0.72rem', height: 'auto', minHeight: 0 }}
                                onClick={() => setResolvingQuery(q)}
                              >
                                Resolve
                              </button>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Low-Rated Queries List */}
          <div className="section-header" style={{ marginTop: 20 }}>
            <h2 className="section-title"><ThumbsDown size={18} /> Thumbs-Down Responses</h2>
          </div>

          {lowRated.length === 0 ? (
            <div className="glass-card">
              <div className="empty-state">
                <div className="empty-state-icon"><Check size={24} color="var(--confidence-high)" /></div>
                <div className="empty-state-text">No negative feedback yet</div>
                <div className="empty-state-hint">Thumbs-down responses will appear here for review</div>
              </div>
            </div>
          ) : (
            <>
              {lowRated.map((q) => (
                <div key={q.id} className="feedback-card">
                  <div className="feedback-question">❓ {q.question}</div>
                  <div className="feedback-answer">{q.answer || 'No answer recorded'}</div>
                  {q.is_resolved && (
                    <div style={{
                      marginTop: 10, padding: '10px 14px', borderRadius: 8,
                      background: 'rgba(34, 197, 94, 0.08)', border: '1px solid rgba(34, 197, 94, 0.15)',
                      color: 'var(--text-bright)', fontSize: '0.86rem'
                    }}>
                      <div style={{ fontWeight: 600, display: 'flex', alignItems: 'center', gap: 6, color: 'var(--confidence-high)' }}>
                        <Check size={14} /> Resolved knowledge added to database:
                      </div>
                      <div style={{ marginTop: 6, color: 'var(--text-muted)', fontStyle: 'italic' }}>"{q.resolved_answer}"</div>
                    </div>
                  )}
                  <div className="feedback-meta" style={{ justifyContent: 'space-between', display: 'flex', alignItems: 'center' }}>
                    <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                      <span className={`confidence-badge ${q.confidence_tier?.toLowerCase()}`}>
                        {q.confidence_tier}
                      </span>
                      <span>{formatTime(q.created_at)}</span>
                      {q.is_bridge_response && <span style={{ color: 'var(--confidence-medium)' }}>⚠ Bridge Response</span>}
                      {q.is_resolved && <span style={{ color: 'var(--confidence-high)', fontWeight: 500, fontSize: '0.78rem' }}>✓ Resolved</span>}
                    </div>
                    {!q.is_resolved && (
                      <button
                        className="btn btn-primary"
                        style={{ padding: '4px 10px', fontSize: '0.75rem', height: 'auto', minHeight: 0 }}
                        onClick={() => setResolvingQuery(q)}
                      >
                        Resolve Gap
                      </button>
                    )}
                  </div>
                </div>
              ))}

              {lowRatedTotalPages > 1 && (
                <div className="pagination">
                  <button
                    className="pagination-btn"
                    disabled={lowRatedPage <= 1}
                    onClick={() => setLowRatedPage(p => p - 1)}
                  >
                    <ChevronLeft size={14} /> Prev
                  </button>
                  <span className="pagination-info">
                    Page {lowRatedPage} of {lowRatedTotalPages}
                  </span>
                  <button
                    className="pagination-btn"
                    disabled={lowRatedPage >= lowRatedTotalPages}
                    onClick={() => setLowRatedPage(p => p + 1)}
                  >
                    Next <ChevronRight size={14} />
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* Invite User Modal */}
      {isInviteModalOpen && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div className="modal-header">
              <h3>Invite Team Member</h3>
              <button className="close-btn" onClick={() => setIsInviteModalOpen(false)}>
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleInviteUser}>
              {inviteError && (
                <div style={{
                  padding: '8px 12px', background: 'var(--confidence-low-bg)',
                  border: '1px solid rgba(239,68,68,0.3)', color: 'var(--confidence-low)',
                  borderRadius: 6, marginBottom: 16, fontSize: '0.84rem'
                }}>
                  {inviteError}
                </div>
              )}

              <div className="form-group">
                <label>Full Name</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="Alex Morgan"
                  value={inviteName}
                  onChange={(e) => setInviteName(e.target.value)}
                  required
                />
              </div>

              <div className="form-group">
                <label>Email Address</label>
                <input
                  type="email"
                  className="form-input"
                  placeholder="alex@company.com"
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  required
                />
              </div>

              <div className="form-group">
                <label>Temporary Password</label>
                <input
                  type="text"
                  className="form-input"
                  value={invitePassword}
                  onChange={(e) => setInvitePassword(e.target.value)}
                  required
                />
              </div>

              <div className="form-group">
                <label>System Role</label>
                <select
                  className="form-select"
                  value={inviteRole}
                  onChange={(e) => setInviteRole(e.target.value)}
                >
                  <option value="bd_rep">BD Rep (Standard Chat User)</option>
                  <option value="tenant_admin">Tenant Admin (Dashboard access)</option>
                </select>
              </div>

              <div className="modal-actions">
                <button type="button" className="btn btn-ghost" onClick={() => setIsInviteModalOpen(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  Create User
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
      {/* Resolve Knowledge Gap Modal */}
      {resolvingQuery && (
        <div className="modal-overlay">
          <div className="modal-content" style={{ maxWidth: 600 }}>
            <div className="modal-header">
              <h3>Resolve Knowledge Gap</h3>
              <button
                className="close-btn"
                onClick={() => {
                  setResolvingQuery(null);
                  setResolvingError('');
                  setResolvingSuccess('');
                  setResolutionAnswer('');
                }}
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleResolveQuery}>
              {resolvingError && (
                <div style={{
                  padding: '8px 12px', background: 'var(--confidence-low-bg)',
                  border: '1px solid rgba(239,68,68,0.3)', color: 'var(--confidence-low)',
                  borderRadius: 6, marginBottom: 16, fontSize: '0.84rem'
                }}>
                  {resolvingError}
                </div>
              )}
              {resolvingSuccess && (
                <div style={{
                  padding: '8px 12px', background: 'var(--confidence-high-bg)',
                  border: '1px solid rgba(34,197,94,0.3)', color: 'var(--confidence-high)',
                  borderRadius: 6, marginBottom: 16, fontSize: '0.84rem'
                }}>
                  {resolvingSuccess}
                </div>
              )}

              <div className="form-group">
                <label style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Client Question</label>
                <div style={{
                  padding: '12px', background: 'rgba(255,255,255,0.03)',
                  border: '1px solid rgba(255,255,255,0.08)', borderRadius: 6,
                  color: 'var(--text-bright)', fontSize: '0.9rem', marginTop: 4,
                  fontWeight: 500, lineHeight: 1.4
                }}>
                  ❓ {resolvingQuery.question}
                </div>
              </div>

              <div className="form-group" style={{ marginTop: 16 }}>
                <label>Correct Answer / Missing Knowledge Context</label>
                <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: 8, marginTop: 4 }}>
                  Provide the facts or documentation needed to answer this question. This information will be appended to the tenant's vector database, allowing the assistant to answer similar questions correctly.
                </p>
                <textarea
                  className="form-input"
                  style={{ minHeight: 120, resize: 'vertical', padding: 12, width: '100%', fontFamily: 'inherit' }}
                  placeholder="E.g., TechAssist supports SSO integration via SAML 2.0 and OpenID Connect. The setup can be completed by your administrator in the Settings panel under Integrations."
                  value={resolutionAnswer}
                  onChange={(e) => setResolutionAnswer(e.target.value)}
                  required
                  disabled={isResolvingSubmitting}
                />
              </div>

              <div className="modal-actions" style={{ marginTop: 24 }}>
                <button
                  type="button"
                  className="btn btn-ghost"
                  onClick={() => {
                    setResolvingQuery(null);
                    setResolvingError('');
                    setResolvingSuccess('');
                    setResolutionAnswer('');
                  }}
                  disabled={isResolvingSubmitting}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={isResolvingSubmitting || !resolutionAnswer.trim()}
                >
                  {isResolvingSubmitting ? 'Updating Knowledge Base...' : 'Add Knowledge & Resolve'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
