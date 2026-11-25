# Engineering Checkpoint — KJV Bible Audio Generator 0.3.4

Date: 2026-11-24. Separate from legacy KJV Bible Reader / USB Builder.

## User acceptance target

A self-contained Windows app imports the complete KJV, preserves reviewed recurring voice identities and verse-level speaker segmentation, and generates 1,189 chapter MP3s with timestamps. Durable queue, pause/resume, safe stop, retries and restart recovery are required. No customer installs/configuration, no dedicated GPU requirement. Do not ask user to test before genuine Qwen/Windows gates pass.

## 0.3.4 improvements

- Added SHA-256 fingerprint columns `output_sha256` and `cue_sha256` to SQLite jobs.
- Existing queues are migrated additively using `PRAGMA table_info` and `ALTER TABLE`.
- Completion refuses to mark a row complete unless both MP3 and cue files exist; fingerprints are calculated and stored.
- Startup re-hashes both files. Missing hash, missing file, same-size tampering or cue schema/timing error requeues the chapter. Legacy completed rows without hashes are requeued one time.
- Worker avoids loading the Qwen models for an already complete, integrity-verified project.
- Persisted manual verse segments must still match the current imported verse exactly at generation time.

## Current verification

Host: Linux x86_64, Python 3.13.5, PyTorch 2.10.0+cpu, system FFmpeg 7.1.5, ~5.8 GB RAM and 3 CPU cores. No CUDA, Qwen runtime/weights, Windows PowerShell/Wine, PyInstaller or Windows FFmpeg. Hugging Face DNS unavailable.

- compileall PASS.
- Xvfb pytest: **74 passed**.
- Wheel built/installed: 0.3.4, 43,989 bytes, SHA-256 `346bfb6741512e81d489fe4d52c3636e799b3e10c189749c9b7f94b0e9d53512`. Installed module version and canonical metadata (66/1,189/31,102) verified.
- New tests prove same-size MP3 corruption and same-size cue changes trigger requeue/regeneration; older schema migration adds hash columns and requeues unverified completions; missing output pairs cannot be marked complete.
- Full Genesis 1 fixture runs through parser, exact manual speaker splits, worker and MP3 assembly, producing a decodable synthetic MP3 and 33 cue segments. It is not Qwen speech.
- Fresh source ZIP passed CRC/integrity; clean extraction, compileall and full **74 tests passed** again. Exact size/checksum are recorded outside the ZIP in the external GitHub source-archive record.
- `--self-test` expected exit 2; `--audio-smoke` expected exit 3, due absent runtime/models/Windows FFmpeg.

## Remaining release gates

- Native Windows asset prep and offline load of pinned VoiceDesign/Base Qwen model trees.
- Verified LGPL `ffmpeg.exe`, license, build manifest and actual binary MP3 probe.
- Real 31-verse Genesis 1 MP3 and later-chapter character voice reuse/listening.
- Real Qwen pause/stop/retry/restart/long-run tests.
- Windows one-folder build, clean extraction, offline launch, audio playback and USB path test.
- CPU performance/peak RAM, full 1,189 MP3/cue/hash/size validation.
- KJV-specific full cast attribution, ambiguity review and legal/commercial license check.

## Exact resume point

The 0.3.4 wheel and clean source archive are built and independently verified. The 74-test suite passes both in the source tree and fresh extraction. Continue Qwen/Windows gates only on a machine that has network access to official model repositories, enough memory/storage and native Windows tooling. This host cannot perform those gates.
