from __future__ import annotations

from .models import VerseRef
from .voices import VoiceRegistry, speaker_slug


def format_segments_for_editor(segments: list[tuple[str, str]]) -> str:
    """Render exact verse segments as one speaker-id<TAB>text line each."""
    return "\n".join(f"{speaker}\t{text}" for speaker, text in segments)


def parse_segments_from_editor(
    content: str,
    *,
    verse_ref: VerseRef,
    original_text: str,
    registry: VoiceRegistry,
) -> list[dict[str, str]]:
    """Validate a user-edited verse split without allowing text to be lost or altered."""
    rows: list[dict[str, str]] = []
    for line_number, line in enumerate(content.splitlines(), start=1):
        if not line:
            continue
        if "\t" not in line:
            raise ValueError(
                f"Line {line_number} must contain a speaker ID, a tab, then the exact text segment."
            )
        speaker_id_raw, segment_text = line.split("\t", 1)
        if not speaker_id_raw.strip():
            raise ValueError(f"Line {line_number} has no speaker ID.")
        if not segment_text:
            raise ValueError(f"Line {line_number} has an empty text segment.")
        speaker_id = speaker_slug(speaker_id_raw.strip())
        try:
            registry.get(speaker_id)
        except KeyError as exc:
            raise ValueError(
                f"Line {line_number} refers to unknown speaker '{speaker_id}'. Create the voice profile first."
            ) from exc
        rows.append({"speaker_id": speaker_id, "text": segment_text})

    if not rows:
        raise ValueError(f"No speech segments were entered for {verse_ref.label()}.")
    combined = "".join(item["text"] for item in rows)
    if combined != original_text:
        raise ValueError(
            f"The segment text must reproduce {verse_ref.label()} exactly, including spaces and punctuation. "
            f"Original length: {len(original_text)}; combined segments: {len(combined)}."
        )
    return rows
