// User types
export interface User {
  id: string;
  email: string;
  name?: string;
  picture?: string;
  created_at: string;
}

// Document types
export interface Document {
  id: string;
  title: string;
  name: string; // Added for compatibility with existing components
  content: string;
  created_at: string;
  updated_at: string;
  user_id: string;
  metadata?: Record<string, any>;
  file?: File; // Added for compatibility with existing components
  url?: string; // Added for compatibility with existing components
}

// Chat types
export interface ChatMessage {
  id: string;
  sender: 'user' | 'ai';
  text: string;
  timestamp?: string;
}

// Agent types
export interface Agent {
  type: string;
  name: string;
  description: string;
  actions: AgentAction[];
}

export interface AgentAction {
  name: string;
  description: string;
  parameters: string[];
}

// Task types
export type TaskStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';

export interface Task {
  id: string;
  agent_type: string;
  action: string;
  status: TaskStatus;
  created_at: string;
  completed_at?: string;
  result?: any;
  error?: string;
  progress?: TaskProgress;
}

export interface TaskProgress {
  percentage: number;
  message: string;
}

// WebSocket message types
export interface WebSocketMessage {
  type: 'task_created' | 'task_update' | 'ping' | 'queued_message' | 'notification';
  data?: any;
  task_id?: string;
  timestamp?: string;
}

// API Response types
export interface ApiResponse<T> {
  data: T;
  message?: string;
}

export interface ApiError {
  code: string;
  message: string;
  field?: string;
  timestamp: string;
  retryable?: boolean;
}

// App State types
export interface AppState {
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
  setUser: (user: User | null) => void;
  setTheme: (theme: 'light' | 'dark') => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  setActiveView: (view: 'editor' | 'chat' | 'tasks' | 'settings') => void;
  addDocument: (doc: Document) => void;
  updateDocument: (id: string, updates: Partial<Document>) => void;
  removeDocument: (id: string) => void;
  setActiveDocument: (id: string | null) => void;
  addTask: (task: Task) => void;
  updateTask: (id: string, updates: Partial<Task>) => void;
  setConnectionStatus: (status: 'connected' | 'disconnected' | 'reconnecting') => void;
  saveStateToBackend: () => Promise<void>;
  loadStateFromBackend: () => Promise<void>;
}

// Auth types
export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  name?: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

// Form types
export interface TaskSubmissionForm {
  agent_type: string;
  action: string;
  payload: Record<string, any>;
}