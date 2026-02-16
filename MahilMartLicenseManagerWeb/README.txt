MahilMart License Manager Web (Fully Separate Django Project)

Project folder:
  C:\Users\Billing System 2\Documents\MahilMartLicenseManagerWeb

This project is independent from POS codebase and has separate:
  - settings: license_manager_web/settings.py
  - model: licenses/models.py
  - views: licenses/views.py
  - urls: license_manager_web/urls.py + licenses/urls.py

Run steps:
  1) cd C:\Users\Billing System 2\Documents\MahilMartLicenseManagerWeb
  2) python manage.py migrate
  3) python manage.py runserver
  4) Open http://127.0.0.1:8001/
  5) If no superuser exists, setup page opens first. Create superuser, then login normally.

EXE build (POS style):
  1) cd C:\Users\Billing System 2\Documents\MahilMartLicenseManagerWeb
  2) powershell -ExecutionPolicy Bypass -File .\build_exe.ps1
  3) Run dist\MahilMartLicenseManagerWeb.exe

Installer build (Inno Setup):
  1) Install Inno Setup 6
  2) cd C:\Users\Billing System 2\Documents\MahilMartLicenseManagerWeb
  3) powershell -ExecutionPolicy Bypass -File .\build_installer.ps1
  4) Run dist-installer\MahilMartLicenseManagerWebSetup.exe

Installer behavior:
  - No license key prompt is shown during installation.
  - Installer asks:
      * PostgreSQL database name
      * PostgreSQL password (for postgres user)
  - Installer creates the database automatically if it does not exist.
  - Installer writes DB config to {app}\db_config.env used by the EXE.

EXE notes:
  - Launcher file: app_launcher.py
  - PyInstaller spec: MahilMartLicenseManagerWeb.spec
  - EXE enables IP mode automatically and runs on 0.0.0.0:8001
  - EXE opens LAN IP URL by default (POS style)
  - To force opening local URL, set LICENSE_MANAGER_BROWSER_HOST=local
  - EXE reads PostgreSQL config from db_config.env when installed
  - If db_config.env is missing, EXE falls back to writable SQLite at %LOCALAPPDATA%\MahilMartLicenseManagerWeb\db.sqlite3

Main routes:
  /                 -> Login page
  /setup-admin/     -> First superuser setup (one-time)
  /dashboard/       -> License generator dashboard (login required)
  /users/           -> User list/manage (superuser only)

License rule:
  - Default mode: key rotates by validity window (default 10 minutes).
  - After 10 minutes, generating again gives a new key for same machine.
  - Optional POS static mode: set MAHILMARTPOS_LICENSE_KEY_SEED_MODE=pos_static

Optional environment variables:
  MAHILMARTPOS_LICENSE_EMAIL
  MAHILMARTPOS_LICENSE_SOURCE
  MAHILMARTPOS_LICENSE_KEY_VALIDITY_MINUTES
  MAHILMARTPOS_LICENSE_KEY_SEED_MODE
  MAHILMARTPOS_LICENSE_MONGO_URI
  MAHILMARTPOS_LICENSE_MONGO_DB
  MAHILMARTPOS_LICENSE_MONGO_COLLECTION

Mobile + Installable App (Android/iOS):
  - Responsive layout is enabled for phone/tablet breakpoints.
  - PWA files are enabled:
      * /manifest.webmanifest
      * /sw.js
  - App icons:
      * static/icons/icon-192.png
      * static/icons/icon-512.png
      * static/icons/apple-touch-icon.png

Install on Android (Chrome):
  1) Open the app URL in Chrome.
  2) Tap menu -> "Install app" / "Add to Home screen".
  3) Launch from home screen as standalone app.

Install on iOS (Safari):
  1) Open the app URL in Safari.
  2) Tap Share -> "Add to Home Screen".
  3) Launch from home screen (standalone mode).

Important:
  - Service worker and install prompt require HTTPS in production.
  - localhost/127.0.0.1 works for development testing.

Native Mobile App Build (APK / iOS app):
  - Capacitor wrapper project is in: mobile\
  - Detailed guide: mobile\README.md

Quick build command (Windows):
  1) Android:
     powershell -ExecutionPolicy Bypass -File .\build_mobile_wrapper.ps1 -Platform android
  2) iOS (macOS required for final iOS build):
     powershell -ExecutionPolicy Bypass -File .\build_mobile_wrapper.ps1 -Platform ios

Notes for native wrapper:
  - Default mode auto-detects server IP on local Wi-Fi (port 8001) using /healthz/.
  - If needed, set fixed URL:
      npm run mobile:set-url -- --url http://192.168.1.10:8001
  - For release/internet builds, use HTTPS fixed URL.
