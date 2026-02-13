$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$exePath = Join-Path $PSScriptRoot "dist\\MahilMartLicenseManagerWeb.exe"
if (-not (Test-Path $exePath)) {
    Write-Host "EXE not found. Building EXE first..."
    powershell -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "build_exe.ps1")
}

$isccCandidates = @(
    "${env:ProgramFiles(x86)}\\Inno Setup 6\\ISCC.exe",
    "$env:ProgramFiles\\Inno Setup 6\\ISCC.exe"
)

$iscc = $isccCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) {
    throw "Inno Setup 6 not found. Install Inno Setup, then run this script again."
}

& $iscc (Join-Path $PSScriptRoot "MahilMartLicenseManagerWeb.iss")
Write-Host ""
Write-Host "Installer build complete."
Write-Host "Output: $PSScriptRoot\\dist-installer\\MahilMartLicenseManagerWebSetup.exe"
