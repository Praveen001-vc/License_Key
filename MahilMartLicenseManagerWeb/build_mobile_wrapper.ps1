param(
    [ValidateSet("android", "ios")]
    [string]$Platform = "android",
    [Parameter(Mandatory = $true)]
    [string]$AppUrl
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    throw "Node.js is required. Install Node.js 20+ first."
}

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "npm is required. Install Node.js 20+ first."
}

Push-Location "$PSScriptRoot\\mobile"
try {
    npm install
    npm run mobile:set-url -- --url $AppUrl

    if ($Platform -eq "android") {
        if (-not (Test-Path ".\\android")) {
            npm run mobile:add:android
        }
    }
    else {
        if (-not (Test-Path ".\\ios")) {
            npm run mobile:add:ios
        }
    }

    npm run cap:sync

    if ($Platform -eq "android") {
        npm run mobile:open:android
    }
    else {
        npm run mobile:open:ios
    }
}
finally {
    Pop-Location
}
