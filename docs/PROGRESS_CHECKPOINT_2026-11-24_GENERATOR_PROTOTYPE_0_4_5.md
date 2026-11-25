# Engineering Checkpoint — KJV Bible Audio Generator 0.4.5

Date: 2026-11-24  
Status: source hardening and regression validation complete for this checkpoint; not customer-ready.

## Scope of this work session

Continued from the 0.4.4 checkpoint. Focused on the FFmpeg third-party notice importer/verifier because those notice files are copied into the Windows distribution and the previous validator needed stricter Windows filesystem semantics.

## 0.4.5 changes

- Bumped package version to `0.4.5` in `pyproject.toml` and `src/kjv_audio_generator/__init__.py`.
- Added `PureWindowsPath` validation in addition to POSIX path validation.
- Rejects drive-qualified and UNC paths, absolute/rooted paths, backslashes, colon/alternate-data-stream syntax, NUL, traversal, noncanonical duplicate separators, Windows reserved device names (including COM/LPT names and superscript digits), trailing dots/spaces, and Windows case-insensitive path collisions.
- Rejects a root `manifest.json`/`MANIFEST.json` file from source documentation because it would collide with the generated integrity manifest on Windows.
- Validates source documentation file and directory paths before copying. Import refuses Windows-incompatible source paths and duplicate/case-colliding paths.
- Verification refuses symlinks on the notice root, manifest, top-level FFmpeg license file, and anywhere below the notice tree before it reads any listed file.
- Manifest paths are fully validated as a set before any listed file is opened; byte counts must be real integers (not booleans), SHA-256 must be exactly 64 hex characters, and duplicate/case-colliding entries fail closed.
- Import refuses symlinked pre-existing destinations and replaces an existing regular license file by unlinking it before copying, avoiding writes through a hard-linked destination.
- Added regression tests for Windows drive/UNC/ADS/traversal/reserved/trailing-dot-space/noncanonical paths, case collisions, malformed paths at import, symlinked manifest/license/notice files, and previous success/tamper/unlisted-file cases.

## Verification performed

- `python -m compileall -q src tests tools` — PASS.
- Focused FFmpeg asset/security tests — **16 passed**.
- Expanded CLI/GUI integration tests — **15 passed**; `__main__.py` coverage measured at **96%**. These tests cover GUI invocation, successful preflight/audio-smoke wiring, speaker-projection import and the CLI parse-to-queue path.
- Full suite from the current source tree: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 xvfb-run -a env PYTHONPATH=src pytest -q` — **107 passed in 29.79 seconds**, process exit code 0.
- An exploratory coverage run also completed all 101 tests before this CLI test expansion and showed 82% overall package statement coverage; the isolated CLI test run now measures 96% for `__main__.py`.
- Wheel built: `kjv_audio_generator-0.4.5-py3-none-any.whl`, 51,032 bytes, SHA-256 `952a61e57483cf958233ceee33cea4a21b4a6dccf78919c94e965ed8d84cd5bf`.
- Wheel installed into a clean target. Import reported version 0.4.5; packaged tables verified 66 books, 1,189 chapters and 31,102 expected KJV verses.
- Installed `--self-test` returned expected fail-closed exit code 2 because the actual Qwen model directories, pinned model manifest, Qwen runtime and bundled Windows `ffmpeg.exe` are absent.
- Installed `--audio-smoke` returned expected fail-closed exit code 3 because the Base model is absent.
- Sealed source ZIP: 66 files; ZIP CRC, clean extraction and compileall passed; the extracted directory passed the same 107-test suite.

## Speaker attribution research addendum — 2026-11-24

Reviewed Clear Bible speaker quotations, Logos/Lexham Reported Speech, Bible Ontology, Jesus' Words and Theographic. No complete, verified, openly redistributable KJV speech-to-speaker map was found. The current FCBH/MACULA data is a non-KJV suggestion source; the Logos dataset is a licensing/export inquiry; Bible Ontology is model-read and BSB text; Jesus' Words is Gospel-only and CC BY-NC 4.0; Theographic links KJV verses to people/entities but not who speaks. Full notes and citations/URLs are in `docs/ATTRIBUTION_DATASET_RESEARCH_2026-11-24.md`.

Engineering rule: keep source provenance and alternate speakers, do not overwrite manual assignments, and leave ambiguous/nested/unnamed speech in Needs Review. Evaluate licensed data or build a KJV-specific adjudicated set before enabling confident automatic assignment.

## Still not verified / no change in release blockers

- No genuine Qwen model inference and no authentic Genesis 1 audio. The Genesis 1 integration still uses synthetic test audio only.
- No native Windows execution, one-folder EXE, offline launch, real playback, USB relocation, or Windows FFmpeg binary/license/source verification.
- The BtbN LGPL FFmpeg archive candidate is still unapproved because the release archive/executable was not downloaded and inspected. No actual Windows `-version`, `-buildconf`, `-L`, encoder table, dependency notice set or WAV→MP3→decode probe has passed.
- No CPU/RAM benchmark for actual Qwen generation, no 1,189-chapter audio run, and no final USB audio collection size measurement.
- Full KJV-specific speaker attribution and full legal/software/model/codec/data licensing review remain unfinished; dataset research did not identify a complete, verified KJV speaker map with confirmed redistributable rights.

## Resume instructions

Continue from this exact 0.4.5 source tree. Do not ask the user to install or test it. Read `docs/ATTRIBUTION_DATASET_RESEARCH_2026-11-24.md` before changing speaker attribution. First seek a real pinned Windows LGPL FFmpeg package and verify the binary plus notices on Windows; pursue a licensed or independently adjudicated KJV speaker map; then get pinned Qwen assets/runtime working on native Windows 11 / Python 3.12 and generate authentic Genesis 1 before attempting the long-run/Windows release gates.
