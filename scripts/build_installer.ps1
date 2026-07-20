param(
    [string]$Version = "2.0.8",
    [string]$CertificatePath = "",
    [string]$CertificatePassword = "",
    [string]$TimestampUrl = "http://timestamp.digicert.com"
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$app = Join-Path $projectRoot "dist\MathFixer.exe"
$installer = Join-Path $projectRoot "dist\MathFixer-Setup.exe"
$definition = Join-Path $PSScriptRoot "mathfixer.iss"
if (-not (Test-Path $app)) {
    throw "Build dist\MathFixer.exe before creating the installer."
}

$signTool = Get-Command signtool.exe -ErrorAction SilentlyContinue
function Sign-Artifact([string]$Path) {
    if ([string]::IsNullOrWhiteSpace($CertificatePath)) {
        return
    }
    if (-not (Test-Path $CertificatePath)) {
        throw "The configured code-signing certificate was not found."
    }
    if (-not $signTool) {
        throw "signtool.exe is required when a signing certificate is configured."
    }
    & $signTool.Source sign /fd SHA256 /f $CertificatePath /p $CertificatePassword /tr $TimestampUrl /td SHA256 $Path
    if ($LASTEXITCODE -ne 0) {
        throw "Authenticode signing failed for $Path"
    }
}

Sign-Artifact $app
$compilerCommand = Get-Command ISCC.exe -ErrorAction SilentlyContinue
$compilerPath = if ($compilerCommand) { $compilerCommand.Source } else { "" }
if ([string]::IsNullOrWhiteSpace($compilerPath)) {
    $candidate = Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"
    if (Test-Path $candidate) {
        $compilerPath = $candidate
    } else {
        throw "Inno Setup 6 was not found."
    }
}
& $compilerPath "/DMyAppVersion=$Version" $definition
if ($LASTEXITCODE -ne 0 -or -not (Test-Path $installer)) {
    throw "Inno Setup failed to create MathFixer-Setup.exe"
}
Sign-Artifact $installer

if ([string]::IsNullOrWhiteSpace($CertificatePath)) {
    Write-Warning "Installer created without Authenticode signing; configure a certificate for public releases."
} else {
    Write-Host "Signed installer created: $installer"
}
