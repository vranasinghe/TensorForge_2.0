"""Audit original workshop files without modifying them."""
import csv
import hashlib
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'TensorForge 2.0 - MVP Resources DataSet'


def load(split):
    with (DATA / f'{split}.jsonl').open(encoding='utf-8-sig') as f:
        return [json.loads(line) for line in f if line.strip()]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def template(row):
    text = unicodedata.normalize('NFC', row.get('subject', '') + '\n' + row['text']).casefold()
    return re.sub(r'\s+', ' ', re.sub(r'\d+', '<NUMBER>', text)).strip()


def audit():
    out = ROOT / 'experiments'
    out.mkdir(exist_ok=True)
    report = {'source': 'synthetic workshop data; not independently native-speaker reviewed',
              'hashes': {}, 'splits': {}}
    rows = {}
    for split in ('train', 'validation'):
        rows[split] = load(split)
        with (DATA / f'{split}.csv').open(encoding='utf-8-sig', newline='') as f:
            csv_rows = list(csv.DictReader(f))
        for r in csv_rows:
            r['secondary_category'] = r['secondary_category'] or None
            if r['is_urgent'] not in ('true', 'false'):
                raise ValueError('Unexpected CSV urgency value')
            r['is_urgent'] = r['is_urgent'] == 'true'
        csv_map = {r['ticket_id']: r for r in csv_rows}
        json_map = {r['ticket_id']: r for r in rows[split]}
        equivalent = csv_map == json_map and len(csv_rows) == len(rows[split])
        if not equivalent:
            raise ValueError(f'{split} CSV/JSONL mismatch')
        counts = lambda key: dict(Counter(str(r[key]) for r in rows[split]))
        lengths = sorted(len(r['text']) for r in rows[split])
        info = {'count': len(rows[split]), 'csv_jsonl_equivalent': equivalent,
                'duplicate_ids': len(rows[split]) - len(json_map),
                'nulls': {k: sum(r[k] is None or r[k] == '' for r in rows[split]) for k in rows[split][0]},
                'category': counts('category'), 'language': counts('language'), 'channel': counts('channel'),
                'urgency': counts('is_urgent'), 'secondary': counts('secondary_category'),
                'secondary_pairs': dict(Counter(f"{r['category']}->{r['secondary_category']}" for r in rows[split] if r['secondary_category'])),
                'intersections': dict(Counter(f"{r['language']}|{r['channel']}|{r['category']}" for r in rows[split])),
                'urgent_by_category': dict(Counter(r['category'] for r in rows[split] if r['is_urgent'])),
                'text_lengths': {'min': lengths[0], 'median': lengths[len(lengths)//2], 'p95': lengths[int(.95*len(lengths))], 'max': lengths[-1]},
                'not_nfc': sum(unicodedata.normalize('NFC', r['text']) != r['text'] for r in rows[split]),
                'combining_marks': sum(any(unicodedata.combining(c) for c in r['text']) for r in rows[split]),
                'invalid_labels': sum(bool(r['secondary_category'] == r['category'] or (r['category'] == 'spam_irrelevant' and (r['is_urgent'] or r['secondary_category']))) for r in rows[split])}
        report['splits'][split] = info
        for ext in ('csv', 'jsonl'):
            path = DATA / f'{split}.{ext}'
            report['hashes'][str(path.relative_to(ROOT))] = digest(path)
    train_text = {r['subject'] + '\n' + r['text'] for r in rows['train']}
    train_template = {template(r) for r in rows['train']}
    report['overlap'] = {'ticket_ids': len({r['ticket_id'] for r in rows['train']} & {r['ticket_id'] for r in rows['validation']}),
                         'exact_text_validation_rows': sum(r['subject'] + '\n' + r['text'] in train_text for r in rows['validation']),
                         'normalized_template_validation_rows': sum(template(r) in train_template for r in rows['validation'])}
    # Analysis only: this representation is never fitted or reused for prediction.
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.neighbors import NearestNeighbors
    vectorizer = TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 5), min_df=2, max_features=50000)
    x = vectorizer.fit_transform([template(r) for r in rows['train']])
    v = vectorizer.transform([template(r) for r in rows['validation']])
    distance, idx = NearestNeighbors(n_neighbors=1, metric='cosine', algorithm='brute').fit(x).kneighbors(v)
    similarities = 1 - distance[:, 0]
    report['near_duplicates'] = {'method': 'nearest training char_wb TF-IDF cosine; number masking and NFC; analysis only',
                                 'validation_similarity_ge_095': int((similarities >= .95).sum()),
                                 'validation_similarity_ge_090': int((similarities >= .90).sum()),
                                 'examples': [{'validation_id': rows['validation'][i]['ticket_id'], 'train_id': rows['train'][int(idx[i, 0])]['ticket_id'], 'similarity': float(similarities[i])} for i in similarities.argsort()[-10:][::-1]]}
    (out / 'audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('overlap', 'near_duplicates')}, ensure_ascii=True))
    print({s: {k: report['splits'][s][k] for k in ('count', 'csv_jsonl_equivalent', 'category', 'language', 'urgency', 'secondary_pairs')} for s in rows})
    return report


if __name__ == '__main__':
    audit()
