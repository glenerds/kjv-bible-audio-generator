from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path
from typing import Any

from .books import BOOKS, canonical_book
from .models import BibleDocument, Verse, VerseRef

_REF_LINE = re.compile(r"^\s*(?P<book>(?:[1-3]\s*)?[A-Za-z][A-Za-z ]*?)\s+(?P<ch>\d{1,3})\s*:\s*(?P<v>\d{1,3})\s+(?P<text>.+?)\s*$")
_USFM_ID = re.compile(r"^\\id\s+(\S+)")
_USFM_CHAPTER = re.compile(r"^\\c\s+(\d+)")
_USFM_VERSE = re.compile(r"^\\v\s+(\d+)(?:\s+(.+))?$")
_CHAPTER_HEADER = re.compile(r"^\s*((?:[1-3]\s+)?[A-Za-z][A-Za-z ]*?)\s+(?:chapter\s+)?(\d{1,3})\s*$", re.IGNORECASE)
_VERSE_LINE = re.compile(r"^\s*(\d{1,3})[.)]?\s+(.+?)\s*$")
_USFM_BOOKS = {"GEN":"Genesis","EXO":"Exodus","LEV":"Leviticus","NUM":"Numbers","DEU":"Deuteronomy","JOS":"Joshua","JDG":"Judges","RUT":"Ruth","1SA":"1 Samuel","2SA":"2 Samuel","1KI":"1 Kings","2KI":"2 Kings","1CH":"1 Chronicles","2CH":"2 Chronicles","EZR":"Ezra","NEH":"Nehemiah","EST":"Esther","JOB":"Job","PSA":"Psalms","PRO":"Proverbs","ECC":"Ecclesiastes","SNG":"Song of Solomon","ISA":"Isaiah","JER":"Jeremiah","LAM":"Lamentations","EZK":"Ezekiel","DAN":"Daniel","HOS":"Hosea","JOL":"Joel","AMO":"Amos","OBA":"Obadiah","JON":"Jonah","MIC":"Micah","NAM":"Nahum","HAB":"Habakkuk","ZEP":"Zephaniah","HAG":"Haggai","ZEC":"Zechariah","MAL":"Malachi","MAT":"Matthew","MRK":"Mark","LUK":"Luke","JHN":"John","ACT":"Acts","ROM":"Romans","1CO":"1 Corinthians","2CO":"2 Corinthians","GAL":"Galatians","EPH":"Ephesians","PHP":"Philippians","COL":"Colossians","1TH":"1 Thessalonians","2TH":"2 Thessalonians","1TI":"1 Timothy","2TI":"2 Timothy","TIT":"Titus","PHM":"Philemon","HEB":"Hebrews","JAS":"James","1PE":"1 Peter","2PE":"2 Peter","1JN":"1 John","2JN":"2 John","3JN":"3 John","JUD":"Jude","REV":"Revelation"}


def parse_path(path: str | Path) -> BibleDocument:
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(source)
    suffix = source.suffix.casefold()
    if suffix == ".zip":
        with zipfile.ZipFile(source) as archive:
            members = [n for n in archive.namelist() if Path(n).suffix.casefold() in {".usfm", ".sfm", ".txt", ".json"}]
            if not members:
                raise ValueError("ZIP contains no supported .usfm, .sfm, .txt or .json Bible files")
            all_verses: list[Verse] = []
            for name in sorted(members):
                raw = archive.read(name)
                doc = parse_text(raw.decode("utf-8-sig"), Path(name).suffix, name)
                for chapter in doc.ordered_chapters():
                    all_verses.extend(chapter.verses)
            return BibleDocument.from_verses(all_verses, source.name)
    return parse_text(source.read_text(encoding="utf-8-sig"), suffix, source.name)


def _parse_bytes(raw: bytes, suffix: str, name: str) -> BibleDocument:
    return parse_text(raw.decode("utf-8-sig"), suffix, name)


def parse_text(text: str, suffix: str = ".txt", source_name: str = "Pasted text") -> BibleDocument:
    if not text or not text.strip():
        raise ValueError("No Bible text was supplied")
    if suffix.casefold() == ".json" or text.lstrip().startswith(("{", "[")):
        try:
            return _parse_json(json.loads(text), source_name)
        except json.JSONDecodeError:
            if suffix.casefold() == ".json":
                raise
    if "\\id " in text or "\\c " in text or suffix.casefold() in {".usfm", ".sfm"}:
        verses = _parse_usfm(text)
        if verses:
            return BibleDocument.from_verses(verses, source_name)
    verses = _parse_reference_lines(text)
    if verses:
        return BibleDocument.from_verses(verses, source_name)
    verses = _parse_heading_text(text)
    if verses:
        return BibleDocument.from_verses(verses, source_name)
    raise ValueError("Could not recognize this Bible text. Use USFM/SFM, JSON, 'Genesis 1:1 text' lines, or book/chapter headings followed by numbered verses.")


def _clean_usfm_inline(value: str) -> str:
    """Remove USFM markup while retaining scripture text and omitting notes."""
    # Footnotes/cross references are editorial apparatus, not spoken scripture.
    value = re.sub(r"\\[fx]\b.*?\\[fx]\*", " ", value, flags=re.IGNORECASE)
    # Word markup contains the spoken token before the attribute separator.
    value = re.sub(r"\\w\s+([^|\\]+)\|[^\\]*\\w\*", r"\1", value)
    # Drop milestone attributes and all remaining style/paragraph markers.
    value = re.sub(r"\\[A-Za-z][A-Za-z0-9-]*\s*\|[^\\]*", " ", value)
    value = re.sub(r"\\[A-Za-z][A-Za-z0-9-]*\*?", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def _parse_usfm(text: str) -> list[Verse]:
    current_book: str | None = None
    current_chapter: int | None = None
    current_verse: int | None = None
    chunks: dict[tuple[str, int, int], list[str]] = {}
    # These markers introduce headings, captions or notes, not spoken verse text.
    non_scripture_markers = {"s", "s1", "s2", "s3", "s4", "ms", "ms1", "ms2", "mt", "mt1", "mt2",
                             "mte", "mr", "r", "d", "sp", "cl", "cp", "qa", "qc", "qm", "qr", "f", "x"}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = _USFM_ID.match(line)
        if match:
            book_code = match.group(1).upper()
            current_book = _USFM_BOOKS.get(book_code)
            if current_book is None:
                try:
                    current_book = canonical_book(book_code)
                except ValueError:
                    current_book = None
            current_chapter = current_verse = None
            continue
        match = _USFM_CHAPTER.match(line)
        if match and current_book:
            current_chapter = int(match.group(1))
            current_verse = None
            continue
        match = _USFM_VERSE.match(line)
        if match and current_book and current_chapter:
            current_verse = int(match.group(1))
            remainder = _clean_usfm_inline(match.group(2) or "")
            chunks.setdefault((current_book, current_chapter, current_verse), []).append(remainder)
            continue
        if not current_book or not current_chapter or not current_verse:
            continue
        if line.startswith("\\"):
            marker_match = re.match(r"\\([A-Za-z][A-Za-z0-9-]*)(?:\s+)?(.*)$", line)
            if not marker_match:
                continue
            marker, remainder = marker_match.group(1).casefold(), marker_match.group(2)
            if marker in non_scripture_markers:
                continue
            cleaned = _clean_usfm_inline(remainder)
            if cleaned:
                chunks[(current_book, current_chapter, current_verse)].append(cleaned)
            continue
        cleaned = _clean_usfm_inline(line)
        if cleaned:
            chunks[(current_book, current_chapter, current_verse)].append(cleaned)
    ordered = sorted(chunks.items(), key=lambda x: (next(i for i, (n, _) in enumerate(BOOKS) if n == x[0][0]), x[0][1], x[0][2]))
    verses = []
    for (book, chapter, verse), pieces in ordered:
        combined = " ".join(part for part in pieces if part).strip()
        if combined:
            verses.append(Verse(VerseRef(book, chapter, verse), combined))
    return verses


def _parse_reference_lines(text: str) -> list[Verse]:
    verses: list[Verse] = []
    for line in text.splitlines():
        match = _REF_LINE.match(line)
        if not match:
            continue
        try:
            ref = VerseRef(match.group("book"), int(match.group("ch")), int(match.group("v")))
            verses.append(Verse(ref, match.group("text")))
        except ValueError:
            continue
    return verses


def _parse_heading_text(text: str) -> list[Verse]:
    current_book: str | None = None
    current_chapter: int | None = None
    verses: list[Verse] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        heading = _CHAPTER_HEADER.match(line)
        if heading:
            try:
                current_book = canonical_book(heading.group(1))
                current_chapter = int(heading.group(2))
                continue
            except ValueError:
                pass
        verse_line = _VERSE_LINE.match(line)
        if current_book and current_chapter and verse_line:
            try:
                ref = VerseRef(current_book, current_chapter, int(verse_line.group(1)))
                verses.append(Verse(ref, verse_line.group(2)))
                continue
            except ValueError:
                pass
        # Some plain-text editions wrap a single verse over multiple lines.
        if current_book and current_chapter and verses:
            last = verses[-1]
            if last.ref.book == current_book and last.ref.chapter == current_chapter:
                verses[-1] = Verse(last.ref, f"{last.text} {line}")
    return verses


def _parse_json(data: Any, source_name: str) -> BibleDocument:
    # Accepted schemas: {"books":[{"name":"Genesis","chapters":[{"number":1,"verses":[...]}]}]}
    # or [{"book":"Genesis","chapter":1,"verse":1,"text":"..."}, ...]
    verses: list[Verse] = []
    if isinstance(data, dict) and isinstance(data.get("books"), list):
        for book_obj in data["books"]:
            name = book_obj.get("name") or book_obj.get("book")
            for chapter_obj in book_obj.get("chapters", []):
                ch_num = int(chapter_obj.get("number") or chapter_obj.get("chapter"))
                raw_verses = chapter_obj.get("verses", [])
                if isinstance(raw_verses, dict):
                    items = raw_verses.items()
                else:
                    items = ((item.get("number") or item.get("verse"), item.get("text")) for item in raw_verses)
                for verse_num, verse_text in items:
                    verses.append(Verse(VerseRef(name, ch_num, int(verse_num)), str(verse_text)))
    else:
        rows = data.get("verses", []) if isinstance(data, dict) else data
        if not isinstance(rows, list):
            raise ValueError("JSON must contain a books array or verses array")
        for row in rows:
            book = row.get("book") or row.get("book_name")
            chapter = int(row.get("chapter"))
            verse = int(row.get("verse") or row.get("number"))
            verses.append(Verse(VerseRef(book, chapter, verse), str(row.get("text", ""))))
    if not verses:
        raise ValueError("No Bible verses found in JSON")
    return BibleDocument.from_verses(verses, source_name)
