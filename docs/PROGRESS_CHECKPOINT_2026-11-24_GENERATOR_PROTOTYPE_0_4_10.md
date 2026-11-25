# Engineering Checkpoint — KJV Bible Audio Generator 0.4.10

Date: 2026-11-24  
Status: Qwen-generated reference and prompt files use extension-preserving atomic output; FFmpeg notice replacement is staged, verified and rollback-safe; 123 tests pass; wheel install and KJV structure metadata pass. Not customer-ready.

## Problems found after 0.4.9

A full persistence scan found that generated Qwen files still bypassed the shared writer: SoundFile wrote reference WAVs directly to their final path, and `torch.save()` wrote prompt tensors to a fixed `.pt.tmp` filename. The fixed name could collide when two workers prepare the same profile, and a failure could leave incomplete files. The same scan found that the FFmpeg notice importer removed the active notice directory/license before copying the replacement; a copy failure could destroy the previously imported notice set.

## 0.4.10 implementation

- Added `atomic_output_path(path)`, yielding a unique same-directory temporary path while preserving the target's final suffix. This matters because SoundFile infers the WAV format from `.wav` at the end of the filename.
- The helper requires a non-empty staged file, fsyncs it once the third-party writer closes it, then uses `os.replace()`. Exceptions delete the temporary output and do not change the old destination.
- Qwen VoiceDesign reference WAVs now write to an extension-preserving staged path then atomically commit.
- Qwen `.pt` clone-prompt files now use unique `.tmp.pt` staging and atomic commit instead of a shared `.pt.tmp` file.
- `copy_file_atomic()` now delegates to the shared output path, rejects a non-regular source and uses the same flush/fsync/replace behavior.
- FFmpeg notice import now copies docs/license to an isolated temporary tree, writes and verifies the exact SHA-256 manifest there, then swaps the notice directory and license. Prior files are backed up until both new destinations are committed.
- If staging copy fails, old notice files are not touched. If the second destination commit fails, the new first destination is removed and backups are restored. If rollback itself fails, the backup directory is deliberately retained and its path is reported.
- Added seven regression tests across atomic output and FFmpeg import: extension retention, empty output rejection, writer exception cleanup, unique temp names, staging-copy failure preservation, simulated mid-commit rollback and successful full-set replacement.
- Package version bumped to 0.4.10.

## Verification

- Focused `test_json_io.py`, `test_asset_preparation.py`, `test_qwen_adapter.py`: **45 passed**, process exit 0.
- Full suite: **123 passed**, process exit 0.
- Compileall: PASS.
- Wheel `kjv_audio_generator-0.4.10-py3-none-any.whl`: 53,951 bytes; SHA-256 `bfe9aedd5605dd6fd859cfac4b3dfa191da45d13457188fdd55c70af1cfb0737`.
- Wheel installed into a separate target without dependencies; installed version 0.4.10 and packaged counts 66 / 1,189 / 31,102 verified.
- Installed wheel `--self-test` exit 2: expected fail-closed due to missing Qwen VoiceDesign/Base model snapshots, model manifest, `qwen_tts` runtime and bundled Windows `ffmpeg.exe`.
- Installed wheel `--audio-smoke` exit 3: expected fail-closed because Base model is missing.
- Source archive contains 73 files; a fresh extraction, ZIP CRC, compileall and all **123 tests** pass. Exact archive digest/byte size recorded in sidecar.
- Network probe confirms Hugging Face DNS lookup fails in this environment. No actual Qwen audio was generated. Genesis 1 integration still emits synthetic MP3 only.

## Remaining blockers

No genuine Qwen Genesis 1 audio, later-chapter audible recurring-character comparison, native Windows app/launch/playback/USB acceptance, actual pinned Windows FFmpeg binary/source/license/notices/encoder test, real-model recovery/long run, CPU/RAM benchmark, full 1,189-chapter MP3 set/storage check, or complete KJV speaker attribution and licensing audit.

**Not ready for customer installation/testing. Do not ask the user to test until genuine Qwen Genesis 1 and native Windows acceptance gates pass.**

## Resume

Continue from `/mnt/data/kjv-audio-generator-work/`, package 0.4.10. Before future engineering, first update the project README as explicitly required by the user. Then read README, this checkpoint, `docs/RESUME_HERE.md` and `docs/DEVELOPMENT_STATUS.md`. Prioritize authentic Qwen inference and native Windows acceptance when a network-enabled Windows environment is available.
