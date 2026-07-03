# Local Windows build script.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File .\build_windows.ps1
#
# Output: dist\WHPalletPrinter.exe

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

Write-Host "=== Tool versions ===" -ForegroundColor Cyan
python --version
node --version
npm --version

Write-Host "`n=== Building Svelte frontend ===" -ForegroundColor Cyan
Push-Location frontend
npm ci
if ($LASTEXITCODE -ne 0) { throw "npm ci failed (exit $LASTEXITCODE). Stop any running 'npm run dev' and retry." }
npm run build
if ($LASTEXITCODE -ne 0) { throw "Frontend build failed (exit $LASTEXITCODE)" }
Pop-Location

Write-Host "`n=== Setting up Python venv ===" -ForegroundColor Cyan
if (-not (Test-Path .venv)) {
    python -m venv .venv
}
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\pip.exe install -r requirements.txt
.\.venv\Scripts\pip.exe install pyinstaller

Write-Host "`n=== Seeding data files ===" -ForegroundColor Cyan
.\.venv\Scripts\python.exe scripts\seed_data.py

Write-Host "`n=== Building app icon ===" -ForegroundColor Cyan
.\.venv\Scripts\python.exe scripts\build_icon.py

Write-Host "`n=== Running PyInstaller ===" -ForegroundColor Cyan
.\.venv\Scripts\pyinstaller.exe `
    --noconfirm --clean --windowed --onefile `
    --name WHPalletPrinter `
    --icon assets\icon.ico `
    --add-data "frontend\dist;frontend\dist" `
    --add-data "data;data" `
    --collect-all pywebview `
    --collect-submodules uvicorn `
    --collect-submodules reportlab.graphics.barcode `
    app.py

if (-not (Test-Path "dist\WHPalletPrinter.exe")) {
    throw "Build failed: dist\WHPalletPrinter.exe not produced"
}

Write-Host "`n=== Done ===" -ForegroundColor Green
Get-Item dist\WHPalletPrinter.exe | Format-List Name, Length, LastWriteTime
