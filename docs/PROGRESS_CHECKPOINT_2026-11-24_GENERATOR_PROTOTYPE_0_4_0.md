# Engineering Checkpoint — KJV Bible Audio Generator 0.4.0

Date: 2026-11-24. Separate from legacy KJV Bible Reader / USB Builder.

## Target
Self-contained Windows app imports KJV and generates 1,189 canonical chapter MP3s with stable recurring voices and verse/sub-verse cues. Durable queue, pause/resume, safe stop, bounded retries, restart recovery and integrity. No customer Python/models/FFmpeg/config installation and no dedicated GPU requirement. Do not request user testing before genuine Qwen and native Windows acceptance pass.

## 0.4.0 — speaker review queue
The Review Verse Speakers GUI now filters among: All verses, Needs review, and Manual overrides. A verse marked ambiguous by the provisional speaker seed displays the candidate labels. Saving an exact source-text speaker split records the manual override and removes the verse from Needs review. Clearing the manual override restores it to Needs review; the original seed candidate list remains in the attribution metadata for audit.

Regression test imports a two-verse document, stores ambiguity candidates for both, switches to Needs review, verifies both refs appear, saves the first as God, then verifies only the second remains in the queue and the seed candidates remain preserved.

## 0.3.9 — pending-chapter voice preparation
Worker collects speaker IDs only from pending chapters. Completed Moses chapter + pending Jesus chapter test verifies only the pending Jesus voice is prepared.

## 0.3.8 — multi-profile reference metadata
Every Qwen prompt-work item carries its own external reference WAV path. Test prepares Moses and Jesus from different external WAVs plus an internally designed narrator, removes both source WAVs and verifies all three cached prompts reload.

## Earlier core functionality retained
- Canonical narrator identity across all 13 book labels; Jesus-child alias; composite ambiguity review.
- Character profile and exact-text per-verse multi-speaker editors.
- Missing external reference fail-closed; portable intact prompt reuse; prompt tamper checks.
- SQLite SHA-256 MP3/cue audit, additive schema migration and corrupted output requeue.
- Full 31,102-reference parser validation; Genesis 1 synthetic pipeline (31 KJV verses, 33 cues).

## Verification
- compileall: PASS.
- GUI subset: **9 passed**.
- Full Xvfb pytest: **83 passed**.
- Package version 0.4.0 wheel build and fresh-install verification still required after the final source update.
- Current host: Linux x86_64, Python 3.13.5, PyTorch 2.10 CPU-only, FFmpeg 7.1.5, 3 CPU cores, ~5.8GB RAM. No CUDA, Qwen runtime/weights, PowerShell/Wine, PyInstaller or verified Windows FFmpeg; Hugging Face DNS unavailable.

## Still unpassed
No genuine Genesis 1 Qwen speech or later-chapter audio comparison; real-model interruption/restart; Windows build/offline/playback/USB; CPU/peak-RAM benchmarks; 1,189-chapter generation/size; full KJV attribution review and third-party license review.

## Exact resume point
Continue with prototype 0.4.0. The current source suite passes 83 automated tests. Rebuild/install the wheel and clean source ZIP, then continue Qwen/voice and Windows packaging review. Real speech and Windows validation require a network-enabled native Windows 11 / Python 3.12 environment with pinned model snapshots and verified LGPL FFmpeg.
