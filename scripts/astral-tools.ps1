#!/usr/bin/env pwsh
# Astral Toolchain Integration Script
# Demonstrates UV (package management), Ruff (linting/formatting), and Ty (type checking)
# Usage: .\scripts\astral-tools.ps1 [check|format|sync|all]

param(
    [Parameter(Position = 0)]
    [ValidateSet("check", "format", "sync", "all", "")]
    [string]$Action = "all"
)

function Show-Header {
    param([string]$Title)
    Write-Host "`n=== $Title ===" -ForegroundColor Cyan
}

function Run-UV {
    Show-Header "UV - Package Management"
    Write-Host "Syncing dependencies..." -ForegroundColor Blue
    uv sync --all-groups

    Write-Host "Checking lock file status..." -ForegroundColor Blue
    uv lock --check
}

function Run-Ruff {
    Show-Header "Ruff - Linting & Formatting"
    Write-Host "Running Ruff formatter (includes f-string formatting)..." -ForegroundColor Blue
    uv run ruff format .

    Write-Host "Running Ruff linter..." -ForegroundColor Blue
    uv run ruff check . --fix
}

function Run-Ty {
    Show-Header "Ty - Type Checking"
    Write-Host "Running Ty type checker..." -ForegroundColor Blue

    # Check backend source code
    if (Test-Path "backend/src") {
        Write-Host "Checking backend/src..." -ForegroundColor Green
        uvx ty check backend/src
    }

    # Check any Python files in root
    $rootPyFiles = Get-ChildItem -Path . -Name "*.py" -File
    if ($rootPyFiles) {
        Write-Host "Checking Python files in root..." -ForegroundColor Green
        uvx ty check $rootPyFiles
    }
}

function Run-All {
    Write-Host "Running complete Astral toolchain..." -ForegroundColor Magenta
    Run-UV
    Run-Ruff
    Run-Ty
    Write-Host "`nAll tools completed successfully! ✨" -ForegroundColor Green
}

# Execute based on action parameter
switch ($Action) {
    "check" { Run-Ty }
    "format" { Run-Ruff }
    "sync" { Run-UV }
    "all" { Run-All }
    default { Run-All }
}