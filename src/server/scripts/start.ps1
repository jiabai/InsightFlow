# ============================================================
# InsightFlow backend service launcher (Windows PowerShell)
# Usage: .\src\server\scripts\start.ps1
# ============================================================
$ErrorActionPreference = "Stop"

# Force UTF-8 output to avoid mojibake on Windows console
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
chcp 65001 | Out-Null

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path "$ScriptDir\..\..\.."

Write-Host "==> InsightFlow backend service starting" -ForegroundColor Cyan
Write-Host "    Project root: $ProjectRoot"

# Switch to project root
Set-Location $ProjectRoot

# Verify src\.env exists
if (-not (Test-Path "src\.env")) {
    Write-Host "[ERROR] Config file src\.env is missing. Please create it first." -ForegroundColor Red
    exit 1
}

# Activate virtualenv if present
if (Test-Path ".venv") {
    & ".venv\Scripts\Activate.ps1"
    Write-Host "    Virtualenv activated"
}

# Load .env (skip VITE_-prefixed frontend vars)
Get-Content "src\.env" | ForEach-Object {
    $line = $_.Trim()
    if ($line -and -not $line.StartsWith("#") -and $line -match "=") {
        $key, $value = $line -split "=", 2
        if ($key -notmatch "^VITE_") {
            [Environment]::SetEnvironmentVariable($key, $value, "Process")
        }
    }
}
$BindHost = if ($env:SERVER_HOST) { $env:SERVER_HOST } else { "0.0.0.0" }
$Port = if ($env:SERVER_PORT) { $env:SERVER_PORT } else { "8080" }

if (-not $env:INSIGHTFLOW_LOG_LEVEL) {
    $env:INSIGHTFLOW_LOG_LEVEL = "DEBUG"
}
if (-not $env:INSIGHTFLOW_LOG_CONSOLE) {
    $env:INSIGHTFLOW_LOG_CONSOLE = "1"
}

# Set PYTHONPATH
$env:PYTHONPATH = "$ProjectRoot\src;$env:PYTHONPATH"

Write-Host "    Listening on: http://localhost:$Port" -ForegroundColor Green
Write-Host "    API docs:     http://localhost:$Port/docs" -ForegroundColor Green
Write-Host "    Log level:    $env:INSIGHTFLOW_LOG_LEVEL"
Write-Host "    Console log:  $env:INSIGHTFLOW_LOG_CONSOLE"
Write-Host ""

$env:PYTHONPATH = "$ProjectRoot\src;$env:PYTHONPATH"
python -m uvicorn server.main:app --app-dir src --host $BindHost --port $Port --reload
