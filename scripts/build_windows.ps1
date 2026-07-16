param(
    [string]$Python = ""
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $projectRoot

if ([string]::IsNullOrWhiteSpace($Python)) {
    $venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
    $Python = if (Test-Path $venvPython) { $venvPython } else { "python" }
}
Write-Host "Using Python: $Python"

$pandocCommand = Get-Command pandoc.exe -ErrorAction SilentlyContinue
if (-not $pandocCommand) {
    throw "Pandoc was not found. Install Pandoc first and reopen PowerShell."
}
$pandocPath = $pandocCommand.Source
$pandocVersion = (& $pandocPath --version | Select-Object -First 1)
Write-Host "Bundling $pandocVersion from $pandocPath"

& $Python -m pip install -e ".[gui]" pyinstaller
& $Python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --name MathFixer `
    --paths src `
    --add-binary "$pandocPath;." `
    --add-data "src/mathfixer/resources/mathfixer-logo.svg;mathfixer/resources" `
    --add-data "THIRD_PARTY_NOTICES.md;." `
    --collect-all PySide6 `
    scripts/mathfixer_gui.py

Copy-Item THIRD_PARTY_NOTICES.md dist/THIRD_PARTY_NOTICES.md -Force
Write-Host "Build completed: dist/MathFixer.exe"
Write-Host "Pandoc is embedded; the destination computer does not need a separate Pandoc installation."
