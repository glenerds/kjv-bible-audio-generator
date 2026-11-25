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
