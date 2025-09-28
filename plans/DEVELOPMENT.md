# Development Setup

This document explains how to start the Web-UI development environment.

## Quick Start

### Option 1: VS Code Build Task (Recommended)
1. Open the project in VS Code
2. Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on Mac)
3. Type "Tasks: Run Build Task" and select it
4. Choose "Start Development Servers"

**OR** use the keyboard shortcut:
- Press `Ctrl+Shift+B` (or `Cmd+Shift+B` on Mac)

### Option 2: Direct Script Execution

#### Windows (PowerShell)
```powershell
.\start-dev.ps1
```

#### Windows (Command Prompt)
```cmd
start-dev.bat
```

#### Linux/macOS
```bash
./start-dev.sh
```

## What Gets Started

The startup scripts will launch:

1. **Python Backend Server** (`webui.py`)
   - Runs on: `http://localhost:8000/`
   - Provides: REST API, WebSocket connections, agent orchestration

2. **React Frontend Server** (`npm run dev`)
   - Runs on: `http://localhost:3001/`
   - Provides: Modern React UI with hot reload

## Available VS Code Tasks

Press `Ctrl+Shift+P` → "Tasks: Run Task" to access:

- **Start Development Servers** - Starts both frontend and backend
- **Start Frontend Only** - React dev server only
- **Start Backend Only** - Python server only
- **Install Frontend Dependencies** - Runs `npm install`
- **Install Backend Dependencies** - Runs `uv sync --all-groups`

## Manual Setup

If you prefer to start servers manually:

### Backend
```bash
# From project root
python webui.py
```

### Frontend
```bash
# From project root
cd frontend
npm run dev
```

## Stopping Servers

### Script-based startup:
- **PowerShell/Bash**: Press `Ctrl+C` in the terminal
- **Batch file**: Close the terminal windows that opened

### VS Code Tasks:
- Click the trash icon in the terminal panel
- Or press `Ctrl+C` in the task terminal

## Troubleshooting

### Port Conflicts
- Frontend will automatically try port 3001 if 3000 is busy
- Backend uses port 8000 (configurable via environment variables)

### Missing Dependencies
Run the dependency installation tasks:
- Frontend: `npm install` in the `frontend/` directory
- Backend: `uv sync --all-groups` in the project root

### Permission Issues (Linux/macOS)
Make the script executable:
```bash
chmod +x start-dev.sh
```

## Environment Configuration

The development environment uses these default URLs:
- **Frontend**: `http://localhost:3001/`
- **Backend API**: `http://localhost:8000/`
- **WebSocket**: `ws://localhost:8000/ws`

These can be configured via environment variables in `frontend/.env.development`.