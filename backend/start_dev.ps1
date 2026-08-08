$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not $env:TAX_AI_DATABASE_URL) {
    $env:TAX_AI_DATABASE_URL = "sqlite+pysqlite:///./dev.db"
}
if (-not $env:TAX_AI_JWT_SECRET) {
    $env:TAX_AI_JWT_SECRET = ([guid]::NewGuid().ToString("N") + [guid]::NewGuid().ToString("N"))
}

& ".\.venv\Scripts\alembic.exe" upgrade head
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& ".\.venv\Scripts\python.exe" -m uvicorn app.main:create_app --factory --reload
