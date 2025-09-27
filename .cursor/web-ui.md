# Web-UI Project Context

## Project Overview
- **Name**: Browser-use Web UI - Unified AI Research Platform
- **Description**: Gradio-based web interface for browser automation AI agents with orchestrator pattern
- **Tech Stack**: Python 3.13, Gradio, browser-use, ChromaDB, LangChain, uv package manager
- **Architecture**: Orchestrator pattern with simple entry point + comprehensive orchestrator

## Steve's Architectural Preferences
- ✅ **ALWAYS prefers main.py orchestrator pattern** for complex applications
- ✅ **Separation of concerns**: Simple entry point + sophisticated orchestrator
- ✅ **Multiple operational modes**: Web UI, headless, debug, service initialization
- ✅ **Comprehensive logging**: Both console and file output with configurable levels
- ✅ **Service coordination**: Database, AI agents, MCP servers, background tasks

## Entry Points & Architecture

### Primary Entry Point
- **File**: `webui.py` (root level)
- **Role**: Simple command interface - the "front door"
- **Usage**: `python webui.py [options]`
- **Responsibility**: Route user commands to orchestrator

### Application Orchestrator
- **File**: `src/web_ui/main.py`
- **Role**: Application orchestrator - the "restaurant manager"
- **Responsibility**: Initialize services, handle multiple modes, coordinate components
- **Features**:
  - `--headless`: Run services without UI
  - `--init-services`: Initialize background services before UI
  - `--log-level`: Configurable logging (DEBUG, INFO, WARNING, ERROR)

## Current Status
- ✅ Orchestrator pattern implemented
- ✅ ChromaDB integration active with document pipeline
- ✅ Multiple AI agents (browser-use, deep research, database agents)
- ✅ MCP server infrastructure with unified Python server
- ✅ Dependencies managed via uv in `pyproject.toml`
- ✅ Comprehensive database layer with models, managers, and utilities
- ✅ **COMPLETED**: Data directory reorganization - moved to `./data/` (separate from production code)
- ✅ **COMPLETED**: MCP configuration storage in ChromaDB with persistence

## Project Structure
```
web-ui/
├── webui.py                     # 🚪 Simple entry point
├── data/                        # 💾 Database and persistent storage
│   └── chroma_db/               # ChromaDB vector database
├── src/web_ui/
│   ├── main.py                  # 🧠 Application orchestrator
│   ├── database/                # 💾 ChromaDB integration layer
│   │   ├── chroma_manager.py    # Main database interface
│   │   ├── document_pipeline.py # Document processing pipeline
│   │   ├── mcp_config_manager.py # MCP configuration storage
│   │   ├── models.py            # Data models
│   │   ├── connection.py        # Database connection management
│   │   └── utils.py             # Database utilities
│   ├── services/                # 🔧 Background services
│   │   └── mcp_service.py       # MCP configuration service
│   ├── agent/                   # 🤖 AI Agent systems
│   │   ├── browser_use/         # Browser automation agents
│   │   ├── deep_research/       # Research orchestration agents
│   │   ├── database_agent/      # Database interaction agents
│   │   └── orchestrator/        # Agent coordination
│   ├── browser/                 # 🌐 Browser automation
│   ├── controller/              # 🎮 Application controllers
│   ├── mcp_server/              # 📡 Model Context Protocol servers
│   ├── utils/                   # 🔧 Utilities and helpers
│   └── webui/                   # 🖥️ Gradio interface components
├── plans/                       # 📋 Project plans and documentation
├── tests/                       # 🧪 Test suite
└── tmp/                         # 🗂️ Temporary files and data
    ├── deep_research/           # Research task outputs
    ├── documents/               # Document processing workspace
    └── webui_settings/          # UI configuration
```

## Key Features Implemented
- **Database Integration**: ChromaDB with full CRUD operations
- **Document Pipeline**: Automated document processing and vectorization
- **Multi-Agent System**: Browser automation, research, and database agents
- **MCP Infrastructure**: Unified Python MCP server with tool organization
- **Orchestrated Startup**: Service initialization and coordination
- **Multiple Operational Modes**: Web UI, headless, and debug modes

## Development Standards
- **Package Manager**: uv (primary)
- **Formatter**: ruff
- **Type Checker**: ty (Python 3.13)
- **Environment**: Windows 11 Pro with PowerShell
- **Architecture**: Always use orchestrator pattern for complex applications