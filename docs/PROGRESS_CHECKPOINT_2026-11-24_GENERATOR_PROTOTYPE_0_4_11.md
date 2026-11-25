# Engineering Checkpoint — 0.4.11: ADS rejection test assertion follow-up

Date: 2026-11-24

The Windows-specific NTFS stream enumeration now emits "alternate data streams" for the detected named stream. The old unsafe-path regression only recognized unsafe/reserved/manifest.json text. Expanded the expected diagnostic tokens so a correct ADS rejection does not fail the test based only on message wording. The separate Windows-only license ADS test verifies the exact new error. Product behavior unchanged. Local Linux: compileall PASS; 126 passed, 2 Windows-only skipped. Latest hosted Windows full suite still pending.

---

# Engineering Checkpoint — 0.4.11: native Windows alternate data stream validation

Date: 2026-11-24

- Latest verified package version remains 0.4.11.
- Native Windows suite for the sparse-fixture correction: 125 passed, 1 failed in 134.73 seconds. Failure was in FFmpeg notice importer accepting a file path with :stream; NTFS ADS is hidden from normal pathlib enumeration.
- Implemented Windows-only NTFS stream enumeration with FindFirstStreamW/FindNextStreamW/FindClose. Checks source doc tree and license, staged doc tree and license, installed notice tree and license verification. Only ordinary unnamed ::$DATA stream allowed. Known unsupported/no-stream errors are handled; unexpected errors fail closed.
- Adjusted platform-dependent invalid source path test cases (Windows normalizes/reserves specific names) and added raw validator test plus Windows-only ADS-on-license test.
- Local Python 3.13 Linux: compileall PASS; **126 passed, 2 skipped** (Windows-only sparse/ADS).
- Next: check new native Windows Actions run for sparse test, full suite and PowerShell AST parse. No actual Qwen or packaged Windows app acceptance yet.
