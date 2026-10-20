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

## Validation status

Linux regression and genuine human-read audiobook tests are in progress. macOS compatibility is not claimed until a linked Actions run passes. The macOS workflow tests Apple Silicon and Intel in isolated Conda environments using public Russian and French LibriVox recordings. Decoder-test fixtures are generated from synthetic tones and video in the runner; no audio binaries are stored in the repository. No personal recordings are included.

The offline test harness denies Python socket connections. This is not a native-code firewall or full OS network audit. Disconnect networking after setup for stricter local-use assurance.

## Sources

- https://github.com/SYSTRAN/faster-whisper
- https://github.com/OpenNMT/CTranslate2
- https://github.com/PyAV-Org/PyAV
- https://huggingface.co/dropbox-dash/faster-whisper-large-v3-turbo
- https://archive.org/details/white_nights_librivox
- https://archive.org/details/madame_bovary_neb_librivox

The original CLI is MIT licensed. Dependencies, model weights and public audio retain their own licenses. The CI audio consists of human-read public-domain literary recordings, not conversational meeting recordings; this does not establish accuracy for overlapping speakers, accents or background noise.
