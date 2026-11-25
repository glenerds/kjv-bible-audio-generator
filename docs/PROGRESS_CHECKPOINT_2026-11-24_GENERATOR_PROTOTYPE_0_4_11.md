# Engineering Checkpoint — KJV Bible Audio Generator 0.4.11

Date: 2026-11-24

## Starting point and verified source

- Canonical developer archive 0.4.10: 171,950 bytes, SHA-256 `4c9dffa08d75e8ee2efb60f9fa561311d3501f515dbf650e233f15ebd2cc07f9`.
- ZIP integrity: PASS, 73 files.
- Public repository comparison: 72/72 non-README archive files identical by Git blob SHA. README has intentional continuation updates; public repo has three AI review files not in the canonical archive.
- Fresh extraction: `/mnt/data/kjv-generator-verification-pass-20261124`.
- Python 3.13.5 / Linux x86_64; compileall PASS; pre-fix source test suite 123 passed.

## 0.4.11 change

The first real GitHub Actions execution on native Windows / Python 3.12 and Ubuntu / Python 3.13 successfully checked out source, installed the declared development dependencies and compiled all source/tests. Both test jobs failed on collection because `tests/test_qwen_adapter.py` imports `torch` while `torch` was missing from the `dev` extra.

Fix:
- Added `torch==2.10.0` to the `dev` optional dependencies.
- Updated CI to install the official CPU-only PyTorch 2.10.0 wheel before installing the project test extras.
- Added a regression test enforcing the dev dependency.
- Bumped package version in pyproject and package metadata to 0.4.11.
- Added cross-platform CI for native Windows tests, PowerShell parser checks and Linux/Xvfb tests.

## Local results after fix

- `python -m compileall -q src tests tools` — PASS.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 xvfb-run -a env PYTHONPATH=src pytest -q` — **124 passed** in 29.16 seconds.
- CPU PyTorch version `2.10.0+cpu` satisfies the declared `==2.10.0` version constraint.
- Hosted rerun result still needs to be inspected after commit.

## Not yet passed

Genuine Qwen VoiceDesign/Base loading and Genesis 1 audio; listening and character consistency; native Windows test run / PowerShell parse until the corrected CI completes; actual PyInstaller build with pinned models; approved bundled LGPL FFmpeg binary, notices, MP3 encoder and encode/decode probe; Windows offline launch/playback; USB relocation; CPU/RAM/long-run benchmarks; complete 1,189 chapter MP3 and cue generation/storage validation; KJV-specific cast/quotation review and licensing review.

## Continue here

The public repository is `glenerds/kjv-bible-audio-generator`. Check the latest GitHub Actions run for the 0.4.11 commit, inspect failures and fix concrete defects. Do not label any source test as a genuine Qwen or finished Windows acceptance test.
