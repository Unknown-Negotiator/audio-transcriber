#!/usr/bin/env python3
"""Fresh, sequential actual-CLI large-v3-turbo accuracy run on the fixed 32 English FLEURS clips.

Run prepare.py first. This runner never reads or resumes the Linux result files.
By default it refuses non-macOS hosts and any nonempty result directory.
"""
import argparse
import datetime
import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from score import aggregate, score

ROOT = Path(__file__).resolve().parent
EXPECTED_MANIFEST_SHA256 = 'ca824547c4c95c52e38de7a3385e8c87f89f1d353ea1c41a6f66e2a265fa7360'
EXPECTED_APP_SHA256 = '532b240122f6a3e1f8d405391bf0a5e864bb9ce6398a968625777415ffad53dd'
MODEL_REPO = 'dropbox-dash/faster-whisper-large-v3-turbo'
MODEL_REVISION = '0a363e9161cbc7ed1431c9597a8ceaf0c4f78fcf'
EXPECTED_MODEL_HASHES = {
    'config.json': 'b0253ea6c0d3bea6b1e19e91a02acfd3b53f4467362efcb5a3e6b16c9b3a9b7e',
    'model.bin': 'e76620f83d5f5b69efd3d87e3dc180c1bd21df9fbebacfd4335e5e1efcc018da',
    'preprocessor_config.json': '7ccc62c6f2765af1f3b46c00c9b5894426835a05021c8b9c01eecb6dfb542711',
    'tokenizer.json': '297b13372ac43916285644fb9687add3cc62ee2a1adb60da3dc25cc94c1871fd',
    'vocabulary.json': 'c69260f2ab26d659b7c398f9a2b2b48ed0df16c3b47d7326782fd9cba71690c1',
}


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def write_json(path, value):
    pending = path.with_suffix(path.suffix + '.tmp')
    pending.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    pending.replace(path)


def version(package):
    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app', type=Path, required=True)
    parser.add_argument('--model', type=Path, required=True, help='Existing pinned turbo model directory')
    parser.add_argument('--manifest', type=Path, default=ROOT / 'manifest.json')
    parser.add_argument('--audio-root', type=Path, default=ROOT)
    parser.add_argument('--results-dir', type=Path, default=ROOT / 'mac-results')
    parser.add_argument('--threads', type=int, default=4)
    parser.add_argument('--clip-timeout-seconds', type=float, default=600)
    parser.add_argument('--check-only', action='store_true', help='Validate inputs; do not run inference')
    parser.add_argument('--allow-non-macos', action='store_true', help='Explicit local development/smoke-test override; actual platform remains recorded')
    args = parser.parse_args(argv)
    for key in ['app', 'model', 'manifest', 'audio_root', 'results_dir']:
        setattr(args, key, getattr(args, key).expanduser().resolve())
    if args.threads < 1 or args.clip_timeout_seconds <= 0:
        raise ValueError('Thread count and clip timeout must be positive')
    if platform.system() != 'Darwin' and not args.allow_non_macos:
        raise ValueError('This run requires actual macOS; --allow-non-macos is only for explicitly labeled local checks')
    if args.results_dir == (ROOT / 'results').resolve() or (ROOT / 'results').resolve() in args.results_dir.parents:
        raise ValueError('Refusing to write inside the original Linux results directory')
    if args.results_dir.exists() and (not args.results_dir.is_dir() or any(args.results_dir.iterdir())):
        raise ValueError('Results directory must be absent or empty; existing results are never resumed or overwritten')
    if sha256(args.app) != EXPECTED_APP_SHA256:
        raise ValueError('Application source differs from the exact source used in the original 32-clip comparison')
    if sha256(args.manifest) != EXPECTED_MANIFEST_SHA256:
        raise ValueError('Manifest differs from the original fixed 32-clip selection; run the original prepare.py')
    manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
    samples = [sample for language in manifest['languages'] for sample in language['samples']]
    if len(samples) != 32 or any(sum(s['config'] == c for s in samples) != 32 for c in ['en_us']):
        raise ValueError('Expected exactly 32 English clips')
    for sample in samples:
        audio = (args.audio_root / sample['audio_path']).resolve()
        if args.audio_root not in audio.parents:
            raise ValueError('Audio path escapes the selected public-data directory')
        if sha256(audio) != sample['audio_sha256']:
            raise ValueError('Public audio hash mismatch: ' + sample['filename'])
    model_files = {}
    for name, expected in EXPECTED_MODEL_HASHES.items():
        file = args.model / name
        actual = sha256(file)
        if actual != expected:
            raise ValueError('Pinned model hash mismatch: ' + name)
        model_files[name] = {'sha256': actual, 'bytes': file.stat().st_size}
    args.results_dir.mkdir(parents=True, exist_ok=True)
    snapshot = args.results_dir / 'app_snapshot' / 'transcribe.py'
    snapshot.parent.mkdir()
    snapshot.write_bytes(args.app.read_bytes())
    if sha256(snapshot) != EXPECTED_APP_SHA256:
        raise ValueError('Application snapshot failed verification')
    metadata = {
        'schema_version': 1,
        'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'status': 'preflight_passed' if args.check_only else 'running',
        'inference_performed': False,
        'dataset': {k: manifest[k] for k in ['dataset', 'revision', 'split', 'license', 'selection_rule', 'selection_seed']},
        'manifest_sha256': sha256(args.manifest),
        'selected_clips': 32,
        'application': {
            'source_sha256': sha256(snapshot),
            'scorer_sha256': sha256(ROOT.parent / 'score.py'),
            'runner_sha256': sha256(Path(__file__).resolve()),
            'cli_template': 'python transcribe.py transcribe AUDIO --model MODEL --language en --threads THREADS --output OUTPUT',
            'settings': {'device': 'cpu', 'compute_type': 'int8', 'cpu_threads': args.threads, 'beam_size': 5, 'vad_filter': False, 'condition_on_previous_text': False, 'task': 'transcribe', 'language': 'explicit known language'},
        },
        'model': {'name': 'large-v3-turbo', 'repo_id': MODEL_REPO, 'revision': MODEL_REVISION, 'files': model_files},
        'environment': {
            'is_macos': platform.system() == 'Darwin',
            'system': platform.system(), 'release': platform.release(), 'version': platform.version(),
            'platform': platform.platform(), 'machine': platform.machine(), 'processor': platform.processor(),
            'macos_version': platform.mac_ver()[0], 'python': sys.version,
            'packages': {p: version(p) for p in ['faster-whisper', 'ctranslate2', 'av', 'numpy', 'huggingface-hub']},
            'github_actions': os.environ.get('GITHUB_ACTIONS') == 'true',
            'github_sha': os.environ.get('GITHUB_SHA'), 'github_run_id': os.environ.get('GITHUB_RUN_ID'),
            'runner_os': os.environ.get('RUNNER_OS'), 'runner_arch': os.environ.get('RUNNER_ARCH'),
        },
        'metric_definition': {
            'WER': 'Sum word substitutions + deletions + insertions, divided by summed reference words.',
            'CER': 'Same normalized-string minimum edit distance at character level, including single spaces.',
            'normalization': 'Identical score.py: Unicode NFKC/casefold; letters, marks and numbers retained; punctuation/symbols become spaces; collapse whitespace; accents and Cyrillic ё retained; no number-word conversion.',
        },
        'execution': 'Fresh CLI process per clip, sequential; no previous results reused; CPU int8; offline local model; wall time includes CLI/model startup.',
        'limits': ['Small fixed short-read-speech sample, not long-recording accuracy.', 'Languages explicitly supplied, not language-autodetection accuracy.', 'Public test partition is not proof of exclusion from model pretraining.', 'Punctuation, case and semantic correctness are not directly scored.'],
    }
    write_json(args.results_dir / 'run.json', metadata)
    if args.check_only:
        print('PREFLIGHT PASS: 32 public clip hashes, pinned turbo model and exact application source verified; no inference performed.', flush=True)
        return 0
    env = os.environ.copy()
    env.update({'HF_HUB_OFFLINE': '1', 'HF_HUB_DISABLE_TELEMETRY': '1', 'DO_NOT_TRACK': '1', 'OMP_NUM_THREADS': str(args.threads), 'MKL_NUM_THREADS': str(args.threads)})
    rows = []
    for index, sample in enumerate(samples, 1):
        audio = args.audio_root / sample['audio_path']
        destination = args.results_dir / 'turbo' / sample['config']
        destination.mkdir(parents=True, exist_ok=True)
        output = destination / (Path(sample['filename']).stem + '.txt')
        command = [sys.executable, str(snapshot), 'transcribe', str(audio), '--model', str(args.model), '--language', sample['language'], '--threads', str(args.threads), '--output', str(output)]
        start = time.monotonic()
        try:
            result = subprocess.run(command, env=env, capture_output=True, text=True, timeout=args.clip_timeout_seconds)
        except subprocess.TimeoutExpired:
            metadata.update({'status': 'failed', 'failure': {'config': sample['config'], 'filename': sample['filename'], 'reason': 'CLI timeout', 'timeout_seconds': args.clip_timeout_seconds}, 'completed_clips': len(rows)})
            write_json(args.results_dir / 'run.json', metadata)
            raise RuntimeError('CLI timed out on ' + sample['filename'])
        elapsed = time.monotonic() - start
        log = result.stdout + result.stderr
        for old, label in sorted([(str(args.results_dir), 'RESULTS'), (str(args.audio_root), 'AUDIO_ROOT'), (str(args.model), 'MODEL')], key=lambda x: -len(x[0])):
            log = log.replace(old, label)
        output.with_suffix('.log').write_text(log, encoding='utf-8')
        if result.returncode != 0 or not output.is_file():
            metadata.update({'status': 'failed', 'failure': {'config': sample['config'], 'filename': sample['filename'], 'returncode': result.returncode, 'reason': 'CLI failed or did not create output'}, 'completed_clips': len(rows)})
            write_json(args.results_dir / 'run.json', metadata)
            raise RuntimeError('CLI failed on ' + sample['filename'] + '; see per-clip log')
        if sha256(audio) != sample['audio_sha256']:
            raise ValueError('Source audio changed during inference')
        hypothesis = output.read_text(encoding='utf-8').strip()
        row = {k: sample[k] for k in ['config', 'filename', 'id', 'reference_raw', 'reference_dataset_normalized', 'audio_sha256']}
        row.update({'model': 'turbo', 'hypothesis': hypothesis, 'audio_seconds': sample['num_samples'] / 16000, 'wall_seconds': elapsed, 'returncode': result.returncode, 'source_unchanged': True, 'scores': score(sample['reference_dataset_normalized'], hypothesis)})
        with (args.results_dir / 'per_clip.jsonl').open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(row, ensure_ascii=False) + '\n')
        rows.append(row)
        metadata.update({'inference_performed': True, 'completed_clips': len(rows)})
        write_json(args.results_dir / 'run.json', metadata)
        print(f'turbo {index}/32 {sample["config"]} {sample["filename"]}: WER={row["scores"]["word"]["error_rate"]:.6f} CER={row["scores"]["character"]["error_rate"]:.6f} audio={row["audio_seconds"]:.2f}s wall={elapsed:.2f}s', flush=True)
    aggregates = {'turbo': {config: aggregate([r for r in rows if r['config'] == config]) for config in ['en_us']}}
    metadata.update({'status': 'completed', 'completed_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'completed_clips': len(rows), 'aggregate': aggregates})
    write_json(args.results_dir / 'results.json', {**metadata, 'clips': rows})
    write_json(args.results_dir / 'aggregate.json', metadata)
    write_json(args.results_dir / 'run.json', metadata)
    print('COMPLETE', json.dumps(aggregates, ensure_ascii=False), flush=True)
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (Exception, KeyboardInterrupt) as exc:
        print('ERROR: ' + str(exc or 'interrupted'), file=sys.stderr)
        sys.exit(1)
