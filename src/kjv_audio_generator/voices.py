from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .json_io import write_json_atomic


def speaker_slug(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")
    if not value:
        raise ValueError("Speaker ID must contain letters or numbers")
    return value


@dataclass
class VoiceProfile:
    speaker_id: str
    display_name: str
    aliases: list[str]
    voice_description: str
    reference_text: str = "I will speak clearly and naturally, with a steady and expressive reading voice."
    reference_audio: str | None = None
    prompt_asset: str | None = None
    status: str = "not_prepared"

    def __post_init__(self) -> None:
        self.speaker_id = speaker_slug(self.speaker_id)
        self.display_name = self.display_name.strip() or self.speaker_id.replace("_", " ").title()
        self.aliases = sorted({a.strip() for a in self.aliases if a and a.strip()}, key=str.casefold)
        if not self.voice_description.strip():
            raise ValueError(f"Voice description is required for {self.speaker_id}")
        if self.status not in {"not_prepared", "prepared", "needs_review"}:
            raise ValueError(f"Invalid voice profile status: {self.status}")


class VoiceRegistry:
    def __init__(self, profiles: list[VoiceProfile] | None = None) -> None:
        self.profiles: dict[str, VoiceProfile] = {}
        for profile in profiles or []:
            self.add(profile)

    def add(self, profile: VoiceProfile, *, replace: bool = False) -> None:
        key = speaker_slug(profile.speaker_id)
        if key in self.profiles and not replace:
            raise ValueError(f"Duplicate speaker ID: {key}")
        self.profiles[key] = profile

    def get(self, speaker_id: str) -> VoiceProfile:
        key = speaker_slug(speaker_id)
        try:
            return self.profiles[key]
        except KeyError as exc:
            raise KeyError(f"No voice profile exists for speaker '{key}'") from exc

    def resolve_alias(self, name: str) -> str | None:
        normalized = re.sub(r"\s+", " ", name.strip().casefold())
        for profile in self.profiles.values():
            if normalized == profile.display_name.casefold() or normalized == profile.speaker_id.replace("_", " "):
                return profile.speaker_id
            if any(normalized == alias.casefold() for alias in profile.aliases):
                return profile.speaker_id
        return None

    def to_dict(self) -> dict[str, Any]:
        return {"schema_version": 1, "profiles": [asdict(p) for p in sorted(self.profiles.values(), key=lambda p:p.speaker_id)]}

    def save(self, path: str | Path) -> None:
        write_json_atomic(path, self.to_dict())

    @classmethod
    def load(cls, path: str | Path) -> "VoiceRegistry":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if data.get("schema_version") != 1 or not isinstance(data.get("profiles"), list):
            raise ValueError("Unsupported voice registry schema")
        return cls([VoiceProfile(**item) for item in data["profiles"]])

    @classmethod
    def defaults(cls) -> "VoiceRegistry":
        return cls([
            VoiceProfile("narrator", "Bible Narrator", ["narrator", "reader"],
                         "Mature, warm, clear, measured male narrator; calm and reverent, articulate King James English, consistent timbre."),
            VoiceProfile("unknown_speaker", "Unassigned Speaker", ["unknown", "unassigned"],
                         "Neutral clear supporting voice; use only when a quotation speaker has not been identified."),
            VoiceProfile("god", "God", ["the LORD", "the Lord God", "Almighty"],
                         "Deep, resonant, dignified mature male voice; calm authority, controlled warmth, never harsh or theatrical."),
            VoiceProfile("jesus", "Jesus", ["Christ", "the Son", "the Son of man", "the Lord Jesus"],
                         "Warm, compassionate adult male voice; clear, grounded, gentle authority, thoughtful pauses."),
            VoiceProfile("moses", "Moses", ["Moses the servant of the LORD"],
                         "Mature male voice, weathered and thoughtful, steady low-mid register, measured delivery."),
        ])
