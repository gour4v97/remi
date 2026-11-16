<#
.SYNOPSIS
    One-Line Automated Bootstrap & Installer for Remi Suite on Windows.
.DESCRIPTION
    Installs prerequisites, provisions dedicated Python virtual environment,
    downloads whisper.cpp CUDA/CPU binaries, fetches the recommended STT model,
    and sets up desktop shortcuts.
.EXAMPLE
    irm https://raw.githubusercontent.com/gour4v97/remi/main/scripts/install.ps1 | iex
#>

[CmdletBinding()]
param(
    [string]$InstallDir = "$env:LOCALAPPDATA\Programs\Remi",
    [string]$Model = "large-v3-turbo-q5_0"
)

$ErrorActionPreference = "Stop"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "🎙️  Remi Suite: Voice-First Windows AI Agent Installer" -ForegroundColor Cyan
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
    Write-Host "`n[1/5] Python not detected. Installing via winget..." -ForegroundColor Yellow
    winget install --id Python.Python.3.12 -e --silent --accept-package-agreements --accept-source-agreements
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    $PythonExe = "python"
} else {
    Write-Host "`n[1/5] Python detected: $(& $PythonExe --version)" -ForegroundColor Green
}

# 2. Setup Directory and Virtual Environment
Write-Host "`n[2/5] Creating application environment at $InstallDir..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
$VenvDir = Join-Path $InstallDir "venv"

if (-not (Test-Path $VenvDir)) {
    & $PythonExe -m venv $VenvDir
}

$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$VenvPip = Join-Path $VenvDir "Scripts\pip.exe"

# 3. Install Remi & Dependencies
Write-Host "`n[3/5] Installing Remi dependencies into virtual environment..." -ForegroundColor Yellow
& $VenvPython -m pip install --upgrade pip --quiet
& $VenvPip install -r "$PSScriptRoot\..\python\requirements.txt" --quiet

# 4. Download and setup model
Write-Host "`n[4/5] Initializing whisper.cpp engine and model ($Model)..." -ForegroundColor Yellow
$ScriptRoot = Split-Path -Parent $PSScriptRoot
& $VenvPython -c "import sys; sys.path.insert(0, r'$ScriptRoot\src'); from remi.engine.whisper_cpp import ensure_binaries, ensure_cuda; ensure_binaries(); ensure_cuda()"

# 5. Create Desktop Launcher
Write-Host "`n[5/5] Creating desktop shortcuts..." -ForegroundColor Yellow
$WshShell = New-Object -ComObject WScript.Shell
$DesktopPath = [Environment]::GetFolderPath("Desktop")

# Shortcut for Remi Browser Voice
$ShortcutRemi = $WshShell.CreateShortcut((Join-Path $DesktopPath "Remi Voice Browser.lnk"))
$ShortcutRemi.TargetPath = Join-Path $VenvDir "Scripts\pythonw.exe"
$ShortcutRemi.Arguments = "-m remi.agents.browser_agent"
$ShortcutRemi.WorkingDirectory = $InstallDir
$ShortcutRemi.Description = "Remi Voice-Controlled Browser Assistant (Ctrl+Alt+B)"
$ShortcutRemi.Save()

# Shortcut for Voice Trans Dictation
$ShortcutDict = $WshShell.CreateShortcut((Join-Path $DesktopPath "Voice Trans Dictation.lnk"))
$ShortcutDict.TargetPath = Join-Path $VenvDir "Scripts\pythonw.exe"
$ShortcutDict.Arguments = "-m remi.agents.dictation_agent"
$ShortcutDict.WorkingDirectory = $InstallDir
$ShortcutDict.Description = "Voice Trans Universal Push-to-Talk Dictation (Ctrl+Alt+Space)"
$ShortcutDict.Save()

Write-Host "`n==========================================================" -ForegroundColor Green
Write-Host "✅ Remi Suite installation completed successfully!" -ForegroundColor Green
Write-Host "   • Press Ctrl+Alt+B for Voice Browser Assistant" -ForegroundColor White
Write-Host "   • Press Ctrl+Alt+Space for Universal Dictation" -ForegroundColor White
Write-Host "   • Run 'remi doctor' or 'remi bench' anytime" -ForegroundColor White
Write-Host "==========================================================" -ForegroundColor Green
