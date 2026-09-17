"""Upload a checksum-verified release using cached HF login or local HF_TOKEN."""
import argparse
import json
import os
from pathlib import Path
from dotenv import dotenv_values
from huggingface_hub import HfApi, get_token
from scripts.distribution.export_hf import sha


def publish(folder, repo):
    folder=Path(folder).resolve()
    env=dotenv_values(Path(__file__).resolve().parents[2]/'.env',interpolate=False)
    token=os.environ.get('HF_TOKEN') or env.get('HF_TOKEN') or get_token()
    if not token:raise SystemExit('Hugging Face authentication required: run hf auth login, or set HF_TOKEN in local .env.')
    report=json.loads((folder/'release.json').read_text())
    allowed=set(report['files'])|{'release.json','README.md'}
    actual={str(p.relative_to(folder)) for p in folder.rglob('*') if p.is_file()}
    if actual!=allowed:raise ValueError('Unexpected or missing public release files')
    for name,expected in report['files'].items():
        if sha(folder/name)!=expected:raise ValueError('Release file changed: '+name)
    api=HfApi(token=token)
    info=api.repo_info(repo,repo_type='dataset')
    result=api.upload_folder(repo_id=repo,repo_type='dataset',folder_path=folder,
                             parent_commit=info.sha,
                             commit_message='Publish current MStructQA 24-language benchmark')
    print('Published',result.commit_url)
    print('Revision',result.oid)
    remote=api.list_repo_files(repo,repo_type='dataset',revision=result.oid)
    if not allowed.issubset(set(remote)):raise RuntimeError('Remote file verification failed')
    return result.oid


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--folder',type=Path,default=Path('data/hf_publish/MStructBench'))
    p.add_argument('--repo',default='arnodjiang/MStructBench')
    a=p.parse_args();publish(a.folder,a.repo)
