#!/usr/bin/env python3
"""Summarize numeric OpenCode Go cache/token telemetry without prompt content."""
import argparse,json,time
from pathlib import Path

def rows_for(path,since=0.0):
    rows=[]
    if not Path(path).exists():return rows
    for line in Path(path).read_text(errors='replace').splitlines():
        try:d=json.loads(line)
        except Exception:continue
        if d.get('ts',0)<since:continue
        u=d.get('usage') or {};c=d.get('cache') or {};oc=(u.get('opencode') or {}).get('tokens') or {}
        rows.append({
            'ts':d.get('ts'),'status':d.get('status'),'elapsed':d.get('elapsed') or 0,
            'prompt_tokens':u.get('prompt_tokens') or 0,
            'completion_tokens':u.get('completion_tokens') or 0,
            'reasoning_tokens':((u.get('completion_tokens_details') or {}).get('reasoning_tokens') or 0),
            'input_tokens':oc.get('input') if oc.get('input') is not None else u.get('prompt_tokens') or 0,
            'output_tokens':oc.get('output') if oc.get('output') is not None else u.get('completion_tokens') or 0,
            'cache_read':c.get('prompt_cache_hit_tokens') or 0,
            'cache_write_5m':c.get('cache_write_5m_tokens') or 0,
            'cache_write_1h':c.get('cache_write_1h_tokens') or 0,
            'request_redactions':d.get('request_redactions') or 0,
            'response_redactions':d.get('response_redactions') or 0,
            'cost':u.get('cost') or 0,
            'allowance':(u.get('opencode') or {}).get('allowance') or 0,
        })
    return rows

def summarize(rows):
    ok=[r for r in rows if r['status']==200 and r['prompt_tokens']]
    prompt=sum(r['prompt_tokens'] for r in ok);hit=sum(r['cache_read'] for r in ok)
    input_tokens=sum(r['input_tokens'] for r in ok);output=sum(r['output_tokens'] for r in ok)
    rates=[r['cache_read']/r['prompt_tokens'] for r in ok if r['prompt_tokens']]
    return {
        'records':len(rows),'successful_model_requests':len(ok),
        'prompt_tokens':prompt,'cache_read_tokens':hit,'input_tokens_not_cached':input_tokens,
        'output_tokens':output,'weighted_cache_hit_rate':round(hit/prompt,6) if prompt else 0,
        'mean_per_request_cache_hit_rate':round(sum(rates)/len(rates),6) if rates else 0,
        'max_per_request_cache_hit_rate':round(max(rates),6) if rates else 0,
        'min_per_request_cache_hit_rate':round(min(rates),6) if rates else 0,
        'cache_write_5m_tokens':sum(r['cache_write_5m'] for r in ok),
        'cache_write_1h_tokens':sum(r['cache_write_1h'] for r in ok),
        'request_redactions':sum(r['request_redactions'] for r in rows),
        'response_redactions':sum(r['response_redactions'] for r in rows),
        'cost_total':sum(r['cost'] for r in ok),'allowance_total':sum(r['allowance'] for r in ok),
        'statuses':{str(s):sum(1 for r in rows if r['status']==s) for s in sorted({r['status'] for r in rows},key=str)},
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--log',default='/home/nixon/absmax-tokenharbor-proxy/opencode-go-proxy.log')
    ap.add_argument('--since',type=float,default=0.0)
    ap.add_argument('--out')
    args=ap.parse_args()
    rows=rows_for(args.log,args.since)
    out={'generated':time.time(),'log':args.log,'since':args.since,**summarize(rows)}
    text=json.dumps(out,indent=2)
    if args.out:Path(args.out).write_text(text+'\n')
    print(text)
if __name__=='__main__':main()
