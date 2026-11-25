# Continuation handoff — 2026-11-25 (direct engineering resumed)

The user has asked to return to having ChatGPT perform the engineering and testing directly, rather than relying on external AI reviewers. This handoff is recorded before further code engineering so the project state can be recovered in a new chat.

## What has been done so far

- The separate public GitHub repository `https://github.com/glenerds/kjv-bible-audio-generator` was created by the user. It is separate from the original private `glenerds/glenerds-apps` backup repository, so unrelated projects were not made public.
- The public repository was verified as public and initially empty. The 0.4.10 project source, application package, test files, Windows tools, documentation and AI-review instructions were then published.
- The public repository tree was checked: 87 entries total, including 18 files under `src/kjv_audio_generator/` and 10 test files. The README, source directory, test directory, AI review start page and review prompt were fetched successfully through GitHub and verified accessible.
- The AI review prompt was corrected to use the new public repository links, not the old private repository paths.
- The project was previously at developer-prototype version **0.4.10**. The recorded baseline is **123 automated tests passed**, with 45 focused regressions passed, compileall passing, and clean source-archive extraction passing.
- The user decided to stop coordinating external AI reviews and have ChatGPT continue engineering and testing directly.

## Current verified starting state

- Repository: `glenerds/kjv-bible-audio-generator`
- Default branch: `main`
- Version baseline: `0.4.10`
- The public source has been published and is accessible, but the actual product remains a developer prototype, not a customer-ready Windows application.
- The documented full-suite baseline is 123 passing tests. This must be independently rerun against the current public source before being reported as the current result.
- Earlier GitHub Actions attempts failed before runner allocation; no hosted test steps executed. Do not count those attempts as passing or failing code tests.

## Remaining release blockers — do not claim these passed

- Genuine Qwen model installation/loading and real Genesis 1 speech generation.
- Listening validation and recurring-character voice consistency across separate chapters.
- Native Windows build, startup, MP3 playback and offline launch.
- Bundled Windows FFmpeg binary, MP3 encoder probe, licensing and notice verification.
- USB relocation and drive-letter-change behavior.
- Real-model interruption/restart recovery and extended generation.
- CPU/RAM/VRAM and generation-speed benchmarks.
- Full 1,189-chapter production and measured final MP3 collection size.
- Complete KJV dialogue/speaker attribution and software/model/codec/data licensing review.

The prior development host did not have the `qwen_tts` runtime or model weights, could not resolve Hugging Face, and had no native Windows/PowerShell/Wine environment. Do not substitute synthetic audio for real Qwen inference or imply that hosted tests ran when no runner was allocated.

## Work plan for the next engineering passes

1. Reconcile the published public repository against the canonical 0.4.10 developer source archive; check that all expected package files, tests, Windows scripts, model-preparation code and project records are present.
2. Independently rerun the full test suite from the public repository snapshot and from a fresh source archive extraction. Record exact commands, versions, environment and output.
3. Audit Windows asset preparation, model-weight integrity verification, dependency pinning, packaging scripts, FFmpeg binary selection and license-notice handling.
4. Audit the Qwen backend and adapter against verifiable upstream APIs and model requirements. Distinguish static/API review from genuine inference.
5. Fix concrete offline-verifiable defects in small, versioned changes with regression tests.
6. Update this README, `docs/RESUME_HERE.md` and `docs/DEVELOPMENT_STATUS.md` after meaningful engineering work.
7. Do not ask the user to install or test the prototype until genuine Qwen speech and native Windows acceptance tests have passed.

## User's continuing instructions

- Keep work in the current response; do not imply background or asynchronous work.
- When pausing, explicitly tell the user that work is paused.
- On every future "keep working" instruction, update the README first, recording the starting state and intended work, before engineering changes.
- The README and resume guide are the recovery record if the conversation is disconnected or moved to a new chat.

---

> **Public source snapshot:** This repository publishes the KJV Bible Audio Generator developer prototype 0.4.10 for independent inspection. It is not a customer-ready Windows application.
>
> **Independent AI review:** Start with [AI_REVIEW_START_HERE.md](AI_REVIEW_START_HERE.md) and follow [AI_REVIEW_PROMPT.md](AI_REVIEW_PROMPT.md).
>
> **Repository:** https://github.com/glenerds/kjv-bible-audio-generator

---

# KJV Bible Audio Generator — developer prototype 0.4.10

**Developer prototype only. Not a customer-ready Windows application. Do not install or test this as the finished product.** Separate from the legacy KJV Bible Reader / USB Builder.

## End-product requirements

A self-contained Windows desktop app imports or accepts KJV Bible text, lets the user review recurring character profiles and speech assignments, and generates all 66 books in canonical order: 1,189 named chapter MP3s, with verse/sub-verse cues and stable character voice identities. It must support durable queue progress, pause/resume, safe stop, bounded retries, restart recovery and selective regeneration after voice changes. The customer must not separately install Python, packages, models, Qwen, FFmpeg or WSL. A dedicated GPU cannot be a requirement; CPU speed and peak memory must be measured. The target for the final chapter-MP3 collection is below 16 GB.

## Continuation log — 2026-11-24 (README updated before this work session)

The user explicitly requires this README to be updated **before any further engineering whenever they say “keep working.”** This entry is that pre-work update. Do not skip this step on future continuation turns.

### Verified starting point
- Active source: `/mnt/data/kjv-audio-generator-work/`, package version 0.4.9.
- Last reported baseline: **116 automated tests passed** from the source tree and from a fresh 72-file source-archive extraction; compileall and ZIP integrity passed.
- Version 0.4.9 routes the remaining JSON outputs and finalized MP3 copies through atomic replacement. The installed wheel verifies 66 books, 1,189 chapters and 31,102 verse entries.
- Developer ZIP and wheel are backed up in the ChatGPT Library and were also linked in the prior handoff. GitHub project docs now point to 0.4.9 / 116 tests.
- No genuine Qwen Genesis 1 audio, native Windows app, approved Windows FFmpeg executable, offline Windows playback, USB test, full-Bible run or CPU/RAM benchmark has passed. Do not ask the user to test the prototype.

### Work completed in this continuation
1. Audited application, Qwen backend and FFmpeg notice persistence paths. Found direct reference-WAV writes, a fixed `.pt.tmp` Qwen prompt path and destructive FFmpeg notice replacement; fixed all three.
2. Added `atomic_output_path()` with unique same-directory staging, final-extension preservation, non-empty output validation, fsync and atomic replacement. Applied it to SoundFile WAVs and torch prompt assets.
3. Changed FFmpeg notice import to stage/copy/hash/verify the entire package and license before swapping them. Added rollback if a commit step fails.
4. Focused regression suite: 45 passed. Full suite: 123 passed. Compileall: passed.
5. Version 0.4.10 wheel installed in an isolated target; KJV structure 66 / 1,189 / 31,102 verified. Fresh 73-file source ZIP extraction, integrity, compileall and 123 tests passed.
6. Real Qwen remains blocked: `qwen_tts` is not installed and Hugging Face DNS resolution fails. No actual model/audio or Windows toolchain is present. Both installed-wheel preflights correctly fail closed.
7. README, resume guide, development status, checkpoint, downloads/archive notes and GitHub pointers updated to the verified 0.4.10 state.

## Implemented through 0.4.10

### 0.4.10 — atomic files for Qwen assets and transactional FFmpeg notice imports
- Added `atomic_output_path()`: a unique same-directory staging path that preserves the target extension (for example `.tmp.wav`), checks that the writer produced non-empty output, fsyncs the completed file and commits it with `os.replace()`.
- Qwen-generated reference WAVs now use this path, so SoundFile still recognizes the WAV extension and a failed/incomplete voice-design write cannot truncate a previous reference recording.
- Qwen `.pt` clone-prompt tensors now use unique extension-preserving staging plus fsync/atomic replacement instead of the shared fixed `.pt.tmp` path. This prevents concurrent writers from colliding and leaves prior prompt bytes intact on save failure.
- `copy_file_atomic()` now uses the same output-path helper, validates its source is a regular file and fsyncs before replacement.
- FFmpeg license-notice import now copies the new `doc/` tree and `LICENSE.txt` into a staging area, hashes and verifies the entire staged notice set first, then swaps the notice directory and license file with rollback backups. A failed staging copy or mid-commit failure restores the prior bundle; successful re-import removes stale files from the old set.
- Added regression cases for atomic third-party output, extension retention, empty/failed writers, unique staging names, FFmpeg staging failure, FFmpeg pair-commit rollback and successful full-set replacement.

### 0.4.9 — complete the atomic output path
- The final MP3 copy now uses a unique same-directory staging file, flush/fsync and `os.replace()`; failed replacement keeps the previous chapter MP3 intact.
- Chapter cue JSON sidecars, first-run bundled speaker-seed review JSON and backend diagnostic JSON now use the common atomic writer too. A source scan found and removed all remaining direct JSON `write_text()` output paths.
- Added copy/replace regression tests; audio, attribution, GUI/CLI, and persistence tests were rerun.

### 0.4.8 — crash-safe JSON metadata persistence
- Added one shared JSON writer for GUI/CLI review reports, voice registries, attribution maps, Qwen prompt metadata and queue reports.
- Writes to a uniquely named temporary file in the destination directory, flushes and fsyncs it, then uses atomic replacement. A failed serialization, write, fsync or replacement leaves the previous destination intact and removes the temporary file.
- Replaced fixed `.tmp` names, avoiding collisions between simultaneous writers, and covered normal replacement, failed replacement cleanup and serialization failure with regression tests.

### 0.4.7 — GUI speaker import no longer overwrites reviewed work
- The desktop **Import Speaker Data (TSV)** action now loads the existing saved attribution map and uses the same `merge_seed_suggestions()` path as the CLI.
- Exact-text manual verse segments, custom/prepared voice profiles, user-authored ranges, previous review candidates and provenance are retained.
- Same-source re-import replaces only that source's prior suggestions and does not duplicate import history.
- Conflicting suggestions are queued for review and continue to use the neutral unknown-speaker voice until a person resolves them.
- A Tk GUI regression test exercises the real import-button handler twice, including retained manual edits and an overlap conflict.

### 0.4.6 — non-destructive speaker-seed import
- The explicit `--speaker-projections` import now merges suggestions into saved attribution rather than replacing the assignment file.
- Existing exact-text manual verse segments, user-created voice profiles, prior review candidates and untracked user ranges are retained.
- Each suggestion source is tracked separately: re-importing the same source replaces only its previous machine-generated ranges, avoids duplicate source-history entries and preserves edits made since the last import.
- Overlapping speakers from different sources are explicitly queued for review; ambiguous overlaps remain on the neutral unknown-speaker voice until adjudicated.
- Source TSV and details-file SHA-256 values are recorded in import provenance. Regression tests cover preserving a custom profile and manual segment, overlap review and idempotent repeat import.

### Import and structure
- Imports USFM/SFM, ZIP, JSON, reference-per-line text and numbered book/chapter text.
- Validates canonical 66-book structure, 1,189 chapters, 31,102 verses, and each chapter's exact reference verse count. This checks structure/versification, not translation wording.
- A scale test imports 31,102 synthetic verse-reference lines through the application parser. The complete Genesis 1 test fixture contains all 31 authentic KJV verses.

### Speakers and voice review
- Character voice editor: stable speaker IDs, names, aliases, Qwen voice design descriptions, reference scripts and optional external reference WAVs.
- Verse speaker editor supports multiple exact text segments per verse; save and synthesis both verify concatenation preserves source spaces and punctuation.
- Needs-review/manual-override queues and stale assignment checks.
- Thirteen book-labelled narrator aliases normalize to one Bible Narrator; `Jesus (child)` maps to Jesus; ambiguous composite speaker labels remain unassigned for human review.
- MACULA/FCBH attribution is not KJV-specific and remains a provisional review seed. Dataset research found no complete, verified, openly redistributable KJV speaker map; see [Attribution Dataset Research](docs/ATTRIBUTION_DATASET_RESEARCH_2026-11-24.md). Full cast/quotation review is unfinished.

### Qwen character voices
- Pinned Qwen VoiceDesign → Base reusable profile workflow; persistent prompt assets and bounded in-memory cache.
- Voice profiles carry their own reference-audio metadata. External/missing WAVs cannot silently be replaced with another voice. Once a prompt is fully prepared and verified it remains reusable after the source WAV is removed or the project folder is moved.
- Only speaker profiles used by pending chapters are prepared.
- **0.4.2 fixed a critical Qwen 0.1.1 API mismatch:** ICL synthesis requires the reference transcript to build `ref_ids`. Saved prompts now retain `ref_text` and reconstruct the Qwen prompt-item attributes consumed by the upstream wrapper. Earlier four-field dict-only prompts lost the transcript and could fail during real synthesis. Old prompt assets are migrated safely from an available reference WAV; if that is unavailable, the app fails closed.

### Queue, regeneration and portability
- SQLite sequential chapter queue, atomic claims, pause/resume, safe-stop requeue, bounded retry and restart recovery.
- Completed MP3 and cue JSON have SHA-256 fingerprints. Resume verifies them, checks cue chapter/duration/timing, requeues missing/tampered/corrupt outputs, and migrates old hashless rows.
- Chapter generation fingerprints include the speaker/profile inputs, pinned backend/model revision, FFmpeg executable identity, encoder settings and audio pipeline. Changing Moses's voice or a verse assignment regenerates only affected chapters; unrelated outputs keep their hashes.
- Completed chapter paths are rebased to the current project root. A relocated copy of the completed project verifies existing hashes and does not regenerate everything.
- Complete projects skip Qwen model loading on restart.
- MP3 assembly, normalization, FFmpeg decode checks and verse/segment cue JSON.

### Windows preparation and FFmpeg license gate
- Pinned Qwen model snapshots and MACULA source; model folders/configuration/size and upstream Git blob hashes checked; Qwen asset manifest written UTF-8 without BOM.
- Windows builder targets 64-bit Python 3.12 with explicit Torch/Torchaudio CPU or CUDA 12.8 wheel selection.
- FFmpeg manifest must identify a matching executable SHA-256, version/build configuration, LGPL license/version, named license-text file and license SHA-256. `--enable-gpl` and `--enable-nonfree` are rejected; `libmp3lame` must be present and a WAV→MP3→decode probe must pass.
- Builder now accepts either LGPL-2.1-or-later or LGPL-3.0-or-later, and verifies the executable's `-L` output agrees with the manifest. LGPLv3 is needed by the current candidate; previous code incorrectly rejected it.
- **0.4.4 adds complete FFmpeg dependency-notice preservation:** `tools/import_ffmpeg_notices.ps1` imports the extracted package `doc/` tree and `LICENSE.txt`; `tools/ffmpeg_notices.py` writes a manifest with relative path, byte size and SHA-256 for every notice file. The Windows builder verifies the complete file set and every hash before PyInstaller runs, rejecting missing, altered, added/unlisted, unsafe-path or symlink entries.
- **0.4.5 hardens cross-platform path safety:** the importer and verifier reject Windows drive/UNC paths, alternate data streams (`:`), backslashes, traversal and noncanonical paths, reserved device names (including COM/LPT forms), trailing-dot/space names, case-insensitive path collisions and a source file that could overwrite the generated manifest.
- Symlink checks now cover the notice directory root, manifest, license file and every nested notice entry. The verifier validates the complete manifest path namespace before opening any listed file, then checks exact file set, size and SHA-256.
- Regression tests verify Windows-only path cases even on Linux, including alternate data streams, reserved names, case collisions, source import path rejection and symlinked entry points.

## Current FFmpeg candidate (not approved yet)

The BtbN GitHub release published on 2026-11-24 lists `ffmpeg-master-latest-win64-lgpl.zip` as a Windows x86_64 static LGPL build (179,049,798 bytes). GitHub release metadata reports the candidate archive SHA-256 as `3639382f80af8849c7e11b11f3f379992e2f1925fe95fcee262cbe242a005b84`. The BtbN build recipe at commit `b9ebe81995b58cd4e3177a6c0ad5dc2392f7f7fd` selects `variants/win64-lgpl.sh`; that imports `defaults-lgpl.sh` (`--enable-version3 --disable-debug`, license file `COPYING.LGPLv3`) and the enabled `scripts.d/50-libmp3lame.sh`, which adds `--enable-libmp3lame`. The static variant installer also packages FFmpeg's documentation directory.

This is an **LGPLv3 candidate**, not an approved app dependency. The archive download failed in this environment; its `ffmpeg.exe`, actual `-version`/configuration/`-L`, encoder list, embedded license files, dependent library notices and encode/decode probe remain unverified. The GitHub `latest` tag is mutable, so the release-asset digest must be checked before use. The actual FFmpeg source revision used by that binary has also not yet been extracted from the executable. See [FFmpeg build evidence notes](LICENSES/README_FFMPEG.md).

## Verified in this environment

Linux x86_64, Python 3.13.5, PyTorch 2.10 CPU-only, host FFmpeg 7.1.5, approx. 5.8 GB RAM and 3 CPU cores. No CUDA, Qwen runtime/weights, PowerShell/Wine, PyInstaller or bundled Windows FFmpeg; Hugging Face DNS resolution fails.

- `python -m compileall -q src tests tools` — PASS.
- Full source suite: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 xvfb-run -a env PYTHONPATH=src pytest -q` — **123 passed**, process exit 0.
- Focused atomic-output / FFmpeg notice / Qwen adapter suite — **45 passed**, process exit 0.
- `python -m compileall -q src tests tools` — PASS.
- CLI entry-point tests: 17 passed; coverage for `src/kjv_audio_generator/__main__.py` is **96%**, including GUI launch, positive preflight/audio-smoke wiring, speaker-seed import and the standard queue path.
- Wheel `kjv_audio_generator-0.4.10-py3-none-any.whl` built and installed into an isolated target; 53,951 bytes; SHA-256 `bfe9aedd5605dd6fd859cfac4b3dfa191da45d13457188fdd55c70af1cfb0737`. Installed version 0.4.10 and KJV structure data verified as 66 books / 1,189 chapters / 31,102 verses.
- Installed wheel preflight remains fail-closed as intended: `--self-test` exit 2 for missing Qwen models/runtime/asset manifest/bundled FFmpeg; `--audio-smoke` exit 3 for the missing Base model.
- Developer ZIP `KJV_Audio_Generator_Developer_Source_0_4_10_2026-11-24.zip` contains 73 source/documentation files. ZIP CRC, fresh extraction, compileall and **123 tests** from the extracted directory pass. The exact ZIP digest and byte size are recorded in the adjacent `.sha256` sidecar. This remains source-only, not a customer app.
- GUI tests create the main window, character-profile manager and verse speaker reviewer and test profile/speech-assignment save/reload.
- Full Genesis 1 software path processes all 31 KJV test verses through parser, speaker segments, SQLite worker and MP3 assembly; decodable **synthetic** MP3 with 33 cues. Not Qwen audio.
- Qwen adapter uses fake-model tests, but its prompt-item contract was checked against upstream `qwen-tts==0.1.1` source. No real inference.
- Real installed preflight fails closed: self-test exit 2 because Qwen models/runtime, pinned asset manifest and bundled Windows FFmpeg are missing; audio-smoke exit 3 because the Base model is absent.
- The current runtime probe confirms `qwen_tts` is not installed and Hugging Face DNS fails with a temporary name-resolution error. PyTorch and SoundFile are installed; only host Linux FFmpeg 7.1.5 is available. No genuine Genesis 1 MP3, Windows EXE, offline Windows launch, Windows playback, USB relocation or 1,189-chapter real generation has passed.

## Remaining release gates

1. Obtain the exact LGPL Windows FFmpeg candidate or a better pinned build, verify its executable hash, license text/notices, source revision, configuration and `libmp3lame`, then pass real encode/decode probe on Windows.
2. On network-enabled native Windows 11 / 64-bit Python 3.12, download and verify both pinned Qwen model snapshots and run them offline.
3. Generate and listen to all 31 real Qwen Genesis 1 verses; validate pronunciation, speaker assignments, output and cue times.
4. Reuse a recurring character prompt in a later chapter and assess audible consistency.
5. Test real-model pause/stop/retry/crash recovery and long sequential generation.
6. Build one-folder Windows app; clean extraction, offline launch, real playback, portable paths and USB relocation.
7. Benchmark CPU speed/peak RAM; validate 1,189 MP3/cue files and final storage size.
8. Complete KJV-specific cast/quotation review and full software/model/FFmpeg/codec/data licensing review.

**Not ready for customer installation/testing.**

See [Resume Here](docs/RESUME_HERE.md), [Development Status](docs/DEVELOPMENT_STATUS.md), [0.4.10 Checkpoint](docs/PROGRESS_CHECKPOINT_2026-11-24_GENERATOR_PROTOTYPE_0_4_10.md), [0.4.9 Checkpoint](docs/PROGRESS_CHECKPOINT_2026-11-24_GENERATOR_PROTOTYPE_0_4_9.md), [0.4.8 Checkpoint](docs/PROGRESS_CHECKPOINT_2026-11-24_GENERATOR_PROTOTYPE_0_4_8.md), [0.4.6 Checkpoint](docs/PROGRESS_CHECKPOINT_2026-11-24_GENERATOR_PROTOTYPE_0_4_6.md), [0.4.5 Checkpoint](docs/PROGRESS_CHECKPOINT_2026-11-24_GENERATOR_PROTOTYPE_0_4_5.md), [Attribution Dataset Research](docs/ATTRIBUTION_DATASET_RESEARCH_2026-11-24.md), [Downloads](DOWNLOADS.md) and [Source Archive](SOURCE_ARCHIVE.md).
