/**
 * AuthContext — manages authentication state with multi-tenant support.
 */

import { createContext, useContext, useState, useEffect } from 'react';
import { authAPI } from '../api/client';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Restore session from localStorage
    const savedToken = localStorage.getItem('token');
    const savedUser = localStorage.getItem('user');

    if (savedToken && savedUser) {
      setToken(savedToken);
      setUser(JSON.parse(savedUser));
    }
    setLoading(false);
  }, []);

  const login = async (email, password) => {
    const response = await authAPI.login(email, password);
    const { access_token, user: userData } = response.data;

    setToken(access_token);
    setUser(userData);
    localStorage.setItem('token', access_token);
    localStorage.setItem('user', JSON.stringify(userData));

    return userData;
  };

  const registerTenant = async (companyName, adminName, adminEmail, adminPassword) => {
    const response = await authAPI.registerTenant({
      company_name: companyName,
      admin_name: adminName,
      admin_email: adminEmail,
      admin_password: adminPassword,
    });
    const { access_token, user: userData } = response.data;

    setToken(access_token);
    setUser(userData);
    localStorage.setItem('token', access_token);
    localStorage.setItem('user', JSON.stringify(userData));

    return userData;
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('token');
    localStorage.removeItem('user');
  };

  const isAdmin = user?.role === 'admin' || user?.role === 'tenant_admin' || user?.role === 'super_admin';
  const isSuperAdmin = user?.role === 'super_admin';
  const isAuthenticated = !!token;
  const tenantId = user?.tenant_id;
  const tenantName = user?.tenant_name;

  return (
    <AuthContext.Provider
      value={{
        user, token, loading,
        isAdmin, isSuperAdmin, isAuthenticated,
        tenantId, tenantName,
        login, registerTenant, logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
}
