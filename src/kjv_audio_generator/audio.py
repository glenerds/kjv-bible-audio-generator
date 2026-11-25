from __future__ import annotations

import json
import hashlib
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Iterable

import numpy as np
import soundfile as sf

from .json_io import copy_file_atomic, write_json_atomic
from .models import SpeechSegment


class AudioEncodingError(RuntimeError):
    pass


def find_ffmpeg(explicit: str | Path | None = None) -> str:
    candidate = str(explicit) if explicit else shutil.which("ffmpeg")
    if not candidate or not Path(candidate).is_file():
        raise AudioEncodingError("FFmpeg executable was not found. Bundle ffmpeg.exe with the Windows application.")
    return candidate


def _resample(data: np.ndarray, old_rate: int, new_rate: int) -> np.ndarray:
    if old_rate == new_rate:
        return data.astype(np.float32, copy=False)
    new_len = max(1, round(len(data) * new_rate / old_rate))
    old_x = np.linspace(0.0, 1.0, num=len(data), endpoint=False)
    new_x = np.linspace(0.0, 1.0, num=new_len, endpoint=False)
    return np.interp(new_x, old_x, data).astype(np.float32)


class ChapterAudioAssembler:
    def __init__(self, output_root: str | Path, ffmpeg: str | Path | None = None,
                 bitrate_kbps: int = 96, target_sample_rate: int = 24000, gap_ms: int = 120) -> None:
        if bitrate_kbps not in {64, 80, 96, 112, 128, 160, 192}:
            raise ValueError("Unsupported MP3 bitrate")
        self.output_root = Path(output_root)
        self.ffmpeg = find_ffmpeg(ffmpeg)
        self.bitrate_kbps = bitrate_kbps
        self.target_sample_rate = target_sample_rate
        self.gap_samples = max(0, target_sample_rate * gap_ms // 1000)

    def generation_fingerprint(self) -> str:
        """Fingerprint the encoder executable and fixed assembly pipeline."""
        executable = Path(self.ffmpeg)
        digest = hashlib.sha256()
        with executable.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        payload = {
            "ffmpeg_sha256": digest.hexdigest(),
            "bitrate_kbps": self.bitrate_kbps,
            "target_sample_rate": self.target_sample_rate,
            "gap_samples": self.gap_samples,
            "channels": 1,
            "sample_format": "PCM_16",
            "encoder": "libmp3lame",
            "normalization": "loudnorm=I=-18:TP=-1.5:LRA=11",
            "resampler": "linear-v1",
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

    def write_chapter(self, book: str, chapter: int, segments: list[SpeechSegment],
                      waveforms: list[tuple[np.ndarray, int]]) -> tuple[Path, Path]:
        if not segments or len(segments) != len(waveforms):
            raise ValueError("A chapter requires one generated waveform for each speech segment")
        book_dir = self.output_root / book
        meta_dir = self.output_root / "metadata" / "verse_timestamps"
        book_dir.mkdir(parents=True, exist_ok=True); meta_dir.mkdir(parents=True, exist_ok=True)
        stem = f"{book.replace(' ', '_')}_{chapter:03d}"
        output = book_dir / f"{stem}.mp3"
        cues_path = meta_dir / f"{stem}.json"
        target_parts: list[np.ndarray] = []
        cues: list[dict[str, object]] = []
        cursor = 0
        for index, (segment, (samples, sample_rate)) in enumerate(zip(segments, waveforms)):
            audio = _resample(np.asarray(samples, dtype=np.float32).reshape(-1), int(sample_rate), self.target_sample_rate)
            if audio.size == 0 or not np.isfinite(audio).all():
                raise AudioEncodingError(f"Invalid audio segment for {segment.ref.label()}")
            peak = float(np.max(np.abs(audio)))
            if peak > 0.999:
                audio = audio * (0.95 / peak)
            start = cursor / self.target_sample_rate
            target_parts.append(audio)
            cursor += len(audio)
            end = cursor / self.target_sample_rate
            cues.append({"reference": segment.ref.label(), "segment": segment.index,
                         "speaker_id": segment.speaker_id, "text": segment.text,
                         "start_seconds": round(start, 3), "end_seconds": round(end, 3)})
            if index < len(segments) - 1 and self.gap_samples:
                target_parts.append(np.zeros(self.gap_samples, dtype=np.float32))
                cursor += self.gap_samples
        combined = np.concatenate(target_parts)
        with tempfile.TemporaryDirectory(prefix="kjv_audio_") as temp_dir:
            wav_path = Path(temp_dir) / "chapter.wav"
            tmp_mp3 = Path(temp_dir) / "chapter.tmp.mp3"
            sf.write(str(wav_path), combined, self.target_sample_rate, subtype="PCM_16")
            command = [self.ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(wav_path),
                       "-vn", "-ac", "1", "-af", "loudnorm=I=-18:TP=-1.5:LRA=11", "-b:a", f"{self.bitrate_kbps}k", "-codec:a", "libmp3lame", str(tmp_mp3)]
            completed = subprocess.run(command, capture_output=True, text=True, timeout=180)
            if completed.returncode != 0 or not tmp_mp3.is_file() or tmp_mp3.stat().st_size < 512:
                raise AudioEncodingError(f"MP3 encoding failed: {completed.stderr[-1200:]}")
            verify = subprocess.run([self.ffmpeg, "-hide_banner", "-loglevel", "error", "-i", str(tmp_mp3),
                                     "-f", "null", "-"], capture_output=True, text=True, timeout=120)
            if verify.returncode != 0:
                raise AudioEncodingError(f"Generated MP3 did not decode: {verify.stderr[-1200:]}")
            copy_file_atomic(tmp_mp3, output)
        cue_payload = {"schema_version": 1, "book": book, "chapter": chapter,
                       "sample_rate": self.target_sample_rate, "bitrate_kbps": self.bitrate_kbps,
                       "duration_seconds": round(len(combined) / self.target_sample_rate, 3),
                       "segments": cues}
        write_json_atomic(cues_path, cue_payload)
        return output, cues_path
