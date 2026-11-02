# Water Tank System V5 - Native Android Application

A high-performance, real-time native Android application for monitoring and controlling the **Water Tank Management System V5** (Master ESP32, Slave 1 ESP32, Slave 2 ESP32, and Flask backend).

---

## 🌟 Key Features

1. **Live Water Tank Visualization**:
   - Real-time water percentage with dynamic color-coded fill bars for Tanks 1, 2, 3, and 4.
   - Ultrasonic distance reading in centimeters.
   - Sensor health status (`SENSOR OK` / `SENSOR ERROR`).

2. **Motorized Valve Status**:
   - Exact V5 status labels: **`Opening`**, **`Open`**, **`Closing`**, **`Close`**.
   - Distinct color-coded pills (Amber pulse for opening, Green for open, Indigo pulse for closing, Slate for close).

3. **Automation Controls**:
   - Large, responsive **START FILLING** and **STOP ALL** buttons with immediate safety interlocks.
   - Physical vs Dashboard tank selection priority indication.

4. **Hardware Node Diagnostics**:
   - Real-time connectivity and IP address tracking for **Master ESP32**, **Slave 1 ESP32 (Sensors)**, and **Slave 2 ESP32 (Valves)**.

5. **Faults & Troubleshooting Sheet**:
   - Full diagnostic dashboard showing active and resolved faults, root cause analysis, and step-by-step remediation procedures.

6. **Configurable Server IP**:
   - Built-in settings screen to configure the Flask Server URL (default: `http://water.nubeera.com`) with an instant "Test Ping" tool.

---

## 🛠 Project Architecture

- **Language**: Kotlin 1.9
- **Architecture**: MVVM (Model-View-ViewModel) + Android Jetpack
- **Networking**: Retrofit 2 + OkHttp 3 + Gson
- **Concurrency**: Kotlin Coroutines & StateFlow / LiveData
- **UI & Layout**: Material Design 3 Components, ViewBinding, SwipeRefreshLayout
- **Cleartext Traffic Support**: Configured in `network_security_config.xml` to allow seamless local LAN communication.

---

## 📱 How to Generate the APK

### Method 1: Android Studio (Recommended — 1 Click)
1. Open **Android Studio**.
2. Select **Open an Existing Project** and choose the `WaterTankApp` folder:
   `D:\nubeera\iot\arshadbhaijaan\V5\WaterTankApp`
3. Wait for Gradle sync to complete (Android Studio will automatically download any required SDK platforms and dependencies).
4. Click **Build** in the top menu &rarr; **Build Bundle(s) / APK(s)** &rarr; **Build APK(s)**.
5. Once complete, click **locate** in the popup notification to get your `app-debug.apk` ready to install on any Android phone!

### Method 2: Command Line (PowerShell / Terminal)
If you have JDK 17 and the Android SDK installed:
```powershell
cd WaterTankApp
.\gradlew.bat assembleDebug
```
The output APK will be located at:
`WaterTankApp/app/build/outputs/apk/debug/app-debug.apk`

### Method 3: GitHub Actions (Automated Cloud Build)
This repository includes an automated GitHub Actions CI/CD workflow at [`.github/workflows/build-apk.yml`](../.github/workflows/build-apk.yml).
When pushed to GitHub:
1. GitHub automatically spins up a cloud builder with Android SDK & JDK 17 pre-configured.
2. It compiles the project and generates `WaterTankV5-debug-apk`.
3. You can download the `.apk` directly from the **Actions** tab of your repository!

