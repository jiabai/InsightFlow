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

# ------------------------------------------------------------
# Resolve the Python interpreter to launch with.
# Priority: project-root .venv  ->  $env:INSIGHTFLOW_VENV  ->  fallback default.
# Override the fallback by setting INSIGHTFLOW_VENV to your venv directory.
# ------------------------------------------------------------
$ProjectVenv  = Join-Path $ProjectRoot ".venv"
if ($env:INSIGHTFLOW_VENV) { $FallbackVenv = $env:INSIGHTFLOW_VENV } else { $FallbackVenv = "D:\Code\.venv" }

$PythonExe  = $null
$VenvChosen = $null
foreach ($venv in @($ProjectVenv, $FallbackVenv)) {
    if ($venv) {
        $candidate = Join-Path $venv "Scripts\python.exe"
        if (Test-Path $candidate) { $PythonExe = $candidate; $VenvChosen = $venv; break }
    }
}

if ($PythonExe) {
    Write-Host "    Virtualenv:   $VenvChosen"
    $activate = Join-Path $VenvChosen "Scripts\Activate.ps1"
    if (Test-Path $activate) { & $activate }
} else {
    Write-Host "[WARN] No virtualenv found (project '.venv' or fallback '$FallbackVenv')." -ForegroundColor Yellow
    Write-Host "       Using 'python' from PATH. Set INSIGHTFLOW_VENV to a venv dir to override." -ForegroundColor Yellow
    $PythonExe = "python"
}

# Verify the interpreter exists and actually has the backend deps, so a missing
# environment fails with a clear message instead of an uvicorn import traceback.
if (-not (Get-Command $PythonExe -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] Python interpreter not found: $PythonExe" -ForegroundColor Red
    Write-Host "        Install Python or set INSIGHTFLOW_VENV to a valid venv directory." -ForegroundColor Red
    exit 1
}

$hasUvicorn = & $PythonExe -c "import importlib.util as u; print(1 if u.find_spec('uvicorn') else 0)"
if ("$hasUvicorn".Trim() -ne "1") {
    Write-Host ""
    Write-Host "[ERROR] Backend dependencies missing: '$PythonExe' has no 'uvicorn'." -ForegroundColor Red
    Write-Host "        Fix one of:" -ForegroundColor Red
    Write-Host "          1. Create a project venv:    python -m venv .venv ; .\.venv\Scripts\Activate.ps1 ; pip install -r requirements.txt" -ForegroundColor Red
    Write-Host "          2. Point at an existing venv: `$env:INSIGHTFLOW_VENV = '<venv dir>'   (e.g. D:\Code\.venv)" -ForegroundColor Red
    Write-Host "          3. Install into this one:     $PythonExe -m pip install -r requirements.txt" -ForegroundColor Red
    exit 1
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
    $env:INSIGHTFLOW_LOG_LEVEL = "INFO"
}
if (-not $env:INSIGHTFLOW_LOG_CONSOLE) {
    $env:INSIGHTFLOW_LOG_CONSOLE = "0"
}

$ConsoleLogEnabled = $env:INSIGHTFLOW_LOG_CONSOLE -match "^(1|true|yes|on)$"
$UvicornLogLevel = if ($env:UVICORN_LOG_LEVEL) {
    $env:UVICORN_LOG_LEVEL
} elseif ($ConsoleLogEnabled) {
    "info"
} else {
    "warning"
}
$UvicornAccessLogArgs = if ($env:UVICORN_ACCESS_LOG -match "^(1|true|yes|on)$") {
    @()
} else {
    @("--no-access-log")
}

# Set PYTHONPATH
$env:PYTHONPATH = "$ProjectRoot\src;$env:PYTHONPATH"

Write-Host "    Listening on: http://localhost:$Port" -ForegroundColor Green
Write-Host "    API docs:     http://localhost:$Port/docs" -ForegroundColor Green
Write-Host "    Log level:    $env:INSIGHTFLOW_LOG_LEVEL"
Write-Host "    Console log:  $env:INSIGHTFLOW_LOG_CONSOLE"
Write-Host "    Uvicorn log:  $UvicornLogLevel"
Write-Host ""

& $PythonExe -m uvicorn server.main:app --app-dir src --host $BindHost --port $Port --reload --log-level $UvicornLogLevel @UvicornAccessLogArgs
