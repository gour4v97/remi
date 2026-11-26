<#
.SYNOPSIS
    One-Line Automated Bootstrap & Installer for Remi Suite on Windows.
.DESCRIPTION
    Installs prerequisites, provisions dedicated Python virtual environment,
    installs Remi Suite, configures Publisher (Gaurav Manjhi), downloads
    whisper.cpp CUDA/CPU binaries and the recommended STT model,
    and sets up branded desktop shortcuts.
.EXAMPLE
    irm https://raw.githubusercontent.com/gour4v97/remi/main/scripts/install.ps1 | iex
#>

[CmdletBinding()]
param(
    [string]$InstallDir = "$env:LOCALAPPDATA\Programs\Remi",
    [string]$Model = "large-v3-turbo-q5_0",
    [string]$PublisherName = "Gaurav Manjhi"
)

$ErrorActionPreference = "Stop"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Remi Suite: Voice-First Windows AI Agent Installer" -ForegroundColor Cyan
Write-Host "  Publisher: $PublisherName" -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Check Python
$PythonExe = $null
if (Get-Command py -ErrorAction SilentlyContinue) {
    $PythonExe = "py"
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $PythonExe = "python"
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    $PythonExe = "python3"
}

if (-not $PythonExe) {
    Write-Host "`n[1/6] Python not detected. Installing via winget..." -ForegroundColor Yellow
    winget install --id Python.Python.3.12 -e --silent --accept-package-agreements --accept-source-agreements
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    $PythonExe = "python"
} else {
    Write-Host "`n[1/6] Python detected: $(& $PythonExe --version)" -ForegroundColor Green
}

# 2. Resolve source directory (local checkout or remote bootstrap via irm | iex)
Write-Host "`n[2/6] Preparing application directory at $InstallDir..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null

$LocalRepoRoot = if ($PSScriptRoot) { Split-Path -Parent $PSScriptRoot } else { "" }
if ($LocalRepoRoot -and (Test-Path (Join-Path $LocalRepoRoot "pyproject.toml"))) {
    $AppDir = $LocalRepoRoot
} else {
    $AppDir = Join-Path $InstallDir "app"
    if (-not (Test-Path (Join-Path $AppDir "pyproject.toml"))) {
        $ZipFile = Join-Path $env:TEMP "remi-main.zip"
        $ExtractDir = Join-Path $env:TEMP "remi-extract"
        Invoke-WebRequest -Uri "https://github.com/gour4v97/remi/archive/refs/heads/main.zip" -OutFile $ZipFile
        if (Test-Path $ExtractDir) { Remove-Item -Recurse -Force $ExtractDir }
        Expand-Archive -Path $ZipFile -DestinationPath $ExtractDir -Force
        if (Test-Path $AppDir) { Remove-Item -Recurse -Force $AppDir }
        Move-Item -Path (Join-Path $ExtractDir "remi-main") -Destination $AppDir
        Remove-Item -Force $ZipFile -ErrorAction SilentlyContinue
        Remove-Item -Recurse -Force $ExtractDir -ErrorAction SilentlyContinue
    }
}

# 3. Provision Virtual Environment and Install Remi Package
Write-Host "`n[3/6] Installing Remi Suite into virtual environment..." -ForegroundColor Yellow
$VenvDir = Join-Path $InstallDir "venv"
if (-not (Test-Path $VenvDir)) {
    & $PythonExe -m venv $VenvDir
}

$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$VenvPythonW = Join-Path $VenvDir "Scripts\pythonw.exe"
$VenvPip = Join-Path $VenvDir "Scripts\pip.exe"

& $VenvPython -m pip install --upgrade pip --quiet
& $VenvPip install -e $AppDir --quiet

# 4. Configure Publisher Certificate (best-effort)
Write-Host "`n[4/6] Configuring Windows Publisher ($PublisherName)..." -ForegroundColor Yellow
$CertScript = Join-Path $AppDir "scripts\setup-certificate.ps1"
if (Test-Path $CertScript) {
    try {
        & $CertScript -PublisherName $PublisherName
    } catch {
        Write-Host "  Note: Publisher certificate setup skipped ($($_.Exception.Message))" -ForegroundColor Gray
    }
}

# 5. Download whisper.cpp binaries, CUDA (if GPU), and STT model
Write-Host "`n[5/6] Initializing whisper.cpp engine and model ($Model)..." -ForegroundColor Yellow
& $VenvPython -c "from remi.engine.whisper_cpp import ensure_binaries, ensure_cuda; ensure_binaries(); ensure_cuda()"
& $VenvPython -m remi model download $Model

# 6. Create Branded Desktop Shortcuts
Write-Host "`n[6/6] Creating desktop shortcuts..." -ForegroundColor Yellow
$WshShell = New-Object -ComObject WScript.Shell
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$IconPath = Join-Path $AppDir "assets\remi.ico"

# Shortcut for Remi Browser Voice
$ShortcutRemi = $WshShell.CreateShortcut((Join-Path $DesktopPath "Remi Voice Browser.lnk"))
$ShortcutRemi.TargetPath = $VenvPythonW
$ShortcutRemi.Arguments = "-m remi start"
$ShortcutRemi.WorkingDirectory = $AppDir
$ShortcutRemi.Description = "Remi Voice-Controlled Browser Assistant by $PublisherName (Ctrl+Alt+B)"
if (Test-Path $IconPath) { $ShortcutRemi.IconLocation = "$IconPath,0" }
$ShortcutRemi.Save()

# Shortcut for Voice Trans Dictation
$ShortcutDict = $WshShell.CreateShortcut((Join-Path $DesktopPath "Voice Trans Dictation.lnk"))
$ShortcutDict.TargetPath = $VenvPythonW
$ShortcutDict.Arguments = "-m remi dictation"
$ShortcutDict.WorkingDirectory = $AppDir
$ShortcutDict.Description = "Voice Trans Push-to-Talk Dictation by $PublisherName (Ctrl+Alt+Space)"
if (Test-Path $IconPath) { $ShortcutDict.IconLocation = "$IconPath,0" }
$ShortcutDict.Save()

Write-Host "`n==========================================================" -ForegroundColor Green
Write-Host "Remi Suite installation completed successfully!" -ForegroundColor Green
Write-Host "   - Publisher: $PublisherName" -ForegroundColor White
Write-Host "   - Press Ctrl+Alt+B for Voice Browser Assistant" -ForegroundColor White
Write-Host "   - Press Ctrl+Alt+Space for Universal Dictation" -ForegroundColor White
Write-Host "   - Run 'remi doctor' or 'remi bench' anytime" -ForegroundColor White
Write-Host "==========================================================" -ForegroundColor Green
