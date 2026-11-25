from __future__ import annotations

import re

# Canonical Protestant KJV order and chapter counts.
BOOKS: tuple[tuple[str, int], ...] = (
    ("Genesis", 50), ("Exodus", 40), ("Leviticus", 27), ("Numbers", 36), ("Deuteronomy", 34),
    ("Joshua", 24), ("Judges", 21), ("Ruth", 4), ("1 Samuel", 31), ("2 Samuel", 24),
    ("1 Kings", 22), ("2 Kings", 25), ("1 Chronicles", 29), ("2 Chronicles", 36),
    ("Ezra", 10), ("Nehemiah", 13), ("Esther", 10), ("Job", 42), ("Psalms", 150),
    ("Proverbs", 31), ("Ecclesiastes", 12), ("Song of Solomon", 8), ("Isaiah", 66),
    ("Jeremiah", 52), ("Lamentations", 5), ("Ezekiel", 48), ("Daniel", 12),
    ("Hosea", 14), ("Joel", 3), ("Amos", 9), ("Obadiah", 1), ("Jonah", 4),
    ("Micah", 7), ("Nahum", 3), ("Habakkuk", 3), ("Zephaniah", 3), ("Haggai", 2),
    ("Zechariah", 14), ("Malachi", 4), ("Matthew", 28), ("Mark", 16), ("Luke", 24),
    ("John", 21), ("Acts", 28), ("Romans", 16), ("1 Corinthians", 16),
    ("2 Corinthians", 13), ("Galatians", 6), ("Ephesians", 6), ("Philippians", 4),
    ("Colossians", 4), ("1 Thessalonians", 5), ("2 Thessalonians", 3),
    ("1 Timothy", 6), ("2 Timothy", 4), ("Titus", 3), ("Philemon", 1),
    ("Hebrews", 13), ("James", 5), ("1 Peter", 5), ("2 Peter", 3),
    ("1 John", 5), ("2 John", 1), ("3 John", 1), ("Jude", 1), ("Revelation", 22),
)
CHAPTER_COUNTS = dict(BOOKS)
TOTAL_CHAPTERS = sum(n for _, n in BOOKS)


def _key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold())

_ALIASES: dict[str, str] = {}
for _name, _count in BOOKS:
    _ALIASES[_key(_name)] = _name
    _ALIASES[_key(_name.replace(" ", ""))] = _name

# Common book aliases and USFM identifiers.
_EXTRA = {
    "gen": "Genesis", "ge": "Genesis", "exod": "Exodus", "exo": "Exodus", "lev": "Leviticus",
    "num": "Numbers", "deut": "Deuteronomy", "josh": "Joshua", "judg": "Judges", "jdg": "Judges",
    "ps": "Psalms", "psa": "Psalms", "prov": "Proverbs", "eccl": "Ecclesiastes", "song": "Song of Solomon",
    "sos": "Song of Solomon", "mt": "Matthew", "mat": "Matthew", "mk": "Mark", "mrk": "Mark",
    "lk": "Luke", "luk": "Luke", "jn": "John", "jhn": "John", "ac": "Acts", "act": "Acts",
    "rom": "Romans", "1sam": "1 Samuel", "2sam": "2 Samuel", "1kgs": "1 Kings", "2kgs": "2 Kings",
    "1chr": "1 Chronicles", "2chr": "2 Chronicles", "1cor": "1 Corinthians", "2cor": "2 Corinthians",
    "1thess": "1 Thessalonians", "2thess": "2 Thessalonians", "1tim": "1 Timothy", "2tim": "2 Timothy",
    "1pet": "1 Peter", "2pet": "2 Peter", "1jn": "1 John", "2jn": "2 John", "3jn": "3 John",
    "rev": "Revelation", "re": "Revelation", "apoc": "Revelation", "phlm": "Philemon",
}
_ALIASES.update({_key(k): v for k, v in _EXTRA.items()})


def canonical_book(value: str) -> str:
    cleaned = value.strip().replace("_", " ")
    result = _ALIASES.get(_key(cleaned))
    if not result:
        raise ValueError(f"Unknown Bible book name: {value!r}")
    return result


def book_sort_key(book: str) -> int:
    name = canonical_book(book)
    return next(i for i, (candidate, _) in enumerate(BOOKS) if candidate == name)


def validate_chapter(book: str, chapter: int) -> None:
    name = canonical_book(book)
    if not isinstance(chapter, int) or chapter < 1 or chapter > CHAPTER_COUNTS[name]:
        raise ValueError(f"Invalid chapter {chapter} for {name}; expected 1–{CHAPTER_COUNTS[name]}")
