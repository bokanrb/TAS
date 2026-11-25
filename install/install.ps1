# Convenience wrapper for Windows. Calls the cross platform installer.
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
python -m pip install -r requirements.txt
python install\install.py @args
