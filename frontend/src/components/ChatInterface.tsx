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
  statistics?: any; // LLM performance statistics
}

const MESSAGES_STORAGE_KEY = 'chat_messages';
const UPLOADED_FILES_KEY = 'uploaded_file_hashes';

// Configuration: Set to true to disable duplicate file checking (allows re-uploading same file)
// Can be overridden via environment variable REACT_APP_DISABLE_DUPLICATE_CHECK
const DISABLE_DUPLICATE_CHECK = process.env.REACT_APP_DISABLE_DUPLICATE_CHECK === 'true' || 
                                 localStorage.getItem('disable_duplicate_check') === 'true';

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
  // Skip check if disabled
  if (DISABLE_DUPLICATE_CHECK) {
    return false;
  }
  
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
  const [baseDocumentUploaded, setBaseDocumentUploaded] = useState(false);
  const [baseDocumentSections, setBaseDocumentSections] = useState<string[]>([]);
  const [baseDocumentUploading, setBaseDocumentUploading] = useState(false);
  const [showConsentDialog, setShowConsentDialog] = useState(false);
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const [pendingFileHash, setPendingFileHash] = useState<string | undefined>(undefined);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const baseDocumentInputRef = useRef<HTMLInputElement>(null);
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
    
    // Check if base document exists
    checkBaseDocument();
  }, []);
  
  const checkBaseDocument = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/base-document/structure`);
      if (response.data.success && response.data.sections) {
        setBaseDocumentUploaded(true);
        setBaseDocumentSections(response.data.sections);
      }
    } catch (error: any) {
      // Base document not found is OK
      if (error.response?.status !== 404) {
        console.warn('Error checking base document:', error);
      }
    }
  };
  
  const handleBaseDocumentUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    
    setBaseDocumentUploading(true);
    const formData = new FormData();
    formData.append('file', file);
    
    // Get OAuth credentials if available
    const headers: Record<string, string> = {};
    if (user && user.credentials) {
      try {
        const credsJson = JSON.stringify(user.credentials);
        headers['X-OAuth-Credentials'] = encodeURIComponent(credsJson);
      } catch (error) {
        console.warn('Could not add OAuth credentials:', error);
      }
    }
    
    try {
      const response = await axios.post(`${API_URL}/api/upload-base-document`, formData, {
        headers: headers,
      });
      
      if (response.data.success) {
        setBaseDocumentUploaded(true);
        setBaseDocumentSections(response.data.sections || []);
        
        // If consent dialog was open, close it and proceed with pending upload
        if (pendingFile) {
          setShowConsentDialog(false);
          // Proceed with the pending upload now that base document is uploaded
          await handleFileUpload(pendingFile, pendingFileHash);
          setPendingFile(null);
          setPendingFileHash(undefined);
        } else {
          setMessages(prev => [...prev, {
            type: 'assistant',
            content: `✅ Base RFP document uploaded successfully!\n\n**Document Structure:**\n${(response.data.sections || []).map((s: string, i: number) => `${i + 1}. ${s}`).join('\n')}\n\nAll future uploads will be aligned with this structure.`,
            timestamp: new Date()
          }]);
        }
      }
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to upload base document';
      setMessages(prev => [...prev, {
        type: 'assistant',
        content: `❌ Error uploading base document: ${errorMessage}`,
        timestamp: new Date()
      }]);
    } finally {
      setBaseDocumentUploading(false);
      if (baseDocumentInputRef.current) {
        baseDocumentInputRef.current.value = '';
      }
    }
  };

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

      // Calculate file hash and check if already uploaded (if not disabled)
      try {
        const fileHash = await calculateFileHash(file);
        
        // Only check for duplicates if the feature is enabled
        if (!DISABLE_DUPLICATE_CHECK && checkFileAlreadyUploaded(fileHash)) {
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
        // Only store hash if duplicate check is enabled
        await handleFileUpload(file, DISABLE_DUPLICATE_CHECK ? undefined : fileHash);
      } catch (error) {
        console.error('Error calculating file hash:', error);
        // If hash calculation fails, still allow upload
        setUploadedFile(file);
        await handleFileUpload(file);
      }
    }
  };

  const handleFileUpload = async (file?: File, fileHash?: string, proceedWithoutBase: boolean = false) => {
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
      // Add proceed_without_base parameter if user consented
      const params = proceedWithoutBase ? { params: { proceed_without_base: true } } : {};
      
      const response = await axios.post(`${API_URL}/api/upload`, formData, {
        headers: headers,
        ...params
      });

      // Check if user consent is required (no base document)
      if (response.data.requires_consent && response.data.action_required === 'user_consent') {
        // Store file for later upload after consent
        setPendingFile(fileToUpload);
        setPendingFileHash(fileHash);
        setShowConsentDialog(true);
        setFileProcessing(false);
        return;
      }

      if (response.data.success) {
        // Store file hash if provided and duplicate check is enabled
        if (!DISABLE_DUPLICATE_CHECK) {
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
        }

        setMessages(prev => [...prev, {
          type: 'user',
          content: `Uploaded file: ${fileToUpload.name}`,
          timestamp: new Date()
        }]);

        // Handle async processing (background jobs)
        if (response.data.async && response.data.job_id) {
          const jobId = response.data.job_id;
          setMessages(prev => [...prev, {
            type: 'assistant',
            content: '⏳ File uploaded successfully! Processing in background. This may take a few minutes for large audio files...',
            timestamp: new Date()
          }]);

          // Poll for job status
          pollJobStatus(jobId, fileToUpload.name);
          return;
        }

        // Handle synchronous processing (immediate response)
        setMessages(prev => [...prev, {
          type: 'assistant',
          content: response.data.message || 'File uploaded and processed successfully. Generating RFP summary...',
          timestamp: new Date()
        }]);

        if (response.data.download_link) {
          setDownloadLink(response.data.download_link);
          
          // Build statistics message if available
          let statsMessage = `RFP summary document has been generated and uploaded to Google Drive. You can download it using the link below.`;
          
          if (response.data.statistics) {
            const stats = response.data.statistics;
            statsMessage += `\n\n📊 **Generation Statistics:**\n`;
            statsMessage += `- Model: ${stats.model_name || 'N/A'}\n`;
            statsMessage += `- Total Tokens: ${stats.total_tokens || 0}\n`;
            statsMessage += `- Input Tokens: ${stats.input_tokens || 0}\n`;
            statsMessage += `- Output Tokens: ${stats.output_tokens || 0}\n`;
            statsMessage += `- Total Latency: ${stats.latency_ms || 0}ms\n`;
            if (stats.sections_generated) {
              statsMessage += `- Sections Generated: ${stats.sections_generated}\n`;
            }
            if (stats.generation_method) {
              statsMessage += `- Generation Method: ${stats.generation_method}\n`;
            }
            if (stats.generation_steps && stats.generation_steps.length > 0) {
              statsMessage += `- Generation Steps: ${stats.generation_steps.length}\n`;
            }
          }
          
          setMessages(prev => [...prev, {
            type: 'assistant',
            content: statsMessage,
            timestamp: new Date(),
            downloadLink: response.data.download_link,
            statistics: response.data.statistics
          }]);
        }

        setUploadedFile(null);
        if (fileInputRef.current) {
          fileInputRef.current.value = '';
        }
        setFileProcessing(false);
      }
    } catch (error: any) {
      console.error('Upload error:', error);
      const errorMessage = error.response?.data?.detail || error.response?.data?.message || error.message || 'Failed to upload file. Please try again.';
      
      setMessages(prev => [...prev, {
        type: 'assistant',
        content: `❌ Error: ${errorMessage}`,
        timestamp: new Date()
      }]);
      setFileProcessing(false);
    }
  };

  const pollJobStatus = async (jobId: string, fileName: string) => {
    const maxAttempts = 120; // 10 minutes max (5 second intervals)
    let attempts = 0;
    let statusMessageIndex: number | null = null;

    const poll = async () => {
      try {
        const response = await axios.get(`${API_URL}/api/upload/status/${jobId}`);
        const status = response.data;

        // Update or create status message
        setMessages(prev => {
          const updated = [...prev];
          
          // Find or create status message
          if (statusMessageIndex === null || !updated[statusMessageIndex]) {
            // Create new status message
            const newMsg = {
              type: 'assistant' as const,
              content: `🔄 Processing: ${status.message} (${status.progress}%)`,
              timestamp: new Date()
            };
            statusMessageIndex = updated.length;
            return [...updated, newMsg];
          } else {
            // Update existing status message
            updated[statusMessageIndex] = {
              ...updated[statusMessageIndex],
              content: `🔄 Processing: ${status.message} (${status.progress}%)`,
              timestamp: new Date()
            };
            return updated;
          }
        });

        if (status.status === 'completed' && status.result) {
          // Job completed successfully
          const result = status.result;
          setDownloadLink(result.download_link);
          
          // Build statistics message
          let statsMessage = `✅ ${result.message}`;
          
          if (result.statistics) {
            const stats = result.statistics;
            statsMessage += `\n\n📊 **Generation Statistics:**\n`;
            statsMessage += `- Model: ${stats.model_name || 'N/A'}\n`;
            statsMessage += `- Total Tokens: ${stats.total_tokens || 0}\n`;
            statsMessage += `- Input Tokens: ${stats.input_tokens || 0}\n`;
            statsMessage += `- Output Tokens: ${stats.output_tokens || 0}\n`;
            statsMessage += `- Total Latency: ${stats.latency_ms || 0}ms\n`;
            if (stats.sections_generated) {
              statsMessage += `- Sections Generated: ${stats.sections_generated}\n`;
            }
            if (stats.generation_method) {
              statsMessage += `- Generation Method: ${stats.generation_method}\n`;
            }
            if (stats.generation_steps && stats.generation_steps.length > 0) {
              statsMessage += `- Generation Steps: ${stats.generation_steps.length}\n`;
            }
          }
          
          setMessages(prev => {
            const updated = [...prev];
            if (statusMessageIndex !== null && updated[statusMessageIndex]) {
              updated[statusMessageIndex] = {
                ...updated[statusMessageIndex],
                content: statsMessage,
                downloadLink: result.download_link,
                statistics: result.statistics
              };
            }
            return updated;
          });

          setUploadedFile(null);
          if (fileInputRef.current) {
            fileInputRef.current.value = '';
          }
          setFileProcessing(false);
          return; // Stop polling
        }

        if (status.status === 'failed') {
          // Job failed
          setMessages(prev => {
            const updated = [...prev];
            if (statusMessageIndex !== null && updated[statusMessageIndex]) {
              updated[statusMessageIndex] = {
                ...updated[statusMessageIndex],
                content: `❌ Processing failed: ${status.error || status.message}`,
                timestamp: new Date()
              };
            }
            return updated;
          });
          setFileProcessing(false);
          return; // Stop polling
        }

        // Continue polling if still processing
        attempts++;
        if (attempts < maxAttempts) {
          setTimeout(poll, 5000); // Poll every 5 seconds
        } else {
          setMessages(prev => [...prev, {
            type: 'assistant',
            content: '⏱️ Processing is taking longer than expected. Please check back later or contact support.',
            timestamp: new Date()
          }]);
          setFileProcessing(false);
        }
      } catch (error: any) {
        console.error('Error polling job status:', error);
        attempts++;
        if (attempts < maxAttempts) {
          setTimeout(poll, 5000);
        } else {
          setMessages(prev => [...prev, {
            type: 'assistant',
            content: '❌ Error checking processing status. Please try again later.',
            timestamp: new Date()
          }]);
          setFileProcessing(false);
        }
      }
    };

    // Start polling
    poll();
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

  const handleProceedWithoutBase = async () => {
    if (!pendingFile) return;
    
    setShowConsentDialog(false);
    setFileProcessing(true);
    
    // Proceed with upload, passing proceed_without_base=true
    await handleFileUpload(pendingFile, pendingFileHash, true);
    
    setPendingFile(null);
    setPendingFileHash(undefined);
  };

  const handleCancelUpload = () => {
    setShowConsentDialog(false);
    setPendingFile(null);
    setPendingFileHash(undefined);
    setFileProcessing(false);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
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
            
            {/* Base Document Upload Section */}
            <div style={{ marginTop: '15px', padding: '10px', backgroundColor: baseDocumentUploaded ? '#e8f5e9' : '#fff3cd', borderRadius: '5px', border: `1px solid ${baseDocumentUploaded ? '#4caf50' : '#ffc107'}` }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '5px' }}>
                <strong style={{ fontSize: '14px' }}>
                  {baseDocumentUploaded ? '✅ Base Document Uploaded' : '📄 Upload Base RFP Document'}
                </strong>
                {baseDocumentUploaded && (
                  <span style={{ fontSize: '12px', color: '#666' }}>
                    {baseDocumentSections.length} sections
                  </span>
                )}
              </div>
              {baseDocumentUploaded && baseDocumentSections.length > 0 && (
                <div style={{ fontSize: '12px', color: '#666', marginTop: '5px' }}>
                  Sections: {baseDocumentSections.slice(0, 3).join(', ')}
                  {baseDocumentSections.length > 3 && ` +${baseDocumentSections.length - 3} more`}
                </div>
              )}
              <input
                ref={baseDocumentInputRef}
                type="file"
                accept=".pdf,.docx,.txt"
                onChange={handleBaseDocumentUpload}
                style={{ display: 'none' }}
              />
              <button
                onClick={() => baseDocumentInputRef.current?.click()}
                disabled={baseDocumentUploading}
                style={{
                  marginTop: '8px',
                  padding: '6px 12px',
                  fontSize: '12px',
                  backgroundColor: baseDocumentUploaded ? '#4caf50' : '#ffc107',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: baseDocumentUploading ? 'not-allowed' : 'pointer',
                  opacity: baseDocumentUploading ? 0.6 : 1
                }}
              >
                {baseDocumentUploading ? 'Uploading...' : (baseDocumentUploaded ? 'Replace Base Document' : 'Upload Base Document')}
              </button>
            </div>
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
                  <div style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</div>
                  {msg.downloadLink && (
                    <div className="download-section">
                      <button onClick={() => window.open(msg.downloadLink, '_blank')} className="download-btn">
                        Download RFP Summary
                      </button>
                    </div>
                  )}
                  {msg.statistics && (
                    <details className="statistics-section" style={{ marginTop: '10px', padding: '10px', backgroundColor: '#f5f5f5', borderRadius: '5px' }}>
                      <summary style={{ cursor: 'pointer', fontWeight: 'bold' }}>📊 View Detailed Statistics</summary>
                      <pre style={{ marginTop: '10px', fontSize: '12px', overflow: 'auto' }}>
                        {JSON.stringify(msg.statistics, null, 2)}
                      </pre>
                    </details>
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

          {/* Consent Dialog for Missing Base Document */}
          {showConsentDialog && (
            <div style={{
              position: 'fixed',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              backgroundColor: 'rgba(0, 0, 0, 0.5)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 1000
            }}>
              <div style={{
                backgroundColor: 'white',
                padding: '30px',
                borderRadius: '10px',
                maxWidth: '500px',
                width: '90%',
                boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)'
              }}>
                <h3 style={{ marginTop: 0, color: '#ff9800' }}>⚠️ Base Document Not Found</h3>
                <p style={{ margin: '15px 0', lineHeight: '1.6' }}>
                  A base RFP document has not been uploaded. The generated content will use <strong>default sections</strong> which may differ from your expected structure.
                </p>
                <div style={{
                  backgroundColor: '#fff3cd',
                  padding: '15px',
                  borderRadius: '5px',
                  margin: '15px 0',
                  border: '1px solid #ffc107'
                }}>
                  <strong>What this means:</strong>
                  <ul style={{ margin: '10px 0', paddingLeft: '20px' }}>
                    <li>Generated document will use standard RFP sections</li>
                    <li>Content structure may not match your requirements</li>
                    <li>Formatting may differ from your template</li>
                  </ul>
                </div>
                <p style={{ margin: '15px 0', fontSize: '14px', color: '#666' }}>
                  <strong>Recommendation:</strong> Upload a base RFP document template first to ensure consistent formatting and structure.
                </p>
                <div style={{
                  display: 'flex',
                  gap: '10px',
                  justifyContent: 'flex-end',
                  marginTop: '20px'
                }}>
                  <button
                    onClick={handleCancelUpload}
                    style={{
                      padding: '10px 20px',
                      backgroundColor: '#f5f5f5',
                      border: '1px solid #ddd',
                      borderRadius: '5px',
                      cursor: 'pointer',
                      fontSize: '14px'
                    }}
                  >
                    Cancel
                  </button>
                  <button
                    onClick={() => baseDocumentInputRef.current?.click()}
                    style={{
                      padding: '10px 20px',
                      backgroundColor: '#ffc107',
                      color: 'white',
                      border: 'none',
                      borderRadius: '5px',
                      cursor: 'pointer',
                      fontSize: '14px',
                      marginRight: '10px'
                    }}
                  >
                    Upload Base Document
                  </button>
                  <button
                    onClick={handleProceedWithoutBase}
                    style={{
                      padding: '10px 20px',
                      backgroundColor: '#2196F3',
                      color: 'white',
                      border: 'none',
                      borderRadius: '5px',
                      cursor: 'pointer',
                      fontSize: '14px',
                      fontWeight: 'bold'
                    }}
                  >
                    Proceed Anyway
                  </button>
                </div>
              </div>
            </div>
          )}

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
