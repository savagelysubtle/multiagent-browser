# AiChemistForge - Unified MCP Server Development Workspace

## Project Overview

AiChemistForge is a unified development workspace for creating Model Context Protocol (MCP) servers across multiple programming languages (Python, TypeScript, Rust). This project provides structured tooling, reusable components, and clear architectural guidance for AI development workflows.

**Core Technology Stack:**
- **Python**: Primary implementation using `uv` package manager, FastMCP SDK, Python 3.13+
- **TypeScript**: Node.js MCP implementations with Brave Search integration
- **Rust**: Experimental filesystem tools with async support
- **Architecture**: Plugin-style tool registration with modular monolith pattern

## Development Environment Setup

### Prerequisites
- Python 3.13+ with `uv` package manager
- Node.js 18+ with npm/pnpm
- Rust toolchain (for Rust server development)
- Cursor IDE (recommended for full integration)

### Quick Setup Commands
```bash
# Python Server (Primary)
cd ToolRack/Python
uv sync --all-groups
uv run unified-mcp-server

# TypeScript Server
cd ToolRack/TypeScript
npm install
npm run build
npm run start

# Rust Server (Experimental)
cd ToolRack/Rust
cargo build --release
cargo run
```

### Environment Variables
Always set these for proper MCP operation:
```bash
export MCP_SERVER_NAME="aichemist-forge"
export MCP_LOG_LEVEL="INFO"
export MCP_TRANSPORT_TYPE="stdio"
export PYTHONPATH="src"
export MAX_FILE_SIZE="20000000"
```

## Development Standards

### Code Quality Requirements
- **Python**: Use `uv` exclusively for dependency management, not pip or conda
- **Formatting**: Ruff formatting required for Python (line-length: 88)
- **Type Safety**: Full type hints required in Python, TypeScript strict mode enabled
- **Security**: No hardcoded secrets - use environment variables only
- **Testing**: pytest for Python, Jest for TypeScript

### Project Structure Conventions
```
ToolRack/
├── Python/                    # Primary Python MCP server
│   ├── src/unified_mcp_server/
│   │   ├── tools/            # Tool implementations by category
│   │   ├── resources/        # Resource providers
│   │   ├── prompts/          # Analysis prompts
│   │   └── server/           # Core server logic
├── TypeScript/               # TypeScript MCP implementations
└── Rust/                     # Experimental Rust server
```

### Tool Development Guidelines
- **Plugin Pattern**: All tools register via internal registry system
- **Categories**: Organize tools by function (database, filesystem, analysis)
- **Security**: Input validation required for all tool operations
- **Error Handling**: Use structured error types with proper logging

## Testing Instructions

### Python Server Testing
```bash
cd ToolRack/Python
# Run all tests
python -m pytest tests/ -v

# Test specific components
python -m pytest tests/test_registry.py -v
python -m pytest tests/test_filesystem_tools.py -v

# Debug server manually
python tests/debug_server.py
```

### TypeScript Server Testing
```bash
cd ToolRack/TypeScript
# Build and test
npm run build
npm test

# Start with debug logging
npm run start -- --debug
```

### Integration Testing
```bash
# Test MCP connection
cd ToolRack/Python
python tests/test_mcp_connection.py

# Verify tool discovery
python tests/test_server.py
```

## Build and Deployment

### Python Build Process
```bash
cd ToolRack/Python
# Install dependencies
uv sync --all-groups

# Validate setup
uv run python -c "import unified_mcp_server; print('Import successful')"

# Start server
uv run unified-mcp-server --stdio
```

### TypeScript Build Process
```bash
cd ToolRack/TypeScript
# Install and build
npm install
npm run build

# Start server
node dist/index.js
```

### MCP Client Configuration
Add to your MCP client config (e.g., `.cursor/mcp.json`):
```json
{
  "mcpServers": {
    "aichemist-forge": {
      "command": "uv",
      "args": ["run", "unified-mcp-server"],
      "cwd": "./ToolRack/Python",
      "env": {
        "MCP_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

## Architecture Guidelines

### Server Implementation Patterns
- **Single Server Per Runtime**: One unified server per language, not multiple small servers
- **Tool Registration**: Use plugin-style dynamic tool loading
- **Transport**: STDIO-based communication (preferred for local development)
- **Configuration**: Environment-driven with validation

### Security Requirements
- **Path Validation**: Secure path handling in filesystem tools
- **Input Sanitization**: Validate all tool inputs before processing
- **Principle of Least Privilege**: Minimal required permissions
- **Secrets Management**: Environment variables only, never commit secrets

### Performance Considerations
- **Fast Discovery**: Tool/resource discovery must be <1s for 100+ projects
- **File Size Limits**: Respect MAX_FILE_SIZE (default 20MB)
- **Async Operations**: Use async/await for I/O operations
- **Resource Cleanup**: Proper cleanup of file handles and connections

## Common Development Tasks

### Adding a New Tool
1. Create tool file in appropriate category: `ToolRack/Python/src/unified_mcp_server/tools/{category}/`
2. Implement tool class with proper type hints
3. Register tool in server initialization
4. Add tests in `tests/`
5. Update documentation

### Debugging MCP Communication
```bash
# Enable debug logging
export MCP_LOG_LEVEL="DEBUG"

# Test with MCP inspector
npx @modelcontextprotocol/inspector uv run unified-mcp-server

# Check server logs (stderr)
uv run unified-mcp-server 2> debug.log
```

### Working with Cursor Integration
- **Database Tools**: Access Cursor IDE state and project data
- **Resource Discovery**: Use `cursor://projects` resource for project listing
- **Analysis Prompts**: Leverage built-in analysis prompts for code exploration

## Troubleshooting

### Common Issues
- **Tool Not Discovered**: Ensure proper tool registration and capabilities declaration
- **Import Errors**: Check PYTHONPATH is set to "src"
- **UV Command Not Found**: Install uv package manager first
- **Permission Errors**: Verify filesystem tool permissions

### Debug Commands
```bash
# Verify server startup
cd ToolRack/Python
python tests/debug_server.py

# Check tool registration
python -c "from unified_mcp_server.server.registry import ToolRegistry; print(ToolRegistry.list_tools())"

# Test resource discovery
python -c "from unified_mcp_server.resources.cursor import CursorProjectResource; print('Resource OK')"
```

## Project Status and Roadmap

**Current Phase**: Phase 4 - Filesystem Tools Implementation (85% Complete)

- **Phase 1**: ✅ Infrastructure Setup (Complete)
- **Phase 2**: ✅ Tool Organization System (Complete)
- **Phase 3**: ✅ Cursor Database Tools (Complete)
- **Phase 4**: 🚧 Filesystem Tools (In Progress)
- **Phase 5**: 📋 Advanced Features (Planned)

### Known Limitations
- Rust implementation is experimental
- Filesystem tools incomplete in Python server
- Windows-specific batch scripts limit cross-platform support
- TypeScript implementation lacks comprehensive documentation

## Contributing Guidelines

### Before Making Changes
1. Read architecture plans in `Plans/` directory
2. Understand current phase status and priorities
3. Check existing tests and ensure they pass
4. Review security and coding standards

### Code Review Checklist
- [ ] Uses `uv` for Python dependency management
- [ ] Includes proper type hints
- [ ] Has corresponding tests
- [ ] Follows security best practices
- [ ] Updates relevant documentation
- [ ] No hardcoded secrets or paths

### Pull Request Format
- **Title**: `[Component] Brief description`
- **Description**: Explain changes, testing performed, and any breaking changes
- **Testing**: Include test results and validation steps
- **Documentation**: Update relevant docs and architecture plans

---

*This file serves as the primary guide for AI coding agents working on the AiChemistForge project. It should be updated as the project evolves and new patterns emerge.*