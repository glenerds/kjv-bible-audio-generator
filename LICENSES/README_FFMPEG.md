# FFmpeg build evidence required for Windows packaging

The application uses FFmpeg for MP3 encoding/decoding and loudness normalization. The build script intentionally refuses an arbitrary `ffmpeg.exe`.

Before a Windows build, provide all three files:

- `ffmpeg.exe` in the project root
- `LICENSES/FFMPEG_LICENSE.txt` containing the exact LGPL license text
- `LICENSES/FFMPEG_BUILD_MANIFEST.json` based on `FFMPEG_BUILD_MANIFEST.template.json`, with the exact binary SHA-256, version line, complete build-configuration line, source URL, binary download URL, license SPDX identifier, license filename and license SHA-256

The build accepts LGPL-2.1-or-later or LGPL-3.0-or-later, but requires the exact license version in `ffmpeg -L`, the named license text and its SHA-256. It checks the manifest hash against the binary, compares version/configuration, rejects `--enable-gpl` and `--enable-nonfree`, checks for `libmp3lame`, then performs a synthetic WAV → MP3 → decode cycle.

Do not copy the template to the required manifest without replacing every placeholder. A manifest and binary are still not, by themselves, legal clearance: inspect every linked codec/library, preserve all notices, provide matching source or a valid source offer as required, and obtain a commercial-distribution review. FFmpeg's license can change with build configuration.

## Audited LGPLv3 candidate — native Windows technical checks passed

The BtbN/FFmpeg-Builds Windows x64 static LGPL archive used for this candidate is 179,056,458 bytes, SHA-256 `78d1f7728fef503b50a6de5866950a96d7e4db0fdb9dfaa47fc2c6691a48370b`, source commit `b9ebe81995b58cd4e3177a6c0ad5dc2392f7f7fd`.

Native Windows GitHub Actions run `45623835915` verified the archive size and hash, ran the executable, checked `-version`, `-L` and the full build configuration, confirmed LGPL version 3, confirmed no `--enable-gpl` or `--enable-nonfree` switches, found `libmp3lame`, and completed a WAV → MP3 encode → decode test.

- Version line: `ffmpeg version N-129288-gc81e35cf2b-20261125 Copyright (c) 2000-2026 the FFmpeg developers`.
- Executable SHA-256: `3209f0ba6096189de3f850f65488bdb535177b7e46e0b16e902b3230c5ff74fe`.
- License file SHA-256: `da7eabb7bafdf7d3ae5e9f223aa5bdc1eece45ac569dc21b3b037520b4464768`.
- All 35 dependency notice files passed SHA-256 and byte-size verification against the generated notice manifest.
- The workflow artifact includes the Windows executable, build manifest, exact LGPL license file, notice directory and audit report: https://github.com/glenerds/kjv-bible-audio-generator/actions/runs/45623835915 (artifact ID `15027341337`, 14-day retention).

**Technical checks passed; not yet approved for application distribution.** A human must still review all linked codecs/libraries, full source and relinking/source-offer obligations, notice sufficiency and distribution terms. Do not use a different `latest` archive: the fixed archive digest is mandatory.
Candidate release: https://github.com/FFmpeg-Builds/FFmpeg-Builds/releases/tag/latest
Binary: https://github.com/FFmpeg-Builds/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-lgpl.zip
Build source: https://github.com/FFmpeg-Builds/FFmpeg-Builds/tree/b9ebe81995b58cd4e3177a6c0ad5dc2392f7f7fd


## Importing FFmpeg documentation and dependency notices

After extracting the chosen static Windows FFmpeg package, run `tools/import_ffmpeg_notices.ps1 -ExtractedFfmpegPackage <extracted-package-folder>`. The importer requires the package `LICENSE.txt` and `doc/` folder, copies their contents into `LICENSES/`, and writes a no-BOM manifest containing every copied file's relative path, byte count and SHA-256. The Windows builder refuses to package unless every listed file matches and there are no unlisted/missing notice files. This records the exact notice set; a human must still review whether the notices and corresponding source/relinking obligations are complete for the exact build.
