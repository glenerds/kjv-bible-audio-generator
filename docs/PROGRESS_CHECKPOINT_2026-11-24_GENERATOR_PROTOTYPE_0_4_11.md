# Engineering Checkpoint — KJV Bible Audio Generator 0.4.11 (NTFS sparse fixture correction)

Date: 2026-11-24

- Latest product package remains version 0.4.11; this change is confined to tests/CI and does not alter app behavior.
- Windows sparse probe: `FSCTL_SET_SPARSE` marked the file correctly, but NTFS reported 147,324,928 allocated bytes for the 3.5 GB fixture after normal truncate.
- Microsoft documentation confirms normal zero writes can allocate physical space in sparse files and that `FSCTL_SET_ZERO_DATA` can deallocate zero ranges.
- Updated test fixture to call `FSCTL_SET_ZERO_DATA` after logical EOF extension with the full `[0, size)` range. Windows allocation test still checks file size, sparse attribute and <1 MiB actual allocation for both the main and speech-tokenizer fake weights.
- Linux local: compileall PASS; 125 passed, 1 Windows-only test skipped. Windows focused allocation test and full suite pending.
- Do not claim Windows pass until diagnostic, full test suite and PowerShell parse finish successfully.

No genuine Qwen inference, official model integrity, customer Windows build/playback, production LGPL FFmpeg approval, USB relocation or full-Bible generation has passed.
