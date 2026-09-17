"""Build a current-only Hugging Face Parquet release and exact evaluation archive."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import tarfile

import pyarrow.parquet as pq
from datasets import Dataset, Features, Image, Value
from scripts.final_benchmark.clean_release import verify_clean
from scripts.evaluation.migrate_token_router import verify_images


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def export(dataset, output):
    dataset, output = Path(dataset).resolve(), Path(output).resolve()
    verify_clean(dataset, write_report=False)
    rows = [json.loads(s) for s in (dataset/'validation_release/val.candidates.jsonl').read_text().splitlines()]
    verify_images(dataset, rows)
    if output.exists():
        raise ValueError('Use an empty output directory to avoid mixing dataset versions')
    (output/'data').mkdir(parents=True)
    names = ['id', 'base_id', 'case_id', 'query', 'answer', 'query_language', 'image_language',
             'answer_language', 'visual_kind', 'source', 'configuration', 'image_sha256']
    if any('visual_family' in row for row in rows):
        names.append('visual_family')
    features = Features({**{k: Value('string') for k in names}, 'image': Image(),
                         'source_context': Value('string'), 'metadata_json': Value('string')})
    shard_size = 400
    n = (len(rows)+shard_size-1)//shard_size
    for i in range(n):
        path = output/'data'/('validation-%05d-of-%05d.parquet' % (i,n))
        with pq.ParquetWriter(path, features.arrow_schema, compression='zstd') as writer:
            for start in range(i*shard_size, min((i+1)*shard_size,len(rows)), 32):
                batch = []
                for row in rows[start:min(start+32,(i+1)*shard_size)]:
                    record = {k: row[k] for k in names}
                    record['image'] = {'bytes': (dataset/'validation_release'/row['image_path']).read_bytes(),
                                       'path': row['case_id']+'_'+row['image_language']+'.png'}
                    record['source_context'] = '\n\n'.join(p['text'] for p in row.get('source_context',{}).get('paragraphs',[]))
                    record['metadata_json'] = json.dumps(row, ensure_ascii=False, sort_keys=True)
                    batch.append(record)
                writer.write_table(Dataset.from_list(batch, features=features).data.table)
        print('Wrote',path.name,flush=True)
    assets = output/'artifacts'; assets.mkdir()
    with tarfile.open(assets/'mstructqa-current.tar.gz','w:gz',compresslevel=1) as tar:
        tar.add(dataset,arcname='mstructqa-current',recursive=True)
    manifest = {'schema':'mstructqa-hf-v1','split':'validation','variants':len(rows),
                'base_questions':len({r['base_id'] for r in rows}),
                'visuals':len({(r['case_id'],r['image_language']) for r in rows}),
                'languages':sorted({r['image_language'] for r in rows}),
                'sources':dict(Counter(r['source'] for r in rows)),
                'visual_kind_counts':dict(Counter(r['visual_kind'] for r in rows)),
                'references_sha256':sha(dataset/'validation_release/val.candidates.jsonl'),
                'files':{str(p.relative_to(output)):sha(p) for p in sorted(output.rglob('*')) if p.is_file()}}
    (output/'release.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    # Round-trip every ID, reference and image hash; never publish an unchecked conversion.
    position=0
    for path in sorted((output/'data').glob('*.parquet')):
        for batch in pq.ParquetFile(path).iter_batches(batch_size=32):
            for row in batch.to_pylist():
                original=rows[position]
                assert json.loads(row['metadata_json'])==original
                assert row['id']==original['id'] and row['answer']==original['answer']
                assert hashlib.sha256(row['image']['bytes']).hexdigest()==original['image_sha256']
                position+=1
    assert position==len(rows)
    print('Verified',position,'QA and all embedded image hashes',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dataset',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();export(a.dataset,a.output)
