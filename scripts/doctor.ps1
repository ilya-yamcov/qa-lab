param([switch]$CheckServices)
Set-Location (Split-Path -Parent $PSScriptRoot)
$ErrorActionPreference = "Continue"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "          QA LAB DOCTOR"
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

function Check-Port {
    param(
        [int]$Port,
        [string]$Service
    )

    $connection = Get-NetTCPConnection `
        -LocalPort $Port `
        -State Listen `
        -ErrorAction SilentlyContinue

    if ($connection) {
        Write-Host "[INFO] Port $Port is in use ($Service)" -ForegroundColor Yellow
    }
    else {
        Write-Host "[OK] Port $Port is free ($Service)" -ForegroundColor Green
    }
}

Write-Host "Docker:"
docker --version

Write-Host ""
Write-Host "Docker Compose:"
docker compose version

Write-Host ""
Write-Host "WSL:"
wsl --version

Write-Host ""
Write-Host "Docker Engine:"

docker info *> $null

if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Docker engine is running" -ForegroundColor Green
}
else {
    Write-Host "[ERROR] Docker engine is unavailable" -ForegroundColor Red
}

Write-Host ""
Write-Host "Ports:"

Check-Port 3000  "Grafana"
Check-Port 5432  "PostgreSQL"
Check-Port 5601  "Kibana"
Check-Port 8000  "Demo API"
Check-Port 8080  "TaskFlow"
Check-Port 8081  "Kafka UI"
Check-Port 8082  "Adminer"
Check-Port 9090  "Prometheus"
Check-Port 9200  "Elasticsearch"
Check-Port 29092 "Kafka"

Write-Host ""
Write-Host "Containers:"

docker compose ps

Write-Host ""
Write-Host "========================================"
Write-Host "Doctor finished"
Write-Host "========================================"

if ($CheckServices) { & "$PSScriptRoot\init-observability.ps1" -CheckOnly -TimeoutSeconds 15 }
