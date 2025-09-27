# Web-UI Project Context

## Project Overview
- **Name**: Browser-use Web UI
- **Description**: Gradio-based web interface for browser automation AI agents
- **Tech Stack**: Python 3.13, Gradio, browser-use, uv package manager
- **Main Entry**: `webui.py`

## Current Status
- ✅ Basic project structure exists
- ✅ Dependencies managed via uv in `pyproject.toml`
- 🔄 **ACTIVE TASK**: Adding Chroma database integration for data storage in `/data` directory

## Project Structure
```
web-ui/
├── data/                    # Target for Chroma database storage
├── src/web_ui/
│   ├── databse/             # Database layer (note: typo in directory name)
│   ├── agent/               # Agent logic
│   ├── browser/             # Browser automation
│   ├── controller/          # Controllers
│   ├── utils/               # Utilities
│   └── webui/               # Gradio interface
├── plans/                   # Project plans
└── webui.py                # Main entry point
```

## Notes
- Directory `src/web_ui/databse/` appears to be a typo for "database"
- Empty `/data` directory ready for database storage
- No existing database integration found