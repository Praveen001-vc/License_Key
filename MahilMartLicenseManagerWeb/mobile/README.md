# Mobile App Wrapper (Android + iOS)

This folder creates a native mobile app wrapper for the Django web app using Capacitor.

## Prerequisites

- Node.js 20+
- Android Studio (for APK/AAB)
- Xcode on macOS (for iOS build)
- Running Django server on your PC (default port 8001)

## 1) Install Dependencies

```powershell
cd mobile
npm install
```

## 2) Server Connection Mode

Auto-detect mode (recommended for local network IP changes):

```powershell
npm run mobile:set-auto
```

Optional fixed URL mode:

```powershell
npm run mobile:set-url -- --url http://192.168.1.10:8001
```

How auto-detect works:

- App checks last working server URL.
- If not reachable, it scans local LAN on port `8001`.
- It calls `/healthz/` and connects automatically when found.

## 3) Generate Native Projects

### Android

```powershell
npm run mobile:add:android
npm run cap:sync
npm run mobile:open:android
```

In Android Studio:

- Build `APK` from `Build > Build Bundle(s) / APK(s) > Build APK(s)`.
- For Play Store, build `AAB` from `Build > Generate Signed Bundle / APK`.

### iOS (macOS only)

```bash
npm run mobile:add:ios
npm run cap:sync
npm run mobile:open:ios
```

In Xcode:

- Select signing team.
- Build archive and export via TestFlight/App Store.

## Notes

- For production internet deployment, prefer fixed HTTPS URL.
- For local PC network usage, auto mode handles changing IP.
- iOS release build requires macOS + Apple Developer setup.
