$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$Root = Split-Path -Parent $PSScriptRoot
$Models = Join-Path $Root 'models'
$Attribution = Join-Path $Root 'data/speaker-attribution'
New-Item -ItemType Directory -Force -Path $Models, $Attribution | Out-Null

# Pin exact upstream snapshots so a rebuild does not silently change its model/data inputs.
$ModelSources = @(
    @{ Repo = 'Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign'; Revision = '5ecdb67327fd37bb2e042aab12ff7391903235d3'; Folder = 'Qwen3-TTS-12Hz-1.7B-VoiceDesign'; Kind = 'voice_design' },
    @{ Repo = 'Qwen/Qwen3-TTS-12Hz-1.7B-Base'; Revision = 'fd4b254389122332181a7c3db7f27e918eec64e3'; Folder = 'Qwen3-TTS-12Hz-1.7B-Base'; Kind = 'base' }
)
$RequiredModelFiles = @(
    'config.json',
    'generation_config.json',
    'model.safetensors',
    'tokenizer_config.json',
    'vocab.json',
    'merges.txt',
    'preprocessor_config.json',
    'speech_tokenizer/config.json',
    'speech_tokenizer/configuration.json',
    'speech_tokenizer/model.safetensors',
    'speech_tokenizer/preprocessor_config.json'
)

function Test-CompleteModel([string]$Folder, [string]$ExpectedKind) {
    if (-not (Test-Path $Folder -PathType Container)) { return $false }
    foreach ($Relative in $RequiredModelFiles) {
        if (-not (Test-Path (Join-Path $Folder $Relative) -PathType Leaf)) { return $false }
    }
    if ((Get-Item (Join-Path $Folder 'model.safetensors')).Length -lt 3500000000) { return $false }
    if ((Get-Item (Join-Path $Folder 'speech_tokenizer/model.safetensors')).Length -lt 650000000) { return $false }
    try {
        $Config = Get-Content -Raw -LiteralPath (Join-Path $Folder 'config.json') | ConvertFrom-Json
        $SpeechConfig = Get-Content -Raw -LiteralPath (Join-Path $Folder 'speech_tokenizer/config.json') | ConvertFrom-Json
        if ($Config.model_type -ne 'qwen3_tts' -or
            $Config.tokenizer_type -ne 'qwen3_tts_tokenizer_12hz' -or
            $Config.tts_model_type -ne $ExpectedKind -or
            $SpeechConfig.model_type -ne 'qwen3_tts_tokenizer_12hz') { return $false }
    } catch { return $false }
    return $true
}

$Python = (Get-Command python -ErrorAction Stop).Source
$Scripts = (& $Python -c "import sysconfig; print(sysconfig.get_path('scripts'))").Trim()
if ($Scripts) { $env:PATH = "$Scripts;$env:PATH" }
$Hf = Get-Command hf -ErrorAction SilentlyContinue
if (-not $Hf) {
    Write-Host 'Installing the Hugging Face download utility for the developer build environment…'
    & $Python -m pip install 'huggingface_hub>=0.34,<1.0'
    if ($LASTEXITCODE -ne 0) { throw 'Could not install huggingface_hub. No model assets were prepared.' }
    $Hf = Get-Command hf -ErrorAction SilentlyContinue
}
if (-not $Hf) { throw 'The hf command is still unavailable after installing huggingface_hub.' }

foreach ($Model in $ModelSources) {
    $Destination = Join-Path $Models $Model.Folder
    if (Test-CompleteModel $Destination $Model.Kind) {
        Write-Host "Verified existing model snapshot: $($Model.Folder)"
        continue
    }
    Write-Host "Downloading pinned $($Model.Repo) snapshot $($Model.Revision). This is several gigabytes."
    New-Item -ItemType Directory -Force -Path $Destination | Out-Null
    & $Hf.Source download $Model.Repo --revision $Model.Revision --local-dir $Destination
    if ($LASTEXITCODE -ne 0) { throw "Hugging Face download failed for $($Model.Repo)." }
    if (-not (Test-CompleteModel $Destination $Model.Kind)) {
        throw "Downloaded Qwen model is still incomplete: $Destination"
    }
}

# Verify the full multi-gigabyte weight contents, not just their presence or size.
# The helper uses the publisher's file SHA-256 values and streams files in chunks.
$IntegrityScript = Join-Path $PSScriptRoot 'qwen_asset_integrity.py'
if (-not (Test-Path $IntegrityScript -PathType Leaf)) { throw 'Pinned Qwen asset integrity verifier is missing.' }
$IntegrityOutput = & $Python $IntegrityScript report --models-root $Models
if ($LASTEXITCODE -ne 0) {
    throw 'Pinned Qwen weight verification failed. Do not package these model folders; remove the damaged weights and rerun preparation.'
}
$IntegrityRecords = @(($IntegrityOutput -join [Environment]::NewLine) | ConvertFrom-Json)
if ($IntegrityRecords.Count -ne 2) { throw 'Qwen weight verifier did not return exactly two pinned model records.' }

# The Clear Bible speaker seed is pinned to an exact commit. Verify each downloaded
# file against its Git object SHA-1 before using it in the offline app bundle.
$SeedCommit = 'b09e308a3a1aafdb7d6c75baf0fe2a31d61601da'
$SeedFiles = @(
    @{ Name = 'Clear-Aligned-Projections.tsv'; GitBlobSha = '25adc6c12d49f3328ddcb21436ff05ea03cdc390' },
    @{ Name = 'character_detail.semantic_data.tsv'; GitBlobSha = 'c6c7ddfcb419378b396a863abb312a727abbfcda' },
    @{ Name = 'LICENSE.md'; GitBlobSha = '3fd9f2363dab97473dcac24c7723b09ba6b9f295' }
)
function Get-GitBlobSha1([string]$FilePath) {
    $Bytes = [System.IO.File]::ReadAllBytes($FilePath)
    $Header = [System.Text.Encoding]::ASCII.GetBytes("blob $($Bytes.Length)`0")
    $All = New-Object byte[] ($Header.Length + $Bytes.Length)
    [System.Buffer]::BlockCopy($Header, 0, $All, 0, $Header.Length)
    [System.Buffer]::BlockCopy($Bytes, 0, $All, $Header.Length, $Bytes.Length)
    $Hasher = [System.Security.Cryptography.SHA1]::Create()
    try { return ([System.BitConverter]::ToString($Hasher.ComputeHash($All))).Replace('-', '').ToLowerInvariant() }
    finally { $Hasher.Dispose() }
}
foreach ($Entry in $SeedFiles) {
    $Destination = Join-Path $Attribution $Entry.Name
    $Actual = if (Test-Path $Destination -PathType Leaf) { Get-GitBlobSha1 $Destination } else { '' }
    if ($Actual -ne $Entry.GitBlobSha) {
        if ($Entry.Name -eq 'LICENSE.md') { $RelativePath = 'LICENSE.md' }
        else { $RelativePath = "tsv/$($Entry.Name)" }
        $Uri = "https://raw.githubusercontent.com/Clear-Bible/speaker-quotations/$SeedCommit/$RelativePath"
        Write-Host "Downloading pinned speaker-attribution source: $($Entry.Name)"
        Invoke-WebRequest -Uri $Uri -OutFile $Destination -UseBasicParsing
        $Actual = Get-GitBlobSha1 $Destination
        if ($Actual -ne $Entry.GitBlobSha) { throw "Git blob checksum mismatch for $($Entry.Name): $Actual" }
    }
}

$AttributionNotice = @'
MACULA Quotation and Speaker Data, © 2023 by Clear Bible, Inc, available at https://github.com/Clear-Bible/speaker-quotations/.

The upstream data is licensed CC BY 4.0. Character-detail material includes FCBH/Glyssen data; its upstream MIT license notice is preserved separately in LICENSES/GLYSSEN_MIT.txt. This dataset is not KJV-specific and its verse references are only provisional speaker suggestions. It must not be represented as authoritative KJV quotation attribution.

Pinned upstream source commit: b09e308a3a1aafdb7d6c75baf0fe2a31d61601da.
'@
Set-Content -Path (Join-Path $Attribution 'ATTRIBUTION.md') -Value $AttributionNotice -Encoding UTF8

$GlyssenLicense = @'
The MIT License (MIT)

Copyright (c) 2014-2020 SIL LSDev and Faith Comes By Hearing

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'@
$LicenseDir = Join-Path $Root 'LICENSES'
New-Item -ItemType Directory -Force -Path $LicenseDir | Out-Null
Set-Content -Path (Join-Path $LicenseDir 'GLYSSEN_MIT.txt') -Value $GlyssenLicense -Encoding UTF8

# Include the exact Apache-2.0 notice for the Qwen3-TTS software and model family.
$QwenLicenseCommit = '022e286b98fbec7e1e916cb940cdf532cd9f488e'
$QwenLicensePath = Join-Path $LicenseDir 'QWEN3_TTS_APACHE_2.0.txt'
$QwenLicenseUri = "https://raw.githubusercontent.com/QwenLM/Qwen3-TTS/$QwenLicenseCommit/LICENSE"
Invoke-WebRequest -Uri $QwenLicenseUri -OutFile $QwenLicensePath -UseBasicParsing
if ((Get-GitBlobSha1 $QwenLicensePath) -ne 'c347eb5ec781d2702623e8e2b5923fa1a766a64d') {
    throw 'Qwen Apache-2.0 license notice checksum does not match the pinned upstream source.'
}

# tokenizers 0.22.2 is present in the packaged Transformers runtime. Its wheel
# did not expose a license file in the frozen .dist-info payload, so preserve
# the exact Apache-2.0 license from the dependency's immutable source commit.
$TokenizerLicenseCommit = 'f383101a26663708484cac0727792aad74f78234'
$TokenizerLicensePath = Join-Path $LicenseDir 'TOKENIZERS_APACHE_2.0.txt'
$TokenizerLicenseUri = "https://raw.githubusercontent.com/huggingface/tokenizers/$TokenizerLicenseCommit/LICENSE"
Invoke-WebRequest -Uri $TokenizerLicenseUri -OutFile $TokenizerLicensePath -UseBasicParsing
if ((Get-GitBlobSha1 $TokenizerLicensePath) -ne '261eeb9e9f8b2b4b0d119366dda99c6fd7d35c64') {
    throw 'tokenizers Apache-2.0 license notice checksum does not match the pinned upstream source.'
}

# PyTorch 2.10.0's Windows CUDA 12.8 build configuration selects the official
# cuDNN 9.7.0.66 archive. Preserve the matching versioned NVIDIA SDK EULA and
# its third-party acknowledgements in the portable application.
$CudnnVersion = '9.10.2.21'
$CudnnDocsVersion = '9.10.2'
$CudnnEulaPath = Join-Path $LicenseDir "CUDNN_${CudnnVersion}_EULA.html"
$CudnnAcknowledgementsPath = Join-Path $LicenseDir "CUDNN_${CudnnVersion}_ACKNOWLEDGEMENTS.html"
$CudnnEulaUri = "https://docs.nvidia.com/deeplearning/cudnn/backend/v$CudnnDocsVersion/reference/eula.html"
$CudnnAcknowledgementsUri = "https://docs.nvidia.com/deeplearning/cudnn/backend/v$CudnnDocsVersion/reference/acknowledgements.html"
Invoke-WebRequest -Uri $CudnnEulaUri -OutFile $CudnnEulaPath -UseBasicParsing
Invoke-WebRequest -Uri $CudnnAcknowledgementsUri -OutFile $CudnnAcknowledgementsPath -UseBasicParsing
$CudnnEulaText = Get-Content -Raw -LiteralPath $CudnnEulaPath
$CudnnAcknowledgementsText = Get-Content -Raw -LiteralPath $CudnnAcknowledgementsPath
foreach ($RequiredTerm in @('LICENSE AGREEMENT FOR NVIDIA SOFTWARE DEVELOPMENT KITS','cuDNN SUPPLEMENT TO SOFTWARE LICENSE AGREEMENT','runtime files','.so','.dll')) {
    if ($CudnnEulaText -notmatch [regex]::Escape($RequiredTerm)) {
        throw "Downloaded cuDNN EULA is missing a required version/redistribution clause: $RequiredTerm"
    }
}
foreach ($RequiredTerm in @('University of Tennessee','University of California','Facebook AI Research','Redistribution and use in source and binary forms')) {
    if ($CudnnAcknowledgementsText -notmatch [regex]::Escape($RequiredTerm)) {
        throw "Downloaded cuDNN acknowledgements are missing a required third-party notice: $RequiredTerm"
    }
}
$CudnnUtf8NoBom = New-Object -TypeName System.Text.UTF8Encoding -ArgumentList $false
$CudnnNoticeManifest = @{
    schema_version = 1
    cudnn_archive = 'cudnn-windows-x86_64-9.10.2.21_cuda12-archive.zip'
    cudnn_version = $CudnnVersion
    upstream_release_metadata = 'https://github.com/pytorch/pytorch/blob/9d06effee01af3b8a06988b18cc724037ca03940/RELEASE.md'
    eula_url = $CudnnEulaUri
    eula_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $CudnnEulaPath).Hash.ToLowerInvariant()
    acknowledgements_url = $CudnnAcknowledgementsUri
    acknowledgements_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $CudnnAcknowledgementsPath).Hash.ToLowerInvariant()
}
$CudnnManifestJson = $CudnnNoticeManifest | ConvertTo-Json -Depth 5
[System.IO.File]::WriteAllText(
    (Join-Path $LicenseDir 'NVIDIA_CUDNN_NOTICE_MANIFEST.json'),
    $CudnnManifestJson + [Environment]::NewLine,
    $CudnnUtf8NoBom
)

$ManifestModels = @()
foreach ($Model in $ModelSources) {
    $Destination = Join-Path $Models $Model.Folder
    $IntegrityRecord = @($IntegrityRecords | Where-Object { $_.repo -eq $Model.Repo }) | Select-Object -First 1
    if (-not $IntegrityRecord) { throw "Verified Qwen weight hashes are missing from report: $($Model.Repo)" }
    $ManifestModels += @{
        repo = $Model.Repo
        revision = $Model.Revision
        folder = $Model.Folder
        kind = $Model.Kind
        config_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $Destination 'config.json')).Hash.ToLowerInvariant()
        speech_tokenizer_config_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $Destination 'speech_tokenizer/config.json')).Hash.ToLowerInvariant()
        model_sha256 = [string]$IntegrityRecord.model_sha256
        speech_tokenizer_sha256 = [string]$IntegrityRecord.speech_tokenizer_sha256
        model_bytes = [long]$IntegrityRecord.model_bytes
        speech_tokenizer_bytes = [long]$IntegrityRecord.speech_tokenizer_bytes
    }
}
$AssetManifest = @{
    schema_version = 1
    models = $ManifestModels
    speaker_seed = @{ repo = 'Clear-Bible/speaker-quotations'; revision = $SeedCommit }
    qwen_package = 'qwen-tts==0.1.1'
    transformers = 'transformers==4.57.3'
}
$ManifestPath = Join-Path $Models 'KJV_QWEN_ASSET_MANIFEST.json'
$ManifestJson = $AssetManifest | ConvertTo-Json -Depth 8
$Utf8NoBom = New-Object -TypeName System.Text.UTF8Encoding -ArgumentList $false
[System.IO.File]::WriteAllText($ManifestPath, $ManifestJson + [Environment]::NewLine, $Utf8NoBom)
Write-Host "Pinned Qwen asset manifest written: $ManifestPath"
Write-Host 'All pinned Qwen model files, model configurations and speaker-attribution data are present and verified.'
Write-Host 'The speaker mapping remains provisional because the dataset is not KJV-specific.'
