$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
python -m venv .venv
if ($LASTEXITCODE -ne 0) { throw 'Virtual environment creation failed' }
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
& .\.venv\Scripts\python.exe -c "from backend.database import init_db; init_db()"
if ($LASTEXITCODE -ne 0) { throw 'Database initialization failed' }
Write-Host 'Setup complete. For a new demo catalog: .\.venv\Scripts\python.exe -m sandbox.seed'
