# FFmpeg build evidence required for Windows packaging

The application uses FFmpeg for MP3 encoding/decoding and loudness normalization. The build script intentionally refuses an arbitrary `ffmpeg.exe`.

Before a Windows build, provide all three files:

- `ffmpeg.exe` in the project root
- `LICENSES/FFMPEG_LICENSE.txt` containing the exact LGPL license text
- `LICENSES/FFMPEG_BUILD_MANIFEST.json` based on `FFMPEG_BUILD_MANIFEST.template.json`, with the exact binary SHA-256, version line, complete build-configuration line, source URL, binary download URL, license SPDX identifier, license filename and license SHA-256

The build accepts LGPL-2.1-or-later or LGPL-3.0-or-later, but requires the exact license version in `ffmpeg -L`, the named license text and its SHA-256. It checks the manifest hash against the binary, compares version/configuration, rejects `--enable-gpl` and `--enable-nonfree`, checks for `libmp3lame`, then performs a synthetic WAV → MP3 → decode cycle.

Do not copy the template to the required manifest without replacing every placeholder. A manifest and binary are still not, by themselves, legal clearance: inspect every linked codec/library, preserve all notices, provide matching source or a valid source offer as required, and obtain a commercial-distribution review. FFmpeg's license can change with build configuration.

## Audited LGPLv3 candidate (not yet binary-verified)

The BtbN/FFmpeg-Builds release was refreshed on 2026-11-25. The current Windows x64 **LGPL, static** asset is `ffmpeg-master-latest-win64-lgpl.zip`, 179,056,458 bytes, with the GitHub release asset digest SHA-256 `78d1f7728fef503b50a6de5866950a96d7e4db0fdb9dfaa47fc2c6691a48370b`. The release tag still resolves to source commit `b9ebe81995b58cd4e3177a6c0ad5dc2392f7f7fd`. The exact recipe previously inspected at that commit selects `variants/win64-lgpl.sh`, which uses `--enable-version3 --disable-debug` and `COPYING.LGPLv3`; `scripts.d/50-libmp3lame.sh` enables `--enable-libmp3lame`.

The new 2026-11-25 archive has **not yet been downloaded or internally inspected**. Do not copy the prior 2026-11-24 archive digest forward. Before use, the exact archive digest above must match, then the contained `ffmpeg.exe` must pass `-version`, `-L`, configuration, `libmp3lame`, notice import/verification, and WAV→MP3→decode testing. The release URL uses a mutable `latest` tag; the digest check is mandatory.

Candidate release: https://github.com/FFmpeg-Builds/FFmpeg-Builds/releases/tag/latest
Binary: https://github.com/FFmpeg-Builds/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-lgpl.zip
Build source: https://github.com/FFmpeg-Builds/FFmpeg-Builds/tree/b9ebe81995b58cd4e3177a6c0ad5dc2392f7f7fd


## Importing FFmpeg documentation and dependency notices

After extracting the chosen static Windows FFmpeg package, run `tools/import_ffmpeg_notices.ps1 -ExtractedFfmpegPackage <extracted-package-folder>`. The importer requires the package `LICENSE.txt` and `doc/` folder, copies their contents into `LICENSES/`, and writes a no-BOM manifest containing every copied file's relative path, byte count and SHA-256. The Windows builder refuses to package unless every listed file matches and there are no unlisted/missing notice files. This records the exact notice set; a human must still review whether the notices and corresponding source/relinking obligations are complete for the exact build.
