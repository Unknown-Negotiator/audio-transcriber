# Actual macOS ARM transcription accuracy

Date: 2026-10-20. Model: Whisper large-v3-turbo, CPU int8, four threads. This is a separate actual macOS run, not a relabeled Linux result.

The saved GitHub Actions artifact reports macOS 15.7.9, Darwin 24.6.0, arm64 / ARM64, run 39502317919, commit d010817a4be599ef39354b441d21ef354741822c. All 24 sequential application CLI invocations completed successfully: the same fixed 12 Russian and 12 French human-recorded FLEURS clips used in the original comparison.

| Language | Word error rate | Character error rate | Word errors / reference words | Word substitutions / deletions / insertions |
|---|---:|---:|---:|---:|
| Russian | 1.46% | 0.85% | 3 / 206 | 2 / 1 / 0 |
| French | 5.92% | 2.25% | 20 / 338 | 16 / 2 / 2 |

## Independent verification

jiwer 4.0.0 independently reproduced every one of the 24 word/character edit totals and both language-level WER/CER aggregates, within 1e-12. Saved transcript files, per-clip JSON, aggregate JSON and the full result agree. `metric_verification.json` documents the checks.

The application snapshot, all 24 reference pairs and reported audio hashes, all five model-file hashes, model revision, decoding settings and recorded package versions match the original Linux comparison. The scorer and Mac-runner hashes also match their retained source files. Model and audio hashes were verified on the Mac by the runner; this additional check compared the saved artifact's recorded hashes to the original inputs and results. Large model/audio files were not present in the downloaded artifact.

## The results are not cross-platform-identical

All 12 normalized Russian outputs match Linux. Three of the 12 normalized French outputs differ, so only 21 of 24 outputs match overall. French WER rose from 5.03% on Linux to 5.92% on this ARM run; CER rose from 1.89% to 2.25%.

- One place-name spelling changed without changing that clip's total word-error count.
- `États` became `Etats`, adding one scored word error because the normalization preserves accents.
- Reference `était entreposé roulé` became `est être entreposé roulé`, adding two word errors relative to the Linux output.

Full changed clips and both sets of metrics are in `comparison_to_linux.json`. The cause of these differences was not isolated; identical weights, input files and package versions do not establish identical numerical execution across hardware.

## Scope and source

These are short read-speech clips with the known language supplied explicitly. This does not establish accuracy throughout long videos, noisy conversations or the user's recordings, and it does not test automatic language detection. Punctuation and case are ignored; accents and number-word differences are not. This note covers ARM only and makes no claim about Intel results.

Source: [Google FLEURS](https://huggingface.co/datasets/google/fleurs), official test split, revision 70bb2e84b976b7e960aa89f1c648e09c59f894dd, under CC BY 4.0. See `LICENSE_DATA.md` for attribution. `results.json` includes all 24 reference/hypothesis pairs and per-clip counts; `aggregate.json` provides the compact result. No new inference was performed during this independent check.
