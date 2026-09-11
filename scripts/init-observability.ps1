param([int]$TimeoutSeconds = 300, [switch]$CheckOnly)
$ErrorActionPreference = 'Stop'

function Wait-Service($Uri) {
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        try { return Invoke-RestMethod -Uri $Uri -TimeoutSec 5 }
        catch { $lastFailure = $_.Exception.Message }
        if ((Get-Date) -ge $deadline) { throw "Timed out waiting for ${Uri}: $lastFailure" }
        Start-Sleep -Seconds 3
    } while ($true)
}

$null = Wait-Service 'http://localhost:5601/api/status'
$headers = @{ 'kbn-xsrf' = 'qa-lab-provisioning' }
$base = 'http://localhost:5601/api/data_views'
$views = Invoke-RestMethod $base -TimeoutSec 10
$view = $views.data_view | Where-Object title -eq 'qa-demo-*' | Select-Object -First 1
if (!$CheckOnly) {
    if ($view) {
        $body = @{ data_view = @{ title = 'qa-demo-*'; timeFieldName = '@timestamp'; allowNoIndex = $true } } | ConvertTo-Json -Depth 5
        $result = Invoke-RestMethod "$base/data_view/$($view.id)" -Method Post -Headers $headers -ContentType 'application/json' -Body $body -TimeoutSec 15
    } else {
        $body = @{ data_view = @{ title = 'qa-demo-*'; timeFieldName = '@timestamp'; allowNoIndex = $true } } | ConvertTo-Json -Depth 5
        $result = Invoke-RestMethod "$base/data_view" -Method Post -Headers $headers -ContentType 'application/json' -Body $body -TimeoutSec 15
    }
    $view = $result.data_view
    $body = @{ data_view_id = $view.id; force = $true } | ConvertTo-Json
    $null = Invoke-RestMethod "$base/default" -Method Post -Headers $headers -ContentType 'application/json' -Body $body -TimeoutSec 15
}
if (!$view) { throw 'Kibana qa-demo-* data view is missing. Run scripts/init-observability.ps1.' }
$details = Invoke-RestMethod "$base/data_view/$($view.id)" -TimeoutSec 10
if ($details.data_view.timeFieldName -ne '@timestamp') { throw 'Kibana time field must be @timestamp.' }
Write-Host '[OK] Kibana qa-demo-* (@timestamp)' -ForegroundColor Green

$auth = @{ Authorization = 'Basic ' + [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes('qaengineer:123qa')) }
$null = Wait-Service 'http://localhost:3000/api/health'
$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
do {
    try {
        $ds = Invoke-RestMethod 'http://localhost:3000/api/datasources/name/Prometheus' -Headers $auth -TimeoutSec 5
        $dashboard = Invoke-RestMethod 'http://localhost:3000/api/dashboards/uid/qa-lab-overview' -Headers $auth -TimeoutSec 5
        if ($ds.url -ne 'http://prometheus:9090') { throw 'Unexpected Prometheus datasource URL.' }
        break
    } catch {
        if ((Get-Date) -ge $deadline) { throw "Grafana provisioning check failed: $($_.Exception.Message). Check docker compose logs grafana. Existing volumes retain their original admin password." }
        Start-Sleep -Seconds 3
    }
} while ($true)
Write-Host '[OK] Grafana Prometheus datasource and QA Lab dashboard' -ForegroundColor Green

