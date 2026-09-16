param([switch]$Install)
$ErrorActionPreference = 'Stop'
$projectPath = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectPath
if ($Install) {
    uv sync --python 3.12
    if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed.' }
    Push-Location frontend
    npm.cmd ci
    if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed.' }
    Pop-Location
}
& .\.venv\Scripts\python.exe -m alembic upgrade head
if ($LASTEXITCODE -ne 0) { throw 'Migration failed.' }
& .\.venv\Scripts\python.exe -m backend.bootstrap
Push-Location frontend
npm.cmd run build
if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
Pop-Location
$backendProcess = Start-Process -FilePath "$projectPath\.venv\Scripts\python.exe" -ArgumentList @('-m','uvicorn','backend.main:app','--host','127.0.0.1','--port','8000') -WorkingDirectory $projectPath -WindowStyle Hidden -PassThru
Write-Host 'ShopPilot: http://127.0.0.1:5173 — Ctrl+C stops the frontend.'
try {
    Set-Location -LiteralPath "$projectPath\frontend"
    npm.cmd run preview -- --port 5173
} finally {
    Stop-Process -Id $backendProcess.Id -ErrorAction SilentlyContinue
}
