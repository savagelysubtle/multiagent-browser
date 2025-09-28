export interface WindowsProtectedPaths {
  system: string[];      // Windows System directories
  program: string[];     // Program Files directories
  user: string[];        // User profile directories
  registry: string[];    // Registry paths to protect
}

export interface WindowsNetworkRestrictions {
  allowOutbound: boolean;
  allowedHosts: string[];
  blockedPorts: number[];
}

export interface WindowsResourceLimits {
  maxMemoryMB: number;
  maxCPUPercent: number;
  maxProcesses: number;
  maxFileSize: number;
}

export interface WindowsSecurityConfig {
  protectedPaths: WindowsProtectedPaths;
  allowSystemCommands: boolean;
  allowRegistryAccess: boolean;
  allowPowerShellScripts: boolean;
  allowBatchScripts: boolean;
  requireAdminWarning: boolean;
  // Enhanced security features
  useJobObjects: boolean;
  networkRestrictions: WindowsNetworkRestrictions;
  resourceLimits: WindowsResourceLimits;
  isolateProcesses: boolean;
}

export interface CommandTimeouts {
  default: number;
  network: number;
  fileSystem: number;
  database: number;
}

export interface RetryPolicy {
  maxAttempts: number;
  delayMs: number;
  exponentialBackoff: boolean;
}

export interface ExecutionConfig {
  enableDryRun: boolean;
  timeoutSeconds: number;
  timeoutBehavior: 'error' | 'kill';
}

export interface SecurityConfig {
  maxCommandLength: number;
  blockedCommands: string[];
  blockedArguments: string[];
  allowedPaths: string[];
  restrictWorkingDirectory: boolean;
  logCommands: boolean;
  maxHistorySize: number;
  commandTimeout: number;
  enableInjectionProtection: boolean;
  enableUnixTranslation: boolean;
  confirmDestructiveCommands: boolean;
  destructiveCommandPatterns: string[];
  windows: WindowsSecurityConfig;
  // Enhanced features
  timeouts: CommandTimeouts;
  retry: RetryPolicy;
  suggestCorrections: boolean;
  auditLog: {
    enabled: boolean;
    path: string;
    maxSize: number;
    rotate: boolean;
  };
}

export interface ShellConfig {
  enabled: boolean;
  command: string;
  args: string[];
  validatePath?: (dir: string) => boolean;
  blockedOperators?: string[];
  // Enhanced shell features
  environmentVariables: { [key: string]: string };
  workingDirectory: string;
  encoding: string;
  timeout: number;
}

export interface ShellsConfig {
  powershell: ShellConfig;
  cmd: ShellConfig;
  gitbash: ShellConfig;
}

export interface ServerConfig {
  security: SecurityConfig;
  execution: ExecutionConfig;
  shells: {
    [key: string]: {
      enabled: boolean;
      command: string;
      args: string[];
      blockedOperators: string[];
      environmentVariables: Record<string, string>;
      workingDirectory: string;
      encoding: string;
      timeout: number;
    };
  };
}

export interface CommandHistoryEntry {
  command: string;
  output: string;
  timestamp: string;
  exitCode: number;
  duration: number;
  workingDirectory: string;
  shell: string;
  user: string;
  force?: boolean;
  isDryRun?: boolean;
  translatedCommand?: string; // Add optional field for translated command
}

// MCP Tool specific types
export interface ExecuteCommandArgs {
  shell: 'powershell' | 'cmd' | 'gitbash';
  command: string;
  workingDir?: string;
  dryRun?: boolean;
  force?: boolean;
}

export interface GetCommandHistoryArgs {
  limit?: number;
}

export interface ExecutionResult {
  isError: boolean;
  content: Array<{
    type: 'text' | 'stdout' | 'stderr';
    text: string;
  }>;
  exitCode: number;
  duration: number;
  lastPrompt?: string;
  isDryRun: boolean;
  error?: Record<string, unknown>;
}

export interface ExecutionMessage {
  type: 'stream' | 'prompt' | 'completion';
}

export interface StreamUpdateMessage extends ExecutionMessage {
  type: 'stream';
  stream: 'stdout' | 'stderr';
  data: string;
}

export interface PromptMessage extends ExecutionMessage {
  type: 'prompt';
  prompt: string;
}

export interface CompletionMessage extends ExecutionMessage {
  type: 'completion';
  exitCode: number;
  duration: number;
}

export type ExecutionMessageUnion = StreamUpdateMessage | PromptMessage | CompletionMessage;