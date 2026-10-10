# Data audit

Command: `python -m training.audit`. Machine-readable source: experiments/audit.json.

- Train: 4,000; validation: 800; CSV/JSONL equivalence verified for every key column.
- Duplicate IDs: train 0, validation 0.
- Invalid secondary/spam label invariants: train 0, validation 0.
- Shared split IDs: 0; exact shared text rows: 0.
- Number-masked/NFC normalized shared templates: 0.
- Validation rows with nearest train char_wb cosine ≥0.90: 0.
- Detailed nulls, labels, lengths, Unicode normalization, language/channel/category intersections and hashes are saved in audit.json.

Similarity is heuristic, not proof of independence. All labels/text are synthetic;
native-speaker validation was not performed. No raw files were edited. Source/copy
SHA256 equality was checked for all 16 supplied API/data files.
