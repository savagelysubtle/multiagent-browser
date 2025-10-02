#!/usr/bin/env pwsh
# Electron Build Script for Web-UI

param(
    [ValidateSet("win", "mac", "linux", "all")]
    [string]$Platform = "win",
    [switch]$Clean,
    [switch]$Publish
)

Write-Host "🔧 Building Electron App for $Platform..." -ForegroundColor Green

# Clean previous builds if requested
if ($Clean) {
    Write-Host "🧹 Cleaning previous builds..." -ForegroundColor Yellow
    Remove-Item -Path "dist", "dist-electron" -Recurse -Force -ErrorAction SilentlyContinue
}

# Change to frontend directory
Set-Location "frontend"

try {
    # Install dependencies if node_modules doesn't exist
    if (!(Test-Path "node_modules")) {
        Write-Host "📦 Installing dependencies..." -ForegroundColor Cyan
        npm install
    }

    # Build the web app first
    Write-Host "🏗️ Building React app..." -ForegroundColor Cyan
    npm run build:web

    # Build Electron app
    switch ($Platform) {
        "win" {
            Write-Host "🪟 Building for Windows..." -ForegroundColor Cyan
            npm run electron-builder -- --win
        }
        "mac" {
            Write-Host "🍎 Building for macOS..." -ForegroundColor Cyan
            npm run electron-builder -- --mac
        }
        "linux" {
            Write-Host "🐧 Building for Linux..." -ForegroundColor Cyan
            npm run electron-builder -- --linux
        }
        "all" {
            Write-Host "🌍 Building for all platforms..." -ForegroundColor Cyan
            npm run dist:all
        }
    }

    Write-Host "✅ Build completed successfully!" -ForegroundColor Green
    Write-Host "📁 Output directory: dist-electron/" -ForegroundColor Cyan

    # List built files
    if (Test-Path "dist-electron") {
        Write-Host "`nBuilt files:" -ForegroundColor Cyan
        Get-ChildItem "dist-electron" | ForEach-Object {
            Write-Host "  📦 $($_.Name)" -ForegroundColor Gray
        }
    }

} catch {
    Write-Host "❌ Build failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
} finally {
    # Return to project root
    Set-Location ".."
}