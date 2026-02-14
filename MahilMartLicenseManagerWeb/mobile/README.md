# Mobile App Wrapper (Android + iOS)

This folder creates a native mobile app wrapper for the Django web app using Capacitor.

## Prerequisites

- Node.js 20+
- Android Studio (for APK/AAB)
- Xcode on macOS (for iOS build)
- Running Django server over reachable URL

## 1) Install Dependencies

```powershell
cd mobile
npm install
```

## 2) Set Web App URL

Use your deployed HTTPS URL (recommended):

```powershell
npm run mobile:set-url -- --url https://your-domain.example.com
```

For local LAN testing:

```powershell
npm run mobile:set-url -- --url http://192.168.1.10:8001
```

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

- `http://` URL requires Android cleartext enabled; this is handled automatically by `set-mobile-url.mjs`.
- For production mobile apps, use `https://`.
- iOS release build requires macOS + Apple Developer setup.
