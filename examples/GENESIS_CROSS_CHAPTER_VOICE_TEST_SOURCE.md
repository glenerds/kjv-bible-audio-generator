# Cross-chapter narrator identity fixture

This is a deliberately minimal, real-KJV integration fixture for testing that a recurring
speaker keeps the same prepared Qwen voice prompt when a single queue processes more than
one chapter. It is **not** a Bible import and must not be used as a replacement for complete
scripture.

It contains two exact KJV verses:
- Genesis 1:1 — narrator only.
- Genesis 2:23 — narrator introduction followed by Adam's direct speech, manually split
  for this speaker-identity test.

The text was cross-checked against the public KJV corpus at
https://github.com/renniemaharaj/kjv-bible (file `Genesis.json`). All 31 verses in the
project's existing Genesis 1 acceptance fixture were compared against that corpus with no
text differences; Genesis 2:23 was taken from the same book JSON. The second verse is split
in the test script without changing any character of the source verse.

The test runs one real `ChapterWorker` across both chapter records using the production
`QwenVoiceBackend`. It checks that the narrator prompt-file SHA-256 is identical at the
narrator synthesis in Genesis 1 and Genesis 2, the narrator profile fingerprint is unchanged,
the narrator is prepared once, both chapter MP3s decode, and all cue text is preserved.

This is a narrow voice-prompt continuity check, not perceptual voice-quality approval and
not a Bible-wide speaker attribution test.
