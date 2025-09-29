#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Development startup script for Web-UI project
.DESCRIPTION
    Starts both the React frontend (npm run dev) and Python backend (webui.py) concurrently
.EXAMPLE
    .\start-dev.ps1
#>

Write-Host "?? Starting Web-UI Development Environment..." -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Cyan

# Check if we're in the correct directory
if (-not (Test-Path "webui.py")) {
    Write-Host "? Error: webui.py not found. Please run this script from the project root." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path "frontend/package.json")) {
    Write-Host "? Error: frontend/package.json not found. Please ensure frontend is set up." -ForegroundColor Red
    exit 1
}

# Function to cleanup background jobs on exit
function Cleanup {
    Write-Host "`n?? Shutting down servers..." -ForegroundColor Yellow
    Get-Job | Stop-Job
    Get-Job | Remove-Job
    Write-Host "? Cleanup complete. Goodbye!" -ForegroundColor Green
}

# Register cleanup function for Ctrl+C
Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action { Cleanup }

try {
    # Start Python backend
    Write-Host "?? Starting Python backend server..." -ForegroundColor Blue
    $backendJob = Start-Job -ScriptBlock {
        Set-Location $using:PWD
        python webui.py
    } -Name "Backend"

    # Wait a moment for backend to initialize
    Start-Sleep -Seconds 2

    # Start React frontend
    Write-Host "??  Starting React frontend server..." -ForegroundColor Blue
    $frontendJob = Start-Job -ScriptBlock {
        Set-Location $using:PWD
        Set-Location frontend
        npm run dev
    } -Name "Frontend"

    # Wait a moment for frontend to initialize
    Start-Sleep -Seconds 3

    Write-Host "`n? Both servers are starting up!" -ForegroundColor Green
    Write-Host "?? Frontend: http://localhost:3000/" -ForegroundColor Cyan
    Write-Host "?? Backend:  http://localhost:8000/" -ForegroundColor Cyan
    Write-Host "`n?? Press Ctrl+C to stop both servers" -ForegroundColor Yellow
    Write-Host "================================================" -ForegroundColor Cyan

    # Monitor jobs and display output
    while ($true) {
        # Check if jobs are still running
        $runningJobs = Get-Job | Where-Object { $_.State -eq "Running" }

        if ($runningJobs.Count -eq 0) {
            Write-Host "? All servers have stopped." -ForegroundColor Red
            break
        }

        # Display job output (without -Keep to show only new output)
        foreach ($job in $runningJobs) {
            $output = Receive-Job -Job $job
            if ($output) {
                $text = $output | Where-Object { $null -ne $_ } | ForEach-Object { $_.ToString().TrimEnd("`r", "`n") }
                if ($text) {
                    Write-Host ("[$($job.Name)] " + ($text -join "`n[$($job.Name)] ")) -ForegroundColor Gray
                }
            }
        }

        Start-Sleep -Seconds 1
    }
}
catch {
    Write-Host "? Error occurred: $($_.Exception.Message)" -ForegroundColor Red
}
finally {
    Cleanup
}
