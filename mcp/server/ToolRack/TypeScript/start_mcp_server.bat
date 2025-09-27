@echo off
REM Windows batch file for starting the TypeScript MCP Server
REM This provides better error handling and environment setup

cd /d "%~dp0"

REM Set environment variables
set NODE_ENV=production
set LOG_LEVEL=INFO
set MCP_SERVER_NAME=TypeScript

REM Enable detailed Node.js diagnostics
set NODE_OPTIONS=--trace-warnings

echo =====================================
echo  TypeScript MCP Server Startup
echo =====================================
echo Current Directory: %CD%
echo Node Version:
node --version 2>nul || echo Node.js not found in PATH
echo.

REM Check if dist directory exists
if not exist "dist\index.js" (
    echo [ERROR] Compiled JavaScript not found. Please run 'npm run build' first.
    echo.
    echo To build the project:
    echo   npm run build
    echo.
    pause
    exit /b 1
)

REM Check if node_modules exists
if not exist "node_modules" (
    echo [ERROR] Dependencies not installed. Please run 'npm install' first.
    echo.
    echo To install dependencies:
    echo   npm install
    echo.
    pause
    exit /b 1
)

echo [INFO] All prerequisites checked - OK
echo [INFO] Starting TypeScript MCP Server...
echo [INFO] Listening on STDIO for MCP protocol messages
echo [INFO] Press Ctrl+C to stop the server
echo.

REM Start the server
node dist\index.js

REM Capture exit code
set EXIT_CODE=%ERRORLEVEL%
echo.
echo =====================================
echo [INFO] TypeScript MCP Server stopped with exit code: %EXIT_CODE%
if %EXIT_CODE% neq 0 (
    echo [ERROR] Server exited with an error
    echo [INFO] Check the logs above for error details
)
echo =====================================