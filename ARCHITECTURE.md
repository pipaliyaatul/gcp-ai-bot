# ZS-RFP-Demo Architecture Diagrams

This document contains Mermaid diagrams illustrating the architecture of the ZS-RFP-Demo application.

## System Architecture Overview

```mermaid
graph TB
    subgraph "Client Layer"
        User[👤 User]
        Browser[🌐 Web Browser]
    end
    
    subgraph "Frontend - React Application"
        Login[Login Component]
        ChatUI[ChatInterface Component]
        AuthCtx[AuthContext]
        Router[React Router]
    end
    
    subgraph "Backend - FastAPI Application"
        API[FastAPI App]
        AuthService[Auth Service]
        FileProcessor[File Processor]
        RFPGenerator[RFP Generator]
        DriveService[Drive Service]
    end
    
    subgraph "Google Cloud Platform"
        OAuth[Google OAuth 2.0]
        SpeechAPI[Speech-to-Text API]
        DriveAPI[Google Drive API]
        DocAI[Document AI API<br/>Optional]
        ServiceAccount[Service Account]
    end
    
    subgraph "Storage"
        LocalStorage[Browser LocalStorage]
        GoogleDrive[Google Drive Storage]
        TempFiles[Temporary Files]
    end
    
    User --> Browser
    Browser --> Login
    Browser --> ChatUI
    Login --> AuthCtx
    ChatUI --> AuthCtx
    AuthCtx --> LocalStorage
    
    ChatUI -->|HTTP/REST| API
    Login -->|OAuth Flow| API
    
    API --> AuthService
    API --> FileProcessor
    API --> RFPGenerator
    API --> DriveService
    
    AuthService --> OAuth
    FileProcessor --> SpeechAPI
    FileProcessor --> DocAI
    DriveService --> DriveAPI
    DriveService --> ServiceAccount
    
    DriveService --> GoogleDrive
    FileProcessor --> TempFiles
    
    style User fill:#e1f5ff
    style Browser fill:#fff4e1
    style API fill:#e8f5e9
    style GoogleDrive fill:#f3e5f5
```

## Component Architecture

```mermaid
graph LR
    subgraph "Frontend Components"
        A[App.js<br/>Main App Router]
        B[Login.js<br/>Authentication UI]
        C[ChatInterface.js<br/>Main Chat UI]
        D[AuthContext.js<br/>Auth State Management]
    end
    
    subgraph "Backend Services"
        E[app.py<br/>FastAPI Routes]
        F[auth_service.py<br/>OAuth Handler]
        G[file_processor.py<br/>File Processing]
        H[rfp_generator.py<br/>RFP Document Generator]
        I[drive_service.py<br/>Drive Integration]
    end
    
    subgraph "External Services"
        J[Google OAuth]
        K[Speech-to-Text]
        L[Google Drive]
    end
    
    A --> B
    A --> C
    B --> D
    C --> D
    
    E --> F
    E --> G
    E --> H
    E --> I
    
    F --> J
    G --> K
    I --> L
    
    C -.->|API Calls| E
    
    style A fill:#bbdefb
    style E fill:#c8e6c9
    style J fill:#fff9c4
    style K fill:#fff9c4
    style L fill:#fff9c4
```

## File Upload & Processing Flow

```mermaid
sequenceDiagram
    participant User
    participant Frontend as React Frontend
    participant API as FastAPI Backend
    participant FileProc as File Processor
    participant SpeechAPI as Speech-to-Text API
    participant RFPGen as RFP Generator
    participant DriveSvc as Drive Service
    participant GoogleDrive as Google Drive
    
    User->>Frontend: Upload File (PDF/DOCX/TXT/Audio)
    Frontend->>Frontend: Validate File Type & Size
    Frontend->>API: POST /api/upload<br/>(with OAuth credentials)
    
    API->>API: Parse OAuth Credentials
    API->>FileProc: Extract Text/Transcribe Audio
    
    alt Text File (PDF/DOCX/TXT)
        FileProc->>FileProc: Extract text using<br/>PyPDF2/python-docx
    else Audio File (WAV/M4A/MP3)
        FileProc->>SpeechAPI: Transcribe audio
        SpeechAPI-->>FileProc: Return transcript
    end
    
    FileProc-->>API: Extracted Text
    API->>RFPGen: Generate RFP Summary
    RFPGen->>RFPGen: Create DOCX document<br/>(Executive Summary, Requirements, etc.)
    RFPGen-->>API: RFP Document (DOCX)
    
    API->>DriveSvc: Upload Document to Drive
    DriveSvc->>GoogleDrive: Upload DOCX file<br/>(using OAuth or Service Account)
    GoogleDrive-->>DriveSvc: File ID & Shareable Link
    DriveSvc-->>API: Download Link
    
    API-->>Frontend: Success Response<br/>(with download link)
    Frontend->>Frontend: Display Download Link
    Frontend-->>User: Show Success Message
    User->>GoogleDrive: Download RFP Summary
```

## Authentication Flow

```mermaid
sequenceDiagram
    participant User
    participant Frontend as React Frontend
    participant API as FastAPI Backend
    participant AuthSvc as Auth Service
    participant GoogleOAuth as Google OAuth
    participant LocalStorage as Browser Storage
    
    alt Dummy Login
        User->>Frontend: Enter username/password<br/>(admin/admin123)
        Frontend->>Frontend: Validate Credentials
        Frontend->>LocalStorage: Store Auth State
        Frontend-->>User: Redirect to Chat
    else Google OAuth Login
        User->>Frontend: Click "Login with Google"
        Frontend->>API: GET /auth/google
        API->>AuthSvc: Generate OAuth URL
        AuthSvc->>GoogleOAuth: Create OAuth Flow
        GoogleOAuth-->>AuthSvc: Authorization URL
        AuthSvc-->>API: Return Auth URL
        API-->>Frontend: Return Auth URL
        Frontend->>GoogleOAuth: Redirect to Google
        GoogleOAuth->>User: Show Consent Screen
        User->>GoogleOAuth: Grant Permissions
        GoogleOAuth->>API: GET /auth/google/callback?code=xxx
        API->>AuthSvc: Handle Callback
        AuthSvc->>GoogleOAuth: Exchange Code for Tokens
        GoogleOAuth-->>AuthSvc: Access Token + User Info
        AuthSvc->>AuthSvc: Extract User Info & Credentials
        AuthSvc-->>API: User Info + OAuth Credentials
        API->>Frontend: Redirect with User Data
        Frontend->>Frontend: Parse User Data
        Frontend->>LocalStorage: Store User + Credentials
        Frontend-->>User: Redirect to Chat Interface
    end
```

## Data Flow Diagram

```mermaid
flowchart TD
    Start([User Action]) --> Choice{Action Type?}
    
    Choice -->|Login| LoginFlow[Login Flow]
    Choice -->|Upload File| UploadFlow[File Upload Flow]
    Choice -->|Chat Message| ChatFlow[Chat Flow]
    
    LoginFlow --> AuthCheck{Authentication<br/>Method?}
    AuthCheck -->|Dummy| DummyAuth[Validate<br/>admin/admin123]
    AuthCheck -->|OAuth| OAuthFlow[Google OAuth<br/>Flow]
    DummyAuth --> StoreAuth[Store in<br/>LocalStorage]
    OAuthFlow --> StoreAuth
    StoreAuth --> End1([Authenticated])
    
    UploadFlow --> ValidateFile[Validate File<br/>Type & Size]
    ValidateFile --> ExtractContent{File Type?}
    ExtractContent -->|Text| ExtractText[Extract Text<br/>PDF/DOCX/TXT]
    ExtractContent -->|Audio| Transcribe[Transcribe Audio<br/>Speech-to-Text API]
    ExtractText --> GenerateRFP[Generate RFP<br/>Summary Document]
    Transcribe --> GenerateRFP
    GenerateRFP --> UploadDrive[Upload to<br/>Google Drive]
    UploadDrive --> ReturnLink[Return Download<br/>Link to User]
    ReturnLink --> End2([File Processed])
    
    ChatFlow --> SendMessage[Send Message to<br/>API /api/chat]
    SendMessage --> ProcessChat[Process Chat<br/>with AI Agent]
    ProcessChat --> ReturnResponse[Return AI<br/>Response]
    ReturnResponse --> End3([Message Displayed])
    
    style Start fill:#e1f5ff
    style End1 fill:#c8e6c9
    style End2 fill:#c8e6c9
    style End3 fill:#c8e6c9
    style OAuthFlow fill:#fff9c4
    style Transcribe fill:#fff9c4
    style UploadDrive fill:#fff9c4
```

## Service Dependencies

```mermaid
graph TD
    subgraph "Backend Services"
        App[app.py<br/>FastAPI Application]
        Auth[AuthService<br/>Authentication]
        File[FileProcessor<br/>File Processing]
        RFP[RFPGenerator<br/>RFP Generation]
        Drive[DriveService<br/>Drive Integration]
    end
    
    subgraph "External Dependencies"
        GCP[Google Cloud Platform]
        OAuth[Google OAuth 2.0]
        Speech[Speech-to-Text API]
        DriveAPI[Drive API]
        DocAI[Document AI API]
    end
    
    subgraph "Python Libraries"
        FastAPI[FastAPI Framework]
        Docx[python-docx]
        PyPDF[PyPDF2]
        GoogleLib[Google API Client]
    end
    
    App --> Auth
    App --> File
    App --> RFP
    App --> Drive
    
    Auth --> OAuth
    Auth --> GoogleLib
    File --> Speech
    File --> DocAI
    File --> PyPDF
    File --> Docx
    Drive --> DriveAPI
    Drive --> GoogleLib
    
    OAuth --> GCP
    Speech --> GCP
    DriveAPI --> GCP
    DocAI --> GCP
    
    App --> FastAPI
    
    style App fill:#4caf50
    style GCP fill:#ff9800
    style FastAPI fill:#009688
```

## Deployment Architecture

```mermaid
graph TB
    subgraph "User Devices"
        User[👤 Users]
    end
    
    subgraph "Cloud Run Services"
        FrontendSvc[Frontend Service<br/>React + Nginx<br/>Port 80]
        BackendSvc[Backend Service<br/>FastAPI + Uvicorn<br/>Port 8000]
    end
    
    subgraph "Google Cloud Platform"
        CloudRun[Cloud Run]
        IAM[IAM & Service Accounts]
        APIs[GCP APIs<br/>Drive, Speech-to-Text]
    end
    
    subgraph "Storage & Configuration"
        Secrets[Secret Manager<br/>Credentials]
        DriveStorage[Google Drive<br/>Document Storage]
    end
    
    User -->|HTTPS| FrontendSvc
    FrontendSvc -->|API Calls| BackendSvc
    BackendSvc -->|Authenticate| IAM
    BackendSvc -->|Access| APIs
    BackendSvc -->|Read| Secrets
    BackendSvc -->|Upload| DriveStorage
    
    FrontendSvc -.->|Deployed on| CloudRun
    BackendSvc -.->|Deployed on| CloudRun
    
    style User fill:#e1f5ff
    style CloudRun fill:#ff9800
    style DriveStorage fill:#9c27b0
    style Secrets fill:#f44336
```

## Environment Configuration

```mermaid
graph LR
    subgraph "Backend Environment Variables"
        BE1[GOOGLE_APPLICATION_CREDENTIALS]
        BE2[GCP_PROJECT_ID]
        BE3[GOOGLE_CLIENT_ID]
        BE4[GOOGLE_CLIENT_SECRET]
        BE5[GOOGLE_REDIRECT_URI]
        BE6[GOOGLE_SHARED_DRIVE_ID]
        BE7[FRONTEND_URL]
        BE8[USE_AI_FOR_RFP]
    end
    
    subgraph "Frontend Environment Variables"
        FE1[REACT_APP_API_URL]
    end
    
    subgraph "Services Using Config"
        Auth[Auth Service]
        File[File Processor]
        Drive[Drive Service]
        RFP[RFP Generator]
    end
    
    BE1 --> File
    BE1 --> Drive
    BE2 --> File
    BE3 --> Auth
    BE4 --> Auth
    BE5 --> Auth
    BE6 --> Drive
    BE7 --> Auth
    BE8 --> RFP
    FE1 --> Frontend[Frontend App]
    
    style BE1 fill:#ffeb3b
    style BE3 fill:#ffeb3b
    style BE4 fill:#ffeb3b
    style BE6 fill:#ffeb3b
```

## API Endpoints Overview

```mermaid
graph LR
    subgraph "Frontend"
        UI[React UI]
    end
    
    subgraph "Backend API Endpoints"
        Root[GET /<br/>API Info]
        Health[GET /health<br/>Health Check]
        Chat[POST /api/chat<br/>Chat with AI]
        Upload[POST /api/upload<br/>Upload & Process]
        AuthStart[GET /auth/google<br/>OAuth Start]
        AuthCallback[GET /auth/google/callback<br/>OAuth Callback]
    end
    
    subgraph "Service Handlers"
        ChatHandler[RFP Generator]
        UploadHandler[File Processor<br/>+ RFP Generator<br/>+ Drive Service]
        AuthHandler[Auth Service]
    end
    
    UI --> Root
    UI --> Health
    UI --> Chat
    UI --> Upload
    UI --> AuthStart
    AuthStart --> AuthCallback
    
    Chat --> ChatHandler
    Upload --> UploadHandler
    AuthStart --> AuthHandler
    AuthCallback --> AuthHandler
    
    style UI fill:#bbdefb
    style Chat fill:#c8e6c9
    style Upload fill:#c8e6c9
    style AuthStart fill:#fff9c4
    style AuthCallback fill:#fff9c4
```

---

## How to View These Diagrams

1. **VS Code**: Install the "Markdown Preview Mermaid Support" extension
2. **GitHub**: Diagrams will render automatically in markdown files
3. **Online**: Copy the mermaid code to [Mermaid Live Editor](https://mermaid.live)
4. **Documentation Tools**: Most modern documentation tools support Mermaid

## Diagram Types Explained

- **System Architecture**: High-level overview of all components
- **Component Architecture**: Detailed component relationships
- **Sequence Diagrams**: Step-by-step flow of operations
- **Data Flow**: How data moves through the system
- **Service Dependencies**: What each service depends on
- **Deployment Architecture**: How the system is deployed
- **Environment Configuration**: Configuration management
- **API Endpoints**: API structure and routing

