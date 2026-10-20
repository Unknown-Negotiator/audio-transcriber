#!/usr/bin/env python3
"""Local-only speech transcription. Model acquisition is a separate operation."""
import argparse
import os
from pathlib import Path
import sys
import tempfile


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    d = sub.add_parser('download-model', help='Explicit ONLINE setup: download model weights only')
    d.add_argument('--size', choices=['tiny', 'base', 'small', 'medium', 'large-v3', 'large-v3-turbo'], default='small')
    d.add_argument('--directory', type=Path, required=True)
    t = sub.add_parser('transcribe', help='OFFLINE: media audio to UTF-8 TXT')
    t.add_argument('input', type=Path)
    t.add_argument('--model', type=Path, required=True, help='Existing local model directory, not model name')
    t.add_argument('--output', type=Path, help='Default: input basename.txt')
    t.add_argument('--language', default=None, help='e.g. en, ru, fr; default autodetect')
    t.add_argument('--audio-track', type=int, default=0, help='Zero-based audio track index')
    t.add_argument('--threads', type=int, default=4)
    t.add_argument('--timestamps', action='store_true', help='Prefix paragraphs with timestamps')
    t.add_argument('--force', action='store_true', help='Replace an existing transcript')
    return p


def offline_mode():
    # Set before importing HF / Whisper. No model-name downloads are allowed.
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
    os.environ['DO_NOT_TRACK'] = '1'


def decode_audio(source, target, track):
    import av
    import wave
    if track < 0:
        raise ValueError('Audio track index must be nonnegative')
    with av.open(str(source)) as container, wave.open(str(target), 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        if track >= len(container.streams.audio):
            raise ValueError(f'Requested audio track {track}; file has {len(container.streams.audio)} audio tracks')
        resampler = None
        previous_format = None
        for frame in container.decode(container.streams.audio[track]):
            signature = (frame.sample_rate, frame.format.name, frame.layout.name)
            if signature != previous_format:
                if resampler is not None:
                    for out in resampler.resample(None):
                        wav.writeframes(out.to_ndarray().astype('<i2', copy=False).tobytes())
                resampler = av.AudioResampler(format='s16', layout='mono', rate=16000)
                previous_format = signature
            for out in resampler.resample(frame):
                wav.writeframes(out.to_ndarray().astype('<i2', copy=False).tobytes())
        if resampler is not None:
            for out in resampler.resample(None):
                wav.writeframes(out.to_ndarray().astype('<i2', copy=False).tobytes())


def bounded_timestamps(start, end, duration):
    """Keep displayed model estimates inside the actual audio extent."""
    import math
    start, end, duration = float(start), float(end), float(duration)
    if not all(math.isfinite(x) for x in (start, end, duration)) or duration < 0:
        raise ValueError('Invalid non-finite model timestamp or audio duration')
    start = min(max(start, 0.0), duration)
    end = min(max(float(end), start), float(duration))
    return start, end


def transcribe(args):
    offline_mode()
    source = args.input.expanduser().resolve()
    model_path = args.model.expanduser().resolve()
    output = (args.output or source.with_suffix('.txt')).expanduser().resolve()
    if not source.is_file():
        raise ValueError(f'Input file does not exist: {source}')
    if source == output:
        raise ValueError('Output must not overwrite the source media')
    if output.exists() and not args.force:
        raise ValueError(f'Output exists: {output}; choose another output or use --force')
    for name in ['model.bin', 'config.json', 'tokenizer.json']:
        if not (model_path / name).is_file():
            raise ValueError(f'Local model is incomplete: missing {name}. Run download-model during setup.')
    if args.threads < 1:
        raise ValueError('--threads must be positive')
    output.parent.mkdir(parents=True, exist_ok=True)
    from faster_whisper import WhisperModel
    print('Loading local model (CPU int8). No upload or model download.', file=sys.stderr)
    model = WhisperModel(str(model_path), device='cpu', compute_type='int8',
                         cpu_threads=args.threads, local_files_only=True)
    pending = None
    try:
        with tempfile.TemporaryDirectory(prefix='local-transcriber-') as td:
            wav = Path(td) / 'audio.wav'
            print('Decoding selected audio track to lossless PCM...', file=sys.stderr)
            decode_audio(source, wav, args.audio_track)
            # Decode WAV ourselves to avoid a second FFmpeg pass and version-specific PyAV APIs.
            import wave
            import numpy as np
            with wave.open(str(wav), 'rb') as audio_file:
                audio = np.frombuffer(audio_file.readframes(audio_file.getnframes()), dtype='<i2').astype(np.float32) / 32768.0
            decoded_duration = len(audio) / 16000.0
            segments, info = model.transcribe(audio, language=args.language, task='transcribe',
                beam_size=5, vad_filter=False, condition_on_previous_text=False)
            print(f'Language: {info.language}; audio duration: {info.duration:.1f}s', file=sys.stderr)
            # Same-filesystem temporary output; interruption never leaves a partial final TXT.
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=output.parent,
                                             prefix='.' + output.name + '.', delete=False) as f:
                pending = Path(f.name)
                for seg in segments:
                    text = seg.text.strip()
                    if text:
                        start, end = bounded_timestamps(seg.start, seg.end, decoded_duration)
                        if start != seg.start or end != seg.end:
                            print(f'Warning: unreliable model interval [{seg.start}, {seg.end}] for {decoded_duration:.2f}s audio; displayed times clipped to [{start}, {end}]. Text was retained and needs review against audio.', file=sys.stderr)
                        prefix = f'[{start:.2f}–{end:.2f}] ' if args.timestamps else ''
                        f.write(prefix + text + '\n')
                        f.flush()
                        print(f'Processed through {end:.1f}s', file=sys.stderr)
            if args.force:
                os.replace(pending, output)
            else:
                # Atomic creation without a race that could overwrite another process's result.
                os.link(pending, output)
                pending.unlink()
            pending = None
        print(f'Saved: {output}', file=sys.stderr)
    finally:
        if pending is not None:
            pending.unlink(missing_ok=True)


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == 'download-model':
            os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
            path = args.directory.expanduser().resolve()
            os.environ['HF_HOME'] = str(path.parent / '.download-cache')
            from huggingface_hub import snapshot_download
            if path.exists() and any(path.iterdir()):
                raise ValueError('Model destination must be absent or empty; use a fresh directory')
            print('ONLINE SETUP: downloading public model weights, no recordings are accessed.', file=sys.stderr)
            repo_id = ('dropbox-dash/faster-whisper-large-v3-turbo' if args.size == 'large-v3-turbo'
                       else f'Systran/faster-whisper-{args.size}')
            snapshot_download(repo_id=repo_id, local_dir=str(path),
                              allow_patterns=['model.bin', 'config.json', 'tokenizer.json', 'preprocessor_config.json', 'vocabulary.*'])
            print(f'Model saved: {path}')
        else:
            transcribe(args)
        return 0
    except (Exception, KeyboardInterrupt) as exc:
        print(f'Error: {exc or "interrupted"}', file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())
