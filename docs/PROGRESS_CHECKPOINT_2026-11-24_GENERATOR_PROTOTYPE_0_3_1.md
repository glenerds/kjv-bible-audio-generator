# Checkpoint — KJV Bible Audio Generator prototype 0.3.1

Date: 2026-11-24 (America/Indiana/Indianapolis)

## Assignment

Build a separate KJV audiobook generator. Import/paste a full Bible, preserve recurring character voice identities, render continuously in canonical order from Genesis 1 through Revelation 22, produce 1,189 individually named MP3 chapter files plus verse/segment cue metadata, and persist queue state with pause/resume, safe stop, retries and restart recovery. Finished Windows delivery must be self-contained; no customer Python/runtime/model/FFmpeg setup. Do not request customer testing before real Qwen + native Windows integration pass.

## 0.3.1 changes made in this session

1. **Qwen model preflight is now structural.** It requires the official model files: `config.json`, `model.safetensors`, root tokenizer config/vocabulary/merges/preprocessor, and nested `speech_tokenizer/config.json`, `speech_tokenizer/model.safetensors`, and `speech_tokenizer/preprocessor_config.json`. A non-empty directory is no longer accepted.
2. **Qwen runtime import is stricter.** The adapter verifies that `qwen_tts` exposes a callable `Qwen3TTSModel`, not merely that a Python module of that name imports.
3. **Reusable prompt persistence is safer.** Qwen prompt item lists are converted to the documented dictionary form (`ref_code`, `ref_spk_embedding`, `x_vector_only_mode`, `icl_mode`). This is saved as plain tensor/primitive data and loaded with `torch.load(..., weights_only=True)`. The adapter will fail clearly on PyTorch versions without this safe-loading option.
4. **Dependency target made reproducible.** `pyproject.toml` pins `qwen-tts==0.1.1` and `transformers==4.57.3`; the upstream qwen-tts project metadata also pins `accelerate==1.12.0`.
5. **Windows build collection expanded.** PyInstaller collects librosa, torchaudio, accelerate, einops, safetensors, sox and onnxruntime in addition to the Qwen package, Transformers, tokenizers, soundfile and torch. This still requires a real Windows build test; collection flags alone do not prove an executable works.
6. **Tests added.** A partial/non-empty model folder is rejected, a correctly laid-out fake model folder passes structure validation, and the fake Qwen contract verifies a dictionary-shaped prompt payload survives saved-profile reuse.
7. **Handoff files rewritten** to remove stale/contradictory 0.1/0.3.0 statements in the standalone generator docs.

## Verification performed

- Environment: Linux x86_64, Python 3.13.5, PyTorch 2.10.0+cpu, CUDA unavailable, `qwen_tts` absent, Transformers absent, host FFmpeg 7.1.5. No model weights or Windows `ffmpeg.exe` are staged.
- `python -m compileall -q src tests`: PASS.
- `xvfb-run -a env PYTHONPATH=src pytest -q`: **46 passed**.
- Tests use fakes and synthetic waveforms for Qwen/MP3 behavior; these do not prove real Qwen speech.
- Real Qwen self-test is still expected to fail closed (exit 2) because Qwen runtime/models/bundled Windows FFmpeg are absent.
- Real Qwen audio smoke is still expected to fail (exit 3) because the Base model is absent.

## Confirmed upstream API (source review only)

Official `QwenLM/Qwen3-TTS` source reviewed 2026-11-24:

- Upstream `qwen-tts` metadata version 0.1.1 pins Transformers 4.57.3 and Accelerate 1.12.0.
- `create_voice_clone_prompt()` returns a list of structured prompt objects.
- `generate_voice_clone()` accepts either the list or a prepared dictionary; the official wrapper converts prompt items into four arrays under `ref_code`, `ref_spk_embedding`, `x_vector_only_mode`, and `icl_mode`.
- Official 1.7B Base and VoiceDesign model folders include a nested `speech_tokenizer` subdirectory. The structural preflight now checks this.

Sources: `https://github.com/QwenLM/Qwen3-TTS/blob/main/qwen_tts/inference/qwen3_tts_model.py`, `https://github.com/QwenLM/Qwen3-TTS/blob/main/pyproject.toml`, `https://github.com/QwenLM/Qwen3-TTS/blob/main/README.md`, `https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign/tree/main`, `https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-Base/tree/main`.

## Outstanding release gates

- Stage and verify actual Qwen runtime and both official model folders, including nested speech-tokenizer assets.
- Generate real speech for all 31 authentic KJV Genesis 1 verses; inspect/listen to MP3 and cue file.
- Reuse same character profile in a later chapter and compare audible identity.
- Test real Qwen generation through pause/stop/retry/restart and multi-chapter long runs.
- Build in native Windows with PyInstaller; test fresh extraction, offline use, Windows audio playback, portable data paths and USB relocation.
- Benchmark CPU-only speed, peak RAM, startup and storage. Do not advertise a hardware floor until measured.
- Complete reviewed KJV speaker attribution and the polished per-verse review workflow.
- Finish third-party software/model/data/FFmpeg commercial redistribution and Amazon distribution review.

## Exact resume point

Continue from source version 0.3.1. First obtain a host with a supported Qwen runtime and complete official VoiceDesign/Base model folders. Run structural `--self-test`, then produce the first genuine Genesis 1 audio. Keep mock tests clearly labeled. Do not create a customer download or ask the user to test this developer archive.
