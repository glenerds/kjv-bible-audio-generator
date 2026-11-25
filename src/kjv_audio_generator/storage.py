from __future__ import annotations

import hashlib
import json
import math
import sqlite3
import time
from pathlib import Path
from typing import Any

from .books import book_sort_key
from .models import Chapter
from .json_io import write_json_atomic


class QueueStore:
    def __init__(self, path: str | Path, output_root: str | Path | None = None) -> None:
        self.path = Path(path)
        self._project_layout = self.path.parent.name.casefold() == "metadata"
        inferred_root = self.path.parent.parent if self._project_layout else self.path.parent
        self.output_root = Path(output_root or inferred_root).resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._create_schema()
        self.recover_running_jobs()

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.path, timeout=30)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA foreign_keys=ON")
        return con

    def _create_schema(self) -> None:
        with self._connect() as con:
            con.executescript("""
                CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS jobs (
                    book TEXT NOT NULL, chapter INTEGER NOT NULL, sequence INTEGER NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('pending','running','complete','failed')),
                    attempts INTEGER NOT NULL DEFAULT 0, output_path TEXT, cue_path TEXT,
                    output_sha256 TEXT, cue_sha256 TEXT, input_sha256 TEXT,
                    error TEXT, updated_at REAL NOT NULL, PRIMARY KEY(book, chapter)
                );
                CREATE INDEX IF NOT EXISTS jobs_status_sequence ON jobs(status, sequence);
            """)
            # Additive migration for existing output folders created before hashes
            # were stored. Existing complete rows remain hashless until the audit
            # requeues them once for regeneration and a verified new completion.
            columns = {row[1] for row in con.execute("PRAGMA table_info(jobs)")}
            if "output_sha256" not in columns:
                con.execute("ALTER TABLE jobs ADD COLUMN output_sha256 TEXT")
            if "cue_sha256" not in columns:
                con.execute("ALTER TABLE jobs ADD COLUMN cue_sha256 TEXT")
            if "input_sha256" not in columns:
                con.execute("ALTER TABLE jobs ADD COLUMN input_sha256 TEXT")

    def recover_running_jobs(self) -> int:
        with self._connect() as con:
            cur = con.execute("UPDATE jobs SET status='pending', error='Recovered after interruption', updated_at=? WHERE status='running'", (time.time(),))
            return cur.rowcount

    def _remove_owned_output(self, raw_path: str | None) -> None:
        if not raw_path:
            return
        path = Path(raw_path)
        try:
            resolved = path.resolve()
            resolved.relative_to(self.output_root)
        except (OSError, ValueError):
            return
        if resolved.is_file():
            resolved.unlink(missing_ok=True)

    def seed(
        self,
        chapters: list[Chapter],
        source_hash: str,
        chapter_hashes: dict[tuple[str, int], str] | None = None,
    ) -> int:
        """Ensure jobs exist and invalidate only chapters whose generation inputs changed.

        The whole-Bible text hash still prevents mixing different imports in one
        output folder. Per-chapter hashes additionally cover speaker segmentation,
        voice profile inputs and encoding settings so edited characters/assignments
        regenerate only affected chapter audio.
        """
        invalidated = 0
        with self._connect() as con:
            old = con.execute("SELECT value FROM metadata WHERE key='source_sha256'").fetchone()
            count = con.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
            if old and old["value"] != source_hash and count:
                raise ValueError("The output folder already contains progress for a different Bible import. Choose a new output folder or clear its generation database.")
            con.execute("INSERT OR REPLACE INTO metadata(key,value) VALUES('source_sha256',?)", (source_hash,))
            for chapter in chapters:
                sequence = book_sort_key(chapter.book) * 1000 + chapter.number
                input_hash = chapter_hashes.get((chapter.book, chapter.number)) if chapter_hashes is not None else None
                con.execute(
                    "INSERT OR IGNORE INTO jobs(book,chapter,sequence,status,updated_at,input_sha256) VALUES(?,?,?,'pending',?,?)",
                    (chapter.book, chapter.number, sequence, time.time(), input_hash),
                )
                if chapter_hashes is None:
                    continue
                row = con.execute(
                    "SELECT status,input_sha256,output_path,cue_path FROM jobs WHERE book=? AND chapter=?",
                    (chapter.book, chapter.number),
                ).fetchone()
                previous = row["input_sha256"]
                changed = previous != input_hash
                if not changed:
                    continue
                # A hashless old completion cannot be proven to match today's
                # speaker/voice inputs, so regenerate it once after this migration.
                self._remove_owned_output(row["output_path"])
                self._remove_owned_output(row["cue_path"])
                con.execute(
                    "UPDATE jobs SET status='pending',attempts=0,output_path=NULL,cue_path=NULL,"
                    "output_sha256=NULL,cue_sha256=NULL,input_sha256=?,error=?,updated_at=? "
                    "WHERE book=? AND chapter=?",
                    (input_hash, "Generation inputs changed or legacy job lacks an input fingerprint; requeued", time.time(), chapter.book, chapter.number),
                )
                invalidated += 1
        return invalidated

    @staticmethod
    def _sha256_file(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def reconcile_completed_outputs(self) -> int:
        """Requeue missing, modified or structurally invalid completed output pairs.

        A chapter is marked complete only together with SHA-256 fingerprints of its
        MP3 and cue JSON. On resume, both files are rehashed before the cue structure
        is inspected. Older completed rows without fingerprints are deliberately
        requeued once so they can receive verifiable hashes.
        """
        with self._connect() as con:
            rows = [dict(row) for row in con.execute(
                "SELECT book,chapter,output_path,cue_path,output_sha256,cue_sha256 "
                "FROM jobs WHERE status='complete'"
            )]
            invalid: list[tuple[str, int, str]] = []
            for row in rows:
                # Completed output paths are stored as absolute paths for older
                # project versions. If the entire project folder was copied to a
                # new drive, the DB moved but those absolute paths did not. Rebase
                # the canonical filename pair to the current project root before
                # checking their hashes. Standalone QueueStore tests/uses that do
                # not use the production metadata layout retain their explicit paths.
                if self._project_layout:
                    stem = f"{row['book'].replace(' ', '_')}_{int(row['chapter']):03d}"
                    expected_mp3 = self.output_root / row["book"] / f"{stem}.mp3"
                    expected_cue = self.output_root / "metadata" / "verse_timestamps" / f"{stem}.json"
                    row["output_path"] = str(expected_mp3)
                    row["cue_path"] = str(expected_cue)
                    con.execute(
                        "UPDATE jobs SET output_path=?,cue_path=? WHERE book=? AND chapter=? AND status='complete'",
                        (str(expected_mp3), str(expected_cue), row["book"], int(row["chapter"])),
                    )
                reason = ""
                try:
                    mp3 = Path(row["output_path"] or "")
                    cue = Path(row["cue_path"] or "")
                    if not mp3.is_file() or mp3.stat().st_size < 512:
                        reason = "Completed MP3 is missing or too small"
                    elif not cue.is_file() or cue.stat().st_size < 16:
                        reason = "Completed timestamp cue file is missing or too small"
                    elif not row.get("output_sha256") or not row.get("cue_sha256"):
                        reason = "Completed outputs lack SHA-256 fingerprints"
                    elif self._sha256_file(mp3) != row["output_sha256"]:
                        reason = "Completed MP3 SHA-256 fingerprint mismatch"
                    elif self._sha256_file(cue) != row["cue_sha256"]:
                        reason = "Completed cue SHA-256 fingerprint mismatch"
                    else:
                        payload = json.loads(cue.read_text(encoding="utf-8"))
                        if not isinstance(payload, dict):
                            reason = "Completed timestamp cue file is not a JSON object"
                            segments = None
                        else:
                            segments = payload.get("segments")
                        if reason:
                            pass
                        elif (payload.get("schema_version") != 1 or payload.get("book") != row["book"]
                                or int(payload.get("chapter", -1)) != int(row["chapter"])
                                or not isinstance(segments, list) or not segments):
                            reason = "Completed timestamp cue file has an invalid chapter/segment header"
                        else:
                            previous_end = -1.0
                            duration = float(payload.get("duration_seconds", 0))
                            if not math.isfinite(duration) or duration <= 0:
                                reason = "Completed timestamp cue duration is invalid"
                            for segment in segments:
                                if reason:
                                    break
                                if not isinstance(segment, dict):
                                    reason = "Completed timestamp cue segment is not an object"
                                    break
                                start = float(segment["start_seconds"])
                                end = float(segment["end_seconds"])
                                if (not segment.get("speaker_id") or not segment.get("text")
                                        or not math.isfinite(start) or not math.isfinite(end)
                                        or start < previous_end or end <= start or end > duration + 0.1):
                                    reason = "Completed timestamp cue segments are inconsistent"
                                    break
                                previous_end = end
                except (OSError, ValueError, TypeError, KeyError, AttributeError, json.JSONDecodeError):
                    reason = "Completed output or timestamp cue file cannot be read"
                if reason:
                    invalid.append((row["book"], int(row["chapter"]), reason))
            for book, chapter, reason in invalid:
                con.execute(
                    "UPDATE jobs SET status='pending', output_path=NULL, cue_path=NULL, "
                    "output_sha256=NULL, cue_sha256=NULL, error=?, updated_at=? "
                    "WHERE book=? AND chapter=? AND status='complete'",
                    (reason + "; automatically requeued on resume", time.time(), book, chapter),
                )
            return len(invalid)

    def claim_next(self) -> dict[str, Any] | None:
        with self._connect() as con:
            # Reserve the write lock before selecting. Two app processes must not
            # both observe and claim the same pending chapter between SELECT/UPDATE.
            con.execute("BEGIN IMMEDIATE")
            row = con.execute("SELECT * FROM jobs WHERE status='pending' ORDER BY sequence LIMIT 1").fetchone()
            if row is None:
                return None
            con.execute("UPDATE jobs SET status='running', attempts=attempts+1, error=NULL, updated_at=? WHERE book=? AND chapter=?",
                        (time.time(), row["book"], row["chapter"]))
            return dict(con.execute("SELECT * FROM jobs WHERE book=? AND chapter=?", (row["book"], row["chapter"])).fetchone())

    def complete(self, book: str, chapter: int, output_path: str, cue_path: str) -> None:
        mp3 = Path(output_path)
        cue = Path(cue_path)
        if not mp3.is_file() or not cue.is_file():
            raise FileNotFoundError("Cannot mark a chapter complete without both its MP3 and timestamp cue file")
        output_sha256 = self._sha256_file(mp3)
        cue_sha256 = self._sha256_file(cue)
        with self._connect() as con:
            con.execute(
                "UPDATE jobs SET status='complete', output_path=?, cue_path=?, output_sha256=?, cue_sha256=?, "
                "error=NULL, updated_at=? WHERE book=? AND chapter=?",
                (str(mp3), str(cue), output_sha256, cue_sha256, time.time(), book, chapter),
            )

    def requeue_interrupted(self, book: str, chapter: int, reason: str = "Paused/stopped; resume safely") -> None:
        """Return an interrupted chapter to pending without consuming a failure retry."""
        with self._connect() as con:
            row = con.execute("SELECT attempts FROM jobs WHERE book=? AND chapter=?", (book, chapter)).fetchone()
            if row is None:
                raise KeyError((book, chapter))
            # claim_next increments attempts. A deliberate user stop is not a
            # synthesis failure, so restore the pre-claim retry count.
            attempts = max(0, int(row["attempts"]) - 1)
            con.execute(
                "UPDATE jobs SET status='pending', attempts=?, error=?, updated_at=? WHERE book=? AND chapter=?",
                (attempts, reason[-3000:], time.time(), book, chapter),
            )

    def retry_failed(self) -> int:
        """Make failed chapters eligible for a deliberate retry without erasing history."""
        with self._connect() as con:
            cur = con.execute(
                "UPDATE jobs SET status='pending', attempts=0, error='Manually queued for retry', updated_at=? WHERE status='failed'",
                (time.time(),),
            )
            return cur.rowcount

    def fail(self, book: str, chapter: int, error: str, max_attempts: int) -> str:
        with self._connect() as con:
            row = con.execute("SELECT attempts FROM jobs WHERE book=? AND chapter=?", (book, chapter)).fetchone()
            if row is None:
                raise KeyError((book, chapter))
            status = "pending" if row["attempts"] < max_attempts else "failed"
            con.execute("UPDATE jobs SET status=?, error=?, updated_at=? WHERE book=? AND chapter=?",
                        (status, error[-3000:], time.time(), book, chapter))
            return status

    def progress(self) -> dict[str, int]:
        with self._connect() as con:
            counts = {row["status"]: row["n"] for row in con.execute("SELECT status, COUNT(*) n FROM jobs GROUP BY status")}
        return {key: int(counts.get(key, 0)) for key in ("pending", "running", "complete", "failed")}

    def rows(self) -> list[dict[str, Any]]:
        with self._connect() as con:
            return [dict(r) for r in con.execute("SELECT * FROM jobs ORDER BY sequence")]

    def export_report(self, path: str | Path) -> dict[str, Any]:
        rows = self.rows()
        report = {"schema_version": 1, "generated_at_unix": time.time(), "counts": self.progress(), "chapters": rows}
        write_json_atomic(path, report)
        return report


def document_sha256(chapters: list[Chapter]) -> str:
    digest = hashlib.sha256()
    for chapter in chapters:
        digest.update(chapter.book.encode("utf-8")); digest.update(b"\0")
        digest.update(str(chapter.number).encode("ascii")); digest.update(b"\n")
        for verse in chapter.verses:
            digest.update(str(verse.ref.verse).encode("ascii")); digest.update(b"\0")
            digest.update(verse.text.encode("utf-8")); digest.update(b"\n")
    return digest.hexdigest()
