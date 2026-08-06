#!/usr/bin/env python3
"""Compare MTB dual-profile TSV with the frozen official OncoVI example output."""
import argparse, csv, json
from pathlib import Path

def criteria(value):
    return set(filter(None,str(value or '').replace('|',',').split(',')))

def main():
    p=argparse.ArgumentParser(); p.add_argument('--expected',required=True,help='Official OncoVI xlsx or TSV')
    p.add_argument('--observed',required=True); p.add_argument('--output',required=True); a=p.parse_args()
    if a.expected.endswith('.xlsx'):
        import pandas as pd
        expected=pd.read_excel(a.expected,na_filter=False).to_dict('records')
    else:
        with open(a.expected,encoding='utf-8') as h: expected=list(csv.DictReader(h,delimiter='\t'))
    with open(a.observed,encoding='utf-8') as h: observed=list(csv.DictReader(h,delimiter='\t'))
    exp={str(r['new_identifier']):r for r in expected}; obs={str(r['new_identifier']):r for r in observed}
    shared=sorted(exp.keys()&obs.keys()); differences=[]
    for key in shared:
        e,o=exp[key],obs[key]; ec,oc=criteria(e['Criteria']),criteria(o['oncovi_2026_criteria'])
        if e['Classification']!=o['oncovi_2026_classification'] or str(e['Points'])!=str(o['oncovi_2026_score']) or ec!=oc:
            differences.append({'variant':key,'gene':e.get('SYMBOL',''),'expected_score':e['Points'],'observed_score':o['oncovi_2026_score'],'expected_classification':e['Classification'],'observed_classification':o['oncovi_2026_classification'],'expected_only_criteria':sorted(ec-oc),'observed_only_criteria':sorted(oc-ec)})
    n=len(shared); report={'expected_variants':len(exp),'observed_variants':len(obs),'compared_variants':n,'missing_expected_keys':sorted(obs.keys()-exp.keys()),'missing_observed_keys':sorted(exp.keys()-obs.keys()),'classification_exact':sum(exp[k]['Classification']==obs[k]['oncovi_2026_classification'] for k in shared),'score_exact':sum(str(exp[k]['Points'])==str(obs[k]['oncovi_2026_score']) for k in shared),'criteria_exact':sum(criteria(exp[k]['Criteria'])==criteria(obs[k]['oncovi_2026_criteria']) for k in shared),'differences':differences}
    report['classification_concordance']=report['classification_exact']/n if n else 0
    Path(a.output).write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='differences'},indent=2))
    raise SystemExit(0 if n and report['classification_exact']==n else 1)
if __name__=='__main__':main()
