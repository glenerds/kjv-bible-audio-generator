> **Historical checkpoint — superseded by prototype 0.3.1.** The 45-test result below is retained as the 0.3.0 record; use `PROGRESS_CHECKPOINT_2026-11-24_GENERATOR_PROTOTYPE_0_3_1.md` and `RESUME_HERE.md` for the current source, test count and release gates.

# Checkpoint — KJV Audio Generator prototype 0.3.0

Date: 2026-11-24 (America/Indiana/Indianapolis)

## Assignment / acceptance criteria
Build a new application, separate from the legacy Bible Reader, that accepts pasted or imported Bible text; keeps stable voice identities for recurring Bible speakers; generates continuously in canonical order from Genesis 1 to Revelation 22; writes 1,189 individually named chapter MP3s plus verse/segment cues; persists progress and supports pause, safe stop, failed-chapter retry and restart recovery. The final Windows delivery must be self-contained with UI, runtime, Qwen weights, dependencies, FFmpeg, data and license notices. No customer test request/package before real synthesis and Windows integration tests pass.

## Work performed for 0.3.0

1. Exact KJV versification validation:
   - Added packaged JSON reference containing per-chapter KJV verse counts for all 66 canonical books.
   - Validation now checks every chapter's verse IDs are exactly 1..N and each chapter has its expected count, then checks the total 31,102 verses and 1,189 chapters.
   - Added source/license notice under `LICENSES/VERSE_COUNTS_LICENSE.txt` and included package-data configuration.
2. Qwen voice prompt compatibility:
   - Checked the official Qwen implementation contract: voice-clone prompt creation returns a collection/list of prompt items and `generate_voice_clone` expects the list (or a prepared dictionary).
   - Fixed adapter to persist and pass the complete prompt item list rather than a single first element.
   - Test double now explicitly asserts list-shaped argument; this is an adapter contract test, not actual inference.
3. Bounded memory:
   - Persistent prompt assets remain on disk; added eight-item in-memory LRU. This avoids loading every character's prompt at once for a large Bible cast.
4. Voice preparation and control:
   - Pause/stop checks run between preparation/synthesis operations.
   - Emits progress for reference design, clone prompt creation, and cached prompt reuse.
   - Added safe stop and retry-failed controls in UI.
   - User stop during a claimed chapter requeues that chapter and restores the attempt count, so deliberate stopping does not consume a synthesis-failure retry.
5. Build recipe:
   - Added verse-count JSON as PyInstaller data.
   - Added `LICENSES` folder to the one-folder bundle (script not yet run on Windows).
6. Tests:
   - Added exact per-chapter verse count / redistribution regression tests.
   - Added eight-profile prompt LRU test.
   - Added safe-stop/retry/recovery test.
   - Added UI controls and build-script checks.

## Verified results in current environment

Environment: Linux container, Python 3.13.5, Tk via Xvfb, host FFmpeg `/usr/bin/ffmpeg`.

- `python -m compileall -q src tests` — PASS.
- `xvfb-run -a env PYTHONPATH=src pytest -q` — **45 passed in 3.56 seconds** (latest run before packaging).
- Additional independent Tk launch smoke — PASS: app initialized; start, safe-stop and retry controls existed.
- `--self-test --models ./models` — **expected fail-closed exit 2**. Checks: VoiceDesign model false, Base model false, Qwen runtime false, bundled FFmpeg false. Host `/usr/bin/ffmpeg` detected but is not a Windows bundle.
- `--audio-smoke` — **expected fail-closed exit 3**: Base model folder missing/empty. No real AI audio was generated.

## Current code capabilities

- Parser supports USFM/SFM, text/JSON and ZIP inputs.
- KJV exact chapter/verse structure guard.
- Persistent speaker registry, aliases, descriptions, reference text, Qwen prompt asset storage and invalidation on profile/reference changes.
- Optional Clear/MACULA provisional attribution importer.
- SQLite chapter job queue with restart recovery, ordered processing and retries.
- MP3 assembly, loudness normalization, validation and verse/segment timestamp JSON.
- Tk UI import/paste, output folder, validation, start/pause/resume/stop/retry and log.

## Important attribution limitation

The optional Clear/MACULA speaker dataset is derived from other English translations and original-language alignment, not KJV. Upstream documentation says it is an initial effort and can be improved; alternates/conflicts exist. It must be treated as a review seed. The actual TSV assets are not bundled in this prototype. Only default profiles (Narrator, Unknown, God, Jesus, Moses) exist until a data import or manual profile/assignment process creates more. The UI currently imports projection TSVs but does not yet provide a complete polished per-verse attribution editor. Do not claim that every Bible quotation has already been identified or assigned to the correct person.

## Release blockers / nothing to claim

- No Qwen package/model weights are installed or staged.
- No genuine Genesis 1 MP3 (authentic 31 KJV verses) exists.
- No authentic 66-book KJV wording is bundled.
- No real speaker-cast completeness/accuracy review.
- No native Windows PyInstaller build, executable launch, or fresh extraction/offline test.
- No real Windows speaker-device playback; no CPU-only performance/RAM/long-run test.
- No physical USB relocation/drive-letter/capacity test.
- No full licensing/resale clearance for commercial Amazon distribution.
- No customer test package. Prototype source archive (if supplied) is developer-only.

## Resume exactly here

1. Read this checkpoint and project README.
2. First attempt to obtain/prepare the supported Qwen3-TTS VoiceDesign and Base model runtime in a native Windows build/test environment; verify offline loading and package API against the actual installed version.
3. Generate genuine Genesis 1 audio for all 31 verses, with voice changes only where confidently attributed; inspect audio decode, cues, listening quality and exact profile reuse.
4. Expand and curate speaker attribution data. Ensure all names/aliases resolve to a single persistent character ID; flag uncertainty for review rather than silently inventing a speaker.
5. Test two or more chapters with repeat character use to prove cross-chapter prompt reuse and identity consistency.
6. Run long generation/stop/retry/restart with the actual Qwen backend.
7. Execute Windows PyInstaller build, fresh extraction, offline start, no extraneous profile writes, real audio playback, and USB tests.
8. Update GitHub README, Resume Here, Development Status, Downloads, Source Archive, Project Index and checkpoint after meaningful work.
9. Do not call this finished or ask the user to test until the above gates have passed.

## Commands

```bash
cd /mnt/data/kjv-audio-generator
python -m compileall -q src tests
xvfb-run -a env PYTHONPATH=src pytest -q
PYTHONPATH=src python -m kjv_audio_generator --self-test --models ./models
PYTHONPATH=src python -m kjv_audio_generator --audio-smoke --models ./models --output /tmp/kjv-qwen-smoke
```

The two final CLI commands are expected to fail until the Qwen runtime/model and Windows FFmpeg assets are staged. An expected fail-closed result is not a successful real-audio test.
