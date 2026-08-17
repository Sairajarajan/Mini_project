# One-command Aegis setup (Windows): creates .env, installs deps, downloads models.
# Run from backend/:  powershell -ExecutionPolicy Bypass -File setup.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "==> 1/4 Creating .env from .env.example (if missing)"
if (-not (Test-Path "$root\.env")) {
    Copy-Item "$root\.env.example" "$root\.env"
    Write-Host "    .env created - EDIT IT NOW and paste your MONGODB_URI:"
    Write-Host "    notepad $root\.env"
} else {
    Write-Host "    .env already exists"
}

Write-Host "==> 2/4 Creating virtualenv + installing dependencies"
if (-not (Test-Path "$root\.venv")) {
    python -m venv "$root\.venv"
}
& "$root\.venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
& "$root\.venv\Scripts\python.exe" -m pip install -r "$root\requirements.txt" --quiet
& "$root\.venv\Scripts\python.exe" -m pip install -r "$root\requirements-ml.txt" --quiet
& "$root\.venv\Scripts\python.exe" -m pip install email-validator pytest pytest-asyncio --quiet

Write-Host "==> 3/4 Downloading ML models (~4.4 GB, one time)"
& "$root\.venv\Scripts\python.exe" "$root\scripts\download_models.py"

Write-Host "==> 4/4 Verifying MongoDB"
& "$root\.venv\Scripts\python.exe" "$root\scripts\test_db.py"

Write-Host ""
Write-Host "DONE. Start the backend with:"
Write-Host "    $root\.venv\Scripts\python -m uvicorn app.main:app --port 8000"
Write-Host "Start the web UI (new terminal):"
Write-Host "    cd ..\web; npm install; npm run dev"