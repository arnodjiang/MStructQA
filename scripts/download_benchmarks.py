"""Download pinned public benchmark files, verify upstream hashes, and retain manifests."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import subprocess
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
REPOS = ['terryoo/TableVQA-Bench', 'princeton-nlp/CharXiv',
         'ahmed-masry/ChartQAPro', 'AI-4-Everyone/Visual-TableQA',
         'HuggingFaceM4/ChartQA', 'MMTU-benchmark/MMTU']


def selected(repo, name):
    if name == 'README.md':
        return True
    if repo.endswith('/CharXiv'):
        return name == 'val.parquet'
    if repo.endswith('/ChartQA'):
        return name.startswith('data/test-') and name.endswith('.parquet')
    return name.endswith('.parquet')


def download(job):
    repo, revision, item = job
    name = item['rfilename']
    dest = ROOT / 'data/raw' / repo.split('/')[-1] / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    size = item['size']
    if not dest.exists() or dest.stat().st_size != size:
        part = Path(str(dest) + '.part')
        url = f'https://huggingface.co/datasets/{repo}/resolve/{revision}/{quote(name)}?download=true'
        print('DOWNLOADING', repo, name, size, flush=True)
        subprocess.run(['curl', '--http1.1', '-fLsS', '--retry', '5', '--retry-all-errors', '--retry-delay', '3',
                        '--connect-timeout', '30', '--max-time', '3600',
                        '-C', '-', '-o', str(part), url], check=True)
        if part.stat().st_size != size:
            raise ValueError(f'Size mismatch: {part}')
        part.replace(dest)
    sha = hashlib.sha256()
    gitsha = hashlib.sha1(f'blob {size}\0'.encode())
    with dest.open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            sha.update(block)
            gitsha.update(block)
    expected = item.get('lfs', {}).get('sha256')
    if expected and sha.hexdigest() != expected:
        raise ValueError(f'SHA256 mismatch: {dest}')
    if not expected and item.get('blobId') and gitsha.hexdigest() != item['blobId']:
        raise ValueError(f'Git blob hash mismatch: {dest}')
    record = dict(repo=repo, revision=revision, file=name, bytes=size,
                  sha256=sha.hexdigest(), upstream_hash_verified=True,
                  local_path=str(dest.relative_to(ROOT)))
    print('VERIFIED', repo, name, flush=True)
    return record


def main():
    jobs = []
    for repo in REPOS:
        metadata_path = ROOT / 'data/metadata' / (repo.split('/')[-1] + '.json')
        if metadata_path.exists():
            meta = json.loads(metadata_path.read_text())
        else:
            manifest = json.loads((ROOT / 'configs/upstream_manifest.json').read_text())
            meta = manifest['repositories'][repo]
            metadata_path.parent.mkdir(parents=True, exist_ok=True)
            metadata_path.write_text(json.dumps(meta, indent=2) + '\n')
        jobs.extend((repo, meta['sha'], item) for item in meta['siblings']
                    if selected(repo, item['rfilename']))
    print('FILES', len(jobs), 'BYTES', sum(j[2]['size'] for j in jobs), flush=True)
    records, errors = [], []
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(download, job): job for job in jobs}
        for future in concurrent.futures.as_completed(futures):
            try:
                records.append(future.result())
            except Exception as exc:
                job = futures[future]
                errors.append(dict(repo=job[0], file=job[2]['rfilename'], error=str(exc)))
                print('ERROR', errors[-1], flush=True)
            (ROOT / 'data/download_manifest.json').write_text(json.dumps(
                dict(complete=len(records) == len(jobs), expected_files=len(jobs),
                     verified_files=records, errors=errors), ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
