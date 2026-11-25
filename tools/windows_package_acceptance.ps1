param(
    [ValidateSet('cpu', 'cu128')]
    [string]$TorchVariant = 'cu128'
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$BuildScript = Join-Path $PSScriptRoot 'build_windows.ps1'
$DistRoot = Join-Path $Root 'dist/KJV Bible Audio Generator'
$ExecutableName = 'KJV Bible Audio Generator.exe'
$Executable = Join-Path $DistRoot $ExecutableName
$RunRoot = Join-Path $env:RUNNER_TEMP 'kjv-windows-package-acceptance'
$EvidenceRoot = Join-Path $Root 'artifacts/windows-package-acceptance'
$OfflineNames = @('HF_HUB_OFFLINE', 'TRANSFORMERS_OFFLINE', 'HF_DATASETS_OFFLINE', 'KJV_APP_DIAGNOSTICS_FILE')
$PreviousEnv = @{}
foreach ($Name in $OfflineNames) {
    $PreviousEnv[$Name] = [Environment]::GetEnvironmentVariable($Name, 'Process')
}

New-Item -ItemType Directory -Force -Path $RunRoot, $EvidenceRoot | Out-Null
$Transcript = Join-Path $EvidenceRoot 'windows-package-acceptance.log'
Start-Transcript -LiteralPath $Transcript -Force | Out-Null
$DriveLetter = $null
$RelocatedRoot = Join-Path $env:RUNNER_TEMP 'KJV Bible Audio Generator Relocated'

function Invoke-PackagedExecutable {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ExecutablePath,

        [Parameter(Mandatory = $true)]
        [string[]]$Arguments,

        [ValidateRange(1, 7200)]
        [int]$TimeoutSeconds = 1800
    )

    $ResolvedExecutable = (Resolve-Path -LiteralPath $ExecutablePath).Path
    $StartInfo = [System.Diagnostics.ProcessStartInfo]::new()
    $StartInfo.FileName = $ResolvedExecutable
    $StartInfo.WorkingDirectory = Split-Path -Parent $ResolvedExecutable
    $StartInfo.UseShellExecute = $false
    $StartInfo.CreateNoWindow = $true
    foreach ($Argument in $Arguments) {
        [void]$StartInfo.ArgumentList.Add([string]$Argument)
    }

    $Process = [System.Diagnostics.Process]::new()
    $Process.StartInfo = $StartInfo
    try {
        if (-not $Process.Start()) {
            throw "Could not start packaged application: $ResolvedExecutable"
        }
        if (-not $Process.WaitForExit($TimeoutSeconds * 1000)) {
            try { $Process.Kill() } catch { }
            $Process.WaitForExit()
            throw "Packaged application exceeded its $TimeoutSeconds second timeout: $ResolvedExecutable"
        }
        $Process.WaitForExit()
        return [int]$Process.ExitCode
    }
    finally {
        $Process.Dispose()
    }
}
try {
    Write-Host "Starting full Windows package acceptance with TorchVariant=$TorchVariant"
    Write-Host 'Available filesystem capacity before build:'
    Get-PSDrive -PSProvider FileSystem | Format-Table -AutoSize

    & $BuildScript -TorchVariant $TorchVariant
    if ($LASTEXITCODE -ne 0 -or -not $?) {
        throw 'The native Windows PyInstaller build script failed.'
    }

    # Asset preparation above needs network access. Only the already-built app
    # is switched to offline mode, after all pinned models and dependencies exist.
    foreach ($Name in $OfflineNames) {
        [Environment]::SetEnvironmentVariable($Name, '1', 'Process')
    }

    if (-not (Test-Path $Executable -PathType Leaf)) {
        throw "The built Windows GUI executable is missing: $Executable"
    }
    $Ffmpeg = Join-Path $DistRoot '_internal/ffmpeg.exe'
    if (-not (Test-Path $Ffmpeg -PathType Leaf)) {
        throw "The packaged FFmpeg executable is missing from PyInstaller _internal: $Ffmpeg"
    }

    $SelfTestOutput = Join-Path $DistRoot 'portable-acceptance/self-test'
    $SelfTestDiagnostics = Join-Path $EvidenceRoot 'self-test-entrypoint-diagnostics.json'
    [Environment]::SetEnvironmentVariable('KJV_APP_DIAGNOSTICS_FILE', $SelfTestDiagnostics, 'Process')
    $SelfTestExitCode = Invoke-PackagedExecutable -ExecutablePath $Executable -Arguments @('--self-test', '--device', 'cpu', '--output', $SelfTestOutput) -TimeoutSeconds 900
    $SelfTestReport = Join-Path $SelfTestOutput 'metadata/self_test_report.json'
    if (-not (Test-Path $SelfTestReport -PathType Leaf)) {
        $DiagnosticText = if (Test-Path $SelfTestDiagnostics -PathType Leaf) { Get-Content -Raw -LiteralPath $SelfTestDiagnostics } else { 'No entrypoint diagnostics were written.' }
        throw "Packaged --self-test did not create its machine-readable report. Entrypoint diagnostics: $DiagnosticText"

    }
    $SelfTest = Get-Content -Raw -LiteralPath $SelfTestReport | ConvertFrom-Json
    if ($SelfTestExitCode -ne 0 -or -not $SelfTest.ok -or @($SelfTest.checks.PSObject.Properties | Where-Object { -not $_.Value }).Count -gt 0) {
        throw "Packaged self-test reported a failed check: $($SelfTest | ConvertTo-Json -Depth 8 -Compress)"
    }
    Copy-Item -LiteralPath $SelfTestReport -Destination (Join-Path $EvidenceRoot 'self-test-report.json') -Force

    $AudioOutput = Join-Path $DistRoot 'portable-acceptance/audio-smoke'
    $AudioDiagnostics = Join-Path $EvidenceRoot 'audio-smoke-entrypoint-diagnostics.json'
    [Environment]::SetEnvironmentVariable('KJV_APP_DIAGNOSTICS_FILE', $AudioDiagnostics, 'Process')
    $AudioExitCode = Invoke-PackagedExecutable -ExecutablePath $Executable -Arguments @('--audio-smoke', '--device', 'cpu', '--output', $AudioOutput) -TimeoutSeconds 1800
    $AudioReport = Join-Path $AudioOutput 'metadata/audio_smoke_report.json'
    if (-not (Test-Path $AudioReport -PathType Leaf)) {
        throw 'Packaged --audio-smoke did not create its machine-readable report.'
    }
    $Audio = Get-Content -Raw -LiteralPath $AudioReport | ConvertFrom-Json
    if ($AudioExitCode -ne 0 -or -not $Audio.ok -or [int]$Audio.samples -le 0 -or [int]$Audio.sample_rate -ne 24000) {
        throw "Packaged audio-smoke report is invalid: $($Audio | ConvertTo-Json -Depth 8 -Compress)"
    }
    $AudioMp3 = Join-Path $AudioOutput 'Genesis/Genesis_001.mp3'
    $AudioCue = Join-Path $AudioOutput 'metadata/verse_timestamps/Genesis_001.json'
    if (-not (Test-Path $AudioMp3 -PathType Leaf) -or (Get-Item $AudioMp3).Length -lt 512) {
        throw 'Packaged Qwen audio smoke did not create a nonempty Genesis MP3.'
    }
    if (-not (Test-Path $AudioCue -PathType Leaf)) {
        throw 'Packaged Qwen audio smoke did not create its verse cue JSON.'
    }
    & $Ffmpeg -hide_banner -loglevel error -i $AudioMp3 -f null NUL
    if ($LASTEXITCODE -ne 0) {
        throw 'The packaged FFmpeg binary could not decode the generated Qwen MP3.'
    }
    Copy-Item -LiteralPath $AudioReport -Destination (Join-Path $EvidenceRoot 'audio-smoke-report.json') -Force
    Copy-Item -LiteralPath $AudioMp3 -Destination (Join-Path $EvidenceRoot 'packaged-qwen-smoke.mp3') -Force
    Copy-Item -LiteralPath $AudioCue -Destination (Join-Path $EvidenceRoot 'packaged-qwen-smoke-cues.json') -Force

    # Move the complete app folder and expose it through a new drive letter.
    # This is a drive-letter relocation simulation on NTFS, not a physical USB device.
    if (Test-Path $RelocatedRoot) { Remove-Item -LiteralPath $RelocatedRoot -Recurse -Force }
    Move-Item -LiteralPath $DistRoot -Destination $RelocatedRoot
    $Candidates = @('Z:', 'Y:', 'X:', 'W:', 'V:')
    foreach ($Candidate in $Candidates) {
        $Name = $Candidate.TrimEnd(':')
        if (-not (Get-PSDrive -Name $Name -ErrorAction SilentlyContinue)) {
            $DriveLetter = $Candidate
            break
        }
    }
    if (-not $DriveLetter) { throw 'Could not find an unused drive letter for the relocation test.' }
    $SubstCommand = 'subst {0} "{1}"' -f $DriveLetter, $RelocatedRoot
    & $env:ComSpec /c $SubstCommand
    if ($LASTEXITCODE -ne 0) { throw "Could not assign the temporary relocated drive $DriveLetter." }

    $RelocatedDriveRoot = $DriveLetter + '\'
    $RelocatedExecutable = Join-Path $RelocatedDriveRoot $ExecutableName
    $RelocatedSelfOutput = Join-Path $RelocatedDriveRoot 'portable-acceptance-relocated/self-test'
    $RelocatedSelfDiagnostics = Join-Path $EvidenceRoot 'relocated-self-test-entrypoint-diagnostics.json'
    [Environment]::SetEnvironmentVariable('KJV_APP_DIAGNOSTICS_FILE', $RelocatedSelfDiagnostics, 'Process')
    $RelocatedSelfExitCode = Invoke-PackagedExecutable -ExecutablePath $RelocatedExecutable -Arguments @('--self-test', '--device', 'cpu', '--output', $RelocatedSelfOutput) -TimeoutSeconds 900
    $RelocatedSelfReport = Join-Path $RelocatedSelfOutput 'metadata/self_test_report.json'
    if (-not (Test-Path $RelocatedSelfReport -PathType Leaf)) {
        throw 'Relocated packaged self-test did not create its report.'
    }
    $RelocatedSelf = Get-Content -Raw -LiteralPath $RelocatedSelfReport | ConvertFrom-Json
    if ($RelocatedSelfExitCode -ne 0 -or -not $RelocatedSelf.ok) { throw 'Relocated package self-test reported a failed check.' }

    $RelocatedAudioOutput = Join-Path $RelocatedDriveRoot 'portable-acceptance-relocated/audio-smoke'
    $RelocatedAudioDiagnostics = Join-Path $EvidenceRoot 'relocated-audio-smoke-entrypoint-diagnostics.json'
    [Environment]::SetEnvironmentVariable('KJV_APP_DIAGNOSTICS_FILE', $RelocatedAudioDiagnostics, 'Process')
    $RelocatedAudioExitCode = Invoke-PackagedExecutable -ExecutablePath $RelocatedExecutable -Arguments @('--audio-smoke', '--device', 'cpu', '--output', $RelocatedAudioOutput) -TimeoutSeconds 1800
    $RelocatedAudioReport = Join-Path $RelocatedAudioOutput 'metadata/audio_smoke_report.json'
    if (-not (Test-Path $RelocatedAudioReport -PathType Leaf)) {
        throw 'Relocated package audio smoke did not create its report.'
    }
    $RelocatedAudio = Get-Content -Raw -LiteralPath $RelocatedAudioReport | ConvertFrom-Json
    if ($RelocatedAudioExitCode -ne 0 -or -not $RelocatedAudio.ok) { throw 'Relocated package audio smoke reported a failure.' }
    $RelocatedFfmpeg = Join-Path $RelocatedDriveRoot '_internal/ffmpeg.exe'
    $RelocatedMp3 = Join-Path $RelocatedAudioOutput 'Genesis/Genesis_001.mp3'
    & $RelocatedFfmpeg -hide_banner -loglevel error -i $RelocatedMp3 -f null NUL
    if ($LASTEXITCODE -ne 0) { throw 'Relocated package FFmpeg could not decode its generated MP3.' }

    Copy-Item -LiteralPath $RelocatedSelfReport -Destination (Join-Path $EvidenceRoot 'relocated-self-test-report.json') -Force
    Copy-Item -LiteralPath $RelocatedAudioReport -Destination (Join-Path $EvidenceRoot 'relocated-audio-smoke-report.json') -Force
    Copy-Item -LiteralPath $RelocatedMp3 -Destination (Join-Path $EvidenceRoot 'relocated-qwen-smoke.mp3') -Force
    # Diagnostics are written directly into EvidenceRoot by the frozen entrypoint.

    $PackageFiles = @(Get-ChildItem -LiteralPath $RelocatedRoot -File -Recurse)
    $PackageBytes = [long](($PackageFiles | Measure-Object -Property Length -Sum).Sum)
    $PackageFileManifest = @(
        $PackageFiles | ForEach-Object {
            [ordered]@{
                path = $_.FullName.Substring($RelocatedRoot.Length).TrimStart('\')
                size_bytes = [long]$_.Length
            }
        }
    )
    $PackageManifest = [ordered]@{
        root = $ExecutableName
        payload_file_count = $PackageFiles.Count
        payload_bytes = $PackageBytes
        payload_gib = [math]::Round($PackageBytes / 1GB, 3)
        files = $PackageFileManifest
        note = 'Manifest of the built portable one-folder app after its drive-letter acceptance test.'
    }
    $PackageManifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $EvidenceRoot 'portable-package-manifest.json') -Encoding UTF8

    $Summary = @{
        status = 'passed'
        torch_variant = $TorchVariant
        pyinstaller_mode = 'onedir-windowed'
        packaged_executable = $ExecutableName
        package_payload_file_count = $PackageFiles.Count
        package_payload_bytes = $PackageBytes
        package_payload_gib = [math]::Round($PackageBytes / 1GB, 3)
        bundled_ffmpeg = 'passed'
        package_self_test = 'passed'
        package_real_qwen_audio_smoke = 'passed'
        qwen_audio_sample_rate = [int]$Audio.sample_rate
        qwen_audio_sample_count = [int]$Audio.samples
        package_mp3_decode = 'passed'
        relocated_drive_letter = $DriveLetter
        relocated_self_test = 'passed'
        relocated_real_qwen_audio_smoke = 'passed'
        relocated_mp3_decode = 'passed'
        relocation_note = 'subst drive-letter test on NTFS; physical removable USB not tested'
    }
    $Summary | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $EvidenceRoot 'acceptance-summary.json') -Encoding UTF8
    Write-Host ($Summary | ConvertTo-Json -Depth 8)
    Write-Host 'WINDOWS_PORTABLE_PACKAGE_ACCEPTANCE_PASSED'
}
finally {
    if ($DriveLetter) {
        & $env:ComSpec /c "subst $DriveLetter /D" | Out-Null
    }
    if ($RelocatedRoot -and (Test-Path $RelocatedRoot -PathType Container) -and -not (Test-Path $DistRoot)) {
        Move-Item -LiteralPath $RelocatedRoot -Destination $DistRoot
        Write-Host "Restored validated portable app folder to $DistRoot"
    }
    Stop-Transcript | Out-Null
    foreach ($Name in $OfflineNames) {
        [Environment]::SetEnvironmentVariable($Name, $PreviousEnv[$Name], 'Process')
    }
}
