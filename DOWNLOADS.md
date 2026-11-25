# Downloads — KJV Bible Audio Generator 0.4.10

## No customer app download exists

Version 0.4.10 is a developer source/wheel prototype only. It has not generated authentic Qwen Genesis 1 speech and has no native Windows application. **Do not install this as the finished application or ask the user to test it.**

## Current engineering status

- Latest source version: **0.4.10**.
- Full source suite: **123 passed**, process exit 0; focused atomic/Qwen/FFmpeg tests **45 passed**.
- 0.4.10 adds atomic staging for Qwen reference WAV and `.pt` prompt files, removes the shared `.pt.tmp` collision, and makes FFmpeg notice import staged, verified and rollback-safe.
- Wheel: `kjv_audio_generator-0.4.10-py3-none-any.whl`, 53,951 bytes; SHA-256 `bfe9aedd5605dd6fd859cfac4b3dfa191da45d13457188fdd55c70af1cfb0737`.
- Source ZIP: 73 files; exact SHA-256 is in the adjacent `.sha256` sidecar. Clean extraction, compileall and all 123 tests pass.
- Isolated wheel installation verifies package 0.4.10 and Bible structure 66 books / 1,189 chapters / 31,102 verses.
- Installed-wheel preflight correctly remains fail-closed: `--self-test` exit 2 because actual models/runtime/manifest/Windows FFmpeg are absent; `--audio-smoke` exit 3 because Base model is absent.
- This archive/wheel contains developer code/docs only: no Qwen weights/runtime, approved Windows FFmpeg or customer EXE.

The GitHub project folder contains documentation and handoff notes; binary ZIP/wheel/checksum artifacts are supplied as conversation downloads rather than GitHub release assets.

## Customer release gates

Genuine Qwen Genesis 1 and later-chapter recurring voice; real-model recovery; verified native Windows LGPL FFmpeg binary/source/license/dependency notices/encoder/probe; native Windows one-folder app, clean extraction, offline launch/playback/USB relocation; CPU/RAM and all 1,189 MP3/cue integrity/storage; KJV cast attribution and licensing review.
