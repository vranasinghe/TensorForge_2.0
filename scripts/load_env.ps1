# Dot-source this file: loads API_KEY from the git-ignored .env into THIS process only.
# The key is never echoed, never written to another file and never baked into an image.
$envFile = Join-Path (Split-Path $PSScriptRoot -Parent) '.env'
if (-not (Test-Path $envFile)) {
    throw "Missing $envFile. Copy .env.example to .env and put the organizers' key in it."
}
# Names are deliberately unusual: PowerShell variables are case-insensitive and this file is
# dot-sourced, so a loop variable called $name would silently overwrite a caller's $Name.
foreach ($envLine in Get-Content -LiteralPath $envFile -Encoding UTF8) {
    if ($envLine -match '^\s*#' -or $envLine -notmatch '=') { continue }
    $envPair = $envLine -split '=', 2
    Set-Item -Path ('Env:' + $envPair[0].Trim()) -Value $envPair[1].Trim().Trim('"').Trim("'")
}
Remove-Variable envLine, envPair -ErrorAction SilentlyContinue
if ([string]::IsNullOrWhiteSpace($env:API_KEY)) {
    throw 'API_KEY is empty in .env. The service would refuse every protected request (401).'
}
Write-Host ("API_KEY loaded ({0} characters)." -f $env:API_KEY.Length)
