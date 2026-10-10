# Start the API locally with the key from .env:  .\scripts\run_local.ps1  [-Port 8000]
param([int]$Port = 8000)
. (Join-Path $PSScriptRoot 'load_env.ps1')
$root = Split-Path $PSScriptRoot -Parent
& (Join-Path $root '.venv\Scripts\python.exe') -m uvicorn app.main:app --host 127.0.0.1 --port $Port --workers 1
