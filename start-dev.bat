@echo off
REM Development startup script for Web-UI project
REM Starts both the React frontend (npm run dev) and Python backend (webui.py) concurrently

echo 🚀 Starting Web-UI Development Environment...
echo ================================================

REM Check if we're in the correct directory
if not exist "webui.py" (
    echo ❌ Error: webui.py not found. Please run this script from the project root.
    pause
    exit /b 1
)

if not exist "frontend\package.json" (
    echo ❌ Error: frontend\package.json not found. Please ensure frontend is set up.
    pause
    exit /b 1
)

echo 🐍 Starting Python backend server...
start "Backend Server" cmd /k "python webui.py"

REM Wait a moment for backend to initialize
timeout /t 3 /nobreak >nul

echo ⚛️  Starting React frontend server...
start "Frontend Server" cmd /k "cd frontend && npm run dev"

echo.
echo ✅ Both servers are starting up!
echo 📱 Frontend: http://localhost:3001/
echo 🔧 Backend:  http://localhost:8000/
echo.
echo 💡 Close the terminal windows to stop the servers
echo ================================================

pause