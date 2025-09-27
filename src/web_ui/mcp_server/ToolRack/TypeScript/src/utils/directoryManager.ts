import { promises as fs } from 'fs';
import path from 'path';
import { log } from './logger.js';

export interface WorkspaceInfo {
  root: string;
  type: 'git' | 'npm' | 'python' | 'rust' | 'dotnet' | 'generic';
  name: string;
  hasConfig: boolean;
}

export interface DirectoryContext {
  current: string;
  workspace?: WorkspaceInfo;
  suggested: string;
  isUserProject: boolean;
  accessibility: 'full' | 'restricted' | 'blocked';
}

export class DynamicDirectoryManager {
  private static instance: DynamicDirectoryManager;
  private directoryStack: string[] = [];
  private workspaceCache: Map<string, WorkspaceInfo> = new Map();
  private lastKnownUserDirectory: string | null = null;

  private constructor() {
    // Initialize with sensible defaults
    this.directoryStack.push(process.cwd());
  }

  static getInstance(): DynamicDirectoryManager {
    if (!DynamicDirectoryManager.instance) {
      DynamicDirectoryManager.instance = new DynamicDirectoryManager();
    }
    return DynamicDirectoryManager.instance;
  }

  /**
   * Detect workspace information for a given directory
   */
  async detectWorkspace(directory: string): Promise<WorkspaceInfo | null> {
    const cached = this.workspaceCache.get(directory);
    if (cached) {
      return cached;
    }

    try {
      const stat = await fs.stat(directory);
      if (!stat.isDirectory()) {
        return null;
      }

      // Check for various workspace indicators
      const checks = [
        { file: '.git', type: 'git' as const },
        { file: 'package.json', type: 'npm' as const },
        { file: 'requirements.txt', type: 'python' as const },
        { file: 'pyproject.toml', type: 'python' as const },
        { file: 'Cargo.toml', type: 'rust' as const },
        { file: '*.sln', type: 'dotnet' as const },
        { file: '*.csproj', type: 'dotnet' as const }
      ];

      for (const check of checks) {
        const filePath = path.join(directory, check.file);
        try {
          await fs.access(filePath);
          const workspace: WorkspaceInfo = {
            root: directory,
            type: check.type,
            name: path.basename(directory),
            hasConfig: true
          };
          this.workspaceCache.set(directory, workspace);
          return workspace;
        } catch {
          // Continue checking
        }
      }

      // Generic directory with no specific markers
      const workspace: WorkspaceInfo = {
        root: directory,
        type: 'generic',
        name: path.basename(directory),
        hasConfig: false
      };

      this.workspaceCache.set(directory, workspace);
      return workspace;

    } catch (error) {
      log('warn', 'Failed to detect workspace', { directory, error });
      return null;
    }
  }

  /**
   * Find the nearest workspace root by walking up the directory tree
   */
  async findWorkspaceRoot(startDirectory: string): Promise<string> {
    let current = path.resolve(startDirectory);
    const root = path.parse(current).root;

    while (current !== root) {
      const workspace = await this.detectWorkspace(current);
      if (workspace && workspace.hasConfig) {
        return current;
      }
      current = path.dirname(current);
    }

    // Return the original directory if no workspace found
    return startDirectory;
  }

  /**
   * Analyze directory context and provide recommendations
   */
  async analyzeDirectory(directory: string, allowedPaths: string[]): Promise<DirectoryContext> {
    const resolved = path.resolve(directory);

    // Check accessibility
    let accessibility: DirectoryContext['accessibility'] = 'full';
    if (allowedPaths.length > 0) {
      const isAllowed = allowedPaths.some(allowedPath =>
        resolved.startsWith(path.resolve(allowedPath))
      );
      accessibility = isAllowed ? 'full' : 'restricted';
    }

    // Detect workspace
    const workspace = await this.detectWorkspace(resolved);

    // Determine if this looks like a user project directory
    const isUserProject = this.isLikelyUserProject(resolved);

    // Suggest the best directory to use
    let suggested = resolved;
    if (workspace && workspace.hasConfig) {
      suggested = workspace.root;
    } else if (!isUserProject && this.lastKnownUserDirectory) {
      suggested = this.lastKnownUserDirectory;
    }

    // Update last known user directory if this looks like a user project
    if (isUserProject) {
      this.lastKnownUserDirectory = resolved;
    }

    return {
      current: resolved,
      workspace: workspace ?? undefined,
      suggested,
      isUserProject,
      accessibility
    };
  }

  /**
   * Determine if a directory looks like a user project
   */
  private isLikelyUserProject(directory: string): boolean {
    const normalized = path.resolve(directory).toLowerCase();

    // System directories that are unlikely to be user projects
    const systemPaths = [
      'c:\\windows',
      'c:\\program files',
      'c:\\program files (x86)',
      'c:\\programdata',
      'c:\\$recycle.bin',
      process.env.WINDIR?.toLowerCase(),
      process.env.SYSTEMROOT?.toLowerCase()
    ].filter(Boolean);

    const isSystemPath = systemPaths.some(sysPath =>
      sysPath && normalized.startsWith(sysPath)
    );

    if (isSystemPath) {
      return false;
    }

    // User profile areas that are likely projects
    const userPaths = [
      process.env.USERPROFILE?.toLowerCase(),
      'c:\\users',
      'd:\\',
      'e:\\',
      'f:\\' // Common development drives
    ].filter(Boolean);

    return userPaths.some(userPath =>
      userPath && normalized.startsWith(userPath)
    );
  }

  /**
   * Smart working directory resolution
   */
  async resolveWorkingDirectory(
    requestedDir?: string,
    allowedPaths: string[] = []
  ): Promise<{
    directory: string;
    context: DirectoryContext;
    reasoning: string;
  }> {
    // Start with the requested directory or current working directory
    let targetDir = requestedDir || this.getCurrentDirectory();

    try {
      // Analyze the target directory
      const context = await this.analyzeDirectory(targetDir, allowedPaths);

      let finalDir = targetDir;
      let reasoning = 'Using requested directory';

      // Apply intelligent fallbacks
      if (context.accessibility === 'restricted' || context.accessibility === 'blocked') {
        if (this.lastKnownUserDirectory && allowedPaths.some(p =>
          this.lastKnownUserDirectory!.startsWith(path.resolve(p))
        )) {
          finalDir = this.lastKnownUserDirectory;
          reasoning = 'Fallback to last known user directory due to path restrictions';
        } else if (allowedPaths.length > 0) {
          finalDir = allowedPaths[0];
          reasoning = 'Fallback to first allowed path due to restrictions';
        }
      } else if (context.workspace?.root && context.workspace.root !== targetDir) {
        // Suggest workspace root if we found one
        finalDir = context.workspace.root;
        reasoning = `Using workspace root (${context.workspace.type} project)`;
      }

      // Update our state
      this.pushDirectory(finalDir);

      const finalContext = await this.analyzeDirectory(finalDir, allowedPaths);

      return {
        directory: finalDir,
        context: finalContext,
        reasoning
      };

    } catch (error) {
      log('error', 'Error resolving working directory', { targetDir, error });

      // Ultimate fallback
      const fallbackDir = this.lastKnownUserDirectory || process.cwd();
      const fallbackContext = await this.analyzeDirectory(fallbackDir, allowedPaths);

      return {
        directory: fallbackDir,
        context: fallbackContext,
        reasoning: 'Fallback due to error in directory resolution'
      };
    }
  }

  /**
   * Directory stack management
   */
  pushDirectory(directory: string): void {
    const resolved = path.resolve(directory);
    if (this.directoryStack[this.directoryStack.length - 1] !== resolved) {
      this.directoryStack.push(resolved);
      // Keep stack reasonable size
      if (this.directoryStack.length > 10) {
        this.directoryStack = this.directoryStack.slice(-10);
      }
    }
  }

  popDirectory(): string | null {
    if (this.directoryStack.length > 1) {
      this.directoryStack.pop();
      return this.directoryStack[this.directoryStack.length - 1];
    }
    return null;
  }

  getCurrentDirectory(): string {
    return this.directoryStack[this.directoryStack.length - 1] || process.cwd();
  }

  getDirectoryStack(): string[] {
    return [...this.directoryStack];
  }

  /**
   * Infer working directory from command content
   */
  inferDirectoryFromCommand(command: string): string | null {
    // Extract potential paths from the command
    const pathPattern = /(?:[a-zA-Z]:\\(?:[^\\/:*?"<>|\r\n]+\\)*[^\\/:*?"<>|\r\n]*)|(?:\.{1,2}[/\\](?:[^/\\:*?"<>|\r\n]+[/\\])*[^/\\:*?"<>|\r\n]*)/g;
    const paths = command.match(pathPattern);

    if (paths) {
      for (const potentialPath of paths) {
        try {
          const resolved = path.resolve(this.getCurrentDirectory(), potentialPath);
          const stat = require('fs').statSync(resolved);
          if (stat.isDirectory()) {
            return path.dirname(resolved);
          } else if (stat.isFile()) {
            return path.dirname(resolved);
          }
        } catch {
          // Path doesn't exist or isn't accessible
        }
      }
    }

    return null;
  }

  /**
   * Generate helpful directory information for users
   */
  async getDirectoryInfo(directory?: string): Promise<string> {
    const targetDir = directory || this.getCurrentDirectory();
    const context = await this.analyzeDirectory(targetDir, []);

    const info = [
      `📁 Current Directory: ${context.current}`,
      context.workspace ? `🏗️  Workspace: ${context.workspace.name} (${context.workspace.type})` : '📂 No workspace detected',
      `🔐 Accessibility: ${context.accessibility}`,
      `👤 User Project: ${context.isUserProject ? '✅' : '❌'}`,
      ''
    ];

    if (this.directoryStack.length > 1) {
      info.push('📚 Directory Stack:');
      this.directoryStack.forEach((dir, index) => {
        const marker = index === this.directoryStack.length - 1 ? '👉' : '  ';
        info.push(`${marker} ${dir}`);
      });
    }

    return info.join('\n');
  }
}

export const directoryManager = DynamicDirectoryManager.getInstance();