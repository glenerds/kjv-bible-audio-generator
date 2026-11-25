from __future__ import annotations

import copy
import csv
import hashlib
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

from .attribution import AttributionMap, SpeakerRange
from .books import BOOKS, book_sort_key, canonical_book
from .parser import _USFM_BOOKS
from .json_io import write_json_atomic
from .voices import VoiceProfile, VoiceRegistry, speaker_slug


@dataclass(frozen=True)
class SeedReport:
    source_rows: int
    suggested_ranges: int
    uniquely_mapped_verses: int
    ambiguous_verses: int
    skipped_cross_chapter_rows: int
    skipped_invalid_rows: int
    speakers_found: int
    profiles_created: int
    source_is_kjv_specific: bool = False
    requires_review: bool = True

    def to_dict(self) -> dict[str, object]:
        return {
            "source_rows": self.source_rows,
            "suggested_ranges": self.suggested_ranges,
            "uniquely_mapped_verses": self.uniquely_mapped_verses,
            "ambiguous_verses": self.ambiguous_verses,
            "skipped_cross_chapter_rows": self.skipped_cross_chapter_rows,
            "skipped_invalid_rows": self.skipped_invalid_rows,
            "speakers_found": self.speakers_found,
            "profiles_created": self.profiles_created,
            "source_is_kjv_specific": self.source_is_kjv_specific,
            "requires_review": self.requires_review,
        }


def _ref(value: str) -> tuple[str, int, int]:
    match = re.fullmatch(r"\s*([A-Za-z0-9]{3})\s+(\d{1,3}):(\d{1,3})\s*", value)
    if not match:
        raise ValueError(f"Invalid speaker reference: {value!r}")
    code, chapter, verse = match.group(1).upper(), int(match.group(2)), int(match.group(3))
    book = _USFM_BOOKS.get(code)
    if book is None:
        book = canonical_book(code)
    from .models import VerseRef
    ref = VerseRef(book, chapter, verse)
    return ref.book, ref.chapter, ref.verse


def _canonical_speaker_id(label: str, registry: VoiceRegistry) -> str:
    """Map upstream speaker labels to persistent Bible character identities.

    The MACULA seed has book-specific narrator labels (for example narrator-GEN
    and narrator-JHN). Those are not separate characters: every such label must
    use the single Bible Narrator profile. The childhood Jesus label is likewise
    unified with the canonical Jesus identity rather than creating a second voice.
    Other compound/ambiguous names are intentionally not collapsed.
    """
    cleaned = label.strip()
    folded = cleaned.casefold()
    if folded.startswith("narrator-"):
        return registry.get("narrator").speaker_id
    if folded == "jesus (child)":
        return registry.get("jesus").speaker_id
    # Slash-combined labels (for example God/Jeremiah or God/Jesus) describe
    # unresolved/overlapping speaker attribution, not a literal compound person.
    # Keep those passages on the unknown profile and mark their verses for review.
    if "/" in cleaned and "unknown_speaker" in registry.profiles:
        return registry.get("unknown_speaker").speaker_id
    return registry.resolve_alias(cleaned) or speaker_slug(cleaned)


def _voice_description(name: str, gender: str, age: str, divinity: str) -> str:
    age_key = age.casefold()
    gender_key = gender.casefold()
    if "female" in gender_key:
        gender_phrase = "female"
        qualities = ["clear warm mezzo tone", "bright articulate upper register", "soft grounded alto tone", "resonant steady mid register"]
    elif "male" in gender_key:
        gender_phrase = "male"
        qualities = ["warm low-mid register", "clear resonant baritone", "steady mid register", "slightly bright articulate tenor"]
    else:
        gender_phrase = "androgynous, natural"
        qualities = ["clear warm mid register", "bright articulate tone", "soft grounded tone", "resonant steady register"]
    if "child" in age_key:
        age_phrase = "child"
    elif "young" in age_key or "teen" in age_key:
        age_phrase = "young adult"
    elif "elder" in age_key or "old" in age_key:
        age_phrase = "older adult"
    else:
        age_phrase = "adult"
    variant = int(hashlib.sha256(name.casefold().encode("utf-8")).hexdigest()[:8], 16) % len(qualities)
    role = "stately and dignified" if divinity.strip().casefold() in {"y", "yes", "true"} else "expressive but natural"
    return (
        f"A distinctive {gender_phrase} {age_phrase} voice for the Bible character {name}; "
        f"{qualities[variant]}, {role}, clear pronunciation of King James English, "
        "measured conversational delivery, consistent vocal identity, no exaggerated acting."
    )


def import_clear_speaker_seed(
    projections_path: str | Path,
    details_path: str | Path | None,
    registry: VoiceRegistry,
) -> tuple[AttributionMap, SeedReport, dict[str, object]]:
    """Import Clear/MACULA speaker projections as non-authoritative review suggestions.

    The Clear consensus projections are not KJV-specific and only provide verse-level
    ranges. If a verse has conflicting primary/alternate speakers, it is flagged for
    review and uses the neutral unknown-speaker voice until corrected.
    """
    projections_path = Path(projections_path)
    if not projections_path.is_file():
        raise FileNotFoundError(projections_path)
    details: dict[str, dict[str, str]] = {}
    if details_path:
        detail_file = Path(details_path)
        if not detail_file.is_file():
            raise FileNotFoundError(detail_file)
        with detail_file.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle, delimiter="\t"):
                name = (row.get("CharacterID") or "").strip()
                if name:
                    details[name.casefold()] = row

    candidates: dict[tuple[str, int, int], set[str]] = defaultdict(set)
    labels: dict[tuple[str, int, int], str] = {}
    forced_review: set[tuple[str, int, int]] = set()
    source_rows = 0
    skipped_cross = 0
    skipped_invalid = 0
    names: set[str] = set()
    with projections_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        required = {"START VS", "END VS", "SPEAKER (FCBH)", "ALT SPEAKER (FCBH)"}
        if not required.issubset(set(reader.fieldnames or [])):
            raise ValueError("Speaker projection TSV is missing required MACULA columns")
        for row in reader:
            source_rows += 1
            speaker = (row.get("SPEAKER (FCBH)") or "").strip()
            alternate = (row.get("ALT SPEAKER (FCBH)") or "").strip()
            try:
                start = _ref(row.get("START VS") or "")
                end = _ref(row.get("END VS") or "")
            except ValueError:
                skipped_invalid += 1
                continue
            if speaker:
                names.add(speaker)
            if alternate:
                names.add(alternate)
            if not speaker or start[0] != end[0] or start[1] != end[1]:
                skipped_cross += 1
                continue
            if end[2] < start[2]:
                skipped_invalid += 1
                continue
            primary_id = _canonical_speaker_id(speaker, registry)
            alternate_id = _canonical_speaker_id(alternate, registry) if alternate else None
            for verse_number in range(start[2], end[2] + 1):
                key = (start[0], start[1], verse_number)
                candidates[key].add(primary_id)
                if alternate_id:
                    candidates[key].add(alternate_id)
                if "/" in speaker or (alternate and "/" in alternate):
                    forced_review.add(key)
                labels[key] = f"{start[0]} {start[1]}:{verse_number}"

    before = set(registry.profiles)
    for name in sorted(names, key=str.casefold):
        speaker_id = _canonical_speaker_id(name, registry)
        if speaker_id in registry.profiles:
            continue
        detail = details.get(name.casefold(), {})
        profile = VoiceProfile(
            speaker_id=speaker_id,
            display_name=name,
            aliases=[],
            voice_description=_voice_description(name, detail.get("Gender", ""), detail.get("Age", ""), detail.get("Divinty", "")),
            status="needs_review",
        )
        registry.add(profile)

    by_speaker: dict[tuple[str, int, str], list[int]] = defaultdict(list)
    review: dict[str, list[str]] = {}
    unique_count = 0
    for key, speaker_ids in candidates.items():
        label = labels[key]
        if len(speaker_ids) != 1 or key in forced_review:
            review[label] = sorted(speaker_ids)
            continue
        speaker_id = next(iter(speaker_ids))
        by_speaker[(key[0], key[1], speaker_id)].append(key[2])
        unique_count += 1

    ranges: list[SpeakerRange] = []
    for (book, chapter, speaker_id), verse_numbers in by_speaker.items():
        ordered = sorted(set(verse_numbers))
        if not ordered:
            continue
        start = previous = ordered[0]
        for number in ordered[1:]:
            if number != previous + 1:
                ranges.append(SpeakerRange(book, chapter, start, previous, speaker_id, priority=10))
                start = number
            previous = number
        ranges.append(SpeakerRange(book, chapter, start, previous, speaker_id, priority=10))
    ranges.sort(key=lambda rule: (book_sort_key(rule.book), rule.chapter, rule.start_verse, rule.speaker_id))

    provenance = {
        "dataset": "MACULA Quotation and Speaker Data — Clear aligned projections",
        "source_url": "https://github.com/Clear-Bible/speaker-quotations/",
        "source_is_kjv_specific": False,
        "review_required": True,
        "note": "Translation-derived, verse-level speaker suggestions only. Conflicts and cross-chapter rows are not auto-applied; verify against the imported KJV text.",
        "license": "CC BY 4.0; includes FCBH/Glyssen character detail licensed under MIT; preserve upstream notices.",
        "projections_sha256": _sha256_file(projections_path),
        "details_sha256": _sha256_file(details_path) if details_path else None,
    }
    provenance["source_fingerprint"] = hashlib.sha256(
        json.dumps({k: provenance[k] for k in ("dataset", "projections_sha256", "details_sha256")}, sort_keys=True).encode("utf-8")
    ).hexdigest()
    attribution = AttributionMap(registry, ranges, seed_review=review, provenance=provenance)
    report = SeedReport(
        source_rows=source_rows,
        suggested_ranges=len(ranges),
        uniquely_mapped_verses=unique_count,
        ambiguous_verses=len(review),
        skipped_cross_chapter_rows=skipped_cross,
        skipped_invalid_rows=skipped_invalid,
        speakers_found=len(names),
        profiles_created=len(set(registry.profiles) - before),
    )
    return attribution, report, {
        "ambiguous_verse_candidates": review,
        "source": attribution.provenance,
        "summary": report.to_dict(),
    }


def _sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def merge_seed_suggestions(existing: AttributionMap | None, incoming: AttributionMap) -> tuple[AttributionMap, dict[str, int]]:
    """Merge imported suggestions without discarding reviewed user work.

    Manual segment overrides always win. Each suggestion source is tracked
    separately so re-importing that source replaces only its previous ranges,
    while ranges from other sources and any untracked user-authored ranges remain.
    Overlapping speakers are added to the review queue and resolve to the neutral
    unknown-speaker voice until a person adjudicates them.
    """
    if existing is None:
        return incoming, {
            "preserved_manual_overrides": 0,
            "preserved_existing_ranges": 0,
            "merged_ranges": len(incoming.ranges),
            "review_candidates": len(incoming.seed_review),
        }

    incoming_record = copy.deepcopy(incoming.provenance)
    source_name = str(incoming_record.get("dataset") or "unknown dataset")
    provenance = dict(existing.provenance)
    suggestion_sources = provenance.get("suggestion_sources", {})
    if not isinstance(suggestion_sources, dict):
        suggestion_sources = {}
    suggestion_sources = copy.deepcopy(suggestion_sources)

    # Remove only ranges previously recorded as imported from this same source.
    # For older databases that predate source tracking, the legacy dataset marker
    # is the only available ownership clue; manual segment overrides are separate
    # and are always preserved below.
    owned_records = suggestion_sources.get(source_name)
    if isinstance(owned_records, list):
        owned_keys = {
            (str(x.get("book")), int(x.get("chapter", 0)), int(x.get("start_verse", 0)),
             int(x.get("end_verse", 0)), str(x.get("speaker_id")), int(x.get("priority", 0)))
            for x in owned_records if isinstance(x, dict)
        }
        base_ranges = [rule for rule in existing.ranges if _speaker_range_key(rule) not in owned_keys]
    elif existing.provenance.get("dataset") == source_name:
        # Compatibility path for pre-0.4.6 imported seed maps.
        base_ranges = []
    else:
        base_ranges = list(existing.ranges)

    incoming_records = [_speaker_range_record(rule) for rule in incoming.ranges]
    suggestion_sources[source_name] = incoming_records

    unique: dict[tuple[str, int, int, int, str, int], SpeakerRange] = {}
    for rule in [*base_ranges, *incoming.ranges]:
        unique[_speaker_range_key(rule)] = rule
    ranges = list(unique.values())
    ranges.sort(key=lambda rule: (book_sort_key(rule.book), rule.chapter, rule.start_verse,
                                  rule.end_verse, rule.speaker_id, rule.priority))

    review: dict[str, list[str]] = {
        key: sorted(set(values)) for key, values in existing.seed_review.items()
    }
    for key, values in incoming.seed_review.items():
        review[key] = sorted(set(review.get(key, [])) | set(values))

    # Existing, text-verified edits are authoritative. Importers do not produce
    # manual segment overrides, and must never replace a prior manual edit.
    overrides = copy.deepcopy(existing.segment_overrides)

    # Different data sources can overlap the same verse. Make those conflicts
    # explicit in the review UI, except where a human has already saved an exact
    # override for that verse.
    by_verse: dict[tuple[str, int, int], set[str]] = defaultdict(set)
    for rule in ranges:
        for verse_number in range(rule.start_verse, rule.end_verse + 1):
            by_verse[(rule.book, rule.chapter, verse_number)].add(rule.speaker_id)
    for (book, chapter, verse_number), speaker_ids in by_verse.items():
        if len(speaker_ids) > 1:
            label = f"{book} {chapter}:{verse_number}"
            if label not in overrides:
                review[label] = sorted(set(review.get(label, [])) | speaker_ids)

    previous_history = provenance.get("import_history", [])
    history = list(previous_history) if isinstance(previous_history, list) else []
    fingerprint = incoming_record.get("source_fingerprint")
    if not any(isinstance(item, dict) and item.get("source_fingerprint") == fingerprint for item in history):
        history.append(incoming_record)

    provenance.update(incoming_record)
    provenance["import_history"] = history
    provenance["suggestion_sources"] = suggestion_sources
    provenance["last_import_source_fingerprint"] = fingerprint

    merged = AttributionMap(
        existing.registry,
        ranges=ranges,
        segment_overrides=overrides,
        seed_review=review,
        provenance=provenance,
    )
    return merged, {
        "preserved_manual_overrides": len(overrides),
        "preserved_existing_ranges": len(base_ranges),
        "merged_ranges": len(ranges),
        "review_candidates": len(review),
    }


def _speaker_range_key(rule: SpeakerRange) -> tuple[str, int, int, int, str, int]:
    return (rule.book, rule.chapter, rule.start_verse, rule.end_verse, rule.speaker_id, rule.priority)


def _speaker_range_record(rule: SpeakerRange) -> dict[str, object]:
    return {
        "book": rule.book,
        "chapter": rule.chapter,
        "start_verse": rule.start_verse,
        "end_verse": rule.end_verse,
        "speaker_id": rule.speaker_id,
        "priority": rule.priority,
    }


def load_or_seed_attribution(output_root: str | Path, runtime_data_root: str | Path, registry: VoiceRegistry) -> AttributionMap:
    """Load saved assignments or auto-seed them from data bundled with the application."""
    output_root = Path(output_root)
    metadata = output_root / "metadata"
    assignments_path = metadata / "speaker_assignments.json"
    registry_path = metadata / "voice_registry.json"
    if assignments_path.is_file():
        return AttributionMap.load(assignments_path, registry)
    source_dir = Path(runtime_data_root) / "data" / "speaker-attribution"
    projections = source_dir / "Clear-Aligned-Projections.tsv"
    details = source_dir / "character_detail.semantic_data.tsv"
    if projections.is_file() and details.is_file():
        attribution, report, review = import_clear_speaker_seed(projections, details, registry)
        metadata.mkdir(parents=True, exist_ok=True)
        registry.save(registry_path)
        attribution.save(assignments_path)
        write_json_atomic(metadata / "speaker_seed_review.json", review)
    else:
        attribution = AttributionMap(registry)
    return attribution
