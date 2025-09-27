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

## Current Status - SUCCESSFUL STARTUP! 🎉
- ✅ **FIXED**: IBM Watson import issue - conditional imports implemented
- ✅ **FIXED**: Orchestrator pattern implemented correctly in webui.py → main.py
- ✅ **FIXED**: Relative import issues resolved with improved import strategy
- ✅ **FIXED**: Unicode encoding issues - all emoji characters replaced with plain text
- ✅ **NEW**: MCP configuration auto-loading from data/mcp.json implemented
- ✅ **WORKING**: Web UI successfully starting on configured ports
- ✅ **WORKING**: Database initialization and ChromaDB connections
- ✅ **WORKING**: Document pipeline and MCP service integration
- ✅ **CONFIRMED**: Application runs without startup errors or encoding issues

## Entry Points & Architecture ✅ COMPLETE

### Primary Entry Point ✅ WORKING
- **File**: `webui.py` (root level)
- **Current State**: ✅ Properly routes to main.py orchestrator (22 lines)
- **Usage**: `python webui.py [options]`
- **Responsibility**: Route user commands to orchestrator

### Application Orchestrator ✅ WORKING  
- **File**: `src/web_ui/main.py`
- **Role**: Application orchestrator - the "restaurant manager"
- **Current State**: ✅ Handles service initialization, import resolution, UI startup
- **Responsibility**: Initialize services, handle multiple modes, coordinate components
- **Features**:
  - `--headless`: Run services without UI
  - `--init-services`: Initialize background services before UI
  - `--log-level`: Configurable logging (DEBUG, INFO, WARNING, ERROR)
  - `--port`: Custom port configuration
  - `--theme`: UI theme selection

## Recent Fixes Applied - LATEST SESSION
1. **MCP Auto-Loading**: Agent Settings tab now automatically loads `data/mcp.json`
2. **Unicode Fix**: Removed all emoji characters from log messages to prevent Windows encoding errors
3. **Enhanced MCP UI**: Added MCP section header and file path display
4. **Default Configuration**: MCP textbox now shows loaded configuration by default
5. **File Integration**: MCP file component pre-populated with default file path

## MCP Configuration Features ✅ NEW
- **Auto-Loading**: Automatically loads `data/mcp.json` on startup
- **File Display**: Shows current MCP file path in UI
- **Content Preview**: MCP configuration visible in textbox by default
- **File Upload**: Still supports manual file upload for different configurations
- **Database Sync**: Automatically syncs file changes to ChromaDB

## Current Status
- ✅ **WORKING**: Orchestrator pattern implemented correctly
- ✅ **WORKING**: All dependency import issues resolved  
- ✅ **WORKING**: ChromaDB integration active with document pipeline
- ✅ **WORKING**: Multiple AI agents (browser-use, deep research, database agents)
- ✅ **WORKING**: MCP server infrastructure with unified Python server
- ✅ **WORKING**: UI startup and Gradio server initialization
- ✅ **WORKING**: MCP configuration auto-loading and display
- ✅ Dependencies managed via uv in `pyproject.toml`
- ✅ Comprehensive database layer with models, managers, and utilities
- ✅ **COMPLETED**: Data directory reorganization - moved to `./data/` (separate from production code)
- ✅ **COMPLETED**: MCP configuration storage in ChromaDB with persistence

## Project Structure
```
web-ui/
├── webui.py                     # 🚪 Simple entry point ✅ WORKING
├── data/
│   └── mcp.json                 # 📡 MCP server configuration ✅ AUTO-LOADED
├── src/web_ui/
│   ├── main.py                  # 🧠 Application orchestrator ✅ WORKING
│   ├── database/                # 💾 ChromaDB integration layer
│   │   ├── chroma_manager.py    # Main database interface
│   │   ├── document_pipeline.py # Document processing pipeline
│   │   ├── mcp_config_manager.py # MCP configuration storage
│   │   ├── models.py            # Data models
│   │   ├── connection.py        # Database connection management
│   │   └── utils.py             # Database utilities
│   ├── services/                # 🔧 Background services
│   │   └── mcp_service.py       # MCP configuration service ✅ FIXED (no emojis)
│   ├── agent/                   # 🤖 AI Agent systems
│   │   ├── browser_use/         # Browser automation agents
│   │   ├── deep_research/       # Research orchestration agents
│   │   ├── database_agent/      # Database interaction agents
│   │   └── orchestrator/        # Agent coordination
│   ├── browser/                 # 🌐 Browser automation
│   ├── controller/              # 🎮 Application controllers
│   ├── mcp_server/              # 📡 Model Context Protocol servers
│   ├── utils/                   # 🔧 Utilities and helpers
│   │   └── llm_provider.py      # LLM abstraction ✅ FIXED (conditional imports)
│   └── webui/                   # 🖥️ Gradio interface components ✅ WORKING
│       ├── interface.py         # Main UI interface
│       ├── webui_manager.py     # UI manager ✅ FIXED (no emojis)
│       └── components/          # UI components
│           ├── agent_settings_tab.py # ✅ ENHANCED (MCP auto-load)
│           ├── browser_settings_tab.py
│           ├── browser_use_agent_tab.py
│           ├── deep_research_agent_tab.py
│           ├── document_editor_tab.py
│           └── load_save_config_tab.py
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
- **UI Interface**: Gradio-based web interface with theme support
- **Configuration Management**: Settings persistence and MCP configuration storage
- **MCP Auto-Loading**: Automatic loading and display of data/mcp.json configuration

## Development Standards
- **Package Manager**: uv (primary)
- **Formatter**: ruff
- **Type Checker**: ty (Python 3.13)
- **Environment**: Windows 11 Pro with PowerShell
- **Architecture**: Always use orchestrator pattern for complex applications
- **Encoding**: UTF-8 text only in log messages (no Unicode emojis for Windows compatibility)

## Usage Examples (ALL CONFIRMED WORKING)
```bash
# Basic startup
python webui.py

# Custom port and theme
python webui.py --port 8080 --theme Ocean

# Initialize services first
python webui.py --init-services

# Headless mode (services only)
python webui.py --headless

# Debug logging
python webui.py --log-level DEBUG
```

## Tasks Completed ✅ ALL ISSUES RESOLVED
1. ✅ Fixed orchestrator pattern violation in webui.py
2. ✅ Resolved IBM Watson dependency import issues
3. ✅ Fixed relative import issues in webui modules  
4. ✅ Implemented proper import strategy with Python path management
5. ✅ Resolved Windows console Unicode encoding issues
6. ✅ Confirmed successful application startup
7. ✅ Verified database initialization and service coordination
8. ✅ Tested multiple startup configurations
9. ✅ **NEW**: Implemented MCP configuration auto-loading from data/mcp.json
10. ✅ **NEW**: Enhanced Agent Settings tab with MCP section and file display
11. ✅ **NEW**: Fixed all Unicode emoji characters causing Windows encoding errors

## MCP Configuration Display ✅ USER REQUEST COMPLETED
- **File**: `data/mcp.json` automatically loaded and displayed
- **Location**: Agent Settings tab → MCP Server Configuration section
- **Features**: 
  - Shows current MCP file path
  - Displays configuration content in textbox
  - Supports file upload for alternative configurations
  - Auto-syncs changes to ChromaDB database
  - Background monitoring for file changes