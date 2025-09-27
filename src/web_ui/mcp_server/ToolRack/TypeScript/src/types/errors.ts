// Error handling for Windows CLI Tool integration

export enum ErrorSeverity {
  INFO = 'info',
  WARNING = 'warning',
  ERROR = 'error',
  CRITICAL = 'critical'
}

export interface ErrorMetadata {
  command?: string;
  shell?: string;
  workingDir?: string;
  originalCommand?: string;
  severity?: ErrorSeverity;
  errorCode?: string | number;
  [key: string]: unknown;
}

export class CLIServerError extends Error {
  public readonly severity: ErrorSeverity;
  public readonly metadata: Partial<ErrorMetadata>;
  public readonly originalError?: Error;

  constructor(
    message: string,
    severity: ErrorSeverity = ErrorSeverity.ERROR,
    metadata: Partial<ErrorMetadata> = {},
    originalError?: Error
  ) {
    super(message);
    this.name = 'CLIServerError';
    this.severity = severity;
    this.metadata = metadata;
    this.originalError = originalError;

    // Maintains proper stack trace for where our error was thrown (only available on V8)
    if (Error.captureStackTrace) {
      Error.captureStackTrace(this, CLIServerError);
    }
  }
}

export class CommandTimeoutError extends Error {
  constructor(command: string, timeoutSeconds: number) {
    super(`Command execution timed out after ${timeoutSeconds} seconds: ${command}`);
    this.name = 'CommandTimeoutError';
  }
}