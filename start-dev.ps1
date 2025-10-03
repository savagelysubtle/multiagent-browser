#!/usr/bin/env pwsh
# To enable script execution, run: Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

<#
.SYNOPSIS
    Development startup script for the Web-UI project.
.DESCRIPTION
    This script starts the React frontend and the Python backend concurrently.
    Backend services log to their own files (e.g., api.log, database.log).
    This script's own output is logged to logs/dev_script.log.
.PARAMETER ScriptLogFile
    The path to the log file for this script's console output.
.PARAMETER BackendOnly
    A switch to run only the backend server for testing purposes.
.EXAMPLE
    .\start-dev.ps1
.EXAMPLE
    .\start-dev.ps1 -BackendOnly
#>

param(
    [string]$ScriptLogFile = "d:\Coding\web-ui\logs\dev_script.log",
    [switch]$BackendOnly
)

# --- Configuration Variables ---
$script:backendPortRange = 8000..8010
$script:frontendPortRange = 3000..3010
$script:backendPort = 8000
$script:frontendPort = 3000

# --- Additional Configuration ---
$ErrorActionPreference = "Stop"
$DebugPreference = "SilentlyContinue"
$VerbosePreference = "SilentlyContinue"
Set-StrictMode -Version Latest

# --- Functions ---
function Write-StatusMessage {
    param(
        [string]$Message,
        [string]$Color = "White",
        [switch]$Log
    )
    Write-Host $Message -ForegroundColor $Color
    if ($Log) {
        Add-Content -Path $ScriptLogFile -Value "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - $Message"
    }
}

# ... (Keep all other helper functions like Test-Dependencies, Test-Port, etc. as they are) ...
function Test-Dependencies {
    Write-Host "Checking dependencies..." -ForegroundColor Cyan
    $nodeVersion = $(node -v)
    if (-not $nodeVersion) {
        Write-Host "❌ Node.js not found. Please install Node.js" -ForegroundColor Red
        return $false
    }
    $pythonVersion = $(python --version 2>&1)
    if (-not $pythonVersion) {
        Write-Host "❌ Python not found. Please install Python" -ForegroundColor Red
        return $false
    }
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        Write-Host "❌ uv not found. Please install uv package manager" -ForegroundColor Red
        return $false
    }
    Write-Host "✅ All dependencies verified" -ForegroundColor Green
    return $true
}

function Test-Port {
    param([int]$Port, [int]$RetryCount = 3, [int]$RetryDelay = 2)
    for ($i = 1; $i -le $RetryCount; $i++) {
        try {
            $connections = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
            if ($connections) {
                if ($i -lt $RetryCount) {
                    Write-Host "Port $Port still in use, retry $i/$RetryCount..." -ForegroundColor Yellow
                    Start-Sleep -Seconds $RetryDelay
                }
                continue
            }
            $tcpListener = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Loopback, $Port)
            $tcpListener.Start()
            $tcpListener.Stop()
            return $true
        } catch {
            if ($i -lt $RetryCount) {
                Start-Sleep -Seconds $RetryDelay
            }
        }
    }
    return $false
}

function Clear-PortRange {
    param([int[]]$PortRange, [string]$ServiceName)
    Write-Host "Clearing ports $($PortRange[0])-$($PortRange[-1]) for $ServiceName..." -ForegroundColor Cyan
    foreach ($port in $PortRange) {
        try {
            $connections = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue -WarningAction SilentlyContinue
            if ($connections) {
                foreach ($conn in $connections) {
                    Write-Host "Found process using port $port, stopping PID: $($conn.OwningProcess)" -ForegroundColor Yellow
                    Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
                }
            }
        } catch {}
    }
}

function Find-AvailablePort {
    param([int[]]$PortRange, [string]$ServiceName)
    foreach ($port in $PortRange) {
        if (Test-Port $port) {
            Write-Host "✅ Found available port $port for $ServiceName" -ForegroundColor Green
            return $port
        }
    }
    Write-Host "❌ No available ports in range $($PortRange[0])-$($PortRange[-1]) for $ServiceName" -ForegroundColor Red
    return $null
}

function Initialize-Logging {
    param([string]$logPath)
    $logsDir = Split-Path -Path $logPath -Parent
    if (-not (Test-Path $logsDir)) {
        New-Item -ItemType Directory -Path $logsDir | Out-Null
    }
    if (-not (Test-Path $logPath)) {
        New-Item -ItemType File -Path $logPath | Out-Null
    }
    Write-Host "✅ Initialized script logging in $logsDir" -ForegroundColor Green
}

# --- Pre-flight Checks ---
if (-not (Test-Path "pyproject.toml") -or -not (Test-Path "frontend/package.json")) {
    Write-StatusMessage "❌ Error: Please run this script from the project root directory." -Color Red
    exit 1
}
if (-not (Test-Path "frontend/node_modules")) {
    Write-StatusMessage "⚠️ Warning: frontend/node_modules not found. Please run 'npm install' in 'frontend' directory." -Color Yellow
    exit 1
}
Write-StatusMessage "✅ Pre-flight checks passed." -Color Green

# --- Cleanup Function ---
function Cleanup {
    Write-Host "`n🛑 Shutting down servers..." -ForegroundColor Yellow
    $runningJobs = Get-Job | Where-Object { $_.State -eq 'Running' }
    if ($runningJobs) {
        $runningJobs | Stop-Job -PassThru | Remove-Job
        Write-Host "✅ All background jobs stopped." -ForegroundColor Green
    }
    Get-Process -Name "python" | Where-Object { $_.CommandLine -like "*uvicorn*" } | Stop-Process -Force -ErrorAction SilentlyContinue
    Write-Host "✅ Cleaned up any lingering uvicorn processes." -ForegroundColor Green
    Write-Host "Goodbye!" -ForegroundColor Green
}

# Register cleanup for script exit and Ctrl+C
$null = Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action { Cleanup }

# --- Main Execution ---
try {
    Initialize-Logging $ScriptLogFile

    if ($BackendOnly) {
        Write-StatusMessage -Message "🚀 Starting Web-UI Backend-Only Mode..." -Color Green -Log
        Clear-PortRange -PortRange $script:backendPortRange -ServiceName "Backend"
        $script:backendPort = Find-AvailablePort -PortRange $script:backendPortRange -ServiceName "Backend"
        if (-not $script:backendPort) { exit 1 }

        Write-StatusMessage -Message "✅ Backend will run on port $($script:backendPort). Press Ctrl+C to quit." -Color Cyan -Log
        $env:WEBUI_PORT = $script:backendPort
        uv run python -m uvicorn web_ui.api.server:app --host 127.0.0.1 --port $script:backendPort --reload
    } else {
        Write-StatusMessage -Message "🚀 Starting Web-UI Full-Stack Environment..." -Color Green -Log
        
        # --- Port Setup ---
        Clear-PortRange -PortRange $script:backendPortRange -ServiceName "Backend"
        Clear-PortRange -PortRange $script:frontendPortRange -ServiceName "Frontend"
        $script:backendPort = Find-AvailablePort -PortRange $script:backendPortRange -ServiceName "Backend"
        $script:frontendPort = Find-AvailablePort -PortRange $script:frontendPortRange -ServiceName "Frontend"
        if (-not $script:backendPort -or -not $script:frontendPort) { exit 1 }

        # --- Start Backend ---
        Write-StatusMessage -Message "Starting Backend server..." -Color Cyan -Log
        $backendJob = Start-Job -ScriptBlock {
            param($backendPort)
            $env:WEBUI_PORT = $backendPort
            uv run python -m uvicorn web_ui.api.server:app --host 127.0.0.1 --port $backendPort --reload
        } -ArgumentList $script:backendPort -Name "Backend"

        # --- Wait for Backend ---
        Write-Host "Waiting for backend server to start..." -ForegroundColor Cyan
        $backendStarted = $false
        foreach ($i in 1..60) {
            if ($backendJob.State -ne 'Running') { break }
            try {
                $res = Invoke-WebRequest -Uri "http://localhost:$($script:backendPort)/health" -TimeoutSec 1 -ErrorAction SilentlyContinue
                if ($res.StatusCode -eq 200) {
                    $backendStarted = $true
                    break
                }
            } catch {}
            Start-Sleep -Seconds 1
        }

        if (-not $backendStarted) {
            Write-StatusMessage -Message "❌ Backend failed to start. Check logs/api.log for details." -Color Red -Log
            Receive-Job -Job $backendJob # Display error output
            Cleanup; exit 1
        }
        Write-StatusMessage -Message "✅ Backend server started successfully." -Color Green -Log

        # --- Start Frontend ---
        Write-StatusMessage -Message "Starting Electron Desktop App..." -Color Cyan -Log
        $frontendJob = Start-Job -ScriptBlock {
            param($frontendDir)
            Set-Location -Path $frontendDir
            npm run start
        } -ArgumentList (Join-Path $PWD.Path "frontend") -Name "ElectronApp"

        Write-StatusMessage -Message "✅ Development environment ready. See separate log files for details." -Color Green -Log
        Write-StatusMessage -Message "`nMonitoring server status. Press Ctrl+C to shut down.`n" -Color Cyan

        # --- Monitoring Loop ---
        while ($backendJob.State -eq 'Running' -and $frontendJob.State -eq 'Running') {
            Start-Sleep -Seconds 5
        }

        # --- Handle unexpected shutdown ---
        if ($backendJob.State -ne 'Running') {
            Write-StatusMessage -Message "❌ Backend server has stopped unexpectedly." -Color Red -Log
        }
        if ($frontendJob.State -ne 'Running') {
            Write-StatusMessage -Message "❌ Frontend server has stopped unexpectedly." -Color Red -Log
        }
        Cleanup
        exit 1
    }
} catch {
    Write-StatusMessage -Message "❌ An unexpected error occurred in the script: $($_.Exception.Message)" -Color Red -Log
    Add-Content -Path $ScriptLogFile -Value "ERROR: $($_.Exception.Message)`n$($_.ScriptStackTrace)"
    Cleanup
    exit 1
}
