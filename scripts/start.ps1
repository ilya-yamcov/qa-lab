$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "          STARTING QA LAB"
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Проверяем Docker
docker info *> $null

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Docker Desktop is not running." -ForegroundColor Red
    exit 1
}

# Elasticsearch kernel requirement
Write-Host "[1/4] Configuring Elasticsearch..."

try {
    wsl -d docker-desktop -u root `
        sysctl -w vm.max_map_count=1048576 *> $null

    if ($LASTEXITCODE -ne 0) { throw "sysctl failed" }; Write-Host "[OK] vm.max_map_count configured" -ForegroundColor Green
}
catch {
    Write-Host "[WARNING] Could not automatically set vm.max_map_count" -ForegroundColor Yellow
}

# Start
Write-Host ""
Write-Host "[2/4] Starting containers..."

docker compose up -d --build

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Docker Compose startup failed" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "[3/4] Waiting for services..."

Start-Sleep -Seconds 15

# Health API
$ApiReady = $false

for ($i = 1; $i -le 20; $i++) {

    try {
        $response = Invoke-RestMethod `
            -Uri "http://localhost:8000/health" `
            -TimeoutSec 3

        if ($response.status -eq "UP") {
            $ApiReady = $true
            break
        }
    }
    catch {}

    Write-Host "Waiting for API... ($i/20)"
    Start-Sleep -Seconds 3
}

Write-Host ""
if (!$ApiReady) { throw "API did not become ready. Check docker compose logs demo-api." }
& "$PSScriptRoot\init-observability.ps1"
Write-Host "[4/4] Status:"
docker compose ps

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan

if ($ApiReady) {
    Write-Host "          QA LAB IS READY" -ForegroundColor Green
}
else {
    Write-Host "QA LAB STARTED, BUT API IS NOT READY" -ForegroundColor Yellow
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "TaskFlow:    http://localhost:8080"
Write-Host "Swagger:     http://localhost:8000/docs"
Write-Host "Kafka UI:    http://localhost:8081"
Write-Host "Adminer:     http://localhost:8082"
Write-Host "Grafana:     http://localhost:3000"
Write-Host "Kibana:      http://localhost:5601"
Write-Host "Prometheus:  http://localhost:9090"
Write-Host ""
Write-Host "PostgreSQL:  localhost:5432"
Write-Host "Kafka:       localhost:29092"
Write-Host ""
Write-Host "Login:       qaengineer"
Write-Host "Password:    123qa"
Write-Host ""
Write-Host "========================================"

