/**
 * App — Root component with routing and session management.
 */

import { useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import ProtectedRoute from './components/common/ProtectedRoute';
import LoginPage from './components/Auth/LoginPage';
import Sidebar from './components/Layout/Sidebar';
import ChatWindow from './components/Chat/ChatWindow';
import AdminPanel from './components/Admin/AdminPanel';
import PlatformDashboard from './components/SuperAdmin/PlatformDashboard';

function AppRoutes() {
  const { isAuthenticated } = useAuth();
  const [activeSessionId, setActiveSessionId] = useState(null);

  const handleNewChat = () => {
    setActiveSessionId(null);
  };

  const handleSelectSession = (sessionId) => {
    setActiveSessionId(sessionId);
  };

  return (
    <Routes>
      <Route
        path="/login"
        element={isAuthenticated ? <Navigate to="/" replace /> : <LoginPage />}
      />

      <Route
        path="/"
        element={
          <ProtectedRoute>
            <div>
              <Sidebar
                onNewChat={handleNewChat}
                activeSessionId={activeSessionId}
                onSelectSession={handleSelectSession}
              />
              <ChatWindow
                activeSessionId={activeSessionId}
                onSessionCreated={(id) => setActiveSessionId(id)}
              />
            </div>
          </ProtectedRoute>
        }
      />

      <Route
        path="/admin"
        element={
          <ProtectedRoute requireAdmin>
            <div>
              <Sidebar
                onNewChat={handleNewChat}
                activeSessionId={activeSessionId}
                onSelectSession={handleSelectSession}
              />
              <AdminPanel />
            </div>
          </ProtectedRoute>
        }
      />

      <Route
        path="/superadmin"
        element={
          <ProtectedRoute requireSuperAdmin>
            <div>
              <Sidebar
                onNewChat={handleNewChat}
                activeSessionId={activeSessionId}
                onSelectSession={handleSelectSession}
              />
              <PlatformDashboard />
            </div>
          </ProtectedRoute>
        }
      />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
