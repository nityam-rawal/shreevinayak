# Android Wrapper Notes

This project is currently a Python web app, not a native Android app.

To make a native APK, the easiest practical path is:

1. Deploy this app to a public URL.
2. Create an Android WebView wrapper or Trusted Web Activity.
3. Build APK from Android Studio.

## Recommended wrapper behavior

- Open deployed app URL inside a WebView
- Allow microphone permission for browser voice input
- Keep app fullscreen
- Optional splash screen and launcher icon

## Blockers on this machine

- No Java installed
- No Gradle installed
- No Android SDK / Android Studio detected

## Suggested next deployment target

- Render or Railway for the Python app
- Then Android Studio wrapper for APK
