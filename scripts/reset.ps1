$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

Write-Host ""
Write-Host "WARNING!" -ForegroundColor Red
Write-Host "This will delete ALL QA Lab data:"
Write-Host "- PostgreSQL data"
Write-Host "- Kafka messages"
Write-Host "- Elasticsearch logs"
Write-Host "- Grafana data"
Write-Host ""

$answer = Read-Host "Continue? Type YES"

if ($answer -ne "YES") {
    Write-Host "Cancelled."
    exit 0
}

docker compose down -v --remove-orphans

if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to remove QA Lab." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Starting clean QA Lab..."

& "$PSScriptRoot\start.ps1"
