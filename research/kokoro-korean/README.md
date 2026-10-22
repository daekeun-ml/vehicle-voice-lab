# Kokoro Korean phoneme-input probe

See the [Korean write-up](../../asset-guide/KOKORO_KOREAN_TEST.md) and [listening gallery](../../asset-guide/audio-lab.html#kokoro).

- `probe.json`: pinned model/voice revision, package versions, attempted language codes, phonemes, output hashes and execution hardware.
- `asr-diagnostic.json`: Whisper re-transcriptions compared with authored text. Not a human listening test or MOS score.
- WAVs: 4 Korean phrases × 2 phoneme adapters × 2 non-Korean voices; 1 English synthesis control.

The experiment does not establish official Korean support and does not change the application's TTS provider. Model: [hexgrad/Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M), Apache-2.0 model card; voice IDs `af_heart` and `jf_alpha`.
