import React, { useState, useRef, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import './ChatInterface.scss';

interface Message {
  type: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  downloadLink?: string;
}

const MESSAGES_STORAGE_KEY = 'chat_messages';
const UPLOADED_FILES_KEY = 'uploaded_file_hashes';

// Helper function to calculate file hash
const calculateFileHash = async (file: File): Promise<string> => {
  const arrayBuffer = await file.arrayBuffer();
  const hashBuffer = await crypto.subtle.digest('SHA-256', arrayBuffer);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
  return hashHex;
};

// Helper function to check if file was already uploaded
const checkFileAlreadyUploaded = (fileHash: string): boolean => {
  const storedHashes = localStorage.getItem(UPLOADED_FILES_KEY);
  if (!storedHashes) return false;
  
  try {
    const hashes: string[] = JSON.parse(storedHashes);
    return hashes.includes(fileHash);
  } catch {
    return false;
  }
};

// Helper function to store file hash
const storeFileHash = (fileHash: string) => {
  const storedHashes = localStorage.getItem(UPLOADED_FILES_KEY);
  let hashes: string[] = [];
  
  if (storedHashes) {
    try {
      hashes = JSON.parse(storedHashes);
    } catch {
      hashes = [];
    }
  }
  
  if (!hashes.includes(fileHash)) {
    hashes.push(fileHash);
    localStorage.setItem(UPLOADED_FILES_KEY, JSON.stringify(hashes));
  }
};

const ChatInterface: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [fileProcessing, setFileProcessing] = useState(false);
  const [downloadLink, setDownloadLink] = useState<string | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [mediaRecorder, setMediaRecorder] = useState<MediaRecorder | null>(null);
  const [audioChunks, setAudioChunks] = useState<Blob[]>([]);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const audioRecorderRef = useRef<MediaRecorder | null>(null);

  const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

  // Load messages from localStorage on mount
  useEffect(() => {
    const storedMessages = localStorage.getItem(MESSAGES_STORAGE_KEY);
    if (storedMessages) {
      try {
        const parsed = JSON.parse(storedMessages);
        const restoredMessages: Message[] = parsed.map((msg: any) => ({
          ...msg,
          timestamp: new Date(msg.timestamp)
        }));
        setMessages(restoredMessages);
      } catch (error) {
        console.error('Error loading messages from storage:', error);
      }
    }
  }, []);

  // Save messages to localStorage whenever they change
  useEffect(() => {
    if (messages.length > 0) {
      localStorage.setItem(MESSAGES_STORAGE_KEY, JSON.stringify(messages));
    }
  }, [messages]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleLogout = () => {
    // Chat history is preserved in localStorage and will be available when user logs back in
    logout();
    navigate('/login');
  };

  const handleClearChatHistory = () => {
    if (window.confirm('Are you sure you want to clear all chat history? This action cannot be undone.')) {
      setMessages([]);
      localStorage.removeItem(MESSAGES_STORAGE_KEY);
    }
  };

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      // Validate file type
      const allowedTextTypes = ['.pdf', '.docx', '.txt'];
      const allowedAudioTypes = ['.wav', '.m4a', '.mp3', '.webm'];
      const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase();
      
      if (!allowedTextTypes.includes(fileExtension) && !allowedAudioTypes.includes(fileExtension)) {
        alert('Invalid file type. Please upload .pdf, .docx, .txt, .wav, .m4a, .mp3, or .webm files.');
        return;
      }

      // Check if file is not blank
      if (file.size === 0) {
        alert('File is empty. Please upload a non-empty file.');
        return;
      }

      // Calculate file hash and check if already uploaded
      try {
        const fileHash = await calculateFileHash(file);
        if (checkFileAlreadyUploaded(fileHash)) {
          setMessages(prev => [...prev, {
            type: 'assistant',
            content: '⚠️ This file has already been uploaded. You can visit the Documents section to view it, or upload a different file.',
            timestamp: new Date()
          }]);
          if (fileInputRef.current) {
            fileInputRef.current.value = '';
          }
          return;
        }

        setUploadedFile(file);
        // Auto-upload when file is selected
        await handleFileUpload(file, fileHash);
      } catch (error) {
        console.error('Error calculating file hash:', error);
        // If hash calculation fails, still allow upload
        setUploadedFile(file);
        await handleFileUpload(file);
      }
    }
  };

  const handleFileUpload = async (file?: File, fileHash?: string) => {
    const fileToUpload = file || uploadedFile;
    if (!fileToUpload) {
      alert('Please select a file first');
      return;
    }

    setFileProcessing(true);
    const formData = new FormData();
    formData.append('file', fileToUpload);

    // Get OAuth credentials from user data if available
    const headers: Record<string, string> = {};
    
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
      });

      if (response.data.success) {
        // Store file hash if provided
        if (fileHash) {
          storeFileHash(fileHash);
        } else {
          // Calculate hash if not provided
          try {
            const hash = await calculateFileHash(fileToUpload);
            storeFileHash(hash);
          } catch (error) {
            console.warn('Could not store file hash:', error);
          }
        }

        setMessages(prev => [...prev, {
          type: 'user',
          content: `Uploaded file: ${fileToUpload.name}`,
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
    } catch (error: any) {
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

    const userMessage: Message = {
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

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      
      // Try to use a supported format, fallback to default
      let mimeType = 'audio/webm';
      if (MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
        mimeType = 'audio/webm;codecs=opus';
      } else if (MediaRecorder.isTypeSupported('audio/mp4')) {
        mimeType = 'audio/mp4';
      }
      
      const recorder = new MediaRecorder(stream, { mimeType });
      const chunks: Blob[] = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunks.push(e.data);
        }
      };

      recorder.onstop = async () => {
        // Determine file extension based on mime type
        let extension = 'webm';
        if (mimeType.includes('mp4')) {
          extension = 'm4a';
        } else if (mimeType.includes('webm')) {
          extension = 'webm';
        }
        
        const audioBlob = new Blob(chunks, { type: mimeType });
        const audioFile = new File([audioBlob], `recording-${Date.now()}.${extension}`, { type: mimeType });
        
        // For audio recordings, we'll skip hash check since they're unique by timestamp
        setUploadedFile(audioFile);
        await handleFileUpload(audioFile);
        
        // Stop all tracks
        stream.getTracks().forEach(track => track.stop());
      };

      recorder.start();
      setMediaRecorder(recorder);
      audioRecorderRef.current = recorder;
      setIsRecording(true);
      setAudioChunks(chunks);
    } catch (error) {
      console.error('Error starting recording:', error);
      alert('Could not access microphone. Please check permissions.');
    }
  };

  const stopRecording = () => {
    if (audioRecorderRef.current && isRecording) {
      audioRecorderRef.current.stop();
      setIsRecording(false);
      setMediaRecorder(null);
    }
  };

  const handleDownload = () => {
    if (downloadLink) {
      window.open(downloadLink, '_blank');
    }
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
          <button className="nav-item active">
            <span className="nav-icon">💬</span>
            <span className="nav-label">Chat</span>
          </button>
          <button className="nav-item" onClick={() => navigate('/documents')}>
            <span className="nav-icon">📄</span>
            <span className="nav-label">Documents</span>
          </button>
          <button className="nav-item" onClick={handleClearChatHistory} title="Clear chat history">
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
        <div className="chat-container">
          <div className="chat-header">
            <h2>RFP Assistant</h2>
            <p>Ask questions or upload documents to generate RFP summaries</p>
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

          {/* Integrated Chat Input with File Upload and Audio Recording */}
          <div className="chat-input-container">
            {uploadedFile && !fileProcessing && (
              <div className="file-preview">
                <span className="file-name">📎 {uploadedFile.name}</span>
                <button 
                  className="remove-file-btn"
                  onClick={() => {
                    setUploadedFile(null);
                    if (fileInputRef.current) {
                      fileInputRef.current.value = '';
                    }
                  }}
                >
                  ×
                </button>
              </div>
            )}
            
            <div className="input-wrapper">
              <input
                ref={fileInputRef}
                type="file"
                id="file-input"
                accept=".pdf,.docx,.txt,.wav,.m4a,.mp3,.webm"
                onChange={handleFileSelect}
                style={{ display: 'none' }}
              />
              
              <input
                type="text"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && !e.shiftKey && handleSendMessage()}
                placeholder="Type your message..."
                className="chat-input"
                disabled={loading || fileProcessing}
              />

              <div className="input-actions">
                <button
                  className="input-action-btn"
                  onClick={() => fileInputRef.current?.click()}
                  title="Attach file"
                  disabled={fileProcessing || loading}
                >
                  📎
                </button>

                <button
                  className={`input-action-btn record-btn ${isRecording ? 'recording' : ''}`}
                  onClick={isRecording ? stopRecording : startRecording}
                  title={isRecording ? 'Stop recording' : 'Record audio'}
                  disabled={fileProcessing || loading}
                >
                  {isRecording ? '⏹️' : '🎤'}
                </button>

                <button
                  onClick={handleSendMessage}
                  className="send-btn"
                  disabled={loading || fileProcessing || (!inputMessage.trim() && !uploadedFile)}
                >
                  Send
                </button>
              </div>
            </div>
            
            {fileProcessing && (
              <div className="processing-indicator">
                Processing file...
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatInterface;
