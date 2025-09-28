# Technical Architecture

## System Overview

The new architecture replaces Gradio with a modern React frontend while maintaining all agent functionality through a robust API layer.

## Component Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              Frontend Layer                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐ │
│  │   React     │  │  TypeScript │  │   Zustand   │  │  TailwindCSS │ │
│  │   Router    │  │   + Vite    │  │   Store     │  │     UI       │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └──────────────┘ │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                     React Components                             │   │
│  ├─────────────┬─────────────┬─────────────┬────────────────────┤   │
│  │   Editor    │    Chat     │    Tasks    │     Settings       │   │
│  │   View      │    View     │    View     │      View          │   │
│  └─────────────┴─────────────┴─────────────┴────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                            HTTP/WebSocket
                                    │
┌─────────────────────────────────────────────────────────────────────────┐
│                              Backend Layer                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                         FastAPI Server                           │   │
│  ├──────────────┬──────────────┬──────────────┬──────────────────┤   │
│  │    Auth      │   WebSocket  │   Document   │     Agent        │   │
│  │   Routes     │   Handler    │    Routes    │    Routes        │   │
│  └──────────────┴──────────────┴──────────────┴──────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                          Middleware                              │   │
│  ├──────────────┬──────────────┬──────────────┬──────────────────┤   │
│  │    CORS      │    Auth      │    Error     │   Rate Limit     │   │
│  │              │  Middleware  │   Handler    │                  │   │
│  └──────────────┴──────────────┴──────────────┴──────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
┌─────────────────────────────────────────────────────────────────────────┐
│                            Service Layer                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐ │
│  │    Auth     │  │   Agent     │  │  Document   │  │  User State  │ │
│  │  Service    │  │ Orchestrator│  │  Pipeline   │  │   Manager    │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └──────────────┘ │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                         Agent Pool                               │   │
│  ├─────────────────┬─────────────────┬────────────────────────────┤   │
│  │  Document       │   Browser Use   │    Deep Research           │   │
│  │  Editor Agent   │     Agent       │       Agent                │   │
│  └─────────────────┴─────────────────┴────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
┌─────────────────────────────────────────────────────────────────────────┐
│                           Database Layer                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                          ChromaDB                                │   │
│  ├──────────────┬──────────────┬──────────────┬──────────────────┤   │
│  │  Documents   │  User States │   Policies   │   MCP Configs    │   │
│  │ Collection   │  Collection  │  Collection  │   Collection     │   │
│  └──────────────┴──────────────┴──────────────┴──────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Data Flow Diagrams

### Authentication Flow

```
User Login Request
    │
    ▼
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   React     │─────▶│   FastAPI   │─────▶│    Auth     │
│   Login     │      │   /auth     │      │   Service   │
└─────────────┘      └─────────────┘      └─────────────┘
                            │                      │
                            │                      ▼
                            │              ┌─────────────┐
                            │◀─────────────│   ChromaDB  │
                            │   JWT Token  │ User Store  │
                            ▼              └─────────────┘
                     ┌─────────────┐
                     │   Return    │
                     │    Token    │
                     └─────────────┘
```

### WebSocket Connection Flow

```
Frontend App
    │
    ├─── HTTP Request (/api/*) ──────▶ FastAPI Routes
    │
    └─── WebSocket (/ws) ────────────▶ WebSocket Handler
                                              │
                                              ▼
                                      ┌──────────────┐
                                      │ Authenticate │
                                      │    Token     │
                                      └──────┬───────┘
                                             │
                                      ┌──────▼───────┐
                                      │  Connection  │
                                      │   Manager    │
                                      └──────┬───────┘
                                             │
                                ┌────────────┴────────────┐
                                │                         │
                          ┌─────▼─────┐           ┌──────▼──────┐
                          │  Message  │           │  Heartbeat  │
                          │   Queue   │           │   Monitor   │
                          └───────────┘           └─────────────┘
```

### Agent Task Flow

```
User Request
    │
    ▼
React UI ──────▶ API /agents/execute
                        │
                        ▼
                 Agent Orchestrator
                        │
                        ├─── Task Created ───▶ WebSocket Notification
                        │
                        ▼
                 Agent Selection
                        │
        ┌───────────────┼───────────────┐
        │               │               │
   Document         Browser         Research
   Editor            Use            Agent
        │               │               │
        └───────────────┴───────────────┘
                        │
                        ▼
                 Task Execution
                        │
                        ├─── Progress Updates ───▶ WebSocket
                        │
                        ▼
                 Task Complete
                        │
                        ├─── Result ───▶ ChromaDB
                        │
                        └─── Final Update ───▶ WebSocket
```

## State Management

### Frontend State (Zustand)

```typescript
interface AppState {
  // User
  user: User | null;

  // UI State
  theme: 'light' | 'dark';
  sidebarCollapsed: boolean;
  activeView: 'editor' | 'chat' | 'tasks' | 'settings';

  // Document State
  openDocuments: Document[];
  activeDocument: string | null;
  documentCache: Map<string, Document>;

  // Agent State
  activeTasks: Task[];
  taskHistory: Task[];

  // WebSocket
  connectionStatus: 'connected' | 'disconnected' | 'reconnecting';

  // Actions
  setUser: (user: User) => void;
  addDocument: (doc: Document) => void;
  updateTaskStatus: (taskId: string, status: TaskStatus) => void;
}
```

### Backend State (ChromaDB)

```python
# User State Collection
{
  "id": "user_state_{user_id}",
  "content": {
    "preferences": {
      "theme": "dark",
      "editorFontSize": 14,
      "preferredAgent": "document_editor"
    },
    "workspace": {
      "openDocuments": ["doc1", "doc2"],
      "activeDocument": "doc1",
      "recentFiles": ["file1.md", "file2.py"]
    },
    "agentSettings": {
      "document_editor": {"autoSave": true},
      "browser_use": {"headless": true}
    }
  },
  "metadata": {
    "user_id": "user123",
    "last_updated": "2024-01-01T00:00:00Z"
  }
}
```

## Security Architecture

### Authentication & Authorization

```
┌─────────────────┐
│   User Login    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│ Email/Password  │ OR  │   Google SSO    │
└────────┬────────┘     └────────┬────────┘
         │                       │
         └───────────┬───────────┘
                     │
                     ▼
            ┌─────────────────┐
            │  Generate JWT   │
            │  (24hr expiry)  │
            └────────┬────────┘
                     │
                     ▼
            ┌─────────────────┐
            │ Store in Local  │
            │    Storage      │
            └────────┬────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │ Include in Headers:   │
         │ Authorization: Bearer │
         └───────────────────────┘
```

### API Security Layers

1. **CORS Policy**: Restrict origins
2. **Rate Limiting**: Per-user limits
3. **Input Validation**: Pydantic models
4. **SQL Injection**: Parameterized queries
5. **XSS Protection**: Content sanitization

## Deployment Architecture

### Development Environment

```
Developer Machine
    │
    ├── Frontend (npm start) ──▶ http://localhost:3000
    │
    └── Backend (uvicorn) ────▶ http://localhost:8000
            │
            └── ChromaDB ─────▶ ./data/chroma_db
```

### Production Environment

```
                    ┌─────────────────┐
                    │   CloudFlare    │
                    │      CDN        │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │   Load Balancer │
                    └────────┬────────┘
                             │
        ┌────────────────────┴────────────────────┐
        │                                         │
┌───────▼────────┐                    ┌──────────▼────────┐
│    Nginx       │                    │     Nginx         │
│  (Frontend)    │                    │   (Frontend)      │
└───────┬────────┘                    └──────────┬────────┘
        │                                         │
        └──────────────┬──────────────────────────┘
                       │
              ┌────────▼────────┐
              │   API Gateway   │
              └────────┬────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
┌───────▼────────┐          ┌────────▼────────┐
│   FastAPI      │          │    FastAPI      │
│   Instance 1   │          │   Instance 2    │
└───────┬────────┘          └────────┬────────┘
        │                             │
        └──────────┬──────────────────┘
                   │
          ┌────────▼────────┐
          │   ChromaDB      │
          │   (Persistent)  │
          └─────────────────┘
```

## Performance Considerations

### Frontend Optimization

1. **Code Splitting**: React.lazy() for views
2. **Bundle Size**: Tree shaking, minification
3. **Caching**: Service worker for offline
4. **Lazy Loading**: Images, documents
5. **State Management**: Normalized data

### Backend Optimization

1. **Connection Pooling**: Database connections
2. **Caching**: Redis for frequent queries
3. **Async Operations**: All I/O operations
4. **Background Tasks**: Celery for long tasks
5. **Query Optimization**: Indexed searches

### WebSocket Optimization

1. **Message Compression**: zlib compression
2. **Batching**: Group small messages
3. **Heartbeat**: 30-second intervals
4. **Reconnection**: Exponential backoff
5. **Message Queue**: Persistent for offline

## Monitoring Points

### Application Metrics

- Request rate by endpoint
- Response times (p50, p95, p99)
- Error rates by type
- Active users count
- WebSocket connections
- Agent task queue length
- Database query times

### Infrastructure Metrics

- CPU usage
- Memory usage
- Disk I/O
- Network throughput
- Container health
- Database size
- Log volume

### Business Metrics

- User sessions
- Documents created
- Agent tasks completed
- Feature usage
- Error impact
- User retention
- Performance SLA