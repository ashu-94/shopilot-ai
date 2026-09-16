param([switch]$SkipBuild)
$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')
$composeArgs = @('compose','-p','shopilot-verification','-f','docker-compose.yml','-f','docker-compose.verify.yml')
function Invoke-Stack {
    & docker @composeArgs @args
    if ($LASTEXITCODE -ne 0) { throw "Docker verification step failed: $args" }
}
& docker info --format '{{.ServerVersion}}'
if ($LASTEXITCODE -ne 0) { throw 'Docker engine access is required. Run this script from a PowerShell session with Docker Desktop access.' }
New-Item -ItemType Directory -Force 'verification' | Out-Null
try {
    Invoke-Stack config --quiet
    if ($SkipBuild) { Invoke-Stack up -d --wait --wait-timeout 600 } else { Invoke-Stack up -d --build --wait --wait-timeout 600 }
    Invoke-Stack exec -T backend python -m scripts.verify_stack
    Invoke-Stack exec -T backend python -m scripts.verify_stack --phase prepare-restart
    Invoke-Stack restart backend
    Invoke-Stack up -d --wait --wait-timeout 120
    Invoke-Stack exec -T backend python -m scripts.verify_stack --phase resume
    Invoke-Stack stop kafka
    try { Invoke-Stack exec -T backend python -m scripts.verify_stack --phase kafka-outage }
    finally { Invoke-Stack start kafka }
    Invoke-Stack exec -T backend python -m scripts.verify_stack --phase kafka-recovery
    Invoke-Stack cp backend:/app/data/verification/. ./verification/
} finally {
    & docker @composeArgs logs --no-color --tail 150 > verification/docker.log
    & docker @composeArgs ps -a > verification/containers.txt
}
Write-Host 'Verification passed. Stack remains available at http://127.0.0.1:15173. Evidence is in verification/.'
