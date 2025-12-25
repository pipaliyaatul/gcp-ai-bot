import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import axios from 'axios';
import './Login.scss';

const Login: React.FC = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  // Dummy credentials
  const DUMMY_USERNAME = 'admin';
  const DUMMY_PASSWORD = 'admin123';

  const handleDummyLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    
    if (!username || !password) {
      setError('Please enter both username and password');
      return;
    }

    if (username === DUMMY_USERNAME && password === DUMMY_PASSWORD) {
      login({ username, email: `${username}@example.com`, name: 'Admin User' });
      navigate('/chat');
    } else {
      setError('Invalid username or password');
    }
  };

  const handleGoogleLogin = async () => {
    setLoading(true);
    setError('');
    try {
      // Check if OAuth is configured by calling the endpoint first
      const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
      const response = await axios.get(`${API_URL}/auth/google`);
      
      if (response.data.auth_url) {
        // Redirect to backend OAuth endpoint
        window.location.href = response.data.auth_url;
      } else {
        throw new Error('No auth URL received');
      }
    } catch (err: any) {
      setLoading(false);
      if (err.response?.status === 400) {
        setError(err.response.data.detail || 'Google OAuth is not configured. Please use the dummy login (admin/admin123) or configure OAuth credentials.');
      } else {
        setError('Failed to initiate Google login. Please use the dummy login (admin/admin123) or check your configuration.');
      }
    }
  };

  return (
    <div className="login-container">
      <div className="login-box">
        <h1 className="login-title">ZS RFP Demo</h1>
        <h2 className="login-subtitle">Sign In</h2>
        
        <form onSubmit={handleDummyLogin} className="login-form">
          <div className="form-group">
            <label htmlFor="username">Username</label>
            <input
              type="text"
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Enter username"
              required
            />
          </div>
          
          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter password"
              required
            />
          </div>
          
          {error && <div className="error-message">{error}</div>}
          
          <button type="submit" className="btn btn-primary" disabled={loading}>
            {loading ? 'Logging in...' : 'Login'}
          </button>
        </form>
        
        <div className="divider">
          <span>OR</span>
        </div>
        
        <button
          onClick={handleGoogleLogin}
          className="btn btn-google"
          disabled={loading}
        >
          <svg className="google-icon" viewBox="0 0 24 24">
            <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
            <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
            <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
            <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
          </svg>
          Sign in with Google
        </button>
        
        <div className="login-info">
          <p>Dummy Credentials:</p>
          <p>Username: <strong>admin</strong></p>
          <p>Password: <strong>admin123</strong></p>
        </div>
      </div>
    </div>
  );
};

export default Login;

