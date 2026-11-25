# Engineering Checkpoint — KJV Bible Audio Generator 0.4.2

Date: 2026-11-24. Separate from the legacy KJV Bible Reader / USB Builder.

## Target
Self-contained Windows app imports KJV text and generates 1,189 separate chapter MP3s in canonical order, with verse/sub-verse cues and recurring character voice identity. Durable pause/resume/safe-stop/retry/recovery queue. No customer installs or dedicated GPU requirement. No user testing before genuine Qwen and native Windows release gates pass.

## Critical Qwen 0.4.2 fix
Pinned upstream `qwen-tts==0.1.1` `generate_voice_clone()` has two paths:
- A prepared dictionary path sets prompt tensors/flags but does not derive `ref_texts_for_ids`, so ICL (`icl_mode=true`) lacks its required `ref_ids`.
- A list of prompt-item objects takes each object's `ref_text`, tokenizes it, and builds the `ref_ids` needed by ICL mode.

The older adapter persisted only `ref_code`, `ref_spk_embedding`, `x_vector_only_mode` and `icl_mode`. 0.4.2 now:
1. Saves all five fields including `ref_text` as safe tensors/primitives.
2. Reconstructs a Qwen-compatible prompt-item object for each saved item so its wrapper list path creates the reference text IDs.
3. Tags saved prompt metadata `prompt_schema_version=2`.
4. Detects old transcript-less prompts. With a retained/generated local WAV, it recreates the prompt; when a required external WAV is missing, it fails closed.
5. Bumps backend fingerprint so older generated chapter outputs are invalidated.

## Other implemented features
Stable character profiles, exact-text per-verse speaker splits, Needs-review filter, canonical narrator/Jesus aliases, ambiguous-speaker fallback, pending-voice-only preparation, per-chapter input hashes, selective regeneration, output SHA/cue SHA, SQLite migrations/concurrency, restart recovery, MP3 decode check and portable USB path rebasing.

## Verification
Linux x86_64, Python 3.13.5, Torch 2.10 CPU-only, FFmpeg 7.1.5, about 5.8 GB RAM and 3 CPU cores. No CUDA/Qwen runtime or models, PowerShell/Wine, PyInstaller or Windows FFmpeg; Hugging Face DNS unavailable.

- Compileall PASS.
- Xvfb pytest **92 passed**.
- Qwen prompt regression tests verify ICL transcript persists and is reconstructed; old prompt schema safely rebuilds or fails closed if required external WAV is missing.
- Genesis 1 end-to-end pipeline: all 31 fixture verses through parser/segments/queue/worker/synthetic MP3 with 33 cues. This is not Qwen audio.
- GUI windows and editor save/reload workflows tested.
- Wheel/ZIP must now be rebuilt from final 0.4.2 source and tested from clean target/extraction.

## Unpassed release gates
No real Qwen Genesis 1, no later-chapter audible voice comparison, no native Windows build/offline/playback/USB, no full 1,189 chapter run, no CPU/RAM benchmark, no complete speaker-cast review or commercial license clearance.

## Next work
Build and test 0.4.2 artifacts, then run actual Qwen on a network-enabled native Windows 11 / Python 3.12 environment with complete pinned model assets. Provide a verified LGPL FFmpeg binary/license/source manifest. Generate/listen to Genesis 1 and check same-character voice in another chapter; run real-model queue recovery and the Windows portability/CPU/output acceptance gates.
