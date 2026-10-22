# Korean vehicle TTS comparison

[Korean guide](../../asset-guide/TTS_COMPARISON.md) · [24-output listening gallery](../../asset-guide/tts-comparison.html)

- `cases.json`: eight fixed texts and a separate synthetic reference text.
- `supertonic3.json`, `qwen17.json`, `cosyvoice3.json`: pinned revisions, voice/configuration, generation timing, output hashes and memory observations.
- `asr-diagnostic.json`: common Whisper re-transcription with explicit normalization; not a human listening/MOS test.
- `summary.json`: aggregate diagnostic counts and valid-output timing.
- `model-assets.json`, `environments/`: reviewed model revisions/files and installed packages.
- Model subdirectories: original PCM16 WAV outputs. `cosyvoice-reference-qwen-sohee.wav` is the additional synthetic reference.

All 24 attempts are retained, including CosyVoice's 0.08-second greeting failure. There is no selection of a best generation from multiple trials. The application TTS defaults are unchanged.
