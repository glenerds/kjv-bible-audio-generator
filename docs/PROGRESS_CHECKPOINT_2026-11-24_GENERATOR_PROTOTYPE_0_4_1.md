# Engineering Checkpoint — KJV Bible Audio Generator 0.4.1

Date: 2026-11-24. Separate from legacy KJV Bible Reader / USB Builder.

## Target
Self-contained Windows desktop app imports/pastes KJV, reviews character voices and speech segment assignments, generates all 1,189 chapter MP3s in canonical order with verse/sub-verse cues, retains recurring character voice identity and supports durable pause/resume/stop/retry/recovery. No customer installs/configuration and no dedicated GPU requirement. User testing only after real Qwen and native Windows gates pass.

## 0.4.1 engineering
- Per-chapter generation-input SHA-256 covers exact segment text/speaker IDs, every used profile fingerprint, stable backend family/version, pinned model snapshot manifest, language/device and audio pipeline settings.
- Voice description or verse speaker assignment changes regenerate only chapters whose speech uses that input; unaffected chapter outputs remain complete.
- Model asset manifest records pinned VoiceDesign/Base revisions, model config hashes, speech-tokenizer config hashes and weights sizes. Runtime verifies manifest against model folders; invalid/mismatched files or unapproved revisions fail closed.
- FFmpeg binary SHA-256, normalization and output-pipeline settings are included in generation identity.
- SQLite claim uses `BEGIN IMMEDIATE` to serialize competing app instances' chapter claims.
- On USB/drive relocation, completed MP3/cue paths rebase to the current project root before output SHA-256 verification; copied completed projects do not regenerate all chapters.
- Qwen-generated internal reference WAV prompts can be reused after a project folder move even if the profile JSON still stores the old absolute reference WAV path; verified prompt metadata and SHA are required.

## Verified
Linux x86_64, Python 3.13.5, PyTorch 2.10 CPU, FFmpeg 7.1.5, ~5.8 GB RAM and 3 CPU cores. No CUDA, Qwen runtime/weights, PowerShell/Wine, PyInstaller or Windows FFmpeg. Hugging Face DNS unavailable.

- Compileall PASS.
- Xvfb pytest **90 passed**.
- Wheel `kjv_audio_generator-0.4.1-py3-none-any.whl` built/installed in clean target, 50,112 bytes, SHA-256 `c3fa6dda08d7736d22bacde9f3ade6559d43a39991b45aae651b207b35fb9d2e`; installed package has 66 / 1,189 / 31,102 verse metadata.
- Developer ZIP passed CRC/integrity, clean extraction, compileall and **90 tests**.
- Installed preflight correctly fails closed: self-test exit 2 due to missing models/runtime/asset manifest/Windows FFmpeg; audio-smoke exit 3 due to missing Base model.
- Full 31-verse Genesis 1 fixture path uses synthetic audio with 33 cue segments, not Qwen.
- Full 31,102 reference-line import test proves parser/versification behavior, not translation wording.

## Still unpassed
- No authentic Genesis 1 Qwen MP3 or later-chapter audible character voice comparison.
- No native Windows build, offline launch, playback, USB device test or CPU performance benchmark.
- No 1,189 chapter audio collection / final size test.
- Full KJV-specific cast attribution and legal/commercial software/model/FFmpeg/codec/data review remain.

## Next work
Run pinned model prep and actual Qwen inference on network-enabled native Windows 11 / 64-bit Python 3.12; provide verified LGPL Windows FFmpeg. Generate/listen to Genesis 1, reuse a character profile in a later chapter, test actual-model recovery, then Windows one-folder/offline/playback/USB/CPU acceptance.
