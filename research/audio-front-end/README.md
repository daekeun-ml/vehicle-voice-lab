# Experimental audio front end

See the [Korean design and evaluation notes](../../asset-guide/AUDIO_FRONTEND.md) and [audio A/B gallery](../../asset-guide/audio-lab.html#noise).

- `signal-metrics.json`: conservative DSP, clean references, synthetic-noise parameters, input hashes and processing metadata.
- `rnnoise-metrics.json`: same saved input WAVs through pyrnnoise; fixed 20 ms delay compensation calibrated on clean controls.
- `asr-diagnostic.json`, `rnnoise-asr.json`: Whisper transcripts and error rates against the clean-audio ASR proxy, **not human ground truth**.
- `summary.json`: improved/equal/worse proxy-transcription counts over the 12 noisy conditions.
- WAVs: 2 source clips, 12 synthetic noisy conditions, references and outputs. Not real cabin recordings.

These results do not enable preprocessing in the application. DSP source: [experimental_denoise.py](../../runtime/experimental_denoise.py).
