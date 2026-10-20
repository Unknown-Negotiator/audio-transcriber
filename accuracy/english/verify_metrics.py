#!/usr/bin/env python3
"""Independent, read-only benchmark-input audit and jiwer result verification.

Does not import the benchmark runner, score.py, or the application under test.
Writes only independent_* audit deliverables to a selected results directory.
"""
import argparse
import collections
import csv
import datetime
import hashlib
import importlib.metadata
import json
import math
import platform
import struct
import sys
import tarfile
import unicodedata
from pathlib import Path

import jiwer

EXPECTED_MANIFEST = 'ca824547c4c95c52e38de7a3385e8c87f89f1d353ea1c41a6f66e2a265fa7360'
EXPECTED_APP = '532b240122f6a3e1f8d405391bf0a5e864bb9ce6398a968625777415ffad53dd'
EXPECTED_REVISION = '70bb2e84b976b7e960aa89f1c648e09c59f894dd'

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def normalize(value):
    # Independent implementation of the declared metric contract.
    folded = unicodedata.normalize('NFKC', value).casefold()
    retained = []
    for character in folded:
        category = unicodedata.category(character)
        retained.append(character if category.startswith(('L', 'N', 'M')) else ' ')
    return ' '.join(''.join(retained).split())

def close(a, b):
    return math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-12)

def wav_info(data):
    assert data[:4] == b'RIFF' and data[8:12] == b'WAVE'
    assert struct.unpack_from('<I', data, 4)[0] + 8 == len(data)
    position, info = 12, {}
    while position + 8 <= len(data):
        tag = data[position:position + 4]
        length = struct.unpack_from('<I', data, position + 4)[0]
        body = data[position + 8:position + 8 + length]
        assert len(body) == length
        if tag == b'fmt ':
            fmt, channels, rate, byte_rate, block_align, bits = struct.unpack_from('<HHIIHH', body)
            info.update(format_code=fmt, channels=channels, sample_rate=rate,
                        byte_rate=byte_rate, block_align=block_align, bits_per_sample=bits)
        if tag == b'data':
            info['data_bytes'] = length
        position += 8 + length + length % 2
    info['frames'] = info['data_bytes'] // info['block_align']
    return info

def counts(result, ref, hyp, unit):
    n = len(ref.split()) if unit == 'word' else len(ref)
    hn = len(hyp.split()) if unit == 'word' else len(hyp)
    return {'substitutions': result.substitutions, 'deletions': result.deletions,
            'insertions': result.insertions, 'correct': result.hits,
            'reference_units': n, 'hypothesis_units': hn,
            'errors': result.substitutions + result.deletions + result.insertions,
            'error_rate': result.wer if unit == 'word' else result.cer}

def replay_word_operations(ref, hyp, operations):
    r, h = ref.split(), hyp.split()
    ri = hi = 0
    totals = collections.Counter()
    for operation in operations:
        rpos, hpos = operation['reference_index'], operation['hypothesis_index']
        assert rpos >= ri and hpos >= hi
        assert r[ri:rpos] == h[hi:hpos]
        totals['correct'] += rpos - ri
        ri, hi = rpos, hpos
        kind = operation['op']
        if kind == 'substitution':
            assert r[ri] == operation['reference'] and h[hi] == operation['hypothesis']
            assert r[ri] != h[hi]
            ri += 1
            hi += 1
            totals['substitutions'] += 1
        elif kind == 'deletion':
            assert r[ri] == operation['reference'] and operation['hypothesis'] == ''
            ri += 1
            totals['deletions'] += 1
        elif kind == 'insertion':
            assert h[hi] == operation['hypothesis'] and operation['reference'] == ''
            hi += 1
            totals['insertions'] += 1
        else:
            raise AssertionError('Unknown operation ' + kind)
    assert r[ri:] == h[hi:]
    totals['correct'] += len(r) - ri
    return dict(totals)

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, default=Path(__file__).resolve().parent)
    p.add_argument('--results', type=Path, required=True)
    p.add_argument('--preparation-only', action='store_true')
    p.add_argument('--skip-archive', action='store_true', help='Reuse independently verified source manifest; does not claim archive verification')
    args = p.parse_args()
    root, out = args.root.resolve(), args.results.resolve()
    manifest = json.loads((root / 'manifest.json').read_text())
    language = manifest['languages'][0]
    samples = language['samples']
    checks, issues, clips, ties = [], [], [], []
    def check(label, result, detail=None):
        checks.append({'check': label, 'passed': bool(result), **({'detail': detail} if detail is not None else {})})
        if not result:
            issues.append(label)
    check('manifest_expected_sha256', sha(root / 'manifest.json') == EXPECTED_MANIFEST)
    check('dataset_revision_and_split', manifest['dataset'] == 'google/fleurs' and manifest['revision'] == EXPECTED_REVISION and manifest['split'] == 'test')
    check('exactly_32_en_us_samples', len(samples) == 32 and all(s['config'] == 'en_us' and s['language'] == 'en' for s in samples))
    check('32_unique_filenames', len(set(s['filename'] for s in samples)) == 32)
    check('32_unique_input_hashes', len(set(s['audio_sha256'] for s in samples)) == 32)
    tsv = root / 'data/en_us/test.tsv'
    check('tsv_sha256_matches_manifest', sha(tsv) == language['tsv_sha256'])
    with tsv.open() as f:
        rows = list(csv.reader(f, delimiter='\t', quoting=csv.QUOTE_NONE))
    check('tsv_row_shape_and_count', len(rows) == language['test_rows'] == 647 and all(len(r) == 7 for r in rows))
    selected = sorted(enumerate(rows), key=lambda pair: hashlib.sha256((manifest['selection_seed'] + '\0en_us\0' + pair[1][1]).encode()).digest())[:32]
    check('selection_reproduced_without_results', [(i, r[1]) for i, r in selected] == [(s['original_tsv_row_0_based'], s['filename']) for s in samples])
    prerecord = json.loads((root / 'data/en_us/selection_before_inference.json').read_text())
    check('selection_before_inference_matches_manifest', [{k: s[k] for k in r} for s, r in zip(samples, prerecord)] == prerecord and len(prerecord) == len(samples))
    by_name = {s['filename']: s for s in samples}
    references, raw_norm_differences, audio_details = [], [], []
    for sample in samples:
        source = rows[sample['original_tsv_row_0_based']]
        expected = [str(sample['id']), sample['filename'], sample['reference_raw'], sample['reference_dataset_normalized'], None, str(sample['num_samples']), sample['gender']]
        check('tsv_exact_fields:' + sample['filename'], all(actual == desired for actual, desired in zip(source, expected) if desired is not None))
        data_path = root / sample['audio_path']
        data = data_path.read_bytes()
        check('input_sha256_and_bytes:' + sample['filename'], hashlib.sha256(data).hexdigest() == sample['audio_sha256'] and len(data) == sample['audio_bytes'])
        info = wav_info(data)
        check('wav_format_and_duration:' + sample['filename'], info['sample_rate'] == 16000 and info['channels'] == 1 and info['frames'] == sample['num_samples'] and info['format_code'] == 3 and info['bits_per_sample'] == 32)
        audio_details.append({'filename': sample['filename'], 'sha256': sample['audio_sha256'], **info})
        if normalize(sample['reference_raw']) != normalize(sample['reference_dataset_normalized']):
            raw_norm_differences.append(sample['filename'])
    check('raw_and_dataset_reference_normalization_equal', not raw_norm_differences, raw_norm_differences)
    if not args.skip_archive:
        archive = root / 'data/en_us/test.tar.gz'
        check('archive_sha256_matches_manifest', sha(archive) == language['archive_sha256'])
        members = collections.Counter()
        with tarfile.open(archive, 'r:gz') as tar:
            for member in tar:
                name = Path(member.name).name
                if name not in by_name:
                    continue
                members[name] += 1
                sample = by_name[name]
                check('archive_exact_audio_bytes:' + name, member.isfile() and member.name == sample['archive_member'] and tar.extractfile(member).read() == (root / sample['audio_path']).read_bytes())
        check('each_selected_archive_member_found_once', members == collections.Counter({s['filename']: 1 for s in samples}))
    report = {
        'auditor': 'Independent script without importing scorer, runner, or application',
        'audited_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'auditor_python': sys.version, 'jiwer_version': importlib.metadata.version('jiwer'),
        'rapidfuzz_version': importlib.metadata.version('rapidfuzz'),
        'manifest_sha256': sha(root / 'manifest.json'),
        'input_summary': {'recordings': len(samples), 'unique_recording_filenames': len(by_name), 'unique_sentence_ids': len(set(s['id'] for s in samples)), 'unique_normalized_references': len(set(normalize(s['reference_dataset_normalized']) for s in samples)), 'test_partition_recordings': len(rows), 'duration_seconds': sum(s['num_samples'] for s in samples)/16000, 'gender_counts': dict(collections.Counter(s['gender'] for s in samples)), 'normalization_raw_reference_differences': raw_norm_differences, 'archive_verified': not args.skip_archive},
        'method_review': {
            'selection': 'Outcome-independent seeded SHA-256 filename ranking; exact reproduction verified.',
            'reference': 'Scored against the original dataset normalized field, checked byte-for-byte against the pinned TSV. Independently normalizing raw references gives the same strings for all 32 clips.',
            'normalization': 'NFKC then casefold; keep Unicode letter/mark/number categories; replace all else with spaces and collapse whitespace. No numeric-word or lexical spelling equivalence.',
            'metrics': 'Per-clip minimum Levenshtein distance; micro-aggregate errors divided by reference units, not average clip rates. CER counts spaces.',
            'execution': 'Inspected runner launches actual snapshotted CLI in fresh sequential subprocesses, no resume; explicit en, CPU int8, beam 5, VAD off, previous-text conditioning off, offline local model.',
            'limitations': ['32 recordings but only 31 distinct source sentence IDs.', 'Read speech and explicit language only; not spontaneous speech, long-recording accuracy, language autodetection, or representative population performance.', 'Public official test partition does not prove exclusion from Whisper pretraining.', 'Case/punctuation are discarded; correctness is not semantic accuracy, and alternate spellings can count as errors.', 'Saved metadata and logs establish recorded provenance, not an independent network packet trace.']
        },
        'audio_inputs': audio_details,
    }
    if not args.preparation_only:
        run = json.loads((out / 'run.json').read_text())
        result = json.loads((out / 'results.json').read_text())
        aggregate_file = json.loads((out / 'aggregate.json').read_text())
        result_rows = [json.loads(line) for line in (out / 'per_clip.jsonl').read_text().splitlines() if line.strip()]
        check('run_completed_with_32_clips', run['status'] == 'completed' and run['completed_clips'] == 32 and run['inference_performed'] is True)
        check('results_equal_jsonl_exactly', result['clips'] == result_rows)
        check('metadata_equal_in_all_three_outputs', {k: v for k, v in result.items() if k != 'clips'} == run == aggregate_file)
        check('all_selected_clips_once_in_exact_order', [r['filename'] for r in result_rows] == [s['filename'] for s in samples])
        check('recorded_manifest_hash', run['manifest_sha256'] == EXPECTED_MANIFEST)
        check('snapshot_exact_expected_source', sha(out / 'app_snapshot/transcribe.py') == run['application']['source_sha256'] == EXPECTED_APP)
        check('current_source_same_as_run', sha(root.parent.parent / 'transcribe.py') == EXPECTED_APP)
        check('scorer_hash_unchanged', sha(root.parent / 'score.py') == run['application']['scorer_sha256'])
        check('runner_hash_unchanged', sha(root / 'benchmark.py') == run['application']['runner_sha256'])
        audit_aggregate = {unit: collections.Counter() for unit in ['word', 'character']}
        declared_aggregate = {unit: collections.Counter() for unit in ['word', 'character']}
        independently_normalized_refs, independently_normalized_hyps = [], []
        for index, (sample, row) in enumerate(zip(samples, result_rows)):
            name = sample['filename']
            check('result_manifest_fields:' + name, all(row[k] == sample[k] for k in ['config', 'filename', 'id', 'reference_raw', 'reference_dataset_normalized', 'audio_sha256']))
            output = out / 'turbo' / sample['config'] / (Path(name).stem + '.txt')
            saved = output.read_text(encoding='utf-8')
            check('saved_output_equals_hypothesis:' + name, saved.strip() == row['hypothesis'])
            check('successful_return_and_duration:' + name, row['returncode'] == 0 and row['source_unchanged'] is True and close(row['audio_seconds'], sample['num_samples']/16000))
            ref, hyp = normalize(sample['reference_dataset_normalized']), normalize(saved.strip())
            independently_normalized_refs.append(ref)
            independently_normalized_hyps.append(hyp)
            check('independent_normalization_matches:' + name, row['scores']['reference_normalized'] == ref and row['scores']['hypothesis_normalized'] == hyp)
            results = {'word': jiwer.process_words(ref, hyp), 'character': jiwer.process_characters(ref, hyp)}
            audit_clip = {'index': index+1, 'filename': name, 'output_sha256': sha(output), 'output_bytes': output.stat().st_size, 'hypothesis_equals_saved_output_after_declared_strip': saved.strip() == row['hypothesis'], 'reference_normalized': ref, 'hypothesis_normalized': hyp, 'metrics': {}}
            for unit, calculated in results.items():
                actual = counts(calculated, ref, hyp, unit)
                recorded = row['scores'][unit]
                audit_clip['metrics'][unit] = actual
                check('independent_' + unit + '_distance_and_rate:' + name, all(actual[k] == recorded[k] for k in ['errors', 'reference_units', 'hypothesis_units']) and close(actual['error_rate'], recorded['error_rate']))
                check('recorded_' + unit + '_count_invariants:' + name, recorded['correct'] + recorded['substitutions'] + recorded['deletions'] == actual['reference_units'] and recorded['correct'] + recorded['substitutions'] + recorded['insertions'] == actual['hypothesis_units'] and recorded['substitutions'] + recorded['deletions'] + recorded['insertions'] == actual['errors'])
                if any(actual[k] != recorded[k] for k in ['substitutions', 'deletions', 'insertions', 'correct']):
                    ties.append({'filename': name, 'unit': unit, 'jiwer': actual, 'recorded': {k: v for k, v in recorded.items() if k != 'operations'}, 'explanation': 'Same minimal edit distance/rate but equally optimal alignments can have different component counts.'})
                for k in ['substitutions', 'deletions', 'insertions', 'correct', 'reference_units', 'hypothesis_units', 'errors']:
                    audit_aggregate[unit][k] += actual[k]
                    declared_aggregate[unit][k] += recorded[k]
            try:
                replayed = replay_word_operations(ref, hyp, row['scores']['word']['operations'])
                valid = all(replayed.get(k, 0) == row['scores']['word'][k] for k in ['substitutions', 'deletions', 'insertions', 'correct'])
            except (AssertionError, IndexError, KeyError):
                valid = False
            check('word_operation_alignment_replays:' + name, valid)
            clips.append(audit_clip)
        aggregate = run['aggregate']['turbo']['en_us']
        independent_aggregate = {}
        for unit in ['word', 'character']:
            actual = dict(audit_aggregate[unit])
            actual['error_rate'] = actual['errors'] / actual['reference_units']
            independent_aggregate[unit] = actual
            recorded = aggregate[unit]
            check('aggregate_' + unit + '_sum_of_published_components', all(declared_aggregate[unit][k] == recorded[k] for k in declared_aggregate[unit]))
            check('aggregate_' + unit + '_independent_distance_and_rate', all(actual[k] == recorded[k] for k in ['errors', 'reference_units', 'hypothesis_units']) and close(actual['error_rate'], recorded['error_rate']))
        corpus_word = jiwer.process_words(independently_normalized_refs, independently_normalized_hyps)
        corpus_character = jiwer.process_characters(independently_normalized_refs, independently_normalized_hyps)
        check('jiwer_full_corpus_word_rate', close(corpus_word.wer, aggregate['word']['error_rate']))
        check('jiwer_full_corpus_character_rate', close(corpus_character.cer, aggregate['character']['error_rate']))
        duration = sum(s['num_samples'] for s in samples) / 16000
        wall = sum(r['wall_seconds'] for r in result_rows)
        exact = sum(r == h for r, h in zip(independently_normalized_refs, independently_normalized_hyps))
        check('aggregate_duration_wall_and_exact_matches', aggregate['clips'] == 32 and close(aggregate['audio_seconds'], duration) and close(aggregate['cli_wall_seconds'], wall) and close(aggregate['real_time_factor_including_cli_startup'], wall/duration) and aggregate['normalized_exact_match_clips'] == exact)
        report.update(run_environment=run['environment'], recorded_source_hash=run['application']['source_sha256'], result_artifact_hashes={n: sha(out/n) for n in ['run.json', 'results.json', 'aggregate.json', 'per_clip.jsonl']}, verified_clips=len(clips), independent_aggregate=independent_aggregate, normalized_exact_match_clips=exact, alignment_tie_differences=ties, per_clip=clips)
        errors = [r for r in result_rows if r['scores']['word']['errors']]
        errors.sort(key=lambda r: (-r['scores']['word']['errors'], -r['scores']['word']['error_rate'], r['filename']))
        analysis = [f"Independent English benchmark error review ({run['environment']['system']} / {run['environment']['machine']})", '', f"32 distinct recordings, 31 distinct sentence IDs; {duration:.2f} seconds of public FLEURS English-US read speech.", f"WER {100*independent_aggregate['word']['error_rate']:.6f}% ({independent_aggregate['word']['errors']}/{independent_aggregate['word']['reference_units']}); CER {100*independent_aggregate['character']['error_rate']:.6f}% ({independent_aggregate['character']['errors']}/{independent_aggregate['character']['reference_units']}, spaces included).", f"{exact}/32 normalized exact matches. Not perfect recognition. Every clip's WER/CER and the corpus rates were independently recalculated with jiwer {importlib.metadata.version('jiwer')}.", '', 'Representative largest word-error clips (chosen by error count, not used for sample selection):']
        for row in errors[:8]:
            analysis.extend(['', row['filename'] + f" | WER {100*row['scores']['word']['error_rate']:.2f}% ({row['scores']['word']['errors']}/{row['scores']['word']['reference_units']})", 'Reference: ' + row['reference_raw'], 'Hypothesis: ' + row['hypothesis'], 'Word edits: ' + '; '.join(f"{op['op']}: {op['reference']!r} -> {op['hypothesis']!r}" for op in row['scores']['word']['operations'])])
        analysis.extend(['', 'Interpretation limits:', '- These are text/reference comparisons, not a fresh human auditory adjudication of the recordings.', '- WER penalizes alternative spellings and lexical/number formatting; this normalization does not equate numeric tokens with number words.', '- Public test membership does not establish exclusion from pretraining. Short read speech does not establish long-recording or spontaneous speech accuracy.', '- Different minimal alignments may allocate the same edit distance differently among substitutions/deletions/insertions. ' + str(len(ties)) + ' such per-clip component discrepancies versus jiwer were observed.'])
        (out / 'independent_error_analysis.txt').write_text('\n'.join(analysis) + '\n')
    report.update(status='passed' if not issues else 'failed', checks=checks, check_count=len(checks), failed_checks=issues)
    target = out / ('independent_preparation_audit.json' if args.preparation_only else 'independent_verification.json')
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'status': report['status'], 'checks': len(checks), 'failed_checks': issues, 'path': str(target), 'independent_aggregate': report.get('independent_aggregate'), 'alignment_tie_differences': len(ties)}, indent=2))
    return 0 if not issues else 1

if __name__ == '__main__':
    sys.exit(main())
