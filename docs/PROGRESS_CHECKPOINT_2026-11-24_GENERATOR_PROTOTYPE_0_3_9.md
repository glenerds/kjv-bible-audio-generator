# Engineering Checkpoint — KJV Bible Audio Generator 0.3.9

Date: 2026-11-24. Separate from legacy KJV Bible Reader / USB Builder.

## Target
Self-contained Windows app imports KJV and generates 1,189 canonical chapter MP3s with stable character voices and verse/sub-verse cues. Durable queue, pause/resume, safe stop, bounded retries, restart recovery and integrity. No customer Python/models/FFmpeg/config installation and no dedicated GPU requirement. Do not request user testing before genuine Qwen and native Windows acceptance pass.

## 0.3.9 pending-chapter optimization
The worker used to collect speaker profiles across the whole Bible before generating any remaining chapter. On a resumed job this needlessly prepared Qwen profiles for characters whose chapters were already complete. The worker now checks durable queue rows after reconciliation, builds the pending chapter list, and prepares only profiles referenced by those pending chapters.

Regression test: create a two-chapter Bible with Moses attributed to Genesis 1 and Jesus to Genesis 2; mark Genesis 1 complete with a real synthetic MP3/cue pair and leave Genesis 2 pending; run the worker and assert only the Jesus profile is prepared while both chapters remain complete.

## 0.3.8 multi-profile reference metadata fix retained
Each Qwen prompt-work tuple carries the exact external reference WAV path for its profile. The adapter no longer accidentally writes the final loop iteration's WAV path into every profile manifest. New test uses two distinct external WAVs and one generated narrator, removes both external WAV files and verifies all saved prompts reload without re-designing voices.

## Other implemented
- Canonical narrator identity across all 13 book labels; Jesus-child alias; composite speaker ambiguity review.
- Character profile and exact-source-text verse segment editors.
- Missing external reference fail-closed for new voice prompt; intact prompt portability; tamper detection.
- SQLite SHA-256 output/cue audit, migration, missing/tampered file recovery, completed project no-op.
- Full 31,102 reference-line parsing validation.
- Complete Genesis 1 synthetic pipeline, 31 KJV verses and 33 cues.

## Test results
- compileall: PASS.
- Xvfb pytest: **82 passed**.
- 31,102-line reference parser validates 66 books / 1,189 chapters / 31,102 verses.
- Genesis 1 integration is synthetic test audio, not Qwen.
- Qwen adapter uses fake model.

## Environment / blockers
Linux x86_64, Python 3.13.5, PyTorch 2.10 CPU-only, FFmpeg 7.1.5, 3 CPU cores and ~5.8 GB RAM. No CUDA, Qwen runtime/weights, Windows PowerShell/Wine, PyInstaller or verified Windows FFmpeg. Hugging Face DNS resolution fails here.

Still unpassed: genuine Genesis 1 Qwen audio, later-chapter voice comparison, real-model stop/retry/restart/long-run, Windows build/offline/playback/USB, CPU/peak-RAM benchmark, 1,189-chapter full audio output, KJV cast review and licensing.

## Exact resume point
Continue from source 0.3.9. The 0.3.8 multi-external-reference bug and 0.3.9 pending-profile preparation optimization are covered by regression tests. Next, build/install the wheel, fresh-extraction ZIP retest and continue reviewing model/Windows packaging. Real speech and Windows packaging require a network-enabled native Windows 11 / Python 3.12 environment with the pinned models and a verified LGPL FFmpeg binary.
