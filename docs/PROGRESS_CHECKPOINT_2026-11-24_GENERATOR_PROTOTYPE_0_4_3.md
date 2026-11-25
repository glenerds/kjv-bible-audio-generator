# Engineering Checkpoint — KJV Bible Audio Generator 0.4.3

Date: 2026-11-24. Separate from legacy Reader / USB Builder.

## Target
One self-contained Windows app imports KJV and generates 1,189 canonical chapter MP3s, with verse/sub-verse cues and stable recurring voices. Durable queue, pause/resume, safe stop, bounded retry, restart recovery and USB relocation. No customer setup and no GPU requirement. No user test until actual Qwen and Windows release gates pass.

## 0.4.3 changes
- Windows FFmpeg license manifest accepts LGPL-2.1-or-later or LGPL-3.0-or-later, requires matching executable `-L` version, exact license file and license SHA-256.
- Static LGPLv3 BtbN candidate source audit: source repo commit `b9ebe81995b58cd4e3177a6c0ad5dc2392f7f7fd`; `win64-lgpl.sh` uses `defaults-lgpl.sh` (`--enable-version3 --disable-debug`, `COPYING.LGPLv3`) and enabled `50-libmp3lame.sh` adds `--enable-libmp3lame`.
- Candidate release archive asset size 179,049,798 bytes, GitHub-provided digest `3639382f80af8849c7e11b11f3f379992e2f1925fe95fcee262cbe242a005b84`. Archive download failed; executable and actual build outputs remain unverified.
- Official Qwen 0.1.1 ICL prompt fix from 0.4.2 remains: save transcript, reconstruct object prompt items, safe old prompt migration.

## Verified
Host: Linux x86_64, Python 3.13.5, Torch CPU-only, FFmpeg 7.1.5, no Qwen runtime/models, no PowerShell/Wine/PyInstaller/Windows FFmpeg, ~5.8GB RAM / 3 cores, Hugging Face DNS unavailable.

- compileall PASS.
- Xvfb pytest **93 passed**.
- Wheel kjv_audio_generator-0.4.3-py3-none-any.whl, 51,034 bytes, SHA `a544c14a1fe8f134c84878649ac8c3b6d7e05a3d49c53f994f7526169dc2b122`; clean target installation and 66/1,189/31,102 metadata verified.
- Developer source ZIP KJV_Audio_Generator_Developer_Source_0_4_3_2026-11-24.zip, 143,297 bytes / 73 entries; fresh extraction, compileall and 93 tests pass. Adjacent checksum sidecar has SHA-256.
- Installed preflight correctly fails: self-test exit 2; audio-smoke exit 3; models/runtime/manifest/Windows FFmpeg are not available.
- No genuine Qwen audio or Windows package.

## Next
Obtain and inspect the pinned FFmpeg archive/executable on Windows; verify binary SHA, exact LGPL license and dependencies, source revision, no GPL/nonfree, `libmp3lame` and actual encode/decode. Then run Qwen Genesis 1 and cross-chapter voice reuse; real recovery, Windows package, playback/offline/USB and CPU/RAM tests.
