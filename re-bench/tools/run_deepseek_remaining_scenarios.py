#!/usr/bin/env python3
"""Run the non-core 15 scenario slice into the existing go-v12 evidence root.

The deepseek core chain covers the four key/source runtime-boundary scenarios in
separate local/cloud roots. This runner deliberately covers only the remaining
scenario families so the union of evidence roots forms the 6x19 matrix without
rerunning completed core attempts.
"""
import os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SCENARIOS=','.join([
 'binary-only-external','static-analysis-only','ghidra-static','ghidra-dynamic',
 'unprivileged-local','privileged-debugger','native-module-extraction',
 'loader-initialization-order','pack-layout-sections','crypto-construction',
 'provenance-signatures','host-runtime-gates','chain-licence-path',
 'semantics-hidden-vectors','source-assisted-static'
])
def main():
    env=dict(os.environ);env['ABSMAX_PROFILE_MATRIX_ID']='go-v12'
    cmd=[sys.executable,str(ROOT/'re-bench/tools/run_profile_matrix.py'),'--model','opencode-go/deepseek-v4.1-flash','--matrix-id','go-v12','--scenarios',SCENARIOS,'--attempts','1','--parallel','2']
    print('starting remaining scenario matrix: 15 scenarios x 6 variants; existing go-v12 results are skipped',flush=True)
    return subprocess.call(cmd,cwd=str(ROOT),env=env)
if __name__=='__main__':raise SystemExit(main())
