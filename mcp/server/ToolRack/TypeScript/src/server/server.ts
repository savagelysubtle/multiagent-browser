process.stderr.write('SERVER.TS TOP OF FILE\n');
process.stderr.write(`SERVER.TS CWD AT VERY START: ${process.cwd()}\n`);
process.stderr.write(`SERVER.TS BRAVE_API_KEY AT VERY START: ${process.env.BRAVE_API_KEY || 'UNDEFINED'}\n`);

import 'dotenv/config';
import { log } from '../utils/logger.js'; // Import the logger

// --- Debugging Logs ---
log('warn', `MCP Server Starting. CWD: ${process.cwd()}`);
// ----------------------

log('info', "dotenv/config imported.");
// --- Debugging Logs ---
log('warn', `API Key check after dotenv: ${process.env.BRAVE_API_KEY ? 'LOADED' : 'MISSING'}`);
// ----------------------
log('info', `BRAVE_API_KEY from process.env after dotenv: ${process.env.BRAVE_API_KEY ? 'Loaded' : 'NOT LOADED'}`);

import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { CallToolResult, TextContent } from "@modelcontextprotocol/sdk/types.js"; // Import types for wrapper
import { z } from 'zod';

// Import the tool execution functions and schemas
import {
  executeWebSearch,
  executeCodeSearch,
  BraveWebSearchZodSchema,
  BraveCodeSearchZodSchema
} from '../tools/braveSearchTools.js';

// Import Windows CLI tools
import {
  executeCommandTool,
  getCommandHistoryTool,
  getCurrentDirectoryTool,
  changeDirectoryTool,
  findWorkspaceTool,
  ExecuteCommandZodSchema,
  GetCommandHistoryZodSchema,
  GetCurrentDirectoryZodSchema,
  ChangeDirectoryZodSchema,
  FindWorkspaceZodSchema
} from '../tools/winCliTools.js';

log('info', "Imported from ../tools/braveSearchTools.js");

// Setup signal handlers for graceful shutdown (following Python pattern)
function setupSignalHandlers(): void {
  const signalHandler = (signal: string) => {
    log('info', `Received signal ${signal}, shutting down gracefully`);
    try {
      // Perform any necessary cleanup here
      process.exit(0);
    } catch (error) {
      log('error', `Error during shutdown: ${error}`);
      process.exit(1);
    }
  };

  process.on('SIGINT', () => signalHandler('SIGINT'));
  process.on('SIGTERM', () => signalHandler('SIGTERM'));
}

// Setup error handling for unhandled exceptions (following Python pattern)
function setupErrorHandling(): void {
  process.on('uncaughtException', (error) => {
    log('error', 'Uncaught exception:', error);
    process.exit(1);
  });

  process.on('unhandledRejection', (reason, promise) => {
    log('error', 'Unhandled rejection at:', promise, 'reason:', reason);
    process.exit(1);
  });
}

// Helper function to wrap tool execution with logging
async function wrapToolExecution(
  toolName: string,
  executor: (args: any) => Promise<CallToolResult>,
  args: unknown
): Promise<CallToolResult> {
  log('info', `Executing tool: ${toolName}`, { args }); // Log args too
  try {
    const result = await executor(args as any);
    if (result.isError) {
      log('warn', `Tool ${toolName} finished with error.`, { result });
    } else {
      log('info', `Tool ${toolName} finished successfully.`); // Avoid logging potentially large results unless debugging
      // log('debug', `Tool ${toolName} result:`, { result }); // Optional: Add if needed for debugging
    }
    return result;
  } catch (executionError) {
    // This catches errors *thrown* by the executor, which shouldn't happen
    // if it follows the pattern of returning { isError: true, ... }
    log('error', `Unexpected error thrown during ${toolName} execution:`, executionError);
    return {
      content: [{ type: "text", text: `Unexpected server error during ${toolName}: ${executionError instanceof Error ? executionError.message : String(executionError)}` } as TextContent],
      isError: true,
    };
  }
}


async function main() {
  log('info', "Starting AiChemistForge MCP Server...");

  // Setup error handling and signal handlers (following Python pattern)
  setupErrorHandling();
  setupSignalHandlers();

  try {
    const server = new McpServer({
      name: "AiChemistForgeServer",
      version: "0.2.0", // Increment version for new functionality
      description: "MCP Server providing Brave Search and Windows CLI execution tools.",
      capabilities: {
        tools: {}, // CRITICAL: Must declare tools capability when providing tools
        resources: {},
      }
    });

    // Register Brave Search tools using the correct registerTool API
    log('info', 'Registering tool: brave_web_search');
    server.registerTool(
      "brave_web_search",
      {
        description: "Performs a web search using the Brave Search API, ideal for general queries, news, articles, and online content. " +
                    "Use this for broad information gathering, recent events, or when you need diverse web sources. " +
                    "Supports pagination, content filtering, and freshness controls. " +
                    "Maximum 20 results per request, with offset for pagination.",
        inputSchema: {
          query: z.string().describe("Search query (max 400 chars, 50 words)"),
          count: z.number().default(10).describe("Number of results (1-20, default 10)").optional(),
          offset: z.number().default(0).describe("Pagination offset (max 9, default 0)").optional(),
        },
        annotations: {
          title: "Brave Web Search"
        }
      },
      async (args) => wrapToolExecution("brave_web_search", executeWebSearch, args)
    );

    log('info', 'Registering tool: brave_code_search');
    server.registerTool(
      "brave_code_search",
      {
        description: "Searches developer-focused sites like Stack Overflow, GitHub, MDN, and technical subreddits using Brave Search. " +
                    "Ideal for finding code snippets, technical documentation, programming discussions, and solutions to coding problems. " +
                    "Uses targeted site search for relevance. Supports result count customization. " +
                    "Maximum 20 results per request.",
        inputSchema: {
          query: z.string().describe("Code search query (e.g. 'github repository for brave search')"),
          count: z.number().default(10).describe("Number of results (1-20, default 10)").optional(),
        },
        annotations: {
          title: "Brave Code Search"
        }
      },
      async (args) => wrapToolExecution("brave_code_search", executeCodeSearch, args)
    );

    // Register Windows CLI tools
    log('info', 'Registering tool: execute_command');
    server.registerTool(
      "execute_command",
      {
        description: "Execute a Windows command line command safely with validation and security controls.",
        inputSchema: {
          shell: z.enum(['powershell', 'cmd', 'gitbash']).describe("Shell to use for command execution"),
          command: z.string().describe("Command to execute"),
          workingDir: z.string().optional().describe("Working directory for command execution"),
          dryRun: z.boolean().optional().describe("Preview command without executing"),
          force: z.boolean().optional().describe("Force execution of destructive commands")
        },
        annotations: {
          title: "Execute Command"
        }
      },
      async (args) => wrapToolExecution("execute_command", executeCommandTool, args)
    );

    log('info', 'Registering tool: get_command_history');
    server.registerTool(
      "get_command_history",
      {
        description: "Retrieve the recent command execution history.",
        inputSchema: {
          limit: z.number().int().positive().optional().describe("Maximum number of history entries to return")
        },
        annotations: {
          title: "Get Command History"
        }
      },
      async (args) => wrapToolExecution("get_command_history", getCommandHistoryTool, args)
    );

    log('info', 'Registering tool: get_current_directory');
    server.registerTool(
      "get_current_directory",
      {
        description: "Get comprehensive information about the current working directory, workspace detection, and directory stack.",
        inputSchema: {},
        annotations: {
          title: "Get Current Directory"
        }
      },
      async (args) => wrapToolExecution("get_current_directory", getCurrentDirectoryTool, args)
    );

    log('info', 'Registering tool: change_directory');
    server.registerTool(
      "change_directory",
      {
        description: "Intelligently change the working directory with workspace detection and path validation.",
        inputSchema: {
          path: z.string().describe("Target directory path"),
          relative: z.boolean().optional().describe("Whether the path is relative to current directory")
        },
        annotations: {
          title: "Change Directory"
        }
      },
      async (args) => wrapToolExecution("change_directory", changeDirectoryTool, args)
    );

    log('info', 'Registering tool: find_workspace');
    server.registerTool(
      "find_workspace",
      {
        description: "Find and analyze workspace information starting from a given directory, detecting project types and configuration files.",
        inputSchema: {
          startPath: z.string().optional().describe("Starting path to search for workspace (defaults to current directory)")
        },
        annotations: {
          title: "Find Workspace"
        }
      },
      async (args) => wrapToolExecution("find_workspace", findWorkspaceTool, args)
    );

    log('info', `All tools registered.`);

    const transport = new StdioServerTransport();
    log('info', "Connecting to transport...");

    // Small delay to ensure all modules are fully initialized (following Python pattern)
    await new Promise(resolve => setTimeout(resolve, 100));

    await server.connect(transport);

    log('info', "AiChemistForge MCP Server connected and listening on stdio.");
    log('info', "Stdio transport selected - logs will appear on stderr");

    // Keep the process alive
    process.stdin.resume();

  } catch (error) {
    log('error', "Failed to start or run AiChemistForge MCP Server:", error);
    if (error instanceof Error && error.stack) {
      log('error', "Stack trace:", error.stack);
    }
    process.exit(1);
  }
}

// Enhanced error handling for main function (following Python pattern)
main().catch(error => {
  log('error', "Unhandled error in main async function execution:", error);
  if (error instanceof Error && error.stack) {
    log('error', "Stack trace:", error.stack);
  }
  process.exit(1);
});
