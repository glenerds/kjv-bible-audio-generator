# Engineering Checkpoint — KJV Bible Audio Generator 0.3.6

Date: 2026-11-24. This is a separate application from the legacy KJV Bible Reader / USB Builder.

## User's acceptance target

Self-contained Windows app imports KJV and generates 1,189 chapter MP3s in canonical order with verse/sub-verse cues and stable recurring character voice identities. Persistent queue, pause/resume, safe stop, retry, restart recovery and output integrity. No customer Python/packages/models/FFmpeg/WSL installs or manual config; no dedicated GPU requirement. No user test before genuine Qwen and Windows release gates.

## 0.3.6 engineering changes

- Canonical narrator normalization: all 13 book-specific upstream labels (narrator-GEN, narrator-JHN, narrator-MAT, etc.) map to the one `narrator` profile.
- `Jesus (child)` maps to canonical `jesus` profile.
- Slash-composite labels (God/Jeremiah, God/Jesus, etc.) are assigned to `unknown_speaker` and flagged for human review; no fictional composite character profile is created.
- Tests added for all three policies.
- Removed a duplicated profile-exists check in speaker seed import after inspection.

## Previous implemented functionality retained

- Character voice profile manager and exact-text-preserving verse speaker segment editor.
- Stale segment detection against imported KJV at synthesis.
- SQLite completed MP3/cue SHA-256, additive schema migration, restart audit, same-size tampering detection and regeneration.
- Full 31-verse Genesis 1 synthetic integration path, 33 timing cues, decodable synthetic MP3.

## Verified here

Linux x86_64 / Python 3.13.5 / PyTorch 2.10+cpu / FFmpeg 7.1.5; 3 CPU cores / ~5.8 GB RAM. No CUDA, Qwen runtime/weights, PowerShell/Wine, PyInstaller or Windows FFmpeg. Hugging Face DNS does not resolve from this container.

- Compileall PASS.
- Xvfb pytest: **77 passed** (latest run after removing the redundant check).
- Genesis 1 pipeline test is synthetic, not Qwen speech.
- Qwen adapter tests use fake model objects.
- Real CLI preflight fails closed when models/runtime/Windows FFmpeg are missing.
- Native Windows EXE, offline launch, playback, USB and full Bible generation remain untested.

## Next exact actions

1. Build new 0.3.6 wheel and developer ZIP after code/document sync; fresh install/extraction and rerun tests.
2. Run model prep on network-enabled native Windows 11 / Python 3.12, verify offline model load and obtain verified LGPL Windows FFmpeg.
3. Generate/listen to authentic Genesis 1, test later-chapter character identity.
4. Run real Qwen queue recovery; Windows package/offline/playback/USB acceptance.
5. Measure CPU speed, peak RAM, 1,189 chapter output size/integrity; finish KJV attribution review and licensing.

Do not label developer archive or synthetic Genesis audio as the customer application or real Qwen output.
