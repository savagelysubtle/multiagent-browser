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
        }
        catch {
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

    $processesKilled = @()

    foreach ($port in $PortRange) {
        try {
            $connections = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue -WarningAction SilentlyContinue
            if ($connections) {
                foreach ($conn in $connections) {
                    $processId = $conn.OwningProcess
                    try {
                        $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
                        if ($process) {
                            Write-Host "  Killing process on port ${port}: $($process.ProcessName) (PID: $processId)" -ForegroundColor Yellow
                            Stop-Process -Id $processId -Force -ErrorAction Stop
                            $processesKilled += $processId
                        }
                    }
                    catch {
                        Write-Host "  Failed to kill process $processId on port ${port}: $($_.Exception.Message)" -ForegroundColor Red
                    }
                }
            }
        }
        catch {
            Write-Host "  Error checking port ${port}: $($_.Exception.Message)" -ForegroundColor Red
        }
    }

    # Wait for ports to be released
    if ($processesKilled.Count -gt 0) {
        Write-Host "  Waiting for ports to be released..." -ForegroundColor Gray
        Start-Sleep -Seconds 3

        # Verify ports are clear
        $stillInUse = @()
        foreach ($port in $PortRange) {
            $connections = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue -WarningAction SilentlyContinue
            if ($connections) {
                $stillInUse += $port
            }
        }

        if ($stillInUse.Count -gt 0) {
            Write-Host "  ⚠️  Warning: Ports still in use: $($stillInUse -join ', ')" -ForegroundColor Yellow
        }
        else {
            Write-Host "  ✅ All ports cleared successfully" -ForegroundColor Green
        }
    }
    else {
        Write-Host "  ✅ No processes found using ports" -ForegroundColor Green
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

    # Clean up temporary config file
    $tempConfigPath = Join-Path $PWD.Path "frontend/.env.local"
    if (Test-Path $tempConfigPath) {
        Remove-Item $tempConfigPath -Force -ErrorAction SilentlyContinue
        Write-Host "  Removed temporary config file" -ForegroundColor Gray
    }

    # Stop all background jobs
    $runningJobs = Get-Job | Where-Object { $_.State -eq 'Running' }
    if ($runningJobs) {
        Write-Host "  Stopping $($runningJobs.Count) background job(s)..." -ForegroundColor Gray
        $runningJobs | Stop-Job -PassThru | Remove-Job
        Write-Host "  ✅ Background jobs stopped" -ForegroundColor Green
    }

    # Clean up processes on backend ports
    Write-Host "  Cleaning up processes on backend ports..." -ForegroundColor Gray
    foreach ($port in $script:backendPortRange) {
        $connections = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
        if ($connections) {
            foreach ($conn in $connections) {
                try {
                    $process = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue
                    if ($process) {
                        Write-Host "  Killing process on port ${port}: $($process.ProcessName) (PID: $($conn.OwningProcess))" -ForegroundColor Yellow
                        Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
                    }
                }
                catch {}
            }
        }
    }

    # Clean up processes on frontend ports
    Write-Host "  Cleaning up processes on frontend ports..." -ForegroundColor Gray
    foreach ($port in $script:frontendPortRange) {
        $connections = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
        if ($connections) {
            foreach ($conn in $connections) {
                try {
                    $process = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue
                    if ($process) {
                        Write-Host "  Killing process on port ${port}: $($process.ProcessName) (PID: $($conn.OwningProcess))" -ForegroundColor Yellow
                        Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
                    }
                }
                catch {}
            }
        }
    }

    # Clean up any lingering Python/Node processes related to our services
    Write-Host "  Cleaning up lingering processes..." -ForegroundColor Gray
    Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object {
        $_.MainWindowTitle -like "*uvicorn*" -or $_.CommandLine -like "*uvicorn*"
    } | Stop-Process -Force -ErrorAction SilentlyContinue

    Get-Process -Name "node" -ErrorAction SilentlyContinue | Where-Object {
        $_.MainWindowTitle -like "*Electron*" -or $_.CommandLine -like "*electron*"
    } | Stop-Process -Force -ErrorAction SilentlyContinue

    Write-Host "  ✅ Cleanup complete" -ForegroundColor Green
    Write-Host "Goodbye!" -ForegroundColor Green
}

# Register cleanup for script exit and Ctrl+C
$null = Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action { Cleanup }

# --- Main Execution ---
try {
    # Ensure logs directory exists before starting
    if (-not (Test-Path "logs")) {
        Write-Host "Creating logs directory..." -ForegroundColor Gray
        New-Item -ItemType Directory -Path "logs" -Force | Out-Null
    }

    Initialize-Logging $ScriptLogFile

    if ($BackendOnly) {
        Write-StatusMessage -Message "🚀 Starting Web-UI Backend-Only Mode..." -Color Green -Log
        Clear-PortRange -PortRange $script:backendPortRange -ServiceName "Backend"
        $script:backendPort = Find-AvailablePort -PortRange $script:backendPortRange -ServiceName "Backend"
        if (-not $script:backendPort) { exit 1 }

        Write-StatusMessage -Message "✅ Backend will run on port $($script:backendPort). Press Ctrl+C to quit." -Color Cyan -Log
        $env:WEBUI_PORT = $script:backendPort
        $env:LOG_LEVEL = "DEBUG"
        uv run python -m uvicorn web_ui.api.server:app --host 127.0.0.1 --port $script:backendPort --reload --log-level debug
    }
    else {
        Write-StatusMessage -Message "🚀 Starting Web-UI Full-Stack Environment..." -Color Green -Log

        # --- Port Setup ---
        Clear-PortRange -PortRange $script:backendPortRange -ServiceName "Backend"
        Clear-PortRange -PortRange $script:frontendPortRange -ServiceName "Frontend"
        $script:backendPort = Find-AvailablePort -PortRange $script:backendPortRange -ServiceName "Backend"
        $script:frontendPort = Find-AvailablePort -PortRange $script:frontendPortRange -ServiceName "Frontend"
        if (-not $script:backendPort -or -not $script:frontendPort) { exit 1 }

        # --- Start Backend ---
        Write-StatusMessage -Message "Starting Backend server..." -Color Cyan -Log

        # Create backend job log file
        $backendJobLog = "logs\backend_job.log"
        if (-not (Test-Path "logs")) {
            New-Item -ItemType Directory -Path "logs" | Out-Null
        }

        $backendJob = Start-Job -ScriptBlock {
            param($backendPort, $workingDir)

            # Set working directory to project root
            Set-Location -Path $workingDir

            # Load .env file if it exists
            if (Test-Path ".env") {
                Get-Content ".env" | ForEach-Object {
                    if ($_ -match "^([^=]+)=(.*)$") {
                        $key = $matches[1].Trim()
                        $value = $matches[2].Trim()
                        Set-Item -Path "env:$key" -Value $value
                    }
                }
            }

            # Set environment variable
            $env:WEBUI_PORT = $backendPort
            $env:LOG_LEVEL = "DEBUG"

            # Run uvicorn directly (same as backend-only mode) with debug logging
            & uv run python -m uvicorn web_ui.api.server:app --host 127.0.0.1 --port $backendPort --reload --log-level debug
        } -ArgumentList $script:backendPort, $PWD.Path -Name "Backend"

        # --- Wait for Backend with Better Error Handling ---
        Write-Host "Waiting for backend server to start..." -ForegroundColor Cyan
        Write-Host "  Backend port: $($script:backendPort)" -ForegroundColor Gray
        Write-Host "  Working directory: $($PWD.Path)" -ForegroundColor Gray
        Start-Sleep -Seconds 2  # Give the job a moment to start

        $backendStarted = $false
        foreach ($i in 1..60) {
            # Check if job failed or stopped
            if ($backendJob.State -eq 'Failed' -or $backendJob.State -eq 'Stopped') {
                Write-StatusMessage -Message "❌ Backend job failed! State: $($backendJob.State)" -Color Red -Log
                Write-Host "`nBackend Job Output:" -ForegroundColor Yellow
                $jobOutput = Receive-Job -Job $backendJob -ErrorAction SilentlyContinue
                if ($jobOutput) {
                    $jobOutput | Write-Host
                    # Save to log file for reference
                    $jobOutput | Out-File -FilePath $backendJobLog -Append
                }
                else {
                    Write-Host "(No output from job)" -ForegroundColor Gray
                }
                Write-StatusMessage -Message "Check logs/api.log for details." -Color Red -Log
                Cleanup; exit 1
            }

            # Check job output for startup indicators
            $allOutput = Receive-Job -Job $backendJob -Keep -ErrorAction SilentlyContinue
            if ($allOutput) {
                $outputText = $allOutput -join "`n"
                # Look for any of these startup indicators
                if ($outputText -match "Uvicorn running on" -or
                    $outputText -match "Application startup complete" -or
                    $outputText -match "Started server process" -or
                    $outputText -match "Auth service initialized and admin user checked") {
                    $backendStarted = $true
                    Write-StatusMessage -Message "✅ Backend server initialized (detected from output)" -Color Green -Log
                    break
                }
            }

            # Try health check on multiple possible endpoints
            $healthEndpoints = @("/health", "/api/health", "/", "/docs")
            foreach ($endpoint in $healthEndpoints) {
                try {
                    $healthUrl = "http://localhost:$($script:backendPort)$endpoint"
                    $res = Invoke-WebRequest -Uri $healthUrl -TimeoutSec 1 -ErrorAction SilentlyContinue
                    if ($res.StatusCode -eq 200) {
                        $backendStarted = $true
                        Write-StatusMessage -Message "✅ Backend server responded at $healthUrl" -Color Green -Log
                        break
                    }
                }
                catch {
                    # Continue to next endpoint
                }
            }

            if ($backendStarted) {
                break
            }

            # Health checks failed, but job might still be starting
            if ($i % 5 -eq 0) {
                Write-Host "  Still waiting... (attempt $i/60)" -ForegroundColor Gray
                # Check for any job output
                $currentOutput = Receive-Job -Job $backendJob -Keep -ErrorAction SilentlyContinue
                if ($currentOutput) {
                    Write-Host "  Backend output:" -ForegroundColor Gray
                    $currentOutput | ForEach-Object { Write-Host "    $_" -ForegroundColor DarkGray }

                    # Check if server has initialized
                    $outputText = $currentOutput -join "`n"
                    if ($outputText -match "Auth service initialized and admin user checked") {
                        Write-Host "  Backend initialization detected, giving it a moment to fully start..." -ForegroundColor Yellow
                        Start-Sleep -Seconds 2
                        $backendStarted = $true
                        Write-StatusMessage -Message "✅ Backend server running (initialization confirmed)" -Color Green -Log
                        break
                    }
                }
            }
            Start-Sleep -Milliseconds 500  # Check more frequently
        }

        if (-not $backendStarted) {
            Write-StatusMessage -Message "❌ Backend failed to respond within 60 seconds." -Color Red -Log
            Write-Host "`nBackend Job State: $($backendJob.State)" -ForegroundColor Yellow
            Write-Host "`nBackend Job Output:" -ForegroundColor Yellow
            $jobOutput = Receive-Job -Job $backendJob -ErrorAction SilentlyContinue
            if ($jobOutput) {
                $jobOutput | Write-Host
                $jobOutput | Out-File -FilePath $backendJobLog -Append
            }
            else {
                Write-Host "(No output from job yet)" -ForegroundColor Gray
            }
            Write-StatusMessage -Message "Check logs/api.log for details." -Color Red -Log
            Cleanup; exit 1
        }
        Write-StatusMessage -Message "✅ Backend server started successfully on port $($script:backendPort)" -Color Green -Log
        Write-Host "  Frontend should connect to: http://localhost:$($script:backendPort)" -ForegroundColor Yellow

        # --- Start Frontend ---
        Write-StatusMessage -Message "Starting Electron Desktop App..." -Color Cyan -Log
        Write-Host "  Frontend will connect to backend at port: $($script:backendPort)" -ForegroundColor Gray

        # Create a temporary config file with the actual backend port
        $tempConfig = @{
            VITE_API_URL      = "http://localhost:$($script:backendPort)"
            VITE_WS_URL       = "ws://localhost:$($script:backendPort)/ws"
            REACT_APP_API_URL = "http://localhost:$($script:backendPort)"
            REACT_APP_WS_URL  = "ws://localhost:$($script:backendPort)/ws"
        }
        $tempConfigPath = Join-Path $PWD.Path "frontend/.env.local"

        # Write the config file
        $configContent = ""
        foreach ($key in $tempConfig.Keys) {
            $configContent += "$key=$($tempConfig[$key])`n"
        }
        [System.IO.File]::WriteAllText($tempConfigPath, $configContent)

        Write-Host "  Created temporary config: $tempConfigPath" -ForegroundColor Gray
        Write-Host "  Config contents:" -ForegroundColor Gray
        foreach ($key in $tempConfig.Keys) {
            Write-Host "    $key=$($tempConfig[$key])" -ForegroundColor DarkGray
        }

        # Wait a moment for file to be written and ensure it's readable
        Start-Sleep -Seconds 1

        # Verify the file was created
        if (Test-Path $tempConfigPath) {
            Write-Host "  ✅ Config file verified at: $tempConfigPath" -ForegroundColor Green
        }
        else {
            Write-Host "  ❌ ERROR: Config file not found at: $tempConfigPath" -ForegroundColor Red
        }

        $frontendJob = Start-Job -ScriptBlock {
            param($frontendDir, $backendPort)
            Set-Location -Path $frontendDir

            # Set environment variables for the frontend - both VITE and REACT_APP prefixes
            $env:VITE_API_URL = "http://localhost:$backendPort"
            $env:VITE_WS_URL = "ws://localhost:$backendPort/ws"
            $env:REACT_APP_API_URL = "http://localhost:$backendPort"
            $env:REACT_APP_WS_URL = "ws://localhost:$backendPort/ws"

            Write-Output "Frontend environment variables set:"
            Write-Output "  VITE_API_URL=$env:VITE_API_URL"
            Write-Output "  REACT_APP_API_URL=$env:REACT_APP_API_URL"

            # Check if .env.local exists
            if (Test-Path ".env.local") {
                Write-Output "Found .env.local file with contents:"
                Get-Content ".env.local" | ForEach-Object { Write-Output "  $_" }
            }

            npm run start
        } -ArgumentList (Join-Path $PWD.Path "frontend"), $script:backendPort -Name "ElectronApp"

        Write-StatusMessage -Message "✅ Development environment ready. See separate log files for details." -Color Green -Log

        # Show which log files to monitor
        Write-Host "`n📋 Log files to monitor for debugging:" -ForegroundColor Cyan
        Write-Host "  - logs/auth.log      (authentication issues)" -ForegroundColor Gray
        Write-Host "  - logs/api.log       (general API requests)" -ForegroundColor Gray
        Write-Host "  - logs/database.log  (database operations)" -ForegroundColor Gray
        Write-Host "  - logs/backend_default.log (other backend logs)" -ForegroundColor Gray
        Write-Host "  - logs/dev_script.log (this script's output)" -ForegroundColor Gray

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
}
catch {
    Write-StatusMessage -Message "❌ An unexpected error occurred in the script: $($_.Exception.Message)" -Color Red -Log
    Add-Content -Path $ScriptLogFile -Value "ERROR: $($_.Exception.Message)`n$($_.ScriptStackTrace)"
    Cleanup
    exit 1
}
