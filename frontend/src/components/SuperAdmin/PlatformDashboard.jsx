/**
 * PlatformDashboard — Super Admin portal for tenant management and platform statistics.
 */

import { useState, useEffect } from 'react';
import { superadminAPI } from '../../api/client';
import {
  Building2, Users, FileText, MessageSquare, Shield,
  RefreshCw, TrendingUp, AlertCircle, Ban, CheckCircle, Save
} from 'lucide-react';
import './PlatformDashboard.css';

export default function PlatformDashboard() {
  const [stats, setStats] = useState(null);
  const [tenants, setTenants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editingTenantId, setEditingTenantId] = useState(null);
  
  // Edit Fields State
  const [editName, setEditName] = useState('');
  const [editPlan, setEditPlan] = useState('');
  const [editMaxDocs, setEditMaxDocs] = useState(20);
  const [editMaxUsers, setEditMaxUsers] = useState(5);
  const [updateError, setUpdateError] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [statsRes, tenantsRes] = await Promise.all([
        superadminAPI.getStats(),
        superadminAPI.listTenants(),
      ]);
      setStats(statsRes.data);
      setTenants(tenantsRes.data);
    } catch (err) {
      console.error('Failed to load superadmin dashboard data:', err);
    } finally {
      setLoading(false);
    }
  };

  const startEditing = (tenant) => {
    setEditingTenantId(tenant.id);
    setEditName(tenant.name);
    setEditPlan(tenant.plan);
    setEditMaxDocs(tenant.max_documents);
    setEditMaxUsers(tenant.max_users);
    setUpdateError('');
  };

  const handleSaveTenant = async (tenantId) => {
    try {
      await superadminAPI.updateTenant(tenantId, {
        name: editName,
        plan: editPlan,
        max_documents: parseInt(editMaxDocs),
        max_users: parseInt(editMaxUsers),
      });
      setEditingTenantId(null);
      loadData();
    } catch (err) {
      setUpdateError(err.response?.data?.detail || 'Failed to update tenant');
    }
  };

  const handleToggleTenantStatus = async (tenantId, currentStatus) => {
    try {
      await superadminAPI.updateTenant(tenantId, { is_active: !currentStatus });
      loadData();
    } catch (err) {
      console.error('Failed to toggle tenant status:', err);
    }
  };

  const formatTime = (dateStr) => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
      month: 'short', day: 'numeric', year: 'numeric'
    });
  };

  if (loading && !stats) {
    return (
      <div className="superadmin-page" style={{ justifyContent: 'center', alignItems: 'center', display: 'flex', height: '100vh' }}>
        <div className="text-gradient" style={{ fontSize: '1.2rem', fontWeight: 600 }}>
          Loading platform dashboard...
        </div>
      </div>
    );
  }

  return (
    <div className="superadmin-page">
      <div className="superadmin-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div className="superadmin-badge-icon">
            <Shield size={20} color="white" />
          </div>
          <div>
            <h1>Platform Administration</h1>
            <p>Super Admin control panel for SaaS tenants, usage limits, and system overview</p>
          </div>
        </div>
        <button className="btn btn-ghost btn-sm" onClick={loadData} disabled={loading}>
          <RefreshCw size={14} className={loading ? 'spin' : ''} /> Refresh
        </button>
      </div>

      {/* Stats Grid */}
      <div className="stats-grid">
        <div className="stat-card glass-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <span className="stat-label">Total Organizations</span>
            <Building2 size={16} color="var(--accent-blue)" />
          </div>
          <span className="stat-value gradient">{stats?.total_tenants || 0}</span>
        </div>
        <div className="stat-card glass-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <span className="stat-label">Platform Users</span>
            <Users size={16} color="var(--accent-cyan)" />
          </div>
          <span className="stat-value">{stats?.total_users || 0}</span>
        </div>
        <div className="stat-card glass-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <span className="stat-label">Documents Indexed</span>
            <FileText size={16} color="var(--accent-blue)" />
          </div>
          <span className="stat-value">{stats?.total_documents || 0}</span>
        </div>
        <div className="stat-card glass-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <span className="stat-label">Total API Queries</span>
            <MessageSquare size={16} color="var(--confidence-high)" />
          </div>
          <span className="stat-value">{stats?.total_queries || 0}</span>
        </div>
      </div>

      {/* Tenants Table Section */}
      <div className="superadmin-section">
        <div className="section-header">
          <h2 className="section-title"><Building2 size={20} /> Registered Organizations (Tenants)</h2>
        </div>

        {updateError && (
          <div className="error-alert">
            <AlertCircle size={16} /> {updateError}
          </div>
        )}

        <div className="glass-card" style={{ overflow: 'hidden' }}>
          {tenants.length === 0 ? (
            <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>
              No tenants registered yet.
            </div>
          ) : (
            <table className="tenants-table">
              <thead>
                <tr>
                  <th>Organization</th>
                  <th>Status</th>
                  <th>Subscription Plan</th>
                  <th>Usage (Users / Docs / Queries)</th>
                  <th>Allocated Limits</th>
                  <th>Created</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {tenants.map((t) => {
                  const isEditing = editingTenantId === t.id;
                  return (
                    <tr key={t.id} className={isEditing ? 'editing-row' : ''}>
                      <td>
                        <div style={{ fontWeight: 600, color: 'var(--text-bright)', fontSize: '0.94rem' }}>
                          {isEditing ? (
                            <input
                              type="text"
                              className="edit-input"
                              value={editName}
                              onChange={(e) => setEditName(e.target.value)}
                            />
                          ) : (
                            t.name
                          )}
                        </div>
                        <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: 2 }}>
                          slug: {t.slug} | id: {t.id.slice(0, 8)}...
                        </div>
                      </td>
                      <td>
                        <span className={`status-badge ${t.is_active ? 'active' : 'inactive'}`}>
                          {t.is_active ? 'Active' : 'Suspended'}
                        </span>
                      </td>
                      <td>
                        {isEditing ? (
                          <select
                            className="edit-select"
                            value={editPlan}
                            onChange={(e) => setEditPlan(e.target.value)}
                          >
                            <option value="free">Free</option>
                            <option value="pro">Pro</option>
                            <option value="enterprise">Enterprise</option>
                          </select>
                        ) : (
                          <span className={`plan-badge ${t.plan.toLowerCase()}`}>
                            {t.plan}
                          </span>
                        )}
                      </td>
                      <td>
                        <div className="usage-stats-cell">
                          <span>👤 {t.stats?.users || 0}</span>
                          <span>📄 {t.stats?.documents || 0}</span>
                          <span>💬 {t.stats?.queries || 0}</span>
                        </div>
                      </td>
                      <td>
                        {isEditing ? (
                          <div className="edit-limits-cell">
                            <div>
                              <label>Docs:</label>
                              <input
                                type="number"
                                value={editMaxDocs}
                                onChange={(e) => setEditMaxDocs(e.target.value)}
                              />
                            </div>
                            <div>
                              <label>Users:</label>
                              <input
                                type="number"
                                value={editMaxUsers}
                                onChange={(e) => setEditMaxUsers(e.target.value)}
                              />
                            </div>
                          </div>
                        ) : (
                          <div style={{ fontSize: '0.84rem' }}>
                            Max Docs: <strong>{t.max_documents}</strong> | Max Users: <strong>{t.max_users}</strong>
                          </div>
                        )}
                      </td>
                      <td>{formatTime(t.created_at)}</td>
                      <td>
                        <div className="table-actions">
                          {isEditing ? (
                            <>
                              <button
                                className="btn btn-primary btn-sm btn-icon"
                                onClick={() => handleSaveTenant(t.id)}
                                title="Save Settings"
                              >
                                <Save size={14} /> Save
                              </button>
                              <button
                                className="btn btn-ghost btn-sm"
                                onClick={() => setEditingTenantId(null)}
                              >
                                Cancel
                              </button>
                            </>
                          ) : (
                            <>
                              <button
                                className="btn btn-ghost btn-sm"
                                onClick={() => startEditing(t)}
                              >
                                Edit Settings
                              </button>
                              <button
                                className="btn btn-ghost btn-sm"
                                style={{
                                  color: t.is_active ? 'var(--confidence-low)' : 'var(--confidence-high)',
                                  borderColor: t.is_active ? 'rgba(239, 68, 68, 0.2)' : 'rgba(34, 197, 94, 0.2)'
                                }}
                                onClick={() => handleToggleTenantStatus(t.id, t.is_active)}
                              >
                                {t.is_active ? 'Suspend' : 'Activate'}
                              </button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
