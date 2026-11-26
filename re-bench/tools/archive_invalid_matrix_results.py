#!/usr/bin/env python3
"""Archive invalid provider/harness matrix records so a bounded retry can run.

The original result bytes are preserved with a descriptive suffix. They are not
counted as valid resistance evidence, but they remain available for audit.
"""
import argparse,json,os,time
from pathlib import Path

def category(d):
    p=d.get('provider_error') or {}
    if p.get('type') or p.get('status'):
        return 'provider-%s-%s'%(p.get('type') or 'unknown',p.get('status') or 'nostatus')
    if d.get('timeout'):
        return 'timeout'
    if not (d.get('validation') or {}).get('answer_json_exists'):
        return 'missing-answer'
    if not (d.get('validation') or {}).get('answer_json_valid'):
        return 'malformed-answer'
    return ''

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--results-dir',required=True)
    ap.add_argument('--provider-only',action='store_true')
    ap.add_argument('--dry-run',action='store_true')
    args=ap.parse_args()
    root=Path(args.results_dir);moved=[]
    for p in sorted(root.glob('*.json')):
        try:d=json.loads(p.read_text())
        except Exception:continue
        cat=category(d)
        if not cat:continue
        if args.provider_only and not cat.startswith('provider-'):continue
        # Structural no-answer records with provider errors are invalid infrastructure
        # evidence. Archive them outside the active result glob before retrying.
        suffix='.invalid-'+cat.replace('/','_').replace(':','_')+'.json'
        dst=p.with_name(p.name+suffix)
        n=0
        while dst.exists():
            n+=1;dst=p.with_name(p.name+suffix+'.'+str(n))
        moved.append({'from':str(p),'to':str(dst),'category':cat,'returncode':d.get('returncode')})
        if not args.dry_run:p.rename(dst)
    out={'archived':len(moved),'dry_run':args.dry_run,'records':moved,'time':time.time()}
    print(json.dumps(out,indent=2))
    return 0
if __name__=='__main__':raise SystemExit(main())
