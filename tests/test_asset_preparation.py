from pathlib import Path
import sys


def test_asset_preparation_pins_qwen_models_and_checks_all_required_files():
    root = Path(__file__).resolve().parents[1]
    script = (root / "tools" / "prepare_assets.ps1").read_text(encoding="utf-8")
    helper = (root / "tools" / "qwen_asset_integrity.py").read_text(encoding="utf-8")
    assert "report --models-root" in script
    assert "qwen_asset_integrity.py" in script
    for token in (
        "391e8db219f292c515297cdceeb43e4eae67cdde35fa57e79a6a8a532fca0522",
        "38fc7fc51c5e776e840414b6fd443962e9411b9654888fd7913e4da643cb857c",
        "836b7b357f5ea43e889936a3709af68dfe3751881acefe4ecf0dbd30ba571258",
    ):
        assert token in helper
    for token in (
        "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign",
        "5ecdb67327fd37bb2e042aab12ff7391903235d3",
        "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
        "fd4b254389122332181a7c3db7f27e918eec64e3",
        "generation_config.json",
        "speech_tokenizer/configuration.json",
        "speech_tokenizer/model.safetensors",
        "3500000000",
        "650000000",
        "KJV_QWEN_ASSET_MANIFEST.json",
        "ConvertTo-Json -Depth 8",
        "System.Text.UTF8Encoding",
        "WriteAllText($ManifestPath",
    ):
        assert token in script


def test_asset_preparation_pins_and_verifies_speaker_data_and_licenses():
    root = Path(__file__).resolve().parents[1]
    script = (root / "tools" / "prepare_assets.ps1").read_text(encoding="utf-8")
    for token in (
        "b09e308a3a1aafdb7d6c75baf0fe2a31d61601da",
        "25adc6c12d49f3328ddcb21436ff05ea03cdc390",
        "c6c7ddfcb419378b396a863abb312a727abbfcda",
        "3fd9f2363dab97473dcac24c7723b09ba6b9f295",
        "GLYSSEN_MIT.txt",
        "QWEN3_TTS_APACHE_2.0.txt",
    ):
        assert token in script
    assert "Get-GitBlobSha1" in script
    assert "KJV_QWEN_ASSET_MANIFEST.json" in script


def test_windows_build_prepares_pinned_assets_before_pyinstaller():
    root = Path(__file__).resolve().parents[1]
    script = (root / "tools" / "build_windows.ps1").read_text(encoding="utf-8")
    assert "pip install -e '.[qwen,dev]'" in script
    assert "prepare_assets.ps1" in script
    assert script.index("prepare_assets.ps1") < script.index("-m PyInstaller")
    assert "QWEN3_TTS_APACHE_2.0.txt" in script
    assert "KJV_QWEN_ASSET_MANIFEST.json" in script
    assert "speech_tokenizer_config_sha256" in script
    assert "Pinned Qwen model files no longer match" in script
    assert "qwen_asset_integrity.py" in script
    assert "verify --models-root $Models --manifest $AssetManifestPath" in script
    assert "Pinned Qwen weight SHA-256 or manifest verification failed" in script


def test_windows_build_requires_pinned_python_and_explicit_torch_variant():
    root = Path(__file__).resolve().parents[1]
    script = (root / "tools" / "build_windows.ps1").read_text(encoding="utf-8")
    for token in (
        "ValidateSet('cpu','cu128')",
        "PythonMinor -ne '3.12'",
        "PythonBits -ne '64'",
        "$TorchVersion = '2.10.0'",
        '"torch==$TorchVersion" "torchaudio==$TorchVersion"',
        "https://download.pytorch.org/whl/cpu",
        "https://download.pytorch.org/whl/cu128",
        "--collect-all huggingface_hub",
        "--collect-all torchaudio",
    ):
        assert token in script


def test_windows_build_fails_closed_without_verified_lgpl_ffmpeg():
    root = Path(__file__).resolve().parents[1]
    script = (root / "tools" / "build_windows.ps1").read_text(encoding="utf-8")
    for token in (
        "FFMPEG_LICENSE.txt",
        "FFMPEG_BUILD_MANIFEST.json",
        "Get-FileHash -Algorithm SHA256",
        "LGPL-2.1-or-later",
        "LGPL-3.0-or-later",
        "--enable-gpl|--enable-nonfree",
        "GNU Lesser General Public License",
        "ExpectedLicenseVersion",
        "LGPL-3.0-or-later",
        "license_sha256",
        "ActualLicenseHash",
        "libmp3lame",
        "probe.mp3",
        "-f null NUL",
    ):
        assert token in script
    assert "FFMPEG_BUILD_MANIFEST.template.json" in (root / "LICENSES" / "README_FFMPEG.md").read_text(encoding="utf-8") or \
        "FFMPEG_BUILD_MANIFEST.template.json" in (root / "LICENSES" / "FFMPEG_BUILD_MANIFEST.template.json").read_text(encoding="utf-8")


def test_project_version_is_consistent():
    root = Path(__file__).resolve().parents[1]
    pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
    package_init = (root / "src" / "kjv_audio_generator" / "__init__.py").read_text(encoding="utf-8")
    assert 'version = "0.4.12"' in pyproject
    assert '__version__ = "0.4.12"' in package_init


def test_hf_download_cli_version_stays_compatible_with_pinned_transformers():
    root = Path(__file__).resolve().parents[1]
    script = (root / "tools" / "prepare_assets.ps1").read_text(encoding="utf-8")
    pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
    assert "huggingface_hub>=0.34,<1.0" in script
    assert "transformers==4.57.3" in pyproject


def test_ffmpeg_documentation_records_a_pinned_lgplv3_candidate_without_claiming_binary_verification():
    root = Path(__file__).resolve().parents[1]
    readme = (root / "LICENSES" / "README_FFMPEG.md").read_text(encoding="utf-8")
    candidate_sha = "78d1f7728fef503b50a6de5866950a96d7e4db0fdb9dfaa47fc2c6691a48370b"
    source_commit = "b9ebe81995b58cd4e3177a6c0ad5dc2392f7f7fd"
    assert candidate_sha in readme
    assert source_commit in readme
    assert "--enable-version3" in readme
    assert "--enable-libmp3lame" in readme
    assert "confirmed both its byte length and SHA-256" in readme
    assert "not an approved app dependency" in readme


def test_windows_builder_requires_complete_hash_manifest_for_ffmpeg_dependency_notices():
    root = Path(__file__).resolve().parents[1]
    script = (root / "tools" / "build_windows.ps1").read_text(encoding="utf-8")
    assert "ffmpeg_notices.py') verify" in script
    importer = (root / "tools" / "import_ffmpeg_notices.ps1").read_text(encoding="utf-8")
    assert "ffmpeg_notices.py') import" in importer
    helper = (root / "tools" / "ffmpeg_notices.py").read_text(encoding="utf-8")
    for token in ("MANIFEST.json", "sha256", "unlisted", "is_symlink", "PurePosixPath"):
        assert token in helper


def test_ffmpeg_notice_import_and_verification_hash_every_file(tmp_path):
    import json
    import subprocess
    import sys

    root = Path(__file__).resolve().parents[1]
    source = tmp_path / "ffmpeg-package"
    (source / "doc" / "licenses").mkdir(parents=True)
    (source / "doc" / "README.txt").write_text("FFmpeg docs\n", encoding="utf-8")
    (source / "doc" / "licenses" / "libx.txt").write_text("Example dependency notice\n", encoding="utf-8")
    (source / "LICENSE.txt").write_text("GNU Lesser General Public License version 3\n", encoding="utf-8")
    licenses = tmp_path / "LICENSES"
    helper = root / "tools" / "ffmpeg_notices.py"
    imported = subprocess.run([sys.executable, str(helper), "import", "--source-package", str(source), "--licenses-dir", str(licenses)], capture_output=True, text=True)
    assert imported.returncode == 0, imported.stderr
    manifest_path = licenses / "FFMPEG_DEPENDENCY_NOTICES" / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert len(manifest["files"]) == 2
    verified = subprocess.run([sys.executable, str(helper), "verify", "--licenses-dir", str(licenses)], capture_output=True, text=True)
    assert verified.returncode == 0, verified.stderr

    altered = licenses / "FFMPEG_DEPENDENCY_NOTICES" / "README.txt"
    altered.write_text("XFmpeg docs\n", encoding="utf-8")
    rejected = subprocess.run([sys.executable, str(helper), "verify", "--licenses-dir", str(licenses)], capture_output=True, text=True)
    assert rejected.returncode == 2
    assert "SHA-256 mismatch" in rejected.stderr

    altered.write_text("FFmpeg docs\n", encoding="utf-8")
    (licenses / "FFMPEG_DEPENDENCY_NOTICES" / "extra.txt").write_text("unlisted\n", encoding="utf-8")
    rejected_extra = subprocess.run([sys.executable, str(helper), "verify", "--licenses-dir", str(licenses)], capture_output=True, text=True)
    assert rejected_extra.returncode == 2
    assert "unlisted" in rejected_extra.stderr


def test_ffmpeg_notice_import_rejects_symlinked_source_doc_or_license(tmp_path):
    import subprocess
    import sys

    root = Path(__file__).resolve().parents[1]
    package = tmp_path / "ffmpeg-package"
    external = tmp_path / "external-doc"
    external.mkdir()
    (external / "NOTICE.txt").write_text("external notice\n", encoding="utf-8")
    package.mkdir()
    (package / "LICENSE.txt").write_text("LGPL notice\n", encoding="utf-8")
    (package / "doc").symlink_to(external, target_is_directory=True)

    result = subprocess.run(
        [
            sys.executable,
            str(root / "tools" / "ffmpeg_notices.py"),
            "import",
            "--source-package",
            str(package),
            "--licenses-dir",
            str(tmp_path / "licenses"),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "must not be symlinks" in result.stderr


def test_ffmpeg_notice_verifier_rejects_malformed_manifest_entries(tmp_path):
    import json
    import subprocess
    import sys

    root = Path(__file__).resolve().parents[1]
    licenses = tmp_path / "LICENSES"
    notice_dir = licenses / "FFMPEG_DEPENDENCY_NOTICES"
    notice_dir.mkdir(parents=True)
    (licenses / "FFMPEG_LICENSE.txt").write_text("LGPL notice\n", encoding="utf-8")
    (notice_dir / "MANIFEST.json").write_text(
        json.dumps({"schema_version": 1, "files": ["not-an-object"]}),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(root / "tools" / "ffmpeg_notices.py"),
            "verify",
            "--licenses-dir",
            str(licenses),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "entries must be JSON objects" in result.stderr


def test_ffmpeg_notice_verifier_rejects_windows_unsafe_manifest_paths(tmp_path):
    import json
    import subprocess
    import sys

    root = Path(__file__).resolve().parents[1]
    helper = root / "tools" / "ffmpeg_notices.py"
    unsafe_paths = [
        "../escape.txt",
        "/absolute.txt",
        "C:/Windows/win.ini",
        "C:relative.txt",
        "//server/share/notice.txt",
        "NOTICE.txt:alternate-stream",
        "folder\\notice.txt",
        "CON.txt",
        "NUL",
        "COM1.txt",
        "LPT9.notice",
        "folder./notice.txt",
        "trailing-space /notice.txt",
        "folder//notice.txt",
        "./NOTICE.txt",
        "folder/../NOTICE.txt",
        "bad\x00name.txt",
    ]
    for index, unsafe_path in enumerate(unsafe_paths):
        licenses = tmp_path / f"licenses-{index}"
        notice_dir = licenses / "FFMPEG_DEPENDENCY_NOTICES"
        notice_dir.mkdir(parents=True)
        (licenses / "FFMPEG_LICENSE.txt").write_text("LGPL notice\\n", encoding="utf-8")
        (notice_dir / "MANIFEST.json").write_text(
            json.dumps({"schema_version": 1, "files": [{"path": unsafe_path, "bytes": 0, "sha256": "0" * 64}]}),
            encoding="utf-8",
        )
        result = subprocess.run(
            [sys.executable, str(helper), "verify", "--licenses-dir", str(licenses)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 2, (unsafe_path, result.stdout, result.stderr)
        assert "Unsafe" in result.stderr or "reserved" in result.stderr, (unsafe_path, result.stderr)


def test_ffmpeg_notice_verifier_rejects_windows_case_collisions(tmp_path):
    import json
    import subprocess
    import sys

    root = Path(__file__).resolve().parents[1]
    licenses = tmp_path / "LICENSES"
    notice_dir = licenses / "FFMPEG_DEPENDENCY_NOTICES"
    notice_dir.mkdir(parents=True)
    (licenses / "FFMPEG_LICENSE.txt").write_text("LGPL notice\\n", encoding="utf-8")
    (notice_dir / "Readme.txt").write_text("one\\n", encoding="utf-8")
    (notice_dir / "README.txt").write_text("two\\n", encoding="utf-8")
    (notice_dir / "MANIFEST.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "files": [
                    {"path": "Readme.txt", "bytes": (notice_dir / "Readme.txt").stat().st_size, "sha256": "0" * 64},
                    {"path": "README.txt", "bytes": (notice_dir / "README.txt").stat().st_size, "sha256": "0" * 64},
                ],
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, str(root / "tools" / "ffmpeg_notices.py"), "verify", "--licenses-dir", str(licenses)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "Windows-colliding" in result.stderr


def test_ffmpeg_notice_verifier_rejects_symlinked_manifest_license_and_notice_files(tmp_path):
    import json
    import subprocess
    import sys

    root = Path(__file__).resolve().parents[1]
    helper = root / "tools" / "ffmpeg_notices.py"

    for symlink_kind in ("manifest", "license", "notice"):
        case = tmp_path / symlink_kind
        licenses = case / "LICENSES"
        notice_dir = licenses / "FFMPEG_DEPENDENCY_NOTICES"
        notice_dir.mkdir(parents=True)
        outside = case / "outside.txt"
        outside.write_text("external notice\\n", encoding="utf-8")
        (notice_dir / "NOTICE.txt").write_text("inside notice\\n", encoding="utf-8")
        manifest_path = notice_dir / "MANIFEST.json"
        manifest_path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "files": [
                        {
                            "path": "NOTICE.txt",
                            "bytes": (notice_dir / "NOTICE.txt").stat().st_size,
                            "sha256": __import__("hashlib").sha256((notice_dir / "NOTICE.txt").read_bytes()).hexdigest(),
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        (licenses / "FFMPEG_LICENSE.txt").write_text("LGPL notice\\n", encoding="utf-8")

        if symlink_kind == "manifest":
            manifest_path.unlink()
            manifest_path.symlink_to(outside)
        elif symlink_kind == "license":
            (licenses / "FFMPEG_LICENSE.txt").unlink()
            (licenses / "FFMPEG_LICENSE.txt").symlink_to(outside)
        else:
            (notice_dir / "NOTICE.txt").unlink()
            (notice_dir / "NOTICE.txt").symlink_to(outside)

        result = subprocess.run(
            [sys.executable, str(helper), "verify", "--licenses-dir", str(licenses)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 2, (symlink_kind, result.stdout, result.stderr)
        assert "symlink" in result.stderr.lower(), (symlink_kind, result.stderr)


def test_ffmpeg_notice_import_rejects_windows_unsafe_and_reserved_source_paths(tmp_path):
    import subprocess
    import sys

    root = Path(__file__).resolve().parents[1]
    helper = root / "tools" / "ffmpeg_notices.py"
    source_names = ["NOTICE.txt:stream", "manifest.json"]
    if sys.platform != "win32":
        # Win32 normalizes trailing dot/space names and reserves DOS device
        # names before Python can create these exact path strings. Their raw
        # spelling is covered by the platform-independent validator test below.
        source_names.extend(("CON.txt", "trailing. "))
    for index, source_name in enumerate(source_names):
        package = tmp_path / f"package-{index}"
        (package / "doc").mkdir(parents=True)
        (package / "doc" / source_name).write_text("notice\\n", encoding="utf-8")
        (package / "LICENSE.txt").write_text("LGPL notice\\n", encoding="utf-8")
        licenses = tmp_path / f"licenses-{index}"
        result = subprocess.run(
            [sys.executable, str(helper), "import", "--source-package", str(package), "--licenses-dir", str(licenses)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 2, (source_name, result.stdout, result.stderr)
        assert any(token in result.stderr.lower() for token in ("unsafe", "reserved", "manifest.json", "alternate data streams")), (source_name, result.stderr)
        assert not (licenses / "FFMPEG_DEPENDENCY_NOTICES").exists()




def test_ffmpeg_notice_path_validator_rejects_windows_unsafe_raw_names():
    import pytest

    tool = _load_ffmpeg_notice_tool()
    for raw_name in ("NOTICE.txt:stream", "CON.txt", "NUL.bin", "LPT1.log", "trailing. "):
        with pytest.raises(ValueError):
            tool._validated_relative_path(raw_name)


def test_ffmpeg_notice_import_rejects_alternate_stream_on_source_license(tmp_path):
    if sys.platform != "win32":
        import pytest
        pytest.skip("NTFS alternate data streams are Windows-only")

    import subprocess
    import sys as python_sys
    root = Path(__file__).resolve().parents[1]
    helper = root / "tools" / "ffmpeg_notices.py"
    package = tmp_path / "package-with-license-stream"
    (package / "doc").mkdir(parents=True)
    (package / "doc" / "README.txt").write_text("notice\n", encoding="utf-8")
    license_file = package / "LICENSE.txt"
    license_file.write_text("LGPL license\n", encoding="utf-8")
    Path(str(license_file) + ":hidden").write_text("not part of the license\n", encoding="utf-8")
    result = subprocess.run(
        [python_sys.executable, str(helper), "import", "--source-package", str(package), "--licenses-dir", str(tmp_path / "licenses")],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2, (result.stdout, result.stderr)
    assert "alternate data streams" in result.stderr.lower()


def _load_ffmpeg_notice_tool():
    import importlib.util

    root = Path(__file__).resolve().parents[1]
    tool_path = root / "tools" / "ffmpeg_notices.py"
    spec = importlib.util.spec_from_file_location("ffmpeg_notices_under_test", tool_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _make_ffmpeg_package(root: Path, *, notice_text: str, license_text: str):
    (root / "doc" / "licenses").mkdir(parents=True)
    (root / "doc" / "README.txt").write_text(notice_text, encoding="utf-8")
    (root / "doc" / "licenses" / "libx.txt").write_text("dependency notice\n", encoding="utf-8")
    (root / "LICENSE.txt").write_text(license_text, encoding="utf-8")


def test_ffmpeg_notice_import_keeps_previous_bundle_if_staging_copy_fails(tmp_path, monkeypatch):
    import pytest

    tool = _load_ffmpeg_notice_tool()
    licenses = tmp_path / "LICENSES"
    old_package = tmp_path / "old-package"
    new_package = tmp_path / "new-package"
    _make_ffmpeg_package(old_package, notice_text="old notice\n", license_text="old LGPL\n")
    _make_ffmpeg_package(new_package, notice_text="new notice\n", license_text="new LGPL\n")

    tool.import_notices(old_package, licenses)
    old_manifest = (licenses / "FFMPEG_DEPENDENCY_NOTICES" / "MANIFEST.json").read_bytes()
    old_notice = (licenses / "FFMPEG_DEPENDENCY_NOTICES" / "README.txt").read_bytes()
    old_license = (licenses / "FFMPEG_LICENSE.txt").read_bytes()

    def fail_copytree(*_args, **_kwargs):
        raise OSError("injected staging copy failure")

    monkeypatch.setattr(tool.shutil, "copytree", fail_copytree)
    with pytest.raises(OSError, match="injected staging copy failure"):
        tool.import_notices(new_package, licenses)

    assert (licenses / "FFMPEG_DEPENDENCY_NOTICES" / "MANIFEST.json").read_bytes() == old_manifest
    assert (licenses / "FFMPEG_DEPENDENCY_NOTICES" / "README.txt").read_bytes() == old_notice
    assert (licenses / "FFMPEG_LICENSE.txt").read_bytes() == old_license
    assert not list(licenses.glob(".ffmpeg-notices-stage-*"))
    assert not list(licenses.glob(".ffmpeg-notices-backup-*"))


def test_ffmpeg_notice_import_rolls_back_if_pair_commit_fails(tmp_path, monkeypatch):
    import pytest

    tool = _load_ffmpeg_notice_tool()
    licenses = tmp_path / "LICENSES"
    old_package = tmp_path / "old-package"
    new_package = tmp_path / "new-package"
    _make_ffmpeg_package(old_package, notice_text="old notice\n", license_text="old LGPL\n")
    _make_ffmpeg_package(new_package, notice_text="new notice\n", license_text="new LGPL\n")

    tool.import_notices(old_package, licenses)
    old_manifest = (licenses / "FFMPEG_DEPENDENCY_NOTICES" / "MANIFEST.json").read_bytes()
    old_notice = (licenses / "FFMPEG_DEPENDENCY_NOTICES" / "README.txt").read_bytes()
    old_license = (licenses / "FFMPEG_LICENSE.txt").read_bytes()
    real_replace = tool.os.replace
    license_destination = licenses / "FFMPEG_LICENSE.txt"

    def fail_new_license_install(source, destination):
        source_path = Path(source)
        destination_path = Path(destination)
        if destination_path == license_destination and ".ffmpeg-notices-stage-" in str(source_path):
            raise OSError("injected staged license commit failure")
        return real_replace(source, destination)

    monkeypatch.setattr(tool.os, "replace", fail_new_license_install)
    with pytest.raises(OSError, match="injected staged license commit failure"):
        tool.import_notices(new_package, licenses)

    assert (licenses / "FFMPEG_DEPENDENCY_NOTICES" / "MANIFEST.json").read_bytes() == old_manifest
    assert (licenses / "FFMPEG_DEPENDENCY_NOTICES" / "README.txt").read_bytes() == old_notice
    assert (licenses / "FFMPEG_LICENSE.txt").read_bytes() == old_license
    assert tool.verify_notices(licenses)["ok"] is True
    assert not list(licenses.glob(".ffmpeg-notices-stage-*"))
    assert not list(licenses.glob(".ffmpeg-notices-backup-*"))


def test_ffmpeg_notice_import_successfully_replaces_old_bundle_as_a_set(tmp_path):
    tool = _load_ffmpeg_notice_tool()
    licenses = tmp_path / "LICENSES"
    old_package = tmp_path / "old-package"
    new_package = tmp_path / "new-package"
    _make_ffmpeg_package(old_package, notice_text="old notice\n", license_text="old LGPL\n")
    _make_ffmpeg_package(new_package, notice_text="new notice\n", license_text="new LGPL\n")

    tool.import_notices(old_package, licenses)
    (licenses / "FFMPEG_DEPENDENCY_NOTICES" / "stale-extra.txt").write_text("old extra\n", encoding="utf-8")
    result = tool.import_notices(new_package, licenses)

    assert (licenses / "FFMPEG_DEPENDENCY_NOTICES" / "README.txt").read_text(encoding="utf-8") == "new notice\n"
    assert not (licenses / "FFMPEG_DEPENDENCY_NOTICES" / "stale-extra.txt").exists()
    assert (licenses / "FFMPEG_LICENSE.txt").read_text(encoding="utf-8") == "new LGPL\n"
    assert len(result["files"]) == 2
    assert tool.verify_notices(licenses)["ok"] is True
    assert not list(licenses.glob(".ffmpeg-notices-stage-*"))
    assert not list(licenses.glob(".ffmpeg-notices-backup-*"))


def test_developer_test_dependencies_include_the_pytorch_adapter_runtime():
    root = Path(__file__).resolve().parents[1]
    pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
    dev_section = pyproject.split("dev = [", 1)[1].split("]", 1)[0]
    assert "pytest>=8" in dev_section
    assert "torch==2.10.0" in dev_section



def test_cross_platform_ci_installs_ffmpeg_before_running_audio_integration_tests():
    root = Path(__file__).resolve().parents[1]
    workflow = (root / ".github" / "workflows" / "tests.yml").read_text(encoding="utf-8")
    assert "choco install ffmpeg --yes --no-progress" in workflow
    assert "sudo apt-get install --yes xvfb ffmpeg" in workflow
    assert "FFmpeg for audio integration tests (CI only)" in workflow


def test_pinned_windows_ffmpeg_audit_is_digest_locked_and_runs_real_acceptance_checks():
    root = Path(__file__).resolve().parents[1]
    workflow = (root / ".github" / "workflows" / "ffmpeg-candidate-audit.yml").read_text(encoding="utf-8")
    script = (root / "tools" / "run_ffmpeg_candidate_audit.ps1").read_text(encoding="utf-8")
    for token in (
        "runs-on: windows-latest",
        "actions/upload-artifact@v4",
        "./tools/run_ffmpeg_candidate_audit.ps1",
    ):
        assert token in workflow
    assert chr(8) not in script
    for token in (
        "78d1f7728fef503b50a6de5866950a96d7e4db0fdb9dfaa47fc2c6691a48370b",
        "179056458",
        "b9ebe81995b58cd4e3177a6c0ad5dc2392f7f7fd",
        "Get-FileHash -Algorithm SHA256",
        "& $Ffmpeg -version",
        "& $Ffmpeg -L",
        "--enable-version3",
        "libmp3lame",
        "tools/import_ffmpeg_notices.ps1",
        "ffmpeg_notices.py",
        "probe.mp3",
        "-f null NUL",
        "FFMPEG_BUILD_MANIFEST.json",
    ):
        assert token in script

def test_windows_builder_uses_the_separate_pinned_ffmpeg_bootstrap_helper():
    root = Path(__file__).resolve().parents[1]
    builder = (root / "tools" / "build_windows.ps1").read_text(encoding="utf-8")
    helper = (root / "tools" / "ensure_ffmpeg.ps1").read_text(encoding="utf-8")
    for token in (
        "ensure_ffmpeg.ps1",
        "-Root $Root",
        "Pinned FFmpeg dependency bootstrap failed",
    ):
        assert token in builder
    for token in (
        "run_ffmpeg_candidate_audit.ps1",
        "GITHUB_WORKSPACE",
        "RUNNER_TEMP",
        "FFMPEG_BUILD_MANIFEST.json",
        "FFMPEG_DEPENDENCY_NOTICES/MANIFEST.json",
        "Copy-Item -LiteralPath $AuditedExecutable -Destination $Ffmpeg",
        "Pinned FFmpeg download/audit script failed",
    ):
        assert token in helper


def _run_powershell_script(executable, script_path, args, env):
    return subprocess.run(
        [executable, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script_path), *map(str, args)],
        text=True,
        capture_output=True,
        timeout=60,
        env=env,
        check=False,
    )


def test_windows_ffmpeg_bootstrap_copies_audited_outputs_and_restores_environment(tmp_path):
    if os.name != "nt":
        pytest.skip("Native PowerShell filesystem behavior is tested on Windows.")
    executable = shutil.which("pwsh") or shutil.which("powershell")
    if not executable:
        pytest.skip("PowerShell is not installed on this Windows runner.")

    root = tmp_path / "project"
    audit_output = root / "artifacts" / "ffmpeg-candidate-audit"
    licenses = root / "LICENSES"
    audit_output.mkdir(parents=True)
    licenses.mkdir(parents=True)
    bootstrap = Path(__file__).resolve().parents[1] / "tools" / "ensure_ffmpeg.ps1"
    audit_script = tmp_path / "fake-audit.ps1"
    audit_script.write_text(
        r"""
$ErrorActionPreference = 'Stop'
$workspace = $env:GITHUB_WORKSPACE
$output = Join-Path $workspace 'artifacts/ffmpeg-candidate-audit'
$licenses = Join-Path $workspace 'LICENSES'
New-Item -ItemType Directory -Force -Path $output | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $licenses 'FFMPEG_DEPENDENCY_NOTICES') | Out-Null
[System.IO.File]::WriteAllText((Join-Path $output 'ffmpeg.exe'), 'test-executable')
[System.IO.File]::WriteAllText((Join-Path $output 'FFMPEG_BUILD_MANIFEST.json'), '{"test":true}')
[System.IO.File]::WriteAllText((Join-Path $licenses 'FFMPEG_LICENSE.txt'), 'test-license')
[System.IO.File]::WriteAllText((Join-Path $licenses 'FFMPEG_DEPENDENCY_NOTICES/MANIFEST.json'), '{"files":[]}')
""".strip(),
        encoding="utf-8",
    )
    wrapper = tmp_path / "invoke-bootstrap.ps1"
    state_path = tmp_path / "environment.json"
    wrapper.write_text(
        r"""
param([string]$Bootstrap, [string]$Root, [string]$AuditScript, [string]$StatePath)
$ErrorActionPreference = 'Stop'
& $Bootstrap -Root $Root -AuditScript $AuditScript
if (-not $?) { throw 'Bootstrap helper did not complete.' }
@{
    workspace = [Environment]::GetEnvironmentVariable('GITHUB_WORKSPACE', 'Process')
    runner_temp = [Environment]::GetEnvironmentVariable('RUNNER_TEMP', 'Process')
} | ConvertTo-Json | Set-Content -LiteralPath $StatePath -Encoding UTF8
""".strip(),
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["GITHUB_WORKSPACE"] = "original-workspace"
    env["RUNNER_TEMP"] = "original-runner-temp"
    result = _run_powershell_script(executable, wrapper, [bootstrap, root, audit_script, state_path], env)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (root / "ffmpeg.exe").read_text(encoding="utf-8") == "test-executable"
    assert (licenses / "FFMPEG_BUILD_MANIFEST.json").read_text(encoding="utf-8") == '{"test":true}'
    assert (licenses / "FFMPEG_LICENSE.txt").read_text(encoding="utf-8") == "test-license"
    state = json.loads(state_path.read_text(encoding="utf-8-sig"))
    assert state == {"workspace": "original-workspace", "runner_temp": "original-runner-temp"}


def test_windows_ffmpeg_bootstrap_skips_when_all_inputs_already_exist(tmp_path):
    if os.name != "nt":
        pytest.skip("Native PowerShell filesystem behavior is tested on Windows.")
    executable = shutil.which("pwsh") or shutil.which("powershell")
    if not executable:
        pytest.skip("PowerShell is not installed on this Windows runner.")

    root = tmp_path / "project"
    licenses = root / "LICENSES"
    notices = licenses / "FFMPEG_DEPENDENCY_NOTICES"
    notices.mkdir(parents=True)
    (root / "ffmpeg.exe").write_text("existing-executable", encoding="utf-8")
    (licenses / "FFMPEG_BUILD_MANIFEST.json").write_text("{}", encoding="utf-8")
    (licenses / "FFMPEG_LICENSE.txt").write_text("license", encoding="utf-8")
    (notices / "MANIFEST.json").write_text('{"files":[]}', encoding="utf-8")
    bootstrap = Path(__file__).resolve().parents[1] / "tools" / "ensure_ffmpeg.ps1"
    audit_script = tmp_path / "should-not-run.ps1"
    marker = tmp_path / "audit-ran.txt"
    audit_script.write_text(
        '[System.IO.File]::WriteAllText(' + "'" + str(marker) + "'" + ', "called")',
        encoding="utf-8",
    )
    result = subprocess.run(
        [executable, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(bootstrap),
         "-Root", str(root), "-AuditScript", str(audit_script)],
        text=True,
        capture_output=True,
        timeout=60,
        env=os.environ.copy(),
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert (root / "ffmpeg.exe").read_text(encoding="utf-8") == "existing-executable"
    assert not marker.exists()
