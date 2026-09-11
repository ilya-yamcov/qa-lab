$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "       QA LAB - WINDOWS SETUP"
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$HasErrors = $false

# Windows
Write-Host "[1/7] Checking Windows..."

if ($env:OS -eq "Windows_NT") {
    Write-Host "[OK] Windows detected" -ForegroundColor Green
}
else {
    Write-Host "[ERROR] This script is intended for Windows" -ForegroundColor Red
    $HasErrors = $true
}

# WSL
Write-Host ""
Write-Host "[2/7] Checking WSL2..."

try {
    $wslVersion = wsl --version 2>&1

    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] WSL is installed" -ForegroundColor Green
    }
    else {
        throw
    }
}
catch {
    Write-Host "[ERROR] WSL is not installed" -ForegroundColor Red
    Write-Host "Run PowerShell as Administrator:"
    Write-Host "wsl --install"
    $HasErrors = $true
}

# Docker CLI
Write-Host ""
Write-Host "[3/7] Checking Docker..."

try {
    $dockerVersion = docker --version 2>&1

    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] $dockerVersion" -ForegroundColor Green
    }
    else {
        throw
    }
}
catch {
    Write-Host "[ERROR] Docker not found" -ForegroundColor Red
    Write-Host "Install Docker Desktop first."
    $HasErrors = $true
}

# Docker Engine
Write-Host ""
Write-Host "[4/7] Checking Docker Desktop engine..."

try {
    docker info *> $null

    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] Docker Desktop is running" -ForegroundColor Green
    }
    else {
        throw
    }
}
catch {
    Write-Host "[ERROR] Docker Desktop is installed but not running" -ForegroundColor Red
    $HasErrors = $true
}

# Compose
Write-Host ""
Write-Host "[5/7] Checking Docker Compose..."

try {
    $composeVersion = docker compose version 2>&1

    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] $composeVersion" -ForegroundColor Green
    }
    else {
        throw
    }
}
catch {
    Write-Host "[ERROR] Docker Compose not found" -ForegroundColor Red
    $HasErrors = $true
}

# RAM
Write-Host ""
Write-Host "[6/7] Checking RAM..."

$ramBytes = (Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory
$ramGB = [math]::Round($ramBytes / 1GB, 1)

if ($ramGB -ge 16) {
    Write-Host "[OK] RAM: $ramGB GB" -ForegroundColor Green
}
elseif ($ramGB -ge 8) {
    Write-Host "[WARNING] RAM: $ramGB GB. QA Lab may be slow." -ForegroundColor Yellow
}
else {
    Write-Host "[ERROR] RAM: $ramGB GB. At least 8 GB required." -ForegroundColor Red
    $HasErrors = $true
}

# Disk
Write-Host ""
Write-Host "[7/7] Checking free disk space..."

$drive = Get-PSDrive -Name C
$freeGB = [math]::Round($drive.Free / 1GB, 1)

if ($freeGB -ge 40) {
    Write-Host "[OK] Free disk space: $freeGB GB" -ForegroundColor Green
}
elseif ($freeGB -ge 25) {
    Write-Host "[WARNING] Free disk space: $freeGB GB" -ForegroundColor Yellow
}
else {
    Write-Host "[ERROR] Only $freeGB GB free" -ForegroundColor Red
    $HasErrors = $true
}

Write-Host ""
Write-Host "========================================"

if ($HasErrors) {
    Write-Host "SETUP CHECK FAILED" -ForegroundColor Red
    Write-Host "Fix the errors above and run this script again."
    exit 1
}
else {
    Write-Host "QA LAB REQUIREMENTS: OK" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next command:"
    Write-Host ".\scripts\start.ps1" -ForegroundColor Cyan
}

Write-Host "========================================"
