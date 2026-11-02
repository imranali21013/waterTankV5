<#
.SYNOPSIS
    Automated Android SDK Setup and APK Generator for Water Tank V5
.DESCRIPTION
    Downloads portable JDK 17, Android Command-line Tools, Gradle, installs SDK 34,
    compiles the Native Android App, and outputs the final APK.
#>

$ErrorActionPreference = "Stop"

$Workspace = "D:\nubeera\iot\arshadbhaijaan\V5"
$ToolsDir = Join-Path $Workspace ".build_tools"
$AppDir = Join-Path $Workspace "WaterTankApp"
$FinalApk = Join-Path $Workspace "WaterTankV5.apk"

if (-not (Test-Path $ToolsDir)) {
    New-Item -ItemType Directory -Path $ToolsDir -Force | Out-Null
}

Write-Host "`n========================================================" -ForegroundColor Cyan
Write-Host "  Water Tank V5 - Android Environment Setup & Build" -ForegroundColor Cyan
Write-Host "========================================================`n" -ForegroundColor Cyan

# -----------------------------------------------------------------------------
# 1. DOWNLOAD & SETUP PORTABLE OPENJDK 17
# -----------------------------------------------------------------------------
# Search if JDK was extracted in .build_tools
$SubJdk = Get-ChildItem -Path $ToolsDir -Filter "java.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
if ($SubJdk) {
    $JavaExe = $SubJdk.FullName
    $JdkDir = $SubJdk.Directory.Parent.FullName
} else {
    $JdkDir = Join-Path $ToolsDir "jdk17"
    $JavaExe = Join-Path $JdkDir "bin\java.exe"
}

if (-not (Test-Path $JavaExe)) {
    $JdkZip = Join-Path $ToolsDir "openjdk-17.zip"
    $JdkUrl = "https://aka.ms/download-jdk/microsoft-jdk-17.0.11-windows-x64.zip"

    Write-Host "[1/5] Downloading OpenJDK 17 (~170 MB)..." -ForegroundColor Yellow
    curl.exe -L -o $JdkZip $JdkUrl --progress-bar

    Write-Host "[1/5] Extracting OpenJDK 17..." -ForegroundColor Yellow
    tar.exe -xf $JdkZip -C $ToolsDir

    # Locate java.exe
    $SubJdk = Get-ChildItem -Path $ToolsDir -Filter "java.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($SubJdk) {
        $JavaExe = $SubJdk.FullName
        $JdkDir = $SubJdk.Directory.Parent.FullName
    }
    Remove-Item -Path $JdkZip -Force -ErrorAction SilentlyContinue
}

Write-Host "[+] OpenJDK 17 Ready: $JavaExe" -ForegroundColor Green
$env:JAVA_HOME = $JdkDir
$env:PATH = "$JdkDir\bin;" + $env:PATH

# -----------------------------------------------------------------------------
# 2. DOWNLOAD & SETUP ANDROID COMMAND-LINE TOOLS
# -----------------------------------------------------------------------------
$AndroidHome = Join-Path $ToolsDir "android-sdk"
$CmdlineLatest = Join-Path $AndroidHome "cmdline-tools\latest"
$SdkManagerBat = Join-Path $CmdlineLatest "bin\sdkmanager.bat"

if (-not (Test-Path $SdkManagerBat)) {
    $CmdlineZip = Join-Path $ToolsDir "commandlinetools.zip"
    $CmdlineUrl = "https://dl.google.com/android/repository/commandlinetools-win-11076708_latest.zip"

    Write-Host "`n[2/5] Downloading Android Command-Line Tools (~140 MB)..." -ForegroundColor Yellow
    curl.exe -L -o $CmdlineZip $CmdlineUrl --progress-bar

    Write-Host "[2/5] Extracting Android Command-Line Tools..." -ForegroundColor Yellow
    $TempExtract = Join-Path $ToolsDir "cmdline-temp"
    if (Test-Path $TempExtract) { Remove-Item -Path $TempExtract -Recurse -Force }
    New-Item -ItemType Directory -Path $TempExtract -Force | Out-Null
    tar.exe -xf $CmdlineZip -C $TempExtract

    # Android SDK requires cmdline-tools to be at <ANDROID_HOME>/cmdline-tools/latest/
    if (-not (Test-Path $CmdlineLatest)) {
        New-Item -ItemType Directory -Path (Split-Path -Parent $CmdlineLatest) -Force | Out-Null
    }
    Move-Item -Path (Join-Path $TempExtract "cmdline-tools") -Destination $CmdlineLatest -Force
    Remove-Item -Path $TempExtract -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -Path $CmdlineZip -Force -ErrorAction SilentlyContinue
}

Write-Host "[+] Android Command-Line Tools Ready: $SdkManagerBat" -ForegroundColor Green
$env:ANDROID_HOME = $AndroidHome
$env:ANDROID_SDK_ROOT = $AndroidHome
$env:PATH = "$CmdlineLatest\bin;$AndroidHome\platform-tools;" + $env:PATH

# -----------------------------------------------------------------------------
# 3. ACCEPT LICENSES & INSTALL ANDROID PLATFORM 34 + BUILD-TOOLS
# -----------------------------------------------------------------------------
$LicenseDir = Join-Path $AndroidHome "licenses"
if (-not (Test-Path $LicenseDir)) {
    New-Item -ItemType Directory -Path $LicenseDir -Force | Out-Null
}
# Accept standard Android SDK licenses
Set-Content -Path (Join-Path $LicenseDir "android-sdk-license") -Value "`n24333f8a63b6825ea9c5514f83c2829b004d1fee`n84831b9409646a918e30573bab4c9c91346d8abd`n"
Set-Content -Path (Join-Path $LicenseDir "android-sdk-preview-license") -Value "`n84831b9409646a918e30573bab4c9c91346d8abd`n"

$Platform34 = Join-Path $AndroidHome "platforms\android-34"
$BuildTools34 = Join-Path $AndroidHome "build-tools\34.0.0"

if (-not (Test-Path $Platform34) -or -not (Test-Path $BuildTools34)) {
    Write-Host "`n[3/5] Installing Android Platform 34 and Build-Tools 34.0.0 (~150 MB)..." -ForegroundColor Yellow
    cmd.exe /c "echo y | `"$SdkManagerBat`" --sdk_root=`"$AndroidHome`" `"platform-tools`" `"platforms;android-34`" `"build-tools;34.0.0`""
}

Write-Host "[+] Android Platform & Build Tools Ready" -ForegroundColor Green

# -----------------------------------------------------------------------------
# 4. DOWNLOAD & SETUP GRADLE
# -----------------------------------------------------------------------------
$GradleDir = Join-Path $ToolsDir "gradle-8.6"
$GradleBat = Join-Path $GradleDir "bin\gradle.bat"

if (-not (Test-Path $GradleBat)) {
    $GradleZip = Join-Path $ToolsDir "gradle-8.6-bin.zip"
    $GradleUrl = "https://services.gradle.org/distributions/gradle-8.6-bin.zip"

    Write-Host "`n[4/5] Downloading Gradle 8.6 (~130 MB)..." -ForegroundColor Yellow
    curl.exe -L -o $GradleZip $GradleUrl --progress-bar

    Write-Host "[4/5] Extracting Gradle 8.6..." -ForegroundColor Yellow
    tar.exe -xf $GradleZip -C $ToolsDir
    Remove-Item -Path $GradleZip -Force -ErrorAction SilentlyContinue
}

Write-Host "[+] Gradle Ready: $GradleBat" -ForegroundColor Green
$env:PATH = "$GradleDir\bin;" + $env:PATH

# -----------------------------------------------------------------------------
# 5. COMPILE ANDROID APPLICATION (assembleDebug)
# -----------------------------------------------------------------------------
Write-Host "`n[5/5] Building Android Application (assembleDebug)..." -ForegroundColor Yellow

# Write local.properties for Gradle
$LocalProps = Join-Path $AppDir "local.properties"
$SdkDirEscaped = $AndroidHome.Replace("\", "\\")
Set-Content -Path $LocalProps -Value "sdk.dir=$SdkDirEscaped"

Set-Location $AppDir
& "$GradleBat" assembleDebug --no-daemon

$GeneratedApk = Join-Path $AppDir "app\build\outputs\apk\debug\app-debug.apk"
if (Test-Path $GeneratedApk) {
    Copy-Item -Path $GeneratedApk -Destination $FinalApk -Force
    Write-Host "`n========================================================" -ForegroundColor Green
    Write-Host "  SUCCESS! APK Generated Successfully!" -ForegroundColor Green
    Write-Host "========================================================" -ForegroundColor Green
    Write-Host "APK File: $FinalApk" -ForegroundColor White
    Write-Host "Size: $((Get-Item $FinalApk).Length / 1MB | ForEach-Object { '{0:N2} MB' -f $_ })" -ForegroundColor White
} else {
    Write-Host "`n[ERROR] Build finished but APK was not found at $GeneratedApk" -ForegroundColor Red
    exit 1
}

