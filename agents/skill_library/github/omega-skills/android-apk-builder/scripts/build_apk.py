
import os
import subprocess

def run_command(command, cwd=None):
    print(f"Running command: {command}")
    process = subprocess.run(command, shell=True, cwd=cwd, capture_output=True, text=True)
    if process.returncode != 0:
        print(f"Error: {process.stderr}")
        raise Exception(f"Command failed: {command}")
    print(f"Output: {process.stdout}")
    return process.stdout

def install_android_sdk():
    print("Installing Android SDK...")
    os.makedirs(os.path.expanduser("~/android-sdk"), exist_ok=True)
    run_command("wget https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip", cwd=os.path.expanduser("~/android-sdk"))
    run_command("unzip commandlinetools-linux-11076708_latest.zip", cwd=os.path.expanduser("~/android-sdk"))
    os.makedirs(os.path.expanduser("~/android-sdk/cmdline-tools/latest"), exist_ok=True)
    run_command("mv cmdline-tools/* cmdline-tools/latest/ || true", cwd=os.path.expanduser("~/android-sdk"))
    run_command("rm commandlinetools-linux-11076708_latest.zip", cwd=os.path.expanduser("~/android-sdk"))

    os.environ["ANDROID_HOME"] = os.path.expanduser("~/android-sdk")
    os.environ["PATH"] = f"{os.environ.get("PATH")}:{os.environ["ANDROID_HOME"]}/cmdline-tools/latest/bin"

    run_command("yes | sdkmanager --sdk_root=$ANDROID_HOME --licenses")
    run_command("sdkmanager --sdk_root=$ANDROID_HOME \"platform-tools\" \"platforms;android-34\" \"build-tools;34.0.0\"")

def install_java17():
    print("Installing Java 17...")
    run_command("sudo apt update")
    run_command("sudo apt install -y openjdk-17-jdk")
    os.environ["JAVA_HOME"] = "/usr/lib/jvm/java-17-openjdk-amd64"
    os.environ["PATH"] = f"{os.environ.get("PATH")}:{os.environ["JAVA_HOME"]}/bin"
    run_command("java -version")

def update_gradle_wrapper(project_path):
    print("Updating Gradle wrapper...")
    run_command("gradle wrapper --gradle-version 8.5", cwd=project_path)

def configure_gradle_properties(project_path):
    print("Configuring gradle.properties...")
    gradle_properties_path = os.path.join(project_path, "gradle.properties")
    with open(gradle_properties_path, "w") as f:
        f.write("android.useAndroidX=true\n")
        f.write("android.enableJetifier=true\n")

def build_apk(project_path):
    print("Building APK...")
    os.environ["PATH"] = f"{os.environ.get("PATH")}:{os.environ["ANDROID_HOME"]}/platform-tools"
    run_command("./gradlew assembleDebug", cwd=project_path)
    apk_path = run_command("find . -name \"*.apk\"", cwd=project_path).strip()
    if apk_path:
        final_apk_path = os.path.expanduser("~/ble-tester.apk")
        run_command(f"cp {apk_path} {final_apk_path}", cwd=project_path)
        print(f"APK built successfully and copied to {final_apk_path}")
        return final_apk_path
    else:
        raise Exception("APK not found after build.")

if __name__ == "__main__":
    project_root = os.path.expanduser("~/ble-tester") # Assuming the project is unzipped here
    install_android_sdk()
    install_java17()
    update_gradle_wrapper(project_root)
    configure_gradle_properties(project_root)
    final_apk = build_apk(project_root)
    print(f"Final APK available at: {final_apk}")
