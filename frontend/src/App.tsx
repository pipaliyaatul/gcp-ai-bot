import React, { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useSearchParams } from 'react-router-dom';
import Login from './components/Login';
import ChatInterface from './components/ChatInterface';
import Documents from './components/Documents';
import { AuthProvider, useAuth } from './context/AuthContext';
import './App.scss';

const OAuthCallback: React.FC = () => {
  const [searchParams] = useSearchParams();
  const { login } = useAuth();
  
  useEffect(() => {
    const auth = searchParams.get('auth');
    const userParam = searchParams.get('user');
    
    if (auth === 'success' && userParam) {
      try {
        const userInfo = JSON.parse(decodeURIComponent(userParam));
        login(userInfo);
      } catch (e) {
        console.error('Error parsing user info:', e);
      }
    }
  }, [searchParams, login]);
  
  return <Navigate to="/chat" />;
};

const PrivateRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();
  
  if (isLoading) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh' 
      }}>
        <div>Loading...</div>
      </div>
    );
  }
  
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" />;
};

const App: React.FC = () => {
  return (
    <AuthProvider>
      <Router>
        <div className="App">
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/auth/callback" element={<OAuthCallback />} />
            <Route
              path="/chat"
              element={
                <PrivateRoute>
                  <ChatInterface />
                </PrivateRoute>
              }
            />
            <Route
              path="/documents"
              element={
                <PrivateRoute>
                  <Documents />
                </PrivateRoute>
              }
            />
            <Route path="/" element={<Navigate to="/login" />} />
          </Routes>
        </div>
      </Router>
    </AuthProvider>
  );
};

export default App;

