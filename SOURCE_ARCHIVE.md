# Source Archive — KJV Bible Audio Generator 0.4.10

**Developer source only; not a customer application.**

## 0.4.10 changes

Qwen-generated reference WAVs and `.pt` prompt tensors now use a shared extension-preserving atomic-output context with unique same-directory staging, non-empty output validation, fsync and atomic replace. This removes direct reference-WAV writes and the fixed `.pt.tmp` collision. The FFmpeg notice importer now stages docs, license and SHA-256 manifest, verifies the complete staged set, and only then swaps the live notice directory and license with backup/rollback. Failure-injection tests verify that the previous notice bundle survives both a staging-copy failure and a mid-commit failure.

## Source ZIP

- File: `KJV_Audio_Generator_Developer_Source_0_4_10_2026-11-24.zip`
- Contents: 73 source/documentation files; no model weights, caches, build outputs or egg-info.
- Exact SHA-256 is recorded in the adjacent `.sha256` sidecar.
- ZIP CRC, clean extraction, compileall and all **123 tests** from the extracted source: PASS.
- Not a customer app; no Qwen weights/runtime, verified Windows FFmpeg binary or Windows executable.

## Wheel

- File: `kjv_audio_generator-0.4.10-py3-none-any.whl`
- Size: 53,951 bytes.
- SHA-256: `bfe9aedd5605dd6fd859cfac4b3dfa191da45d13457188fdd55c70af1cfb0737`.
- Built without dependency downloads; installed into an isolated target.
- Installed package version 0.4.10; packaged KJV metadata verified as 66 books / 1,189 chapters / 31,102 verses.

## Download location

The GitHub project directory contains documentation and handoff notes. Binary ZIP, wheel and checksum sidecars are supplied as conversation downloads, not GitHub binary-release assets.
