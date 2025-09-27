import path from 'path';
import { exec } from 'child_process';
import { promisify } from 'util';
import type { ShellConfig } from '../types/config.js';

const execAsync = promisify(exec);

// Cache for resolved command paths
const commandPathCache = new Map<string, string | null>();

// Cache for compiled regexes
const blockedArgRegexCache = new Map<string, RegExp>();
const shellOperatorRegexCache = new Map<string, RegExp>();

// Cache for blocked command sets
const blockedCommandSetCache = new Map<string, Set<string>>();

export async function resolveCommandPath(command: string): Promise<string | null> {
  const lowerCaseCommand = command.toLowerCase();
  if (commandPathCache.has(lowerCaseCommand)) {
    return commandPathCache.get(lowerCaseCommand)!;
  }

  try {
    const { stdout } = await execAsync(`where "${command}"`, { encoding: 'utf8' });
    const resolvedPath = stdout.split('\n')[0].trim();
    commandPathCache.set(lowerCaseCommand, resolvedPath);
    return resolvedPath;
  } catch {
    commandPathCache.set(lowerCaseCommand, null);
    return null;
  }
}

export function extractCommandName(command: string): string {
  const basename = path.basename(command);
  return basename.replace(/\.(exe|cmd|bat)$/i, '').toLowerCase();
}

export function isCommandBlocked(command: string, blockedCommands: string[]): boolean {
  const commandName = extractCommandName(command.toLowerCase());

  const blockedCommandsKey = JSON.stringify(blockedCommands.sort());
  let blockedSet = blockedCommandSetCache.get(blockedCommandsKey);

  if (!blockedSet) {
    blockedSet = new Set<string>();
    blockedCommands.forEach(blocked => {
      const lowerBlocked = blocked.toLowerCase();
      blockedSet!.add(lowerBlocked);
      blockedSet!.add(`${lowerBlocked}.exe`);
      blockedSet!.add(`${lowerBlocked}.cmd`);
      blockedSet!.add(`${lowerBlocked}.bat`);
    });
    blockedCommandSetCache.set(blockedCommandsKey, blockedSet);
  }

  return blockedSet.has(commandName);
}

export function isArgumentBlocked(args: string[], blockedArguments: string[]): boolean {
  const regexes = blockedArguments.map(blocked => {
    const cacheKey = `^${blocked}$_i`;
    if (!blockedArgRegexCache.has(cacheKey)) {
      blockedArgRegexCache.set(cacheKey, new RegExp(`^${blocked}$`, 'i'));
    }
    return blockedArgRegexCache.get(cacheKey)!;
  });

  return args.some(arg =>
    regexes.some(regex => regex.test(arg))
  );
}

export function validateShellOperators(command: string, shellConfig: ShellConfig): void {
  if (!shellConfig.blockedOperators?.length) {
    return;
  }

  const cacheKey = JSON.stringify(shellConfig.blockedOperators.sort());
  let regex = shellOperatorRegexCache.get(cacheKey);

  if (!regex) {
    const operatorPattern = shellConfig.blockedOperators
      .map(op => op.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
      .join('|');
    regex = new RegExp(operatorPattern);
    shellOperatorRegexCache.set(cacheKey, regex);
  }

  if (regex.test(command)) {
    throw new Error(`Command contains blocked operators for this shell: ${shellConfig.blockedOperators.join(', ')}`);
  }
}

export function parseCommand(fullCommand: string): { command: string; args: string[] } {
  fullCommand = fullCommand.trim();
  if (!fullCommand) {
    return { command: '', args: [] };
  }

  const tokens: string[] = [];
  let current = '';
  let inQuotes = false;
  let quoteChar = '';

  for (let i = 0; i < fullCommand.length; i++) {
    const char = fullCommand[i];

    if ((char === '"' || char === "'") && (!inQuotes || char === quoteChar)) {
      if (inQuotes) {
        tokens.push(current);
        current = '';
      }
      inQuotes = !inQuotes;
      quoteChar = inQuotes ? char : '';
      continue;
    }

    if (char === ' ' && !inQuotes) {
      if (current) {
        tokens.push(current);
        current = '';
      }
      continue;
    }

    current += char;
  }

  if (current) {
    tokens.push(current);
  }

  if (tokens.length === 0) {
    return { command: '', args: [] };
  }

  if (!tokens[0].includes(' ') && !tokens[0].includes('\\')) {
    return {
      command: tokens[0],
      args: tokens.slice(1)
    };
  }

  let commandTokens: string[] = [];
  let i = 0;

  while (i < tokens.length) {
    commandTokens.push(tokens[i]);
    const potentialCommand = commandTokens.join(' ');

    if (/\.(exe|cmd|bat)$/i.test(potentialCommand) ||
        (!potentialCommand.includes('\\') && commandTokens.length === 1)) {
      return {
        command: potentialCommand,
        args: tokens.slice(i + 1)
      };
    }

    if (potentialCommand.includes('\\')) {
      i++;
      continue;
    }

    return {
      command: tokens[0],
      args: tokens.slice(1)
    };
  }

  return {
    command: commandTokens.join(' '),
    args: tokens.slice(commandTokens.length)
  };
}

export function isPathAllowed(testPath: string, allowedPaths: string[]): boolean {
  const normalizedPath = path.normalize(testPath).toLowerCase();
  return allowedPaths.some(allowedPath => {
    const normalizedAllowedPath = path.normalize(allowedPath).toLowerCase();
    return normalizedPath.startsWith(normalizedAllowedPath);
  });
}

export function validateWorkingDirectory(dir: string, allowedPaths: string[]): void {
  if (!path.isAbsolute(dir)) {
    throw new Error('Working directory must be an absolute path');
  }

  if (!isPathAllowed(dir, allowedPaths)) {
    const allowedPathsStr = allowedPaths.join(', ');
    throw new Error(
      `Working directory must be within allowed paths: ${allowedPathsStr}`
    );
  }
}

export function normalizeWindowsPath(inputPath: string): string {
  let normalized = inputPath.replace(/\//g, '\\');

  if (/^[a-zA-Z]:\\.+/.test(normalized)) {
    return path.normalize(normalized);
  }

  if (normalized.startsWith('\\')) {
    normalized = `C:${normalized}`;
  }

  return path.normalize(normalized);
}