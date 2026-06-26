/**
 * LoginPage — Login + Organization Registration for multi-tenant SaaS.
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { Zap, LogIn, Building2, ArrowLeft } from 'lucide-react';
import './LoginPage.css';

export default function LoginPage() {
  const { login, registerTenant } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState('login'); // 'login' | 'register'
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // Login form
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  // Register form
  const [companyName, setCompanyName] = useState('');
  const [adminName, setAdminName] = useState('');
  const [adminEmail, setAdminEmail] = useState('');
  const [adminPassword, setAdminPassword] = useState('');

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await login(email, password);
      navigate('/');
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setError('');

    if (adminPassword.length < 6) {
      setError('Password must be at least 6 characters');
      return;
    }

    setLoading(true);
    try {
      await registerTenant(companyName, adminName, adminEmail, adminPassword);
      navigate('/');
    } catch (err) {
      setError(err.response?.data?.detail || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-container">
        {/* Brand Header */}
        <div className="login-brand">
          <div className="login-logo">
            <Zap size={28} color="white" />
          </div>
          <h1>TechAssist AI</h1>
          <p className="login-subtitle">
            {mode === 'login'
              ? 'Sign in to your knowledge assistant'
              : 'Create your organization'}
          </p>
        </div>

        {/* Error */}
        {error && <div className="login-error">{error}</div>}

        {mode === 'login' ? (
          <>
            {/* Login Form */}
            <form onSubmit={handleLogin} className="login-form">
              <div className="form-group">
                <label htmlFor="email">Email</label>
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@company.com"
                  required
                  autoFocus
                />
              </div>
              <div className="form-group">
                <label htmlFor="password">Password</label>
                <input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  required
                />
              </div>
              <button type="submit" className="login-btn" disabled={loading}>
                <LogIn size={18} />
                {loading ? 'Signing in...' : 'Sign In'}
              </button>
            </form>

            {/* Demo credentials hint */}
            <div className="login-demo-hint">
              <strong>Demo Accounts:</strong>
              <div className="demo-accounts">
                <div className="demo-account">
                  <span className="demo-role">BD Rep</span>
                  <code>demo@cloudnexus.com</code> / <code>demo123</code>
                </div>
                <div className="demo-account">
                  <span className="demo-role">Admin</span>
                  <code>admin@cloudnexus.com</code> / <code>admin123</code>
                </div>
              </div>
            </div>

            {/* Switch to register */}
            <div className="login-switch">
              <span>New company?</span>
              <button onClick={() => { setMode('register'); setError(''); }} className="login-switch-btn">
                <Building2 size={16} />
                Create Organization
              </button>
            </div>
          </>
        ) : (
          <>
            {/* Register Form */}
            <form onSubmit={handleRegister} className="login-form">
              <div className="form-group">
                <label htmlFor="companyName">Company Name</label>
                <input
                  id="companyName"
                  type="text"
                  value={companyName}
                  onChange={(e) => setCompanyName(e.target.value)}
                  placeholder="Acme Corporation"
                  required
                  autoFocus
                />
              </div>
              <div className="form-group">
                <label htmlFor="adminName">Your Name</label>
                <input
                  id="adminName"
                  type="text"
                  value={adminName}
                  onChange={(e) => setAdminName(e.target.value)}
                  placeholder="John Doe"
                  required
                />
              </div>
              <div className="form-group">
                <label htmlFor="adminEmail">Admin Email</label>
                <input
                  id="adminEmail"
                  type="email"
                  value={adminEmail}
                  onChange={(e) => setAdminEmail(e.target.value)}
                  placeholder="admin@acme.com"
                  required
                />
              </div>
              <div className="form-group">
                <label htmlFor="adminPassword">Password</label>
                <input
                  id="adminPassword"
                  type="password"
                  value={adminPassword}
                  onChange={(e) => setAdminPassword(e.target.value)}
                  placeholder="Min 6 characters"
                  required
                  minLength={6}
                />
              </div>
              <button type="submit" className="login-btn register-btn" disabled={loading}>
                <Building2 size={18} />
                {loading ? 'Creating...' : 'Create Organization'}
              </button>
            </form>

            {/* Switch to login */}
            <div className="login-switch">
              <button onClick={() => { setMode('login'); setError(''); }} className="login-switch-btn">
                <ArrowLeft size={16} />
                Back to Sign In
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
