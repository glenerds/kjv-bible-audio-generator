# Engineering Checkpoint — KJV Bible Audio Generator 0.4.6

Date: 2026-11-24  
Status: non-destructive speaker-attribution import fix, regression tests and clean build validation complete; not customer-ready.

## Why this update was required

After documenting the speaker-attribution rule that imported data must never overwrite reviewed human work, a code review found that the CLI's explicit `--speaker-projections` operation loaded the existing registry but replaced `metadata/speaker_assignments.json` with a new seed. That could discard saved verse segment overrides and review decisions. The default startup path preserved saved assignments; the separate import command did not.

## 0.4.6 implementation

- Added `merge_seed_suggestions()` so speaker projection imports are non-destructive.
- Existing exact-text manual `segment_overrides` are copied and preserved; the importer does not replace them.
- Existing custom `VoiceRegistry` profiles and their saved state are retained when importing additional speakers.
- Existing range assignments not owned by the incoming suggestion source are preserved.
- Tracks imported ranges per source in `provenance.suggestion_sources`. Re-importing a source replaces only its previously imported range set rather than duplicating it or deleting other sources' ranges.
- Stores SHA-256 fingerprints of the projection TSV and optional details TSV in provenance, plus de-duplicated import history.
- When ranges from different sources overlap with different speaker IDs, the affected verse is explicitly added to `seed_review`; the normal attribution logic uses `unknown_speaker` pending human review. Existing manual exact-segment overrides remain authoritative.
- Registry and assignment files use temporary-file plus replacement saves; the generated review JSON now uses the same same-directory atomic-replacement pattern. A failure-injection regression test confirms that a failed replace preserves the prior review file and removes the temporary file.
- Added CLI regression coverage proving manual assignment, custom prepared voice, pre-existing range, prior review item and provenance survive; a second identical import is idempotent and does not duplicate history or lose user work.
- Updated package version to 0.4.6.

## Verification

- Focused attribution/CLI regression suite: **17 passed**.
- Full source suite: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 xvfb-run -a env PYTHONPATH=src pytest -q` — **109 passed**.
- Compileall: PASS.
- CLI-focused GUI/CLI tests: **17 passed**; statement coverage for `src/kjv_audio_generator/__main__.py`: **96%**.
- Wheel 0.4.6 built and installed in an isolated target; installed version and bundled Bible metadata verified: 66 books / 1,189 chapters / 31,102 verses.
- Ran the installed wheel CLI (not merely the source-tree module) against an existing project; verified its manual segment, user-created prepared voice, user range and overlap review behavior.
- Genesis 1 integration remains synthetic audio (31 KJV fixture verses, 33 cues); no Qwen inference occurred.
- Native Windows app build and actual Windows FFmpeg binary verification remain blocked by this Linux host's missing PowerShell/Wine/PyInstaller and unavailable external DNS.

## Attribution data decision

No complete, verified, openly redistributable KJV word-level dialogue-speaker map has been identified. MACULA/FCBH is not KJV-specific and stays a provisional suggestion source. Logos/Lexham may be a commercial licensing lead, not a dataset to scrape or redistribute without permission. Bible Ontology is model-read/BSB, Jesus' Words is limited to Jesus in the Gospels and CC BY-NC, and Theographic provides KJV entity links but not dialogue speakers. See `ATTRIBUTION_DATASET_RESEARCH_2026-11-24.md`.

## Remaining release blockers

- Authentic Qwen Genesis 1 audio and later-chapter recurring-character listening comparison.
- Real-model pause/stop/retry/crash recovery and sustained multi-chapter generation.
- Pinned native Windows Qwen model preparation/offline load.
- Actual approved Windows LGPL FFmpeg executable, source revision, full license/dependency notices, `-version`/`-buildconf`/`-L`, MP3 encoder and WAV→MP3→decode probe.
- Native Windows one-folder build, clean extraction, offline launch, playback and USB relocation.
- CPU/RAM benchmark, all 1,189 chapter MP3/cue validation and final audio storage size.
- KJV cast/quotation adjudication and full licensing review.

**Not ready for customer installation/testing.** Do not ask the user to test until genuine Qwen Genesis 1 and native Windows acceptance gates have passed.

## Resume

Continue from `/mnt/data/kjv-audio-generator-work/`, package 0.4.6. Review `docs/RESUME_HERE.md`, `docs/DEVELOPMENT_STATUS.md` and `docs/ATTRIBUTION_DATASET_RESEARCH_2026-11-24.md`. Prioritize the real Qwen / Windows runtime gate after the speaker-import data-loss issue is closed.
