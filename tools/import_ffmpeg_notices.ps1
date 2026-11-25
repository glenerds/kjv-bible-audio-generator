param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$ExtractedFfmpegPackage
)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$Python = (Get-Command python -ErrorAction Stop).Source
& $Python (Join-Path $PSScriptRoot 'ffmpeg_notices.py') import --source-package $ExtractedFfmpegPackage --licenses-dir (Join-Path $Root 'LICENSES')
if ($LASTEXITCODE -ne 0) { throw 'Could not import FFmpeg license/dependency notices. The Windows package must not be built.' }
