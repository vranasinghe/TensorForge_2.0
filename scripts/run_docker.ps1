# Run the submitted image exactly as the PSF requires, with the key taken from .env:
#   docker run -p 8000:8000 -e API_KEY=<key> <image>
# "-e API_KEY" (no value) makes Docker copy the variable from this process, so the key never
# appears in the command line, shell history, `docker inspect` of the image, or any image layer.
param([string]$Image = 'tensorforge:local', [int]$Port = 8000, [string]$ContainerName = 'tensorforge-eval',
      [string]$Volume = 'tensorforge-eval-jobs')
. (Join-Path $PSScriptRoot 'load_env.ps1')
# Refuse to run if the host port is taken, instead of failing half-way; never touch other containers.
if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) {
    throw "Port $Port is already in use. Pick another with -Port, or stop whatever is listening."
}
# Replace only a previous container created by THIS script (same name); leave everything else alone.
if (docker ps -a --filter "name=^${ContainerName}$" --format '{{.Names}}') { docker rm -f $ContainerName | Out-Null }
docker run -d --name $ContainerName -p "${Port}:8000" -e API_KEY -v "${Volume}:/srv/runtime" $Image
Write-Host "Started $ContainerName on http://127.0.0.1:$Port (check: python -m scripts.key_check --base http://127.0.0.1:$Port)"
