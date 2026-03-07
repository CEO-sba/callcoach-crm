# CallCoach Android Build Guide

## Prerequisites

1. Node.js 18+ and npm
2. Java Development Kit (JDK) 17
3. Android Studio with:
   - Android SDK 34
   - Android SDK Build-Tools 34.0.0
   - NDK 25.1.8937393
   - Android Emulator (optional, for testing)
4. Set environment variables:
   ```
   export ANDROID_HOME=$HOME/Library/Android/sdk    # macOS
   export ANDROID_HOME=$HOME/Android/Sdk            # Linux
   export PATH=$PATH:$ANDROID_HOME/emulator
   export PATH=$PATH:$ANDROID_HOME/platform-tools
   ```

## Setup

```bash
cd mobile
npm install
```

## Debug Build (Development)

### Run on connected device or emulator:
```bash
npm run android
```

### Or build debug APK manually:
```bash
cd android
./gradlew assembleDebug
```

Debug APK location: `android/app/build/outputs/apk/debug/app-debug.apk`

## Release Build (Production)

### Step 1: Generate a release signing keystore
```bash
cd android/app
keytool -genkeypair -v -storetype PKCS12 \
  -keystore callcoach-release.keystore \
  -alias callcoach-key \
  -keyalg RSA -keysize 2048 -validity 10000 \
  -storepass callcoach2024 -keypass callcoach2024
```

### Step 2: Build release APK
```bash
cd android
./gradlew assembleRelease
```

Release APK: `android/app/build/outputs/apk/release/app-release.apk`

### Step 3: Build AAB for Play Store
```bash
cd android
./gradlew bundleRelease
```

AAB file: `android/app/build/outputs/bundle/release/app-release.aab`

## Testing on Device

### Install debug APK via ADB:
```bash
adb install android/app/build/outputs/apk/debug/app-debug.apk
```

### Required permissions to grant manually (Settings > Apps > CallCoach > Permissions):
- Phone (for making calls)
- Microphone (for recording)
- Storage (for saving recordings)

## Troubleshooting

### Build fails with "SDK not found"
Create `android/local.properties`:
```
sdk.dir=/path/to/Android/Sdk
```

### Metro bundler not starting
```bash
npm start -- --reset-cache
```

### Clean build
```bash
npm run android:clean
cd ..
npm start -- --reset-cache
```

## App Configuration

- **Server URL**: Set in `src/services/api.ts` (currently `https://callcoachsba.com`)
- **App ID**: `com.callcoachmobile` (change in `android/app/build.gradle`)
- **Version**: Update `versionCode` and `versionName` in `android/app/build.gradle`
