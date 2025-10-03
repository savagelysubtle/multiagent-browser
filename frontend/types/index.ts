/**
 * Type definitions for authentication and user management
 */

export interface User {
  id: string;
  email: string;
  name?: string;
  picture?: string;
  is_active: boolean;
  created_at: string;
  last_login?: string;
  state?: UserState;
}

export interface UserState {
  preferences?: {
    theme?: string;
    sidebarWidth?: number;
    editorFontSize?: number;
    [key: string]: any;
  };
  workspace?: {
    openDocuments?: string[];
    activeDocument?: string | null;
    recentFiles?: string[];
    [key: string]: any;
  };
  agentSettings?: {
    [key: string]: any;
  };
  [key: string]: any;
}

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

export interface TokenResponse extends AuthResponse {}

// API Error types
export interface ApiError {
  code: string;
  message: string;
  timestamp: string;
  retryable?: boolean;
  field?: string;
  details?: any;
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

export interface Task {
  id: string;
  agent_type: string;
  action: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  created_at: string;
  started_at?: string;
  completed_at?: string;
  result?: any;
  error?: string;
  progress?: any;
}

// Document types
export interface Document {
  id: string;
  title: string;
  content: string;
  document_type: string;
  metadata?: Record<string, any>;
  created_at: string;
  updated_at: string;
}
