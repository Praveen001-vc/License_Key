$ErrorActionPreference = "Stop"

python -m pip install --upgrade pip pyinstaller pymongo dnspython certifi

python -m PyInstaller --clean --noconfirm MahilMartLicenseManagerWeb.spec

Write-Host ""
Write-Host "Build completed."
Write-Host "EXE path: dist\\MahilMartLicenseManagerWeb.exe"
