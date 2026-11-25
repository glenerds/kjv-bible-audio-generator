from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Iterable

from .books import BOOKS, TOTAL_CHAPTERS, book_sort_key, canonical_book, validate_chapter

EXPECTED_KJV_VERSES = 31102
_VERSE_COUNTS_PATH = Path(__file__).with_name("data") / "kjv_chapter_verse_counts.json"
try:
    with _VERSE_COUNTS_PATH.open("r", encoding="utf-8") as _counts_handle:
        KJV_CHAPTER_VERSE_COUNTS: dict[str, list[int]] = json.load(_counts_handle)["books"]
except (OSError, ValueError, KeyError, TypeError) as exc:
    raise RuntimeError(f"Bundled KJV chapter verse-count data is missing or invalid: {_VERSE_COUNTS_PATH}") from exc


@dataclass(frozen=True, order=True)
class VerseRef:
    book: str
    chapter: int
    verse: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "book", canonical_book(self.book))
        validate_chapter(self.book, self.chapter)
        if self.verse < 1:
            raise ValueError("Verse numbers must be positive")

    def key(self) -> str:
        return f"{self.book}|{self.chapter}|{self.verse}"

    def label(self) -> str:
        return f"{self.book} {self.chapter}:{self.verse}"


@dataclass(frozen=True)
class Verse:
    ref: VerseRef
    text: str

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError(f"Empty verse text at {self.ref.label()}")


@dataclass(frozen=True)
class SpeechSegment:
    ref: VerseRef
    index: int
    speaker_id: str
    text: str

    def __post_init__(self) -> None:
        if self.index < 0:
            raise ValueError("Segment index cannot be negative")
        if not self.speaker_id.strip():
            raise ValueError("Each speech segment must have a speaker ID")
        if not self.text.strip():
            raise ValueError("Speech segment text cannot be empty")


@dataclass
class Chapter:
    book: str
    number: int
    verses: list[Verse] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.book = canonical_book(self.book)
        validate_chapter(self.book, self.number)
        self.verses.sort(key=lambda v: v.ref.verse)
        refs = [v.ref.verse for v in self.verses]
        if len(refs) != len(set(refs)):
            raise ValueError(f"Duplicate verse in {self.book} {self.number}")
        if any(v.ref.book != self.book or v.ref.chapter != self.number for v in self.verses):
            raise ValueError("Chapter contains verse references from a different chapter")

    @property
    def key(self) -> str:
        return f"{self.book}|{self.number}"

    @property
    def label(self) -> str:
        return f"{self.book} {self.number}"


@dataclass
class BibleDocument:
    chapters: dict[tuple[str, int], Chapter]
    source_name: str = "Imported text"

    def ordered_chapters(self) -> list[Chapter]:
        return sorted(self.chapters.values(), key=lambda c: (book_sort_key(c.book), c.number))

    def validate_complete(self, *, require_verse_text: bool = True) -> dict[str, int | bool]:
        present = set(self.chapters)
        expected = {(book, ch) for book, count in BOOKS for ch in range(1, count + 1)}
        missing = expected - present
        extra = present - expected
        if extra:
            raise ValueError(f"Import contains invalid chapter references: {sorted(extra)[:5]}")
        if missing:
            sample = ", ".join(f"{b} {c}" for b, c in sorted(missing, key=lambda x:(book_sort_key(x[0]),x[1]))[:8])
            raise ValueError(f"Bible import is incomplete: {len(missing)} chapters missing (for example {sample})")
        verse_count = sum(len(ch.verses) for ch in self.chapters.values())
        if require_verse_text and verse_count == 0:
            raise ValueError("No verses were imported")
        # First reject gaps/duplicates in verse numbering, then compare every
        # chapter against its KJV reference count. A wrong/missing verse in one
        # chapter must not be masked by an extra verse elsewhere that preserves
        # the Bible-wide total.
        if set(KJV_CHAPTER_VERSE_COUNTS) != {book for book, _ in BOOKS}:
            raise RuntimeError("Bundled KJV verse-count data does not match the canonical 66-book list")
        for chapter in self.ordered_chapters():
            numbers = [verse.ref.verse for verse in chapter.verses]
            expected = list(range(1, len(numbers) + 1))
            if numbers != expected:
                raise ValueError(
                    f"Verse numbering in {chapter.label} must be continuous from 1; "
                    f"found {numbers[:8]}{'...' if len(numbers) > 8 else ''}"
                )
            expected_count = KJV_CHAPTER_VERSE_COUNTS[chapter.book][chapter.number - 1]
            if len(chapter.verses) != expected_count:
                raise ValueError(
                    f"{chapter.label} has {len(chapter.verses)} verses; the KJV reference count is {expected_count}. "
                    "Check the imported text or verse-numbering convention."
                )
        if verse_count != EXPECTED_KJV_VERSES:
            raise ValueError(
                f"The complete KJV must contain {EXPECTED_KJV_VERSES:,} verses; found {verse_count:,}. "
                "Check the source text and import format before generating the entire Bible."
            )
        return {"books": len({b for b, _ in present}), "chapters": len(present), "verses": verse_count,
                "complete_66_book_structure": len(present) == TOTAL_CHAPTERS,
                "complete_verse_count": verse_count == EXPECTED_KJV_VERSES}

    def chapter(self, book: str, number: int) -> Chapter:
        name = canonical_book(book)
        return self.chapters[(name, number)]

    @classmethod
    def from_verses(cls, verses: Iterable[Verse], source_name: str = "Imported text") -> "BibleDocument":
        grouped: dict[tuple[str, int], list[Verse]] = {}
        for verse in verses:
            grouped.setdefault((verse.ref.book, verse.ref.chapter), []).append(verse)
        chapters = {key: Chapter(key[0], key[1], values) for key, values in grouped.items()}
        return cls(chapters, source_name)
