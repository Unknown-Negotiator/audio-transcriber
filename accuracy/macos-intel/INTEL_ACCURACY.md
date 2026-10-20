# Actual macOS Intel transcription accuracy

Date: 2026-10-20. Model: Whisper large-v3-turbo, CPU int8, four threads. This is a separate actual Intel macOS run, not a relabeled Linux or ARM result.

The saved GitHub Actions artifact reports macOS 15.7.9, Darwin 24.6.0, x86_64 / X64, run 39502317919, commit d010817a4be599ef39354b441d21ef354741822c. All 24 sequential application CLI invocations completed successfully: the same fixed 12 Russian and 12 French human-recorded FLEURS clips used in the Linux and ARM comparisons.

| Language | Word error rate | Character error rate | Word errors / reference words | Word substitutions / deletions / insertions |
|---|---:|---:|---:|---:|
| Russian | 1.94% | 0.92% | 4 / 206 | 3 / 1 / 0 |
| French | 5.03% | 1.84% | 17 / 338 | 14 / 2 / 1 |

## Independent verification

jiwer 4.0.0 independently reproduced all 24 word/character edit totals and both language-level WER/CER aggregates, within 1e-12. Saved transcript files, per-clip JSON, aggregate JSON and the full result agree. `metric_verification.json` documents the checks.

The application snapshot, all 24 reference pairs and reported audio hashes, all five model-file hashes, model revision, decoding settings and recorded package versions match the original Linux comparison. The scorer and Mac-runner hashes also match their retained source files. Model/audio hashes were checked on the Mac by the runner; this additional verification compared the recorded hashes with the original inputs and results. Large model/audio files were not included in the downloaded artifact.

## The results are not cross-platform-identical

Three normalized outputs differ from Linux: one Russian clip and two French clips. Only 21 of 24 match overall. Russian WER increased from 1.46% on Linux to 1.94% here. French WER is numerically equal at 5.03%, but that does not mean the French outputs are identical: CER changed from 1.89% to 1.84%.

- Russian `железа` became `железо`, adding one word error compared with the Linux output.
- French `mengal` became `bengal`; both still differ from reference `Bengale` under the stated normalization, so the word-error count is unchanged while character errors decrease by one.
- One French place-name spelling changed without changing that clip's total word-error count.

Compared with the actual ARM run, four normalized clips differ: one Russian and three French. ARM measured Russian WER/CER of 1.46%/0.85% and French 5.92%/2.25%. These small-sample differences do not establish a general accuracy ranking between platforms.

`comparison_to_linux.json` and `comparison_to_arm.json` contain all changed clips. The cause of the differences was not isolated. Identical weights, inputs and recorded package versions do not establish identical numerical execution across hardware.

## Scope and source

These short read-speech clips use explicitly supplied languages. The check does not establish word-level accuracy throughout long videos, noisy conversations or the user's recordings, and does not test language autodetection. Punctuation and case are ignored; accents and number-word differences are not. Long-file completion testing is a separate task and is not established by this note.

Source: [Google FLEURS](https://huggingface.co/datasets/google/fleurs), official test split, revision 70bb2e84b976b7e960aa89f1c648e09c59f894dd, under CC BY 4.0. See `LICENSE_DATA.md` for attribution. `results.json` includes all 24 reference/hypothesis pairs and counts; `aggregate.json` provides the compact result. No new inference was performed during this independent check.
