# Local Audio Transcriber

Offline multilingual MKV/audio-to-TXT CLI using faster-whisper, CTranslate2 and PyAV.
No recordings are uploaded. Online model acquisition is an explicit separate command.

## Isolated setup

```sh
conda env create --prefix ./env --file environment.yml
conda activate ./env
python transcribe.py download-model --size large-v3-turbo --directory ./models/turbo
python transcribe.py transcribe recording.mkv --model ./models/turbo --language ru
```

Use `--language fr` for French, `en` for English, or omit for autodetection. `--timestamps` adds segment times. `--output path.txt` selects the output. Existing outputs are protected unless `--force` is supplied. Original media are never overwritten. No diarization is provided. Recognition can omit, mishear or hallucinate words: review important content.

Models: tiny, base, small, medium, large-v3, large-v3-turbo. Multilingual models are used. Approximate model disk sizes: small 486 MB; medium 1.53 GB; turbo 1.62 GB; large-v3 3.09 GB. Environment, caches and temporary audio require additional space. CPU int8 is used on all platforms; Apple GPU acceleration is not implemented.

The application decodes audio locally to temporary mono PCM WAV instead of lossy MP3. Allow about 115 MB of temporary WAV per hour plus model/runtime RAM. Conda package caches may live outside the environment according to Conda settings. No system Python installation is required.

## Verified CPU release

Tested on macOS 15.7.9 Apple Silicon ARM64 and Intel x86_64, and Linux, in isolated Conda environments. Full real Russian (32:45) and French (52:40) recordings completed with large-v3-turbo on both Mac architectures. The final timestamp patch additionally has a separate 13-test regression suite and real two-minute inference check. These are hosted machines, not a benchmark of your specific MacBook.

Accuracy was checked separately against known Google FLEURS transcripts. On the small 24-clip sample, turbo's word error rates were 1.46% Russian / 5.92% French on macOS ARM and 1.94% / 5.03% on Intel. This is not a guarantee for long recordings or meetings. The Linux comparison included small and medium as well. See [the full validation record](VALIDATION.md) for evidence, exact source versions, errors, storage and limits.

Start with large-v3-turbo for a quality-oriented choice; small remains available when resources matter more. Turbo weights use about 1.62 GB. Budget roughly 4–5 GB free for setup and working room, plus original media. Actual RAM can be several GB: full French peaked at about 2.90 GB process RSS on the ARM runner. This version uses CPU only, including on M1 Macs; no Apple GPU acceleration is claimed.

Recognition can omit or invent text. Final timestamp warnings retain the text for review rather than silently deleting it. No speaker labels are generated. Clean read-speech validation is not evidence of accuracy for overlapping conversations.

The offline test harness denies Python socket connections. This is not a native-code firewall or full OS network audit. Disconnect networking after setup for stricter local-use assurance. Initial dependency/model downloads require internet; subsequent transcription requires the local model and does not intentionally upload audio.

## Sources

- https://github.com/SYSTRAN/faster-whisper
- https://github.com/OpenNMT/CTranslate2
- https://github.com/PyAV-Org/PyAV
- https://huggingface.co/dropbox-dash/faster-whisper-large-v3-turbo
- https://archive.org/details/white_nights_librivox
- https://archive.org/details/madame_bovary_neb_librivox

The original CLI is MIT licensed. Dependencies, model weights and public audio retain their own licenses. The CI audio consists of human-read public-domain literary recordings, not conversational meeting recordings; this does not establish accuracy for overlapping speakers, accents or background noise.
