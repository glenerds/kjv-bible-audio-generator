# Engineering Checkpoint — KJV Bible Audio Generator 0.3.3

Date: 2026-11-24. Project: separate KJV Bible Audio Generator (not legacy Reader/USB Builder).

## Acceptance target

A fully self-contained Windows desktop app imports/pastes the complete KJV, supports reviewed stable character voices and speech segments, and renders all 66 canonical books into 1,189 individual chapter MP3s with speaker/verse/sub-verse cues. The app must have durable queue/checkpoints, pause/resume, safe stop, bounded retries, restart recovery and portability. No customer installs for Python, packages, models, WSL or FFmpeg. No GPU requirement. Do not request user testing before real Qwen/Windows acceptance passes.

## 0.3.3 code delivered

1. Added **Manage Character Voices** GUI. It creates a stable character ID, edits display name and aliases, Qwen voice design prompt, reference script and optional reference audio. Existing IDs are immutable to protect assignments. Changes affecting the voice reference invalidate the prepared prompt so it will be rebuilt.
2. Added **Review Verse Speakers** GUI. A user can choose any imported verse and edit its speech as line-separated `speaker_id<TAB>exact text` segments. Save checks the exact concatenation against the source verse, rejecting any missing or modified text. Multiple speech parts/voices within one verse are supported and saved to the output's speaker assignments JSON.
3. Added pure segment-editor validator and tests for round-trip, unknown speaker, missing tab, empty segment, empty submission and text mismatch.
4. Added Xvfb GUI tests that create/save a new John the Baptist profile and edit Genesis 1:3 into narrator + God speech, then reload the persisted files to confirm correctness.
5. Previous 0.3.2 Qwen/model structure checks, pinned asset preparation, explicit Torch CPU/CUDA build selection, FFmpeg provenance/license/hash gate and portable PyInstaller recipe remain in place.

## Test results executed

Environment: Linux x86_64; Python 3.13.5; PyTorch 2.10.0+cpu; CUDA unavailable; host FFmpeg 7.1.5; roughly 5.8 GB RAM and 3 CPU cores. No installed Qwen TTS runtime, real weights, PowerShell/Wine, PyInstaller or Windows FFmpeg. An outbound DNS check to Hugging Face failed (`Could not resolve host`), so the two official model trees were not downloadable here.

- `python -m compileall -q src tests`: PASS.
- `xvfb-run -a env PYTHONPATH=src pytest -q`: **65 passed**.
- Clean 51-entry source ZIP built, ZIP integrity passed, extracted to new directory, compileall passed and **65 tests passed again**.
- Wheel `kjv_audio_generator-0.3.3-py3-none-any.whl` built and installed in isolated target: 41,942 bytes, SHA-256 `1c0cafaae84f54f1adc79ae2a9a3ca013cb9b24a0f9e5fac547c9cb044add245`. Installed module version 0.3.3 and bundled data counts 66/1,189/31,102 verified.
- CLI `--self-test`: expected exit 2, missing both models, Qwen runtime and bundled Windows `ffmpeg.exe`. `--audio-smoke`: expected exit 3, Base model missing.
- Full 31-verse KJV Genesis 1 software-flow integration test: parses all verses, applies reviewed two-part speech splits at Genesis 1:3 and 1:6, runs actual queue/worker, assembles MP3 and timestamp JSON, verifies FFmpeg decode, 33 cue segments, two God segments and 31 narrator segments. Backend is `SyntheticTestBackend` only; the MP3 is not genuine voice audio.
- UI profile editor test opens the dialog, creates a new John the Baptist profile, saves the registry and reloads it.
- UI verse editor test saves a narrator/God split for Genesis 1:3 and reloads the persisted attribution JSON; helper validates original verse text preserved exactly.
- Qwen API tests remain fake-model contract tests. No authentic Qwen output exists.
- Wheel build/install and fresh archive retests are the next step after this source update; record exact results here.

## Remaining actual product blockers

- Qwen package and official VoiceDesign/Base model trees (~9.06 GB combined per upstream listing) absent from this Linux host; genuine Genesis 1 cannot be generated here.
- No Windows-native test runner/PowerShell/PyInstaller, no Windows FFmpeg binary. FFmpeg is intentionally a hard release gate pending verified license, build manifest and SHA.
- No cross-chapter audible voice comparison, real model interruption/recovery, or Windows playback.
- MACULA is not KJV-specific. The new editor supports manual per-verse speaker segmentation, but the complete KJV character cast and automatic attribution review is not done.
- No full 1,189-chapter real audio generation or size/integrity run, CPU benchmark, or commercial licensing review.

## Latest developer archive

`KJV_Audio_Generator_Developer_Source_0_3_3_2026-11-24.zip` is the latest developer-only artifact. ZIP integrity, fresh extraction, compileall and the 65-test run passed. The exact hash is recorded outside the archive in the GitHub `SOURCE_ARCHIVE.md` handoff to avoid a self-referential checksum. The ZIP contains no Qwen models/runtime and no bundled Windows FFmpeg.

## Exact resume point

The 0.3.3 wheel/install and clean ZIP extraction/retest have now passed. Next secure genuine Windows FFmpeg with verifiable provenance and execute asset preparation / real Qwen inference on native Windows. The first real audio gate remains all 31 authentic Genesis 1 verses plus one later-chapter recurring-character voice reuse. Do not call the app user-ready before that and the native Windows package gates pass.
