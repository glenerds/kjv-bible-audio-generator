# KJV Bible Audio Generator — developer prototype 0.4.10

**Status: developer prototype only. Not a customer-ready Windows application.**

This public repository contains the KJV Bible Audio Generator source snapshot and independent AI review instructions. It is separate from the older KJV Bible Reader / USB Builder.

## Start here

- [Full project requirements and engineering history](README.md)
- [Development status and verified test results](docs/DEVELOPMENT_STATUS.md)
- [Resume / continuation notes](docs/RESUME_HERE.md)
- [0.4.10 engineering checkpoint](docs/PROGRESS_CHECKPOINT_2026-11-24_GENERATOR_PROTOTYPE_0_4_10.md)
- [Independent AI engineering review prompt](AI_REVIEW_PROMPT.md)
- [AI review start instructions](AI_REVIEW_START_HERE.md)

## Project objective

Build a self-contained, portable Windows desktop app that imports KJV text and generates 1,189 chapter MP3 files across 66 books, with verse/sub-verse timing cues, multiple speakers, consistent recurring character voices, and durable pause/resume/crash recovery.

The intended speech engine is genuine Qwen3-TTS VoiceDesign and Base. Mocked or synthetic audio is not evidence of real Qwen operation.

## 0.4.10 baseline

The project documentation records **123 automated tests passing** on the source suite, including a clean source-archive extraction. Those tests do not establish genuine Qwen speech, native Windows operation, offline playback, USB portability, or full-Bible generation.

**Open release gates:** real Qwen Genesis 1 inference and listening validation; recurring-character voice comparison; native Windows build/start/playback; bundled FFmpeg verification; offline and USB acceptance; real-model crash recovery; CPU/RAM/storage benchmarks; full 1,189-chapter production; and final attribution/licensing review.

## Important

Do not describe this prototype as finished or customer-ready. See [Development Status](docs/DEVELOPMENT_STATUS.md) for tested versus untested functionality.

## AI reviewers

This repository is public so independent AI systems and reviewers can inspect the source directly. Start with [AI_REVIEW_START_HERE.md](AI_REVIEW_START_HERE.md), then follow the detailed [AI_REVIEW_PROMPT.md](AI_REVIEW_PROMPT.md).

Reviewers must explicitly say when a test was not run. They must not invent line numbers, test results, Qwen speech results, or Windows acceptance results.
