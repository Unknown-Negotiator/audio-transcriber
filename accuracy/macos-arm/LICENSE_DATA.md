# Data attribution and license

The audio references and raw reference transcripts in this benchmark come from Google FLEURS, revision 70bb2e84b976b7e960aa89f1c648e09c59f894dd, Russian (ru_ru) and French (fr_fr), official test partitions. Audio is not included in this small release bundle; prepare.py downloads it from the original source.

Source: https://huggingface.co/datasets/google/fleurs
License: Creative Commons Attribution 4.0 International (CC BY 4.0), https://creativecommons.org/licenses/by/4.0/
Attribution: Alexis Conneau, Min Ma, Simran Khanuja, Yu Zhang, Vera Axelrod, Siddharth Dalmia, Jason Riesa, Clara Rivera, and Ankur Bapna (2022). FLEURS: Few-shot Learning Evaluation of Universal Representations of Speech. https://arxiv.org/abs/2205.12446

Changes: a fixed 12-clip sample per language was selected from the original test sets. Raw reference text is retained; scoring-only normalized forms use Unicode normalization, casefolding, punctuation separation and whitespace collapsing, as documented in REPORT.md. Model hypotheses and evaluation metrics were added. This does not imply endorsement by the original dataset creators.

This data license is separate from the repository's source-code license.
