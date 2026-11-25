# Engineering Checkpoint — KJV Bible Audio Generator 0.4.4

Date: 2026-11-24. Separate from legacy KJV Bible Reader / USB Builder.

## Target
A self-contained Windows app imports KJV and generates 1,189 named chapter MP3s in canonical order with speaker IDs and verse/sub-verse cues, stable recurring character voices, durable queue, pause/resume, safe stop, bounded retry, restart recovery and USB portability. No separate customer Python/packages/WSL/Qwen/models/FFmpeg setup. No dedicated GPU requirement. Do not ask the user to test until genuine Qwen and native Windows release gates pass.

## 0.4.4 changes
- Added `tools/import_ffmpeg_notices.ps1` to import the extracted FFmpeg distribution's complete `doc/` directory and package `LICENSE.txt`.
- Added `tools/ffmpeg_notices.py`: import mode copies notices and generates a manifest with every relative path, byte size and SHA-256; verify mode checks all hashes and the exact file set.
- Verifier rejects missing/changed notice files, extra/unlisted files, duplicate or unsafe paths, and symlinks.
- Windows builder now invokes notice verification before PyInstaller; incomplete third-party notice sets block packaging.
- Regression tests cover import/verify success, changed-file rejection and extra/unlisted-file rejection.

## Prior Qwen/FFmpeg work retained
- Qwen 0.1.1 ICL prompts preserve `ref_text` and reconstruct official prompt-item attributes; old prompt migration is safe/fail-closed.
- FFmpeg builder accepts LGPL 2.1 or LGPL 3, checks version/configuration, exact license version and text hash, rejects GPL/nonfree, requires libmp3lame and performs an encode/decode probe.
- BtbN candidate recipe is source-audited but archive/executable was not downloaded or binary-verified.

## Test record
Most recent recorded environment: Linux x86_64, Python 3.13.5, PyTorch 2.10 CPU-only, FFmpeg 7.1.5, about 5.8GB RAM/3 CPU cores. No CUDA, Qwen runtime/weights, PowerShell/Wine, PyInstaller or Windows FFmpeg. Hugging Face DNS resolution unavailable.

- Xvfb pytest: **97 passed**.
- Notice tests import a synthetic package documentation set, verify every file hash, detect same-size tampering and unlisted files, reject symlinked source docs, and reject malformed manifest entries.
- After README/handoff synchronization: compileall PASS; Xvfb pytest **97 passed**.
- Genuine Qwen audio and native Windows build remain untested.

## Release blockers
- Obtain and inspect actual LGPL Windows FFmpeg distribution, executable, complete licenses/notices, source revision and MP3 probe.
- Load pinned Qwen VoiceDesign/Base models on network-enabled Windows 11 / Python 3.12, offline.
- Generate/listen to genuine Genesis 1, verify cues, then reuse a recurring character profile in a later chapter.
- Run actual-model queue interruption/recovery and long generation.
- Build and test Windows one-folder app, fresh extraction, offline launch, playback and USB relocation.
- Measure CPU speed/peak RAM and validate all 1,189 outputs; complete KJV cast review and licensing.

## Exact resume point
0.4.4 notice preservation code is in place. 0.4.4 wheel and source ZIP are now built, the isolated wheel install passed, and fresh ZIP extraction passed compileall plus 97 tests. Continue FFmpeg distribution acquisition/verification, but do not claim binary approval without the actual archive and executable.
