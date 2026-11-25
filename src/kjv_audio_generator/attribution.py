from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import SpeechSegment, Verse, VerseRef
from .voices import VoiceRegistry, speaker_slug
from .json_io import write_json_atomic


@dataclass(frozen=True)
class SpeakerRange:
    book: str
    chapter: int
    start_verse: int
    end_verse: int
    speaker_id: str
    priority: int = 0

    def matches(self, ref: VerseRef) -> bool:
        return (ref.book == self.book and ref.chapter == self.chapter
                and self.start_verse <= ref.verse <= self.end_verse)


class AttributionMap:
    """Reviewable speaker ranges and exact per-verse segment overrides.

    Unmapped passages deliberately use the narrator. This class does not claim to infer
    unstated speakers from prose; uncertain quotations remain reviewable.
    """
    def __init__(self, registry: VoiceRegistry, ranges: list[SpeakerRange] | None = None,
                 segment_overrides: dict[str, list[dict[str, str]]] | None = None,
                 seed_review: dict[str, list[str]] | None = None,
                 provenance: dict[str, object] | None = None) -> None:
        self.registry = registry
        self.ranges = ranges or []
        self.segment_overrides = segment_overrides or {}
        self.seed_review = seed_review or {}
        self.provenance = provenance or {}
        for rule in self.ranges:
            registry.get(rule.speaker_id)
        for key, items in self.segment_overrides.items():
            for item in items:
                registry.get(item["speaker_id"])
                if not item.get("text", "").strip():
                    raise ValueError(f"Empty segment override in {key}")

    def segments_for(self, verse: Verse) -> list[SpeechSegment]:
        key = verse.ref.label()
        overrides = self.segment_overrides.get(key)
        if overrides:
            # Saved manual assignments are tied to the exact imported text. If the
            # source Bible was edited after a review, refuse stale splits instead of
            # dropping, duplicating or silently changing any scripture text.
            combined = "".join(item.get("text", "") for item in overrides)
            if combined != verse.text:
                raise ValueError(
                    f"Saved speaker segments for {key} no longer match the imported verse text. "
                    "Review and save this verse again before generating audio."
                )
            return [SpeechSegment(verse.ref, i, speaker_slug(item["speaker_id"]), item["text"])
                    for i, item in enumerate(overrides)]
        if key in self.seed_review:
            speaker = "unknown_speaker" if "unknown_speaker" in self.registry.profiles else "narrator"
            return [SpeechSegment(verse.ref, 0, speaker, verse.text)]
        matches = [r for r in self.ranges if r.matches(verse.ref)]
        matched_speakers = {r.speaker_id for r in matches}
        if len(matched_speakers) > 1:
            speaker = "unknown_speaker" if "unknown_speaker" in self.registry.profiles else "narrator"
        elif matched_speakers:
            speaker = next(iter(matched_speakers))
        else:
            speaker = "narrator"
        self.registry.get(speaker)
        if speaker != "narrator":
            split = self._split_explicit_quoted_speech(verse.text, speaker)
            if split:
                return [
                    SpeechSegment(verse.ref, index, segment_speaker, text)
                    for index, (segment_speaker, text) in enumerate(split)
                ]
        return [SpeechSegment(verse.ref, 0, speaker, verse.text)]

    @staticmethod
    def _split_explicit_quoted_speech(text: str, quoted_speaker: str) -> list[tuple[str, str]] | None:
        """Split explicitly delimited double-quoted dialogue from surrounding narration.

        This is deliberately conservative: it only acts when at least one complete
        straight- or curly-double-quoted span exists in the same verse. It does not
        infer quotation boundaries, identify the speaker, or rewrite unquoted KJV text.
        Whitespace-only text around/between quotes is attached to an adjacent speech
        segment so the exact source text is preserved without creating silent chunks.
        """
        matches = list(re.finditer(r'“[^”]*”|"[^"]*"', text))
        if not matches:
            return None
        pieces: list[tuple[str, str]] = []
        cursor = 0
        pending_prefix = ""
        for match in matches:
            narration = text[cursor:match.start()]
            dialogue = match.group(0)
            if narration:
                if narration.strip():
                    pieces.append(("narrator", pending_prefix + narration))
                    pending_prefix = ""
                elif pieces:
                    speaker, previous = pieces[-1]
                    pieces[-1] = (speaker, previous + narration)
                else:
                    pending_prefix += narration
            if dialogue.strip():
                pieces.append((quoted_speaker, pending_prefix + dialogue))
                pending_prefix = ""
            cursor = match.end()
        trailing = text[cursor:]
        if trailing:
            if trailing.strip():
                pieces.append(("narrator", pending_prefix + trailing))
                pending_prefix = ""
            elif pieces:
                speaker, previous = pieces[-1]
                pieces[-1] = (speaker, previous + trailing)
            else:
                pending_prefix += trailing
        if pending_prefix:
            if pieces:
                speaker, previous = pieces[-1]
                pieces[-1] = (speaker, previous + pending_prefix)
            else:
                pieces.append((quoted_speaker, pending_prefix))
        if len(pieces) < 2:
            return None
        return pieces

    def save(self, path: str | Path) -> None:
        payload = {
            "schema_version": 1,
            "ranges": [{"book":r.book,"chapter":r.chapter,"start_verse":r.start_verse,
                        "end_verse":r.end_verse,"speaker_id":r.speaker_id,"priority":r.priority} for r in self.ranges],
            "segment_overrides": self.segment_overrides,
            "seed_review": self.seed_review,
            "provenance": self.provenance,
        }
        write_json_atomic(path, payload)

    @classmethod
    def load(cls, path: str | Path, registry: VoiceRegistry) -> "AttributionMap":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if data.get("schema_version") != 1:
            raise ValueError("Unsupported speaker assignment schema")
        from .books import canonical_book
        ranges = [SpeakerRange(canonical_book(x["book"]), int(x["chapter"]), int(x["start_verse"]),
                               int(x["end_verse"]), speaker_slug(x["speaker_id"]), int(x.get("priority",0)))
                  for x in data.get("ranges", [])]
        return cls(registry, ranges, data.get("segment_overrides", {}),
                   data.get("seed_review", {}), data.get("provenance", {}))
