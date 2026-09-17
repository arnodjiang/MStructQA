"""Download and verify the exact current evaluation release from Hugging Face."""
import argparse
import json
from pathlib import Path
import tarfile
import tempfile
import shutil
from huggingface_hub import hf_hub_download
from scripts.distribution.export_hf import sha
from scripts.final_benchmark.clean_release import verify_clean
from scripts.evaluation.migrate_token_router import verify_images


def download(repo, revision, output):
    output=Path(output).resolve()
    if output.exists():raise ValueError('Output exists; use a new directory')
    manifest=Path(hf_hub_download(repo,'release.json',repo_type='dataset',revision=revision))
    info=json.loads(manifest.read_text())
    name='artifacts/mstructqa-current.tar.gz'
    archive=Path(hf_hub_download(repo,name,repo_type='dataset',revision=revision))
    if sha(archive)!=info['files'][name]:raise ValueError('Archive checksum mismatch')
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as tmp:
        root=Path(tmp).resolve()
        with tarfile.open(archive) as tar:
            for member in tar.getmembers():
                target=(root/member.name).resolve()
                if root not in target.parents or not (member.isfile() or member.isdir()):
                    raise ValueError('Unsafe archive entry')
            tar.extractall(root)
        staged=root/'mstructqa-current'
        refs=staged/'validation_release/val.candidates.jsonl'
        if sha(refs)!=info['references_sha256']:raise ValueError('Reference checksum mismatch')
        verify_clean(staged,write_report=False)
        verify_images(staged,[json.loads(s) for s in refs.read_text().splitlines()])
        shutil.move(str(staged),output)
    print(output)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo',default='arnodjiang/MStructBench');p.add_argument('--revision',default='main')
    p.add_argument('--output',type=Path,default=Path('data/visual_benchmark/final_128_24lang_v5_visual_types'))
    a=p.parse_args();download(a.repo,a.revision,a.output)
