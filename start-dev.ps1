#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Development startup script for the Web-UI project.
.DESCRIPTION
    This script starts the React frontend and the Python backend concurrently for a seamless development experience.
    It includes port checking, dependency validation, and consolidated logging.
.PARAMETER LogFile
    The path to the log file where the output of both servers will be written.
.EXAMPLE
    .\start-dev.ps1 -LogFile .\logs\web-ui.log
#>

param(
    [string]$LogFile = "d:\Coding\web-ui\logs\web-ui.log"
)

Write-Host "🚀 Starting Web-UI Development Environment..." -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Cyan

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
Clear-Content $LogFile
Write-Host "📝 Logging output to: $LogFile" -ForegroundColor Cyan

# --- Cleanup Function ---
function Cleanup {
    Write-Host "`n🛑 Shutting down servers..." -ForegroundColor Yellow
    Get-Job | Stop-Job -PassThru | Remove-Job
    Write-Host "✅ Cleanup complete. Goodbye!" -ForegroundColor Green
}

# Register cleanup function for Ctrl+C
$null = Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action { Cleanup }

# --- Main Execution ---
try {
    # Start Python backend
    Write-Host "🐍 Starting Python backend server..." -ForegroundColor Blue
    $backendJob = Start-Job -ScriptBlock {
        param($LogFile)
        Set-Location $using:PWD
        uv run python -m web_ui.main --api-only --reload *>> $LogFile
    } -Name "Backend" -ArgumentList $LogFile

    # Wait a moment for backend to initialize
    Start-Sleep -Seconds 3

    # Start React frontend
    Write-Host "⚛️ Starting React frontend server..." -ForegroundColor Blue
    $frontendJob = Start-Job -ScriptBlock {
        param($LogFile)
        Set-Location $using:PWD/frontend
        npm run dev *>> $LogFile
    } -Name "Frontend" -ArgumentList $LogFile

    # Wait a moment for frontend to initialize
    Start-Sleep -Seconds 5

    Write-Host "`n🎉 Both servers are starting up!" -ForegroundColor Green
    Write-Host "   - Frontend: http://localhost:$frontendPort" -ForegroundColor Cyan
    Write-Host "   - Backend:  http://localhost:$backendPort" -ForegroundColor Cyan
    Write-Host "`n🔔 Press Ctrl+C to stop both servers" -ForegroundColor Yellow
    Write-Host "================================================" -ForegroundColor Cyan

    # --- Job Monitoring ---
    while ($true) {
        $backendJobState = $backendJob.State
        $frontendJobState = $frontendJob.State

        if ($backendJobState -ne 'Running' -or $frontendJobState -ne 'Running') {
            Write-Host "`n🔥 A server has stopped unexpectedly:" -ForegroundColor Red
            $backendColor = if ($backendJobState -eq 'Running') { 'Green' } else { 'Red' }
            $frontendColor = if ($frontendJobState -eq 'Running') { 'Green' } else { 'Red' }
            Write-Host "   - Backend: $backendJobState" -ForegroundColor $backendColor
            Write-Host "   - Frontend: $frontendJobState" -ForegroundColor $frontendColor
            Write-Host "`n📜 Check the log file for details: $LogFile" -ForegroundColor Yellow
            break
        }

        # Display a live heartbeat, logs are in the file
        Write-Host -NoNewline "."
        Start-Sleep -Seconds 2
    }
}
catch {
    Write-Host "`n❌ An unexpected error occurred: $($_.Exception.Message)" -ForegroundColor Red
}
finally {
    Cleanup
}