from __future__ import annotations

import json
import zipfile

import pytest

from kjv_audio_generator.books import BOOKS, TOTAL_CHAPTERS, canonical_book
from kjv_audio_generator.models import BibleDocument, Verse, VerseRef
from kjv_audio_generator.parser import parse_path, parse_text


def test_canonical_bible_structure():
    assert len(BOOKS) == 66
    assert TOTAL_CHAPTERS == 1189
    assert canonical_book("Gen") == "Genesis"
    assert canonical_book("1Jn") == "1 John"
    assert canonical_book("REV") == "Revelation"


def test_reference_line_parser():
    doc = parse_text("Genesis 1:1 In the beginning.\nGenesis 1:2 The earth was.")
    assert len(doc.chapters) == 1
    assert [v.text for v in doc.chapter("Genesis", 1).verses] == ["In the beginning.", "The earth was."]


def test_book_heading_parser():
    doc = parse_text("Genesis 1\n1 In the beginning.\n2 The earth was.\nGenesis 2\n1 These are the generations.")
    assert [c.label for c in doc.ordered_chapters()] == ["Genesis 1", "Genesis 2"]
    assert len(doc.chapter("Gen", 2).verses) == 1


def test_usfm_parser_with_continuation():
    text = "\\id GEN\n\\c 1\n\\v 1 In the beginning God created.\nAnd the earth.\n\\v 2 And the earth was without form.\n"
    doc = parse_text(text, ".usfm")
    assert doc.chapter("Genesis", 1).verses[0].text == "In the beginning God created. And the earth."
    assert len(doc.chapter("Genesis", 1).verses) == 2


def test_json_nested_schema():
    raw = {"books":[{"name":"Genesis","chapters":[{"number":1,"verses":[{"number":1,"text":"Beginning"},{"number":2,"text":"Earth"}]}]}]}
    doc = parse_text(json.dumps(raw), ".json")
    assert len(doc.chapter("Genesis", 1).verses) == 2


def test_json_flat_schema():
    raw = [{"book":"Genesis","chapter":1,"verse":1,"text":"Beginning"}]
    doc = parse_text(json.dumps(raw), ".json")
    assert doc.chapter("Genesis", 1).verses[0].text == "Beginning"


def test_zip_with_multiple_book_files(tmp_path):
    target = tmp_path / "bible.zip"
    with zipfile.ZipFile(target, "w") as zf:
        zf.writestr("01-GEN.usfm", "\\id GEN\n\\c 1\n\\v 1 Begin")
        zf.writestr("02-EXO.usfm", "\\id EXO\n\\c 1\n\\v 1 Exodus begins")
    doc = parse_path(target)
    assert [(c.book,c.number) for c in doc.ordered_chapters()] == [("Genesis",1),("Exodus",1)]


def test_invalid_book_chapter_and_empty_input():
    with pytest.raises(ValueError, match="Unknown Bible book"):
        VerseRef("Narnia",1,1)
    with pytest.raises(ValueError, match="Invalid chapter"):
        VerseRef("Genesis",51,1)
    with pytest.raises(ValueError, match="No Bible text"):
        parse_text("  ")


def test_duplicate_verse_rejected():
    with pytest.raises(ValueError, match="Duplicate verse"):
        BibleDocument.from_verses([Verse(VerseRef("Genesis",1,1),"one"), Verse(VerseRef("Genesis",1,1),"two")])


def test_complete_document_validation_reports_missing_chapters():
    doc = parse_text("Genesis 1:1 text")
    with pytest.raises(ValueError, match="1188 chapters missing"):
        doc.validate_complete()


def test_plain_text_accepts_chapter_wording_and_wrapped_verses():
    doc = parse_text("Genesis Chapter 1\n1 In the beginning God created\nthe heaven and the earth.\n2 And the earth was without form.")
    verses = doc.chapter("Genesis", 1).verses
    assert [v.text for v in verses] == [
        "In the beginning God created the heaven and the earth.",
        "And the earth was without form.",
    ]


def test_usfm_preserves_paragraph_text_and_omits_footnotes():
    text = (
        "\\id GEN\n\\c 1\n\\v 1 In the beginning \\w God|lemma=God strong=H430\\w* created. "
        "\\f + \\ft editorial footnote should not be spoken\\f*\n"
        "\\q1 And the earth was without form.\n\\v 2 And darkness was upon the face."
    )
    doc = parse_text(text, ".usfm")
    assert doc.chapter("Genesis", 1).verses[0].text == "In the beginning God created. And the earth was without form."
    assert "footnote" not in doc.chapter("Genesis", 1).verses[0].text


def test_complete_document_requires_exact_kjv_per_chapter_verse_counts():
    import json
    from pathlib import Path
    from kjv_audio_generator.models import KJV_CHAPTER_VERSE_COUNTS

    verses = []
    for book, chapters in BOOKS:
        for chapter in range(1, chapters + 1):
            count = KJV_CHAPTER_VERSE_COUNTS[book][chapter - 1]
            for number in range(1, count + 1):
                verses.append(Verse(VerseRef(book, chapter, number), f"Synthetic test verse {number}."))
    doc = BibleDocument.from_verses(verses, "synthetic-schema-test")
    report = doc.validate_complete()
    assert (report["books"], report["chapters"], report["verses"]) == (66, 1189, 31102)
    assert report["complete_verse_count"] is True
    assert sum(map(len, KJV_CHAPTER_VERSE_COUNTS.values())) == 1189


def test_complete_document_refuses_redistributed_verse_counts_even_when_total_matches():
    from kjv_audio_generator.models import KJV_CHAPTER_VERSE_COUNTS
    verses = []
    for book, chapters in BOOKS:
        for chapter in range(1, chapters + 1):
            count = KJV_CHAPTER_VERSE_COUNTS[book][chapter - 1]
            if book == "Genesis" and chapter == 1:
                count += 1
            elif book == "Genesis" and chapter == 2:
                count -= 1
            for number in range(1, count + 1):
                verses.append(Verse(VerseRef(book, chapter, number), f"Synthetic test verse {number}."))
    doc = BibleDocument.from_verses(verses, "synthetic-wrong-chapter-counts")
    with pytest.raises(ValueError, match="Genesis 1 has 32 verses; the KJV reference count is 31"):
        doc.validate_complete()


def test_complete_document_refuses_non_contiguous_verse_numbers():
    from kjv_audio_generator.books import BOOKS
    verses = []
    for book, chapters in BOOKS:
        for chapter in range(1, chapters + 1):
            if book == "Genesis" and chapter == 1:
                verses.extend([Verse(VerseRef(book, chapter, 1), "One."), Verse(VerseRef(book, chapter, 3), "Three.")])
            else:
                verses.append(Verse(VerseRef(book, chapter, 1), "Synthetic verse."))
    doc = BibleDocument.from_verses(verses, "synthetic-incomplete")
    with pytest.raises(ValueError, match="continuous from 1"):
        doc.validate_complete()


def test_reference_line_import_parses_all_31102_kjv_verse_references():
    from kjv_audio_generator.models import KJV_CHAPTER_VERSE_COUNTS

    lines = []
    for book, chapter_total in BOOKS:
        chapter_counts = KJV_CHAPTER_VERSE_COUNTS[book]
        assert len(chapter_counts) == chapter_total
        for chapter, verse_count in enumerate(chapter_counts, start=1):
            for verse in range(1, verse_count + 1):
                lines.append(f"{book} {chapter}:{verse} Synthetic verse for full-Bible parser testing.")

    document = parse_text("\n".join(lines))
    report = document.validate_complete()
    assert len(lines) == 31_102
    assert (report["books"], report["chapters"], report["verses"]) == (66, 1_189, 31_102)
    assert report["complete_verse_count"] is True
    assert document.ordered_chapters()[0].verses[0].ref.label() == "Genesis 1:1"
    assert document.ordered_chapters()[-1].verses[-1].ref.label() == "Revelation 22:21"
