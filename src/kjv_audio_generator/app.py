from __future__ import annotations

import json
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .attribution import AttributionMap
from .attribution_seed import import_clear_speaker_seed, load_or_seed_attribution, merge_seed_suggestions
from .audio import ChapterAudioAssembler
from .backend import QwenSettings, QwenVoiceBackend
from .parser import parse_path, parse_text
from .voices import VoiceRegistry
from .worker import ChapterWorker
from .runtime import bundled_ffmpeg, runtime_root
from .json_io import write_json_atomic
from .editing import format_segments_for_editor, parse_segments_from_editor
from .models import VerseRef
from .voices import VoiceProfile


class GeneratorApp:
    def __init__(self, root: tk.Tk | None = None) -> None:
        self.root = root or tk.Tk()
        self.root.title("KJV Bible Audio Generator")
        self.root.geometry("850x670")
        self.document = None
        self.output_dir = tk.StringVar(value=str(Path.home() / "KJV_Bible_Audio"))
        self.source_label = tk.StringVar(value="Paste Bible text below or open a supported text file.")
        self.status = tk.StringVar(value="Ready — import text to begin.")
        self.events: queue.Queue[tuple[str, dict]] = queue.Queue()
        self.worker: ChapterWorker | None = None
        self.registry: VoiceRegistry | None = None
        self.attribution: AttributionMap | None = None
        self._build_ui()
        self.root.after(150, self._poll_events)

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, padding=12); outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="KJV Bible Audio Generator", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(outer, text="Import or paste the Bible text. The generator saves each chapter as a separate MP3.").pack(anchor="w", pady=(2,10))
        row = ttk.Frame(outer); row.pack(fill="x")
        ttk.Button(row, text="Open Bible Text / USFM / ZIP", command=self._open_file).pack(side="left")
        ttk.Label(row, textvariable=self.source_label).pack(side="left", padx=10)
        self.text = tk.Text(outer, height=17, wrap="word", undo=True)
        self.text.pack(fill="both", expand=True, pady=8)
        output = ttk.Frame(outer); output.pack(fill="x", pady=4)
        ttk.Label(output, text="Output folder:").pack(side="left")
        ttk.Entry(output, textvariable=self.output_dir).pack(side="left", fill="x", expand=True, padx=6)
        ttk.Button(output, text="Browse", command=self._browse_output).pack(side="left")
        controls = ttk.Frame(outer); controls.pack(fill="x", pady=(7, 3))
        ttk.Button(controls, text="Validate Imported Text", command=self._validate).pack(side="left")
        ttk.Button(controls, text="Import Speaker Data (TSV)", command=self._import_speaker_data).pack(side="left", padx=6)
        self.start_button = ttk.Button(controls, text="GENERATE ENTIRE BIBLE", command=self._start)
        self.start_button.pack(side="left", padx=8)
        review = ttk.Frame(outer); review.pack(fill="x", pady=(2, 7))
        ttk.Button(review, text="Manage Character Voices", command=self._manage_voices).pack(side="left")
        ttk.Button(review, text="Review Verse Speakers", command=self._review_verse_speakers).pack(side="left", padx=6)
        self.pause_button = ttk.Button(review, text="Pause", command=self._pause_resume, state="disabled")
        self.pause_button.pack(side="left", padx=(14, 5))
        self.stop_button = ttk.Button(review, text="Stop safely", command=self._stop, state="disabled")
        self.stop_button.pack(side="left")
        self.retry_button = ttk.Button(review, text="Retry failed chapters", command=lambda: self._start(retry_failed=True), state="disabled")
        self.retry_button.pack(side="left", padx=(5, 0))
        ttk.Label(outer, textvariable=self.status, wraplength=810).pack(anchor="w", pady=5)
        self.progress = ttk.Progressbar(outer, mode="determinate", maximum=100)
        self.progress.pack(fill="x", pady=4)
        ttk.Label(outer, text="Generation log").pack(anchor="w")
        self.log = tk.Text(outer, height=8, state="disabled", wrap="word")
        self.log.pack(fill="both", expand=False)

    def _append_log(self, text: str) -> None:
        self.log.configure(state="normal"); self.log.insert("end", text + "\n"); self.log.see("end"); self.log.configure(state="disabled")

    def _open_file(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("Bible text", "*.usfm *.sfm *.txt *.json *.zip"), ("All files", "*.*")])
        if not path: return
        try:
            doc = parse_path(path)
            self.document = doc
            self.text.delete("1.0", "end")
            self.source_label.set(f"{Path(path).name}: {len(doc.chapters)} chapters")
            self._append_log(f"Imported {path}")
            self.status.set(f"Imported {len(doc.chapters)} chapters / {sum(len(c.verses) for c in doc.chapters.values())} verses.")
        except Exception as exc:
            messagebox.showerror("Import failed", str(exc))

    def _browse_output(self) -> None:
        path = filedialog.askdirectory(initialdir=self.output_dir.get() or str(Path.home()))
        if path: self.output_dir.set(path)

    def _get_document(self):
        raw = self.text.get("1.0", "end-1c")
        if raw.strip():
            self.document = parse_text(raw)
        if self.document is None or not self.document.chapters:
            raise ValueError("Import or paste Bible text first")
        return self.document

    def _validate(self) -> None:
        try:
            doc = self._get_document()
            books = len({c.book for c in doc.ordered_chapters()})
            chapters = len(doc.chapters)
            verses = sum(len(c.verses) for c in doc.chapters.values())
            try:
                report = doc.validate_complete()
                message = (f"KJV structure/versification validated: {report['books']} books, "
                           f"{report['chapters']} chapters, {report['verses']:,} verses. "
                           "This check does not authenticate the translation wording.")
            except ValueError as validation_error:
                message = f"Import recognized: {books} books, {chapters} chapters, {verses:,} verses. Not ready for whole-Bible generation: {validation_error}"
            self.status.set(message)
            self._append_log(message)
        except Exception as exc:
            messagebox.showerror("Validation failed", str(exc))

    def _metadata_dir(self) -> Path:
        return Path(self.output_dir.get()).expanduser().resolve() / "metadata"

    def _load_registry(self) -> VoiceRegistry:
        path = self._metadata_dir() / "voice_registry.json"
        self.registry = VoiceRegistry.load(path) if path.is_file() else VoiceRegistry.defaults()
        return self.registry

    def _save_registry(self, registry: VoiceRegistry) -> None:
        registry.save(self._metadata_dir() / "voice_registry.json")
        self.registry = registry

    def _manage_voices(self) -> None:
        registry = self._load_registry()
        dialog = tk.Toplevel(self.root)
        dialog.title("Manage Character Voice Profiles")
        dialog.geometry("980x690")
        dialog.transient(self.root)

        shell = ttk.Frame(dialog, padding=10); shell.pack(fill="both", expand=True)
        left = ttk.Frame(shell); left.pack(side="left", fill="y", padx=(0, 12))
        ttk.Label(left, text="Saved characters").pack(anchor="w")
        tree = ttk.Treeview(left, columns=("id", "status"), show="tree headings", height=25, selectmode="browse")
        tree.heading("#0", text="Character")
        tree.heading("id", text="Stable ID")
        tree.heading("status", text="Voice")
        tree.column("#0", width=155); tree.column("id", width=125); tree.column("status", width=90)
        tree.pack(fill="y", expand=True)

        right = ttk.Frame(shell); right.pack(side="left", fill="both", expand=True)
        id_var = tk.StringVar(); name_var = tk.StringVar(); aliases_var = tk.StringVar()
        reference_audio_var = tk.StringVar(); status_var = tk.StringVar(value="not_prepared")
        fields = ttk.Frame(right); fields.pack(fill="x")
        ttk.Label(fields, text="Stable speaker ID").grid(row=0, column=0, sticky="w", pady=3)
        id_entry = ttk.Entry(fields, textvariable=id_var, width=35); id_entry.grid(row=0, column=1, sticky="ew", pady=3)
        ttk.Label(fields, text="Display name").grid(row=1, column=0, sticky="w", pady=3)
        ttk.Entry(fields, textvariable=name_var).grid(row=1, column=1, sticky="ew", pady=3)
        ttk.Label(fields, text="Aliases (comma separated)").grid(row=2, column=0, sticky="w", pady=3)
        ttk.Entry(fields, textvariable=aliases_var).grid(row=2, column=1, sticky="ew", pady=3)
        ttk.Label(fields, text="Profile status").grid(row=3, column=0, sticky="w", pady=3)
        ttk.Label(fields, textvariable=status_var).grid(row=3, column=1, sticky="w", pady=3)
        fields.columnconfigure(1, weight=1)

        ttk.Label(right, text="Voice description (how Qwen should sound)").pack(anchor="w", pady=(10, 2))
        description = tk.Text(right, height=7, wrap="word", undo=True); description.pack(fill="x")
        ttk.Label(right, text="Reference script (spoken once to create the reusable voice)").pack(anchor="w", pady=(10, 2))
        reference_text = tk.Text(right, height=5, wrap="word", undo=True); reference_text.pack(fill="x")
        audio_row = ttk.Frame(right); audio_row.pack(fill="x", pady=(10, 2))
        ttk.Label(audio_row, text="Optional reference audio:").pack(side="left")
        ttk.Entry(audio_row, textvariable=reference_audio_var).pack(side="left", fill="x", expand=True, padx=5)

        selected_id: dict[str, str | None] = {"value": None}
        loading = {"value": False}

        def fill_tree(select_id: str | None = None) -> None:
            for item in tree.get_children(): tree.delete(item)
            for profile in sorted(registry.profiles.values(), key=lambda item: item.display_name.casefold()):
                tree.insert("", "end", iid=profile.speaker_id, text=profile.display_name,
                            values=(profile.speaker_id, profile.status))
            if select_id and tree.exists(select_id):
                tree.selection_set(select_id); tree.focus(select_id); load_selected()

        def load_selected(_event=None) -> None:
            selection = tree.selection()
            if not selection: return
            profile = registry.get(selection[0])
            loading["value"] = True
            selected_id["value"] = profile.speaker_id
            id_var.set(profile.speaker_id); name_var.set(profile.display_name)
            aliases_var.set(", ".join(profile.aliases)); reference_audio_var.set(profile.reference_audio or "")
            status_var.set(profile.status)
            description.delete("1.0", "end"); description.insert("1.0", profile.voice_description)
            reference_text.delete("1.0", "end"); reference_text.insert("1.0", profile.reference_text)
            id_entry.configure(state="readonly")
            loading["value"] = False

        tree.bind("<<TreeviewSelect>>", load_selected)

        def new_profile() -> None:
            tree.selection_remove(tree.selection())
            selected_id["value"] = None
            id_entry.configure(state="normal")
            id_var.set(""); name_var.set(""); aliases_var.set(""); reference_audio_var.set("")
            status_var.set("not_prepared")
            description.delete("1.0", "end")
            reference_text.delete("1.0", "end")
            description.insert("1.0", "Distinctive, clear Bible character voice; measured conversational delivery, consistent timbre, natural emotion.")
            reference_text.insert("1.0", "I will speak clearly and naturally, with a steady and expressive reading voice.")
            id_entry.focus_set()

        def choose_audio() -> None:
            path = filedialog.askopenfilename(parent=dialog, title="Select reference voice audio",
                filetypes=[("Audio files", "*.wav *.flac *.mp3 *.m4a"), ("All files", "*.*")])
            if path: reference_audio_var.set(path)

        def save_profile() -> None:
            try:
                speaker_id = id_var.get().strip()
                if not speaker_id: raise ValueError("Enter a stable speaker ID.")
                if selected_id["value"] and speaker_id.casefold().replace("-", "_") != selected_id["value"]:
                    raise ValueError("A saved speaker ID cannot be changed. Create a new profile instead to preserve references.")
                description_text = description.get("1.0", "end-1c").strip()
                reference_script = reference_text.get("1.0", "end-1c").strip()
                if not description_text or not reference_script:
                    raise ValueError("Voice description and reference script are both required.")
                aliases = [item.strip() for item in aliases_var.get().split(",") if item.strip()]
                existing = registry.profiles.get(speaker_id.casefold().replace("-", "_"))
                changed = bool(existing and (existing.voice_description != description_text or
                    existing.reference_text != reference_script or
                    existing.reference_audio != (reference_audio_var.get().strip() or None)))
                profile = VoiceProfile(
                    speaker_id=speaker_id,
                    display_name=name_var.get(),
                    aliases=aliases,
                    voice_description=description_text,
                    reference_text=reference_script,
                    reference_audio=reference_audio_var.get().strip() or None,
                    prompt_asset=None if changed else (existing.prompt_asset if existing else None),
                    status="not_prepared" if changed or not existing else existing.status,
                )
                registry.add(profile, replace=existing is not None)
                self._save_registry(registry)
                selected_id["value"] = profile.speaker_id
                fill_tree(profile.speaker_id)
                self.status.set(f"Saved voice profile: {profile.display_name} ({profile.speaker_id}).")
                self._append_log(f"Saved character voice profile: {profile.speaker_id}")
            except Exception as exc:
                messagebox.showerror("Cannot save voice profile", str(exc), parent=dialog)

        buttons = ttk.Frame(right); buttons.pack(fill="x", pady=12)
        ttk.Button(buttons, text="New Character", command=new_profile).pack(side="left")
        ttk.Button(buttons, text="Choose Audio…", command=choose_audio).pack(side="left", padx=5)
        ttk.Button(buttons, text="Save Voice Profile", command=save_profile).pack(side="left", padx=5)
        ttk.Button(buttons, text="Close", command=dialog.destroy).pack(side="right")
        fill_tree(next(iter(registry.profiles), None))
        if registry.profiles:
            load_selected()

    def _review_verse_speakers(self) -> None:
        try:
            doc = self._get_document()
            verses = [verse for chapter in doc.ordered_chapters() for verse in chapter.verses]
            if not verses:
                raise ValueError("Import verse text before reviewing speakers.")
            registry = self._load_registry()
            self._save_registry(registry)
            output_root = Path(self.output_dir.get()).expanduser().resolve()
            assignments_path = output_root / "metadata" / "speaker_assignments.json"
            if assignments_path.is_file():
                attribution = AttributionMap.load(assignments_path, registry)
            else:
                attribution = AttributionMap(registry)
            self.attribution = attribution
        except Exception as exc:
            messagebox.showerror("Cannot review speakers", str(exc), parent=self.root)
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Review Verse Speaker Assignments")
        dialog.geometry("900x650")
        dialog.transient(self.root)
        shell = ttk.Frame(dialog, padding=12); shell.pack(fill="both", expand=True)
        verse_refs = [verse.ref.label() for verse in verses]
        verse_lookup = {verse.ref.label(): verse for verse in verses}
        ref_var = tk.StringVar(value=verse_refs[0])
        filter_var = tk.StringVar(value="All verses")
        ttk.Label(shell, text="Filter review queue").pack(anchor="w")
        filter_row = ttk.Frame(shell); filter_row.pack(fill="x", pady=(2, 4))
        filter_combo = ttk.Combobox(
            filter_row, textvariable=filter_var,
            values=("All verses", "Needs review", "Manual overrides"),
            state="readonly", width=20,
        )
        filter_combo.pack(side="left")
        ttk.Label(filter_row, text="Verse reference").pack(side="left", padx=(12, 4))
        ref_row = ttk.Frame(shell); ref_row.pack(fill="x", pady=4)
        ref_combo = ttk.Combobox(ref_row, textvariable=ref_var, values=verse_refs, width=34)
        ref_combo.pack(side="left")
        ttk.Label(shell, text="Original verse text (do not edit here)").pack(anchor="w", pady=(10, 2))
        original = tk.Text(shell, height=5, wrap="word", state="disabled"); original.pack(fill="x")
        ttk.Label(shell, text="Speech segments — one line per segment: speaker_id, TAB, exact text.\nThe combined text must match the verse exactly.").pack(anchor="w", pady=(10, 2))
        segments_text = tk.Text(shell, height=16, wrap="word", undo=True); segments_text.pack(fill="both", expand=True)
        footer = ttk.Frame(shell); footer.pack(fill="x", pady=10)
        message_var = tk.StringVar(value="Choose a verse to review or override.")
        ttk.Label(shell, textvariable=message_var, wraplength=860).pack(anchor="w")

        def refresh_reference_values(*, keep_selection: bool = True) -> None:
            current = ref_var.get().strip() if keep_selection else ""
            mode = filter_var.get()
            if mode == "Needs review":
                values = [
                    ref for ref in verse_refs
                    if ref in attribution.seed_review and ref not in attribution.segment_overrides
                ]
            elif mode == "Manual overrides":
                values = [ref for ref in verse_refs if ref in attribution.segment_overrides]
            else:
                values = verse_refs
            ref_combo.configure(values=values)
            if current in values:
                ref_var.set(current)
            elif values:
                ref_var.set(values[0])
            else:
                ref_var.set("")
            return values

        def on_filter_changed(_event=None) -> None:
            values = refresh_reference_values(keep_selection=False)
            if values:
                show_verse()
            else:
                original.configure(state="normal"); original.delete("1.0", "end"); original.configure(state="disabled")
                segments_text.delete("1.0", "end")
                message_var.set("No verses match this filter.")

        def show_verse(_event=None) -> None:
            label = ref_var.get().strip()
            verse = verse_lookup.get(label)
            if verse is None:
                original.configure(state="normal"); original.delete("1.0", "end"); original.configure(state="disabled")
                segments_text.delete("1.0", "end")
                message_var.set("No verse is selected. Change the filter or import text.")
                return
            original.configure(state="normal"); original.delete("1.0", "end"); original.insert("1.0", verse.text); original.configure(state="disabled")
            existing = attribution.segment_overrides.get(label)
            if existing:
                rows = [(item["speaker_id"], item["text"]) for item in existing]
                review_state = "Manually reviewed"
            else:
                rows = [(segment.speaker_id, segment.text) for segment in attribution.segments_for(verse)]
                candidates = attribution.seed_review.get(label)
                review_state = ("Needs review — provisional candidates: " + ", ".join(candidates)) if candidates else "No ambiguity flag"
            segments_text.delete("1.0", "end")
            segments_text.insert("1.0", format_segments_for_editor(rows))
            message_var.set(f"{label} — {review_state}; {len(rows)} segment(s). Speaker IDs: {', '.join(sorted(registry.profiles))}")

        def save_segments() -> None:
            label = ref_var.get().strip(); verse = verse_lookup.get(label)
            if verse is None: return
            try:
                content = segments_text.get("1.0", "end-1c")
                rows = parse_segments_from_editor(content, verse_ref=verse.ref,
                                                  original_text=verse.text, registry=registry)
                attribution.segment_overrides[label] = rows
                attribution.save(assignments_path)
                self.attribution = attribution
                refresh_reference_values()
                message_var.set(f"Saved {len(rows)} speaker segment(s) for {label}; marked reviewed.")
                self._append_log(f"Saved speaker assignments for {label}: {', '.join(r['speaker_id'] for r in rows)}")
                self.status.set(f"Saved reviewed voice assignments for {label}.")
            except Exception as exc:
                messagebox.showerror("Invalid speaker segments", str(exc), parent=dialog)

        def reset_auto() -> None:
            label = ref_var.get().strip()
            if label in attribution.segment_overrides:
                del attribution.segment_overrides[label]
                attribution.save(assignments_path)
            refresh_reference_values()
            show_verse()
            message_var.set(f"Removed manual override for {label}; automatic attribution will be used.")

        ttk.Button(ref_row, text="Load Verse", command=show_verse).pack(side="left", padx=6)
        ttk.Button(footer, text="Save Speaker Segments", command=save_segments).pack(side="left")
        ttk.Button(footer, text="Clear Manual Override", command=reset_auto).pack(side="left", padx=6)
        ttk.Button(footer, text="Close", command=dialog.destroy).pack(side="right")
        filter_combo.bind("<<ComboboxSelected>>", on_filter_changed)
        ref_combo.bind("<<ComboboxSelected>>", show_verse)
        refresh_reference_values(keep_selection=False)
        show_verse()

    def _import_speaker_data(self) -> None:
        projections = filedialog.askopenfilename(
            title="Select Clear-Aligned-Projections.tsv",
            filetypes=[("Tab-separated speaker data", "*.tsv"), ("All files", "*.*")],
        )
        if not projections:
            return
        details = filedialog.askopenfilename(
            title="Select character_detail.semantic_data.tsv (optional)",
            filetypes=[("Tab-separated character details", "*.tsv"), ("All files", "*.*")],
        )
        try:
            out = Path(self.output_dir.get()).expanduser().resolve()
            metadata = out / "metadata"
            registry_path = metadata / "voice_registry.json"
            registry = VoiceRegistry.load(registry_path) if registry_path.is_file() else VoiceRegistry.defaults()
            assignments_path = metadata / "speaker_assignments.json"
            existing = AttributionMap.load(assignments_path, registry) if assignments_path.is_file() else None
            incoming, report, review = import_clear_speaker_seed(projections, details or None, registry)
            attribution, merge_report = merge_seed_suggestions(existing, incoming)
            metadata.mkdir(parents=True, exist_ok=True)
            # Keep GUI and CLI imports on the same non-destructive merge path. A
            # user may have carefully reviewed thousands of verses before adding
            # another provisional suggestion source.
            registry.save(registry_path)
            attribution.save(assignments_path)
            review["ambiguous_verse_candidates"] = attribution.seed_review
            review["merge"] = merge_report
            write_json_atomic(metadata / "speaker_seed_review.json", review)
            self.registry = registry
            self.attribution = attribution
            summary = report.to_dict()
            summary["merge"] = merge_report
            message = (
                f"Imported {summary['speakers_found']} speaker labels; created {summary['profiles_created']} new profiles; "
                f"prepared {summary['suggested_ranges']} provisional ranges; {summary['ambiguous_verses']} verses need review. "
                "The source dataset is not KJV-specific, so verify its suggestions against your KJV text."
            )
            self.status.set(message)
            self._append_log(message)
            messagebox.showinfo("Speaker suggestions imported", message)
        except Exception as exc:
            messagebox.showerror("Speaker data import failed", str(exc))

    def _start(self, *, retry_failed: bool = False) -> None:
        try:
            doc = self._get_document()
            validation = doc.validate_complete()
            if not validation.get("complete_verse_count"):
                raise ValueError("The import is not a complete 66-book KJV. Generation was not started.")
            out = Path(self.output_dir.get()).expanduser().resolve(); out.mkdir(parents=True, exist_ok=True)
            registry_path = out / "metadata" / "voice_registry.json"
            registry = VoiceRegistry.load(registry_path) if registry_path.exists() else VoiceRegistry.defaults()
            self.registry = registry
            base = runtime_root()
            attribution = load_or_seed_attribution(out, base, registry)
            self.attribution = attribution
            settings = QwenSettings(base / "models" / "Qwen3-TTS-12Hz-1.7B-VoiceDesign",
                                    base / "models" / "Qwen3-TTS-12Hz-1.7B-Base", device="auto")
            backend = QwenVoiceBackend(settings, out / "metadata" / "voice_assets")
            ffmpeg_path = bundled_ffmpeg()
            assembler = ChapterAudioAssembler(out, ffmpeg=ffmpeg_path if ffmpeg_path.is_file() else None)
            self.worker = ChapterWorker(doc, out, registry, attribution, backend, assembler, callback=lambda ev,data:self.events.put((ev,data)))
            if retry_failed:
                retried = self.worker.store.retry_failed()
                self._append_log(f"Requeued {retried} failed chapter(s).")
            self.worker.start(background=True)
            self.start_button.configure(state="disabled")
            self.pause_button.configure(state="normal", text="Pause")
            self.stop_button.configure(state="normal")
            self.retry_button.configure(state="disabled")
            self.status.set("Preparing persistent character voices and generation queue…")
        except Exception as exc:
            messagebox.showerror("Cannot start generation", str(exc))

    def _stop(self) -> None:
        if self.worker:
            self.stop_button.configure(state="disabled")
            self.status.set("Stopping safely after the current synthesis step…")
            self.worker.stop()

    def _pause_resume(self) -> None:
        if not self.worker: return
        if self.pause_button.cget("text") == "Pause":
            self.worker.pause(); self.pause_button.configure(text="Resume")
        else:
            self.worker.resume(); self.pause_button.configure(text="Pause")

    def _poll_events(self) -> None:
        try:
            while True:
                event, data = self.events.get_nowait()
                if event == "chapter_started":
                    self.status.set(f"Generating {data['book']} {data['chapter']}…")
                elif event == "chapter_complete":
                    counts = data["counts"]; total = sum(counts.values())
                    self.progress.configure(value=100*counts["complete"]/max(1,total))
                    self._append_log(f"Saved {data['output']}")
                elif event == "chapter_error":
                    self._append_log(f"ERROR {data['book']} {data['chapter']}: {data['error']} ({data['status']})")
                elif event == "preparing_voices":
                    self._append_log(f"Preparing {len(data['speaker_ids'])} persistent voice profile(s).")
                elif event == "voice_profile_progress":
                    phase_text = {
                        "voice_design": "Designing voice",
                        "clone_prompt": "Building reusable voice prompt",
                        "cached": "Reusing saved voice prompt",
                        "synthetic": "Preparing test voice",
                    }.get(data["phase"], "Preparing voice")
                    self.status.set(f"{phase_text} {data['index']} of {data['total']}: {data['speaker_id']}")
                    if data["index"] == 1 or data["index"] % 10 == 0 or data["index"] == data["total"]:
                        self._append_log(f"{phase_text} {data['index']}/{data['total']}: {data['speaker_id']}")
                elif event == "finished":
                    self.status.set(f"Finished. Completed: {data['counts']['complete']}; failed: {data['counts']['failed']}; pending: {data['counts']['pending']}.")
                    self.start_button.configure(state="normal")
                    self.pause_button.configure(state="disabled")
                    self.stop_button.configure(state="disabled")
                    self.retry_button.configure(state="normal" if data['counts']['failed'] else "disabled")
                    if data.get("stopped"):
                        self.status.set(f"Stopped safely. Completed: {data['counts']['complete']}; pending: {data['counts']['pending']}; failed: {data['counts']['failed']}.")
                elif event == "fatal_error":
                    self.status.set(f"Generation stopped: {data['error']}"); self._append_log(data['error'])
                    self.start_button.configure(state="normal")
                    self.pause_button.configure(state="disabled")
                    self.stop_button.configure(state="disabled")
                    self.retry_button.configure(state="normal" if self.worker and self.worker.store.progress()["failed"] else "disabled")
                elif event in {"paused","resumed","stop_requested"}:
                    self.status.set(event.replace("_", " ").title())
        except queue.Empty:
            pass
        self.root.after(150, self._poll_events)

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    GeneratorApp().run()
