from __future__ import annotations

import gc
import hashlib
import importlib
import json
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol

import numpy as np

from .voices import VoiceProfile
from .json_io import atomic_output_path, write_json_atomic


class SpeechBackend(Protocol):
    def prepare_profiles(
        self,
        profiles: list[VoiceProfile],
        *,
        control_check: Callable[[], None] | None = None,
        progress_callback: Callable[[str, int, int, str], None] | None = None,
    ) -> None: ...

    def synthesize(self, text: str, profile: VoiceProfile) -> tuple[np.ndarray, int]: ...


class QwenRuntimeUnavailable(RuntimeError):
    pass


@dataclass
class QwenSettings:
    voice_design_model: Path
    base_model: Path
    device: str = "cpu"
    language: str = "English"


class QwenVoiceBackend:
    fingerprint_name = "qwen3-tts-12hz-1.7b"
    fingerprint_version = "qwen-tts-0.1.1-icl-reftext-prompt-v2"
    """Qwen3-TTS VoiceDesign -> Base voice-clone adapter.

    A saved speaker reference waveform and reusable Base-model prompt are retained per
    stable speaker ID. The prompt cache is invalidated when voice instructions, reference
    text or a supplied reference waveform changes.
    """

    def __init__(self, settings: QwenSettings, profile_dir: str | Path) -> None:
        self.settings = settings
        self.profile_dir = Path(profile_dir)
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self._torch: Any = None
        self._soundfile: Any = None
        self._design_model: Any = None
        self._base_model: Any = None
        # Keep only a small working set of prepared prompts in RAM. A complete
        # Bible can reference hundreds of speakers; loading every prompt at once
        # would make RAM usage grow with the character count.
        self._prompt_cache: OrderedDict[str, Any] = OrderedDict()
        self._prompt_cache_limit = 8

    # Official Qwen3-TTS 12 Hz 1.7B folders contain the speech tokenizer as a
    # nested subfolder. Checking only that a directory is non-empty is not enough:
    # a partial model download could otherwise pass preflight and fail much later.
    _REQUIRED_MODEL_FILES = (
        "config.json",
        "generation_config.json",
        "model.safetensors",
        "tokenizer_config.json",
        "vocab.json",
        "merges.txt",
        "preprocessor_config.json",
        "speech_tokenizer/config.json",
        "speech_tokenizer/configuration.json",
        "speech_tokenizer/model.safetensors",
        "speech_tokenizer/preprocessor_config.json",
    )

    @classmethod
    def _require_directory(cls, path: Path, label: str) -> None:
        if not path.is_dir():
            raise QwenRuntimeUnavailable(f"{label} model folder is missing: {path}")
        missing = [relative for relative in cls._REQUIRED_MODEL_FILES if not (path / relative).is_file()]
        if missing:
            details = ", ".join(missing)
            raise QwenRuntimeUnavailable(
                f"{label} model folder is incomplete: {path}. Missing required Qwen files: {details}"
            )
        size_checks = {
            "model.safetensors": 3_500_000_000,
            "speech_tokenizer/model.safetensors": 650_000_000,
        }
        undersized = [
            f"{relative} ({(path / relative).stat().st_size:,} bytes; expected at least {minimum:,})"
            for relative, minimum in size_checks.items()
            if (path / relative).stat().st_size < minimum
        ]
        if undersized:
            raise QwenRuntimeUnavailable(
                f"{label} model files are too small to be the official 1.7B Qwen snapshot: "
                + "; ".join(undersized)
            )
        try:
            config = json.loads((path / "config.json").read_text(encoding="utf-8"))
            tokenizer_config = json.loads(
                (path / "speech_tokenizer" / "config.json").read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError) as exc:
            raise QwenRuntimeUnavailable(f"{label} model configuration is not valid JSON: {path}") from exc
        if config.get("model_type") != "qwen3_tts" or config.get("tokenizer_type") != "qwen3_tts_tokenizer_12hz":
            raise QwenRuntimeUnavailable(f"{label} folder is not an official Qwen3-TTS 12 Hz model: {path}")
        expected_model_type = {"VoiceDesign": "voice_design", "Base": "base"}.get(label)
        if expected_model_type and config.get("tts_model_type") != expected_model_type:
            raise QwenRuntimeUnavailable(
                f"{label} folder contains the wrong Qwen TTS model type: {config.get('tts_model_type')!r}"
            )
        if tokenizer_config.get("model_type") != "qwen3_tts_tokenizer_12hz":
            raise QwenRuntimeUnavailable(f"{label} speech tokenizer config is not Qwen3-TTS 12 Hz: {path}")

    def _imports(self) -> None:
        try:
            self._torch = importlib.import_module("torch")
            self._soundfile = importlib.import_module("soundfile")
            qwen_module = importlib.import_module("qwen_tts")
            if not callable(getattr(qwen_module, "Qwen3TTSModel", None)):
                raise ImportError("qwen_tts does not expose the required Qwen3TTSModel API")
        except Exception as exc:
            raise QwenRuntimeUnavailable(
                "Qwen runtime is unavailable. The bundled qwen-tts, PyTorch and soundfile packages must be installed."
            ) from exc

    def _load_model(self, model_path: Path) -> Any:
        from qwen_tts import Qwen3TTSModel  # type: ignore

        device = self.settings.device
        if device == "auto":
            device = "cuda:0" if self._torch.cuda.is_available() else "cpu"
        # The official 1.7B checkpoints are stored as BF16. On CPU, keep the
        # checkpoint precision instead of expanding all weights to float32;
        # this roughly halves the resident weight memory. Older CPUs may run
        # BF16 through software emulation, so actual inference/performance still
        # has to be measured on the target Windows hardware.
        dtype = "auto" if device == "cpu" else self._torch.float16
        return Qwen3TTSModel.from_pretrained(str(model_path), device_map=device, dtype=dtype, local_files_only=True)

    def _ensure_design_model(self) -> Any:
        if self._design_model is None:
            self._require_directory(self.settings.voice_design_model, "VoiceDesign")
            self._imports()
            self._design_model = self._load_model(self.settings.voice_design_model)
        return self._design_model

    def _ensure_base_model(self) -> Any:
        if self._base_model is None:
            self._require_directory(self.settings.base_model, "Base")
            self._imports()
            self._base_model = self._load_model(self.settings.base_model)
        return self._base_model

    def _paths(self, profile: VoiceProfile) -> tuple[Path, Path]:
        return (
            self.profile_dir / f"{profile.speaker_id}.reference.wav",
            self.profile_dir / f"{profile.speaker_id}.prompt.pt",
        )

    @staticmethod
    def _file_sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _profile_base_signature(profile: VoiceProfile) -> str:
        payload = {
            "speaker_id": profile.speaker_id,
            "voice_description": profile.voice_description.strip(),
            "reference_text": profile.reference_text.strip(),
        }
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def _profile_signature(self, profile: VoiceProfile, external_reference: Path | None) -> str:
        payload = {
            "profile_signature": self._profile_base_signature(profile),
            "external_reference_sha256": self._file_sha256(external_reference) if external_reference else None,
        }
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def _saved_prompt_signature(
        self,
        profile: VoiceProfile,
        prompt_path: Path,
        *,
        expected_reference_path: str | None,
        allow_relocated_internal_reference: bool = False,
    ) -> str | None:
        """Return a verified saved prompt signature, including portable internal refs."""
        metadata = self._read_json_dict(prompt_path.with_suffix(".prompt.json"))
        if not prompt_path.is_file() or not metadata:
            return None
        if metadata.get("prompt_schema_version") != 2:
            return None
        if metadata.get("profile_signature") != self._profile_base_signature(profile):
            return None
        if metadata.get("prompt_sha256") != self._file_sha256(prompt_path):
            return None
        reference_matches = metadata.get("reference_audio_path") == expected_reference_path
        if not reference_matches and allow_relocated_internal_reference:
            # VoiceDesign-generated reference WAVs live beside the prompt. The
            # profile stores their original absolute path; after a USB/folder move
            # that path is stale. The metadata's null external ref and canonical
            # filename prove this was generated internally, so the prompt is still
            # self-contained and can be reused without redesigning the character.
            reference_matches = metadata.get("reference_audio_path") is None
        if not reference_matches:
            return None
        signature = metadata.get("signature")
        return str(signature) if isinstance(signature, str) and signature else None

    def generation_fingerprint(self) -> str:
        """Fingerprint the pinned Qwen model snapshots used for synthesis.

        The Windows asset-preparation step writes a manifest with immutable
        snapshot revisions. For development environments without that manifest,
        fall back to model config hashes and weight sizes so replacing a model
        config or changing a checkpoint's size does not silently reuse old MP3s.
        """
        design = Path(self.settings.voice_design_model)
        base = Path(self.settings.base_model)
        manifest_path = design.parent / "KJV_QWEN_ASSET_MANIFEST.json"
        manifest_exists = manifest_path.is_file()
        manifest = self._read_json_dict(manifest_path) if manifest_exists else None
        if manifest_exists and manifest is None:
            raise QwenRuntimeUnavailable(f"Pinned Qwen asset manifest cannot be read: {manifest_path}")
        if manifest is not None:
            if manifest.get("schema_version") != 1:
                raise QwenRuntimeUnavailable(f"Pinned Qwen asset manifest has an unsupported schema: {manifest_path}")
            model_rows = manifest.get("models")
            if not isinstance(model_rows, list) or len(model_rows) != 2:
                raise QwenRuntimeUnavailable(f"Pinned Qwen asset manifest is invalid: {manifest_path}")
            expected = {
                ("Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign", "5ecdb67327fd37bb2e042aab12ff7391903235d3"),
                ("Qwen/Qwen3-TTS-12Hz-1.7B-Base", "fd4b254389122332181a7c3db7f27e918eec64e3"),
            }
            actual = {(item.get("repo"), item.get("revision")) for item in model_rows if isinstance(item, dict)}
            if actual != expected or len(actual) != 2:
                raise QwenRuntimeUnavailable(
                    f"Pinned Qwen asset manifest contains an unapproved model revision: {manifest_path}"
                )
            folders = {
                "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign": (design, "voice_design"),
                "Qwen/Qwen3-TTS-12Hz-1.7B-Base": (base, "base"),
            }
            for item in model_rows:
                if not isinstance(item, dict) or item.get("repo") not in folders:
                    raise QwenRuntimeUnavailable(f"Pinned Qwen asset manifest entry is malformed: {manifest_path}")
                folder, expected_kind = folders[item["repo"]]
                try:
                    actual_values = {
                        "folder": folder.name,
                        "kind": expected_kind,
                        "config_sha256": self._file_sha256(folder / "config.json"),
                        "speech_tokenizer_config_sha256": self._file_sha256(folder / "speech_tokenizer" / "config.json"),
                        "model_bytes": (folder / "model.safetensors").stat().st_size,
                        "speech_tokenizer_bytes": (folder / "speech_tokenizer" / "model.safetensors").stat().st_size,
                    }
                except OSError as exc:
                    raise QwenRuntimeUnavailable(
                        f"Pinned Qwen model asset is missing or unreadable in {folder}: {exc}"
                    ) from exc
                for field, actual_value in actual_values.items():
                    expected_value = item.get(field)
                    if (str(expected_value).casefold() != str(actual_value).casefold()):
                        raise QwenRuntimeUnavailable(
                            f"Pinned Qwen asset manifest mismatch for {folder.name} ({field}); re-run prepare_assets.ps1."
                        )
            payload = {
                "manifest": model_rows,
                "speaker_seed": manifest.get("speaker_seed"),
                "qwen_package": manifest.get("qwen_package", "qwen-tts==0.1.1"),
                "transformers": manifest.get("transformers", "transformers==4.57.3"),
            }
        else:
            model_rows = []
            for folder in (design, base):
                config_path = folder / "config.json"
                weight_path = folder / "model.safetensors"
                model_rows.append({
                    "folder": folder.name,
                    "config_sha256": self._file_sha256(config_path) if config_path.is_file() else None,
                    "weight_size": weight_path.stat().st_size if weight_path.is_file() else None,
                })
            payload = {
                "models": model_rows,
                "qwen_package": "qwen-tts==0.1.1",
                "transformers": "4.57.3",
            }
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def profile_fingerprint(self, profile: VoiceProfile) -> str:
        """Return a stable hash of the voice inputs that affect generated speech.

        Verified saved prompts remain portable when their source WAV is no longer
        present, including internal VoiceDesign WAVs whose absolute path changed
        when the output project was moved to another drive.
        """
        base_signature = self._profile_base_signature(profile)
        local_reference, prompt_path = self._paths(profile)
        supplied = Path(profile.reference_audio).expanduser() if profile.reference_audio else None
        external = supplied is not None and supplied.resolve() != local_reference.resolve()
        if not external:
            return base_signature
        if supplied.is_file():
            return self._profile_signature(profile, supplied)

        relocated_internal = supplied.name.casefold() == local_reference.name.casefold()
        saved_signature = self._saved_prompt_signature(
            profile,
            prompt_path,
            expected_reference_path=str(supplied),
            allow_relocated_internal_reference=relocated_internal,
        )
        if saved_signature:
            # A prompt created from an internally generated WAV has the same
            # signature as the base profile plus a null external reference.
            metadata = self._read_json_dict(prompt_path.with_suffix(".prompt.json")) or {}
            if metadata.get("reference_audio_path") is None and metadata.get("signature") == self._profile_signature(profile, None):
                return str(metadata["signature"])
            return saved_signature
        payload = {"profile_signature": base_signature, "missing_external_reference": str(supplied)}
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def _read_json_dict(path: Path) -> dict[str, Any] | None:
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
            return data if isinstance(data, dict) else None
        except (OSError, json.JSONDecodeError):
            return None

    @staticmethod
    def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
        write_json_atomic(path, payload)

    def _load_prompt_payload_file(self, prompt_path: Path) -> dict[str, Any]:
        try:
            payload = self._torch.load(str(prompt_path), map_location="cpu", weights_only=True)
        except TypeError as exc:
            raise QwenRuntimeUnavailable(
                "The installed PyTorch is too old for safe voice-profile loading; "
                "install a supported torch release with weights_only support."
            ) from exc
        except Exception as exc:
            raise QwenRuntimeUnavailable(f"Saved Qwen voice prompt cannot be safely loaded: {prompt_path}") from exc
        self._payload_to_prompt_items(payload)
        return payload

    @staticmethod
    def _read_signature(path: Path) -> str | None:
        try:
            return json.loads(path.read_text(encoding="utf-8")).get("signature")
        except (OSError, json.JSONDecodeError, AttributeError):
            return None

    def prepare_profiles(
        self,
        profiles: list[VoiceProfile],
        *,
        control_check: Callable[[], None] | None = None,
        progress_callback: Callable[[str, int, int, str], None] | None = None,
    ) -> None:
        if not profiles:
            return
        self._require_directory(self.settings.base_model, "Base")
        self._imports()

        unique_profiles = {profile.speaker_id: profile for profile in profiles}
        needs_reference: dict[str, tuple[VoiceProfile, Path, str]] = {}
        prompt_work: dict[str, tuple[VoiceProfile, Path, Path, str, Path | None]] = {}
        prompts_to_reuse: dict[str, tuple[VoiceProfile, Path, str]] = {}

        profile_items = list(unique_profiles.values())
        total_profiles = len(profile_items)
        for profile_index, profile in enumerate(profile_items, start=1):
            if control_check:
                control_check()
            local_reference, prompt_path = self._paths(profile)
            supplied = Path(profile.reference_audio).expanduser() if profile.reference_audio else None
            supplied_is_external = supplied is not None and supplied.resolve() != local_reference.resolve()
            reference_meta = local_reference.with_suffix(".reference.json")
            prompt_meta = prompt_path.with_suffix(".prompt.json")

            if supplied_is_external and not supplied.is_file():
                # A prepared voice prompt is self-contained and can travel with the
                # project folder. Reuse it when the profile definition and original
                # reference path still match the metadata and the prompt checksum is
                # intact; only require the source WAV again if a new prompt is needed.
                relocated_internal_reference = supplied.name.casefold() == local_reference.name.casefold()
                saved_signature = self._saved_prompt_signature(
                    profile,
                    prompt_path,
                    expected_reference_path=str(supplied),
                    allow_relocated_internal_reference=relocated_internal_reference,
                )
                saved_meta = self._read_json_dict(prompt_meta)
                saved_prompt_valid = bool(
                    saved_signature and saved_meta and saved_meta.get("prompt_schema_version") == 2
                )
                if saved_prompt_valid:
                    try:
                        self._load_prompt_payload_file(prompt_path)
                    except QwenRuntimeUnavailable:
                        saved_prompt_valid = False
                if (saved_prompt_valid and saved_meta.get("reference_audio_path") is None
                        and saved_meta.get("signature") != self._profile_signature(profile, None)):
                    saved_prompt_valid = False
                if not saved_prompt_valid:
                    raise QwenRuntimeUnavailable(
                        f"Reference audio for {profile.speaker_id} is missing or is not a file: {supplied}. "
                        "A verified saved voice prompt is unavailable; restore the WAV or clear the reference-audio field."
                    )
                prompts_to_reuse[profile.speaker_id] = (profile, prompt_path, str(saved_meta["signature"]))
                continue

            external_reference = supplied if supplied_is_external else None
            reference = external_reference or local_reference
            signature = self._profile_signature(profile, external_reference)

            if external_reference is None:
                local_reference_valid = (
                    local_reference.is_file() and self._read_signature(reference_meta) == signature
                )
                if not local_reference_valid:
                    local_reference.unlink(missing_ok=True)
                    reference_meta.unlink(missing_ok=True)
                    reference = local_reference
                    needs_reference[profile.speaker_id] = (profile, local_reference, signature)

            saved_prompt_meta = self._read_json_dict(prompt_meta)
            prompt_valid = bool(
                prompt_path.is_file()
                and saved_prompt_meta
                and saved_prompt_meta.get("prompt_schema_version") == 2
                and saved_prompt_meta.get("signature") == signature
                and saved_prompt_meta.get("profile_signature") == self._profile_base_signature(profile)
                and saved_prompt_meta.get("prompt_sha256") == self._file_sha256(prompt_path)
                and saved_prompt_meta.get("reference_audio_path") == (str(external_reference) if external_reference else None)
            )
            if prompt_valid:
                try:
                    self._load_prompt_payload_file(prompt_path)
                except QwenRuntimeUnavailable:
                    prompt_valid = False
            if prompt_valid:
                self._prompt_cache.pop(profile.speaker_id, None)
                prompts_to_reuse[profile.speaker_id] = (profile, prompt_path, signature)
            else:
                self._prompt_cache.pop(profile.speaker_id, None)
                profile.status = "not_prepared"
                prompt_path.unlink(missing_ok=True)
                prompt_meta.unlink(missing_ok=True)
                # Carry the reference identity with each work item. Do not use the loop's
                # last external_reference value when writing prompt metadata: a Bible
                # normally prepares many profiles with different external WAV paths.
                prompt_work[profile.speaker_id] = (
                    profile, reference, prompt_path, signature, external_reference
                )

        if needs_reference:
            # Avoid keeping the Base model and VoiceDesign model resident together
            # if profiles are added/revised during a later generation run.
            if self._base_model is not None:
                self._base_model = None
                self._prompt_cache.clear()
                gc.collect()
                if self._torch is not None and self._torch.cuda.is_available():
                    self._torch.cuda.empty_cache()
            design = self._ensure_design_model()
            for profile_index, (profile, reference, signature) in enumerate(needs_reference.values(), start=1):
                if control_check:
                    control_check()
                waveforms, sample_rate = design.generate_voice_design(
                    text=profile.reference_text,
                    instruct=profile.voice_description,
                    language=self.settings.language,
                )
                if not waveforms or not isinstance(waveforms[0], np.ndarray) or waveforms[0].size == 0:
                    raise RuntimeError(f"Qwen produced empty reference audio for {profile.speaker_id}")
                reference.parent.mkdir(parents=True, exist_ok=True)
                with atomic_output_path(reference) as staged_reference:
                    self._soundfile.write(str(staged_reference), waveforms[0], int(sample_rate))
                self._write_json_atomic(reference.with_suffix(".reference.json"), {"signature": signature})
                profile.reference_audio = str(reference)
                if progress_callback:
                    progress_callback("voice_design", profile_index, total_profiles, profile.speaker_id)
            # Do not keep the 1.7B VoiceDesign model resident while Base loads.
            self._design_model = None
            del design
            gc.collect()
            if self._torch.cuda.is_available():
                self._torch.cuda.empty_cache()

        if prompt_work:
            base = self._ensure_base_model()
            for profile_index, (profile, reference, prompt_path, signature, external_reference) in enumerate(prompt_work.values(), start=1):
                if control_check:
                    control_check()
                if not reference.is_file():
                    raise QwenRuntimeUnavailable(f"Missing generated voice reference for {profile.speaker_id}")
                prompt_items = base.create_voice_clone_prompt(
                    ref_audio=str(reference), ref_text=profile.reference_text, x_vector_only_mode=False
                )
                if not prompt_items:
                    raise RuntimeError(f"Qwen did not create a reusable voice prompt for {profile.speaker_id}")
                prompt_payload = self._prompt_items_to_payload(prompt_items)
                # Qwen accepts either the original prompt-item list or its documented
                # dictionary representation. Persist a plain tensor/primitive dict so
                # PyTorch can reload it with weights_only=True (no arbitrary pickle
                # object deserialization from an existing output folder). A unique
                # same-directory staging path prevents concurrent workers from sharing
                # a fixed .pt.tmp file; failed saves leave the previous prompt intact.
                with atomic_output_path(prompt_path) as staged_prompt:
                    self._torch.save(prompt_payload, str(staged_prompt))
                self._write_json_atomic(prompt_path.with_suffix(".prompt.json"), {
                    "prompt_schema_version": 2,
                    "signature": signature,
                    "profile_signature": self._profile_base_signature(profile),
                    "reference_audio_path": str(external_reference) if external_reference else None,
                    "prompt_sha256": self._file_sha256(prompt_path),
                })
                self._remember_prompt(profile.speaker_id, prompt_payload)
                profile.prompt_asset = str(prompt_path)
                profile.status = "prepared"
                if progress_callback:
                    progress_callback("clone_prompt", profile_index, total_profiles, profile.speaker_id)

        for profile_index, (speaker_id, (profile, prompt_path, _signature)) in enumerate(prompts_to_reuse.items(), start=1):
            # Do not preload every reusable prompt tensor. Keep it on disk and load
            # it on demand into the bounded LRU working set used by synthesis.
            profile.prompt_asset = str(prompt_path)
            profile.status = "prepared"
            if progress_callback:
                progress_callback("cached", profile_index, total_profiles, profile.speaker_id)

    @staticmethod
    def _prompt_items_to_payload(prompt_items: list[Any]) -> dict[str, list[Any]]:
        # Keep the reference transcript as well as codec/speaker tensors. Qwen
        # 0.1.1 uses that transcript to create ref_ids for ICL-mode generation;
        # a bare dict of the four tensors/flags silently loses this input.
        fields = ("ref_code", "ref_spk_embedding", "x_vector_only_mode", "icl_mode", "ref_text")
        payload: dict[str, list[Any]] = {}
        for field in fields:
            try:
                payload[field] = [getattr(item, field) for item in prompt_items]
            except AttributeError as exc:
                raise RuntimeError(
                    "The installed qwen-tts returned an unsupported voice-prompt item; "
                    f"missing field {field!r}"
                ) from exc
        if not payload["ref_spk_embedding"]:
            raise RuntimeError("Qwen returned a voice prompt without speaker embeddings")
        lengths = {len(value) for value in payload.values()}
        if len(lengths) != 1:
            raise RuntimeError("Qwen returned inconsistent voice-prompt item fields")
        for index, icl_mode in enumerate(payload["icl_mode"]):
            if bool(icl_mode) and not str(payload["ref_text"][index] or "").strip():
                raise RuntimeError(
                    "Qwen returned an ICL voice prompt without its reference transcript; "
                    "the saved profile cannot be used for voice cloning."
                )
        return payload

    @staticmethod
    def _payload_to_prompt_items(payload: Any) -> list[Any]:
        """Rebuild Qwen's prompt-item object shape, preserving the ICL transcript.

        In qwen-tts 0.1.1, generate_voice_clone accepts either a list of
        VoiceClonePromptItem objects or a dictionary. The dictionary path does
        not populate ref_texts_for_ids, however, so ICL mode then lacks ref_ids.
        The wrapper's list path obtains ref_text from each item and works with
        its documented prepared-prompt contract. SimpleNamespace is sufficient
        because the pinned Qwen implementation consumes these objects by their
        five named attributes rather than enforcing a concrete dataclass type.
        """
        import types

        required = ("ref_code", "ref_spk_embedding", "x_vector_only_mode", "icl_mode", "ref_text")
        if not isinstance(payload, dict) or any(name not in payload for name in required):
            raise QwenRuntimeUnavailable("Saved Qwen voice prompt is missing required fields, including ref_text.")
        lengths = {len(payload[name]) for name in required if isinstance(payload[name], (list, tuple))}
        if len(lengths) != 1 or not all(isinstance(payload[name], (list, tuple)) for name in required):
            raise QwenRuntimeUnavailable("Saved Qwen voice prompt fields have inconsistent batch lengths.")
        items = []
        for index in range(next(iter(lengths), 0)):
            ref_text = payload["ref_text"][index]
            icl_mode = bool(payload["icl_mode"][index])
            if icl_mode and not str(ref_text or "").strip():
                raise QwenRuntimeUnavailable("Saved ICL voice prompt has no reference transcript; rebuild this voice profile.")
            items.append(types.SimpleNamespace(
                ref_code=payload["ref_code"][index],
                ref_spk_embedding=payload["ref_spk_embedding"][index],
                x_vector_only_mode=bool(payload["x_vector_only_mode"][index]),
                icl_mode=icl_mode,
                ref_text=ref_text,
            ))
        if not items:
            raise QwenRuntimeUnavailable("Saved Qwen voice prompt contains no prompt items.")
        return items

    def _remember_prompt(self, speaker_id: str, prompt: Any) -> None:
        self._prompt_cache[speaker_id] = prompt
        self._prompt_cache.move_to_end(speaker_id)
        while len(self._prompt_cache) > self._prompt_cache_limit:
            self._prompt_cache.popitem(last=False)

    def _load_prompt(self, profile: VoiceProfile) -> Any:
        cached = self._prompt_cache.get(profile.speaker_id)
        if cached is not None:
            self._prompt_cache.move_to_end(profile.speaker_id)
            return self._payload_to_prompt_items(cached)
        _reference, prompt_path = self._paths(profile)
        if not prompt_path.is_file():
            raise QwenRuntimeUnavailable(f"Reusable voice prompt is missing for {profile.speaker_id}: {prompt_path}")
        prompt = self._load_prompt_payload_file(prompt_path)
        self._remember_prompt(profile.speaker_id, prompt)
        return self._payload_to_prompt_items(prompt)

    def synthesize(self, text: str, profile: VoiceProfile) -> tuple[np.ndarray, int]:
        if not text.strip():
            raise ValueError("Cannot synthesize empty text")
        if profile.speaker_id not in self._prompt_cache:
            prompt_path = self._paths(profile)[1]
            if not prompt_path.is_file():
                self.prepare_profiles([profile])
        base = self._ensure_base_model()
        result, sample_rate = base.generate_voice_clone(
            text=text,
            language=self.settings.language,
            voice_clone_prompt=self._load_prompt(profile),
            non_streaming_mode=True,
        )
        if not result or not isinstance(result[0], np.ndarray) or result[0].size == 0:
            raise RuntimeError(f"Qwen returned no speech for {profile.speaker_id}")
        audio = np.asarray(result[0], dtype=np.float32).reshape(-1)
        if not np.isfinite(audio).all():
            raise RuntimeError("Qwen returned invalid non-finite audio")
        return audio, int(sample_rate)


class SyntheticTestBackend:
    fingerprint_name = "synthetic-test-backend"
    fingerprint_version = "1"
    """Deterministic synthetic audio. Tests only; never use for customer recordings."""

    is_test_backend = True

    def __init__(self, sample_rate: int = 24000) -> None:
        self.sample_rate = sample_rate
        self.prepared: set[str] = set()

    def prepare_profiles(
        self,
        profiles: list[VoiceProfile],
        *,
        control_check: Callable[[], None] | None = None,
        progress_callback: Callable[[str, int, int, str], None] | None = None,
    ) -> None:
        self.prepared.update(profile.speaker_id for profile in profiles)

    def synthesize(self, text: str, profile: VoiceProfile) -> tuple[np.ndarray, int]:
        duration = max(0.12, min(1.5, len(text) / 36.0))
        count = int(self.sample_rate * duration)
        frequency = 170 + (sum(profile.speaker_id.encode("utf-8")) % 160)
        t = np.arange(count, dtype=np.float32) / self.sample_rate
        envelope = np.minimum(1.0, np.arange(count) / max(1, self.sample_rate // 50))
        audio = (0.06 * np.sin(2 * np.pi * frequency * t) * envelope).astype(np.float32)
        return audio, self.sample_rate


def save_backend_diagnostic(path: str | Path, backend: SpeechBackend) -> None:
    data = {
        "backend": type(backend).__name__,
        "synthetic_test_backend": bool(getattr(backend, "is_test_backend", False)),
    }
    write_json_atomic(Path(path), data)
