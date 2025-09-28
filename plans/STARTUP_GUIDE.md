# 🚀 Web-UI Startup Guide

## Quick Start (Recommended)

### Method 1: VS Code Build Task
1. Open project in VS Code
2. Press **`Ctrl+Shift+B`** (Windows/Linux) or **`Cmd+Shift+B`** (Mac)
3. Select "Start Development Servers"
4. Both servers will start automatically!

### Method 2: NPM Script
```bash
npm run dev
```

## 🎯 What You Get

When you start the development environment, you'll have:

| Service | URL | Description |
|---------|-----|-------------|
| **Frontend** | http://localhost:3001/ | React app with hot reload |
| **Backend** | http://localhost:8000/ | Python API server |
| **WebSocket** | ws://localhost:8000/ws | Real-time updates |

## 📋 Available Commands

### Root Directory (npm scripts)
```bash
npm run dev              # Start both servers
npm run dev:frontend     # Frontend only
npm run dev:backend      # Backend only
npm run install:all      # Install all dependencies
npm run build            # Build for production
```

### Platform-Specific Scripts
```bash
# Windows PowerShell
.\start-dev.ps1

# Windows Command Prompt
start-dev.bat

# Linux/macOS
./start-dev.sh
```

### Manual Start
```bash
# Terminal 1: Backend
python webui.py

# Terminal 2: Frontend
cd frontend && npm run dev
```

## 🛠️ VS Code Tasks

Press `Ctrl+Shift+P` → "Tasks: Run Task":

- **Start Development Servers** - Both servers (npm)
- **Start Development Servers (Script)** - Both servers (platform scripts)
- **Start Frontend Only** - React dev server
- **Start Backend Only** - Python server
- **Install Frontend Dependencies** - `npm install`
- **Install Backend Dependencies** - `uv sync --all-groups`

## 🔧 First Time Setup

1. **Install Backend Dependencies**
   ```bash
   uv sync --all-groups
   ```

2. **Install Frontend Dependencies**
   ```bash
   cd frontend && npm install
   ```

3. **Install Root Dependencies** (for npm scripts)
   ```bash
   npm install
   ```

## 🚦 Stopping Servers

- **npm/concurrently**: Press `Ctrl+C`
- **VS Code tasks**: Click trash icon in terminal or `Ctrl+C`
- **Script-based**: Press `Ctrl+C` (PowerShell/Bash) or close windows (Batch)

## 🐛 Troubleshooting

### Port Already in Use
- Frontend auto-switches to 3001 if 3000 is busy
- Backend uses 8000 (configurable via env vars)

### Missing Dependencies
```bash
# Frontend
cd frontend && npm install

# Backend
uv sync --all-groups

# Root (for npm scripts)
npm install
```

### Permission Denied (Linux/macOS)
```bash
chmod +x start-dev.sh
```

### Python Not Found
Ensure Python is in your PATH or activate your virtual environment:
```bash
# If using conda/venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
```

## 🌐 Environment Configuration

Default configuration in `frontend/.env.development`:
```env
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws
```

## 🎉 Success Indicators

You'll know everything is working when you see:
- ✅ Frontend: "Local: http://localhost:3001/"
- ✅ Backend: Server running on port 8000
- ✅ No error messages in either terminal
- ✅ Browser opens to the login page

## 📱 Next Steps

1. Visit http://localhost:3001/
2. Create an account or login
3. Explore the agent dashboard
4. Test the chat, editor, and tasks features

---

**Need help?** Check `DEVELOPMENT.md` for detailed documentation.