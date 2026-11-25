# Engineering Checkpoint — KJV Bible Audio Generator 0.3.2

Date: 2026-11-24, current conversation session.

## Assignment and acceptance target

Build a separate, self-contained Windows application for the complete KJV Bible. It must render Genesis 1 through Revelation 22 to 1,189 separately named chapter MP3s, with verse/sub-verse cue metadata and recurring character voice identities. Import/paste input; one Generate Entire Bible command; durable queue, checkpoint, pause/resume, safe stop, retry and restart recovery. End users must not install Python, packages, models, FFmpeg, WSL or edit config. A GPU is not a customer requirement. No customer testing until real Qwen + native Windows release gates pass.

## 0.3.2 changes made

1. Set `pyproject.toml` and package `__version__` to 0.3.2.
2. Qwen model asset preparation pins VoiceDesign and Base snapshots and checks all expected model/tokenizer/speech-tokenizer files, minimum weight sizes and JSON model/task types.
3. Speaker data preparation pulls pinned Clear/MACULA TSV data and verifies exact upstream Git blob SHA-1 values; writes CC BY 4.0 attribution and preserves Glyssen/FCBH MIT licensing.
4. Added in-verse explicit double-quote splitting: unquoted narration goes to narrator; quoted span goes to the verse-assigned speaker. It is conservative and does not cover multiple speakers in one quote or quote spans continued across verse boundaries.
5. Made Windows build select explicit PyTorch 2.10.0 / torchaudio 2.10.0 CPU or CUDA 12.8 packages, with Python 3.12 and pinned Qwen/Transformers/Accelerate.
6. Added strict FFmpeg validation requirements: manifest, exact binary SHA-256, exact version/build configuration, LGPL build only, reject GPL/nonfree, require `libmp3lame`, and run a synthetic WAV-to-MP3 decode cycle.
7. Added FFmpeg manifest template and licensing instructions. No binary or finished manifest is included; build remains blocked until supplied.
8. Added tests around build requirements, model preparation, version metadata and quote splitting.

## Tests actually executed

Host: Linux x86_64; Python 3.13.5; PyTorch 2.10.0+cpu; CUDA unavailable; system FFmpeg 7.1.5; no Qwen runtime, model weights, PowerShell, Wine, PyInstaller or Windows FFmpeg.

- `python -m compileall -q src tests`: PASS.
- `xvfb-run -a env PYTHONPATH=src pytest -q`: **56 passed**.
- Tests cover parser/import and chapter structure; SQLite queue and simulated worker; synthetic MP3/cues; fake Qwen adapter/profile cache; Tk GUI under Xvfb; static PowerShell build contracts.
- No actual Qwen speech, no actual Genesis 1, no Windows PowerShell test and no EXE build.

## Official model sizing and preparation

Official HF listings show Qwen VoiceDesign about 4.52 GB and Base about 4.54 GB, approximately 9.06 GB combined. The exact pinned snapshots are referenced in `tools/prepare_assets.ps1`. Build-time downloads are intended; the models are not in this archive. Qwen's upstream README recommends an isolated Python 3.12 setup. PyTorch's 2.10.0 install matrix has CPU and CUDA 12.8 Windows wheels.

## Hard blockers before user test

- Run `prepare_assets.ps1` under native 64-bit Windows Python 3.12; fetch/verify both models and attribution data.
- Provide actual LGPL FFmpeg Windows binary, manifest and license evidence; verify binary SHA and MP3 encoding/decoding.
- Load official Qwen VoiceDesign/Base offline; pass real self-test.
- Generate and listen to authentic KJV Genesis 1 (all 31 verses), inspect MP3 and per-verse cue alignment.
- Reuse one character's persisted voice profile in another chapter and assess consistent voice identity.
- Actual-model pause/resume/stop/retry/restart and long-run tests.
- PyInstaller Windows build, fresh extraction, offline launch, Windows playback, portable and USB relocation.
- CPU-only and CUDA performance/peak RAM benchmark. No minimum system spec can be stated yet.
- Complete speaker editor and KJV-specific attribution. MACULA is a non-KJV-specific seed; quoted-span split remains only partial.
- Full Bible generation, 1,189 audio/cue integrity checks, output size check, licensing and commercial review.

## Exact resume point

Continue by running native Windows model preparation/build. Do not treat this source prototype or the fake/synthetic tests as the app the user can test. First user-facing candidate only after genuine Genesis 1, cross-chapter voices, Windows offline build, audio playback and recovery all pass.
