---
name: android-apk-builder
description: Builds an Android APK from a given project directory in the sandbox environment. This skill handles Android SDK installation, Java version management, Gradle wrapper updates, and APK compilation, providing a ready-to-install APK file.
license: Complete terms in LICENSE.txt
---

# Android APK Builder

This skill automates the process of building an Android Application Package (APK) from a provided Android project within the sandbox environment. It is designed to streamline the build process by handling common prerequisites such as Android SDK installation, Java Development Kit (JDK) configuration, and Gradle setup.

## Usage

To use this skill, ensure your Android project is unzipped into a directory (e.g., `~/ble-tester`). Then, execute the `build_apk.py` script located in the `scripts/` directory of this skill. The script will perform the following steps:

1.  **Install Android SDK**: Downloads and installs a minimal set of Android command-line tools and necessary platforms.
2.  **Install Java 17**: Installs OpenJDK 17 and configures it as the default Java environment.
3.  **Update Gradle Wrapper**: Updates the project's Gradle wrapper to a compatible version (8.5) to ensure successful builds with Java 17.
4.  **Configure `gradle.properties`**: Adds `android.useAndroidX=true` and `android.enableJetifier=true` to the project's `gradle.properties` file to resolve common build issues with AndroidX dependencies.
5.  **Build Debug APK**: Compiles the Android project to generate a debug APK.
6.  **Locate and Copy APK**: Finds the generated APK file and copies it to `~/ble-tester.apk` for easy access.

### Example Execution

Assuming your Android project is located at `~/ble-tester`:

```bash
python3 /home/ubuntu/skills/android-apk-builder/scripts/build_apk.py
```

Upon successful execution, the final APK will be available at `/home/ubuntu/ble-tester.apk`.

## Troubleshooting

-   **Build Failures**: If the build fails, review the output for specific error messages. Common issues are often related to missing dependencies or incorrect project configurations. The script attempts to address the most common ones.
-   **Gradle Version**: If your project requires a different Gradle version, you can modify the `update_gradle_wrapper` function in `build_apk.py`.
-   **Android SDK Components**: If additional Android SDK components are needed, modify the `install_android_sdk` function in `build_apk.py` to include them in the `sdkmanager` command.
