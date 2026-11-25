param(
    [ValidateSet('cpu','cu128')]
    [string]$TorchVariant = 'cu128'
)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$Python = (Get-Command python -ErrorAction Stop).Source
Push-Location $Root
try {
    $PythonMinor = (& $Python -c 'import sys; print(".".join(map(str, sys.version_info[:2])))').Trim()
    $PythonBits = (& $Python -c 'import struct; print(struct.calcsize("P") * 8)').Trim()
    if ($PythonMinor -ne '3.12' -or $PythonBits -ne '64') {
        throw "Use 64-bit Python 3.12 to build the Qwen Windows bundle; detected Python $PythonMinor ($PythonBits-bit)."
    }
    $TorchVersion = '2.10.0'
    $TorchIndex = if ($TorchVariant -eq 'cpu') { 'https://download.pytorch.org/whl/cpu' } else { 'https://download.pytorch.org/whl/cu128' }
    Write-Host "Installing pinned PyTorch $TorchVersion ($TorchVariant) from $TorchIndex…"
    & $Python -m pip install "torch==$TorchVersion" "torchaudio==$TorchVersion" --index-url $TorchIndex
    if ($LASTEXITCODE -ne 0) { throw 'Could not install the selected PyTorch/torchaudio wheel set.' }
    Write-Host 'Installing the pinned Qwen and developer packaging dependencies…'
    & $Python -m pip install -e '.[qwen,dev]'
    if ($LASTEXITCODE -ne 0) { throw 'Could not install the Qwen/packaging dependencies.' }
    # Invoke as a PowerShell script: terminating errors from the preparation stage
    # are allowed to propagate. Do not rely on a stale native $LASTEXITCODE here.
    & (Join-Path $PSScriptRoot 'prepare_assets.ps1')
    if (-not $?) { throw 'Pinned asset preparation failed.' }
} finally { Pop-Location }

$Models = Join-Path $Root 'models'
$AssetManifestPath = Join-Path $Models 'KJV_QWEN_ASSET_MANIFEST.json'
if (-not (Test-Path $AssetManifestPath -PathType Leaf)) { throw 'Pinned Qwen asset manifest is missing. Run tools/prepare_assets.ps1 first.' }
$AssetManifest = Get-Content -Raw -LiteralPath $AssetManifestPath | ConvertFrom-Json
if ($AssetManifest.schema_version -ne 1 -or @($AssetManifest.models).Count -ne 2) { throw 'Pinned Qwen asset manifest is invalid.' }
$WeightIntegrityScript = Join-Path $PSScriptRoot 'qwen_asset_integrity.py'
if (-not (Test-Path $WeightIntegrityScript -PathType Leaf)) { throw 'Pinned Qwen asset integrity verifier is missing.' }
& $Python $WeightIntegrityScript verify --models-root $Models --manifest $AssetManifestPath
if ($LASTEXITCODE -ne 0) {
    throw 'Pinned Qwen weight SHA-256 or manifest verification failed. Packaging is blocked.'
}
$ExpectedRevisions = @{
    'Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign' = '5ecdb67327fd37bb2e042aab12ff7391903235d3'
    'Qwen/Qwen3-TTS-12Hz-1.7B-Base' = 'fd4b254389122332181a7c3db7f27e918eec64e3'
}
foreach ($Entry in $AssetManifest.models) {
    if (-not $ExpectedRevisions.ContainsKey([string]$Entry.repo) -or
        $ExpectedRevisions[[string]$Entry.repo] -ne [string]$Entry.revision) {
        throw "Qwen asset manifest contains an unapproved model revision: $($Entry.repo) $($Entry.revision)"
    }
}
$RequiredModels = @(
    @{ Path = (Join-Path $Models 'Qwen3-TTS-12Hz-1.7B-VoiceDesign'); Kind = 'voice_design' },
    @{ Path = (Join-Path $Models 'Qwen3-TTS-12Hz-1.7B-Base'); Kind = 'base' }
)
$RequiredModelFiles = @(
    'config.json', 'generation_config.json', 'model.safetensors', 'tokenizer_config.json',
    'vocab.json', 'merges.txt', 'preprocessor_config.json', 'speech_tokenizer/config.json',
    'speech_tokenizer/configuration.json', 'speech_tokenizer/model.safetensors',
    'speech_tokenizer/preprocessor_config.json'
)
foreach ($Model in $RequiredModels) {
    foreach ($RelativeFile in $RequiredModelFiles) {
        $RequiredFile = Join-Path $Model.Path $RelativeFile
        if (-not (Test-Path $RequiredFile -PathType Leaf)) {
            throw "Qwen model folder is incomplete; required file missing: $RequiredFile"
        }
    }
    if ((Get-Item (Join-Path $Model.Path 'model.safetensors')).Length -lt 3500000000) {
        throw "Qwen main model weights appear truncated: $($Model.Path)"
    }
    if ((Get-Item (Join-Path $Model.Path 'speech_tokenizer/model.safetensors')).Length -lt 650000000) {
        throw "Qwen speech tokenizer weights appear truncated: $($Model.Path)"
    }
    $ModelConfig = Get-Content -Raw -LiteralPath (Join-Path $Model.Path 'config.json') | ConvertFrom-Json
    $SpeechConfig = Get-Content -Raw -LiteralPath (Join-Path $Model.Path 'speech_tokenizer/config.json') | ConvertFrom-Json
    if ($ModelConfig.model_type -ne 'qwen3_tts' -or
        $ModelConfig.tokenizer_type -ne 'qwen3_tts_tokenizer_12hz' -or
        $ModelConfig.tts_model_type -ne $Model.Kind -or
        $SpeechConfig.model_type -ne 'qwen3_tts_tokenizer_12hz') {
        throw "Qwen model configuration does not match expected model family/type: $($Model.Path)"
    }
    $ExpectedRepo = if ($Model.Kind -eq 'voice_design') { 'Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign' } else { 'Qwen/Qwen3-TTS-12Hz-1.7B-Base' }
    $ManifestEntry = @($AssetManifest.models | Where-Object { $_.repo -eq $ExpectedRepo }) | Select-Object -First 1
    if (-not $ManifestEntry -or $ManifestEntry.folder -ne (Split-Path -Leaf $Model.Path) -or $ManifestEntry.kind -ne $Model.Kind) {
        throw "Qwen asset manifest entry is missing or targets the wrong model folder: $ExpectedRepo"
    }
    $ActualConfigHash = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $Model.Path 'config.json')).Hash.ToLowerInvariant()
    $ActualSpeechConfigHash = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $Model.Path 'speech_tokenizer/config.json')).Hash.ToLowerInvariant()
    if ($ActualConfigHash -ne [string]$ManifestEntry.config_sha256 -or
        $ActualSpeechConfigHash -ne [string]$ManifestEntry.speech_tokenizer_config_sha256 -or
        (Get-Item (Join-Path $Model.Path 'model.safetensors')).Length -ne [long]$ManifestEntry.model_bytes -or
        (Get-Item (Join-Path $Model.Path 'speech_tokenizer/model.safetensors')).Length -ne [long]$ManifestEntry.speech_tokenizer_bytes) {
        throw "Pinned Qwen model files no longer match their verified asset manifest: $($Model.Path)"
    }
}

$Ffmpeg = Join-Path $Root 'ffmpeg.exe'
$Attribution = Join-Path $Root 'data/speaker-attribution'
$PackageData = Join-Path $Root 'src/kjv_audio_generator/data'
$Licenses = Join-Path $Root 'LICENSES'
$FfmpegManifestPath = Join-Path $Licenses 'FFMPEG_BUILD_MANIFEST.json'
$FfmpegLicensePath = Join-Path $Licenses 'FFMPEG_LICENSE.txt'
$FfmpegNoticesManifestPath = Join-Path $Licenses 'FFMPEG_DEPENDENCY_NOTICES/MANIFEST.json'

# Ensure the exact digest-pinned FFmpeg executable and its matching notices exist.
# The helper skips complete inputs; otherwise it runs the same native audit used by CI.
& (Join-Path $PSScriptRoot 'ensure_ffmpeg.ps1') -Root $Root
if (-not $?) { throw 'Pinned FFmpeg dependency bootstrap failed.' }

foreach ($DataFile in @('Clear-Aligned-Projections.tsv','character_detail.semantic_data.tsv','LICENSE.md','ATTRIBUTION.md')) {
    if (-not (Test-Path (Join-Path $Attribution $DataFile) -PathType Leaf)) {
        throw "Required bundled speaker-attribution data is missing: $(Join-Path $Attribution $DataFile)"
    }
}
foreach ($LicenseFile in @('GLYSSEN_MIT.txt','QWEN3_TTS_APACHE_2.0.txt','TOKENIZERS_APACHE_2.0.txt','CUDNN_9.7.0_EULA.html','CUDNN_9.7.0_ACKNOWLEDGEMENTS.html','NVIDIA_CUDNN_NOTICE_MANIFEST.json','FFMPEG_LICENSE.txt','FFMPEG_BUILD_MANIFEST.json')) {
    if (-not (Test-Path (Join-Path $Licenses $LicenseFile) -PathType Leaf)) {
        throw "Required third-party license/build notice is missing: $(Join-Path $Licenses $LicenseFile)"
    }
}

# A random ffmpeg.exe is not an acceptable release dependency. Require reproducible
# provenance, a matching binary SHA-256, an LGPL-only build and the actual MP3 encoder.
if (-not (Test-Path $Ffmpeg -PathType Leaf)) { throw 'Place a verified LGPL Windows ffmpeg.exe beside this script before packaging.' }
$FfmpegManifest = Get-Content -Raw -LiteralPath (Join-Path $Licenses 'FFMPEG_BUILD_MANIFEST.json') | ConvertFrom-Json
$ExpectedFfmpegArchiveSha256 = '78d1f7728fef503b50a6de5866950a96d7e4db0fdb9dfaa47fc2c6691a48370b'
$ExpectedFfmpegArchiveBytes = 179056458L
$ExpectedFfmpegBinarySha256 = '3209f0ba6096189de3f850f65488bdb535177b7e46e0b16e902b3230c5ff74fe'
$ExpectedFfmpegLicenseSha256 = 'da7eabb7bafdf7d3ae5e9f223aa5bdc1eece45ac569dc21b3b037520b4464768'
$ExpectedFfmpegSourceCommit = 'b9ebe81995b58cd4e3177a6c0ad5dc2392f7f7fd'
$ExpectedFfmpegBinaryUrl = 'https://github.com/FFmpeg-Builds/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-lgpl.zip'
if ($FfmpegManifest.archive_sha256 -ne $ExpectedFfmpegArchiveSha256 -or [long]$FfmpegManifest.archive_bytes -ne $ExpectedFfmpegArchiveBytes) {
    throw 'FFmpeg build manifest does not identify the exact digest-pinned 2026-11-25 archive.'
}
if ($FfmpegManifest.binary_sha256 -ne $ExpectedFfmpegBinarySha256) {
    throw 'FFmpeg executable hash in the build manifest is not the pinned candidate hash.'
}
if ($FfmpegManifest.license_sha256 -ne $ExpectedFfmpegLicenseSha256) {
    throw 'FFmpeg license hash in the build manifest is not the pinned candidate license.'
}
if ($FfmpegManifest.license_spdx -ne 'LGPL-3.0-or-later' -or
    $FfmpegManifest.source_commit -ne $ExpectedFfmpegSourceCommit -or
    $FfmpegManifest.binary_source_url -ne $ExpectedFfmpegBinaryUrl -or
    $FfmpegManifest.source_url -ne "https://github.com/FFmpeg-Builds/FFmpeg-Builds/tree/$ExpectedFfmpegSourceCommit") {
    throw 'FFmpeg build manifest source or license identity does not match the pinned candidate.'
}
$PinnedActualFfmpegHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $Ffmpeg).Hash.ToLowerInvariant()
$PinnedActualFfmpegLicenseHash = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $Licenses 'FFMPEG_LICENSE.txt')).Hash.ToLowerInvariant()
if ($PinnedActualFfmpegHash -ne $ExpectedFfmpegBinarySha256 -or $PinnedActualFfmpegLicenseHash -ne $ExpectedFfmpegLicenseSha256) {
    throw 'FFmpeg binary or license bytes do not match the compiled-in trusted hashes.'
}

$AllowedFfmpegLicenses = @('LGPL-2.1-or-later', 'LGPL-3.0-or-later')
if ($FfmpegManifest.license_spdx -notin $AllowedFfmpegLicenses) { throw 'FFmpeg manifest must declare LGPL-2.1-or-later or LGPL-3.0-or-later; GPL/nonfree builds are not accepted.' }
foreach ($Field in @('binary_sha256','version_line','configuration','binary_source_url','source_url','source_commit','archive_sha256','archive_bytes','license_file','license_sha256')) {
    if ([string]::IsNullOrWhiteSpace([string]$FfmpegManifest.$Field)) { throw "FFmpeg manifest field is required: $Field" }
}
$ActualFfmpegHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $Ffmpeg).Hash.ToLowerInvariant()
if ($ActualFfmpegHash -ne ([string]$FfmpegManifest.binary_sha256).ToLowerInvariant()) {
    throw "FFmpeg SHA-256 mismatch. Expected $($FfmpegManifest.binary_sha256), got $ActualFfmpegHash"
}
$FfmpegVersionOutput = & $Ffmpeg -version 2>&1 | Out-String
if ($LASTEXITCODE -ne 0) { throw 'Bundled FFmpeg could not execute -version.' }
$FfmpegVersionLine = ($FfmpegVersionOutput -split "`r?`n")[0].Trim()
if ($FfmpegVersionLine -ne [string]$FfmpegManifest.version_line) { throw 'FFmpeg version line does not match its build manifest.' }
if ($FfmpegVersionOutput -notmatch 'configuration:') { throw 'FFmpeg did not report build configuration.' }
$FfmpegConfigLine = (($FfmpegVersionOutput -split "`r?`n" | Where-Object { $_ -match '^configuration:' }) -join '').Trim()
if ($FfmpegConfigLine -ne [string]$FfmpegManifest.configuration) { throw 'FFmpeg configuration does not match the build manifest.' }
if ($FfmpegConfigLine -match '--enable-gpl|--enable-nonfree') { throw 'FFmpeg build enables GPL or nonfree components; do not bundle it.' }
$FfmpegLicenseOutput = & $Ffmpeg -L 2>&1 | Out-String
$ExpectedLicenseVersion = if ($FfmpegManifest.license_spdx -eq 'LGPL-3.0-or-later') { 'version 3' } else { 'version 2.1' }
if ($LASTEXITCODE -ne 0 -or $FfmpegLicenseOutput -notmatch 'GNU Lesser General Public License' -or $FfmpegLicenseOutput -notmatch [regex]::Escape($ExpectedLicenseVersion)) {
    throw "Bundled FFmpeg does not identify itself as the manifest's $($FfmpegManifest.license_spdx) build."
}
$DeclaredLicensePath = Join-Path $Licenses ([string]$FfmpegManifest.license_file)
if (-not (Test-Path $DeclaredLicensePath -PathType Leaf)) { throw "The exact FFmpeg license text named in the manifest is missing: $DeclaredLicensePath" }
$ActualLicenseHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $DeclaredLicensePath).Hash.ToLowerInvariant()
if ($ActualLicenseHash -ne ([string]$FfmpegManifest.license_sha256).ToLowerInvariant()) {
    throw "FFmpeg license-text SHA-256 mismatch. Expected $($FfmpegManifest.license_sha256), got $ActualLicenseHash"
}
& $Python (Join-Path $PSScriptRoot 'ffmpeg_notices.py') verify --licenses-dir $Licenses
if ($LASTEXITCODE -ne 0) { throw 'FFmpeg documentation/dependency notice manifest verification failed.' }
$FfmpegEncoders = & $Ffmpeg -hide_banner -encoders 2>&1 | Out-String
if ($LASTEXITCODE -ne 0 -or $FfmpegEncoders -notmatch '\blibmp3lame\b') {
    throw 'Bundled FFmpeg lacks the required libmp3lame MP3 encoder.'
}

# Verify an actual MP3 encode/decode cycle using a deterministic synthetic WAV. This
# checks the supplied Windows FFmpeg executable, not the app's real Qwen synthesis.
$ProbeDir = Join-Path ([System.IO.Path]::GetTempPath()) ('kjv-ffmpeg-probe-' + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $ProbeDir | Out-Null
try {
    $ProbeWav = Join-Path $ProbeDir 'probe.wav'
    $ProbeMp3 = Join-Path $ProbeDir 'probe.mp3'
    $ProbeScript = @'
import math, struct, sys, wave
path = sys.argv[1]
rate = 24000
with wave.open(path, "wb") as out:
    out.setnchannels(1); out.setsampwidth(2); out.setframerate(rate)
    frames = (int(0.2 * 32767 * math.sin(2 * math.pi * 440 * i / rate)) for i in range(rate // 2))
    out.writeframes(b"".join(struct.pack("<h", sample) for sample in frames))
'@
    & $Python -c $ProbeScript $ProbeWav
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the FFmpeg probe WAV.' }
    & $Ffmpeg -hide_banner -loglevel error -y -i $ProbeWav -ac 1 -b:a 96k -codec:a libmp3lame $ProbeMp3
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $ProbeMp3 -PathType Leaf)) { throw 'FFmpeg MP3 encoding probe failed.' }
    & $Ffmpeg -hide_banner -loglevel error -i $ProbeMp3 -f null NUL
    if ($LASTEXITCODE -ne 0) { throw 'FFmpeg MP3 decoding probe failed.' }
} finally {
    Remove-Item -LiteralPath $ProbeDir -Recurse -Force -ErrorAction SilentlyContinue
}

& $Python -m PyInstaller --version | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller is unavailable. Install the developer requirements before running this build.' }
Push-Location $Root
try {
    & $Python -m PyInstaller --noconfirm --clean --onedir --windowed `
        --name 'KJV Bible Audio Generator' `
        --paths 'src' `
        --add-data "$Models;models" `
        --add-data "$Attribution;data/speaker-attribution" `
        --add-data "$PackageData;kjv_audio_generator/data" `
        --add-data "$Licenses;LICENSES" `
        --add-binary "$Ffmpeg;." `
        --collect-all qwen_tts `
        --collect-all huggingface_hub `
        --collect-all torchaudio `
        --collect-all transformers `
        --collect-all tokenizers `
        --collect-all soundfile `
        --collect-all librosa `
        --collect-all torchaudio `
        --collect-all accelerate `
        --collect-all einops `
        --collect-all safetensors `
        --collect-all sox `
        --collect-all onnxruntime `
        --collect-all torch `
        'tools/entrypoint.py'
    if ($LASTEXITCODE -ne 0) { throw 'PyInstaller build failed.' }
    $Internal = 'dist/KJV Bible Audio Generator/_internal'
    if (-not (Test-Path (Join-Path $Internal 'ffmpeg.exe') -PathType Leaf)) { Copy-Item $Ffmpeg (Join-Path $Internal 'ffmpeg.exe') -Force }
    $Launcher = @'
@echo off
setlocal
cd /d "%~dp0"
set "TMP=%CD%\portable\temp"
set "TEMP=%TMP%"
set "TMPDIR=%TMP%"
set "HOME=%CD%\portable\home"
set "USERPROFILE=%HOME%"
set "APPDATA=%CD%\portable\appdata\roaming"
set "LOCALAPPDATA=%CD%\portable\appdata\local"
set "PYTHONUSERBASE=%CD%\portable\python-userbase"
set "PIP_CACHE_DIR=%CD%\portable\cache\pip"
set "HF_HOME=%CD%\portable\cache\huggingface"
set "HF_HUB_CACHE=%HF_HOME%\hub"
set "TRANSFORMERS_CACHE=%HF_HOME%\transformers"
set "HF_HUB_OFFLINE=1"
set "TRANSFORMERS_OFFLINE=1"
set "HF_DATASETS_OFFLINE=1"
set "TORCH_HOME=%CD%\portable\cache\torch"
set "XDG_CACHE_HOME=%CD%\portable\xdg\cache"
set "NUMBA_CACHE_DIR=%CD%\portable\cache\numba"
set "MPLCONFIGDIR=%CD%\portable\config\matplotlib"
set "XDG_CONFIG_HOME=%CD%\portable\xdg\config"
set "XDG_DATA_HOME=%CD%\portable\xdg\data"
set "XDG_STATE_HOME=%CD%\portable\xdg\state"
for %%D in ("%TMP%" "%HOME%" "%APPDATA%" "%LOCALAPPDATA%" "%PYTHONUSERBASE%" "%PIP_CACHE_DIR%" "%HF_HOME%" "%HF_HUB_CACHE%" "%TRANSFORMERS_CACHE%" "%TORCH_HOME%" "%XDG_CONFIG_HOME%" "%XDG_DATA_HOME%" "%XDG_STATE_HOME%" "%XDG_CACHE_HOME%" "%NUMBA_CACHE_DIR%" "%MPLCONFIGDIR%") do if not exist %%D mkdir %%D
start "" "%~dp0KJV Bible Audio Generator.exe"
'@
    Set-Content -Path 'dist/KJV Bible Audio Generator/START_KJV_AUDIO_GENERATOR.bat' -Value $Launcher -Encoding ASCII
} finally { Pop-Location }
Write-Host 'Build produced in dist. Real Qwen inference, real Genesis 1, cross-chapter voice consistency, Windows playback, offline extraction, CPU performance and USB relocation remain separate mandatory release tests.'
