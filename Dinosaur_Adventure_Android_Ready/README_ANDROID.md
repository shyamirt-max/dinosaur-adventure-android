# Dinosaur Adventure Android build package

## Recommended: build online with GitHub Actions
1. Create a new empty GitHub repository.
2. Upload the CONTENTS of this folder, including the hidden `.github` folder.
3. Commit to the `main` branch.
4. Open **Actions** > **Build Android APK** > **Run workflow**.
5. When the job finishes, open the run and download **dinosaur-adventure-debug-apk** from **Artifacts**.
6. Extract the artifact ZIP and copy the APK to an Android phone.
7. On the phone, allow installation from the browser/file-manager used to open the APK, then install it.

The first cloud build may take 20-60 minutes because Android SDK/NDK and Python dependencies are prepared. Subsequent cached builds are often faster.

## Local build using WSL2 Ubuntu
From the project folder in Ubuntu/WSL:

    chmod +x build_local_wsl.sh
    ./build_local_wsl.sh

The debug APK will be written under `bin/`.

## Android configuration
- Orientation: landscape
- Fullscreen: enabled
- Architectures: arm64-v8a and armeabi-v7a
- Minimum Android API: 24 (Android 7.0)
- Runtime permissions: none requested
- Save data: app-private writable storage
- Python dependency: pygame-ce through the SDL2 bootstrap

## Important test points
- Install the debug APK on a physical Android phone.
- Check touch buttons: START, JUMP, SHOOT, PAUSE and boss controls.
- Confirm audio starts and does not crash when audio is unavailable.
- Create an account, close/reopen the app, and confirm progress is retained.
- Check display scaling and text on phones with different aspect ratios.

## If the GitHub build fails
Open the failed workflow step, copy the first error block plus the final 100 log lines, and use those logs for diagnosis. Do not repeatedly change Python, Cython, Gradle or NDK versions without using the reported failure as the basis.
