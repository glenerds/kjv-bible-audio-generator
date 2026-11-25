# Engineering Checkpoint — KJV Bible Audio Generator 0.4.11 (CI audio test dependency follow-up)

Date: 2026-11-24

- Canonical 0.4.10 source ZIP verified, 73 files and exact SHA-256 `4c9dffa08d75e8ee2efb60f9fa561311d3501f515dbf650e233f15ebd2cc07f9`.
- Public repo reconciliation: 72/72 archive files excluding README match Git blob hashes exactly; README intentionally contains continuation notes; three review documents exist only in the public repo.
- Fresh archive extraction compiled and passed the 123-test 0.4.10 baseline.
- 0.4.11 adds PyTorch to dev requirements and runs hosted Windows/Python 3.12 plus Ubuntu/Python 3.13 CI. PyTorch omission was exposed by both first-run runners; fixed.
- Second CI run got Ubuntu through CPU PyTorch install and compileall. Full suite result: **110 passed, 12 failed, 2 skipped**. All 12 failures are caused by missing `ffmpeg` on the hosted test runner; this is a test harness provisioning issue, as tests intentionally assert FFmpeg is present for audio integration.
- Workflow now installs FFmpeg from Chocolatey on Windows and apt on Ubuntu (CI only), and a regression test checks both provisioning lines.
- Third CI run must be checked to confirm both suites pass and PowerShell scripts parse.

Production FFmpeg is still not approved for packaging. No real Qwen inference, genuine Genesis speech, Windows PyInstaller app, offline playback/USB acceptance, CPU performance benchmark or full-Bible build has passed.
