"""Public CLI for staged MStructQA construction. No API calls for --help."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description='MStructQA: 24-language chart and visual table QA pipeline')
    p.add_argument('stage',choices=['download','prepare','baseline','baseline-audit','expand','expand-audit','finalize'])
    p.add_argument('--baseline',type=Path,default=ROOT/'data/visual_benchmark/baseline')
    p.add_argument('--output',type=Path,default=ROOT/'data/visual_benchmark/mstructqa_24')
    p.add_argument('--workers',type=int,default=4)
    p.add_argument('--retry-failed',action='store_true',help='Explicitly resume previously failed requests after inspection')
    a=p.parse_args();baseline=a.baseline.resolve();out=a.output.resolve()
    env=dict(os.environ,MVISQA_OUTPUT=str(baseline))
    def run(*args):subprocess.run([sys.executable,*map(str,args)],cwd=ROOT,env=env,check=True)
    retry=['--retry-failed'] if a.retry_failed else []
    if a.stage=='download':run('scripts/download_benchmarks.py')
    elif a.stage=='prepare':
        for script in ['profile_and_sample.py','export_candidate_assets.py','build_expansion_registry.py']:run('scripts/'+script)
    elif a.stage=='baseline':
        run('-m','scripts.final_benchmark.pipeline','--output',baseline,'--stage','all','--workers',a.workers,*retry)
        run('-m','scripts.final_benchmark.export','--output',baseline)
    elif a.stage=='baseline-audit':
        run('-m','scripts.final_benchmark.review','--workers',a.workers,*retry)
        run('-m','scripts.final_benchmark.export','--output',baseline)
        run('-m','scripts.final_benchmark.val_verify')
        run('-m','scripts.final_benchmark.val_audit','--workers',a.workers,'--language-batch-size','4',*retry)
    elif a.stage=='expand':run('-m','scripts.final_benchmark.expand24','--source',baseline,'--output',out,'--workers',a.workers,*retry)
    elif a.stage=='expand-audit':run('-m','scripts.final_benchmark.audit24','--output',out,'--max-languages','4',*retry)
    elif a.stage=='finalize':run('-m','scripts.final_benchmark.finalize24','--output',out)


if __name__=='__main__':main()
