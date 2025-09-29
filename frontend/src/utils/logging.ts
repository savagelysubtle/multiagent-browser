/**
 * Centralized logging configuration for the frontend.
 *
 * This module provides a single source of truth for logging configuration,
 * ensuring consistent logging across all frontend components with file persistence.
 */

export enum LogLevel {
  TRACE = 0,
  DEBUG = 1,
  INFO = 2,
  WARN = 3,
  ERROR = 4,
  SILENT = 5,
}

export interface LogEntry {
  timestamp: string;
  level: LogLevel;
  name: string;
  message: string;
  error?: Error;
  metadata?: Record<string, any>;
}

export interface LoggingConfig {
  level: LogLevel;
  enableConsole: boolean;
  enableFile: boolean;
  maxFileSize: number; // in bytes
  maxEntries: number;
  flushInterval: number; // in milliseconds
}

class FrontendLoggingConfig {
  private static _initialized = false;
  private static _config: LoggingConfig = {
    level: LogLevel.INFO,
    enableConsole: true,
    enableFile: true,
    maxFileSize: 5 * 1024 * 1024, // 5MB
    maxEntries: 1000,
    flushInterval: 30000, // 30 seconds
  };

  private static _logBuffer: LogEntry[] = [];
  private static _flushTimer: NodeJS.Timeout | null = null;
  private static _loggers = new Map<string, Logger>();

  /**
   * Initialize the logging system
   */
  static initialize(config?: Partial<LoggingConfig>): void {
    if (this._initialized) {
      return;
    }

    if (config) {
      this._config = { ...this._config, ...config };
    }

    // Set up periodic flush to logs directory
    if (this._config.enableFile) {
      this._setupFileFlush();
    }

    this._initialized = true;

    // Log initialization
    this.getLogger('frontend.logging').info('Logging initialized', {
      level: LogLevel[this._config.level],
      enableConsole: this._config.enableConsole,
      enableFile: this._config.enableFile,
    });
  }

  /**
   * Get a logger instance
   */
  static getLogger(name: string): Logger {
    if (!this._initialized) {
      this.initialize();
    }

    if (!this._loggers.has(name)) {
      this._loggers.set(name, new Logger(name, this._config));
    }

    return this._loggers.get(name)!;
  }

  /**
   * Update logging configuration
   */
  static updateConfig(newConfig: Partial<LoggingConfig>): void {
    const oldLevel = this._config.level;
    this._config = { ...this._config, ...newConfig };

    // Update all existing loggers with new config
    for (const logger of this._loggers.values()) {
      logger.updateConfig(this._config);
    }

    this.getLogger('frontend.logging').info('Logging configuration updated', {
      oldLevel: LogLevel[oldLevel],
      newLevel: LogLevel[this._config.level],
      changes: Object.keys(newConfig),
    });
  }

  /**
   * Set up periodic flush to logs directory
   */
  private static _setupFileFlush(): void {
    if (this._flushTimer) {
      clearInterval(this._flushTimer);
    }

    this._flushTimer = setInterval(() => {
      this.flushLogsToFile();
    }, this._config.flushInterval);
  }

  /**
   * Add a log entry to the buffer
   */
  static addLogEntry(entry: LogEntry): void {
    this._logBuffer.push(entry);

    // Keep buffer size in check
    if (this._logBuffer.length > this._config.maxEntries) {
      this._logBuffer = this._logBuffer.slice(-this._config.maxEntries);
    }
  }

  /**
   * Flush logs to the main logs directory
   */
  static async flushLogsToFile(): Promise<void> {
    if (this._logBuffer.length === 0) {
      return;
    }

    try {
      const logsToFlush = [...this._logBuffer];
      this._logBuffer = [];

      // Format logs for file output (similar to backend format)
      const logContent = logsToFlush
        .map(entry => {
          const timestamp = new Date(entry.timestamp).toISOString().replace('T', ' ');
          const level = LogLevel[entry.level].padEnd(5);
          const name = entry.name.padEnd(30);
          let message = entry.message;

          // Add error details if present
          if (entry.error) {
            message += ` | Error: ${entry.error.message}`;
            if (entry.error.stack) {
              message += `\nStack: ${entry.error.stack}`;
            }
          }

          // Add metadata if present
          if (entry.metadata && Object.keys(entry.metadata).length > 0) {
            message += ` | ${JSON.stringify(entry.metadata)}`;
          }

          return `${timestamp} - ${name} - ${level} - ${message}`;
        })
        .join('\n');

      // Write to logs directory using fetch to backend
      const response = await fetch('/api/logs/frontend', {
        method: 'POST',
        headers: {
          'Content-Type': 'text/plain',
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
        },
        body: logContent,
      });

      if (!response.ok) {
        console.warn('Failed to flush frontend logs to backend');
        // Put logs back in buffer for retry
        this._logBuffer.unshift(...logsToFlush);
      }
    } catch (error) {
      console.warn('Error flushing frontend logs:', error);
      // Put logs back in buffer for retry
      this._logBuffer.unshift(...this._logBuffer);
    }
  }

  /**
   * Get current configuration
   */
  static getConfig(): LoggingConfig {
    return { ...this._config };
  }

  /**
   * Get all buffered log entries
   */
  static getBufferedLogs(): LogEntry[] {
    return [...this._logBuffer];
  }

  /**
   * Clear all buffered logs
   */
  static clearBuffer(): void {
    this._logBuffer = [];
  }

  /**
   * Cleanup resources
   */
  static cleanup(): void {
    if (this._flushTimer) {
      clearInterval(this._flushTimer);
      this._flushTimer = null;
    }

    // Flush any remaining logs
    this.flushLogsToFile();

    this._loggers.clear();
    this._initialized = false;
  }
}

/**
 * Logger class for individual components
 */
export class Logger {
  private name: string;
  private config: LoggingConfig;

  constructor(name: string, config: LoggingConfig) {
    this.name = name;
    this.config = config;
  }

  updateConfig(config: LoggingConfig): void {
    this.config = config;
  }

  private shouldLog(level: LogLevel): boolean {
    return level >= this.config.level;
  }

  private createLogEntry(level: LogLevel, message: string, error?: Error, metadata?: Record<string, any>): LogEntry {
    return {
      timestamp: new Date().toISOString(),
      level,
      name: this.name,
      message,
      error,
      metadata,
    };
  }

  private log(level: LogLevel, message: string, error?: Error, metadata?: Record<string, any>): void {
    if (!this.shouldLog(level)) {
      return;
    }

    const entry = this.createLogEntry(level, message, error, metadata);

    // Add to buffer for file logging
    if (this.config.enableFile) {
      FrontendLoggingConfig.addLogEntry(entry);
    }

    // Console output
    if (this.config.enableConsole) {
      const levelName = LogLevel[level];
      const formattedMessage = `[${this.name}] ${message}`;

      switch (level) {
        case LogLevel.ERROR:
          console.error(formattedMessage, error || '', metadata || '');
          break;
        case LogLevel.WARN:
          console.warn(formattedMessage, metadata || '');
          break;
        case LogLevel.INFO:
          console.info(formattedMessage, metadata || '');
          break;
        case LogLevel.DEBUG:
        case LogLevel.TRACE:
          console.debug(formattedMessage, metadata || '');
          break;
      }
    }
  }

  trace(message: string, metadata?: Record<string, any>): void {
    this.log(LogLevel.TRACE, message, undefined, metadata);
  }

  debug(message: string, metadata?: Record<string, any>): void {
    this.log(LogLevel.DEBUG, message, undefined, metadata);
  }

  info(message: string, metadata?: Record<string, any>): void {
    this.log(LogLevel.INFO, message, undefined, metadata);
  }

  warn(message: string, metadata?: Record<string, any>): void {
    this.log(LogLevel.WARN, message, undefined, metadata);
  }

  error(message: string, error?: Error, metadata?: Record<string, any>): void {
    this.log(LogLevel.ERROR, message, error, metadata);
  }
}

/**
 * Convenience functions for backward compatibility
 */
export function setupFrontendLogging(config?: Partial<LoggingConfig>): void {
  FrontendLoggingConfig.initialize(config);
}

export function getFrontendLogger(name: string): Logger {
  return FrontendLoggingConfig.getLogger(name);
}

// Initialize with default configuration
if (typeof window !== 'undefined') {
  // Auto-initialize when imported in browser
  FrontendLoggingConfig.initialize();
}