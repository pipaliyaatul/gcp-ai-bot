import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import './Documents.scss';

interface DriveFile {
  id: string;
  name: string;
  createdTime: string;
  modifiedTime: string;
  webViewLink: string;
  mimeType: string;
  size?: string;
  downloadLink: string;
  editLink: string;
}

const Documents: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [files, setFiles] = useState<DriveFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

  useEffect(() => {
    fetchDocuments();
  }, []);

  const fetchDocuments = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Check if user has OAuth credentials (required for Google Drive access)
      if (!user || !user.credentials) {
        setError('Google Drive access requires Google OAuth login. Please log out and sign in with Google to view your documents.');
        setLoading(false);
        return;
      }

      const headers: Record<string, string> = {};
      
      // Add OAuth credentials
      try {
        const credsJson = JSON.stringify(user.credentials);
        headers['X-OAuth-Credentials'] = encodeURIComponent(credsJson);
      } catch (error) {
        console.error('Could not serialize OAuth credentials:', error);
        setError('Error preparing authentication. Please log out and log in again.');
        setLoading(false);
        return;
      }

      const response = await axios.get(`${API_URL}/api/documents?days=30`, {
        headers: headers,
      });

      if (response.data.success) {
        const filesList = response.data.files || [];
        // Sort by modifiedTime (most recently updated first)
        const sortedFiles = [...filesList].sort((a, b) => {
          const timeA = new Date(a.modifiedTime || a.createdTime).getTime();
          const timeB = new Date(b.modifiedTime || b.createdTime).getTime();
          return timeB - timeA; // Descending order (newest first)
        });
        setFiles(sortedFiles);
      } else {
        setError('Failed to fetch documents. Please try again.');
      }
    } catch (err: any) {
      console.error('Error fetching documents:', err);
      console.error('Error response:', err.response);
      
      if (err.response?.status === 401) {
        setError('Authentication required. Please log in with Google OAuth to view your documents. (Dummy login does not support Drive access)');
      } else if (err.response?.status === 403) {
        setError(err.response?.data?.detail || 'Insufficient permissions. Please ensure you granted Drive access during login.');
      } else if (err.response?.status === 404) {
        setError('API endpoint not found. Please check if the backend server is running.');
      } else if (err.response?.status) {
        setError(err.response?.data?.detail || err.response?.data?.message || `Error ${err.response.status}: Failed to fetch documents.`);
      } else if (err.message === 'Network Error' || err.code === 'ECONNREFUSED') {
        setError('Cannot connect to the server. Please ensure the backend is running.');
      } else {
        setError(err.response?.data?.detail || err.message || 'Failed to fetch documents. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = (file: DriveFile) => {
    window.open(file.downloadLink, '_blank');
  };

  const handleEdit = (file: DriveFile) => {
    window.open(file.editLink, '_blank');
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    // Format date in user's timezone with timezone abbreviation
    const options: Intl.DateTimeFormatOptions = {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      timeZoneName: 'short' // Shows timezone abbreviation (e.g., PST, EST)
    };
    return date.toLocaleString('en-US', options);
  };

  const formatFileSize = (bytes?: string) => {
    if (!bytes) return 'Unknown size';
    const size = parseInt(bytes);
    if (size < 1024) return `${size} B`;
    if (size < 1024 * 1024) return `${(size / 1024).toFixed(2)} KB`;
    return `${(size / (1024 * 1024)).toFixed(2)} MB`;
  };

  return (
    <div className="dashboard-container">
      {/* Left Sidebar */}
      <div className="sidebar">
        <div className="sidebar-header">
          <h1>ZS RFP Demo</h1>
          <div className="user-info">
            <span className="user-name">{user?.name || user?.username || 'User'}</span>
            <span className="user-email">{user?.email || ''}</span>
          </div>
        </div>
        
        <nav className="sidebar-nav">
          <button className="nav-item" onClick={() => navigate('/chat')}>
            <span className="nav-icon">💬</span>
            <span className="nav-label">Chat</span>
          </button>
          <button className="nav-item active">
            <span className="nav-icon">📄</span>
            <span className="nav-label">Documents</span>
          </button>
          <button className="nav-item" onClick={() => navigate('/chat')} title="Clear chat history">
            <span className="nav-icon">🗑️</span>
            <span className="nav-label">Clear History</span>
          </button>
        </nav>

        <div className="sidebar-footer">
          <button onClick={handleLogout} className="logout-btn">
            <span className="nav-icon">🚪</span>
            <span>Logout</span>
          </button>
        </div>
      </div>

      {/* Right Content Area */}
      <div className="content-area">
        <div className="documents-container">
          <div className="documents-header">
            <h2>My Documents</h2>
            <p>RFP summaries from the last 30 days</p>
            <button onClick={fetchDocuments} className="refresh-btn" disabled={loading}>
              {loading ? '🔄 Loading...' : '🔄 Refresh'}
            </button>
          </div>

          {loading && (
            <div className="loading-container">
              <div className="loading-spinner"></div>
              <p>Loading documents...</p>
            </div>
          )}

          {error && (
            <div className="error-container">
              <div className="error-message">
                <span className="error-icon">⚠️</span>
                <div>
                  <strong>Error loading documents</strong>
                  <p>{error}</p>
                </div>
              </div>
            </div>
          )}

          {!loading && !error && files.length === 0 && (
            <div className="empty-state">
              <div className="empty-icon">📭</div>
              <h3>No documents found</h3>
              <p>You haven't generated any RFP summaries in the last 30 days.</p>
              <button onClick={() => navigate('/chat')} className="primary-btn">
                Create Your First Document
              </button>
            </div>
          )}

          {!loading && !error && files.length > 0 && (
            <div className="documents-grid">
              {files.map((file) => (
                <div key={file.id} className="document-card">
                  <div className="document-header">
                    <div className="document-icon">📄</div>
                    <div className="document-title">{file.name}</div>
                  </div>
                  
                  <div className="document-info">
                    <div className="info-item">
                      <span className="info-label">Created:</span>
                      <span className="info-value">{formatDate(file.createdTime)}</span>
                    </div>
                    <div className="info-item">
                      <span className="info-label">Modified:</span>
                      <span className="info-value">{formatDate(file.modifiedTime)}</span>
                    </div>
                    <div className="info-item">
                      <span className="info-label">Size:</span>
                      <span className="info-value">{formatFileSize(file.size)}</span>
                    </div>
                  </div>

                  <div className="document-actions">
                    <button
                      onClick={() => handleEdit(file)}
                      className="action-btn edit-btn"
                      title="Edit document"
                    >
                      <span className="btn-icon">✏️</span>
                      <span>Edit</span>
                    </button>
                    <button
                      onClick={() => handleDownload(file)}
                      className="action-btn download-btn"
                      title="Download document"
                    >
                      <span className="btn-icon">⬇️</span>
                      <span>Download</span>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Documents;

