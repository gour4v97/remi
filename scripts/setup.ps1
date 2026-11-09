# =====================================================================
#  Remi Suite - Automated Windows Setup & Desktop Shortcut Installer
#  Publisher: GAURAV
# =====================================================================

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "         Remi Voice AI Suite - Windows Setup              " -ForegroundColor Cyan
Write-Host "         Publisher: GAURAV                                " -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

# 0. Configure Verified Publisher (GAURAV)
$certScript = Join-Path $PSScriptRoot "setup-certificate.ps1"
if (Test-Path $certScript) {
    try {
        & $certScript -PublisherName "GAURAV"
    } catch {
        Write-Host "Publisher certificate setup note: $($_.Exception.Message)" -ForegroundColor Gray
    }
}

# 1. Check Python
$pythonCmd = Get-Command "python" -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    $pythonCmd = Get-Command "py" -ErrorAction SilentlyContinue
}

if (-not $pythonCmd) {
    Write-Host "Error: Python was not found in PATH." -ForegroundColor Red
    Write-Host "Please install Python 3.11+ from https://www.python.org/downloads/ and check 'Add Python to PATH'." -ForegroundColor Yellow
    Exit 1
}

$pyExe = $pythonCmd.Source
Write-Host "[1/4] Found Python: $pyExe" -ForegroundColor Green

# 2. Install dependencies in editable mode
Write-Host "[2/4] Installing dependencies via pip..." -ForegroundColor Cyan
& $pyExe -m pip install --upgrade pip
& $pyExe -m pip install -e .

if ($LASTEXITCODE -ne 0) {
    Write-Host "Warning: pip installation encountered an error." -ForegroundColor Yellow
}

# 3. Run interactive setup wizard
Write-Host "[3/4] Running Remi setup wizard..." -ForegroundColor Cyan
& $pyExe -m remi setup

# 4. Create Desktop Shortcuts
Write-Host "[4/4] Creating Windows Desktop Shortcuts..." -ForegroundColor Cyan
try {
    $WshShell = New-Object -ComObject WScript.Shell
    $DesktopPath = [System.Environment]::GetFolderPath([System.Environment+SpecialFolder]::Desktop)

    $rootPath = Split-Path -Parent $PSScriptRoot

    # Shortcut 1: Remi Browser
    $ShortcutRemi = $WshShell.CreateShortcut("$DesktopPath\Remi Browser.lnk")
    $ShortcutRemi.TargetPath = "$pyExe"
    $ShortcutRemi.Arguments = "-m remi start"
    $ShortcutRemi.WorkingDirectory = "$rootPath"
    $ShortcutRemi.Description = "Remi Voice-Controlled Browser"
    $ShortcutRemi.Save()

    # Shortcut 2: Voice Trans Dictation
    $ShortcutDict = $WshShell.CreateShortcut("$DesktopPath\Voice Trans Dictation.lnk")
    $ShortcutDict.TargetPath = "$pyExe"
    $ShortcutDict.Arguments = "-m remi dictation"
    $ShortcutDict.WorkingDirectory = "$rootPath"
    $ShortcutDict.Description = "Voice Trans Push-to-Talk Dictation"
    $ShortcutDict.Save()

    Write-Host "  Desktop shortcuts created successfully!" -ForegroundColor Green
} catch {
    Write-Host "  Note: Desktop shortcut creation skipped ($($_.Exception.Message))" -ForegroundColor Gray
}

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Green
Write-Host " Installation Complete! You can now start Remi anytime:   " -ForegroundColor Green
Write-Host "   - Double click 'Remi Browser' or 'Voice Trans' on Desktop" -ForegroundColor White
Write-Host "   - Or type 'remi start' in any terminal               " -ForegroundColor White
Write-Host "==========================================================" -ForegroundColor Green
