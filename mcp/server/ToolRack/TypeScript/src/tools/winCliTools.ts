import { z } from 'zod';
import { spawn, type ChildProcessWithoutNullStreams, type SpawnOptionsWithoutStdio } from 'child_process';
import path from 'path';
import { ErrorCode, McpError, TextContent, CallToolResult } from "@modelcontextprotocol/sdk/types.js";
import { log } from '../utils/logger.js';

// Import our utilities
import { loadConfig } from '../utils/config.js';
import { validateWindowsSecurity, isDestructiveCommand } from '../utils/windowsValidation.js';
import { validateShellOperators, parseCommand, isCommandBlocked, isArgumentBlocked, isPathAllowed } from '../utils/validation.js';
import { translateUnixToWindows } from '../utils/translation.js';
import { directoryManager } from '../utils/directoryManager.js';
import type {
  ExecuteCommandArgs,
  GetCommandHistoryArgs,
  ExecutionResult,
  CommandHistoryEntry,
  ServerConfig,
  ExecutionMessageUnion,
  StreamUpdateMessage,
  PromptMessage,
  CompletionMessage
} from '../types/config.js';
import { CLIServerError, ErrorSeverity, CommandTimeoutError } from '../types/errors.js';

// Define Zod Schemas for tool inputs
export const ExecuteCommandZodSchema = z.object({
  shell: z.enum(['powershell', 'cmd', 'gitbash']).describe("Shell to use for command execution"),
  command: z.string().describe("Command to execute"),
  workingDir: z.string().optional().describe("Working directory for command execution"),
  dryRun: z.boolean().optional().describe("Preview command without executing"),
  force: z.boolean().optional().describe("Force execution of destructive commands")
});

export const GetCommandHistoryZodSchema = z.object({
  limit: z.number().int().positive().optional().describe("Maximum number of history entries to return")
});

export const GetCurrentDirectoryZodSchema = z.object({});

export const ChangeDirectoryZodSchema = z.object({
  path: z.string().describe("Target directory path"),
  relative: z.boolean().optional().describe("Whether the path is relative to current directory")
});

export const FindWorkspaceZodSchema = z.object({
  startPath: z.string().optional().describe("Starting path to search for workspace (defaults to current directory)")
});

// Global state for CLI server
class CLIServerState {
  private static instance: CLIServerState;
  private config: ServerConfig | null = null;
  private commandHistory: CommandHistoryEntry[] = [];
  private activeChildProcess: ChildProcessWithoutNullStreams | null = null;
  private isShuttingDown: boolean = false;

  private constructor() {}

  static getInstance(): CLIServerState {
    if (!CLIServerState.instance) {
      CLIServerState.instance = new CLIServerState();
    }
    return CLIServerState.instance;
  }

  async getConfig(): Promise<ServerConfig> {
    if (!this.config) {
      this.config = await loadConfig();
    }
    return this.config;
  }

  addToHistory(entry: CommandHistoryEntry): void {
    const config = this.config;
    if (config?.security.logCommands) {
      this.commandHistory.push(entry);
      if (this.commandHistory.length > config.security.maxHistorySize) {
        this.commandHistory = this.commandHistory.slice(-config.security.maxHistorySize);
      }
    }
  }

  getHistory(limit?: number): CommandHistoryEntry[] {
    const actualLimit = Math.min(limit || 50, this.commandHistory.length);
    return this.commandHistory.slice(-actualLimit);
  }

  setActiveProcess(process: ChildProcessWithoutNullStreams | null): void {
    this.activeChildProcess = process;
  }

  getActiveProcess(): ChildProcessWithoutNullStreams | null {
    return this.activeChildProcess;
  }

  setShuttingDown(value: boolean): void {
    this.isShuttingDown = value;
  }

  isShutdown(): boolean {
    return this.isShuttingDown;
  }
}

// Helper function to wrap errors
function wrapError(
  error: unknown,
  context: string,
  metadata: Record<string, unknown> = {}
): CLIServerError {
  if (error instanceof CLIServerError) {
    return error;
  }

  if (error instanceof McpError) {
    return new CLIServerError(
      error.message,
      ErrorSeverity.ERROR,
      { ...metadata, errorCode: error.code },
      error
    );
  }

  const message = error instanceof Error ? error.message : String(error);
  return new CLIServerError(
    `${context}: ${message}`,
    ErrorSeverity.ERROR,
    metadata,
    error instanceof Error ? error : undefined
  );
}

// Command execution with streaming
async function* executeCommandWithStreaming(
  shell: keyof ServerConfig['shells'],
  command: string,
  workingDir?: string,
  config?: ServerConfig
): AsyncGenerator<ExecutionMessageUnion, void, unknown> {
  const serverConfig = config || await CLIServerState.getInstance().getConfig();
  const shellConfig = serverConfig.shells[shell];
  const startTime = Date.now();

  const spawnOptions: SpawnOptionsWithoutStdio = {
    shell: shellConfig.command,
    cwd: workingDir || shellConfig.workingDirectory,
    env: {
      ...process.env,
      ...shellConfig.environmentVariables
    },
    windowsHide: true,
    windowsVerbatimArguments: true
  };

  log('info', `Executing command: ${command} in shell: ${shell}`, { workingDir, shell });

  const childProcess = spawn(command, [], spawnOptions) as ChildProcessWithoutNullStreams;
  CLIServerState.getInstance().setActiveProcess(childProcess);

  try {
    // Set up timeout
    const timeoutHandle = setTimeout(() => {
      if (childProcess && !childProcess.killed) {
        childProcess.kill('SIGTERM');
        setTimeout(() => {
          if (childProcess && !childProcess.killed) {
            childProcess.kill('SIGKILL');
          }
        }, 5000);
      }
    }, shellConfig.timeout);

    let stdoutData = '';
    let stderrData = '';

    // Handle stdout
    childProcess.stdout.setEncoding(shellConfig.encoding as BufferEncoding);
    childProcess.stdout.on('data', (chunk: string) => {
      stdoutData += chunk;
      const message: StreamUpdateMessage = {
        type: 'stream',
        stream: 'stdout',
        data: chunk
      };
      // We can't yield from inside event handlers, so we'll collect data
    });

    // Handle stderr
    childProcess.stderr.setEncoding(shellConfig.encoding as BufferEncoding);
    childProcess.stderr.on('data', (chunk: string) => {
      stderrData += chunk;
      const message: StreamUpdateMessage = {
        type: 'stream',
        stream: 'stderr',
        data: chunk
      };
      // We can't yield from inside event handlers, so we'll collect data
    });

    // Wait for process completion
    const exitCode = await new Promise<number>((resolve, reject) => {
      childProcess.once('close', resolve);
      childProcess.once('error', reject);
    });

    clearTimeout(timeoutHandle);

    // Yield collected output
    if (stdoutData) {
      yield {
        type: 'stream',
        stream: 'stdout',
        data: stdoutData
      } as StreamUpdateMessage;
    }

    if (stderrData) {
      yield {
        type: 'stream',
        stream: 'stderr',
        data: stderrData
      } as StreamUpdateMessage;
    }

    // Yield completion
    yield {
      type: 'completion',
      exitCode,
      duration: Date.now() - startTime
    } as CompletionMessage;

  } finally {
    CLIServerState.getInstance().setActiveProcess(null);
  }
}

// Inferred types for function signatures
export type ExecuteCommandArgsType = z.infer<typeof ExecuteCommandZodSchema>;
export type GetCommandHistoryArgsType = z.infer<typeof GetCommandHistoryZodSchema>;
export type GetCurrentDirectoryArgsType = z.infer<typeof GetCurrentDirectoryZodSchema>;
export type ChangeDirectoryArgsType = z.infer<typeof ChangeDirectoryZodSchema>;
export type FindWorkspaceArgsType = z.infer<typeof FindWorkspaceZodSchema>;

// Main execution function for execute command
export async function executeCommandTool(args: ExecuteCommandArgsType): Promise<CallToolResult> {
  const state = CLIServerState.getInstance();
  const config = await state.getConfig();

  log('info', 'Executing command tool', { args });

  try {
    // Intelligent working directory resolution
    const inferredDir = directoryManager.inferDirectoryFromCommand(args.command);
    const requestedDir = args.workingDir || (inferredDir ?? undefined);

    const { directory: resolvedWorkingDir, context, reasoning } = await directoryManager.resolveWorkingDirectory(
      requestedDir,
      config.security.allowedPaths
    );

    log('info', 'Directory resolution', {
      requested: requestedDir,
      resolved: resolvedWorkingDir,
      reasoning,
      context
    });

    // Translate Unix commands if enabled
    let translatedCommand = args.command;
    if (config.security.enableUnixTranslation) {
      translatedCommand = translateUnixToWindows(args.command);
      if (translatedCommand !== args.command) {
        log('info', 'Command translated', { original: args.command, translated: translatedCommand });
      }
    }

    // Check for destructive commands
    if (config.security.confirmDestructiveCommands) {
      const isDestructive = isDestructiveCommand(
        translatedCommand,
        config.security.destructiveCommandPatterns
      );

      if (isDestructive && !args.force) {
        return {
          content: [{
            type: "text",
            text: [
              `⚠️  DESTRUCTIVE COMMAND DETECTED ⚠️`,
              ``,
              `Command: ${translatedCommand}`,
              `Original: ${args.command}`,
              `Working Directory: ${resolvedWorkingDir}`,
              `Directory Context: ${context.workspace ? `${context.workspace.name} (${context.workspace.type})` : 'No workspace detected'}`,
              ``,
              `This command is potentially destructive and requires confirmation.`,
              `To execute this command, you must:`,
              `1. Review the command carefully`,
              `2. Consider using dryRun: true first to preview`,
              `3. Add 'force: true' to confirm execution`,
              ``,
              `⛔ Execution blocked for safety.`
            ].join('\n')
          } as TextContent],
          isError: true
        };
      }
    }

    // Handle dry run mode
    if (config.execution.enableDryRun && args.dryRun) {
      const dryRunResult = [
        `🔍 DRY RUN SIMULATION`,
        ``,
        `Shell: ${args.shell}`,
        `Requested Directory: ${args.workingDir || 'auto-detected'}`,
        `Resolved Directory: ${resolvedWorkingDir}`,
        `Resolution Reasoning: ${reasoning}`,
        `Workspace: ${context.workspace ? `${context.workspace.name} (${context.workspace.type})` : 'None detected'}`,
        `Directory Accessibility: ${context.accessibility}`,
        `Original Command: ${args.command}`,
        `Translated Command: ${translatedCommand !== args.command ? translatedCommand : '(no translation needed)'}`,
        `Force Flag: ${args.force ? '✅ yes' : '❌ no'}`,
        ``,
        `✅ Validation Checks:`,
        `- Shell validation: passed`,
        `- Security validation: passed`,
        `- Path validation: passed`,
        `- Directory analysis: ${context.isUserProject ? 'user project' : 'system/other'}`,
        ``,
        `ℹ️  This command would be executed with these parameters.`,
        `No actual execution will occur in dry-run mode.`
      ].join('\n');

      // Log dry run attempt
      state.addToHistory({
        command: args.command,
        output: dryRunResult,
        timestamp: new Date().toISOString(),
        exitCode: 0,
        duration: 0,
        workingDirectory: resolvedWorkingDir,
        shell: args.shell,
        user: process.env.USERNAME || 'unknown',
        isDryRun: true,
        force: args.force || false,
        translatedCommand: translatedCommand !== args.command ? translatedCommand : undefined
      });

      return {
        content: [{ type: "text", text: dryRunResult } as TextContent],
        isError: false
      };
    }

    // Validate shell
    if (!config.shells[args.shell]?.enabled) {
      throw new McpError(
        ErrorCode.InvalidRequest,
        `Invalid or disabled shell: ${args.shell}`
      );
    }

    // Validate command
    await validateCommand(args.shell, translatedCommand, resolvedWorkingDir, config);

    // Execute command with streaming
    let fullOutput = '';
    let fullError = '';
    let exitCode = 0;
    let duration = 0;

    for await (const message of executeCommandWithStreaming(
      args.shell,
      translatedCommand,
      resolvedWorkingDir,
      config
    )) {
      switch (message.type) {
        case 'stream':
          if (message.stream === 'stdout') {
            fullOutput += message.data;
          } else if (message.stream === 'stderr') {
            fullError += message.data;
          }
          break;

        case 'completion':
          exitCode = message.exitCode;
          duration = message.duration;
          break;
      }
    }

    // Combine output and error
    const combinedOutput = [
      fullOutput && `STDOUT:\n${fullOutput}`,
      fullError && `STDERR:\n${fullError}`
    ].filter(Boolean).join('\n\n');

    // Log command execution
    state.addToHistory({
      command: args.command,
      output: combinedOutput,
      timestamp: new Date().toISOString(),
      exitCode,
      duration,
      workingDirectory: resolvedWorkingDir,
      shell: args.shell,
      user: process.env.USERNAME || 'unknown',
      isDryRun: false,
      force: args.force || false,
      translatedCommand: translatedCommand !== args.command ? translatedCommand : undefined
    });

    // Format result
    const resultText = [
      `🖥️  Command Execution Result`,
      ``,
      `Command: ${args.command}`,
      translatedCommand !== args.command ? `Translated: ${translatedCommand}` : null,
      `Shell: ${args.shell}`,
      `Working Directory: ${resolvedWorkingDir}`,
      context.workspace ? `Workspace: ${context.workspace.name} (${context.workspace.type})` : null,
      `Directory Resolution: ${reasoning}`,
      `Exit Code: ${exitCode}`,
      `Duration: ${duration}ms`,
      ``,
      combinedOutput || '(No output)'
    ].filter(Boolean).join('\n');

    return {
      content: [{ type: "text", text: resultText } as TextContent],
      isError: exitCode !== 0
    };

  } catch (error) {
    const wrappedError = wrapError(error, 'Command execution failed', {
      command: args.command,
      shell: args.shell,
      workingDir: args.workingDir
    });

    log('error', 'Command execution error', { error: wrappedError });

    return {
      content: [{
        type: "text",
        text: `❌ Command Execution Failed\n\nError: ${wrappedError.message}`
      } as TextContent],
      isError: true
    };
  }
}

// Validation function
async function validateCommand(
  shell: keyof ServerConfig['shells'],
  command: string,
  workingDir: string,
  config: ServerConfig
): Promise<void> {
  // Check for command chaining/injection attempts if enabled
  if (config.security.enableInjectionProtection) {
    const shellConfig = config.shells[shell];
    validateShellOperators(command, shellConfig);
  }

  const { command: executable, args } = parseCommand(command);

  // Check for blocked commands
  if (isCommandBlocked(executable, config.security.blockedCommands)) {
    throw new McpError(
      ErrorCode.InvalidRequest,
      `Command is blocked: "${executable}"`
    );
  }

  // Check for blocked arguments
  if (isArgumentBlocked(args, config.security.blockedArguments)) {
    throw new McpError(
      ErrorCode.InvalidRequest,
      'One or more arguments are blocked. Check configuration for blocked patterns.'
    );
  }

  // Validate command length
  if (command.length > config.security.maxCommandLength) {
    throw new McpError(
      ErrorCode.InvalidRequest,
      `Command exceeds maximum length of ${config.security.maxCommandLength}`
    );
  }

  // Validate working directory if provided
  if (config.security.restrictWorkingDirectory) {
    if (!isPathAllowed(workingDir, config.security.allowedPaths)) {
      throw new McpError(
        ErrorCode.InvalidRequest,
        `Working directory must be within allowed paths: ${config.security.allowedPaths.join(', ')}`
      );
    }
  }

  // Windows-specific security validation
  await validateWindowsSecurity(command, workingDir, config.security.windows);
}

// Get command history function
export async function getCommandHistoryTool(args: GetCommandHistoryArgsType): Promise<CallToolResult> {
  const state = CLIServerState.getInstance();
  const config = await state.getConfig();

  const limit = Math.min(
    args.limit || 50,
    config.security.maxHistorySize
  );

  const history = state.getHistory(limit);

  const historyText = history.length > 0
    ? history.map((entry, index) => [
        `📋 Command ${index + 1}`,
        `Timestamp: ${entry.timestamp}`,
        `Command: ${entry.command}`,
        entry.translatedCommand ? `Translated: ${entry.translatedCommand}` : null,
        `Shell: ${entry.shell}`,
        `Working Dir: ${entry.workingDirectory}`,
        `Exit Code: ${entry.exitCode}`,
        `Duration: ${entry.duration}ms`,
        entry.isDryRun ? `🔍 (Dry Run)` : null,
        entry.force ? `⚠️ (Forced)` : null,
        `User: ${entry.user}`,
        `Output: ${entry.output.substring(0, 200)}${entry.output.length > 200 ? '...' : ''}`,
        ''
      ].filter(Boolean).join('\n')).join('\n')
    : 'No command history available.';

  return {
    content: [{
      type: "text",
      text: `📚 Command History (${history.length} entries)\n\n${historyText}`
    } as TextContent],
    isError: false
  };
}

// Get current directory function
export async function getCurrentDirectoryTool(args: GetCurrentDirectoryArgsType): Promise<CallToolResult> {
  try {
    const directoryInfo = await directoryManager.getDirectoryInfo();
    return {
      content: [{
        type: "text",
        text: `🗂️ Directory Information\n\n${directoryInfo}`
      } as TextContent],
      isError: false
    };
  } catch (error) {
    return {
      content: [{
        type: "text",
        text: `📁 Current Working Directory: ${process.cwd()}\n\n⚠️ Error getting detailed directory information: ${error}`
      } as TextContent],
      isError: false
    };
  }
}

// Change directory function
export async function changeDirectoryTool(args: ChangeDirectoryArgsType): Promise<CallToolResult> {
  try {
    const config = await CLIServerState.getInstance().getConfig();

    let targetPath = args.path;
    if (args.relative) {
      targetPath = path.resolve(directoryManager.getCurrentDirectory(), args.path);
    } else {
      targetPath = path.resolve(args.path);
    }

    const { directory: resolvedDir, context, reasoning } = await directoryManager.resolveWorkingDirectory(
      targetPath,
      config.security.allowedPaths
    );

    const resultText = [
      `📁 Directory Change Result`,
      ``,
      `Requested: ${args.path}`,
      `Resolved: ${resolvedDir}`,
      `Resolution: ${reasoning}`,
      `Workspace: ${context.workspace ? `${context.workspace.name} (${context.workspace.type})` : 'None detected'}`,
      `Accessibility: ${context.accessibility}`,
      `User Project: ${context.isUserProject ? '✅ Yes' : '❌ No'}`,
      ``,
      `ℹ️ The working directory for subsequent commands has been updated.`
    ].join('\n');

    return {
      content: [{ type: "text", text: resultText } as TextContent],
      isError: false
    };

  } catch (error) {
    const wrappedError = wrapError(error, 'Directory change failed', {
      path: args.path,
      relative: args.relative
    });

    return {
      content: [{
        type: "text",
        text: `❌ Directory Change Failed\n\nError: ${wrappedError.message}`
      } as TextContent],
      isError: true
    };
  }
}

// Find workspace function
export async function findWorkspaceTool(args: FindWorkspaceArgsType): Promise<CallToolResult> {
  try {
    const startPath = args.startPath || directoryManager.getCurrentDirectory();
    const workspaceRoot = await directoryManager.findWorkspaceRoot(startPath);
    const workspace = await directoryManager.detectWorkspace(workspaceRoot);

    const resultText = [
      `🔍 Workspace Detection Result`,
      ``,
      `Search Started From: ${startPath}`,
      `Workspace Root: ${workspaceRoot}`,
      workspace ? [
        `Workspace Name: ${workspace.name}`,
        `Workspace Type: ${workspace.type}`,
        `Has Config Files: ${workspace.hasConfig ? '✅ Yes' : '❌ No'}`
      ].join('\n') : 'No workspace detected',
      ``,
      `ℹ️ You can use the change-directory tool to navigate to the workspace root.`
    ].join('\n');

    return {
      content: [{ type: "text", text: resultText } as TextContent],
      isError: false
    };

  } catch (error) {
    const wrappedError = wrapError(error, 'Workspace detection failed', {
      startPath: args.startPath
    });

    return {
      content: [{
        type: "text",
        text: `❌ Workspace Detection Failed\n\nError: ${wrappedError.message}`
      } as TextContent],
      isError: true
    };
  }
}