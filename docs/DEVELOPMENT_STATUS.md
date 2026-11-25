## Windows sparse-fixture correction — 2026-11-24

The isolated Windows test proved FSCTL_SET_SPARSE set the sparse attribute, but an ordinary truncate still allocated 147,324,928 bytes for a 3.5 GB logical file. Updated the fixture to call FSCTL_SET_ZERO_DATA over the entire logical zero range after EOF extension. The dedicated Windows test checks both model placeholders for <1 MiB physical allocation. Latest Windows hosted verification pending; Linux remains 125 passing, 1 Windows-only skip.

---

## Windows CI diagnostic follow-up — 2026-11-24

The two latest Windows attempts did not produce usable test logs: GitHub marked the job failed while its test step remained "in_progress", and the log archive lookup returned BlobNotFound. Dependency installation and compileall passed; Ubuntu's full 125-test run passed. Added an explicit Windows-only sparse-fixture check (NTFS sparse attribute + GetCompressedFileSizeW allocation) as a separate step before the full Windows suite. The result will clarify whether the large sparse model fixtures still consume disk or whether another runner failure exists. Windows acceptance remains unverified.

---

## Native Windows CI follow-up — 2026-11-24

Windows/Python 3.12 installed its test dependencies and compiled source, but its full test step exhausted the runner disk. The Qwen adapter tests create fake 3.5 GB / 650 MB model weights with Path.truncate; unlike Linux, the Windows filesystem allocated real blocks. Added a fixture helper that explicitly marks those NTFS files sparse with FSCTL_SET_SPARSE (DeviceIoControl) before truncation. Local compileall and full suite re-run passed: 125 tests. Latest hosted Ubuntu run also passed all 125 tests. The new Windows hosted run and PowerShell parse are pending.

This fix addresses test-only disk allocation; not a production model download, integrity verification, or application behavior change.

---

## CI follow-up — 2026-11-24

The corrected PyTorch test dependency got the Ubuntu CI job past test collection. Its next failure was environmental: the job had no FFmpeg executable, while 12 tests deliberately require FFmpeg for actual audio assembly/worker flows. Result: 110 passed, 12 failed, 2 skipped; all reported failures trace to missing FFmpeg. CI now installs FFmpeg on Windows (Chocolatey) and Linux (apt) solely to satisfy test prerequisites; a regression test asserts both install commands. This does not establish the production FFmpeg candidate/license gate. New hosted run result pending.

---

## 0.4.11 validation update — 2026-11-24

A clean install on both hosted Windows and Ubuntu initially exposed a missing development dependency: `tests/test_qwen_adapter.py` imports PyTorch, but `torch` was absent from the `dev` extra. This was fixed by declaring `torch==2.10.0` in the dev dependencies, preinstalling the CPU wheel in CI, bumping the project version to 0.4.11 and adding a regression test. The new hosted rerun must pass before the status can say the Windows suite passed.

- Canonical 0.4.10 source ZIP SHA-256: `4c9dffa08d75e8ee2efb60f9fa561311d3501f515dbf650e233f15ebd2cc07f9`; 73 entries; ZIP test PASS.
- Public repo reconciliation: 72/72 non-README archive paths match Git blob hashes exactly; README intentionally updated; three review docs are public-repo-only additions.
- Fresh 0.4.11 working extraction: compileall PASS; **124 tests passed** locally on Python 3.13.5/Linux x86_64.
- First hosted CI attempt: both runners successfully installed dependencies and compiled; both failed collection on missing torch. The corrected workflow is triggered by the 0.4.11 commit.
- Native Windows PowerShell parsing and Windows test result are not yet confirmed.

## Remaining real-world release gates

No genuine Qwen model generation/listening, Windows PyInstaller package, bundled approved FFmpeg/MP3 probe, offline Windows playback, USB relocation, long-run CPU/RAM benchmarking, full 1,189-chapter generation, measured storage, KJV-specific speaker review or complete licensing audit has passed.

---

# Development Status — KJV Bible Audio Generator 0.4.11

Last updated: 2026-11-24.

## Summary

Version 0.4.11 adds the missing PyTorch test dependency and cross-platform CI on top of the 0.4.10 atomic-persistence and transactional FFmpeg-notice work. Qwen-generated reference WAVs and `.pt` prompt assets now use extension-preserving unique staging and fsync/atomic replace. FFmpeg documentation and license files are fully staged and verified before replacing the old set, with rollback on a mid-commit failure. **124 automated tests pass locally**, including clean source execution; the isolated wheel install verifies the KJV structure metadata. No real Qwen speech or native Windows app has been tested; this remains a developer prototype, not a customer release.

| Area | Status | Notes |
|---|---|---|
| KJV import/structure | Implemented | Canonical 66 books / 1,189 chapters / 31,102 verses |
| Character/verse editors | Implemented | GUI-tested; exact verse text preservation |
| Speaker attribution | Partial | No complete verified openly redistributable KJV word-level speaker map |
| Speaker seed import | Hardened | GUI and CLI merge suggestions; manual data retained; overlaps queued |
| Recurring voices | Software path implemented | No audible real-Qwen validation |
| Qwen ICL prompt | Mock-tested | Transcript retained; old-prompt migration; no real inference |
| JSON persistence | Atomic writes | Shared writer for all application JSON outputs |
| Qwen reference audio | Atomic file commit | SoundFile writes extension-preserving temp WAV, fsync + atomic replace |
| Qwen prompt asset | Atomic file commit | torch.save writes unique `.tmp.pt` stage; fixed-name race removed |
| MP3 output commit | Atomic copy | Unique destination-local staging and fsync/replace |
| FFmpeg notices | Transactional import | Verify staged notices before swap; rollback restores previous bundle |
| SQLite queue/recovery | Automated tests | WAL, atomic claims, recovery, hashes, retries and path rebasing |
| Genesis 1 pipeline | Synthetic integration | 31 KJV fixture verses, 33 cues; synthetic MP3 only |
| Wheel 0.4.10 | Built/installed | 53,951 bytes; SHA in README/SOURCE_ARCHIVE |
| Source ZIP 0.4.10 | Built/verified | 73 files; hash in sidecar; clean extraction and 123 tests |
| Windows FFmpeg | Candidate only | Actual binary/notices/encode probe unverified |
| Windows application | Not built | No native Windows build or acceptance test |
| Genuine Genesis 1 | Not generated | `qwen_tts` and model snapshots unavailable |
| Full Bible | Not generated | No real 1,189-chapter audio run |

## 0.4.10 atomic file and notice-import changes

- `atomic_output_path()` creates a unique staging file next to its target, retaining the final extension so libraries such as SoundFile can select the WAV container. It rejects empty output, fsyncs, then atomically replaces the destination. Exceptions preserve prior bytes and clean up staging.
- `QwenVoiceBackend.prepare_profiles()` uses this helper for VoiceDesign reference WAVs and Qwen `.pt` prompt payloads. The old fixed `.pt.tmp` name was removed.
- `copy_file_atomic()` now delegates to the same helper, rejects non-file sources and fsyncs before replacement.
- `tools/ffmpeg_notices.py` stages `doc/`, `LICENSE.txt` and its manifest under a temporary root, verifies the complete SHA-256 set, then swaps both live destinations. Failure while staging leaves old files alone; failure during the second commit rolls back the first and restores the old license. A successful re-import removes stale entries from the previous set.
- Regression cases cover normal and failed third-party file writers, extension preservation, unique stage names, import-copy failure, mid-commit rollback and successful all-at-once notice replacement.

## Test environment and results

Linux x86_64, Python 3.13.5, PyTorch 2.10 and SoundFile installed, host FFmpeg 7.1.5. Qwen `qwen_tts` is absent, Hugging Face DNS fails, and no Windows host/PowerShell/Wine/Windows FFmpeg is available.

- Compileall: PASS.
- Focused atomic-output / FFmpeg notice / Qwen adapter suite: **45 passed**.
- Full source suite: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 xvfb-run -a env PYTHONPATH=src pytest -q` — **123 passed**, process exit 0.
- Wheel 0.4.10 isolated install: PASS; installed version and all 66 / 1,189 / 31,102 KJV structure counts verified.
- Installed-wheel `--self-test`: exit 2, expected because model folders, asset manifest, Qwen runtime and bundled Windows FFmpeg are absent.
- Installed-wheel `--audio-smoke`: exit 3, expected because Base model is missing.
- Fresh 73-file 0.4.10 source ZIP: ZIP CRC, extraction, compileall and all **123 tests** pass.
- Genesis 1 remains a synthetic audio integration, not real Qwen speech.

## Attribution research

No complete, verified, openly redistributable KJV word-level dialogue-speaker map has been identified. MACULA/FCBH projections are not KJV-specific and remain provisional. Keep them human-reviewable; do not bundle proprietary data without permission. See `ATTRIBUTION_DATASET_RESEARCH_2026-11-24.md`.

## Remaining release gates

Authentic Qwen Genesis 1 and later-chapter recurring-voice listening test; real-model recovery/long run; approved Windows LGPL FFmpeg binary/source/license/dependency notices/encoder probe; native Windows one-folder build/offline launch/playback/USB; CPU/RAM and full 1,189 MP3/cue storage/integrity validation; KJV cast/quotation and software/model/codec/data licensing review.

**Not ready for customer installation/testing.**
