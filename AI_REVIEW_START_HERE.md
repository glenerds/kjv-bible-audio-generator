# AI Review — Start Here

This public repository contains the KJV Bible Audio Generator 0.4.10 developer source snapshot.

## Instructions for AI reviewers

1. Inspect the source code in this repository directly; do not stop at the README.
2. Read `AI_REVIEW_PROMPT.md` before beginning. It defines the product requirements, five specialist review roles, release blockers, test expectations, and the required report format.
3. Select one role (Qwen/TTS, Windows release engineering, persistence/reliability, security/licensing, or independent QA/architecture). Different AI systems should use different roles.
4. Inspect actual files and cite repository paths, symbols, and verified line numbers.
5. If you can run code, report exact commands, environment and output. If you cannot run a test, label it NOT TESTED.
6. Do not claim genuine Qwen inference, audible voice consistency, native Windows operation, offline playback, USB relocation or full-Bible production has passed unless you actually performed that test. Synthetic/mock audio does not count as genuine Qwen output.
7. Return a detailed Markdown report following the exact sections in `AI_REVIEW_PROMPT.md`.

## Reviewer roles

- **Reviewer 1 — Qwen/TTS:** Qwen API compatibility, model loading, VoiceDesign/Base workflow, inference, streaming and voice consistency.
- **Reviewer 2 — Windows release:** portable build, dependencies, FFmpeg, offline operation, startup, playback and USB relocation.
- **Reviewer 3 — reliability:** SQLite, queue correctness, atomic writes, pause/resume, retries, crash recovery and regeneration.
- **Reviewer 4 — security/licensing:** model integrity, hashes, extraction, path safety, software/model/FFmpeg licenses and attribution provenance.
- **Reviewer 5 — independent QA:** full architecture, real-world workflows, test gaps, performance and overlooked release blockers.

## Current baseline

Version 0.4.10. Project records report 123 automated tests passing in the recorded Linux source environment. This does not prove real Qwen inference or native Windows release readiness. See `docs/DEVELOPMENT_STATUS.md` and `docs/RESUME_HERE.md` for the detailed status and limitations.
