# Continuation checkpoint — 2026-11-25 (cross-chapter narrator test added; Windows package final evidence retest)

This is the newest recovery point and supersedes older status where different.

## Current source state
- Current branch head: `087aaba01b83d3e8a5a5159fa3dc47b6d6155f29`.
- Prototype version remains **0.4.12**.
- `tools/windows_package_acceptance.ps1` no longer attempts to copy a diagnostic file onto itself. A prior waited-process Windows run reached that final evidence-collection loop only after both original and relocated self-test/audio-smoke/FFmpeg-decode stages had completed; the old loop then raised `Copy-Item` because source and destination were identical. The new script correctly leaves those diagnostic files where the frozen entrypoint wrote them.
- The current Windows package runs `45653137050`, `45654417086`, and `45655573537` are/ were exercising the corrected process-wait/evidence path. Do not claim Windows portable acceptance until one run completes and its artifact/report is checked.
- The most recent full green source baseline before the cross-chapter files: Windows **149 passed**; Ubuntu **145 passed, 4 skipped**. The subsequent cross-chapter harness added static checks and extended the Qwen workflow, so its latest source run is still pending.

## New cross-chapter voice-continuity test
- Added `examples/genesis_cross_chapter_voice_test.txt`, a deliberately minimal fixture with Genesis 1:1 and Genesis 2:23. It is explicitly not a complete Bible import.
- Independently compared the two fixture lines against the `Genesis.json` file in the public KJV corpus at `https://github.com/renniemaharaj/kjv-bible`; both lines now match exactly. The existing Genesis 1 test fixture was also compared verse-by-verse: all 31 verses matched the same corpus.
- Added `tools/qwen_cross_chapter_voice_real.py`. It uses one real `ChapterWorker`, one production `QwenVoiceBackend`, and one output folder across two chapter records. Genesis 2:23 has a manually reviewed narrator/Adam split that rejoins exactly to the original KJV verse.
- The harness checks one batch voice-preparation phase; one VoiceDesign reference and one Base clone prompt per narrator/Adam profile; the same narrator profile fingerprint before/after generation; identical narrator prompt-file SHA-256 at the Genesis 1 and Genesis 2 narrator synthesis calls; two chapter MP3s that decode to non-silent audio; and exact cue-text preservation.
- The Genesis 2:23 punctuation was corrected during review: the approved KJV uses a **colon** after `flesh of my flesh`. The fixture and speaker split now use that exact punctuation. This was verified by direct comparison to the source JSON, not by inference.
- The workflow `.github/workflows/qwen-real-inference.yml` runs the new harness after the real Genesis 1 test, reusing the same already-downloaded and hash-verified Qwen snapshots. A separate artifact is planned for the two chapter excerpts, cues, fingerprints and metrics.
- The cross-chapter real-Qwen run on the corrected source is `45655573454`; source tests on the same head are `45655573349`. They had only just been queued at the time of this note; no real cross-chapter pass is claimed yet.

## Genuine Qwen Genesis 1 evidence remains valid
- Run `45639088515` previously passed the full 31-verse Genesis 1 Qwen worker pipeline on Linux CPU. It produced a 96 kbps MP3 with 33 exact-text timing segments (31 narrator, 2 reviewed God speech), passed MP3 decoding and non-silence checks, and recorded zero failed chapters.
- This establishes real speech and chapter assembly only. It does not establish perceptual voice quality or voice continuity across chapters; that is why the new small test exists.

## Next tasks
1. Confirm the latest source suite passes on Windows and Ubuntu, including the new static test and updated Qwen workflow environment counts.
2. Inspect the new real-Qwen cross-chapter workflow after Genesis 1 finishes. Verify the prompt hash is the same at both narrator uses and check the actual Genesis 1/2 MP3s and cue JSON.
3. Confirm one native Windows package run completes: self-test, real Qwen audio smoke, MP3 decode, drive-letter relocation, relocated audio smoke, relocated decode, evidence JSON and uploaded artifact.
4. Inspect the frozen package contents and hashes; then continue with offline Windows operation, physical USB testing, crash recovery, later speaker identities, target-PC benchmarks and full 1,189-chapter production.

**Release remains developer prototype only — not ready for customer testing.** Full-book generation, subjective listening approval, Bible-wide attribution, physical USB and target-PC performance, and legal/source-obligation review remain open.

---
# Continuation checkpoint — 2026-11-25 (150 Windows / 146 Ubuntu tests green; package evidence finalizing)

This checkpoint supersedes the source counts in the earlier process-wait note below.

## Latest source verification
- Main commit before this README update: `dbcc0ed9aaaf7c75cd89a2a595749256928fb51a`.
- Cross-platform source run `45653136914` passed:
  - Windows 11 / Python 3.12: **150 passed** in 115.23 seconds; NTFS sparse-file fixture passed; all five PowerShell scripts parsed.
  - Ubuntu 24.04 / Python 3.13: **146 passed, 4 skipped** (Windows-only NTFS/PowerShell cases).
- Added regression test for the Windows package evidence-copy bug: diagnostics are already written directly into the evidence folder, so the acceptance script must not copy them back onto themselves.

## Latest portable Windows acceptance progress
- Package run `45653137050` is running on commit `dbcc0ed9aaaf7c75cd89a2a595749256928fb51a`.
- The previous waited-process package run `45650728281` reached the last evidence-copy loop only after passing original frozen self-test, real Qwen audio smoke, original MP3 decode, moved-folder/new-drive-letter relocation, relocated self-test, relocated Qwen audio smoke and relocated MP3 decode. It failed only because `Copy-Item` tried to copy each diagnostic file onto itself in the same evidence folder.
- Removed that self-copy in `tools/windows_package_acceptance.ps1`; current run should now finish summary generation and upload compact evidence. This latest run's outcome is **pending**, not yet accepted.
- Windows GUI window creation itself has not yet been explicitly smoke-tested; current acceptance exercises the frozen CLI in windowed mode. Physical USB removal/reinsertion and the user's actual GPU playback are also still pending.

## Next
1. Confirm package run `45653137050` reaches `WINDOWS_PORTABLE_PACKAGE_ACCEPTANCE_PASSED` and uploads its artifact. Inspect self-test/audio reports, diagnostics, MP3s and manifest evidence.
2. Add a short frozen-GUI launch smoke (open the Tkinter window and auto-close it under a test-only environment variable), then rerun the native Windows package if required.
3. Measure the on-disk portable folder size and decide a practical, complete download artifact strategy. Do not claim a user-downloadable package until its complete files are preserved and verified.
4. Keep physical USB, offline operation, restart/recovery, cross-chapter speaker continuity, full 1,189-chapter output, target-PC GPU/RAM/speed and final software/model/codec/source-license review open.

## Release status
**Developer prototype only—not ready for user/customer testing.** Genuine offline Qwen CPU inference and full Genesis 1 MP3/cues have passed. Source tests are green on Windows and Ubuntu. The native Windows frozen app has passed the core CLI/audio/relocation checks in a run that failed only at evidence finalization; the corrected acceptance run must finish and upload evidence before the package gate is marked passed.

---
# Continuation checkpoint — 2026-11-25 (source suite green; frozen process wait in acceptance)

This is the newest recovery note. Retain the earlier genuine-Qwen and Genesis 1 evidence below.

## Latest committed state
- Public repository: https://github.com/glenerds/kjv-bible-audio-generator
- Current source head at checkpoint: `a7a9abaf9121a9acd033e7437aff429c4679a9cc`.
- Prototype still version **0.4.12**.
- Cross-platform source CI run `45651413075` passed:
  - Windows 11 / Python 3.12: **149 passed** in 110.74 seconds; NTFS sparse-file fixture passed; all five PowerShell scripts parsed.
  - Ubuntu / Python 3.13: **145 passed, 4 skipped** (NTFS/Windows-only cases).
- The Windows package process launcher was corrected in commit `065be59251743fd3005cc28ed1dae85fbe8adbaf`. It now uses .NET `ProcessStartInfo.ArgumentList`, calls `WaitForExit(timeout)`, and reads the process exit code before inspecting self-test/audio JSON. This avoids checking a report before the GUI-subsystem executable has actually exited.
- The old call-operator acceptance runs `45649012489` and `45649421230` completed with the same failure: PyInstaller produced the one-folder build, but after launching the windowed exe there was no entrypoint diagnostic report at the point the script checked. That is consistent with an asynchronous launch/check race, not proof the app code itself failed.
- New waited-process package runs `45650728281` (commit `065be59`) and `45651413337` (commit `a7a9ab`) were still in their build/acceptance step at the time of this note. No frozen-app acceptance result is claimed yet.

## Next immediate checks
1. Inspect run `45650728281` and `45651413337`. The waited process must create the self-test diagnostics and JSON report; inspect argv and any startup traceback if it still fails.
2. Once self-test passes, inspect actual Qwen CPU audio-smoke results and FFmpeg report, then continue through relocated self-test and relocated audio smoke.
3. If the app times out, use the entrypoint diagnostic file to establish whether CLI arguments arrived and whether `main()` was reached. If the process exits nonzero, inspect the recorded exception rather than guessing at PyInstaller warnings.
4. After package success, verify actual package contents and hashes, then keep physical USB/new-drive-letter and target PC GPU playback/performance as separate release checks.

## Confirmed real audio work
- The full genuine Qwen Genesis 1 run `45639088515` passed on Linux CPU: both pinned models passed full-file SHA-256, and the production worker rendered all 31 verses as a 96 kbps MP3 with 33 exact-text timestamped speech segments (31 narrator, 2 manually reviewed God speech). One chapter completed, zero failed.
- I extracted and re-verified the MP3 independently: **3,032,397 bytes**, 252.672 seconds, 96,010 bps. SHA-256 `08b40550f5afec6fc5831b5ece77298eab2558901fc0a56abcf0084c82c8bac8`.
- A genuine sample MP3 and a companion ZIP containing the MP3, 33-segment cue JSON and metrics are preserved in this conversation.
- These results do not establish later-chapter character consistency, Bible-wide speaker attribution, subjective listening quality, or Windows frozen-app operation.

## Release status
**Still a developer prototype—not ready for user/customer testing.** Genuine CPU Qwen inference and full Genesis 1 audio/cues are verified on Linux. Native Windows frozen-app startup, self-test, audio smoke, relocation, offline operation, full 1,189-chapter production, target-PC performance, listening QA and final software/model/codec/source-license review remain open.

---
# Continuation checkpoint — 2026-11-25 (frozen Windows diagnostics and retest)

This latest checkpoint is newer than the previous handoff below.

## Current branch and CI
- Current starting head: `d456a6c24a3daee6f6ea4784f417bcb795aefa7b`.
- Added module-level `Path` import in `tests/test_gui_cli.py`, fixing the prior `NameError` in the native package acceptance test.
- The frozen `tools/entrypoint.py` now optionally writes startup/exit diagnostics when `KJV_APP_DIAGNOSTICS_FILE` is set. It captures argv, executable, cwd, frozen state, stdout/stderr availability, exit code and traceback without changing normal app behavior. `windows_package_acceptance.ps1` records diagnostics for original and relocated self-test/audio-smoke launches.
- Updated static tests to match the diagnostics-enabled launcher and the actual quoted relocation command (`subst {0} "{1}"`).
- Source run `45649904856` on this head: Ubuntu **145 passed, 4 skipped**. Native Windows full suite is still running; NTFS fixture precheck and compile passed.
- Native Windows package run `45649904906` is still in the build/acceptance step. Earlier package runs `45649012489` and `45649421230` are also still active. None has yet produced a final accepted result or uploadable package evidence.

## Already verified audio milestone
The genuine offline Qwen CPU run `45639088515` completed successfully on the previous source head. Both pinned 1.7B model checkpoints and tokenizers passed full-file SHA-256. The real production worker generated all 31 Genesis 1 verses into a 96 kbps, 3,032,397-byte MP3 with 33 timestamped segments (31 narrator, 2 reviewed God speech), exact verse-text checks, MP3 decode and non-silence checks. Runtime was 1,298.381 seconds on the hosted CPU runner; the artifact and full hashes are documented in the handoff below. This does not prove listening quality or cross-chapter voice identity.

## Immediate next
1. Confirm the current Windows source suite and PowerShell parse checks pass.
2. Inspect the frozen package run's diagnostics. If the process does not enter the CLI, use its argv/launch record to correct the PyInstaller startup path. If it enters and raises, fix the actual traceback.
3. Rerun package acceptance until self-test, short real Qwen audio, MP3 decode, relocation and relocated audio all pass.
4. If the package succeeds, inspect uploaded evidence and verify the executable, bundled FFmpeg, models, generated MP3s and manifests; keep offline Windows and physical USB testing open if not exercised.

**Release status remains developer prototype, not ready for user/customer testing.** The Linux CPU Genesis chapter pipeline is real and passed. Native Windows frozen app acceptance is still pending.

---

# Continuation handoff — 2026-11-25 (real Genesis 1 passed; Windows package acceptance under repair)

This recovery note supersedes older status statements below.

## Current source and CI
- Public repository: https://github.com/glenerds/kjv-bible-audio-generator
- Version: **0.4.12**; branch head before this README update: `684b2d2fb19913ca0dc2ea47d57532363e83de84`.
- Latest cross-platform test run `45641832984` failed only on test-harness `NameError: Path is not defined`: Ubuntu **143 passed, 4 skipped, 1 failed**; Windows **147 passed, 1 failed**. Move `from pathlib import Path` to module-level imports in `tests/test_gui_cli.py`.
- Native Windows package run `45641833114`: PyInstaller completed a one-folder build, but packaged `--self-test` did not create the report expected by the acceptance script. Frozen startup, real speech, offline operation and relocation are not yet accepted.
- Earlier green source baseline: Windows **141 passed**; Ubuntu **137 passed, 4 skipped**; all five PowerShell scripts parsed.

## Genuine Qwen and full Genesis 1 — passed
- Workflow: https://github.com/glenerds/kjv-bible-audio-generator/actions/runs/45639088515; tested commit `a72b9e0601d59f195d25a18abbe91857ffefbfb7`.
- Exact pinned 1.7B checkpoint files passed full SHA-256: VoiceDesign `391e8db219f292c515297cdceeb43e4eae67cdde35fa57e79a6a8a532fca0522` (3,833,402,552 bytes); Base `38fc7fc51c5e776e840414b6fd443962e9411b9654888fd7913e4da643cb857c` (3,857,413,744 bytes); both speech tokenizers `836b7b357f5ea43e889936a3709af68dfe3751881acefe4ecf0dbd30ba571258` (682,293,092 bytes each).
- Offline production QwenVoiceBackend generated genuine 24 kHz speech; the smoke sample is 3.12 s, 149,804 bytes, RTF 4.208, peak RSS 5,095.1 MiB.
- The same CPU runner processed all 31 Genesis 1 verses through `ChapterWorker + QwenVoiceBackend + ChapterAudioAssembler`: 33 segments (31 narrator, 2 manually reviewed God speech in verses 3 and 6). All cue text matched source verse text exactly. Result: **1 complete chapter, 0 pending, 0 running, 0 failed**.
- Genuine 96 kbps MP3: **3,032,397 bytes**, **252.64 s**, decoded peak 0.817366, RMS 0.116028. FFmpeg decode and non-silence checks passed. End-to-end CPU time **1,298.381 s** (21m 38s), including voice preparation; this is a hosted CPU benchmark, not a projection for the user's RTX 2070.
- Evidence artifact `qwen-real-genesis1-pipeline`, ID `15035723541`, digest `18b6dd9a1d6a20334cc0a58d81a25a4f68f832a414b38b7778791102513a80e7`, expires 2026-12-09. It contains the MP3, 33-cue JSON, generation report/database, voice references/prompts, model integrity report and metrics. Downloaded ZIP integrity passed; MP3 SHA-256 `08b40550f5afec6fc5831b5ece77298eab2558901fc0a56abcf0084c82c8bac8`.
- This tests only two explicit Genesis 1 speech overrides; no Bible-wide attribution, subjective listening or later-chapter identity claim is made.

## Next steps
1. Fix the missing module-level `Path` import and rerun both source suites.
2. Align the frozen `--self-test` report contract across `tools/windows_package_acceptance.ps1`, `tools/entrypoint.py` and `src/kjv_audio_generator/__main__.py`; preserve stdout and atomically write/validate a JSON report.
3. Rerun Windows package acceptance: require startup, self-test report, real Qwen audio smoke, FFmpeg validation, integrity and drive-letter relocation.
4. Investigate PyInstaller missing imports/DLLs using actual frozen Qwen inference.
5. Continue with offline Windows operation, restart/recovery, later-chapter identity, target-PC performance and final 1,189-chapter storage.

## Release status
**Developer prototype only — not ready for user testing.** Real Qwen CPU speech and the complete 31-verse Genesis 1 MP3/cue pipeline have passed on Linux. The native Windows frozen application has not passed runtime acceptance; listening QA, later-chapter continuity, USB/offline Windows operation, long-run recovery, full-book production, target-PC benchmarks and final model/software/codec/source-license review remain open.

The user requires a README checkpoint before every future “Continue working” request and an explicit pause message if work stops.

---

# Continuation update — 2026-11-25 (Genesis workflow integrated; full real chapter queued/running)

## Current recovery point
- Public repo: https://github.com/glenerds/kjv-bible-audio-generator
- Prototype version: **0.4.12**.
- Source branch head at update start: `7765234f7b51af2f77b5b4f7efcb82706489930e`.
- First actual offline Qwen CPU speech passed on run `45635718244` and was independently inspected. Both 1.7B snapshots and tokenizer weights passed full-file SHA-256; Qwen VoiceDesign and Base generated a real 24 kHz mono WAV, 3.12 seconds, RTF 4.208, peak RSS 5,095.1 MiB. Artifact `qwen-real-cpu-inference-smoke` ID `15033491559`.
- Current Genesis 1 real-model harness: `tools/qwen_genesis1_real.py`. It runs all 31 Genesis 1 verses through the actual `ChapterWorker`, `QwenVoiceBackend` and `ChapterAudioAssembler`, with two explicit reviewed God-speech overrides. It verifies 33 cue segments, exact text preservation for every verse, 96 kbps MP3 output, a real FFmpeg decode and non-silent audio. Static harness/test code is committed; there is not yet a real Genesis MP3 pass.
- Combined workflow `.github/workflows/qwen-real-inference.yml` now downloads the two models once, verifies them, performs the short offline voice smoke, uploads that evidence, installs Linux FFmpeg, and then runs the full Genesis pipeline with the same already-downloaded local snapshots. It uploads a second artifact `qwen-real-genesis1-pipeline`.
- Combined Qwen/Genesis workflow run `45639088515` on commit `a72b9e0601d59f195d25a18abbe91857ffefbfb7` was accepted and had reached the model-download step on the most recent check. The run's final result and Genesis output have not yet been verified.
- Source suite run `45638207016` for Genesis harness commit `0437e4c73c36ab1f876c6b791701548cdb975ded` passed: Windows **141 passed, 1 skipped** (headless GUI test); Ubuntu **138 passed, 4 skipped** (Windows-only tests). The five PowerShell scripts parsed.
- A newer run `45639088537` on `a72b9e...` found one test-only issue: the old static assertion expected three HF cache variables, while the new Genesis inference step correctly makes four. No product code failed in that run. The assertion was corrected in commit `7765234f7b51af2f77b5b4f7efcb82706489930e`; its source-suite rerun is `45639386541`.

## Next steps
1. Confirm the corrected source-test run `45639386541` passes Windows and Ubuntu.
2. Monitor combined Qwen/Genesis run `45639088515`; inspect the hash report, the short smoke artifact, the Genesis progress logs, the completed 31-verse MP3 and cue JSON, and both artifact hashes.
3. Fix any real ChapterWorker/Qwen/FFmpeg issue evidenced by that run; do not substitute synthetic audio.
4. If Genesis passes, compare listening/voice characteristics and measure duration/RSS/RTF; then run a later chapter to check narrator/God voice prompt persistence and recurring identity.
5. Proceed to a genuine native Windows package build with the pinned models and verified FFmpeg, then clean-environment/offline/USB relocation tests.

## Release status
**Still a developer prototype, not ready for customer testing.** Genuine Qwen short-form CPU speech and real model hashes are now verified. The real 31-verse Genesis chapter pipeline, subjective listening QA, Windows packaged app acceptance, offline playback, USB relocation, long-run recovery, complete Bible generation, target-PC performance and final legal/source-obligation review remain open.

---

# Continuation update — 2026-11-25 (first genuine Qwen CPU speech passed; Genesis 1 harness added)

This is the newest recovery note. Earlier checkpoints are retained below.

## Current source state
- Public repository: https://github.com/glenerds/kjv-bible-audio-generator
- Prototype version: **0.4.12**.
- Current branch head at this checkpoint: `0437e4c73c36ab1f876c6b791701548cdb975ded`.
- Added `tools/qwen_genesis1_real.py` to exercise the production `ChapterWorker + QwenVoiceBackend + ChapterAudioAssembler` path on all 31 Genesis 1 verses, 33 expected speech segments, two manual God-speech splits, MP3 decoding and full cue-text preservation.
- This Genesis 1 real-model harness is committed and has a static regression test, but **has not yet run against the real downloaded models**.

## Genuine Qwen CPU inference — passed
- Workflow: https://github.com/glenerds/kjv-bible-audio-generator/actions/runs/45635718244
- Source commit tested: `de4cde4b26a2718a580b45ad858f5afde25bfb6b`.
- Both immutable Qwen3-TTS-12Hz-1.7B snapshots downloaded and passed full-file SHA-256:
  - VoiceDesign revision `5ecdb67327fd37bb2e042aab12ff7391903235d3`; main `model.safetensors` SHA-256 `391e8db219f292c515297cdceeb43e4eae67cdde35fa57e79a6a8a532fca0522`.
  - Base revision `fd4b254389122332181a7c3db7f27e918eec64e3`; main `model.safetensors` SHA-256 `38fc7fc51c5e776e840414b6fd443962e9411b9654888fd7913e4da643cb857c`.
  - Both speech-tokenizer files SHA-256 `836b7b357f5ea43e889936a3709af68dfe3751881acefe4ecf0dbd30ba571258`.
- Offline inference then ran using the production `QwenVoiceBackend`: VoiceDesign reference creation, Base clone-prompt creation, and Base synthesis all completed. Hugging Face/Transformers offline mode was enabled for inference.
- Genuine speech output: 24 kHz WAV, **3.12 seconds**, 149,804 bytes; measured real-time factor **4.208** on the GitHub CPU runner; peak process RSS **5,095.1 MiB**. Audio passed nonempty/finite/non-silent checks and WAV round-trip validation.
- Artifact `qwen-real-cpu-inference-smoke`, ID `15033491559`, includes the actual synthesized WAV, VoiceDesign reference WAV, prompt tensor/metadata, hash report and metrics. Independently downloaded and inspected; the reported metrics and checkpoint hashes matched.
- This is a successful short CPU inference test, not subjective voice/listening QA, multi-verse generation, Windows performance, or proof that the user's PC will achieve the same speed.

## Source CI baseline
- On commit `de4cde4b26a2718a580b45ad858f5afde25bfb6b`, run `45635718643` passed:
  - Windows 11 / Python 3.12: **141 passed**.
  - Ubuntu 24.04 / Python 3.13: **137 passed, 4 skipped** (Windows-only NTFS/PowerShell tests).
  - NTFS sparse-file precheck passed; all five PowerShell scripts parsed.
- A newer source CI run for Genesis harness commit `0437e4c73c36ab1f876c6b791701548cdb975ded` is/was triggered as run `45638207016`; inspect its Windows and Ubuntu jobs before claiming that commit green.

## Next engineering actions
1. Confirm run `45638207016` on Windows and Ubuntu, and fix any real regression.
2. Extend the existing real-Qwen workflow so it invokes `tools/qwen_genesis1_real.py` immediately after the already-passing short Qwen smoke, reusing the same downloaded and verified model snapshots on the same runner.
3. Verify the generated full Genesis 1 MP3, all 33 speaker segments and verse timestamp cues, exact KJV text preservation, actual MP3 decode and non-silence. Save the MP3, cue JSON and metrics as a separate evidence artifact.
4. After Genesis 1 passes, test recurring-speaker voice stability in a later chapter, real pause/stop/restart/recovery, then native Windows packaging, offline playback and USB relocation.
5. Measure realistic CPU/RAM/VRAM and speed on target hardware, then progress toward all 1,189 chapter outputs and final storage measurement.

## Release status
**Developer prototype only — not ready for user/customer testing.** First genuine Qwen CPU inference is now confirmed. The full Genesis 1 Qwen-to-MP3 pipeline, human listening QA, recurring voice continuity, real-model recovery, packaged Windows app, offline playback, USB relocation, complete-book production, target-PC performance and final legal/source-obligation review remain open.

The user requires a README update before each future "Continue working" request and an explicit pause statement when work stops.

---

# Continuation update — 2026-11-25 (cross-platform tests green; Qwen model download running)

## Latest verified source-test results
- Source commit: `de4cde4b26a2718a580b45ad858f5afde25bfb6b`.
- GitHub Actions run `45635718643` passed on both platforms:
  - Windows 11 / Python 3.12: **141 passed** in 154.79 seconds.
  - Ubuntu 24.04 / Python 3.13: **137 passed, 4 skipped** (Windows-only NTFS/PowerShell behavior).
  - Windows NTFS sparse-file fixture check passed.
  - All five PowerShell scripts parsed: Windows builder, Qwen asset preparation, FFmpeg notice importer, FFmpeg candidate audit, and FFmpeg bootstrap helper.
- This covers the new bootstrap acquire/skip and environment cleanup tests, plus pinned FFmpeg template/provenance checks and the real-Qwen workflow structure checks. It is not a full packaged-app build.

## Real Qwen CPU inference attempt
- Workflow run: `45635718244`; job ID `139280475735`; commit `de4cde4b26a2718a580b45ad858f5afde25bfb6b`.
- GitHub accepted the corrected workflow and allocated an Ubuntu 24.04 runner. Python 3.12 setup and pinned CPU PyTorch/Qwen runtime installation passed, and the resource-report step completed.
- At the time of this update, the two pinned 1.7B snapshots are still being downloaded. The model integrity report and offline inference steps have **not** run yet. No real model SHA-256 verification or Qwen audio success is claimed.
- The workflow downloads VoiceDesign revision `5ecdb67327fd37bb2e042aab12ff7391903235d3` and Base revision `fd4b254389122332181a7c3db7f27e918eec64e3`, verifies actual main-weight and speech-tokenizer hashes, then disables Hugging Face/Transformers network access before invoking the production `QwenVoiceBackend`.
- The smoke script produces a WAV and timing/RAM metrics only if VoiceDesign reference creation, Base prompt generation and Base speech synthesis all succeed. It explicitly excludes the synthetic test backend.

## Next steps
1. Monitor run `45635718244` until the download step finishes; inspect the actual file-hash report before claiming models verified.
2. Inspect offline inference logs and any produced WAV/metrics artifact. Fix real API/runtime/resource failures with evidence.
3. Then extend the same pinned-model test to the full Genesis 1 pipeline using the actual chapter worker, two manual speaker segments, MP3 assembly and verse/segment cue checks.
4. Re-run relevant CI and update this handoff with exact results.

**Release status: developer prototype only.** No complete user app, genuine Qwen audio, listening QA, USB portability, full Bible production, system benchmark or final legal signoff has passed yet.

---

# Continuation handoff — 2026-11-25 (real Qwen CPU test workflow correction)

This is the current recovery point for the next chat.

## Exact starting state
- Public source repository: https://github.com/glenerds/kjv-bible-audio-generator
- Application prototype version: **0.4.12**.
- Current source head before this README checkpoint: `d91909df6acc5372438b1cb3dfa8d03c2058d79b`.
- Source CI run `45629599733` completed successfully on that commit. Earlier same-commit Ubuntu summary: **136 passed, 4 skipped** (Windows-only NTFS and PowerShell checks); native Windows job also passed.
- The verified FFmpeg candidate audit remains green at run `45623835915`; archive/binary/license hashes and 35 imported notice hashes are documented below. The Windows builder's new automatic FFmpeg bootstrap is still being validated in the newest runs; do not claim a complete one-folder package.
- Added `tools/qwen_real_smoke.py`: it invokes the production `QwenVoiceBackend` to build a VoiceDesign reference, create a Base voice-clone prompt and synthesize a real sample. It rejects empty/non-finite/silent WAVs and records run-time and memory metrics. It never uses `SyntheticTestBackend`.
- Added `.github/workflows/qwen-real-inference.yml` to download both pinned snapshots, verify actual full-file SHA-256 values, switch model inference to offline mode, run the real adapter, and upload the sample/metrics.
- First workflow run `45629596039` failed immediately before allocating a job. Cause: it used the `runner.temp` context in job-level `env`; that context is unavailable there. **No models were downloaded, no checkpoint hashes were checked and no inference was attempted.**
- An attempted local workflow rewrite did not commit because its guard expected the wrong count of `runner.temp` references. No change from that attempted rewrite should be assumed present.

## Next actions
1. Move Hugging Face cache configuration from job-level `env` to step-level `env` on the install, download and inference steps. Keep `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, and `HF_DATASETS_OFFLINE=1` only for inference after model downloads and hash checks finish.
2. Add/retain a regression test asserting the workflow contains exact pinned revisions, invokes the production Qwen adapter, disables network access for inference, and does not place `runner.temp` at job scope.
3. Commit and check that GitHub allocates a real Ubuntu runner. If accepted, inspect disk/RAM before downloads; let both exact model snapshots download; verify the large file SHA-256 values; then inspect every inference step/log. A pre-runner failure is not a model test.
4. If the runner gets as far as inference, fix only evidence-based API/model/resource failures. Do not replace Qwen output with mock or synthetic audio.
5. Once the real Qwen CPU smoke passes, preserve its WAV/metrics artifact and run a second chapter/voice-continuity sample. Then continue full recovery, packaging and target-PC performance gates.

## Truthful release status
**Still a developer prototype, not ready for user/customer testing.** FFmpeg's standalone native Windows technical audit has passed, but source/relinking obligations still require review. No genuine Qwen inference or listening QA has passed yet; no real model hashes have been run locally; no packaged Windows app, offline playback, USB relocation, complete 1,189-chapter output or system-performance benchmark has passed.

The user requires the README be updated before each "Continue working" request and an explicit pause note whenever work stops.

---

# Continuation handoff — 2026-11-25 (FFmpeg build bootstrap verification)

This checkpoint is recorded before the next engineering pass.

## Current starting point
- Public repository: https://github.com/glenerds/kjv-bible-audio-generator
- Application prototype version remains **0.4.12**.
- Current branch head at checkpoint start: `ea26bf21b7942aa5ecdf8a06a26195ab5354ae89`.
- Previous verified source-test baseline remains commit `dbc1683046378f5b45aafbd8a6c64db654d0b8fa`: Windows 11/Python 3.12 **136 passed**; Ubuntu/Python 3.13 **134 passed, 2 Windows-only skips**.
- Native Windows FFmpeg candidate audit passed at run `45623835915`: fixed archive digest, LGPLv3 output, non-GPL/nonfree configuration, `libmp3lame`, WAV→MP3→decode, license and all 35 notice-file hashes.
- Verified FFmpeg binary SHA-256: `3209f0ba6096189de3f850f65488bdb535177b7e46e0b16e902b3230c5ff74fe`; LGPL text SHA-256: `da7eabb7bafdf7d3ae5e9f223aa5bdc1eece45ac569dc21b3b037520b4464768`.
- Added `tools/ensure_ffmpeg.ps1`: it skips when the executable, build manifest, license and notice manifest are present; otherwise it runs the exact pinned audit and copies the verified executable/manifest into the project.
- `tools/build_windows.ps1` now calls that helper and then verifies FFmpeg before packaging. The builder also carries the expected archive, executable, license and source-commit hashes.
- The audit manifest now records archive provenance. Windows helper tests use a fake audit script and are designed to exercise both the acquire and skip paths without downloading FFmpeg or Qwen.

## CI status at this checkpoint
- Newer source-test runs for the bootstrap work were not yet a verified green result at the time of this handoff. Earlier attempts exposed missing FFmpeg manifest path variables; those were restored in the latest commit. Do not claim the latest branch is green until its exact Windows and Ubuntu logs confirm it.
- First inspect runs `45627490553` (head `ea26bf21...`) and `45627483034` (head `dbdc03a...`), then the newer run triggered by the latest commit. Check the two new Windows helper tests and PowerShell parsing step.

## Next work
1. Inspect the newest Windows/Ubuntu run and fix its first concrete failure; rerun both platforms.
2. Validate `ensure_ffmpeg.ps1` directly with the native Windows fixture, including both branches and cleanup/environment restoration.
3. Audit `build_windows.ps1` for remaining manual FFmpeg assumptions and make its manifest, compiled-in hashes and template consistent.
4. Add a safe Windows packaging preflight using small fixtures; do not represent it as a full model build.
5. Keep Qwen release blockers explicit: real 1.7B snapshots have not been downloaded/hashed in this runtime; no real VoiceDesign/Base inference, Genesis 1 listening, recurring speaker QA, real-model recovery, packaged-app launch/playback, USB relocation, performance or full-book production has passed.

## Release status
**Developer prototype only — not ready for user/customer testing.** FFmpeg's standalone technical candidate is verified but still requires human license/source-obligation review. Source-suite success is not packaged Windows acceptance.

The user requires a README checkpoint update before every “Continue working” request and an explicit pause message whenever work stops. This README is the recovery point.

---

# Continuation handoff — 2026-11-25 (0.4.12, FFmpeg technical audit passed)

This is the current recovery point. Earlier handoffs remain below as historical notes.

## Current verified state
- Public source repository: https://github.com/glenerds/kjv-bible-audio-generator
- Current prototype version: **0.4.12**.
- Current tested source commit: `dbc1683046378f5b45aafbd8a6c64db654d0b8fa`.
- GitHub Actions source-test run `45623891120` completed successfully:
  - Windows 11 / Python 3.12: **136 passed** in 104.29 seconds.
  - Ubuntu / Python 3.13: **134 passed, 2 skipped** (the two Windows-only NTFS tests).
  - The NTFS sparse-fixture allocation precheck passed.
  - Python compileall passed on both systems.
  - Four PowerShell scripts parsed on Windows: build, asset preparation, notice import and FFmpeg candidate audit.
- The Windows alternate-data-stream security regression tests pass; the importer enumerates named NTFS streams and rejects unsafe stream-bearing notice/license files.

## Qwen checkpoint integrity hardening
- Added `tools/qwen_asset_integrity.py`, a stdlib verifier that streams large files in 8 MiB chunks and checks full-file SHA-256, not only file length or Xet chunk identifiers.
- VoiceDesign revision `5ecdb67327fd37bb2e042aab12ff7391903235d3`, `model.safetensors` SHA-256: `391e8db219f292c515297cdceeb43e4eae67cdde35fa57e79a6a8a532fca0522`.
- Base revision `fd4b254389122332181a7c3db7f27e918eec64e3`, `model.safetensors` SHA-256: `38fc7fc51c5e776e840414b6fd443962e9411b9654888fd7913e4da643cb857c`.
- Both `speech_tokenizer/model.safetensors` files use SHA-256 `836b7b357f5ea43e889936a3709af68dfe3751881acefe4ecf0dbd30ba571258`.
- `prepare_assets.ps1` verifies weight contents after download and records the verified hashes and sizes in the asset manifest. `build_windows.ps1` re-hashes them and checks the manifest before packaging.
- These seven integrity tests use small fake files; the publisher hashes have been checked against the exact Hugging Face file pages, but the actual multi-gigabyte model snapshots have not yet been downloaded/hashed in this runtime. Do not claim real Qwen inference or local weight verification.

## Windows FFmpeg candidate — technical audit passed
- Exact BtbN/FFmpeg-Builds Windows x64 LGPL static archive: 179,056,458 bytes; archive SHA-256 `78d1f7728fef503b50a6de5866950a96d7e4db0fdb9dfaa47fc2c6691a48370b`.
- Source commit: `b9ebe81995b58cd4e3177a6c0ad5dc2392f7f7fd`.
- Native Windows audit run `45623835915` downloaded the archive and verified its size and hash, executed the contained `ffmpeg.exe`, confirmed `LGPL-3.0-or-later` via `-L`, rejected GPL/nonfree config flags, confirmed `--enable-version3` and `--enable-libmp3lame`, and completed a real WAV → MP3 encode → decode cycle.
- FFmpeg version line: `ffmpeg version N-129288-gc81e35cf2b-20261125 Copyright (c) 2000-2026 the FFmpeg developers`.
- Executable SHA-256: `3209f0ba6096189de3f850f65488bdb535177b7e46e0b16e902b3230c5ff74fe`.
- License text SHA-256: `da7eabb7bafdf7d3ae5e9f223aa5bdc1eece45ac569dc21b3b037520b4464768`.
- All 35 imported dependency notice files passed independent SHA-256/byte-size verification against their generated manifest. The downloaded Actions artifact was independently unpacked and its executable and license hashes were checked against the build manifest.
- Audit run/artifact: https://github.com/glenerds/kjv-bible-audio-generator/actions/runs/45623835915 — artifact `ffmpeg-candidate-audit-2026-11-25.zip`, artifact ID `15027341337`, 14-day retention.
- **Technical candidate only, not yet approved as an app dependency**. Human review of the full linked-library license set, source/relinking or source-offer obligations, and distribution terms remains required.

## Next engineering actions
1. Integrate the verified, digest-pinned FFmpeg acquisition and license/notice generation into the Windows build path so a developer does not have to manually assemble those files. The build must remain fail-closed if the release URL moves or the archive/binary hash changes.
2. Obtain the exact pinned Qwen snapshots in a suitable runtime, run the verifier on the actual model files, and test offline VoiceDesign and Base model loading.
3. Generate and listen to a real Genesis 1 chapter with all verses/cues; compare recurring speaker voices in a later chapter.
4. Test real-model pause/stop/retry/restart/crash recovery and a long sequential generation run.
5. Build the Windows one-folder package; verify first launch, offline playback, drive-letter/USB relocation and clean-machine dependency isolation.
6. Measure CPU/RAM/VRAM and generation speed; generate all 1,189 chapters and measure output storage; finish KJV-specific attribution and the software/model/codec/data license review.

## Release status
**Developer prototype only — not ready for user/customer testing.** Source CI and the standalone FFmpeg candidate tests are green, but no genuine Qwen inference/listening QA, actual model-snapshot verification, packaged Windows app, offline installation/playback, USB relocation, full-book run or performance benchmark has passed. Synthetic audio remains synthetic.

The user requires a README checkpoint update before every future “Continue working” / “keep working” request and an explicit pause message whenever work stops. Preserve this recovery note.

---
# Continuation handoff — 2026-11-25 (Windows hardening and CI follow-up)

This entry is written before the next engineering pass so another chat can resume from an explicit checkpoint.

## Current verified repository state
- Public source repository: https://github.com/glenerds/kjv-bible-audio-generator
- Project prototype version: **0.4.11**.
- Latest README section records the follow-up ADS assertion change: the Windows notice importer now emits/recognizes the precise "alternate data streams" diagnostic. Local Linux compileall passed and the suite reported **126 passed, 2 Windows-only skips** at that checkpoint.
- Earlier native Windows validation proved the NTFS sparse-fixture correction using `FSCTL_SET_ZERO_DATA`; the isolated Windows allocation probe passed for the 3.5 GB and 650 MB logical model fixtures with less than 1 MiB physical allocation.
- Earlier full Windows run reported **125 passed, 1 failed** because NTFS alternate data streams were not detected by ordinary directory enumeration. A Windows-specific `FindFirstStreamW` / `FindNextStreamW` enumeration fix was then added. The source-license ADS check and cross-platform raw path validator were added.
- The user-provided latest continuation notes identify commit `5465db6` as the follow-up assertion correction. Do not assume its newer hosted Windows run passed until the exact check-run and job logs are inspected.
- Hash verification for downloaded model-weight assets is being added/checked; do not claim the full model files have been downloaded or independently verified in the current runtime unless the latest code and real asset hashes are inspected.

## Work carried out in the most recent pass (from the current conversation handoff)
- Re-reviewed the Windows sparse-file/NTFS failure sequence and the corrective test fixture.
- Inspected the FFmpeg notice import security gap involving Windows alternate data streams.
- Added native Windows enumeration of named streams and rejection of named ADS in source, staged and installed notice/license files.
- Added/adjusted tests for Windows-only ADS behavior and platform-independent unsafe-name validation.
- Corrected the test assertion to accept the explicit "alternate data streams" diagnostic; this should not weaken the importer security rule.
- Investigated Windows CI runs, job steps, logs, packaging and model asset integrity. The last exact hosted-run outcome after the assertion correction still needs confirmation.

## Next engineering actions
1. Inspect current `main` SHA and recent commits. Confirm the actual contents of the ADS validation, source-license handling, path validator, model hash checks and CI workflow.
2. Inspect the newest GitHub Actions run for the current head; retrieve the full Windows and Ubuntu job steps/logs. Do not rely on a stale run, a partial UI state, or an inaccessible log endpoint.
3. Run the Windows-only ADS and sparse allocation probes first, then the full Windows/Python 3.12 suite and PowerShell AST/parser checks. If another failure occurs, reproduce and fix that exact failure; do not infer a pass from the Ubuntu job.
4. Run clean local compileall and the complete Linux test suite for every source/test change.
5. Audit model snapshot integrity checks against the exact pinned upstream file revisions and SHA-256 data; validate every large weight/shard/tokenizer file, not just configuration files or expected byte sizes.
6. Continue the Windows packaging/FFmpeg build validation, but do not approve the candidate until its actual executable hash, `-version`, `-L`, configuration, `libmp3lame`, licenses/notices and WAV→MP3→decode probe are verified.
7. Preserve the major release blockers: genuine offline Qwen VoiceDesign and Base inference; all 31 real Genesis 1 verse audio and listening QA; recurring speaker voice consistency; model-backed pause/stop/retry/crash recovery; native Windows packaged app launch/playback; USB relocation; CPU/RAM/VRAM/time benchmarks; full-book output/storage measurement; KJV-specific attribution and license review.

## Critical honesty/status rule
The passing Linux suite and isolated Windows NTFS fixture are not proof of a passing complete Windows product build. Mocks/synthetic MP3 are not Qwen inference. No Windows executable, offline playback, full real-Qwen chapter, USB portability, full 1,189-chapter run or customer-ready release may be claimed without the corresponding test evidence.

The user has asked that every future **"Continue working" / "keep working"** request be preceded by a README checkpoint update, and that any pause be explicitly stated. This README is the recovery point.

---

# Follow-up test assertion — 2026-11-24

The Windows ADS enumerator reports a precise error phrase ("alternate data streams"). The pre-existing invalid-source-path test's accepted error tokens were only "unsafe", "reserved" and "manifest.json", which would make the Windows ADS case fail on the assertion text even when the importer correctly rejects the source. Expanded the assertion's accepted diagnostic tokens to include "alternate data streams"; the separate Windows-only license ADS test still checks the exact phrase. No change to product behavior.

Local Linux compileall PASS; 126 passed, 2 Windows-only skips. New hosted Windows run is pending and remains authoritative for the NTFS API path.

---

# Native Windows ADS validation fix — 2026-11-24

The latest hosted Windows result for commit 1933c89 was **125 passed, 1 failed**. The failure was the FFmpeg notice import test for NOTICE.txt:stream: ordinary directory enumeration did not expose the NTFS alternate data stream, so the import succeeded when it should have failed closed. Ubuntu passed the same code.

Fix now committed in the source:
- Added Windows-only NTFS stream enumeration using FindFirstStreamW / FindNextStreamW / FindClose.
- Inspects the source notice directory (including directories), source license file, staged notice directory and staged license, and the final installed notice directory and license during verification.
- Allows only the ordinary unnamed ::$DATA stream. Named streams are rejected with a clear validation error.
- Non-stream-capable file systems return known Windows unsupported/no-stream errors and keep compatibility; unexpected enumeration errors fail closed.
- Adjusted the source-name test so raw DOS-reserved/trailing-dot strings are validated platform-independently, but not created as real Windows filenames (Win32 normalizes or reserves those names before Python can create them).
- Added a Windows-only source-license ADS regression test and a cross-platform raw validator regression.

Local verification after fix: compileall PASS; **126 passed, 2 skipped** (the Windows-only sparse and ADS probes are skipped on Linux). The new native Windows Actions result is pending.

---

# Continuation update — 2026-11-24 (pre-work: repair native Windows path validation)

## Verified starting state
- Package version remains 0.4.11. Latest code commit: `1933c8910533df6dc937f2c0c1976769fb816fb1`.
- The focused NTFS allocation test passed on the hosted Windows/Python 3.12 runner after the test fixture added `FSCTL_SET_ZERO_DATA`.
- The same hosted Windows full suite executed to completion: **125 passed, 1 failed** in 134.73 seconds. This is now an actual test result, unlike the previous missing-log failures.
- The single failure is `tests/test_asset_preparation.py::test_ffmpeg_notice_import_rejects_windows_unsafe_and_reserved_source_paths`: an input source filename `NOTICE.txt:stream` was accepted by the FFmpeg notice importer on Windows, although a colon denotes an alternate data stream separator there. The full Windows suite therefore stops before the PowerShell parser check.
- The matching hosted Ubuntu job passed its full suite. The local Linux full suite passed 125 tests with the Windows-only sparse-file diagnostic skipped.

## Work planned next
1. Inspect the exact failing security test and `tools/ffmpeg_notices.py` source-path validation.
2. Fix Windows alternate-data-stream path rejection without weakening Linux checks or rejecting legitimate relative notice paths.
3. Add a narrowly scoped regression test for Windows drive/ADS syntax, then rerun local compileall/full suite.
4. Push the smallest change and rerun the Windows full test suite and PowerShell AST parse; do not treat the existing 125/1 result as a pass.
5. Preserve the remaining release gates: Qwen inference, full model integrity, production FFmpeg licensing, Windows app build/playback, USB relocation and hardware benchmarks.

---

# Windows sparse-file fix — 2026-11-24 (FSCTL_SET_ZERO_DATA)

The isolated Windows allocation probe produced the exact reason the earlier FSCTL_SET_SPARSE-only fixture still failed: the 3.5 GB logical sparse file was marked sparse, but `GetCompressedFileSizeW` still measured 147,324,928 bytes allocated.

The fixture now:
1. Marks the NTFS test file sparse with `FSCTL_SET_SPARSE`.
2. Extends its logical EOF to the desired model-weight size.
3. Calls `FSCTL_SET_ZERO_DATA` with a `FILE_ZERO_DATA_INFORMATION` range of `[0, size)` to ask NTFS to deallocate the zeroed sparse range.
4. The existing Windows-only allocation test requires the sparse attribute, the correct logical size, and physical allocation below 1 MiB for both the 3.5 GB and 650 MB fixtures.

Microsoft documents that ordinary zero writes can allocate clusters in sparse files; `FSCTL_SET_ZERO_DATA` is the operation that can deallocate sparse zero ranges. The exact Windows hosted result is pending. Linux full-suite regression remains 125 passed, with the Windows-only probe skipped.

---

# Windows sparse-file diagnosis — 2026-11-24 (pre-fix engineering note)

The dedicated Windows allocation probe at commit `86149ded45c23eaff32abaa6629b1a8926d7b820` ran on GitHub's Windows/Python 3.12 runner and returned a concrete result:

- The fixture successfully sets the NTFS sparse-file attribute.
- After creating a logical 3,500,000,000-byte fake model file, `GetCompressedFileSizeW` reported **147,324,928 allocated bytes**. The fixture's 1 MiB allocation budget therefore failed.
- The focused diagnostic ran as its own CI step and correctly skipped the full Windows test suite after failing. Ubuntu passed the complete suite.
- This demonstrates that setting `FSCTL_SET_SPARSE` before `Path.truncate()` is not sufficient: extending/zeroing a sparse file through ordinary file writes can still allocate disk space.

## Next change to validate

Use Windows `FSCTL_SET_ZERO_DATA` after setting the EOF on the sparse placeholder. The Windows API accepts a `FILE_ZERO_DATA_INFORMATION` range and may deallocate zeroed NTFS clusters in sparse files. Keep the file's logical length unchanged, then verify allocated bytes via `GetCompressedFileSizeW`. Run the focused check first, then the full suite and PowerShell parse only if that diagnostic passes.

No production application code is changed by this fixture-only work. Genuine Qwen inference, full Windows packaging/playback, approved FFmpeg, USB portability and real performance remain unverified.

---

# Windows CI diagnostic update — 2026-11-24 (verify NTFS sparse fixture allocation)

Two hosted Windows executions of the sparse-fixture patch were marked failed by GitHub, but the job metadata left the pytest step in an impossible "in_progress" state and the job-log storage endpoint returned a missing-log error. Both runs had installed dependencies and passed compileall. Ubuntu passed 125 tests. Because we cannot inspect the lost Windows logs, we must not assert that the fixture fix is correct or claim a Windows test result.

A direct Windows regression/diagnostic was added:
- After creating the fake 3.5 GB and 650 MB Qwen weight files, it checks the Windows sparse-file attribute and calls GetCompressedFileSizeW.
- It asserts logical file size is correct and physical allocation remains below 1 MiB.
- The Windows Actions workflow runs this focused test in its own step before the full suite, so a sparse-fixture failure will be isolated and visible.
- On Linux the test is explicitly skipped; it does not alter or reduce the 125-test software coverage.

Latest local checks after adding the diagnostic:
- `python -m compileall -q src tests tools` — pending in this commit.
- Full Linux suite — pending in this commit.
- Latest previously verified full Linux run — 125 passed.
- Windows/NTFS allocation and full suite — pending.

---

# Continuation update — 2026-11-24 (pre-work: verify latest Windows run and resume engineering)

This note is written before the next engineering actions, as requested.

## Starting state
- Package version: 0.4.11.
- Latest source commit: 9fe98ff92d494a9e38f63060ca637e69db4241de.
- Canonical 0.4.10 archive comparison: all 72 product files other than the intentionally updated README match the public Git tree; three AI-review documents are extra repository files.
- Latest local clean-extraction verification after the 0.4.11 test changes: compileall passed and 125 tests passed.
- Latest hosted Ubuntu run at commit 9fe98ff: 125 tests passed.
- Native Windows failure was traced to test-fixture disk exhaustion: Path.truncate() allocated the 3.5 GB and 650 MB fake Qwen model files on NTFS, unlike the sparse Linux filesystem. The fixture now calls FSCTL_SET_SPARSE before extending the fake files.
- New hosted run ID 45533143315 is for that sparse-file fix. The last checked state had Ubuntu passed and Windows in dependency installation; no Windows pass has yet been claimed.

## Planned work
1. Verify the live commit, workflow run and all latest Windows/Ubuntu job steps.
2. Retrieve Windows test output and run the PowerShell parser step once available; distinguish a real source/test failure from runner setup.
3. If the sparse fixture passes, retain the change and update the recorded Windows result. If it fails, diagnose the exact exception and add the smallest regression fix.
4. Re-run local compileall and the full Linux suite when source code changes.
5. Continue the Windows build, FFmpeg and model-asset audit only after the active CI result is clear; preserve all unpassed product-release gates.

No genuine Qwen inference, finished Windows desktop application, customer FFmpeg bundle, offline playback, USB relocation, full Bible run or hardware performance benchmark is considered passed.

---

# Native Windows CI follow-up — 2026-11-24 (sparse model test fixtures)

The 0.4.11 native Windows / Python 3.12 CI job successfully installed FFmpeg and CPU PyTorch, installed the dev extra, and passed compileall. The full test run then exhausted the hosted runner's system disk. The error occurred in pytest fixture setup (WinError 112) because the Qwen adapter tests create fake 3.5 GB and 650 MB weight placeholders using Path.truncate(). On Linux the fixture files are sparse; on Windows, the same truncate operation reserved actual disk blocks.

Fix committed in the test fixture:
- Added _truncate_sparse_file(); on Windows it calls FSCTL_SET_SPARSE through DeviceIoControl before extending the file, with a hard failure if marking the file sparse is unsupported.
- On non-Windows systems it retains the normal truncate behavior.
- The fake weights remain structurally large for model preflight tests, without consuming several gigabytes on NTFS.

Local revalidation in the clean 0.4.10 archive extraction, with the 0.4.11 source changes applied:
- python -m compileall -q src tests tools — PASS.
- PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 xvfb-run -a env PYTHONPATH=src pytest -q — 125 passed in 27.55 seconds.
- The previous hosted Ubuntu run passed all 125 tests after explicit FFmpeg and CPU PyTorch setup.
- New native Windows run is triggered by this commit. Await its test and PowerShell parse results; no Windows suite pass is claimed yet.

This is a test-fixture correction. It does not claim that the Windows application package, Qwen inference, or production FFmpeg bundle has passed acceptance.

---

# CI follow-up — 2026-11-24 (FFmpeg test prerequisite)

The corrected 0.4.11 CI run installed CPU PyTorch successfully. The Ubuntu runner compiled the source and reached the full test suite: **110 passed, 12 failed, 2 skipped**. The failures all trace to the test host lacking the `ffmpeg` executable; the audio integration tests explicitly require it, and some worker tests fail when the encoder cannot be launched. No Qwen inference was performed.

The workflow now installs FFmpeg strictly as a **CI test dependency**:
- Windows runner: Chocolatey installs FFmpeg and verifies `ffmpeg -version`.
- Ubuntu runner: apt installs `ffmpeg` alongside Xvfb.
- A regression test asserts both OS provisioning steps remain in the workflow.

This does **not** approve the Chocolatey/distro FFmpeg binaries for inclusion in the customer's app. The production bundle still requires a separately pinned Windows LGPL build, binary/source/license notice evidence, `libmp3lame` confirmation and a WAV→MP3→decode probe.

The second-run Windows job is still completing the CPU PyTorch installation at the time of this update. Recheck both jobs after this workflow change.

---

# Engineering log — 2026-11-24 (0.4.11: cross-platform CI and missing test dependency)

The user asked me to continue direct engineering. This entry records what was verified and fixed in this pass.

## Canonical source reconciliation

- Canonical archive: `KJV_Audio_Generator_Developer_Source_0_4_10_2026-11-24.zip`, 171,950 bytes, SHA-256 `4c9dffa08d75e8ee2efb60f9fa561311d3501f515dbf650e233f15ebd2cc07f9`.
- ZIP integrity check passed; it contains 73 files.
- Compared Git object hashes for every archive path with the public repository tree: **72/72 non-README archive files match exactly**. The README is intentionally different because it contains the newly added continuation notes. The public repository has three extra AI-review instruction files. No archive product file is missing or silently substituted.
- Fresh extraction to `/mnt/data/kjv-generator-verification-pass-20261124`; Python 3.13.5 Linux x86_64; compileall passed; full suite **123 passed** before new changes.

## CI discovery and defect

- Added cross-platform GitHub Actions checks for native Windows/Python 3.12 and Ubuntu 24.04/Python 3.13. First real hosted run allocated both runners, installed dependencies and compiled the project.
- Both test jobs then failed during collection for the same concrete reason: `tests/test_qwen_adapter.py` imports `torch`, but `torch` was missing from the declared `dev` extra. This was not a Qwen inference failure; no test case had started.
- The existing Windows builder already pins PyTorch 2.10.0 for CPU or CUDA. Added `torch==2.10.0` to the `dev` optional dependencies so a developer test install is complete.
- Updated CI to preinstall the official CPU wheel from the PyTorch CPU index before installing `.[dev]`, avoiding an unnecessary CUDA runtime in the test jobs.
- Bumped package version to **0.4.11** and added a regression test that keeps the test dependency declaration explicit.

## Local verification after the fix

- `python -m compileall -q src tests tools` — PASS.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 xvfb-run -a env PYTHONPATH=src pytest -q` — **124 passed** in 29.16 seconds.
- Confirmed PEP 440 accepts the CPU build label `2.10.0+cpu` for the declared `torch==2.10.0` constraint.
- The updated cross-platform workflow is being rerun by the new commit. Do not report native Windows or GitHub-hosted results as passed until those checks finish successfully.

## Still not verified

No genuine Qwen inference, no full VoiceDesign/Base model download, no audio listening check, no real FFmpeg Windows binary or encoder test, no complete PyInstaller build, no Windows offline launch/playback, no USB relocation, no CPU-only model-generation benchmark, and no full 1,189-chapter output run. The Linux synthetic Genesis fixture remains synthetic and cannot serve as evidence of Qwen speech.

---

# Continuation log — 2026-11-24 (pre-work update: repository reconciliation and clean test rerun)

This update is being committed **before** engineering, as required by the user's continuation instruction. No application source or test code has been changed in this work pass yet.

## Starting state verified from the public repository

- Repository: `https://github.com/glenerds/kjv-bible-audio-generator`, default branch `main`.
- Published developer baseline: **0.4.10**.
- Latest previously documented source-tree counts: 87 repository entries, including 18 files under `src/kjv_audio_generator/` and 10 test files.
- Prior 0.4.10 verification record: 123 full-suite tests passed, 45 focused regressions passed, compileall passed, and a 73-file source archive passed ZIP integrity, clean extraction, compileall and the 123-test suite.
- These are historical results until this work pass reruns them from the exact current public snapshot.
- The latest README handoff says the product remains a developer prototype; there is no verified genuine Qwen speech run or native Windows acceptance pass.
- Current README blob before this pre-work update: `90bc7b351ddcde32463873ecd2d968b1bddcaad8`.

## Intended work in this pass

1. Retrieve the canonical 0.4.10 developer ZIP from the saved project file and verify its exact SHA-256 and ZIP integrity.
2. Compare its tracked project paths and file contents against the current public GitHub tree, distinguishing intentionally added public-repository review material from product source.
3. Create a clean working extraction from the canonical ZIP and independently rerun compileall and the full automated test suite, recording actual environment and results.
4. Correct any confirmed public-repository/source-archive drift. Do not change application behavior merely to make counts match.
5. Inspect the existing build/test automation and determine whether a native Windows Actions run can be executed; report only work that actually receives a runner and executes.
6. Record precise findings in the README, resume guide and development status. Keep genuine Qwen inference, Windows packaging/playback, USB portability, real-world performance and full-Bible production explicitly marked unverified until actually exercised.

**Safety of claims:** mocks and synthetic Genesis audio are not genuine Qwen inference. A missing Actions runner is not a code test. Linux results are not Windows acceptance. Do not ask the user to test until genuine Qwen audio and native Windows acceptance gates pass.

---

# Continuation handoff — 2026-11-25 (direct engineering resumed)

The user has asked to return to having ChatGPT perform the engineering and testing directly, rather than relying on external AI reviewers. This handoff is recorded before further code engineering so the project state can be recovered in a new chat.

## What has been done so far

- The separate public GitHub repository `https://github.com/glenerds/kjv-bible-audio-generator` was created by the user. It is separate from the original private `glenerds/glenerds-apps` backup repository, so unrelated projects were not made public.
- The public repository was verified as public and initially empty. The 0.4.10 project source, application package, test files, Windows tools, documentation and AI-review instructions were then published.
- The public repository tree was checked: 87 entries total, including 18 files under `src/kjv_audio_generator/` and 10 test files. The README, source directory, test directory, AI review start page and review prompt were fetched successfully through GitHub and verified accessible.
- The AI review prompt was corrected to use the new public repository links, not the old private repository paths.
- The project was previously at developer-prototype version **0.4.10**. The recorded baseline is **123 automated tests passed**, with 45 focused regressions passed, compileall passing, and clean source-archive extraction passing.
- The user decided to stop coordinating external AI reviews and have ChatGPT continue engineering and testing directly.

## Current verified starting state

- Repository: `glenerds/kjv-bible-audio-generator`
- Default branch: `main`
- Version baseline: `0.4.10`
- The public source has been published and is accessible, but the actual product remains a developer prototype, not a customer-ready Windows application.
- The documented full-suite baseline is 123 passing tests. This must be independently rerun against the current public source before being reported as the current result.
- Earlier GitHub Actions attempts failed before runner allocation; no hosted test steps executed. Do not count those attempts as passing or failing code tests.

## Remaining release blockers — do not claim these passed

- Genuine Qwen model installation/loading and real Genesis 1 speech generation.
- Listening validation and recurring-character voice consistency across separate chapters.
- Native Windows build, startup, MP3 playback and offline launch.
- Bundled Windows FFmpeg binary, MP3 encoder probe, licensing and notice verification.
- USB relocation and drive-letter-change behavior.
- Real-model interruption/restart recovery and extended generation.
- CPU/RAM/VRAM and generation-speed benchmarks.
- Full 1,189-chapter production and measured final MP3 collection size.
- Complete KJV dialogue/speaker attribution and software/model/codec/data licensing review.

The prior development host did not have the `qwen_tts` runtime or model weights, could not resolve Hugging Face, and had no native Windows/PowerShell/Wine environment. Do not substitute synthetic audio for real Qwen inference or imply that hosted tests ran when no runner was allocated.

## Work plan for the next engineering passes

1. Reconcile the published public repository against the canonical 0.4.10 developer source archive; check that all expected package files, tests, Windows scripts, model-preparation code and project records are present.
2. Independently rerun the full test suite from the public repository snapshot and from a fresh source archive extraction. Record exact commands, versions, environment and output.
3. Audit Windows asset preparation, model-weight integrity verification, dependency pinning, packaging scripts, FFmpeg binary selection and license-notice handling.
4. Audit the Qwen backend and adapter against verifiable upstream APIs and model requirements. Distinguish static/API review from genuine inference.
5. Fix concrete offline-verifiable defects in small, versioned changes with regression tests.
6. Update this README, `docs/RESUME_HERE.md` and `docs/DEVELOPMENT_STATUS.md` after meaningful engineering work.
7. Do not ask the user to install or test the prototype until genuine Qwen speech and native Windows acceptance tests have passed.

## User's continuing instructions

- Keep work in the current response; do not imply background or asynchronous work.
- When pausing, explicitly tell the user that work is paused.
- On every future "keep working" instruction, update the README first, recording the starting state and intended work, before engineering changes.
- The README and resume guide are the recovery record if the conversation is disconnected or moved to a new chat.

---

> **Public source snapshot:** This repository publishes the KJV Bible Audio Generator developer prototype 0.4.10 for independent inspection. It is not a customer-ready Windows application.
>
> **Independent AI review:** Start with [AI_REVIEW_START_HERE.md](AI_REVIEW_START_HERE.md) and follow [AI_REVIEW_PROMPT.md](AI_REVIEW_PROMPT.md).
>
> **Repository:** https://github.com/glenerds/kjv-bible-audio-generator

---

# KJV Bible Audio Generator — developer prototype 0.4.11

**Developer prototype only. Not a customer-ready Windows application. Do not install or test this as the finished product.** Separate from the legacy KJV Bible Reader / USB Builder.

## End-product requirements

A self-contained Windows desktop app imports or accepts KJV Bible text, lets the user review recurring character profiles and speech assignments, and generates all 66 books in canonical order: 1,189 named chapter MP3s, with verse/sub-verse cues and stable character voice identities. It must support durable queue progress, pause/resume, safe stop, bounded retries, restart recovery and selective regeneration after voice changes. The customer must not separately install Python, packages, models, Qwen, FFmpeg or WSL. A dedicated GPU cannot be a requirement; CPU speed and peak memory must be measured. The target for the final chapter-MP3 collection is below 16 GB.

## Continuation log — 2026-11-24 (README updated before this work session)

The user explicitly requires this README to be updated **before any further engineering whenever they say “keep working.”** This entry is that pre-work update. Do not skip this step on future continuation turns.

### Verified starting point
- Active source: `/mnt/data/kjv-audio-generator-work/`, package version 0.4.9.
- Last reported baseline: **116 automated tests passed** from the source tree and from a fresh 72-file source-archive extraction; compileall and ZIP integrity passed.
- Version 0.4.9 routes the remaining JSON outputs and finalized MP3 copies through atomic replacement. The installed wheel verifies 66 books, 1,189 chapters and 31,102 verse entries.
- Developer ZIP and wheel are backed up in the ChatGPT Library and were also linked in the prior handoff. GitHub project docs now point to 0.4.9 / 116 tests.
- No genuine Qwen Genesis 1 audio, native Windows app, approved Windows FFmpeg executable, offline Windows playback, USB test, full-Bible run or CPU/RAM benchmark has passed. Do not ask the user to test the prototype.

### Work completed in this continuation
1. Audited application, Qwen backend and FFmpeg notice persistence paths. Found direct reference-WAV writes, a fixed `.pt.tmp` Qwen prompt path and destructive FFmpeg notice replacement; fixed all three.
2. Added `atomic_output_path()` with unique same-directory staging, final-extension preservation, non-empty output validation, fsync and atomic replacement. Applied it to SoundFile WAVs and torch prompt assets.
3. Changed FFmpeg notice import to stage/copy/hash/verify the entire package and license before swapping them. Added rollback if a commit step fails.
4. Focused regression suite: 45 passed. Full suite: 123 passed. Compileall: passed.
5. Version 0.4.10 wheel installed in an isolated target; KJV structure 66 / 1,189 / 31,102 verified. Fresh 73-file source ZIP extraction, integrity, compileall and 123 tests passed.
6. Real Qwen remains blocked: `qwen_tts` is not installed and Hugging Face DNS resolution fails. No actual model/audio or Windows toolchain is present. Both installed-wheel preflights correctly fail closed.
7. README, resume guide, development status, checkpoint, downloads/archive notes and GitHub pointers updated to the verified 0.4.10 state.

## Implemented through 0.4.11

### 0.4.11 — complete developer test dependencies and cross-platform CI

- Added the explicitly required PyTorch 2.10.0 runtime to the `dev` optional dependency set. The Qwen adapter's tests import torch and previously failed during test collection on a clean developer install.
- Added public GitHub Actions jobs for native Windows / Python 3.12 and Ubuntu / Python 3.13. The Windows job compiles and runs the complete test suite and parses the PowerShell build scripts; the Linux job runs the full GUI-enabled suite under Xvfb.
- CI installs the matching CPU PyTorch wheel from the official PyTorch CPU index before the project extras, avoiding CUDA packages in test-only runners.
- Bumped package metadata to 0.4.11 and added a regression test that prevents the dev dependency from silently losing torch.

### 0.4.10 — atomic files for Qwen assets and transactional FFmpeg notice imports
- Added `atomic_output_path()`: a unique same-directory staging path that preserves the target extension (for example `.tmp.wav`), checks that the writer produced non-empty output, fsyncs the completed file and commits it with `os.replace()`.
- Qwen-generated reference WAVs now use this path, so SoundFile still recognizes the WAV extension and a failed/incomplete voice-design write cannot truncate a previous reference recording.
- Qwen `.pt` clone-prompt tensors now use unique extension-preserving staging plus fsync/atomic replacement instead of the shared fixed `.pt.tmp` path. This prevents concurrent writers from colliding and leaves prior prompt bytes intact on save failure.
- `copy_file_atomic()` now uses the same output-path helper, validates its source is a regular file and fsyncs before replacement.
- FFmpeg license-notice import now copies the new `doc/` tree and `LICENSE.txt` into a staging area, hashes and verifies the entire staged notice set first, then swaps the notice directory and license file with rollback backups. A failed staging copy or mid-commit failure restores the prior bundle; successful re-import removes stale files from the old set.
- Added regression cases for atomic third-party output, extension retention, empty/failed writers, unique staging names, FFmpeg staging failure, FFmpeg pair-commit rollback and successful full-set replacement.

### 0.4.9 — complete the atomic output path
- The final MP3 copy now uses a unique same-directory staging file, flush/fsync and `os.replace()`; failed replacement keeps the previous chapter MP3 intact.
- Chapter cue JSON sidecars, first-run bundled speaker-seed review JSON and backend diagnostic JSON now use the common atomic writer too. A source scan found and removed all remaining direct JSON `write_text()` output paths.
- Added copy/replace regression tests; audio, attribution, GUI/CLI, and persistence tests were rerun.

### 0.4.8 — crash-safe JSON metadata persistence
- Added one shared JSON writer for GUI/CLI review reports, voice registries, attribution maps, Qwen prompt metadata and queue reports.
- Writes to a uniquely named temporary file in the destination directory, flushes and fsyncs it, then uses atomic replacement. A failed serialization, write, fsync or replacement leaves the previous destination intact and removes the temporary file.
- Replaced fixed `.tmp` names, avoiding collisions between simultaneous writers, and covered normal replacement, failed replacement cleanup and serialization failure with regression tests.

### 0.4.7 — GUI speaker import no longer overwrites reviewed work
- The desktop **Import Speaker Data (TSV)** action now loads the existing saved attribution map and uses the same `merge_seed_suggestions()` path as the CLI.
- Exact-text manual verse segments, custom/prepared voice profiles, user-authored ranges, previous review candidates and provenance are retained.
- Same-source re-import replaces only that source's prior suggestions and does not duplicate import history.
- Conflicting suggestions are queued for review and continue to use the neutral unknown-speaker voice until a person resolves them.
- A Tk GUI regression test exercises the real import-button handler twice, including retained manual edits and an overlap conflict.

### 0.4.6 — non-destructive speaker-seed import
- The explicit `--speaker-projections` import now merges suggestions into saved attribution rather than replacing the assignment file.
- Existing exact-text manual verse segments, user-created voice profiles, prior review candidates and untracked user ranges are retained.
- Each suggestion source is tracked separately: re-importing the same source replaces only its previous machine-generated ranges, avoids duplicate source-history entries and preserves edits made since the last import.
- Overlapping speakers from different sources are explicitly queued for review; ambiguous overlaps remain on the neutral unknown-speaker voice until adjudicated.
- Source TSV and details-file SHA-256 values are recorded in import provenance. Regression tests cover preserving a custom profile and manual segment, overlap review and idempotent repeat import.

### Import and structure
- Imports USFM/SFM, ZIP, JSON, reference-per-line text and numbered book/chapter text.
- Validates canonical 66-book structure, 1,189 chapters, 31,102 verses, and each chapter's exact reference verse count. This checks structure/versification, not translation wording.
- A scale test imports 31,102 synthetic verse-reference lines through the application parser. The complete Genesis 1 test fixture contains all 31 authentic KJV verses.

### Speakers and voice review
- Character voice editor: stable speaker IDs, names, aliases, Qwen voice design descriptions, reference scripts and optional external reference WAVs.
- Verse speaker editor supports multiple exact text segments per verse; save and synthesis both verify concatenation preserves source spaces and punctuation.
- Needs-review/manual-override queues and stale assignment checks.
- Thirteen book-labelled narrator aliases normalize to one Bible Narrator; `Jesus (child)` maps to Jesus; ambiguous composite speaker labels remain unassigned for human review.
- MACULA/FCBH attribution is not KJV-specific and remains a provisional review seed. Dataset research found no complete, verified, openly redistributable KJV speaker map; see [Attribution Dataset Research](docs/ATTRIBUTION_DATASET_RESEARCH_2026-11-24.md). Full cast/quotation review is unfinished.

### Qwen character voices
- Pinned Qwen VoiceDesign → Base reusable profile workflow; persistent prompt assets and bounded in-memory cache.
- Voice profiles carry their own reference-audio metadata. External/missing WAVs cannot silently be replaced with another voice. Once a prompt is fully prepared and verified it remains reusable after the source WAV is removed or the project folder is moved.
- Only speaker profiles used by pending chapters are prepared.
- **0.4.2 fixed a critical Qwen 0.1.1 API mismatch:** ICL synthesis requires the reference transcript to build `ref_ids`. Saved prompts now retain `ref_text` and reconstruct the Qwen prompt-item attributes consumed by the upstream wrapper. Earlier four-field dict-only prompts lost the transcript and could fail during real synthesis. Old prompt assets are migrated safely from an available reference WAV; if that is unavailable, the app fails closed.

### Queue, regeneration and portability
- SQLite sequential chapter queue, atomic claims, pause/resume, safe-stop requeue, bounded retry and restart recovery.
- Completed MP3 and cue JSON have SHA-256 fingerprints. Resume verifies them, checks cue chapter/duration/timing, requeues missing/tampered/corrupt outputs, and migrates old hashless rows.
- Chapter generation fingerprints include the speaker/profile inputs, pinned backend/model revision, FFmpeg executable identity, encoder settings and audio pipeline. Changing Moses's voice or a verse assignment regenerates only affected chapters; unrelated outputs keep their hashes.
- Completed chapter paths are rebased to the current project root. A relocated copy of the completed project verifies existing hashes and does not regenerate everything.
- Complete projects skip Qwen model loading on restart.
- MP3 assembly, normalization, FFmpeg decode checks and verse/segment cue JSON.

### Windows preparation and FFmpeg license gate
- Pinned Qwen model snapshots and MACULA source; model folders/configuration/size and upstream Git blob hashes checked; Qwen asset manifest written UTF-8 without BOM.
- Windows builder targets 64-bit Python 3.12 with explicit Torch/Torchaudio CPU or CUDA 12.8 wheel selection.
- FFmpeg manifest must identify a matching executable SHA-256, version/build configuration, LGPL license/version, named license-text file and license SHA-256. `--enable-gpl` and `--enable-nonfree` are rejected; `libmp3lame` must be present and a WAV→MP3→decode probe must pass.
- Builder now accepts either LGPL-2.1-or-later or LGPL-3.0-or-later, and verifies the executable's `-L` output agrees with the manifest. LGPLv3 is needed by the current candidate; previous code incorrectly rejected it.
- **0.4.4 adds complete FFmpeg dependency-notice preservation:** `tools/import_ffmpeg_notices.ps1` imports the extracted package `doc/` tree and `LICENSE.txt`; `tools/ffmpeg_notices.py` writes a manifest with relative path, byte size and SHA-256 for every notice file. The Windows builder verifies the complete file set and every hash before PyInstaller runs, rejecting missing, altered, added/unlisted, unsafe-path or symlink entries.
- **0.4.5 hardens cross-platform path safety:** the importer and verifier reject Windows drive/UNC paths, alternate data streams (`:`), backslashes, traversal and noncanonical paths, reserved device names (including COM/LPT forms), trailing-dot/space names, case-insensitive path collisions and a source file that could overwrite the generated manifest.
- Symlink checks now cover the notice directory root, manifest, license file and every nested notice entry. The verifier validates the complete manifest path namespace before opening any listed file, then checks exact file set, size and SHA-256.
- Regression tests verify Windows-only path cases even on Linux, including alternate data streams, reserved names, case collisions, source import path rejection and symlinked entry points.

## Current FFmpeg candidate (not approved yet)

The BtbN GitHub release published on 2026-11-24 lists `ffmpeg-master-latest-win64-lgpl.zip` as a Windows x86_64 static LGPL build (179,049,798 bytes). GitHub release metadata reports the candidate archive SHA-256 as `3639382f80af8849c7e11b11f3f379992e2f1925fe95fcee262cbe242a005b84`. The BtbN build recipe at commit `b9ebe81995b58cd4e3177a6c0ad5dc2392f7f7fd` selects `variants/win64-lgpl.sh`; that imports `defaults-lgpl.sh` (`--enable-version3 --disable-debug`, license file `COPYING.LGPLv3`) and the enabled `scripts.d/50-libmp3lame.sh`, which adds `--enable-libmp3lame`. The static variant installer also packages FFmpeg's documentation directory.

This is an **LGPLv3 candidate**, not an approved app dependency. The archive download failed in this environment; its `ffmpeg.exe`, actual `-version`/configuration/`-L`, encoder list, embedded license files, dependent library notices and encode/decode probe remain unverified. The GitHub `latest` tag is mutable, so the release-asset digest must be checked before use. The actual FFmpeg source revision used by that binary has also not yet been extracted from the executable. See [FFmpeg build evidence notes](LICENSES/README_FFMPEG.md).

## Verified in this environment

Linux x86_64, Python 3.13.5, PyTorch 2.10 CPU-only, host FFmpeg 7.1.5, approx. 5.8 GB RAM and 3 CPU cores. No CUDA, Qwen runtime/weights, PowerShell/Wine, PyInstaller or bundled Windows FFmpeg; Hugging Face DNS resolution fails.

- `python -m compileall -q src tests tools` — PASS.
- 0.4.10 clean-source baseline: full suite **123 passed**.\n- 0.4.11 post-fix clean extraction: compileall PASS; full suite **124 passed** on Python 3.13.5 Linux x86_64. The new Windows and Linux hosted workflows are being rerun; their first attempt correctly exposed the missing torch dev dependency and is recorded above.
- Focused atomic-output / FFmpeg notice / Qwen adapter suite — **45 passed**, process exit 0.
- `python -m compileall -q src tests tools` — PASS.
- CLI entry-point tests: 17 passed; coverage for `src/kjv_audio_generator/__main__.py` is **96%**, including GUI launch, positive preflight/audio-smoke wiring, speaker-seed import and the standard queue path.
- Wheel `kjv_audio_generator-0.4.10-py3-none-any.whl` built and installed into an isolated target; 53,951 bytes; SHA-256 `bfe9aedd5605dd6fd859cfac4b3dfa191da45d13457188fdd55c70af1cfb0737`. Installed version 0.4.10 and KJV structure data verified as 66 books / 1,189 chapters / 31,102 verses.
- Installed wheel preflight remains fail-closed as intended: `--self-test` exit 2 for missing Qwen models/runtime/asset manifest/bundled FFmpeg; `--audio-smoke` exit 3 for the missing Base model.
- Developer ZIP `KJV_Audio_Generator_Developer_Source_0_4_10_2026-11-24.zip` contains 73 source/documentation files. ZIP CRC, fresh extraction, compileall and **123 tests** from the extracted directory pass. The exact ZIP digest and byte size are recorded in the adjacent `.sha256` sidecar. This remains source-only, not a customer app.
- GUI tests create the main window, character-profile manager and verse speaker reviewer and test profile/speech-assignment save/reload.
- Full Genesis 1 software path processes all 31 KJV test verses through parser, speaker segments, SQLite worker and MP3 assembly; decodable **synthetic** MP3 with 33 cues. Not Qwen audio.
- Qwen adapter uses fake-model tests, but its prompt-item contract was checked against upstream `qwen-tts==0.1.1` source. No real inference.
- Real installed preflight fails closed: self-test exit 2 because Qwen models/runtime, pinned asset manifest and bundled Windows FFmpeg are missing; audio-smoke exit 3 because the Base model is absent.
- The current runtime probe confirms `qwen_tts` is not installed and Hugging Face DNS fails with a temporary name-resolution error. PyTorch and SoundFile are installed; only host Linux FFmpeg 7.1.5 is available. No genuine Genesis 1 MP3, Windows EXE, offline Windows launch, Windows playback, USB relocation or 1,189-chapter real generation has passed.

## Remaining release gates

1. Obtain the exact LGPL Windows FFmpeg candidate or a better pinned build, verify its executable hash, license text/notices, source revision, configuration and `libmp3lame`, then pass real encode/decode probe on Windows.
2. On network-enabled native Windows 11 / 64-bit Python 3.12, download and verify both pinned Qwen model snapshots and run them offline.
3. Generate and listen to all 31 real Qwen Genesis 1 verses; validate pronunciation, speaker assignments, output and cue times.
4. Reuse a recurring character prompt in a later chapter and assess audible consistency.
5. Test real-model pause/stop/retry/crash recovery and long sequential generation.
6. Build one-folder Windows app; clean extraction, offline launch, real playback, portable paths and USB relocation.
7. Benchmark CPU speed/peak RAM; validate 1,189 MP3/cue files and final storage size.
8. Complete KJV-specific cast/quotation review and full software/model/FFmpeg/codec/data licensing review.

**Not ready for customer installation/testing.**

See [Resume Here](docs/RESUME_HERE.md), [Development Status](docs/DEVELOPMENT_STATUS.md), [0.4.10 Checkpoint](docs/PROGRESS_CHECKPOINT_2026-11-24_GENERATOR_PROTOTYPE_0_4_10.md), [0.4.9 Checkpoint](docs/PROGRESS_CHECKPOINT_2026-11-24_GENERATOR_PROTOTYPE_0_4_9.md), [0.4.8 Checkpoint](docs/PROGRESS_CHECKPOINT_2026-11-24_GENERATOR_PROTOTYPE_0_4_8.md), [0.4.6 Checkpoint](docs/PROGRESS_CHECKPOINT_2026-11-24_GENERATOR_PROTOTYPE_0_4_6.md), [0.4.5 Checkpoint](docs/PROGRESS_CHECKPOINT_2026-11-24_GENERATOR_PROTOTYPE_0_4_5.md), [Attribution Dataset Research](docs/ATTRIBUTION_DATASET_RESEARCH_2026-11-24.md), [Downloads](DOWNLOADS.md) and [Source Archive](SOURCE_ARCHIVE.md).
