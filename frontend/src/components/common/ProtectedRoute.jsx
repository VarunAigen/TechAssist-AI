/**
 * ProtectedRoute — redirects to login if not authenticated.
 */

import { Navigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

export default function ProtectedRoute({ children, requireAdmin = false, requireSuperAdmin = false }) {
  const { isAuthenticated, isAdmin, user, loading } = useAuth();

  if (loading) {
    return (
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        height: '100vh', background: 'var(--bg-primary)'
      }}>
        <div className="text-gradient" style={{ fontSize: '1.2rem', fontWeight: 600 }}>
          Loading...
        </div>
      </div>
    );
  }

  if (!isAuthenticated) return <Navigate to="/login" replace />;
  if (requireSuperAdmin && user?.role !== 'super_admin') return <Navigate to="/" replace />;
  if (requireAdmin && !isAdmin) return <Navigate to="/" replace />;

  return children;
}
