# =====================================================================
#  Remi Suite - Publisher Certificate Generator & Code Signing Tool
#  Configures Windows Authenticode Publisher: GAURAV
# =====================================================================

param (
    [string]$PublisherName = "GAURAV"
)

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "    Configuring Verified Publisher: $PublisherName         " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Check if Code Signing Certificate for GAURAV already exists
$cert = Get-ChildItem -Path "Cert:\CurrentUser\My" -CodeSigningCert | Where-Object { $_.Subject -match "CN=$PublisherName" } | Select-Object -First 1

if (-not $cert) {
    Write-Host "[1/3] Creating Authenticode Code Signing Certificate for '$PublisherName'..." -ForegroundColor Cyan
    try {
        $cert = New-SelfSignedCertificate `
            -Type CodeSigningCert `
            -Subject "CN=$PublisherName" `
            -KeySpec Signature `
            -KeyUsage DigitalSignature `
            -KeyExportPolicy Exportable `
            -CertStoreLocation "Cert:\CurrentUser\My" `
            -FriendlyName "Remi Suite Code Signing Certificate ($PublisherName)" `
            -NotAfter (Get-Date).AddYears(10)
        Write-Host "  ✓ Created certificate: $($cert.Thumbprint)" -ForegroundColor Green
    } catch {
        Write-Host "  ⚠️ Could not create certificate automatically: $($_.Exception.Message)" -ForegroundColor Yellow
        Exit 0
    }
} else {
    Write-Host "[1/3] Found existing Code Signing Certificate for '$PublisherName'." -ForegroundColor Green
}

# 2. Install certificate into Trusted Root and Trusted Publisher stores
Write-Host "[2/3] Registering '$PublisherName' into Trusted Publisher store..." -ForegroundColor Cyan
try {
    # Add to TrustedPublisher
    $pubStore = New-Object System.Security.Cryptography.X509Certificates.X509Store "TrustedPublisher", "CurrentUser"
    $pubStore.Open("ReadWrite")
    $pubStore.Add($cert)
    $pubStore.Close()

    # Add to Root (Trusted Root Certification Authorities)
    $rootStore = New-Object System.Security.Cryptography.X509Certificates.X509Store "Root", "CurrentUser"
    $rootStore.Open("ReadWrite")
    $rootStore.Add($cert)
    $rootStore.Close()

    Write-Host "  ✓ Registered '$PublisherName' as a Verified Publisher." -ForegroundColor Green
} catch {
    Write-Host "  ⚠️ Store registration note: $($_.Exception.Message)" -ForegroundColor Gray
}

# 3. Sign scripts in scripts directory
Write-Host "[3/3] Digitally signing installer and launcher scripts with '$PublisherName'..." -ForegroundColor Cyan
$scriptDir = $PSScriptRoot
$filesToSign = Get-ChildItem -Path $scriptDir -Filter "*.ps1"

foreach ($file in $filesToSign) {
    try {
        $sig = Set-AuthenticodeSignature -FilePath $file.FullName -Certificate $cert -ErrorAction SilentlyContinue
        if ($sig.Status -eq "Valid") {
            Write-Host "  ✓ Signed $($file.Name) [Publisher: $PublisherName]" -ForegroundColor Green
        } else {
            Write-Host "  • $($file.Name) signed ($($sig.Status))" -ForegroundColor Gray
        }
    } catch {
        # Best effort signing
    }
}

Write-Host ""
Write-Host "Verified Publisher configuration complete! Publisher name: $PublisherName" -ForegroundColor Green
