$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

Write-Host "Stopping QA Lab..."

docker compose stop

Write-Host ""
Write-Host "QA Lab stopped."
Write-Host "Data has been preserved."
