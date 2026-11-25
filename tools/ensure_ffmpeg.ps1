param(
    [Parameter(Mandatory = $true)]
    [string]$Root,

    [string]$AuditScript = (Join-Path $PSScriptRoot 'run_ffmpeg_candidate_audit.ps1')
)

$ErrorActionPreference = 'Stop'
$Root = [System.IO.Path]::GetFullPath($Root)
$Ffmpeg = Join-Path $Root 'ffmpeg.exe'
$LicenseDir = Join-Path $Root 'LICENSES'
$ManifestPath = Join-Path $LicenseDir 'FFMPEG_BUILD_MANIFEST.json'
$LicensePath = Join-Path $LicenseDir 'FFMPEG_LICENSE.txt'
$NoticesManifestPath = Join-Path $LicenseDir 'FFMPEG_DEPENDENCY_NOTICES/MANIFEST.json'

$InputsComplete = (Test-Path $Ffmpeg -PathType Leaf) -and
    (Test-Path $ManifestPath -PathType Leaf) -and
    (Test-Path $LicensePath -PathType Leaf) -and
    (Test-Path $NoticesManifestPath -PathType Leaf)
if ($InputsComplete) {
    Write-Host 'Pinned FFmpeg executable, build manifest, license and notice manifest are already present; the packaging step will verify their contents.'
    return
}

if (-not (Test-Path $AuditScript -PathType Leaf)) {
    throw "Pinned FFmpeg audit script does not exist: $AuditScript"
}

$OldWorkspace = [Environment]::GetEnvironmentVariable('GITHUB_WORKSPACE', 'Process')
$OldRunnerTemp = [Environment]::GetEnvironmentVariable('RUNNER_TEMP', 'Process')
$OwnedRunnerTemp = $null
if ([string]::IsNullOrWhiteSpace($OldRunnerTemp)) {
    $OwnedRunnerTemp = Join-Path ([System.IO.Path]::GetTempPath()) ('kjv-ffmpeg-' + [Guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Force -Path $OwnedRunnerTemp | Out-Null
    $env:RUNNER_TEMP = $OwnedRunnerTemp
}
$env:GITHUB_WORKSPACE = $Root

try {
    Write-Host 'FFmpeg inputs are incomplete. Running the pinned download, hash, license, encoder and MP3 audit.'
    & $AuditScript
    if (-not $?) {
        throw 'Pinned FFmpeg download/audit script failed.'
    }

    $AuditOutput = Join-Path $Root 'artifacts/ffmpeg-candidate-audit'
    $AuditedExecutable = Join-Path $AuditOutput 'ffmpeg.exe'
    $AuditedManifest = Join-Path $AuditOutput 'FFMPEG_BUILD_MANIFEST.json'
    if (-not (Test-Path $AuditedExecutable -PathType Leaf) -or
        -not (Test-Path $AuditedManifest -PathType Leaf) -or
        -not (Test-Path $LicensePath -PathType Leaf) -or
        -not (Test-Path $NoticesManifestPath -PathType Leaf)) {
        throw 'Pinned FFmpeg audit did not produce all required executable, manifest, license and notice files.'
    }

    Copy-Item -LiteralPath $AuditedExecutable -Destination $Ffmpeg -Force
    Copy-Item -LiteralPath $AuditedManifest -Destination $ManifestPath -Force
    Write-Host 'Pinned FFmpeg executable and matching build manifest installed. The build script will re-verify every hash before packaging.'
}
finally {
    if ($null -eq $OldWorkspace) {
        Remove-Item Env:GITHUB_WORKSPACE -ErrorAction SilentlyContinue
    }
    else {
        $env:GITHUB_WORKSPACE = $OldWorkspace
    }

    if ($null -eq $OldRunnerTemp) {
        Remove-Item Env:RUNNER_TEMP -ErrorAction SilentlyContinue
    }
    else {
        $env:RUNNER_TEMP = $OldRunnerTemp
    }

    if ($null -ne $OwnedRunnerTemp -and (Test-Path $OwnedRunnerTemp)) {
        Remove-Item -LiteralPath $OwnedRunnerTemp -Recurse -Force -ErrorAction SilentlyContinue
    }
}
