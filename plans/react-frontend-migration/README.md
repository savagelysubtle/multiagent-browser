# 🚀 React Frontend Migration Plan

## Executive Summary

This document outlines a streamlined migration strategy from Gradio to a modern React frontend, optimized for a per-user application with cloud-ready architecture. The plan emphasizes simplicity, security, and scalability while maintaining all existing functionality.

## 📊 Project Overview

### Scope
- **User Model**: Single user type (no admin/roles)
- **Authentication**: Basic auth with Google SSO preparation
- **Deployment**: Local development → Cloud production
- **Database**: ChromaDB for persistent state storage
- **Timeline**: 6-8 weeks

### Key Simplifications (Based on Requirements)
- ✅ No complex role management
- ✅ No data migration needed
- ✅ Clean cutover from Gradio
- ✅ Per-user isolated experience
- ✅ State persistence via ChromaDB

---

## 🏗️ Simplified Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   React Frontend (SPA)                   │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │   Editor    │  │     Chat     │  │  File Manager │  │
│  └──────┬──────┘  └──────┬───────┘  └───────┬───────┘  │
│         └─────────────────┴──────────────────┘         │
│                           │                             │
│                    Zustand Store                        │
│                    (Local State)                        │
└───────────────────────────┬─────────────────────────────┘
                            │
                     HTTP/WebSocket
                            │
┌───────────────────────────┴─────────────────────────────┐
│                    FastAPI Backend                       │
│  ┌──────────────────────────────────────────────────┐  │
│  │          API Routes + WebSocket Handler          │  │
│  └────┬──────────────┬──────────────┬───────────────┘  │
│       │              │              │                   │
│  ┌────┴────┐   ┌────┴────┐   ┌────┴────┐             │
│  │  Auth   │   │  Agent  │   │Database │             │
│  │ Service │   │  Pool   │   │Pipeline │             │
│  └─────────┘   └─────────┘   └────┬────┘             │
│                                    │                   │
│                             ChromaDB                   │
│                         (User State)                   │
└─────────────────────────────────────────────────────────┘
```

---

## 📋 Phase 1: Foundation & Auth (Week 1-2)

### 1.1 Basic Authentication System

```python
# src/web_ui/api/auth/auth_service.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional

class AuthService:
    def __init__(self):
        self.secret_key = os.getenv("JWT_SECRET", "dev-secret-key")
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 1440  # 24 hours

    def create_access_token(self, user_id: str) -> str:
        expires_delta = timedelta(minutes=self.access_token_expire_minutes)
        expire = datetime.utcnow() + expires_delta

        to_encode = {
            "sub": user_id,
            "exp": expire,
            "iat": datetime.utcnow()
        }

        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def verify_token(self, token: str) -> Optional[str]:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            user_id: str = payload.get("sub")
            if user_id is None:
                return None
            return user_id
        except JWTError:
            return None

# Simple user model for now
class User:
    def __init__(self, id: str, email: str):
        self.id = id
        self.email = email

# Dependency for protected routes
security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    token = credentials.credentials
    user_id = auth_service.verify_token(token)

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )

    # Get user from database
    user = await get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user
```

### 1.2 Google SSO Preparation

```python
# src/web_ui/api/auth/google_auth.py
from authlib.integrations.starlette_client import OAuth
from fastapi import Request
import os

# OAuth setup (ready but not active)
oauth = OAuth()

def setup_google_oauth(app):
    """Setup Google OAuth - activate when ready"""
    if os.getenv("ENABLE_GOOGLE_SSO", "false").lower() == "true":
        oauth.register(
            name='google',
            client_id=os.getenv('GOOGLE_CLIENT_ID'),
            client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
            client_kwargs={'scope': 'openid email profile'}
        )
        oauth.init_app(app)

# Routes ready for future activation
@app.get("/auth/google/login")
async def google_login(request: Request):
    if not os.getenv("ENABLE_GOOGLE_SSO", "false").lower() == "true":
        return {"message": "Google SSO not enabled"}

    redirect_uri = request.url_for('google_callback')
    return await oauth.google.authorize_redirect(request, redirect_uri)

@app.get("/auth/google/callback")
async def google_callback(request: Request):
    if not os.getenv("ENABLE_GOOGLE_SSO", "false").lower() == "true":
        return {"message": "Google SSO not enabled"}

    token = await oauth.google.authorize_access_token(request)
    user = token['userinfo']

    # Create or update user in database
    db_user = await create_or_update_user(
        email=user['email'],
        name=user.get('name', ''),
        picture=user.get('picture', '')
    )

    # Generate JWT
    access_token = auth_service.create_access_token(db_user.id)

    return {"access_token": access_token, "token_type": "bearer"}
```

### 1.3 User State Management with ChromaDB

```python
# src/web_ui/database/user_state_manager.py
from typing import Dict, Any, Optional
import json
from datetime import datetime

class UserStateManager:
    """Manages per-user state persistence in ChromaDB"""

    def __init__(self, chroma_manager):
        self.chroma = chroma_manager
        self.collection_name = "user_states"
        self._ensure_collection()

    def _ensure_collection(self):
        """Ensure user state collection exists"""
        from .models import CollectionConfig

        config = CollectionConfig(
            name=self.collection_name,
            metadata={
                "description": "Per-user application state storage",
                "type": "user_state",
                "version": "1.0.0"
            }
        )
        self.chroma.create_collection(config)

    async def save_user_state(self, user_id: str, state: Dict[str, Any]) -> bool:
        """Save user's application state"""
        try:
            from .models import DocumentModel

            doc = DocumentModel(
                id=f"user_state_{user_id}",
                content=json.dumps(state),
                metadata={
                    "user_id": user_id,
                    "state_type": "application_state",
                    "last_updated": datetime.utcnow().isoformat(),
                    "version": "1.0"
                },
                source="user_state_manager",
                timestamp=datetime.utcnow()
            )

            return self.chroma.add_document(self.collection_name, doc)

        except Exception as e:
            logger.error(f"Failed to save user state: {e}")
            return False

    async def get_user_state(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve user's application state"""
        try:
            doc = self.chroma.get_document(self.collection_name, f"user_state_{user_id}")
            if doc:
                return json.loads(doc.content)
            return None

        except Exception as e:
            logger.error(f"Failed to get user state: {e}")
            return None

    async def update_user_preference(self, user_id: str, key: str, value: Any) -> bool:
        """Update a specific user preference"""
        state = await self.get_user_state(user_id) or {}

        if "preferences" not in state:
            state["preferences"] = {}

        state["preferences"][key] = value
        return await self.save_user_state(user_id, state)
```

### 1.4 Frontend State Persistence

```typescript
// frontend/stores/useAppStore.ts
import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { userStateService } from '../services/userStateService';

interface AppState {
  // User info
  user: User | null;

  // UI preferences
  theme: 'light' | 'dark';
  sidebarWidth: number;
  editorFontSize: number;

  // Document state
  openDocuments: string[];
  activeDocument: string | null;
  recentFiles: string[];

  // Agent preferences
  preferredAgent: string | null;
  agentSettings: Record<string, any>;

  // Actions
  setUser: (user: User | null) => void;
  setTheme: (theme: 'light' | 'dark') => void;
  addRecentFile: (filePath: string) => void;
  saveStateToBackend: () => Promise<void>;
  loadStateFromBackend: () => Promise<void>;
}

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      // Initial state
      user: null,
      theme: 'dark',
      sidebarWidth: 250,
      editorFontSize: 14,
      openDocuments: [],
      activeDocument: null,
      recentFiles: [],
      preferredAgent: null,
      agentSettings: {},

      // Actions
      setUser: (user) => set({ user }),
      setTheme: (theme) => {
        set({ theme });
        document.documentElement.classList.toggle('dark', theme === 'dark');
      },

      addRecentFile: (filePath) => set((state) => ({
        recentFiles: [
          filePath,
          ...state.recentFiles.filter(f => f !== filePath)
        ].slice(0, 10) // Keep only 10 recent files
      })),

      // Backend persistence
      saveStateToBackend: async () => {
        const state = get();
        if (!state.user) return;

        const stateToSave = {
          preferences: {
            theme: state.theme,
            sidebarWidth: state.sidebarWidth,
            editorFontSize: state.editorFontSize,
            preferredAgent: state.preferredAgent
          },
          workspace: {
            openDocuments: state.openDocuments,
            activeDocument: state.activeDocument,
            recentFiles: state.recentFiles
          },
          agentSettings: state.agentSettings
        };

        await userStateService.saveState(stateToSave);
      },

      loadStateFromBackend: async () => {
        const state = get();
        if (!state.user) return;

        const savedState = await userStateService.loadState();
        if (savedState) {
          set({
            theme: savedState.preferences?.theme || 'dark',
            sidebarWidth: savedState.preferences?.sidebarWidth || 250,
            editorFontSize: savedState.preferences?.editorFontSize || 14,
            preferredAgent: savedState.preferences?.preferredAgent || null,
            openDocuments: savedState.workspace?.openDocuments || [],
            activeDocument: savedState.workspace?.activeDocument || null,
            recentFiles: savedState.workspace?.recentFiles || [],
            agentSettings: savedState.agentSettings || {}
          });
        }
      }
    }),
    {
      name: 'app-state',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        // Only persist non-sensitive data locally
        theme: state.theme,
        sidebarWidth: state.sidebarWidth,
        editorFontSize: state.editorFontSize
      })
    }
  )
);

// Auto-save to backend periodically
setInterval(() => {
  const state = useAppStore.getState();
  if (state.user) {
    state.saveStateToBackend();
  }
}, 30000); // Every 30 seconds
```

---

## 📋 Phase 2: Core WebSocket & API Integration (Week 3-4)

### 2.1 WebSocket Manager with Error Handling

```python
# src/web_ui/api/websocket/websocket_manager.py
from typing import Dict, Set
from fastapi import WebSocket, WebSocketDisconnect
import asyncio
import json
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # Map user_id to WebSocket connection
        self.active_connections: Dict[str, WebSocket] = {}
        # Track connection health
        self.connection_health: Dict[str, Dict] = {}
        # Message queue for offline users
        self.message_queue: Dict[str, List[Dict]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        """Connect a user with automatic reconnection support"""
        await websocket.accept()

        # Close existing connection if any
        if user_id in self.active_connections:
            await self.disconnect(user_id)

        self.active_connections[user_id] = websocket
        self.connection_health[user_id] = {
            "connected_at": datetime.utcnow(),
            "last_ping": datetime.utcnow(),
            "reconnect_count": 0
        }

        # Send queued messages
        await self._send_queued_messages(user_id)

        # Start heartbeat
        asyncio.create_task(self._heartbeat(user_id))

        logger.info(f"User {user_id} connected via WebSocket")

    async def disconnect(self, user_id: str):
        """Gracefully disconnect a user"""
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].close()
            except Exception as e:
                logger.error(f"Error closing WebSocket for {user_id}: {e}")
            finally:
                del self.active_connections[user_id]
                if user_id in self.connection_health:
                    del self.connection_health[user_id]

        logger.info(f"User {user_id} disconnected")

    async def send_message(self, user_id: str, message: Dict):
        """Send message to specific user with queueing"""
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_json(message)
                return True
            except Exception as e:
                logger.error(f"Failed to send message to {user_id}: {e}")
                await self.disconnect(user_id)

        # Queue message for offline user
        if user_id not in self.message_queue:
            self.message_queue[user_id] = []

        self.message_queue[user_id].append({
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
            "attempts": 0
        })

        # Keep only last 100 messages per user
        self.message_queue[user_id] = self.message_queue[user_id][-100:]

        return False

    async def _send_queued_messages(self, user_id: str):
        """Send queued messages to reconnected user"""
        if user_id not in self.message_queue:
            return

        messages = self.message_queue.get(user_id, [])
        sent_count = 0

        for msg_data in messages:
            try:
                await self.active_connections[user_id].send_json({
                    "type": "queued_message",
                    "data": msg_data["message"],
                    "queued_at": msg_data["timestamp"]
                })
                sent_count += 1
            except Exception as e:
                logger.error(f"Failed to send queued message: {e}")
                break

        if sent_count == len(messages):
            del self.message_queue[user_id]
        else:
            # Keep unsent messages
            self.message_queue[user_id] = messages[sent_count:]

    async def _heartbeat(self, user_id: str):
        """Maintain connection health with periodic pings"""
        while user_id in self.active_connections:
            try:
                await asyncio.sleep(30)  # Ping every 30 seconds

                if user_id in self.active_connections:
                    await self.active_connections[user_id].send_json({
                        "type": "ping",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    self.connection_health[user_id]["last_ping"] = datetime.utcnow()

            except Exception as e:
                logger.error(f"Heartbeat failed for {user_id}: {e}")
                await self.disconnect(user_id)
                break

# Global instance
ws_manager = ConnectionManager()

# WebSocket endpoint with authentication
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str):
    user_id = auth_service.verify_token(token)
    if not user_id:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await ws_manager.connect(websocket, user_id)

    try:
        while True:
            data = await websocket.receive_json()
            await handle_websocket_message(user_id, data)

    except WebSocketDisconnect:
        await ws_manager.disconnect(user_id)
    except Exception as e:
        logger.error(f"WebSocket error for {user_id}: {e}")
        await ws_manager.disconnect(user_id)
```

### 2.2 Error Handling Best Practices

```python
# src/web_ui/api/middleware/error_handler.py
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import traceback
import logging

logger = logging.getLogger(__name__)

class AppException(Exception):
    """Base application exception"""
    def __init__(self, message: str, code: str = "APP_ERROR", status_code: int = 500):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(self.message)

class AgentException(AppException):
    """Agent-specific exceptions"""
    def __init__(self, message: str, agent_name: str, code: str = "AGENT_ERROR"):
        self.agent_name = agent_name
        super().__init__(message, code, status_code=500)

class ValidationException(AppException):
    """Input validation exceptions"""
    def __init__(self, message: str, field: str = None):
        self.field = field
        super().__init__(message, "VALIDATION_ERROR", status_code=400)

async def app_exception_handler(request: Request, exc: AppException):
    """Handle application exceptions"""
    logger.error(f"Application error: {exc.message}", exc_info=True)

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors"""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid input data",
                "details": errors,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    )

async def generic_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)

    # Don't expose internal errors in production
    message = "An unexpected error occurred"
    if os.getenv("ENV") == "development":
        message = str(exc)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": message,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    )

# Circuit breaker for external services
from pybreaker import CircuitBreaker

agent_circuit_breaker = CircuitBreaker(
    fail_max=5,
    reset_timeout=60,
    expected_exception=Exception
)

@agent_circuit_breaker
async def call_agent_with_circuit_breaker(agent_name: str, task: Dict):
    """Protected agent calls with circuit breaker"""
    try:
        return await orchestrator.submit_task(task)
    except Exception as e:
        logger.error(f"Agent {agent_name} failed: {e}")
        raise AgentException(f"Agent operation failed", agent_name)
```

### 2.3 Frontend Error Handling

```typescript
// frontend/services/errorService.ts
import { toast } from 'react-toastify';

export interface AppError {
  code: string;
  message: string;
  field?: string;
  timestamp: string;
  retryable?: boolean;
}

export class ErrorService {
  private static readonly ERROR_MESSAGES: Record<string, string> = {
    'NETWORK_ERROR': 'Connection lost. Please check your internet.',
    'AUTH_EXPIRED': 'Your session has expired. Please login again.',
    'AGENT_TIMEOUT': 'The operation is taking longer than expected.',
    'RATE_LIMIT': 'Too many requests. Please slow down.',
    'VALIDATION_ERROR': 'Please check your input and try again.'
  };

  static handleError(error: any): AppError {
    // API error response
    if (error.response?.data?.error) {
      const apiError = error.response.data.error;
      return {
        code: apiError.code,
        message: apiError.message || this.ERROR_MESSAGES[apiError.code] || 'An error occurred',
        field: apiError.field,
        timestamp: apiError.timestamp || new Date().toISOString(),
        retryable: this.isRetryable(apiError.code)
      };
    }

    // Network error
    if (!error.response) {
      return {
        code: 'NETWORK_ERROR',
        message: this.ERROR_MESSAGES.NETWORK_ERROR,
        timestamp: new Date().toISOString(),
        retryable: true
      };
    }

    // Generic error
    return {
      code: 'UNKNOWN_ERROR',
      message: error.message || 'An unexpected error occurred',
      timestamp: new Date().toISOString(),
      retryable: false
    };
  }

  static showError(error: AppError) {
    toast.error(error.message, {
      position: 'top-right',
      autoClose: error.retryable ? 5000 : false,
      hideProgressBar: false,
      closeOnClick: true,
      pauseOnHover: true,
      draggable: true
    });
  }

  private static isRetryable(code: string): boolean {
    const retryableCodes = ['NETWORK_ERROR', 'AGENT_TIMEOUT', 'RATE_LIMIT'];
    return retryableCodes.includes(code);
  }
}

// Axios interceptor for global error handling
import axios from 'axios';

axios.interceptors.response.use(
  response => response,
  error => {
    const appError = ErrorService.handleError(error);

    // Auto-retry for retryable errors
    if (appError.retryable && error.config && !error.config.__retryCount) {
      error.config.__retryCount = 0;
    }

    if (error.config && error.config.__retryCount < 3 && appError.retryable) {
      error.config.__retryCount++;

      // Exponential backoff
      const delay = Math.pow(2, error.config.__retryCount) * 1000;

      return new Promise(resolve => {
        setTimeout(() => resolve(axios(error.config)), delay);
      });
    }

    // Show error to user
    ErrorService.showError(appError);

    // Redirect to login on auth errors
    if (appError.code === 'AUTH_EXPIRED') {
      window.location.href = '/login';
    }

    return Promise.reject(appError);
  }
);
```

---

## 📋 Phase 3: Agent Integration & Google A2A (Week 5)

### 3.1 Simplified Agent Orchestrator

```python
# src/web_ui/agent/orchestrator/simple_orchestrator.py
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import asyncio
import uuid

@dataclass
class AgentTask:
    id: str
    user_id: str
    agent_type: str
    action: str
    payload: Dict[str, Any]
    status: str = "pending"  # pending, running, completed, failed
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: datetime = None
    completed_at: datetime = None

class SimpleAgentOrchestrator:
    """Simplified agent orchestration for per-user tasks"""

    def __init__(self):
        self.agents = {}
        self.user_tasks: Dict[str, List[str]] = {}  # user_id -> task_ids
        self.task_store: Dict[str, AgentTask] = {}  # task_id -> task

    def register_agent(self, agent_type: str, agent_instance):
        """Register an agent"""
        self.agents[agent_type] = agent_instance
        logger.info(f"Registered agent: {agent_type}")

    async def submit_task(self, user_id: str, agent_type: str, action: str, payload: Dict) -> str:
        """Submit a task for a specific user"""
        if agent_type not in self.agents:
            raise ValueError(f"Unknown agent type: {agent_type}")

        task = AgentTask(
            id=str(uuid.uuid4()),
            user_id=user_id,
            agent_type=agent_type,
            action=action,
            payload=payload,
            created_at=datetime.utcnow()
        )

        # Store task
        self.task_store[task.id] = task

        # Track user tasks
        if user_id not in self.user_tasks:
            self.user_tasks[user_id] = []
        self.user_tasks[user_id].append(task.id)

        # Execute task asynchronously
        asyncio.create_task(self._execute_task(task))

        # Send immediate acknowledgment
        await ws_manager.send_message(user_id, {
            "type": "task_created",
            "task_id": task.id,
            "agent_type": agent_type,
            "action": action
        })

        return task.id

    async def _execute_task(self, task: AgentTask):
        """Execute a task with error handling"""
        try:
            # Update status
            task.status = "running"
            await self._notify_task_status(task)

            # Get agent
            agent = self.agents[task.agent_type]

            # Execute based on action
            if hasattr(agent, task.action):
                method = getattr(agent, task.action)
                result = await method(**task.payload)

                # Update task
                task.status = "completed"
                task.result = result
                task.completed_at = datetime.utcnow()

            else:
                raise AttributeError(f"Agent {task.agent_type} has no action {task.action}")

        except Exception as e:
            logger.error(f"Task {task.id} failed: {e}")
            task.status = "failed"
            task.error = str(e)
            task.completed_at = datetime.utcnow()

        finally:
            # Notify completion
            await self._notify_task_status(task)

    async def _notify_task_status(self, task: AgentTask):
        """Notify user of task status change"""
        await ws_manager.send_message(task.user_id, {
            "type": "task_update",
            "task_id": task.id,
            "status": task.status,
            "result": task.result if task.status == "completed" else None,
            "error": task.error if task.status == "failed" else None,
            "progress": self._calculate_progress(task)
        })

    def _calculate_progress(self, task: AgentTask) -> Dict[str, Any]:
        """Calculate task progress for UI"""
        if task.status == "pending":
            return {"percentage": 0, "message": "Waiting to start"}
        elif task.status == "running":
            return {"percentage": 50, "message": "Processing..."}
        elif task.status == "completed":
            return {"percentage": 100, "message": "Completed"}
        else:
            return {"percentage": 100, "message": f"Failed: {task.error}"}

    async def get_user_tasks(self, user_id: str, limit: int = 50) -> List[AgentTask]:
        """Get recent tasks for a user"""
        task_ids = self.user_tasks.get(user_id, [])
        tasks = [self.task_store[tid] for tid in task_ids if tid in self.task_store]

        # Sort by created_at descending
        tasks.sort(key=lambda t: t.created_at, reverse=True)

        return tasks[:limit]

    async def cancel_task(self, user_id: str, task_id: str) -> bool:
        """Cancel a pending task"""
        task = self.task_store.get(task_id)

        if not task or task.user_id != user_id:
            return False

        if task.status == "pending":
            task.status = "cancelled"
            task.completed_at = datetime.utcnow()
            await self._notify_task_status(task)
            return True

        return False

# Initialize global orchestrator
orchestrator = SimpleAgentOrchestrator()
```

### 3.2 Agent API Routes

```python
# src/web_ui/api/routes/agents.py
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any

router = APIRouter(prefix="/api/agents", tags=["agents"])

@router.get("/available")
async def get_available_agents(user: User = Depends(get_current_user)):
    """Get list of available agents and their capabilities"""
    return {
        "agents": [
            {
                "type": "document_editor",
                "name": "Document Editor",
                "description": "Create and edit documents with AI assistance",
                "actions": [
                    {
                        "name": "create_document",
                        "description": "Create a new document",
                        "parameters": ["filename", "content", "document_type"]
                    },
                    {
                        "name": "edit_document",
                        "description": "Edit an existing document",
                        "parameters": ["document_id", "instruction"]
                    },
                    {
                        "name": "search_documents",
                        "description": "Search through documents",
                        "parameters": ["query", "limit"]
                    }
                ]
            },
            {
                "type": "browser_use",
                "name": "Browser Agent",
                "description": "Browse the web and extract information",
                "actions": [
                    {
                        "name": "browse",
                        "description": "Navigate to a URL and interact with it",
                        "parameters": ["url", "instruction"]
                    },
                    {
                        "name": "extract",
                        "description": "Extract specific information from a webpage",
                        "parameters": ["url", "selectors"]
                    }
                ]
            },
            {
                "type": "deep_research",
                "name": "Research Agent",
                "description": "Conduct in-depth research on topics",
                "actions": [
                    {
                        "name": "research",
                        "description": "Research a topic comprehensively",
                        "parameters": ["topic", "depth", "sources"]
                    }
                ]
            }
        ]
    }

@router.post("/execute")
async def execute_agent_task(
    agent_type: str,
    action: str,
    payload: Dict[str, Any],
    user: User = Depends(get_current_user)
):
    """Execute an agent task"""
    try:
        task_id = await orchestrator.submit_task(
            user_id=user.id,
            agent_type=agent_type,
            action=action,
            payload=payload
        )

        return {
            "task_id": task_id,
            "status": "submitted",
            "message": f"Task submitted to {agent_type}"
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to submit task: {e}")
        raise AppException("Failed to submit agent task")

@router.get("/tasks")
async def get_user_tasks(
    limit: int = 50,
    user: User = Depends(get_current_user)
):
    """Get user's recent tasks"""
    tasks = await orchestrator.get_user_tasks(user.id, limit)

    return {
        "tasks": [
            {
                "id": task.id,
                "agent_type": task.agent_type,
                "action": task.action,
                "status": task.status,
                "created_at": task.created_at.isoformat(),
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                "result": task.result if task.status == "completed" else None,
                "error": task.error if task.status == "failed" else None
            }
            for task in tasks
        ]
    }

@router.delete("/tasks/{task_id}")
async def cancel_task(
    task_id: str,
    user: User = Depends(get_current_user)
):
    """Cancel a pending task"""
    success = await orchestrator.cancel_task(user.id, task_id)

    if not success:
        raise HTTPException(status_code=404, detail="Task not found or cannot be cancelled")

    return {"message": "Task cancelled successfully"}
```

---

## 📋 Phase 4: Enhanced React Frontend (Week 6)

### 4.1 Main App Component with Auth

```tsx
// frontend/src/App.tsx
import React, { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ToastContainer } from 'react-toastify';
import { useAppStore } from './stores/useAppStore';
import { authService } from './services/authService';
import 'react-toastify/dist/ReactToastify.css';

// Pages
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import LoadingScreen from './components/LoadingScreen';

// Create query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      retry: (failureCount, error: any) => {
        if (error?.code === 'AUTH_EXPIRED') return false;
        return failureCount < 3;
      }
    }
  }
});

function App() {
  const { user, setUser, loadStateFromBackend } = useAppStore();
  const [loading, setLoading] = React.useState(true);

  useEffect(() => {
    // Check authentication on app load
    const initAuth = async () => {
      try {
        const token = localStorage.getItem('auth_token');
        if (token) {
          const userData = await authService.verifyToken(token);
          if (userData) {
            setUser(userData);
            await loadStateFromBackend();
          }
        }
      } catch (error) {
        console.error('Auth init failed:', error);
        localStorage.removeItem('auth_token');
      } finally {
        setLoading(false);
      }
    };

    initAuth();
  }, []);

  if (loading) {
    return <LoadingScreen />;
  }

  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
          <Routes>
            <Route
              path="/login"
              element={user ? <Navigate to="/" /> : <LoginPage />}
            />
            <Route
              path="/*"
              element={user ? <DashboardPage /> : <Navigate to="/login" />}
            />
          </Routes>

          <ToastContainer
            position="top-right"
            theme={useAppStore.getState().theme}
            closeOnClick
            pauseOnHover
          />
        </div>
      </Router>
    </QueryClientProvider>
  );
}

export default App;
```

### 4.2 Dashboard with Agent Integration

```tsx
// frontend/src/pages/DashboardPage.tsx
import React, { useEffect } from 'react';
import { Routes, Route } from 'react-router-dom';
import { useWebSocket } from '../hooks/useWebSocket';
import { useAppStore } from '../stores/useAppStore';

// Layout components
import Sidebar from '../components/layout/Sidebar';
import Header from '../components/layout/Header';

// Feature components
import EditorView from '../views/EditorView';
import ChatView from '../views/ChatView';
import TasksView from '../views/TasksView';
import SettingsView from '../views/SettingsView';

export default function DashboardPage() {
  const { user } = useAppStore();
  const { isConnected } = useWebSocket();

  return (
    <div className="flex h-screen">
      {/* Sidebar */}
      <Sidebar />

      {/* Main content */}
      <div className="flex-1 flex flex-col">
        {/* Header with connection status */}
        <Header connectionStatus={isConnected} />

        {/* Content area */}
        <main className="flex-1 overflow-hidden">
          <Routes>
            <Route path="/" element={<EditorView />} />
            <Route path="/chat" element={<ChatView />} />
            <Route path="/tasks" element={<TasksView />} />
            <Route path="/settings" element={<SettingsView />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}
```

### 4.3 Agent Task Management UI

```tsx
// frontend/src/views/TasksView.tsx
import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { agentService } from '../services/agentService';
import { formatDistanceToNow } from 'date-fns';

interface Task {
  id: string;
  agent_type: string;
  action: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  created_at: string;
  completed_at?: string;
  result?: any;
  error?: string;
}

export default function TasksView() {
  const queryClient = useQueryClient();

  // Fetch user tasks
  const { data: tasks, isLoading } = useQuery({
    queryKey: ['tasks'],
    queryFn: () => agentService.getUserTasks(),
    refetchInterval: 5000 // Refresh every 5 seconds
  });

  // Cancel task mutation
  const cancelTaskMutation = useMutation({
    mutationFn: (taskId: string) => agentService.cancelTask(taskId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
    }
  });

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'pending':
        return '⏳';
      case 'running':
        return '🔄';
      case 'completed':
        return '✅';
      case 'failed':
        return '❌';
      default:
        return '❓';
    }
  };

  const getAgentIcon = (agentType: string) => {
    switch (agentType) {
      case 'document_editor':
        return '📝';
      case 'browser_use':
        return '🌐';
      case 'deep_research':
        return '🔍';
      default:
        return '🤖';
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500" />
      </div>
    );
  }

  return (
    <div className="h-full p-6">
      <h1 className="text-2xl font-bold mb-6">Agent Tasks</h1>

      <div className="space-y-4">
        {tasks?.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            No tasks yet. Start by using one of the agents!
          </div>
        ) : (
          tasks?.map((task: Task) => (
            <div
              key={task.id}
              className="bg-white dark:bg-gray-800 rounded-lg shadow p-6"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <span className="text-2xl">{getAgentIcon(task.agent_type)}</span>
                    <h3 className="font-semibold">
                      {task.agent_type.replace('_', ' ').toUpperCase()}
                    </h3>
                    <span className="text-sm text-gray-500">
                      {task.action}
                    </span>
                  </div>

                  <div className="flex items-center gap-4 text-sm">
                    <span className="flex items-center gap-1">
                      {getStatusIcon(task.status)}
                      <span className={`
                        ${task.status === 'completed' ? 'text-green-600' : ''}
                        ${task.status === 'failed' ? 'text-red-600' : ''}
                        ${task.status === 'running' ? 'text-blue-600' : ''}
                      `}>
                        {task.status}
                      </span>
                    </span>

                    <span className="text-gray-500">
                      {formatDistanceToNow(new Date(task.created_at), { addSuffix: true })}
                    </span>
                  </div>

                  {task.error && (
                    <div className="mt-2 p-2 bg-red-50 dark:bg-red-900/20 rounded text-sm text-red-600 dark:text-red-400">
                      {task.error}
                    </div>
                  )}

                  {task.result && (
                    <div className="mt-2 p-2 bg-green-50 dark:bg-green-900/20 rounded text-sm">
                      <pre className="whitespace-pre-wrap">
                        {JSON.stringify(task.result, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>

                {task.status === 'pending' && (
                  <button
                    onClick={() => cancelTaskMutation.mutate(task.id)}
                    className="ml-4 px-3 py-1 text-sm bg-red-500 text-white rounded hover:bg-red-600"
                  >
                    Cancel
                  </button>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
```

---

## 📋 Phase 5: Deployment & DevOps (Week 7-8)

### 5.1 Environment Configuration

```bash
# .env.development
NODE_ENV=development
REACT_APP_API_URL=http://localhost:8000
REACT_APP_WS_URL=ws://localhost:8000/ws

# Backend
DATABASE_URL=sqlite:///./data/dev.db
CHROMA_DB_PATH=./data/chroma_db
JWT_SECRET=dev-secret-key-change-in-production
ENABLE_GOOGLE_SSO=false

# Agent Configuration
MAX_AGENT_TASKS_PER_USER=10
AGENT_TIMEOUT_SECONDS=300
ENABLE_AGENT_MONITORING=true

# Development tools
LOG_LEVEL=DEBUG
ENABLE_SWAGGER=true
```

```bash
# .env.production
NODE_ENV=production
REACT_APP_API_URL=https://api.yourdomain.com
REACT_APP_WS_URL=wss://api.yourdomain.com/ws

# Cloud Database (ready for migration)
DATABASE_URL=${CLOUD_DATABASE_URL}
CHROMA_DB_PATH=/persistent/chroma_db

# Security
JWT_SECRET=${SECURE_JWT_SECRET}
ENABLE_GOOGLE_SSO=true
GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID}
GOOGLE_CLIENT_SECRET=${GOOGLE_CLIENT_SECRET}

# Production settings
LOG_LEVEL=INFO
ENABLE_SWAGGER=false
SENTRY_DSN=${SENTRY_DSN}
```

### 5.2 Docker Configuration for Local Development

```dockerfile
# Dockerfile.dev
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY src/ ./src/
COPY data/ ./data/

# Development command
CMD ["uvicorn", "src.web_ui.api.server:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]
```

### 5.3 Production-Ready docker-compose.yml

```yaml
version: '3.8'

services:
  # Backend API
  backend:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=sqlite:///data/app.db
      - CHROMA_DB_PATH=/data/chroma_db
      - JWT_SECRET=${JWT_SECRET}
      - ENABLE_GOOGLE_SSO=${ENABLE_GOOGLE_SSO:-false}
    volumes:
      - ./data:/data
      - ./logs:/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Frontend (for development)
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    ports:
      - "3000:3000"
    environment:
      - REACT_APP_API_URL=http://localhost:8000
      - REACT_APP_WS_URL=ws://localhost:8000/ws
    volumes:
      - ./frontend:/app
      - /app/node_modules
    depends_on:
      - backend

  # Nginx (production only)
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./frontend/build:/usr/share/nginx/html:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - backend
    profiles:
      - production
```

### 5.4 GitHub Actions CI/CD

```yaml
# .github/workflows/deploy.yml
name: Deploy Application

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-asyncio pytest-cov

    - name: Run tests
      run: |
        pytest tests/ --cov=src --cov-report=xml

    - name: Set up Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '20'
        cache: 'npm'
        cache-dependency-path: frontend/package-lock.json

    - name: Install frontend dependencies
      working-directory: ./frontend
      run: npm ci

    - name: Run frontend tests
      working-directory: ./frontend
      run: npm test -- --coverage --watchAll=false

    - name: Build frontend
      working-directory: ./frontend
      run: npm run build

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.event_name == 'push'

    permissions:
      contents: read
      packages: write

    steps:
    - uses: actions/checkout@v3

    - name: Log in to Container Registry
      uses: docker/login-action@v2
      with:
        registry: ${{ env.REGISTRY }}
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}

    - name: Build and push Docker image
      uses: docker/build-push-action@v4
      with:
        context: .
        push: true
        tags: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:latest
        cache-from: type=gha
        cache-to: type=gha,mode=max

  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
    - name: Deploy to Cloud
      run: |
        echo "Deploy to your cloud provider here"
        # Add your deployment commands
```

---

## 📊 Monitoring & Analytics

### Production Monitoring Setup

```python
# src/web_ui/monitoring/setup.py
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from fastapi import Response
import time

# Metrics
request_count = Counter(
    'app_requests_total',
    'Total requests',
    ['method', 'endpoint', 'status']
)

request_duration = Histogram(
    'app_request_duration_seconds',
    'Request duration',
    ['method', 'endpoint']
)

active_users = Gauge(
    'app_active_users',
    'Number of active users'
)

agent_tasks = Counter(
    'app_agent_tasks_total',
    'Total agent tasks',
    ['agent_type', 'action', 'status']
)

websocket_connections = Gauge(
    'app_websocket_connections',
    'Active WebSocket connections'
)

# Metrics endpoint
@app.get("/metrics")
async def metrics():
    return Response(
        content=generate_latest(),
        media_type="text/plain"
    )

# Middleware for automatic metrics
@app.middleware("http")
async def track_metrics(request: Request, call_next):
    start_time = time.time()

    response = await call_next(request)

    duration = time.time() - start_time

    request_count.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()

    request_duration.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)

    return response
```

---

## 🚀 Migration Checklist

### Pre-Migration
- [ ] Backup existing Gradio configuration
- [ ] Document current user workflows
- [ ] Set up development environment
- [ ] Create development database

### Phase 1 (Weeks 1-2)
- [ ] Implement basic authentication
- [ ] Set up user state management
- [ ] Create WebSocket infrastructure
- [ ] Build login UI

### Phase 2 (Weeks 3-4)
- [ ] Implement error handling
- [ ] Create API routes
- [ ] Build main dashboard
- [ ] Add state persistence

### Phase 3 (Week 5)
- [ ] Set up agent orchestrator
- [ ] Create agent adapters
- [ ] Build agent UI
- [ ] Test agent integration

### Phase 4 (Week 6)
- [ ] Complete React UI
- [ ] Add all features
- [ ] Implement monitoring
- [ ] Performance optimization

### Phase 5 (Weeks 7-8)
- [ ] Set up CI/CD
- [ ] Configure deployment
- [ ] Run integration tests
- [ ] Deploy to staging
- [ ] User acceptance testing
- [ ] Production deployment

### Post-Migration
- [ ] Monitor performance
- [ ] Gather user feedback
- [ ] Plan iteration 2
- [ ] Remove Gradio code

---

## 🎯 Success Metrics

1. **Performance**
   - Page load < 2s
   - API response < 200ms
   - WebSocket latency < 50ms

2. **Reliability**
   - Uptime > 99.9%
   - Error rate < 0.1%
   - Zero data loss

3. **User Experience**
   - Task completion rate > 95%
   - User satisfaction > 4.5/5
   - Support tickets < 5/week

---

## 📚 Next Steps

1. **Immediate Actions**
   - Review plan with team
   - Set up development environment
   - Create project timeline

2. **Future Enhancements**
   - Mobile app support
   - Advanced agent workflows
   - Plugin system
   - Multi-language support

This plan provides a complete roadmap for migrating from Gradio to React while maintaining simplicity and focusing on core functionality. The architecture is designed to scale when needed while keeping complexity low for initial deployment.