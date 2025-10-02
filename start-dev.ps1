#!/usr/bin/env pwsh
# To enable script execution, run: Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

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

# --- Configuration Variables ---
$script:backendPortRange = 8000..8010  # Port range for backend
$script:frontendPortRange = 3000..3010 # Port range for frontend
$script:backendPort = 8000  # Default value, can be overridden by config
$script:frontendPort = 3000 # Default value, can be overridden by config
$script:LogFile = "logs/web-ui-dev.log"
$script:MetricsFile = "logs/metrics.log"
$script:AnalyticsFile = "logs/analytics.log"

# --- Additional Configuration ---
$ErrorActionPreference = "Stop"
# Remove verbose debug output that floods the console
$DebugPreference = "SilentlyContinue"
$VerbosePreference = "SilentlyContinue"
Set-StrictMode -Version Latest

Write-Host "🚀 Starting Web-UI Development Environment..." -ForegroundColor Green
Write-Host "=================================================" -ForegroundColor Cyan

# --- Functions ---
function Write-StatusMessage {
    param(
        [string]$Message,
        [string]$Color = "White",
        [switch]$Log
    )
    Write-Host $Message -ForegroundColor $Color
    if ($Log) {
        Add-Content -Path $LogFile -Value "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - $Message"
    }
}

function Test-Dependencies {
    Write-Host "Checking dependencies..." -ForegroundColor Cyan

    # Check Node.js version
    $nodeVersion = $(node -v)
    if (-not $nodeVersion) {
        Write-Host "❌ Node.js not found. Please install Node.js" -ForegroundColor Red
        return $false
    }

    # Check Python version
    $pythonVersion = $(python --version 2>&1)
    if (-not $pythonVersion) {
        Write-Host "❌ Python not found. Please install Python" -ForegroundColor Red
        return $false
    }

    # Check uv installation
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        Write-Host "❌ uv not found. Please install uv package manager" -ForegroundColor Red
        return $false
    }

    Write-Host "✅ All dependencies verified" -ForegroundColor Green
    return $true
}

# Update port checking function
function Test-Port {
    param(
        [int]$Port,
        [int]$RetryCount = 3,
        [int]$RetryDelay = 2
    )

    for ($i = 1; $i -le $RetryCount; $i++) {
        try {
            # Check if port is in use by looking for existing connections
            $connections = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
            if ($connections) {
                # Port is in use
                if ($i -lt $RetryCount) {
                    Write-Host "Port $Port still in use, retry $i/$RetryCount..." -ForegroundColor Yellow
                    Start-Sleep -Seconds $RetryDelay
                }
                continue
            }

            # Port appears free, try to bind to it to be sure
            $tcpListener = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Loopback, $Port)
            $tcpListener.Start()
            $tcpListener.Stop()
            return $true # Port is available
        } catch {
            # If we can't bind, port might be in use
            if ($i -lt $RetryCount) {
                Start-Sleep -Seconds $RetryDelay
            }
        }
    }
    return $false # Port is likely in use
}

function Clear-Port {
    param(
        [int]$Port,
        [string]$ServiceName
    )

    Write-Host "Checking processes on port ${Port}..." -ForegroundColor Cyan
    try {
        # Suppress debug output from Get-NetTCPConnection
        $connections = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue -WarningAction SilentlyContinue
        if ($connections) {
            foreach ($conn in $connections) {
                Write-Host "Found process using port ${Port}, stopping PID: $($conn.OwningProcess)" -ForegroundColor Yellow
                Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
            }
            Start-Sleep -Seconds 2
            Write-Host "✅ Port ${Port} cleared for ${ServiceName}" -ForegroundColor Green
        } else {
            Write-Host "✅ Port ${Port} is already available" -ForegroundColor Green
        }
    } catch {
        Write-Host "⚠️ Error clearing port ${Port}: $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

function Clear-PortRange {
    param(
        [int[]]$PortRange,
        [string]$ServiceName
    )

    Write-Host "Clearing ports $($PortRange[0])-$($PortRange[-1]) for $ServiceName..." -ForegroundColor Cyan
    $clearedPorts = @()

    foreach ($port in $PortRange) {
        try {
            $connections = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue -WarningAction SilentlyContinue
            if ($connections) {
                foreach ($conn in $connections) {
                    Write-Host "Found process using port $port, stopping PID: $($conn.OwningProcess)" -ForegroundColor Yellow
                    Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
                    $clearedPorts += $port
                }
            }
        } catch {
            # Continue with next port
        }
    }

    if ($clearedPorts.Count -gt 0) {
        Write-Host "✅ Cleared ports: $($clearedPorts -join ', ') for $ServiceName" -ForegroundColor Green
        Start-Sleep -Seconds 2  # Give time for ports to fully release
    } else {
        Write-Host "✅ No processes found using $ServiceName port range" -ForegroundColor Green
    }
}

function Find-AvailablePort {
    param(
        [int[]]$PortRange,
        [string]$ServiceName
    )

    foreach ($port in $PortRange) {
        if (Test-Port $port) {
            Write-Host "✅ Found available port $port for $ServiceName" -ForegroundColor Green
            return $port
        }
    }

    Write-Host "❌ No available ports in range $($PortRange[0])-$($PortRange[-1]) for $ServiceName" -ForegroundColor Red
    return $null
}

function Write-ColoredLog {
    param([string]$Message)

    switch -Regex ($Message) {
        "ERROR|CRITICAL|FAIL" { Write-Host $Message -ForegroundColor Red }
        "WARN|WARNING" { Write-Host $Message -ForegroundColor Yellow }
        "INFO|SUCCESS" { Write-Host $Message -ForegroundColor Green }
        default { Write-Host $Message -ForegroundColor Gray }
    }
}

function Open-Browser {
    param([string]$Url)
    try {
        Start-Process $Url
        Write-Host "✅ Opened $Url in default browser" -ForegroundColor Green
    } catch {
        Write-Host "⚠️ Failed to open browser automatically" -ForegroundColor Yellow
    }
}

function Monitor-ProcessResources {
    param(
        [int]$WarningThresholdMB = 500
    )

    $backendProcess = Get-Process -Name "python" | Where-Object { $_.CommandLine -like "*uvicorn*" }
    $frontendProcess = Get-Process -Name "node" | Where-Object { $_.CommandLine -like "*vite*" }

    if ($backendProcess.WorkingSet64/1MB -gt $WarningThresholdMB) {
        Write-Host "⚠️ Backend memory usage: $([math]::Round($backendProcess.WorkingSet64/1MB,2)) MB" -ForegroundColor Yellow
    }
    if ($frontendProcess.WorkingSet64/1MB -gt $WarningThresholdMB) {
        Write-Host "⚠️ Frontend memory usage: $([math]::Round($frontendProcess.WorkingSet64/1MB,2)) MB" -ForegroundColor Yellow
    }
}

function Show-Spinner {
    param(
        [string]$Message,
        [int]$DelayMilliseconds = 100
    )
    $spinner = "⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"
    $i = 0
    Write-Host "`r$($spinner[$i]) $Message" -NoNewline
    $i = ($i + 1) % $spinner.Length
    Start-Sleep -Milliseconds $DelayMilliseconds
}

function Test-Environment {
    param()
    $requiredEnvVars = @(
        "NODE_ENV",
        "PYTHON_PATH"
    )
    foreach ($var in $requiredEnvVars) {
        if (-not (Get-Item "env:$var" -ErrorAction SilentlyContinue)) {
            Write-Host "⚠️ Warning: Environment variable $var not set" -ForegroundColor Yellow
            return $false
        }
    }
    return $true
}

function Measure-Performance {
    param(
        [string]$Component,
        [datetime]$StartTime
    )
    $duration = (Get-Date) - $StartTime
    $metrics = @{
        Component = $Component
        StartTime = $StartTime
        Duration = $duration
        MemoryUsageMB = (Get-Process -Id $PID).WorkingSet64 / 1MB
    }
    Add-Content -Path "$LogFile.metrics" -Value (ConvertTo-Json $metrics)
    Write-Host "📊 $Component took $($duration.TotalSeconds) seconds" -ForegroundColor Cyan
}

function Test-ServiceHealth {
    param(
        [string]$Url,
        [int]$TimeoutSeconds = 30
    )
    $startTime = Get-Date
    while ((Get-Date) - $startTime -lt [TimeSpan]::FromSeconds($TimeoutSeconds)) {
        try {
            $response = Invoke-WebRequest -Uri $Url -Method HEAD -TimeoutSec 5
            if ($response.StatusCode -eq 200) {
                return $true
            }
        } catch {
            Start-Sleep -Seconds 1
        }
    }
    return $false
}

function Format-LogMessage {
    param(
        [string]$Message,
        [string]$Source
    )

    # Filter out noise from the logs
    if ($Message -match "(watchfiles\.main|chromadb\.telemetry|DEBUG - 1 change detected)") {
        return $null
    }

    $prefix = switch($Source) {
        "Backend" { "🔹" }
        "Frontend" { "🔸" }
        default { "  " }
    }

    return "$prefix [$Source] $Message"
}

function Show-ServerStats {
    param(
        [datetime]$StartTime,
        [int]$LogSize
    )

    $runtime = [math]::Round(((Get-Date) - $StartTime).TotalMinutes, 1)
    $memoryUsage = [math]::Round((Get-Process -Id $PID).WorkingSet64/1MB, 1)

    Write-Host "`n=== Server Stats ===" -ForegroundColor Cyan
    Write-Host "Runtime: $runtime minutes" -ForegroundColor Gray
    Write-Host "Log Size: $([math]::Round($LogSize/1KB, 1)) KB" -ForegroundColor Gray
    Write-Host "Memory Usage: $memoryUsage MB" -ForegroundColor Gray
    Write-Host "==================`n" -ForegroundColor Cyan
}

# --- Initial Port Cleanup ---
function Clear-WebUIPorts {
    param(
        [int[]]$Ports = @(8000, 3000)
    )

    foreach ($port in $Ports) {
        Write-Host "Checking port $port..." -ForegroundColor Cyan
        $connection = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
        if ($connection) {
            Write-Host "Found process using port $port, stopping PID: $($connection.OwningProcess)" -ForegroundColor Yellow
            try {
                Stop-Process -Id $connection.OwningProcess -Force
                Write-Host "✅ Successfully cleared port $port" -ForegroundColor Green
            } catch {
                Write-Host "❌ Failed to stop process on port $port" -ForegroundColor Red
                Write-Host $_.Exception.Message -ForegroundColor Red
            }
            Start-Sleep -Seconds 1
        }
    }
}

# --- Log File Setup ---
function Initialize-Logging {
    param([string]$LogFile)

    # Create logs directory if it doesn't exist
    $logsDir = Join-Path $PWD.Path "logs"
    if (-not (Test-Path $logsDir)) {
        New-Item -ItemType Directory -Path $logsDir | Out-Null
    }

    # Initialize log files
    $logFiles = @(
        (Join-Path $logsDir "web-ui-dev.log"),
        (Join-Path $logsDir "metrics.log"),
        (Join-Path $logsDir "analytics.log")
    )

    foreach ($file in $logFiles) {
        if (-not (Test-Path $file)) {
            New-Item -ItemType File -Path $file | Out-Null
        }
    }

    Write-Host "✅ Initialized logging in $logsDir" -ForegroundColor Green
}

# Update config file paths when importing
function Import-Config {
    param(
        [string]$ConfigPath = "dev-config.json"
    )
    if (Test-Path $ConfigPath) {
        $config = Get-Content $ConfigPath | ConvertFrom-Json

        # Update log file paths to be relative to project root
        if ($config.logFile) {
            $script:LogFile = Join-Path $PWD.Path $config.logFile.TrimStart("./")
        }
        if ($config.metricsFile) {
            $script:MetricsFile = Join-Path $PWD.Path $config.metricsFile.TrimStart("./")
        }
        if ($config.analyticsFile) {
            $script:AnalyticsFile = Join-Path $PWD.Path $config.analyticsFile.TrimStart("./")
        }

        # Set port ranges if specified in config
        if ($config.backendPortRange) {
            $script:backendPortRange = $config.backendPortRange[0]..$config.backendPortRange[1]
        }
        if ($config.frontendPortRange) {
            $script:frontendPortRange = $config.frontendPortRange[0]..$config.frontendPortRange[1]
        }

        # Set specific ports (for backwards compatibility)
        if ($config.backendPort) { $script:backendPort = $config.backendPort }
        if ($config.frontendPort) { $script:frontendPort = $config.frontendPort }

        Write-Host "✅ Loaded configuration from $ConfigPath" -ForegroundColor Green
    }
}

function Track-Usage {
    param(
        [string]$Event,
        [hashtable]$Properties
    )
    $analytics = @{
        Timestamp = Get-Date -Format "o"
        Event = $Event
        Properties = $Properties
    }
    Add-Content -Path "$LogFile.analytics" -Value (ConvertTo-Json $analytics)
}

# Add this function before the main execution block
function Register-KeyboardShortcuts {
    # Create a synchronized hashtable to share state between jobs
    $script:keyboardState = [hashtable]::Synchronized(@{
        LastKeyPress = $null
        ShowHelp = $false
    })

    $job = Start-Job -ScriptBlock {
        param($state)
        while ($true) {
            if ([Console]::KeyAvailable) {
                $key = [Console]::ReadKey($true)
                $state.LastKeyPress = $key

                switch ($key.KeyChar) {
                    'h' { $state.ShowHelp = -not $state.ShowHelp }
                }
            }
            Start-Sleep -Milliseconds 100
        }
    } -ArgumentList $keyboardState

    return $job
}

function Show-KeyboardHelp {
    Write-Host "`nKeyboard Shortcuts:" -ForegroundColor Cyan
    Write-Host "  h - Toggle this help menu" -ForegroundColor Gray
    Write-Host "  c - Clear console" -ForegroundColor Gray
    Write-Host "  s - Show current stats" -ForegroundColor Gray
    Write-Host "  r - Restart failed services" -ForegroundColor Gray
    Write-Host "  q - Quit" -ForegroundColor Gray
    Write-Host ""
}

# --- Pre-flight Checks ---

# 1. Check for project root
if (-not (Test-Path "pyproject.toml") -or -not (Test-Path "frontend/package.json")) {
    Write-StatusMessage "❌ Error: Please run this script from the project root directory." -Color Red
    exit 1
}

# 2. Check for frontend dependencies
if (-not (Test-Path "frontend/node_modules")) {
    Write-StatusMessage "⚠️ Warning: frontend/node_modules not found." -Color Yellow
    Write-StatusMessage "Please run 'npm install' or 'pnpm install' in the 'frontend' directory first." -Color Yellow
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
    Write-Host "🚀 Starting Web-UI Development Environment..." -ForegroundColor Green
    Write-Host "=================================================" -ForegroundColor Cyan

    # Clear ports first, then check if they're available
    Clear-PortRange -PortRange $script:backendPortRange -ServiceName "Backend"
    Clear-PortRange -PortRange $script:frontendPortRange -ServiceName "Frontend"

    # Find available ports
    $script:backendPort = Find-AvailablePort -PortRange $script:backendPortRange -ServiceName "Backend"
    if (-not $script:backendPort) {
        Write-Host "❌ No available ports for backend" -ForegroundColor Red
        exit 1
    }

    $script:frontendPort = Find-AvailablePort -PortRange $script:frontendPortRange -ServiceName "Frontend"
    if (-not $script:frontendPort) {
        Write-Host "❌ No available ports for frontend" -ForegroundColor Red
        exit 1
    }

    Import-Config
    Initialize-Logging $LogFile

    Track-Usage -Event "ScriptStart" -Properties @{
        Version = "1.0"
        LogFile = $LogFile
        MetricsFile = $MetricsFile
        AnalyticsFile = $AnalyticsFile
    }
    $startTime = Get-Date

    Test-Environment

    Write-StatusMessage "Starting backend server..." -Color Cyan
    Write-StatusMessage "Starting Backend server (uv run backend)..." -Color Cyan

    # Update the backend job to use the dynamically assigned port
    $backendJob = Start-Job -ScriptBlock {
        param($projectRoot, $logFilePath, $backendPort)
        try {
            $env:WEBUI_LOG_FILE = $logFilePath
            $env:LOG_TO_CONSOLE = "false"
            $env:WEBUI_PORT = $backendPort
            Set-Location -Path $projectRoot
            # Force uvicorn to use the specific port
            uv run python -m uvicorn web_ui.api.server:app --host 127.0.0.1 --port $backendPort --reload 2>&1
        } catch {
            Write-Error "Backend startup failed: $($_.Exception.Message)"
            throw
        }
    } -ArgumentList $PWD.Path, $LogFile, $script:backendPort -Name "Backend"

    # Wait for backend with improved detection
    Write-Host "Waiting for backend server to start..." -ForegroundColor Cyan
    $backendStartTime = Get-Date
    $timeout = 60 # Increased timeout to 60 seconds
    $backendStarted = $false
    $dotCount = 0

    # Update the backend startup detection with better error handling
    while ((Get-Date) - $backendStartTime -lt [TimeSpan]::FromSeconds($timeout)) {
        Start-Sleep -Seconds 1
        $dotCount++

        # Show progress dots every 5 seconds
        if ($dotCount % 5 -eq 0) {
            Write-Host "." -NoNewline -ForegroundColor Yellow
        }

        # Check if job failed or completed unexpectedly
        if ($backendJob.State -eq 'Failed') {
            Write-Host "`n❌ Backend startup failed" -ForegroundColor Red
            $jobOutput = Receive-Job -Job $backendJob
            Write-Host "Backend Error Output:" -ForegroundColor Red
            Write-Host $jobOutput
            Cleanup
            exit 1
        }

        if ($backendJob.State -eq 'Completed') {
            Write-Host "`n❌ Backend process completed unexpectedly" -ForegroundColor Red
            $jobOutput = Receive-Job -Job $backendJob
            Write-Host "Backend Output:" -ForegroundColor Yellow
            Write-Host $jobOutput
            Write-Host "`nThis usually indicates a startup error or missing dependencies." -ForegroundColor Yellow
            Cleanup
            exit 1
        }

        # Check multiple ways if backend is running
        try {
            # Method 1: Check TCP connection
            $tcpConnection = Get-NetTCPConnection -LocalPort $script:backendPort -ErrorAction SilentlyContinue
            if ($tcpConnection) {
                Write-Host "`n✅ Backend detected on port $script:backendPort" -ForegroundColor Green
                $backendStarted = $true
                break
            }

            # Method 2: Try HTTP request to health endpoint
            try {
                $response = Invoke-WebRequest -Uri "http://localhost:$script:backendPort/health" -TimeoutSec 2 -ErrorAction SilentlyContinue
                if ($response.StatusCode -eq 200) {
                    Write-Host "`n✅ Backend health check passed" -ForegroundColor Green
                    $backendStarted = $true
                    break
                }
            } catch {
                # Health endpoint might not exist, continue with other checks
            }

            # Method 3: Try basic connection test
            try {
                $response = Invoke-WebRequest -Uri "http://localhost:$script:backendPort/" -TimeoutSec 2 -ErrorAction SilentlyContinue
                if ($response.StatusCode -eq 200 -or $response.StatusCode -eq 404) {
                    Write-Host "`n✅ Backend responding on port $script:backendPort" -ForegroundColor Green
                    $backendStarted = $true
                    break
                }
            } catch {
                # Continue waiting
            }

        } catch {
            # Continue waiting
        }

        # Check log output for startup completion
        $jobOutput = Receive-Job -Job $backendJob
        if ($jobOutput) {
            # Write output to log file immediately
            Add-Content -Path $LogFile -Value $jobOutput

            # Check for successful startup messages
            if ($jobOutput -match "Application startup complete|Uvicorn running on") {
                Write-Host "`n✅ Backend startup detected in logs" -ForegroundColor Green
                Start-Sleep -Seconds 2 # Give it a moment to fully initialize
                $backendStarted = $true
                break
            }

            # Check for common error patterns
            if ($jobOutput -match "ModuleNotFoundError|ImportError|FileNotFoundError|Permission denied") {
                Write-Host "`n❌ Backend startup error detected in logs" -ForegroundColor Red
                Write-Host "Error details:" -ForegroundColor Yellow
                $jobOutput | Select-Object -Last 5 | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }
                Cleanup
                exit 1
            }
        }
    }

    if (-not $backendStarted) {
        Write-Host "`n❌ Backend failed to start within $timeout seconds" -ForegroundColor Red
        Write-Host "Debug information:" -ForegroundColor Yellow
        Write-Host "Backend job state: $($backendJob.State)" -ForegroundColor Yellow

        # Show recent job output
        $jobOutput = Receive-Job -Job $backendJob
        if ($jobOutput) {
            Write-Host "Recent backend output:" -ForegroundColor Yellow
            $jobOutput | Select-Object -Last 10 | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }
        }

        # Check if anything is actually running on the port
        $tcpConnection = Get-NetTCPConnection -LocalPort $script:backendPort -ErrorAction SilentlyContinue
        if ($tcpConnection) {
            Write-Host "⚠️ Something is running on port $script:backendPort but not responding properly" -ForegroundColor Yellow
        }

        Cleanup
        exit 1
    }

    # Continue with frontend startup...
    Write-StatusMessage "Starting Frontend server (npm run dev)..." -Color Cyan

    # Update frontend job to use unique log file to prevent conflicts
    $frontendLogFile = Join-Path (Split-Path $LogFile -Parent) "frontend.log"
    $frontendJob = Start-Job -ScriptBlock {
        param($frontendDir, $logFilePath, $frontendPort)
        Set-Location -Path $frontendDir
        # Force Vite to use the specific port
        npm run dev -- --port $frontendPort --host 0.0.0.0 2>&1 | Tee-Object -FilePath $logFilePath -Append
    } -ArgumentList (Join-Path $PWD.Path "frontend"), $frontendLogFile, $script:frontendPort -Name "Frontend"

    # Wait for frontend with similar improved detection
    Write-Host "Waiting for frontend server to start..." -ForegroundColor Cyan
    $frontendStartTime = Get-Date
    $frontendTimeout = 30
    $frontendStarted = $false

    while ((Get-Date) - $frontendStartTime -lt [TimeSpan]::FromSeconds($frontendTimeout)) {
        Start-Sleep -Seconds 1

        # Check if frontend job failed
        if ($frontendJob.State -eq 'Failed' -or $frontendJob.State -eq 'Completed') {
            Write-Host "❌ Frontend process failed or completed unexpectedly" -ForegroundColor Red
            $frontendOutput = Receive-Job -Job $frontendJob
            Write-Host "Frontend Output:" -ForegroundColor Yellow
            Write-Host $frontendOutput
            break
        }

        # Check if frontend is running via HTTP
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:$script:frontendPort" -TimeoutSec 2 -ErrorAction SilentlyContinue
            if ($response.StatusCode -eq 200) {
                Write-Host "✅ Frontend available at: http://localhost:$script:frontendPort" -ForegroundColor Green
                $frontendStarted = $true
                break
            }
        } catch {
            # Continue waiting
        }

        # Check job output for Vite ready messages (multiple patterns)
        $frontendOutput = Receive-Job -Job $frontendJob
        if ($frontendOutput) {
            # Write output to log file immediately
            Add-Content -Path $LogFile -Value $frontendOutput

            # Check for various Vite startup patterns
            if ($frontendOutput -match "Local:.*localhost:$script:frontendPort|ready in.*ms|VITE.*ready") {
                Write-Host "✅ Frontend startup detected in logs" -ForegroundColor Green
                # Give Vite a moment to fully initialize
                Start-Sleep -Seconds 2

                # Double-check with HTTP request
                try {
                    $response = Invoke-WebRequest -Uri "http://localhost:$script:frontendPort" -TimeoutSec 3 -ErrorAction SilentlyContinue
                    if ($response.StatusCode -eq 200) {
                        Write-Host "✅ Frontend confirmed available at: http://localhost:$script:frontendPort" -ForegroundColor Green
                        $frontendStarted = $true
                        break
                    }
                } catch {
                    Write-Host "⚠️ Frontend detected in logs but not responding to HTTP requests yet, continuing to wait..." -ForegroundColor Yellow
                }
            }
        }
    }

    if ($frontendStarted) {
        Write-StatusMessage "✅ Development environment ready" -Color Green

        # Open browser automatically
        Open-Browser "http://localhost:$script:frontendPort"

        Measure-Performance -Component "Startup" -StartTime $startTime

        Write-StatusMessage "`nMonitoring server logs. Press Ctrl+C to shut down.`n" -Color Cyan

        # Register keyboard shortcuts
        $keyboardJob = Register-KeyboardShortcuts
        Write-Host "`nPress 'h' for keyboard shortcuts" -ForegroundColor Cyan

        # Monitor jobs and resources
        while ($backendJob.State -eq 'Running' -and $frontendJob.State -eq 'Running') {
            # Process keyboard input
            if ($keyboardState.LastKeyPress) {
                switch ($keyboardState.LastKeyPress.KeyChar) {
                    'c' { Clear-Host }
                    's' { Show-ServerStats -StartTime $startTime -LogSize (Get-Item $LogFile).Length }
                    'q' {
                        Write-Host "Shutting down..." -ForegroundColor Yellow
                        Cleanup
                        exit 0
                    }
                    'r' {
                        Write-Host "Checking services..." -ForegroundColor Yellow
                        # Service restart logic here
                    }
                }
                $keyboardState.LastKeyPress = $null
            }

            if ($keyboardState.ShowHelp) {
                Show-KeyboardHelp
                $keyboardState.ShowHelp = $false
            }

            # Process backend output with proper error handling and unique file access
            try {
                $backendOutput = Receive-Job -Job $backendJob -ErrorAction SilentlyContinue
                if ($backendOutput) {
                    $formattedOutput = Format-LogMessage -Message $backendOutput -Source "Backend"
                    if ($formattedOutput) {
                        Write-ColoredLog $formattedOutput
                        # Use a unique backend log file to prevent conflicts
                        $backendLogFile = Join-Path (Split-Path $LogFile -Parent) "backend.log"
                        Add-Content -Path $backendLogFile -Value $formattedOutput -ErrorAction SilentlyContinue
                    }
                }
            } catch {
                Write-Host "⚠️ Error processing backend output: $($_.Exception.Message)" -ForegroundColor Yellow
            }

            # Process frontend output with proper error handling
            try {
                $frontendOutput = Receive-Job -Job $frontendJob -ErrorAction SilentlyContinue
                if ($frontendOutput) {
                    $formattedOutput = Format-LogMessage -Message $frontendOutput -Source "Frontend"
                    if ($formattedOutput) {
                        Write-ColoredLog $formattedOutput
                        # Frontend already logs to its own file via Tee-Object
                    }
                }
            } catch {
                Write-Host "⚠️ Error processing frontend output: $($_.Exception.Message)" -ForegroundColor Yellow
            }

            # Show stats every 5 minutes
            if ((Get-Date).Minute % 5 -eq 0 -and (Get-Date).Second -eq 0) {
                try {
                    Show-ServerStats -StartTime $startTime -LogSize (Get-Item $LogFile).Length
                } catch {
                    Write-Host "⚠️ Error showing stats: $($_.Exception.Message)" -ForegroundColor Yellow
                }
            }

            # Monitor resource usage every 30 seconds (but suppress debug output)
            if ((Get-Date).Second % 30 -eq 0) {
                try {
                    Monitor-ProcessResources
                } catch {
                    # Silently ignore monitoring errors to avoid spam
                }
            }

            Start-Sleep -Milliseconds 500
        }

        # Handle job failures
        if ($backendJob.State -ne 'Running') {
            Write-Host "❌ Backend server has stopped unexpectedly." -ForegroundColor Red
            Get-Job -Name "Backend" | Receive-Job | Add-Content -Path $LogFile
            Cleanup
            exit 1
        }
        if ($frontendJob.State -ne 'Running') {
            Write-Host "❌ Frontend server has stopped unexpectedly." -ForegroundColor Red
            Get-Job -Name "Frontend" | Receive-Job | Add-Content -Path $LogFile
            Cleanup
            exit 1
        }
    } else {
        Write-StatusMessage "❌ Frontend failed to start on port $script:frontendPort" -Color Red
        Get-Job -Name "Frontend" | Receive-Job | Add-Content -Path $LogFile
        Cleanup
        exit 1
    }

} catch {
    Track-Usage -Event "ScriptError" -Properties @{ Error = $_.Exception.Message }
    Write-StatusMessage "❌ An unexpected error occurred: $($_.Exception.Message)" -Color Red
    Add-Content -Path $LogFile -Value "ERROR: $($_.Exception.Message)`n$($_.ScriptStackTrace)"
    Cleanup
    exit 1
}
