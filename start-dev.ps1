#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Development startup script for the Web-UI project.
.DESCRIPTION
    This script starts the React frontend and the Python backend concurrently for a seamless development experience.
    It includes port checking, dependency validation, and consolidated logging.
    Updated to use background jobs for robust process management and graceful shutdown on error.
.PARAMETER LogFile
    The path to the log file where the output of both servers will be written.
.EXAMPLE
    .\start-dev.ps1
#>

param(
    [string]$LogFile = "d:\Coding\web-ui\logs\web-ui-dev.log"
)

$ErrorActionPreference = "Stop"

Write-Host "🚀 Starting Web-UI Development Environment..." -ForegroundColor Green
Write-Host "=================================================" -ForegroundColor Cyan

# --- Pre-flight Checks ---

# 1. Check for project root
if (-not (Test-Path "pyproject.toml") -or -not (Test-Path "frontend/package.json")) {
    Write-Host "❌ Error: Please run this script from the project root directory." -ForegroundColor Red
    exit 1
}

# 2. Check for frontend dependencies
if (-not (Test-Path "frontend/node_modules")) {
    Write-Host "⚠️ Warning: frontend/node_modules not found." -ForegroundColor Yellow
    Write-Host "Please run 'npm install' or 'pnpm install' in the 'frontend' directory first." -ForegroundColor Yellow
    exit 1
}

# 3. Check if required ports are available
function Test-Port {
    param([int]$Port)
    try {
        $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Any, $Port)
        $listener.Start()
        $listener.Stop()
        return $true
    } catch {
        return $false
    }
}

$backendPort = 8000
$frontendPort = 3000

if (-not (Test-Port $backendPort)) {
    Write-Host "❌ Error: Port $backendPort for the backend is already in use." -ForegroundColor Red
    exit 1
}

if (-not (Test-Port $frontendPort)) {
    Write-Host "❌ Error: Port $frontendPort for the frontend is already in use." -ForegroundColor Red
    exit 1
}

Write-Host "✅ Pre-flight checks passed." -ForegroundColor Green

# --- Log File Setup ---
if (-not (Test-Path (Split-Path $LogFile -Parent))) {
    New-Item -ItemType Directory -Path (Split-Path $LogFile -Parent) | Out-Null
}
Set-Content -Path $LogFile -Value $null
Write-Host "📝 Logging combined output to: $LogFile" -ForegroundColor Cyan

# --- Cleanup Function ---
function Cleanup {
    Write-Host "`n🛑 Shutting down servers..." -ForegroundColor Yellow
    $runningJobs = Get-Job | Where-Object { $_.State -eq 'Running' }
    if ($runningJobs) {
        $runningJobs | Stop-Job -PassThru | Remove-Job
        Write-Host "✅ All background jobs stopped." -ForegroundColor Green
    } else {
        Write-Host "✅ No running jobs to stop." -ForegroundColor Green
    }

    # Explicitly kill any remaining uvicorn processes
    Get-Process -Name "python" | Where-Object { $_.CommandLine -like "*uvicorn*" } | Stop-Process -Force -ErrorAction SilentlyContinue
    Write-Host "✅ Cleaned up any lingering uvicorn processes." -ForegroundColor Green

    Write-Host "Goodbye!" -ForegroundColor Green
}

# Register cleanup for script exit and Ctrl+C
$null = Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action { Cleanup }

# --- Main Execution ---
try {
    # Start Backend Server as a Job
    Write-Host "Starting Backend server (uv run backend)..."
    $backendJob = Start-Job -ScriptBlock {
        param($projectRoot, $logFilePath)
        $env:WEBUI_LOG_FILE = $logFilePath
        $env:LOG_TO_CONSOLE = "false" # Explicitly force logging to file
        Set-Location -Path $projectRoot
        uv run backend --reload 2>&1
    } -ArgumentList $PWD.Path, $LogFile -Name "Backend"

    # Start Frontend Server as a Job
    Write-Host "Starting Frontend server (npm run dev)..."
    $frontendJob = Start-Job -ScriptBlock {
        param($frontendDir)
        Set-Location -Path $frontendDir
        npm run dev 2>&1
    } -ArgumentList (Join-Path $PWD.Path "frontend") -Name "Frontend"

    Write-Host "✅ Both servers started as background jobs." -ForegroundColor Green
    Write-Host "   - Backend Job ID: $($backendJob.Id)"
    Write-Host "   - Frontend Job ID: $($frontendJob.Id)"

    # Wait for frontend to start and check port
    Write-Host "Waiting for frontend server to start..."
    Start-Sleep -Seconds 5 # Give Vite some time to start
    if (-not (Test-Port $frontendPort)) { # Test-Port returns true if port is available, so -not means it's in use
        Write-Host "✅ Frontend available at: http://localhost:$frontendPort" -ForegroundColor Green
    } else {
        Write-Host "❌ Frontend server did not start on port $frontendPort." -ForegroundColor Red
    }

    Write-Host "Monitoring server logs. Press Ctrl+C to shut down."

    # Continuously pipe job output to the log file
    while ($backendJob.State -eq 'Running' -and $frontendJob.State -eq 'Running') {
        Receive-Job -Job $backendJob | Out-File -FilePath $LogFile -Append
        Receive-Job -Job $frontendJob | Out-File -FilePath $LogFile -Append
        Start-Sleep -Seconds 2
    }

    # Determine which job failed
    if ($backendJob.State -ne 'Running') {
        Write-Host "❌ Backend server has stopped unexpectedly." -ForegroundColor Red
        Receive-Job -Job $backendJob # Display final output
    }
    if ($frontendJob.State -ne 'Running') {
        Write-Host "❌ Frontend server has stopped unexpectedly." -ForegroundColor Red
        Receive-Job -Job $frontendJob # Display final output
    }

} catch {
    Write-Host "`n❌ An unexpected error occurred in the startup script: $($_.Exception.Message)" -ForegroundColor Red
} finally {
    # Cleanup will be triggered by the PowerShell.Exiting event
    Write-Host "Initiating cleanup..."
    Cleanup
}
