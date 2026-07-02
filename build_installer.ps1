# End-to-end Windows installer build.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File .\build_installer.ps1
#   powershell -ExecutionPolicy Bypass -File .\build_installer.ps1 -Version 1.0.0

[CmdletBinding()]
param(
    [string] $Version = "1.0.0",
    [switch] $SkipExeBuild
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

if ($SkipExeBuild) {
    Write-Host "`n=== Skipping exe build ===" -ForegroundColor Yellow
    if (-not (Test-Path "dist\WHPalletPrinter.exe")) {
        throw "dist\WHPalletPrinter.exe not found. Run without -SkipExeBuild first."
    }
} else {
    Write-Host "`n=== Building WHPalletPrinter.exe ===" -ForegroundColor Cyan
    & .\build_windows.ps1
}

$VendorDir = Join-Path $PSScriptRoot "installer\vendor"
New-Item -ItemType Directory -Force -Path $VendorDir | Out-Null

function Fetch-Installer {
    param(
        [Parameter(Mandatory)] [string] $FileName,
        [Parameter(Mandatory)] [string] $Url
    )
    $dest = Join-Path $VendorDir $FileName
    if (Test-Path $dest) {
        Write-Host "  [cached] $FileName" -ForegroundColor DarkGray
        return
    }
    Write-Host "  [download] $FileName" -ForegroundColor DarkGray
    Invoke-WebRequest -Uri $Url -OutFile $dest -UseBasicParsing
}

Write-Host "`n=== Staging prereq installers ===" -ForegroundColor Cyan
Fetch-Installer -FileName "MicrosoftEdgeWebView2Setup.exe" `
    -Url "https://go.microsoft.com/fwlink/?linkid=2124703"
Fetch-Installer -FileName "vc_redist.x64.exe" `
    -Url "https://aka.ms/vs/17/release/vc_redist.x64.exe"

function Find-Iscc {
    $candidates = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\iscc.exe",
        "${env:ProgramFiles}\Inno Setup 6\iscc.exe"
    )
    foreach ($p in $candidates) {
        if ($p -and (Test-Path $p)) { return $p }
    }
    $cmd = Get-Command iscc.exe -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    throw "Inno Setup 6 not found."
}

$iscc = Find-Iscc
Write-Host "`n=== Compiling installer ===" -ForegroundColor Cyan
& $iscc "/DMyAppVersion=$Version" "installer\WHPalletPrinter.iss"
if ($LASTEXITCODE -ne 0) {
    throw "iscc.exe failed (exit code $LASTEXITCODE)"
}

$out = Join-Path $PSScriptRoot "installer\Output\WHPalletPrinter-Setup-$Version.exe"
if (-not (Test-Path $out)) {
    throw "Installer not produced at expected path: $out"
}

Write-Host "`n=== Done ===" -ForegroundColor Green
Get-Item $out | Format-List Name, Length, LastWriteTime
