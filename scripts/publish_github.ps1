param(
    [Parameter(Mandatory=$true)]
    [ValidatePattern('^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:\.git)?$')]
    [string]$RepositoryUrl
)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
gh auth status
if ($LASTEXITCODE -ne 0) { throw 'Sign in using gh auth login before publication.' }
gh repo view $RepositoryUrl --json nameWithOwner
if ($LASTEXITCODE -ne 0) { throw 'The provided repository must exist and be accessible.' }
$reviewedOrigin = git remote get-url origin 2>$null
if ($LASTEXITCODE -eq 0 -and $reviewedOrigin -ne $RepositoryUrl) {
    throw 'Existing origin differs. Review it before publication; it will not be replaced.'
}
if (-not $reviewedOrigin) {
    git remote add origin $RepositoryUrl
    if ($LASTEXITCODE -ne 0) { throw 'Could not set the requested repository origin.' }
}
git add -- .
if ($LASTEXITCODE -ne 0) { throw 'Staging failed.' }
git diff --cached --quiet
if ($LASTEXITCODE -ne 0) {
    git commit -m 'Build tested TensorForge RideEat multilingual MVP'
    if ($LASTEXITCODE -ne 0) { throw 'Commit failed; configure your Git author identity.' }
}
git push -u origin HEAD
if ($LASTEXITCODE -ne 0) { throw 'Push failed. Inspect the remote; do not force push.' }
