# ==============================================================================
# Smart Classroom Environmental Monitoring System
# PowerShell Telemetry Test Script
# ==============================================================================
param (
    [double]$Temperature = 25.4,
    [double]$Humidity = 58.2,
    [string]$DeviceId = "esp32-classroom-01",
    [string]$Uri = "http://localhost:8000/api/readings"
)

Write-Host "Sending HTTP POST reading to $Uri ..." -ForegroundColor Cyan

$body = @{
    temperature = $Temperature
    humidity = $Humidity
    device_id = $DeviceId
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri $Uri -Method Post -Body $body -ContentType "application/json"
    Write-Host "`n[SUCCESS] Reading Received by Server:" -ForegroundColor Green
    $response | Format-List
} catch {
    Write-Host "`n[ERROR] Request failed: $_" -ForegroundColor Red
}
