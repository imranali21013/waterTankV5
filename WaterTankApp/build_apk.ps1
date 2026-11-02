<#
.SYNOPSIS
    Build Script for Water Tank V5 Native Android APK
.DESCRIPTION
    Checks for JDK and Android SDK, invokes Gradle, and outputs the debug APK.
#>

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host " Water Tank System V5 - Android APK Build " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $ScriptDir

# 1. Check for Java
$JavaExe = (Get-Command java -ErrorAction SilentlyContinue)?.Source
if (-not $JavaExe -and $env:JAVA_HOME) {
    $JavaExe = Join-Path $env:JAVA_HOME "bin\java.exe"
}

if (-not $JavaExe -or -not (Test-Path $JavaExe)) {
    Write-Host "`n[!] Java Development Kit (JDK 17) is required to compile Android APKs." -ForegroundColor Yellow
    Write-Host "Please ensure JDK 17+ is installed and JAVA_HOME is configured." -ForegroundColor Yellow
    Write-Host "Alternatively, open this folder in Android Studio for 1-click APK generation." -ForegroundColor Green
    exit 1
}

Write-Host "[+] Found Java: $JavaExe" -ForegroundColor Green

# 2. Check for Android SDK
$AndroidHome = $env:ANDROID_HOME
if (-not $AndroidHome) { $AndroidHome = $env:ANDROID_SDK_ROOT }
if (-not $AndroidHome) {
    $DefaultSdk = "$env:LOCALAPPDATA\Android\Sdk"
    if (Test-Path $DefaultSdk) { $AndroidHome = $DefaultSdk }
}

if (-not $AndroidHome -or -not (Test-Path $AndroidHome)) {
    Write-Host "`n[!] Android SDK not found in environment." -ForegroundColor Yellow
    Write-Host "Recommended: Open the 'WaterTankApp' folder directly in Android Studio." -ForegroundColor Cyan
    Write-Host "Android Studio will auto-download all SDK dependencies and build the APK in 1 click." -ForegroundColor Cyan
    exit 1
}

Write-Host "[+] Found Android SDK: $AndroidHome" -ForegroundColor Green

# 3. Execute Gradle Build
Write-Host "`n[*] Starting Gradle build (assembleDebug)..." -ForegroundColor Cyan
if (Test-Path ".\gradlew.bat") {
    .\gradlew.bat assembleDebug
} else {
    gradle assembleDebug
}

$ApkPath = ".\app\build\outputs\apk\debug\app-debug.apk"
if (Test-Path $ApkPath) {
    Write-Host "`n[SUCCESS] APK Generated Successfully!" -ForegroundColor Green
    Write-Host "APK Location: $(Resolve-Path $ApkPath)" -ForegroundColor White
} else {
    Write-Host "`n[ERROR] Build finished but APK was not found at expected path." -ForegroundColor Red
}

