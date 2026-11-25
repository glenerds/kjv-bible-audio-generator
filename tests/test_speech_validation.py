from tools.verify_smoke_transcript import assess_transcript


EXPECTED = "This is a test of the King James Bible narrator voice."


def test_complete_qwen_smoke_transcript_passes():
    result = assess_transcript(
        EXPECTED,
        "This is a test of the King James Bible narrator voice.",
    )
    assert result["passed"] is True
    assert result["trailing_phrase_present"] is True
    assert result["similarity_ratio"] == 1.0


def test_qwen_smoke_truncated_at_king_james_bi_fails():
    result = assess_transcript(
        EXPECTED,
        "This is a test of the King James Bi",
    )
    assert result["passed"] is False
    assert result["trailing_phrase_present"] is False


def test_transcript_normalization_accepts_case_and_punctuation_changes():
    result = assess_transcript(
        EXPECTED,
        "THIS IS A TEST OF THE KING JAMES BIBLE NARRATOR VOICE!",
    )
    assert result["passed"] is True
    assert result["trailing_phrase_present"] is True


def test_transcript_missing_one_middle_word_keeps_suffix_and_passes_similarity_floor():
    result = assess_transcript(
        EXPECTED,
        "This is test of the King James Bible narrator voice.",
    )
    assert result["trailing_phrase_present"] is True
    assert result["passed"] is True

def test_windows_portable_app_upload_requires_both_final_mp3_transcripts():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    workflow = (root / ".github" / "workflows" / "windows-package-acceptance.yml").read_text(encoding="utf-8")

    verify_name = "- name: Verify complete spoken text from final packaged MP3s with pinned Whisper"
    app_upload_name = "- name: Upload verified Windows portable application"
    evidence_upload_name = "- name: Upload compact Windows package acceptance evidence"
    assert workflow.count(verify_name) == 1
    assert workflow.count(app_upload_name) == 1
    assert workflow.count(evidence_upload_name) == 1

    verify_at = workflow.index(verify_name)
    app_upload_at = workflow.index(app_upload_name)
    evidence_upload_at = workflow.index(evidence_upload_name)
    assert verify_at < app_upload_at < evidence_upload_at

    verify_step = workflow[verify_at:app_upload_at]
    app_upload_step = workflow[app_upload_at:evidence_upload_at]
    assert "if: success()" in verify_step
    assert verify_step.count("--audio") == 2
    assert "--expected-text" in verify_step
    assert "King James Bible narrator voice." in verify_step
    assert "if: success()" in app_upload_step
    assert "kjv-bible-audio-generator-portable-windows-x64" in app_upload_step
    assert "if: always()" in workflow[evidence_upload_at:]
