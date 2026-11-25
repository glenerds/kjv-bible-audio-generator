# Distribution License and Notice Audit — 2026-11-25

## Scope and status

This is an engineering inventory of the actual Windows portable-package manifest produced by acceptance run **45679773296** (artifact `15055775380`, acceptance evidence `15053954142`). It is not legal advice or a legal clearance. The package contained 17,803 files / 14,261,536,648 bytes (13.282 GiB).

**Distribution approval remains blocked.** The repository has no root `LICENSE` file (the GitHub contents API returned 404), and `pyproject.toml` has no `project.license` metadata. Do not invent a license for the application source. The project owner must choose and document the terms for the project's own code and assets before granting downstream redistribution rights.

## Notices confirmed in the Windows package manifest

The run-28 `portable-package-manifest.json` includes the following items:

| Component | Notice evidence in package | Audit finding |
|---|---|---|
| Qwen3-TTS Python package and model family | `LICENSES/QWEN3_TTS_APACHE_2.0.txt`; pinned model files and integrity manifest | Apache-2.0 is declared at the exact official model revisions. The Qwen software license text is fetched from a pinned source commit and Git-blob checked. |
| Hugging Face Tokenizers 0.22.2 | No license text appeared under the frozen `tokenizers-0.22.2.dist-info` in run 28 | Corrected in source: added `LICENSES/TOKENIZERS_APACHE_2.0.txt` from immutable upstream commit `f383101a26663708484cac0727792aad74f78234`, with Git-blob SHA `261eeb9e9f8b2b4b0d119366dda99c6fd7d35c64`. `tools/prepare_assets.ps1` now downloads and verifies this file before packaging. A new regression test checks the pin and notice. Verify it appears in the next package manifest. |
| PyTorch 2.10.0+cu128 | `torch-2.10.0+cu128.dist-info/LICENSE` and `NOTICE` | Present in run-28 package manifest. |
| ONNX Runtime 1.32.0 | `onnxruntime/LICENSE` and `onnxruntime/ThirdPartyNotices.txt` | Present in run-28 package manifest. |
| FFmpeg | `LICENSES/FFMPEG_LICENSE.txt`, `FFMPEG_BUILD_MANIFEST.json`, `FFMPEG_DEPENDENCY_NOTICES/MANIFEST.json` and 35 imported upstream documentation files | Pinned static build reports LGPL-3.0-or-later, no `--enable-gpl` or `--enable-nonfree`, and `libmp3lame`. Native Windows technical acceptance and MP3 encode/decode passed. The imported 35 upstream `doc/` files are hash-checked, but I have not independently established that this is a complete third-party license-notice set for every enabled linked library. FFmpeg source, relinking and source-offer obligations need a separate human review. |
| Clear Bible / MACULA speaker seed | `data/speaker-attribution/LICENSE.md`, `ATTRIBUTION.md`, `LICENSES/GLYSSEN_MIT.txt`, both pinned TSV assets | The notice records CC BY 4.0 and the included FCBH/Glyssen MIT component. This is a provisional cross-translation seed, not authoritative KJV speaker attribution. |
| KJV verse-count metadata | `LICENSES/VERSE_COUNTS_LICENSE.txt` | Includes the Scrollmapper MIT attribution and license text. |
| Other bundled Python distributions | Various `.dist-info/licenses/` files, plus package-specific notices | Most scanned distributions had an included license/notice file. Tokenizers was the exception corrected above; ONNX Runtime keeps its notices in its package directory instead of its dist-info folder. Recheck the next frozen manifest after build changes. |

## Additional redistribution review required

1. **Project-owned code:** no root `LICENSE` and no `pyproject.toml` license metadata. The project owner must choose the intended license; do not assume a public GitHub repository grants a right to redistribute its code.
2. **CUDA/NVIDIA runtime:** the frozen Windows package contains NVIDIA CUDA DLLs under `_internal/torch/lib`, including `cublas64_12.dll`, `cublasLt64_12.dll`, `cudart64_12.dll`, `nvrtc64_120_0.dll`, `nvrtc-builtins64_128.dll`, `nvJitLink_120_0.dll` and cuDNN components. The package also includes PyTorch's `LICENSE` and `NOTICE`, but the separate NVIDIA component redistribution terms and any required notices/source obligations have not been independently audited. Obtain a component-level review before distribution.
3. **FFmpeg enabled libraries:** the fixed LGPL archive's build configuration enables numerous codec/filter libraries. The package's FFmpeg license and imported documentation are present and hash-checked, but this audit has not independently mapped every enabled library to its version, license, binary, notice and corresponding source.
4. **Model and data conditions:** the official Qwen model cards at the pinned revisions declare Apache-2.0. Retain all required notices. The speaker seed's attribution and MIT notices must remain with the data; do not claim that its speaker labels are KJV-verified.
5. **End-user materials:** ensure the final application includes a third-party notices screen or readable notice directory, and that the install/portable distribution points users to all required notices and source/relinking information where applicable.

## Exact evidence and upstream references

- Qwen Base pinned model card: https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-Base/tree/fd4b254389122332181a7c3db7f27e918eec64e3
- Qwen VoiceDesign pinned model card: https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign/tree/5ecdb67327fd37bb2e042aab12ff7391903235d3
- Qwen TTS software license source commit: https://github.com/QwenLM/Qwen3-TTS/tree/022e286b98fbec7e1e916cb940cdf532cd9f488e
- Tokenizers license source commit: https://github.com/huggingface/tokenizers/tree/f383101a26663708484cac0727792aad74f78234
- FFmpeg pinned build/source and technical audit: https://github.com/glenerds/kjv-bible-audio-generator/actions/runs/45623835915
- Windows package acceptance with full package manifest and both Whisper smoke transcripts: https://github.com/glenerds/kjv-bible-audio-generator/actions/runs/45679773296

## Next checks

- Confirm the newly pinned Tokenizers license appears in the next native Windows package artifact.
- Verify the next package's entire notice manifest and file hashes again after asset preparation completes.
- Resolve the project's own license with the owner.
- Obtain human review of the NVIDIA CUDA and FFmpeg linked-component redistribution obligations.
- Do not describe the app as commercially redistributable or legally cleared until these open items are resolved.
