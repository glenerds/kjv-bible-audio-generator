$ErrorActionPreference = 'Stop'
$ArchiveUrl = 'https://github.com/FFmpeg-Builds/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-lgpl.zip'
$ExpectedArchiveSha256 = '78d1f7728fef503b50a6de5866950a96d7e4db0fdb9dfaa47fc2c6691a48370b'
$ExpectedArchiveBytes = 179056458
$SourceCommit = 'b9ebe81995b58cd4e3177a6c0ad5dc2392f7f7fd'
$DownloadPath = Join-Path $env:RUNNER_TEMP 'ffmpeg-master-latest-win64-lgpl.zip'
$ExtractRoot = Join-Path $env:RUNNER_TEMP 'ffmpeg-candidate-extracted'
$ReportRoot = Join-Path $env:GITHUB_WORKSPACE 'artifacts/ffmpeg-candidate-audit'
New-Item -ItemType Directory -Force -Path $ReportRoot | Out-Null

Write-Host 'Downloading the pinned 2026-11-25 Windows x64 LGPL static archive.'
Invoke-WebRequest -Uri $ArchiveUrl -OutFile $DownloadPath -UseBasicParsing
$ArchiveInfo = Get-Item -LiteralPath $DownloadPath
$ArchiveSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $DownloadPath).Hash.ToLowerInvariant()
if ($ArchiveInfo.Length -ne $ExpectedArchiveBytes) {
    throw "FFmpeg archive size mismatch: expected $ExpectedArchiveBytes, got $($ArchiveInfo.Length)"
}
if ($ArchiveSha256 -ne $ExpectedArchiveSha256) {
    throw "FFmpeg archive SHA-256 mismatch: expected $ExpectedArchiveSha256, got $ArchiveSha256"
}
Write-Host "Pinned archive verified: $ArchiveSha256 ($($ArchiveInfo.Length) bytes)"

if (Test-Path $ExtractRoot) { Remove-Item -LiteralPath $ExtractRoot -Recurse -Force }
New-Item -ItemType Directory -Force -Path $ExtractRoot | Out-Null
Expand-Archive -LiteralPath $DownloadPath -DestinationPath $ExtractRoot -Force
$FfmpegItem = Get-ChildItem -LiteralPath $ExtractRoot -Filter 'ffmpeg.exe' -File -Recurse | Select-Object -First 1
if (-not $FfmpegItem) { throw 'The pinned release archive does not contain ffmpeg.exe.' }
$Ffmpeg = $FfmpegItem.FullName

$PackageRoot = $FfmpegItem.Directory.Parent.FullName
if (-not (Test-Path (Join-Path $PackageRoot 'LICENSE.txt') -PathType Leaf) -or
    -not (Test-Path (Join-Path $PackageRoot 'doc') -PathType Container)) {
    throw "The extracted package root lacks the expected LICENSE.txt/doc structure: $PackageRoot"
}

$VersionOutput = & $Ffmpeg -version 2>&1 | Out-String
if ($LASTEXITCODE -ne 0) { throw 'The candidate ffmpeg.exe failed -version.' }
$VersionLine = ($VersionOutput -split "`r?`n")[0].Trim()
$ConfigLines = @($VersionOutput -split "`r?`n" | Where-Object { $_ -match '^configuration:' })
if ($ConfigLines.Count -ne 1) { throw 'The candidate did not report one complete configuration line.' }
$Configuration = $ConfigLines[0].Trim()
if ($Configuration -match '--enable-gpl|--enable-nonfree') {
    throw 'The candidate configuration enables GPL or nonfree components.'
}
if ($Configuration -notmatch '--enable-version3') {
    throw 'The candidate configuration does not include --enable-version3 as expected for LGPLv3.'
}

$LicenseOutput = & $Ffmpeg -L 2>&1 | Out-String
if ($LASTEXITCODE -ne 0 -or
    $LicenseOutput -notmatch 'GNU Lesser General Public License' -or
    $LicenseOutput -notmatch 'version 3') {
    throw 'The candidate -L output does not confirm GNU LGPL version 3.'
}

$EncoderOutput = & $Ffmpeg -hide_banner -encoders 2>&1 | Out-String
if ($LASTEXITCODE -ne 0) {
    Write-Host "FFmpeg encoder listing:`n$EncoderOutput"
    throw 'Could not read the candidate FFmpeg encoder list.'
}
if ($EncoderOutput -notmatch 'libmp3lame') {
    Write-Host "FFmpeg encoder listing:`n$EncoderOutput"
    throw 'The candidate does not expose the required libmp3lame encoder.'
}

$Python = (Get-Command python -ErrorAction Stop).Source
$ProbeWav = Join-Path $env:RUNNER_TEMP 'ffmpeg-candidate-probe.wav'
$ProbeMp3 = Join-Path $env:RUNNER_TEMP 'ffmpeg-candidate-probe.mp3'
$ProbeScript = @'
import math, struct, sys, wave
path = sys.argv[1]
rate = 24000
with wave.open(path, "wb") as out:
    out.setnchannels(1)
    out.setsampwidth(2)
    out.setframerate(rate)
    frames = (int(0.2 * 32767 * math.sin(2 * math.pi * 440 * i / rate)) for i in range(rate // 2))
    out.writeframes(b"".join(struct.pack("<h", sample) for sample in frames))
'@
& $Python -c $ProbeScript $ProbeWav
if ($LASTEXITCODE -ne 0 -or -not (Test-Path $ProbeWav -PathType Leaf)) {
    throw 'Could not create the deterministic WAV input for the FFmpeg probe.'
}
& $Ffmpeg -hide_banner -loglevel error -y -i $ProbeWav -ac 1 -b:a 96k -codec:a libmp3lame $ProbeMp3
if ($LASTEXITCODE -ne 0 -or -not (Test-Path $ProbeMp3 -PathType Leaf)) {
    throw 'The candidate failed its WAV-to-MP3 encode probe.'
}
& $Ffmpeg -hide_banner -loglevel error -i $ProbeMp3 -f null NUL
if ($LASTEXITCODE -ne 0) { throw 'The candidate failed its MP3 decode probe.' }

Push-Location $env:GITHUB_WORKSPACE
try {
    & (Join-Path $PWD 'tools/import_ffmpeg_notices.ps1') -ExtractedFfmpegPackage $PackageRoot
    if (-not $?) { throw 'Could not import the exact candidate license and dependency notices.' }
    & $Python (Join-Path $PWD 'tools/ffmpeg_notices.py') verify --licenses-dir (Join-Path $PWD 'LICENSES')
    if ($LASTEXITCODE -ne 0) { throw 'Imported FFmpeg notices did not pass complete manifest verification.' }

    $BinarySha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $Ffmpeg).Hash.ToLowerInvariant()
    $LicenseFile = Join-Path $PWD 'LICENSES/FFMPEG_LICENSE.txt'
    $LicenseSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $LicenseFile).Hash.ToLowerInvariant()
    $Manifest = @{
        binary_file = 'ffmpeg.exe'
        archive_sha256 = $ArchiveSha256
        archive_bytes = [long]$ExpectedArchiveBytes
        source_commit = $SourceCommit
        binary_sha256 = $BinarySha256
        version_line = $VersionLine
        configuration = $Configuration
        license_spdx = 'LGPL-3.0-or-later'
        license_file = 'FFMPEG_LICENSE.txt'
        license_sha256 = $LicenseSha256
        binary_source_url = $ArchiveUrl
        source_url = "https://github.com/FFmpeg-Builds/FFmpeg-Builds/tree/$SourceCommit"
        notes = "Archive SHA-256 $ArchiveSha256; archive size $ExpectedArchiveBytes bytes; GitHub release refreshed 2026-11-25. Native Windows -version/-L/configuration/libmp3lame, notice verification and WAV-MP3-decode probes passed."
    }
    $Utf8NoBom = New-Object -TypeName System.Text.UTF8Encoding -ArgumentList $false
    $ManifestJson = $Manifest | ConvertTo-Json -Depth 5
    [System.IO.File]::WriteAllText((Join-Path $ReportRoot 'FFMPEG_BUILD_MANIFEST.json'), $ManifestJson + [Environment]::NewLine, $Utf8NoBom)

    Copy-Item -LiteralPath $Ffmpeg -Destination (Join-Path $ReportRoot 'ffmpeg.exe') -Force
    Copy-Item -LiteralPath (Join-Path $PWD 'LICENSES/FFMPEG_LICENSE.txt') -Destination $ReportRoot -Force
    Copy-Item -LiteralPath (Join-Path $PWD 'LICENSES/FFMPEG_DEPENDENCY_NOTICES') -Destination (Join-Path $ReportRoot 'FFMPEG_DEPENDENCY_NOTICES') -Recurse -Force

    $Report = @{
        status = 'passed'
        archive_bytes = $ArchiveInfo.Length
        archive_sha256 = $ArchiveSha256
        source_commit = $SourceCommit
        binary_sha256 = $BinarySha256
        version_line = $VersionLine
        configuration = $Configuration
        license = 'LGPL-3.0-or-later'
        license_sha256 = $LicenseSha256
        mp3_encoder = 'libmp3lame'
        mp3_encode_decode = 'passed'
        notices = 'imported and SHA-256 verified'
    }
    $ReportJson = $Report | ConvertTo-Json -Depth 5
    [System.IO.File]::WriteAllText((Join-Path $ReportRoot 'audit-report.json'), $ReportJson + [Environment]::NewLine, $Utf8NoBom)
} finally {
    Pop-Location
}

Write-Host 'Pinned Windows FFmpeg candidate passed all technical checks. License/source obligations still require human review.'
