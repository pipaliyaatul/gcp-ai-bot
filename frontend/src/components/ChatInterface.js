import React, { useState, useRef, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import './ChatInterface.css';

const ChatInterface = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [uploadedFile, setUploadedFile] = useState(null);
  const [fileProcessing, setFileProcessing] = useState(false);
  const [downloadLink, setDownloadLink] = useState(null);
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);

  const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      // Validate file type
      const allowedTextTypes = ['.pdf', '.docx', '.txt'];
      const allowedAudioTypes = ['.wav', '.m4a', '.mp3'];
      const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
      
      if (!allowedTextTypes.includes(fileExtension) && !allowedAudioTypes.includes(fileExtension)) {
        alert('Invalid file type. Please upload .pdf, .docx, .txt, .wav, .m4a, or .mp3 files.');
        return;
      }

      // Check if file is not blank
      if (file.size === 0) {
        alert('File is empty. Please upload a non-empty file.');
        return;
      }

      setUploadedFile(file);
    }
  };

  const handleFileUpload = async () => {
    if (!uploadedFile) {
      alert('Please select a file first');
      return;
    }

    setFileProcessing(true);
    const formData = new FormData();
    formData.append('file', uploadedFile);

    // Get OAuth credentials from user data if available
    const headers = {};
    
    // Add OAuth credentials if user is authenticated with Google
    if (user && user.credentials) {
      try {
        // Encode credentials as JSON string for header
        const credsJson = JSON.stringify(user.credentials);
        headers['X-OAuth-Credentials'] = encodeURIComponent(credsJson);
      } catch (error) {
        console.warn('Could not add OAuth credentials:', error);
      }
    }

    try {
      const response = await axios.post(`${API_URL}/api/upload`, formData, {
        headers: headers,
        // Let axios set Content-Type automatically for FormData
      });

      if (response.data.success) {
        setMessages(prev => [...prev, {
          type: 'user',
          content: `Uploaded file: ${uploadedFile.name}`,
          timestamp: new Date()
        }, {
          type: 'assistant',
          content: response.data.message || 'File uploaded and processed successfully. Generating RFP summary...',
          timestamp: new Date()
        }]);

        if (response.data.download_link) {
          setDownloadLink(response.data.download_link);
          setMessages(prev => [...prev, {
            type: 'assistant',
            content: `RFP summary document has been generated and uploaded to Google Drive. You can download it using the link below.`,
            timestamp: new Date(),
            downloadLink: response.data.download_link
          }]);
        }

        setUploadedFile(null);
        if (fileInputRef.current) {
          fileInputRef.current.value = '';
        }
      }
    } catch (error) {
      console.error('Upload error:', error);
      const errorMessage = error.response?.data?.detail || error.response?.data?.message || error.message || 'Failed to upload file. Please try again.';
      
      setMessages(prev => [...prev, {
        type: 'assistant',
        content: `❌ Error: ${errorMessage}`,
        timestamp: new Date()
      }]);
    } finally {
      setFileProcessing(false);
    }
  };

  const handleSendMessage = async () => {
    if (!inputMessage.trim() && !uploadedFile) return;

    const userMessage = {
      type: 'user',
      content: inputMessage,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setLoading(true);

    try {
      const response = await axios.post(`${API_URL}/api/chat`, {
        message: inputMessage,
      });

      setMessages(prev => [...prev, {
        type: 'assistant',
        content: response.data.response || 'I received your message.',
        timestamp: new Date()
      }]);
    } catch (error) {
      console.error('Chat error:', error);
      setMessages(prev => [...prev, {
        type: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date()
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = () => {
    if (downloadLink) {
      window.open(downloadLink, '_blank');
    }
  };

  return (
    <div className="chat-container">
      <div className="chat-header">
        <div className="header-left">
          <h1>ZS RFP Demo</h1>
          <span className="user-info">Welcome, {user?.name || user?.username || 'User'}</span>
        </div>
        <button onClick={handleLogout} className="logout-btn">
          Logout
        </button>
      </div>

      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="welcome-message">
            <h2>Welcome to ZS RFP Demo</h2>
            <p>Upload a file or start chatting with the AI agent to generate RFP summaries.</p>
          </div>
        )}
        
        {messages.map((msg, idx) => (
          <div key={idx} className={`message ${msg.type}`}>
            <div className="message-content">
              {msg.content}
              {msg.downloadLink && (
                <div className="download-section">
                  <button onClick={() => window.open(msg.downloadLink, '_blank')} className="download-btn">
                    Download RFP Summary
                  </button>
                </div>
              )}
            </div>
            <div className="message-timestamp">
              {msg.timestamp.toLocaleTimeString()}
            </div>
          </div>
        ))}
        
        {loading && (
          <div className="message assistant">
            <div className="message-content">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      <div className="file-upload-section">
        <input
          ref={fileInputRef}
          type="file"
          id="file-input"
          accept=".pdf,.docx,.txt,.wav,.m4a,.mp3"
          onChange={handleFileSelect}
          style={{ display: 'none' }}
        />
        <label htmlFor="file-input" className="file-input-label">
          📎 Choose File
        </label>
        {uploadedFile && (
          <div className="file-info">
            <span>{uploadedFile.name}</span>
            <button onClick={handleFileUpload} className="upload-btn" disabled={fileProcessing}>
              {fileProcessing ? 'Processing...' : 'Upload & Process'}
            </button>
          </div>
        )}
      </div>

      <div className="chat-input-container">
        <input
          type="text"
          value={inputMessage}
          onChange={(e) => setInputMessage(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
          placeholder="Type your message..."
          className="chat-input"
          disabled={loading}
        />
        <button
          onClick={handleSendMessage}
          className="send-btn"
          disabled={loading || (!inputMessage.trim() && !uploadedFile)}
        >
          Send
        </button>
      </div>
    </div>
  );
};

export default ChatInterface;

