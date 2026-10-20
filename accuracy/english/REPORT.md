# English validation: real macOS and known references

Validated 20 October 2026 with large-v3-turbo, CPU int8, four threads, beam size 5, VAD off, previous-text conditioning off, explicit English. No tuning or output correction was performed. Application SHA256: `532b240122f6a3e1f8d405391bf0a5e864bb9ce6398a968625777415ffad53dd`.

[Actual macOS CI run](https://github.com/Unknown-Negotiator/audio-transcriber/actions/runs/39510329161), commit `f8e92fde560f5063010a7a0b4908fb3df4c5d68a`, completed successfully on both hosted macOS 15.7.9 ARM64 and Intel x86_64. Each passed 13 regression tests and completed all 32 reference clips and the full long recording; accuracy is reported quantitatively, not as a pass/fail threshold. This is not a timing benchmark of a particular MacBook Air M1. No Apple GPU was used.

## 1. Accuracy against independently supplied transcripts

Google FLEURS English-US official test partition, pinned revision, 32 recordings / 31 distinct sentences, total 315.58 seconds and 748 normalized reference words. Selection used a fixed SHA-256 filename ranking before inference, without filtering by output or quality. The manifest, public source hashes and unmodified per-clip hypotheses are retained.

| Platform | Word error rate | Character error rate | Normalized exact-match clips |
|---|---:|---:|---:|
| macOS ARM64 | 54/748 = 7.219% | 148/4340 = 3.410% | 7/32 |
| macOS Intel | 54/748 = 7.219% | 148/4340 = 3.410% | 7/32 |
| Linux x86_64 | 54/748 = 7.219% | 148/4340 = 3.410% | 7/32 |

Equal aggregate rates do not imply identical transcripts. ARM differs from Linux in 3/32 raw outputs and Intel in 8/32; one normalized clip differs on both Macs (`Daru Ibadia` versus Linux `Daru Abadia`), with the same score against the reference. Other differences are case, punctuation or line breaks. WER/CER were independently recomputed with jiwer 4.0.0. Every clip, corpus rate, saved output, application snapshot and declared scorer/runner version was checked. Independent input rehashes used local copies of the pinned public corpus; remote input-integrity assertions come from the Mac runner metadata. Equally optimal character alignments can distribute substitutions/deletions/insertions differently while agreeing on total errors and rates; those ties are retained in the audit rather than hidden. Mac model hashes are verified by the runner; the actual remote model bytes were not downloaded again for a second independent local audit. Linux model bytes were independently rehashed.

Normalization: Unicode NFKC and casefold; punctuation/symbols become spaces; whitespace collapsed; letters, marks and numbers retained. No number-word equivalence or British/American spelling conversion. Character scoring includes normalized spaces. Thus `organised` versus `organized` and `hundred` versus `100` count as errors, alongside genuine recognition mistakes. WER is not a percentage of semantic meaning preserved and is not a full-file reliability guarantee.

Examples of genuine errors include proper names, `periodic table` becoming `PRI cable`, and missing words in the sentence about Vatican City's population. The sample is small, read speech rather than meetings, and public test membership does not prove exclusion from model pretraining. These rates must not be directly ranked against the different Russian/French samples.

## 2. Continuous 42-minute English recording

H. G. Wells, *The Time Machine*, LibriVox version 3, chapter 5, read by Mark Nelson. Single original human recording, not synthesized, looped, or stitched. Original MP3 duration is 2556.154875 seconds (42:36.155). It was remuxed without audio re-encoding into MKV to test the requested input format. Original download hash was checked before each Mac run. MKV container hashes differ between machines, consistent with remux metadata differences; each input's before/after hash is unchanged. Linux independently verified identical compressed audio and decoded PCM between MP3 and MKV.

| Platform | Full-file completion | Runtime | Peak process RSS |
|---|---|---:|---:|
| macOS ARM64 | Exit 0, output saved | 35:03.21 | 3.494 GB |
| macOS Intel | Exit 0, output saved | 18:10.05 | 3.624 GB |
| Linux x86_64 | Exit 0, output saved | 9:25.99 | 3.858 GB |

These are observed hosted-machine timings, not promised personal-laptop performance. Short-clip wall times include a fresh model load for every clip and should not be extrapolated to long-file throughput.

Beginning and ending book-body anchors and the closing chapter announcement appear in the outputs. Final approximately 11 seconds are below -40 dB in a separate analysis of the locally verified source signal, not a repeated inspection of the remote Mac waveform, consistent with the last speech timestamp around 2545.2 seconds. Timestamps are within decoded duration. The CI coverage helper used the catalog duration 2556.41 seconds, whereas the MKV probe reports 2556.134 seconds; independent checks use the actual probe. This supports processing extent, not proof that every spoken word was retained.

An additional comparison with the published book found high body-text agreement and no excess repeated 12/20-word phrases on all three platforms. Exploratory body-text word-edit ratios were 1.476% on ARM, 1.521% on Intel and 1.658% on Linux. It is explicitly **not ground-truth speech WER**: book editions, narration, chapter labels and announcements can differ. One 15-word book-only clause is also absent in a separate small-model excerpt transcription, supporting a possible narration/edition difference, not proving an ASR deletion. No manual exhaustive auditory adjudication was performed. The reference was never used to patch the output.

Two preliminary Linux full-file attempts were killed with signal 9 while the cloud machine's RAM-backed temporary filesystem was nearly full. The successful run moved public model storage and temporary PCM to disk, preserving model bytes and application code. This is a resource-environment recovery, not evidence that the application works without sufficient RAM/disk. All Mac runs succeeded without this issue.

## Reproduction and evidence

- `prepare.py` downloads the pinned public test corpus and recreates the deterministic selection.
- `benchmark.py` runs the actual final CLI in fresh processes and verifies source/model hashes.
- `verify_metrics.py` independently checks references, selection, saved hypotheses and jiwer metrics. Install jiwer 4.0.0 inside a test environment, run preparation, then supply `--results linux` or `--results macos-arm/accuracy` / `macos-intel/accuracy`.
- `.github/workflows/english-macos.yml` runs the complete hosted-macOS test.
- `macos-arm/`, `macos-intel/`, `linux/` retain metrics, outputs and independent audits. `long_provenance.json` and `LICENSE_DATA.md` identify public sources and licensing.

The long-run test harness blocks Python socket connections during transcription. This is not a native-code firewall or complete OS network audit. Models/dependencies/public test audio are downloaded separately before inference. No files from the user's computer were accessed or uploaded. No audio or weights are bundled with the repository or release ZIP.

English now has real long-file and independent-reference validation, not merely a synthetic smoke test. Recognition remains fallible; review names, numbers and consequential passages. No diarization, overlapping-speaker/noisy-meeting validation, automatic-language detection benchmark, or Apple GPU acceleration is claimed.
