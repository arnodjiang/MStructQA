"""Read-only benchmark inspection with separately persisted, fingerprinted reviews."""
import argparse
import hashlib
import json
import mimetypes
import os
import threading
from collections import Counter, defaultdict
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, unquote

ROOT = Path(__file__).resolve().parents[1]


def read_json(path, default):
    return json.loads(path.read_text(encoding='utf-8')) if path.is_file() else default


def fingerprint(row):
    return hashlib.sha256(json.dumps(row, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


class Dataset:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.release = self.root / 'validation_release'
        self.rows = [json.loads(s) for s in (self.release / 'val.candidates.jsonl').read_text().splitlines() if s.strip()]
        self.by_id = {r['id']: r for r in self.rows}
        self.groups = defaultdict(list)
        for row in self.rows:
            self.groups[row['case_id']].append(row)
        self.manifests = {m['id']: m for m in read_json(self.root / 'case_manifest.json', [])}
        lock = read_json(self.root / 'selection_lock.json', {})
        self.languages = list(lock.get('languages') or sorted({r['image_language'] for r in self.rows}))
        self.case_ids = list(dict.fromkeys(list(lock.get('ids', [])) + list(self.groups)))
        self.review_file = self.root / 'manual_review' / 'annotations.json'
        self.reviews = read_json(self.review_file, {})
        self.lock = threading.Lock()
        self.assets = {}
        self.issues = defaultdict(list)
        hashes = {}
        counts = Counter(r['id'] for r in self.rows)
        for rid, count in counts.items():
            if count > 1:
                self.issues[self.by_id[rid]['case_id']].append('Duplicate variant ID: ' + rid)
        for cid in self.case_ids:
            rows = self.groups[cid]
            expected = {(v, q, q) for v in self.languages for q in {v, 'en', 'zh'}}
            actual = Counter((r['image_language'], r['query_language'], r['answer_language']) for r in rows)
            for pair in sorted(expected - set(actual)):
                self.issues[cid].append('Missing configuration: ' + '/'.join(pair))
            for pair, count in actual.items():
                if pair not in expected or count != 1:
                    self.issues[cid].append('Unexpected or repeated configuration: ' + '/'.join(pair))
            data_hashes = {r.get('visual_metadata', {}).get('data_sha256') for r in rows}
            if len(data_hashes) != 1 or None in data_hashes:
                self.issues[cid].append('Missing or inconsistent numerical-data hashes in metadata')
            for lang in self.languages:
                locale = self.root / 'cases' / cid / 'locales' / (lang + '.json')
                try:
                    if not isinstance(read_json(locale, None), dict):
                        raise ValueError('missing')
                except (ValueError, OSError):
                    self.issues[cid].append('Missing or invalid locale: ' + lang)
            for r in rows:
                for field in ('query', 'answer'):
                    if r.get(field) is None or str(r[field]).strip() == '':
                        self.issues[cid].append('Empty ' + field + ': ' + r['id'])
                if '[[' in r.get('query', '') or '[[' in str(r.get('answer', '')):
                    self.issues[cid].append('Unresolved label placeholder: ' + r['id'])
                for field in ('image_path', 'code_path'):
                    p = self.safe_path(self.release / r.get(field, ''))
                    if not p or not p.is_file():
                        self.issues[cid].append('Missing or unsafe ' + field + ': ' + r['id'])
                    elif field == 'image_path':
                        self.assets[r['id']] = p
                        if p not in hashes:
                            hashes[p] = hashlib.sha256(p.read_bytes()).hexdigest()
                        if hashes[p] != r.get('image_sha256'):
                            self.issues[cid].append('Image hash mismatch: ' + r['id'])
            original = self.manifests.get(cid, {}).get('original')
            p = self.safe_path(self.root / original) if original else None
            if p and p.is_file() and p.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp'):
                self.assets['original-' + cid] = p
            self.issues[cid] = list(dict.fromkeys(self.issues[cid]))
        self.image_count = len(hashes)

    def safe_path(self, path):
        path = path.resolve()
        return path if self.root in path.parents else None

    def review(self, row):
        item = dict(self.reviews.get(row['id'], {}))
        if item:
            item['stale'] = item.get('fingerprint') != fingerprint(row)
        return item

    def summary(self):
        cases = []
        for cid in self.case_ids:
            rows = self.groups[cid]
            cases.append(dict(id=cid, source=self.manifests.get(cid, {}).get('source', rows[0]['source'] if rows else 'unknown'),
                kind=self.manifests.get(cid, {}).get('kind', ''), count=len(rows), issues=len(self.issues[cid]),
                flagged=sum(r.get('audit', {}).get('status') != 'accepted' for r in rows),
                reviewed=sum(bool(self.review(r)) and not self.review(r)['stale'] and self.review(r).get('verdict') != 'unreviewed' for r in rows)))
        return dict(languages=self.languages, cases=cases, qa=len(self.rows), images=self.image_count,
                    expected_images=len(self.case_ids)*len(self.languages),
                    expected_qa=len(self.case_ids)*len({(v,q,q) for v in self.languages for q in {v,'en','zh'}}),
                    issues=sum(map(len, self.issues.values())), reviewed=sum(c['reviewed'] for c in cases))

    def detail(self, cid):
        if cid not in self.case_ids:
            raise KeyError(cid)
        locales = {}
        for lang in self.languages:
            try:
                locales[lang] = read_json(self.root / 'cases' / cid / 'locales' / (lang + '.json'), {})
            except ValueError:
                locales[lang] = {'error': 'Invalid JSON'}
        return dict(id=cid, rows=[dict(r, manual_review=self.review(r)) for r in self.groups[cid]],
                    original='/asset/original-' + cid if 'original-' + cid in self.assets else None,
                    issues=self.issues[cid], locales=locales)

    def save(self, body):
        if not isinstance(body, dict):
            raise ValueError('Expected a JSON object')
        rid = body.get('id')
        if rid not in self.by_id or body.get('verdict') not in ('pass', 'fail', 'uncertain', 'unreviewed'):
            raise ValueError('Invalid ID or verdict')
        row = self.by_id[rid]
        if body.get('fingerprint') != fingerprint(row):
            raise ValueError('Dataset changed; reload before saving')
        item = dict(id=rid, case_id=row['case_id'], fingerprint=fingerprint(row), verdict=body['verdict'],
                    notes=str(body.get('notes', ''))[:20000], reviewer=str(body.get('reviewer', ''))[:200],
                    updated_at=datetime.now(timezone.utc).isoformat())
        with self.lock:
            updated = dict(self.reviews, **{rid: item})
            self.review_file.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.review_file.with_suffix('.tmp')
            tmp.write_text(json.dumps(updated, ensure_ascii=False, indent=2), encoding='utf-8')
            os.replace(tmp, self.review_file)
            self.reviews = updated
        return item


def make_handler(dataset):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send(self, data, content_type='application/json', status=200):
            if not isinstance(data, bytes):
                data = json.dumps(data, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; img-src 'self'; style-src 'self'; script-src 'self'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(data)

        def valid_host(self):
            return self.headers.get('Host') in ('127.0.0.1:%s' % self.server.server_port, 'localhost:%s' % self.server.server_port)

        def do_GET(self):
            if not self.valid_host():
                self.send({'error': 'Local host required'}, status=403)
                return
            path = unquote(urlsplit(self.path).path)
            if path == '/api/summary':
                self.send(dataset.summary())
            elif path == '/api/export':
                self.send(dict(schema_version=1, reviews=list(dataset.reviews.values())))
            elif path.startswith('/api/case/'):
                try:
                    detail = dataset.detail(path.split('/')[-1])
                    for r in detail['rows']:
                        r['fingerprint'] = fingerprint(dataset.by_id[r['id']])
                    self.send(detail)
                except KeyError:
                    self.send({'error': 'Unknown case'}, status=404)
            elif path.startswith('/asset/') and path[7:] in dataset.assets:
                p = dataset.assets[path[7:]]
                self.send(p.read_bytes(), mimetypes.guess_type(p.name)[0] or 'application/octet-stream')
            elif path in ('/', '/app.js', '/style.css'):
                p = ROOT / 'web' / 'review' / ('index.html' if path == '/' else path[1:])
                self.send(p.read_bytes(), mimetypes.guess_type(p.name)[0] + '; charset=utf-8')
            else:
                self.send({'error': 'Not found'}, status=404)

        def do_POST(self):
            origin = self.headers.get('Origin')
            host = self.headers.get('Host')
            if not self.valid_host() or self.path != '/api/review' or origin != 'http://' + str(host) or self.headers.get_content_type() != 'application/json':
                self.send({'error': 'Same-origin JSON required'}, status=403)
                return
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if size < 1 or size > 65536:
                    raise ValueError('Invalid request size')
                self.send(dataset.save(json.loads(self.rfile.read(size))))
            except (ValueError, TypeError) as e:
                self.send({'error': str(e)}, status=400)
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', type=Path, default=ROOT / 'data/visual_benchmark/mstructqa_24')
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    print('Checking configuration coverage, files and image hashes...', flush=True)
    dataset = Dataset(args.dataset)
    server = ThreadingHTTPServer(('127.0.0.1', args.port), make_handler(dataset))
    print('Review UI: http://127.0.0.1:%s · %s QA · %s consistency issues' % (args.port, len(dataset.rows), sum(map(len, dataset.issues.values()))), flush=True)
    server.serve_forever()


if __name__ == '__main__':
    main()
