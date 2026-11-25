# Engineering Checkpoint — 0.4.11: NTFS sparse allocation diagnostic

Date: 2026-11-24

- Version 0.4.11 project source remains unchanged; this pass adds a Windows-only test diagnostic and workflow step.
- Two Windows runs with the FSCTL_SET_SPARSE helper were marked failed, but GitHub's job API still showed the test step as in_progress and log archive retrieval failed with BlobNotFound. Cannot infer the actual exception or confirm sparse allocation based on those records.
- Both runs installed dependencies, passed compileall and progressed to the full Windows test step.
- Ubuntu passed the full 125-test suite after PyTorch and FFmpeg test setup.
- Added a Windows-only regression check that verifies both fake weights retain their logical sizes, carry FILE_ATTRIBUTE_SPARSE_FILE, and allocate less than 1 MiB on disk according to GetCompressedFileSizeW.
- Added a dedicated Windows CI step to run this test before the full suite. Linux skips this NTFS-only check.
- Next: run local compileall/full suite; inspect focused Windows sparse smoke result; then full Windows suite and PowerShell parser. Don't claim native Windows pass until all complete.

No genuine Qwen inference, Windows application build, bundled LGPL FFmpeg approval, offline playback, USB relocation or production-generation benchmark has passed.
