#!/bin/bash
# Development startup script for Web-UI project
# Starts both the React frontend (npm run dev) and Python backend (webui.py) concurrently

set -e  # Exit on any error

echo "🚀 Starting Web-UI Development Environment..."
echo "================================================"

# Check if we're in the correct directory
if [ ! -f "webui.py" ]; then
    echo "❌ Error: webui.py not found. Please run this script from the project root."
    exit 1
fi

if [ ! -f "frontend/package.json" ]; then
    echo "❌ Error: frontend/package.json not found. Please ensure frontend is set up."
    exit 1
fi

# Function to cleanup background processes on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down servers..."
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
    fi
    echo "✅ Cleanup complete. Goodbye!"
    exit 0
}

# Register cleanup function for Ctrl+C
trap cleanup SIGINT SIGTERM

# Start Python backend
echo "🐍 Starting Python backend server..."
python webui.py &
BACKEND_PID=$!

# Wait a moment for backend to initialize
sleep 2

# Start React frontend
echo "⚛️  Starting React frontend server..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

# Wait a moment for frontend to initialize
sleep 3

echo ""
echo "✅ Both servers are starting up!"
echo "📱 Frontend: http://localhost:3001/"
echo "🔧 Backend:  http://localhost:8000/"
echo ""
echo "💡 Press Ctrl+C to stop both servers"
echo "================================================"

# Wait for both processes
wait