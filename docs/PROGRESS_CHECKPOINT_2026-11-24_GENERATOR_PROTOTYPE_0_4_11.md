# Engineering Checkpoint — KJV Bible Audio Generator 0.4.11 (native Windows sparse test-fixture follow-up)

Date: 2026-11-24

- Canonical 0.4.10 developer ZIP SHA-256: 4c9dffa08d75e8ee2efb60f9fa561311d3501f515dbf650e233f15ebd2cc07f9; 73 entries, ZIP integrity PASS.
- Public repo reconciliation: all 72 non-README archive files match Git blob SHAs exactly; README is intentionally updated; the repo has three AI-review-only documents.
- Clean extraction compileall PASS; 0.4.10 source baseline 123 tests passed.
- 0.4.11 adds the explicit torch dev dependency, a CI matrix (Windows/Python 3.12 and Ubuntu/Python 3.13), CI-only FFmpeg provisioning and regression checks.
- Hosted Ubuntu after setup corrections: 125 tests passed.
- Hosted Windows after setup corrections: dependencies and compileall passed; pytest ran but filled disk. Root cause: fake Qwen weight test fixtures used truncate, sparse by default on Linux but fully allocated on Windows. Added _truncate_sparse_file() using Windows FSCTL_SET_SPARSE / DeviceIoControl before truncating. Local compileall PASS and 125 tests passed after patch.
- Wait for the next Windows Actions job result, including PowerShell script AST parse.

No genuine Qwen inference/Genesis speech, model asset download and hash, customer Windows PyInstaller app, bundled approved FFmpeg, offline playback, USB relocation, CPU/RAM performance, complete 1,189 chapter run, KJV-specific dialogue review or complete licensing audit has passed.
