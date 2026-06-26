/**
 * Sidebar — Navigation, chat history, tenant info, user profile.
 */

import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { chatAPI } from '../../api/client';
import {
  Zap, Plus, MessageSquare, LayoutDashboard,
  LogOut, Users, Building2, Shield,
} from 'lucide-react';
import './Sidebar.css';

export default function Sidebar({ onNewChat, activeSessionId, onSelectSession }) {
  const { user, isAdmin, tenantName, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [chatHistory, setChatHistory] = useState([]);

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async () => {
    try {
      const res = await chatAPI.getHistory();
      setChatHistory(res.data);
    } catch (err) {
      console.error('Failed to load chat history:', err);
    }
  };

  // Expose refreshHistory so parent can trigger it
  useEffect(() => {
    window.__refreshSidebarHistory = loadHistory;
    return () => { delete window.__refreshSidebarHistory; };
  }, []);

  const handleNewChat = () => {
    if (onNewChat) onNewChat();
    navigate('/');
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const getInitials = (name) => {
    return name?.split(' ').map(n => n[0]).join('').toUpperCase() || '?';
  };

  const formatTime = (dateStr) => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now - date;
    const hours = diff / (1000 * 60 * 60);

    if (hours < 1) return 'Just now';
    if (hours < 24) return `${Math.floor(hours)}h ago`;
    if (hours < 48) return 'Yesterday';
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  return (
    <aside className="sidebar">
      {/* Brand */}
      <div className="sidebar-header">
        <div className="sidebar-brand">
          <div className="sidebar-logo">
            <Zap size={20} color="white" />
          </div>
          <div className="sidebar-brand-text">
            <span className="sidebar-brand-name">TechAssist AI</span>
            <span className="sidebar-brand-tag">
              <Building2 size={11} />
              {tenantName || 'Knowledge Assistant'}
            </span>
          </div>
        </div>
        <button className="btn btn-primary new-chat-btn" onClick={handleNewChat}>
          <Plus size={16} />
          New Chat
        </button>
      </div>

      {/* Navigation */}
      <nav className="sidebar-nav">
        <button
          className={`nav-item ${location.pathname === '/' ? 'active' : ''}`}
          onClick={() => navigate('/')}
        >
          <MessageSquare size={18} />
          Chat
        </button>
        {isAdmin && (
          <button
            className={`nav-item ${location.pathname === '/admin' ? 'active' : ''}`}
            onClick={() => navigate('/admin')}
          >
            <LayoutDashboard size={18} />
            Admin Panel
          </button>
        )}
        {user?.role === 'super_admin' && (
          <button
            className={`nav-item ${location.pathname === '/superadmin' ? 'active' : ''}`}
            onClick={() => navigate('/superadmin')}
          >
            <Shield size={18} />
            Platform Admin
          </button>
        )}
      </nav>

      <div className="sidebar-divider" />

      {/* Chat History */}
      <div className="sidebar-section-title">Recent Chats</div>
      <div className="chat-history-list">
        {chatHistory.length === 0 ? (
          <div style={{ padding: '12px 14px', color: 'var(--text-muted)', fontSize: '0.82rem' }}>
            No conversations yet
          </div>
        ) : (
          chatHistory.map((session) => (
            <button
              key={session.id}
              className={`chat-history-item ${activeSessionId === session.id ? 'active' : ''}`}
              onClick={() => onSelectSession && onSelectSession(session.id)}
            >
              <span className="chat-history-title">{session.title}</span>
              <span className="chat-history-time">{formatTime(session.updated_at)}</span>
            </button>
          ))
        )}
      </div>

      {/* User Footer */}
      <div className="sidebar-footer">
        <div className="sidebar-user">
          <div className="sidebar-avatar">
            {getInitials(user?.full_name)}
          </div>
          <div className="sidebar-user-info">
            <div className="sidebar-user-name">{user?.full_name}</div>
            <div className="sidebar-user-role">
              {user?.role === 'super_admin' && '🛡️ Super Admin'}
              {user?.role === 'tenant_admin' && '🛡️ Admin'}
              {user?.role === 'admin' && '🛡️ Admin'}
              {user?.role === 'bd_rep' && '💼 BD Rep'}
            </div>
          </div>
          <button className="sidebar-logout" onClick={handleLogout} title="Sign out">
            <LogOut size={16} />
          </button>
        </div>
      </div>
    </aside>
  );
}
