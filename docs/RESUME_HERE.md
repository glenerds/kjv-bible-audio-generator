## ADS validation test wording follow-up

Expanded the existing unsafe-source-name test to accept the new precise diagnostic text "alternate data streams" as well as the prior unsafe/reserved messages. This prevents a correct Windows ADS rejection being marked failed merely because its error is more specific. No product behavior change; local compileall and Linux suite remain 126 passed, 2 Windows-only skipped. Hosted Windows run pending.

---

## Latest Windows security correction — alternate data streams

Native Windows suite was 125 passed / 1 failed: FFmpeg notice import accepted NOTICE.txt:stream, because NTFS ADS is hidden from normal pathlib enumeration. Added FindFirstStreamW/FindNextStreamW/FindClose inspection on source, staged and installed notice folders plus source/staged/final license files; all named streams are rejected. Added Windows license-ADS test and platform-independent unsafe raw-name tests. Local compileall PASS; 126 passed, 2 Windows-only skipped. Await the next hosted Windows suite and PowerShell parser.

---

## Windows sparse-fixture correction — FSCTL_SET_ZERO_DATA

The focused NTFS test found that FSCTL_SET_SPARSE alone left 147,324,928 bytes allocated for the 3.5 GB fake file. Added FSCTL_SET_ZERO_DATA over the full logical file range after setting EOF; this is the filesystem operation Microsoft documents for zeroing ranges while allowing sparse NTFS deallocation. The focused test requires <1 MiB physical allocation for both model-weight placeholders. Await the next Windows run; Linux suite previously passed 125 tests and skips the Windows-only allocation check.

---

## Windows CI diagnostic follow-up — explicit sparse allocation test

The latest Windows job records are marked failed while the pytest step remains "in_progress"; the log-storage endpoint reports BlobNotFound. The exact failing assertion is therefore unknown. Ubuntu passed 125 tests. Added a Windows-only test that validates the sparse file attribute and actual on-disk allocation with GetCompressedFileSizeW, and an isolated Windows workflow step runs that test before the full suite. Linux skips this NTFS-only test. Do not claim the Windows fixture fix is verified until this focused step and the full Windows suite complete.

---

## Native Windows CI follow-up — sparse Qwen test fixtures

The hosted Windows/Python 3.12 job installed Python, FFmpeg, PyTorch and project dev dependencies, then passed compileall. During full tests it exhausted disk space: Qwen adapter fixtures created multi-gigabyte fake weights via Path.truncate(), which is sparse on Linux but allocates real disk blocks on Windows. Fixed tests/test_qwen_adapter.py with _truncate_sparse_file(), which calls NTFS FSCTL_SET_SPARSE before extending Windows fixture files. Local revalidation: compileall PASS; 125 tests passed on Linux. Latest hosted Ubuntu run passed 125 tests. Recheck the new Windows run and its PowerShell parse step before claiming native Windows source-test acceptance.

---

## CI follow-up — 2026-11-24: audio tests need FFmpeg in the runner

The 0.4.11 hosted Linux runner successfully installed CPU PyTorch and compiled source, then the full suite reported 110 passed, 12 failed, 2 skipped. All 12 failures resulted from `ffmpeg` not being installed on the runner. Added CI-only installation on Windows via Chocolatey and Ubuntu via apt, plus a test asserting the workflow provisions FFmpeg. This test FFmpeg is not the unapproved production binary. Wait for the next hosted run to verify the full Windows and Linux suites.

---

## Latest continuation — 2026-11-24: cross-platform CI and test dependency fix

- Canonical 0.4.10 archive SHA-256 verified: `4c9dffa08d75e8ee2efb60f9fa561311d3501f515dbf650e233f15ebd2cc07f9`. The 73-file ZIP passes integrity checks; all 72 non-README archive files match the public GitHub tree exactly. README difference is intentional; the repo has three additional AI-review files.
- Fresh clean extraction compiled; prior source baseline reproduced at 123 passing tests.
- New public GitHub Actions checks allocated real Windows/Python 3.12 and Ubuntu/Python 3.13 runners. Both reached test collection and identified the same missing dependency: test module imports torch but the dev extra did not provide it.
- Fixed by adding `torch==2.10.0` to the dev extra, installing CPU torch in CI, adding a dependency regression test, and bumping package metadata to 0.4.11.
- Local 0.4.11 verification: compileall PASS; **124 tests passed** on Python 3.13.5 Linux. The workflow rerun is pending and must be checked before claiming the hosted Windows test passed.
- Do not confuse static/hosted source tests with genuine Qwen speech or full Windows release acceptance; those remain unpassed.

---

# Resume Here — KJV Bible Audio Generator 0.4.11

**Separate project:** KJV Bible Audio Generator, not the legacy KJV Bible Reader / USB Builder.

## User's continuation instruction

Whenever the user says **“keep working,” update the project README before doing any other engineering work in that continuation turn**. The README must record the starting version/state and the intended work. This requirement is active and must not be skipped.

## Finished product requirements

A self-contained Windows desktop app imports/pastes KJV, manages recurring character identities and exact verse-level speaker segments, and generates 1,189 named MP3 chapter files with verse/sub-verse cues. Durable queue, pause/resume, safe stop, bounded retry, restart recovery and USB portability. Customers must not install Python, packages, WSL, Qwen, model weights or FFmpeg. No dedicated GPU requirement. Final chapter-MP3 collection target below 16 GB. **Do not ask the user to install or test until real Qwen inference and native Windows acceptance tests pass.**

## Active source

- Workspace: `/mnt/data/kjv-audio-generator-work/`
- Package version: **0.4.11**
- Main GUI: `src/kjv_audio_generator/app.py`
- Qwen adapter/runtime: `src/kjv_audio_generator/backend.py`, `runtime.py`
- Persistence: `src/kjv_audio_generator/json_io.py`
- Attribution: `src/kjv_audio_generator/attribution.py`, `attribution_seed.py`
- Queue/audio: `storage.py`, `worker.py`, `audio.py`
- FFmpeg notices: `tools/ffmpeg_notices.py`, `tools/import_ffmpeg_notices.ps1`
- Windows build: `tools/prepare_assets.ps1`, `tools/build_windows.ps1`

## 0.4.10 work — Qwen atomic writes and transactional notice import

- Added `atomic_output_path()` to stage arbitrary library-produced files beside their final destination with a unique name retaining the final extension (e.g. `.tmp.wav`), non-empty output validation, fsync and atomic `os.replace()`.
- Qwen VoiceDesign reference WAV output now uses atomic staging; a SoundFile regression originally caught that extension inference requires `.wav` at the end of the temporary name, so the helper now preserves the extension.
- Qwen `.pt` clone prompts now save to unique staged paths and atomically replace the destination, fixing the fixed-name `.pt.tmp` collision and avoiding partial prompt files.
- `copy_file_atomic()` now uses the shared helper and verifies that its source is a regular file.
- FFmpeg notice import now stages both the documentation tree and license file, computes the hash manifest and verifies the staged set before replacing the previous bundle. If copy staging fails or the second file commit fails, rollback restores the prior bundle. Successful import replaces the whole set so stale notices are removed.
- Tests exercise empty/failed staged writers, extension retention, unique temp names, FFmpeg copy staging failure, simulated mid-commit failure with rollback, and successful full-set replacement.

## Existing safeguards

- GUI and CLI speaker-seed imports merge suggestions non-destructively; manual segments, custom/prepared voices, user ranges, review candidates and provenance are retained.
- All application JSON persistence is routed through `write_json_atomic()`; cue JSON, initial review data and backend diagnostic JSON are included.
- MP3 finalization uses `copy_file_atomic()`; chapter MP3 and cue hashes are recorded and verified at restart.
- Qwen 0.1.1 ICL prompts persist `ref_text` and reconstruct official prompt-item attributes; old prompts migrate from WAV or fail closed.
- SQLite queue uses WAL, bounded claims, pause/resume/stop, retries, fingerprints, tamper detection and USB path rebasing.
- FFmpeg notice verification checks Windows/POSIX paths, symlinks, case collisions, reserved names, complete file set and hashes.

## Verified results

Host: Linux x86_64, Python 3.13.5, PyTorch 2.10, SoundFile present, host FFmpeg 7.1.5. `qwen_tts` is not installed; Hugging Face DNS lookup fails. Windows PowerShell/Wine, native Windows FFmpeg and Windows host are unavailable. The current host has no genuine model snapshot.

- 0.4.9 baseline reproduced: **116 passed**.
- Focused 0.4.10 atomic-output/FFmpeg/Qwen tests: **45 passed**.
- Full 0.4.10 source suite: **123 passed**, exit 0.
- Compileall: PASS.
- Wheel 0.4.10 built and installed in isolated target: 53,951 bytes; SHA-256 `bfe9aedd5605dd6fd859cfac4b3dfa191da45d13457188fdd55c70af1cfb0737`.
- Installed package version 0.4.10; bundled data validates 66 books / 1,189 chapters / 31,102 verses.
- Installed wheel fail-closed checks: `--self-test` exit 2 for absent models/asset manifest/qwen runtime/bundled Windows FFmpeg; `--audio-smoke` exit 3 for missing Base model. This is expected and means real audio has not been proven.
- Fresh 73-file source ZIP: SHA-256 is recorded in the adjacent sidecar; ZIP CRC, fresh extraction, compileall and all **123 tests** pass.
- Genesis 1 integration still uses synthetic audio (31 authentic fixture verses, 33 cues), not Qwen speech.

## Unpassed release gates

No authentic Qwen Genesis 1 MP3 or later-chapter audible recurring-voice comparison; no real-model pause/stop/retry/crash run; no native Windows Qwen/offline load; no approved Windows LGPL FFmpeg executable/source/license/notices/encoder probe; no Windows one-folder build, offline playback or USB relocation; no CPU/RAM long-run benchmark or full 1,189-chapter audio generation/storage check; KJV attribution and software/model/codec/data licensing audit remain incomplete.

## Next work

1. Check real network access again before attempting model retrieval; do not start multi-gigabyte downloads if DNS is unavailable.
2. If network-enabled Windows is unavailable, continue source audits and reliability tests, but do not pretend those replace real Qwen inference or Windows acceptance.
3. When a valid native Windows environment becomes available, stage the pinned Qwen VoiceDesign and Base snapshots, verify hashes, run offline preflight and generate/listen to Genesis 1.
4. Verify a recurring character's voice in a later canonical chapter, then exercise real-model recovery and long sequential generation.
5. Obtain and inspect the pinned Windows LGPL FFmpeg binary, notices, source revision and MP3 encode/decode probe.
6. Build/test the Windows one-folder package, offline launch/playback, USB relocation, CPU/RAM performance, all 1,189 chapter files and final storage size.

Do not downgrade the multi-character Qwen voice-design goal to preset-only voices without an explicit reason and decision. Do not call developer ZIP/wheel artifacts a customer application.
