import React, { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useSearchParams } from 'react-router-dom';
import Login from './components/Login';
import ChatInterface from './components/ChatInterface';
import { AuthProvider, useAuth } from './context/AuthContext';
import './App.css';

const OAuthCallback = () => {
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

const PrivateRoute = ({ children }) => {
  const { isAuthenticated } = useAuth();
  return isAuthenticated ? children : <Navigate to="/login" />;
};

function App() {
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
            <Route path="/" element={<Navigate to="/login" />} />
          </Routes>
        </div>
      </Router>
    </AuthProvider>
  );
}

export default App;

