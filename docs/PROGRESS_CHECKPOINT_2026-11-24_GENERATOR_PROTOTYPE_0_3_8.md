# Engineering Checkpoint — KJV Bible Audio Generator 0.3.8

Date: 2026-11-24. Separate from the legacy KJV Bible Reader / USB Builder.

## Target
Self-contained Windows app imports KJV and generates 1,189 canonical chapter MP3s with stable character voices and verse/sub-verse cues. Durable queue, pause/resume, safe stop, retry and restart recovery. No customer Python/models/FFmpeg installation and no dedicated GPU requirement. Do not request customer testing before real Qwen and native Windows acceptance pass.

## 0.3.8 fix
Found a multi-profile Qwen voice-reference metadata bug. `prepare_profiles()` iterates a complete Bible cast. The `prompt_work` entry previously stored profile, reference, prompt path and signature, but not the profile-specific external reference path. The prompt-writing loop then reused the final value from the outer loop when writing `reference_audio_path`. This could make multiple character prompt manifests claim the same external WAV, so a later portable restart with those WAVs removed would reject an otherwise good saved voice prompt.

Fixed by carrying `external_reference` inside each prompt-work tuple and writing that tuple's path to the prompt manifest.

Regression test uses external reference WAV A for Moses, an internally designed Narrator, external reference WAV B for Jesus; verifies manifests record A / null / B; removes both WAV sources; restarts the backend; confirms all 3 profiles are marked cached, no additional prompts are built, and each profile synthesizes through the fake Qwen adapter.

## Verification
Linux x86_64, Python 3.13.5, PyTorch 2.10 CPU-only, FFmpeg 7.1.5, 3 CPU cores, ~5.8 GB RAM. No CUDA, Qwen runtime/model weights, Windows toolchain or Windows FFmpeg. Hugging Face DNS unavailable.

- `python -m compileall -q src tests`: PASS.
- `xvfb-run -a env PYTHONPATH=src pytest -q`: **81 passed**.
- Previous 0.3.7 archive restored and independently retested: 80 passed before new 0.3.8 regression was added.
- Existing full 31,102-reference parsing test passes.
- Existing Genesis 1 31-verse synthetic MP3 pipeline passes with 33 cues.
- Qwen tests use FakeQwenModel, not the actual runtime/model.

## Unpassed release gates
- No Qwen runtime/weights on host and Hugging Face DNS cannot resolve; no genuine Genesis 1 recording or later-chapter audible voice comparison.
- No native Windows build, verified FFmpeg.exe, offline launch, Windows playback or USB relocation.
- No real-model interruption/restart/long-run, 1,189-chapter output, size/CPU benchmark.
- Full KJV cast attribution review and licensing review remain open.

## Exact resume point
Continue with Qwen adapter and voice-profile persistence review from 0.3.8; then run on network-enabled native Windows 11 / Python 3.12 with actual pinned Qwen weights and verified LGPL FFmpeg. Generate/listen to Genesis 1, test recurring voice reuse and queue recovery, then build/test the Windows app.
