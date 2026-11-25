from __future__ import annotations

import json
import shutil
import subprocess

import numpy as np
import pytest

from kjv_audio_generator.attribution import AttributionMap
from kjv_audio_generator.audio import ChapterAudioAssembler
from kjv_audio_generator.backend import SyntheticTestBackend
from kjv_audio_generator.books import BOOKS, TOTAL_CHAPTERS
from kjv_audio_generator.parser import parse_text
from kjv_audio_generator.models import BibleDocument, Verse, VerseRef
from kjv_audio_generator.storage import QueueStore, document_sha256
from kjv_audio_generator.voices import VoiceRegistry
from kjv_audio_generator.worker import ChapterWorker


def sample_doc():
    return BibleDocument.from_verses([
        Verse(VerseRef("Genesis",1,1),"Beginning of sample."),
        Verse(VerseRef("Genesis",1,2),"Second sample verse."),
        Verse(VerseRef("Exodus",1,1),"Exodus sample verse."),
    ], "test")


def test_queue_claim_complete_and_progress(tmp_path):
    doc = sample_doc(); store = QueueStore(tmp_path / "queue.sqlite3")
    store.seed(doc.ordered_chapters(), document_sha256(doc.ordered_chapters()))
    job = store.claim_next()
    assert (job["book"],job["chapter"],job["status"],job["attempts"]) == ("Genesis",1,"running",1)
    mp3 = tmp_path / "gen.mp3"
    cue = tmp_path / "gen.json"
    mp3.write_bytes(b"M" * 700)
    cue.write_text(json.dumps({"schema_version": 1, "book": "Genesis", "chapter": 1,
                               "duration_seconds": 1.0,
                               "segments": [{"speaker_id": "narrator", "text": "test",
                                             "start_seconds": 0.0, "end_seconds": 0.9}]}), encoding="utf-8")
    store.complete("Genesis",1,str(mp3),str(cue))
    row = store.rows()[0]
    assert len(row["output_sha256"]) == 64 and len(row["cue_sha256"]) == 64
    assert store.progress() == {"pending":1,"running":0,"complete":1,"failed":0}


def test_queue_seeds_all_1189_bible_chapters_in_canonical_order(tmp_path):
    lines = [
        f"{book} {chapter}:1 Synthetic queue fixture for {book} {chapter}."
        for book, chapter_count in BOOKS
        for chapter in range(1, chapter_count + 1)
    ]
    document = parse_text("\\n".join(lines))
    chapters = document.ordered_chapters()

    assert len(chapters) == TOTAL_CHAPTERS == 1189
    store = QueueStore(tmp_path / "full-bible-queue.sqlite3")
    store.seed(chapters, document_sha256(chapters))

    rows = store.rows()
    assert len(rows) == 1189
    assert (rows[0]["book"], rows[0]["chapter"]) == ("Genesis", 1)
    assert (rows[-1]["book"], rows[-1]["chapter"]) == ("Revelation", 22)
    sequences = [int(row["sequence"]) for row in rows]
    assert sequences == sorted(sequences)
    assert len(set(sequences)) == TOTAL_CHAPTERS
    assert store.progress() == {
        "pending": 1189, "running": 0, "complete": 0, "failed": 0
    }

    first_three = [store.claim_next() for _ in range(3)]
    assert [(row["book"], row["chapter"]) for row in first_three] == [
        ("Genesis", 1), ("Genesis", 2), ("Genesis", 3)
    ]
    assert store.progress() == {
        "pending": 1186, "running": 3, "complete": 0, "failed": 0
    }


def test_running_jobs_recovered_on_restart(tmp_path):
    db = tmp_path / "queue.sqlite3"; store = QueueStore(db)
    doc = sample_doc(); store.seed(doc.ordered_chapters(), document_sha256(doc.ordered_chapters()))
    store.claim_next()
    reopened = QueueStore(db)
    assert reopened.progress()["running"] == 0
    assert reopened.progress()["pending"] == 2


def test_database_refuses_different_source_in_same_output(tmp_path):
    store = QueueStore(tmp_path / "q.sqlite3"); doc = sample_doc()
    store.seed(doc.ordered_chapters(), "a"*64)
    with pytest.raises(ValueError, match="different Bible import"):
        store.seed(doc.ordered_chapters(), "b"*64)


def test_audio_assembly_produces_decodable_mp3_and_cues(tmp_path):
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not installed")
    doc = sample_doc(); verse = doc.chapter("Genesis",1).verses
    segments = [
        __import__("kjv_audio_generator.models",fromlist=["SpeechSegment"]).SpeechSegment(verse[0].ref,0,"narrator",verse[0].text),
        __import__("kjv_audio_generator.models",fromlist=["SpeechSegment"]).SpeechSegment(verse[1].ref,0,"god",verse[1].text),
    ]
    backend = SyntheticTestBackend()
    waves = [backend.synthesize(s.text, type("P",(),{"speaker_id":s.speaker_id})()) for s in segments]
    assembler = ChapterAudioAssembler(tmp_path, bitrate_kbps=96)
    mp3, cue = assembler.write_chapter("Genesis",1,segments,waves)
    assert mp3.is_file() and mp3.stat().st_size > 512
    payload = json.loads(cue.read_text())
    assert len(payload["segments"]) == 2
    assert payload["segments"][0]["speaker_id"] == "narrator"
    assert payload["segments"][1]["start_seconds"] >= payload["segments"][0]["end_seconds"]
    decoded = subprocess.run(["ffmpeg","-v","error","-i",str(mp3),"-f","null","-"],capture_output=True)
    assert decoded.returncode == 0


def test_worker_runs_all_chapters_sequentially_and_reports(tmp_path):
    assert shutil.which("ffmpeg"), "ffmpeg required for this integration test"
    doc = sample_doc(); registry = VoiceRegistry.defaults(); backend = SyntheticTestBackend()
    worker = ChapterWorker(doc,tmp_path,registry,AttributionMap(registry),backend,ChapterAudioAssembler(tmp_path))
    worker.start(background=False)
    counts = worker.store.progress()
    assert counts == {"pending":0,"running":0,"complete":2,"failed":0}
    rows = worker.store.rows()
    assert [(x["book"],x["chapter"],x["status"]) for x in rows] == [("Genesis",1,"complete"),("Exodus",1,"complete")]
    assert (tmp_path/"Genesis"/"Genesis_001.mp3").is_file()
    assert (tmp_path/"Exodus"/"Exodus_001.mp3").is_file()
    report = json.loads((tmp_path/"metadata"/"generation_report.json").read_text())
    assert report["counts"]["complete"] == 2
    assert (tmp_path/"metadata"/"voice_registry.json").is_file()


def test_synthetic_backend_is_marked_test_only():
    backend = SyntheticTestBackend()
    assert backend.is_test_backend is True
    samples, sr = backend.synthesize("hello", VoiceRegistry.defaults().get("narrator"))
    assert samples.size > 0 and sr == 24000 and np.max(np.abs(samples)) < 0.1


def test_user_interrupt_requeues_without_using_failure_attempt(tmp_path):
    store = QueueStore(tmp_path / "queue.sqlite3")
    doc = sample_doc()
    store.seed(doc.ordered_chapters(), document_sha256(doc.ordered_chapters()))
    job = store.claim_next()
    store.requeue_interrupted(job["book"], job["chapter"])
    row = store.rows()[0]
    assert row["status"] == "pending"
    assert row["attempts"] == 0


def test_failed_chapters_can_be_deliberately_retried(tmp_path):
    store = QueueStore(tmp_path / "queue.sqlite3")
    doc = sample_doc()
    store.seed(doc.ordered_chapters(), document_sha256(doc.ordered_chapters()))
    first = store.claim_next()
    assert store.fail(first["book"], first["chapter"], "temporary", max_attempts=1) == "failed"
    assert store.retry_failed() == 1
    row = store.rows()[0]
    assert row["status"] == "pending" and row["attempts"] == 0


def test_worker_stop_during_multisegment_chapter_leaves_safe_pending_job(tmp_path):
    import threading
    from kjv_audio_generator.models import SpeechSegment

    entered = threading.Event()
    release = threading.Event()

    class BlockingBackend(SyntheticTestBackend):
        def synthesize(self, text, profile):
            if not entered.is_set():
                entered.set()
                assert release.wait(5)
            return super().synthesize(text, profile)

    registry = VoiceRegistry.defaults()
    mapping = AttributionMap(registry, segment_overrides={
        "Genesis 1:1": [
            {"speaker_id": "narrator", "text": "Narrator introduction."},
            {"speaker_id": "god", "text": " A spoken line."},
        ]
    })
    doc = BibleDocument.from_verses([Verse(VerseRef("Genesis", 1, 1), "Narrator introduction. A spoken line.")])
    worker = ChapterWorker(doc, tmp_path, registry, mapping, BlockingBackend(), ChapterAudioAssembler(tmp_path))
    worker.start(background=True)
    assert entered.wait(5)
    worker.stop()
    release.set()
    worker.join(5)
    assert worker._thread is not None and not worker._thread.is_alive()
    row = worker.store.rows()[0]
    assert row["status"] == "pending"
    assert row["attempts"] == 0
    assert not (tmp_path / "Genesis" / "Genesis_001.mp3").exists()


def test_worker_pause_and_resume_finishes_same_chapter(tmp_path):
    import threading
    import time

    entered = threading.Event()
    release = threading.Event()
    calls = []

    class BlockingBackend(SyntheticTestBackend):
        def synthesize(self, text, profile):
            calls.append(text)
            if len(calls) == 1:
                entered.set()
                assert release.wait(5)
            return super().synthesize(text, profile)

    registry = VoiceRegistry.defaults()
    mapping = AttributionMap(registry, segment_overrides={
        "Genesis 1:1": [
            {"speaker_id": "narrator", "text": "Narrator introduction."},
            {"speaker_id": "god", "text": " A spoken line."},
        ]
    })
    doc = BibleDocument.from_verses([Verse(VerseRef("Genesis", 1, 1), "Narrator introduction. A spoken line.")])
    worker = ChapterWorker(doc, tmp_path, registry, mapping, BlockingBackend(), ChapterAudioAssembler(tmp_path))
    worker.start(background=True)
    assert entered.wait(5)
    worker.pause()
    release.set()
    time.sleep(0.1)
    assert calls == ["Narrator introduction."]
    worker.resume()
    worker.join(5)
    assert worker._thread is not None and not worker._thread.is_alive()
    assert calls == ["Narrator introduction.", " A spoken line."]
    assert worker.store.progress()["complete"] == 1
    assert (tmp_path / "Genesis" / "Genesis_001.mp3").is_file()


def test_worker_stop_during_voice_preparation_keeps_all_chapters_pending(tmp_path):
    events = []
    registry = VoiceRegistry.defaults()
    doc = sample_doc()

    def stop_check():
        raise InterruptedError("Generation stopped by user")

    class StopImmediatelyBackend(SyntheticTestBackend):
        def prepare_profiles(self, profiles, *, control_check=None, progress_callback=None):
            if control_check:
                stop_check()

    worker = ChapterWorker(
        doc, tmp_path, registry, AttributionMap(registry), StopImmediatelyBackend(),
        ChapterAudioAssembler(tmp_path), callback=lambda event, data: events.append((event, data)),
    )
    worker.start(background=False)
    assert worker.store.progress() == {"pending": 2, "running": 0, "complete": 0, "failed": 0}
    finished = [data for event, data in events if event == "finished"]
    assert finished and finished[-1]["stopped"] is True


def test_worker_requeues_completed_chapter_when_mp3_was_removed(tmp_path):
    assert shutil.which("ffmpeg"), "ffmpeg required for this integration test"
    doc = sample_doc()
    registry = VoiceRegistry.defaults()
    first = ChapterWorker(doc, tmp_path, registry, AttributionMap(registry), SyntheticTestBackend(),
                          ChapterAudioAssembler(tmp_path))
    first.start(background=False)
    assert first.store.progress()["complete"] == 2

    missing_mp3 = tmp_path / "Genesis" / "Genesis_001.mp3"
    missing_mp3.unlink()
    second = ChapterWorker(doc, tmp_path, registry, AttributionMap(registry), SyntheticTestBackend(),
                           ChapterAudioAssembler(tmp_path))
    second.start(background=False)
    assert second.store.progress() == {"pending": 0, "running": 0, "complete": 2, "failed": 0}
    assert missing_mp3.is_file() and missing_mp3.stat().st_size > 512
    assert second.store.rows()[0]["error"] is None


def test_queue_requeues_completed_chapter_when_cue_json_is_invalid(tmp_path):
    store = QueueStore(tmp_path / "queue.sqlite3")
    doc = sample_doc()
    store.seed(doc.ordered_chapters(), document_sha256(doc.ordered_chapters()))
    job = store.claim_next()
    mp3 = tmp_path / "sample.mp3"; mp3.write_bytes(b"M" * 700)
    cue = tmp_path / "sample.json"; cue.write_text("[]" + (" " * 20), encoding="utf-8")
    store.complete(job["book"], job["chapter"], str(mp3), str(cue))
    assert store.reconcile_completed_outputs() == 1
    row = store.rows()[0]
    assert row["status"] == "pending"
    assert "JSON object" in row["error"]


def test_completed_project_restart_skips_voice_model_preparation(tmp_path):
    assert shutil.which("ffmpeg"), "ffmpeg required for this integration test"
    doc = sample_doc()
    registry = VoiceRegistry.defaults()
    first = ChapterWorker(doc, tmp_path, registry, AttributionMap(registry), SyntheticTestBackend(),
                          ChapterAudioAssembler(tmp_path))
    first.start(background=False)
    assert first.store.progress()["complete"] == 2

    class MustNotLoadModel(SyntheticTestBackend):
        def prepare_profiles(self, profiles, *, control_check=None, progress_callback=None):
            raise AssertionError("A completed output folder must not load Qwen models again")

    second = ChapterWorker(doc, tmp_path, registry, AttributionMap(registry), MustNotLoadModel(),
                           ChapterAudioAssembler(tmp_path))
    second.start(background=False)
    assert second.store.progress() == {"pending": 0, "running": 0, "complete": 2, "failed": 0}


def test_completed_mp3_same_size_corruption_is_detected_and_regenerated(tmp_path):
    assert shutil.which("ffmpeg"), "ffmpeg required for this integration test"
    doc = sample_doc()
    registry = VoiceRegistry.defaults()
    first = ChapterWorker(doc, tmp_path, registry, AttributionMap(registry), SyntheticTestBackend(),
                          ChapterAudioAssembler(tmp_path))
    first.start(background=False)
    row_before = first.store.rows()[0]
    mp3 = tmp_path / "Genesis" / "Genesis_001.mp3"
    original_size = mp3.stat().st_size
    original_sha = row_before["output_sha256"]
    original_bytes = mp3.read_bytes()
    damaged = bytearray(original_bytes)
    damaged[len(damaged)//2] ^= 0x5A
    mp3.write_bytes(damaged)
    assert mp3.stat().st_size == original_size

    events = []
    second = ChapterWorker(doc, tmp_path, registry, AttributionMap(registry), SyntheticTestBackend(),
                           ChapterAudioAssembler(tmp_path), callback=lambda event, data: events.append((event, data)))
    second.start(background=False)
    row_after = second.store.rows()[0]
    assert row_after["status"] == "complete"
    # The synthetic test backend is deterministic, so correct regeneration restores
    # the exact original bytes and therefore the original SHA-256 value.
    assert mp3.read_bytes() == original_bytes
    assert any(event == "outputs_requeued" and data["count"] == 1 for event, data in events)
    assert row_after["output_sha256"] == original_sha


def test_completed_cue_same_size_tampering_is_detected_and_regenerated(tmp_path):
    assert shutil.which("ffmpeg"), "ffmpeg required for this integration test"
    doc = sample_doc()
    registry = VoiceRegistry.defaults()
    first = ChapterWorker(doc, tmp_path, registry, AttributionMap(registry), SyntheticTestBackend(),
                          ChapterAudioAssembler(tmp_path))
    first.start(background=False)
    row_before = first.store.rows()[0]
    cue = tmp_path / "metadata" / "verse_timestamps" / "Genesis_001.json"
    original_sha = row_before["cue_sha256"]
    original_bytes = cue.read_bytes()
    raw = bytearray(original_bytes)
    raw[-2] = ord(" ") if raw[-2] != ord(" ") else ord("\n")
    cue.write_bytes(raw)
    assert len(raw) == cue.stat().st_size

    events = []
    second = ChapterWorker(doc, tmp_path, registry, AttributionMap(registry), SyntheticTestBackend(),
                           ChapterAudioAssembler(tmp_path), callback=lambda event, data: events.append((event, data)))
    second.start(background=False)
    row_after = second.store.rows()[0]
    assert row_after["status"] == "complete"
    assert cue.read_bytes() == original_bytes
    assert any(event == "outputs_requeued" and data["count"] == 1 for event, data in events)
    assert row_after["cue_sha256"] == original_sha


def test_legacy_queue_completed_rows_without_hashes_are_requeued(tmp_path):
    import sqlite3
    db = tmp_path / "legacy.sqlite3"
    with sqlite3.connect(db) as con:
        con.executescript("""
            CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE jobs (
                book TEXT NOT NULL, chapter INTEGER NOT NULL, sequence INTEGER NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('pending','running','complete','failed')),
                attempts INTEGER NOT NULL DEFAULT 0, output_path TEXT, cue_path TEXT,
                error TEXT, updated_at REAL NOT NULL, PRIMARY KEY(book, chapter)
            );
            INSERT INTO jobs(book,chapter,sequence,status,attempts,output_path,cue_path,error,updated_at)
            VALUES('Genesis',1,1001,'complete',1,'old.mp3','old.json',NULL,0);
        """)
    store = QueueStore(db)
    columns = {r[1] for r in sqlite3.connect(db).execute("PRAGMA table_info(jobs)")}
    assert {"output_sha256", "cue_sha256", "input_sha256"}.issubset(columns)
    assert store.reconcile_completed_outputs() == 1
    assert store.rows()[0]["status"] == "pending"


def test_queue_complete_refuses_missing_output_pair(tmp_path):
    store = QueueStore(tmp_path / "q.sqlite3")
    doc = sample_doc()
    store.seed(doc.ordered_chapters(), document_sha256(doc.ordered_chapters()))
    store.claim_next()
    with pytest.raises(FileNotFoundError, match="both its MP3"):
        store.complete("Genesis", 1, str(tmp_path / "missing.mp3"), str(tmp_path / "missing.json"))


def test_worker_prepares_only_profiles_needed_by_pending_chapters(tmp_path):
    """Already-completed chapters must not trigger expensive Qwen profile preparation."""
    from kjv_audio_generator.attribution import SpeakerRange
    from kjv_audio_generator.models import SpeechSegment

    assert shutil.which("ffmpeg"), "ffmpeg required for this integration test"
    doc = BibleDocument.from_verses([
        Verse(VerseRef("Genesis", 1, 1), "Moses speaks in a completed chapter."),
        Verse(VerseRef("Genesis", 2, 1), "Jesus speaks in the pending chapter."),
    ])
    registry = VoiceRegistry.defaults()
    mapping = AttributionMap(registry, ranges=[
        SpeakerRange("Genesis", 1, 1, 1, "moses"),
        SpeakerRange("Genesis", 2, 1, 1, "jesus"),
    ])
    output = tmp_path / "output"
    assembler = ChapterAudioAssembler(output)
    store = QueueStore(output / "metadata" / "generation.sqlite3", output_root=output)

    class CapturingBackend(SyntheticTestBackend):
        def __init__(self):
            super().__init__()
            self.prepared_ids = []

        def prepare_profiles(self, profiles, *, control_check=None, progress_callback=None):
            self.prepared_ids = [profile.speaker_id for profile in profiles]
            return super().prepare_profiles(profiles, control_check=control_check,
                                            progress_callback=progress_callback)

    backend = CapturingBackend()
    worker = ChapterWorker(doc, output, registry, mapping, backend, assembler)
    hashes = worker._build_chapter_input_hashes()
    store.seed(doc.ordered_chapters(), document_sha256(doc.ordered_chapters()), hashes)

    first_job = store.claim_next()
    assert first_job["book"] == "Genesis" and first_job["chapter"] == 1
    completed_segments = mapping.segments_for(doc.chapter("Genesis", 1).verses[0])
    synthetic = SyntheticTestBackend()
    completed_waveforms = [
        synthetic.synthesize(segment.text, registry.get(segment.speaker_id))
        for segment in completed_segments
    ]
    mp3, cue = assembler.write_chapter("Genesis", 1, completed_segments, completed_waveforms)
    store.complete("Genesis", 1, str(mp3), str(cue))

    worker.start(background=False)
    assert worker.store.progress() == {"pending": 0, "running": 0, "complete": 2, "failed": 0}
    assert backend.prepared_ids == ["jesus"]


def test_voice_profile_change_invalidates_only_chapters_using_that_profile(tmp_path):
    assert shutil.which("ffmpeg"), "ffmpeg required for this integration test"
    doc = BibleDocument.from_verses([
        Verse(VerseRef("Genesis", 1, 1), "Moses speaks in this chapter."),
        Verse(VerseRef("Genesis", 2, 1), "Jesus speaks in this chapter."),
    ])
    registry = VoiceRegistry.defaults()
    mapping = AttributionMap(registry, ranges=[
        __import__("kjv_audio_generator.attribution", fromlist=["SpeakerRange"]).SpeakerRange(
            "Genesis", 1, 1, 1, "moses"),
        __import__("kjv_audio_generator.attribution", fromlist=["SpeakerRange"]).SpeakerRange(
            "Genesis", 2, 1, 1, "jesus"),
    ])
    first = ChapterWorker(doc, tmp_path, registry, mapping, SyntheticTestBackend(),
                          ChapterAudioAssembler(tmp_path))
    first.start(background=False)
    assert first.store.progress()["complete"] == 2
    before = {(r["book"], r["chapter"]): r["output_sha256"] for r in first.store.rows()}

    registry.get("moses").voice_description += " More weathered and deliberate."

    class CapturingBackend(SyntheticTestBackend):
        def __init__(self):
            super().__init__()
            self.prepared_ids = []

        def prepare_profiles(self, profiles, *, control_check=None, progress_callback=None):
            self.prepared_ids = [p.speaker_id for p in profiles]
            return super().prepare_profiles(profiles, control_check=control_check,
                                            progress_callback=progress_callback)

    backend = CapturingBackend()
    events = []
    second = ChapterWorker(doc, tmp_path, registry, mapping, backend, ChapterAudioAssembler(tmp_path),
                           callback=lambda event, data: events.append((event, data)))
    second.start(background=False)
    rows = {(r["book"], r["chapter"]): r for r in second.store.rows()}
    assert second.store.progress() == {"pending": 0, "running": 0, "complete": 2, "failed": 0}
    assert backend.prepared_ids == ["moses"]
    assert rows[("Genesis", 1)]["input_sha256"] != None
    assert rows[("Genesis", 2)]["output_sha256"] == before[("Genesis", 2)]
    assert any(event == "chapter_inputs_changed" and data["count"] == 1
               for event, data in events)


def test_speaker_assignment_change_invalidates_only_affected_chapter(tmp_path):
    assert shutil.which("ffmpeg"), "ffmpeg required for this integration test"
    from kjv_audio_generator.attribution import SpeakerRange

    doc = BibleDocument.from_verses([
        Verse(VerseRef("Genesis", 1, 1), "The first chapter is spoken by Moses."),
        Verse(VerseRef("Genesis", 2, 1), "The second chapter is spoken by Jesus."),
    ])
    registry = VoiceRegistry.defaults()
    mapping = AttributionMap(registry, ranges=[
        SpeakerRange("Genesis", 1, 1, 1, "moses"),
        SpeakerRange("Genesis", 2, 1, 1, "jesus"),
    ])
    first = ChapterWorker(doc, tmp_path, registry, mapping, SyntheticTestBackend(),
                          ChapterAudioAssembler(tmp_path))
    first.start(background=False)
    before = {(r["book"], r["chapter"]): r["output_sha256"] for r in first.store.rows()}
    assert first.store.progress()["complete"] == 2

    edited_mapping = AttributionMap(registry, ranges=[
        SpeakerRange("Genesis", 1, 1, 1, "unknown_speaker"),
        SpeakerRange("Genesis", 2, 1, 1, "jesus"),
    ])

    class CapturingBackend(SyntheticTestBackend):
        def __init__(self):
            super().__init__()
            self.prepared_ids = []

        def prepare_profiles(self, profiles, *, control_check=None, progress_callback=None):
            self.prepared_ids = [profile.speaker_id for profile in profiles]
            return super().prepare_profiles(profiles, control_check=control_check,
                                            progress_callback=progress_callback)

    backend = CapturingBackend()
    events = []
    second = ChapterWorker(doc, tmp_path, registry, edited_mapping, backend, ChapterAudioAssembler(tmp_path),
                           callback=lambda event, data: events.append((event, data)))
    second.start(background=False)
    rows = {(r["book"], r["chapter"]): r for r in second.store.rows()}
    assert second.store.progress() == {"pending": 0, "running": 0, "complete": 2, "failed": 0}
    assert backend.prepared_ids == ["unknown_speaker"]
    assert rows[("Genesis", 1)]["output_sha256"] != before[("Genesis", 1)]
    assert rows[("Genesis", 2)]["output_sha256"] == before[("Genesis", 2)]
    assert any(event == "chapter_inputs_changed" and data["count"] == 1
               for event, data in events)


def test_concurrent_queue_claims_are_atomic_across_store_instances(tmp_path):
    import threading

    doc = sample_doc()
    db = tmp_path / "shared" / "queue.sqlite3"
    first_store = QueueStore(db)
    first_store.seed(doc.ordered_chapters(), document_sha256(doc.ordered_chapters()))
    stores = [QueueStore(db), QueueStore(db)]
    barrier = threading.Barrier(3)
    claimed = []
    errors = []

    def claim(store):
        try:
            barrier.wait(timeout=5)
            claimed.append(store.claim_next())
        except BaseException as exc:
            errors.append(exc)

    threads = [threading.Thread(target=claim, args=(store,)) for store in stores]
    for thread in threads:
        thread.start()
    barrier.wait(timeout=5)
    for thread in threads:
        thread.join(timeout=10)

    assert not errors
    assert all(not thread.is_alive() for thread in threads)
    assert len(claimed) == 2
    assert len({(job["book"], job["chapter"]) for job in claimed if job}) == 2
    assert first_store.progress()["running"] == 2


def test_audio_generation_fingerprint_changes_when_encoder_binary_changes(tmp_path):
    ffmpeg = tmp_path / "fake-ffmpeg.exe"
    ffmpeg.write_bytes(b"first encoder build")
    first = ChapterAudioAssembler(tmp_path / "out", ffmpeg=ffmpeg)
    fingerprint_a = first.generation_fingerprint()
    ffmpeg.write_bytes(b"second encoder build with same name")
    second = ChapterAudioAssembler(tmp_path / "out", ffmpeg=ffmpeg)
    fingerprint_b = second.generation_fingerprint()
    assert fingerprint_a != fingerprint_b


def test_completed_project_rebases_output_paths_after_folder_relocation(tmp_path):
    assert shutil.which("ffmpeg"), "ffmpeg required for this integration test"
    import shutil as file_shutil
    from pathlib import Path

    source_root = tmp_path / "old-drive" / "Bible Audio"
    moved_root = tmp_path / "usb-drive" / "Bible Audio"
    doc = sample_doc()
    registry = VoiceRegistry.defaults()
    first = ChapterWorker(doc, source_root, registry, AttributionMap(registry), SyntheticTestBackend(),
                          ChapterAudioAssembler(source_root))
    first.start(background=False)
    assert first.store.progress()["complete"] == 2
    old_paths = [row["output_path"] for row in first.store.rows()]
    file_shutil.copytree(source_root, moved_root)

    class MustNotRegenerate(SyntheticTestBackend):
        def prepare_profiles(self, profiles, *, control_check=None, progress_callback=None):
            raise AssertionError("A copied, complete portable project must not re-synthesize voices")

    moved = ChapterWorker(doc, moved_root, registry, AttributionMap(registry), MustNotRegenerate(),
                          ChapterAudioAssembler(moved_root))
    moved.start(background=False)
    assert moved.store.progress() == {"pending": 0, "running": 0, "complete": 2, "failed": 0}
    new_paths = [row["output_path"] for row in moved.store.rows()]
    assert all(str(moved_root) in path for path in new_paths)
    assert all(Path(path).is_file() for path in new_paths)
    assert all(old != new for old, new in zip(old_paths, new_paths))
