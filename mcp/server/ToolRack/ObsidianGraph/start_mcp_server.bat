@echo off
REM Windows batch file for starting the ObsidianGraph MCP Server
REM This provides better error handling and environment setup

cd /d "%~dp0"

REM Set environment variables
set NODE_ENV=production
set LOG_LEVEL=INFO
set MCP_SERVER_NAME=ObsidianGraph

REM Enable detailed Node.js diagnostics
set NODE_OPTIONS=--trace-warnings

echo =====================================
echo  ObsidianGraph MCP Server Startup
echo =====================================
echo Current Directory: %CD%
echo Node Version:
node --version 2>nul || echo Node.js not found in PATH
echo.

REM Check if build directory exists
if not exist "build\main.js" (
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
echo [INFO] Starting ObsidianGraph MCP Server...
echo [INFO] Listening on STDIO for MCP protocol messages
echo [INFO] Press Ctrl+C to stop the server
echo.
echo [NOTE] ObsidianGraph server requires vault paths as arguments
echo [NOTE] This server will be configured to use default vault paths
echo [NOTE] or paths specified in the MCP client configuration
echo.

REM Default vault paths - these can be overridden in MCP client config
REM The server expects vault paths as command line arguments
REM For now, we'll use a placeholder that the MCP client should override
if "%~1"=="" (
    echo [INFO] No vault paths provided, using default configuration
    echo [INFO] Make sure your MCP client configuration includes vault paths
    node build\main.js "%USERPROFILE%\Documents\Obsidian"
) else (
    echo [INFO] Using provided vault paths: %*
    node build\main.js %*
)

REM Capture exit code
set EXIT_CODE=%ERRORLEVEL%
echo.
echo =====================================
echo [INFO] ObsidianGraph MCP Server stopped with exit code: %EXIT_CODE%
if %EXIT_CODE% neq 0 (
    echo [ERROR] Server exited with an error
    echo [INFO] Check the logs above for error details
)
echo =====================================