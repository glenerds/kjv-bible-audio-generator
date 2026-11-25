from pathlib import Path

from tools.qwen_cross_chapter_voice_real import prompt_metadata_path


def test_qwen_prompt_metadata_path_matches_backend_suffix_convention(tmp_path):
    prompt = tmp_path / "narrator.prompt.pt"
    metadata = prompt_metadata_path(prompt)

    assert metadata == tmp_path / "narrator.prompt.prompt.json"
    assert metadata.name == "narrator.prompt.prompt.json"
