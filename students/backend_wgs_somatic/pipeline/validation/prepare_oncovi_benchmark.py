#!/usr/bin/env python3
"""Merge frozen official OncoVI rows with current VEP plugin annotations."""
import argparse, csv, gzip, re
import pandas as pd

def clean(value):
    value=str(value or '').strip()
    return '' if value in ('-','.','nan') else value

def key(value):
    match=re.match(r'(?:chr)?([^_]+)_(\d+)_([^/]+)/(.+)',str(value))
    return match.groups() if match else ('','','','')

def main():
    p=argparse.ArgumentParser();p.add_argument('--expected',required=True);p.add_argument('--vep',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    expected=pd.read_excel(a.expected,na_filter=False)
    with gzip.open(a.vep,'rt',encoding='utf-8') as h: header=next(x for x in h if x.startswith('#Uploaded_variation')).rstrip().split('\t')
    vep=pd.read_csv(a.vep,sep='\t',comment='#',names=header,na_filter=False,dtype=str)
    vep[['kchrom','kpos','kref','kalt']]=pd.DataFrame(vep['#Uploaded_variation'].map(key).tolist(),index=vep.index)
    vep['rank']=vep.apply(lambda r:(clean(r.get('PICK'))=='1',bool(clean(r.get('MANE_SELECT'))),clean(r.get('CANONICAL'))=='YES',bool(clean(r.get('SYMBOL'))),bool(clean(r.get('HGVSp')))),axis=1)
    selected=vep.sort_values('rank').groupby(['kchrom','kpos','kref','kalt'],as_index=False).tail(1)
    lookup={(r.kchrom,r.kpos,r.kref,r.kalt):r for _,r in selected.iterrows()}
    extras=['gnomADe_AFR_AF','gnomADe_EAS_AF','gnomADe_NFE_AF','gnomADe_AMR_AF','gnomADe_SAS_AF','gnomADg_AFR_AF','gnomADg_EAS_AF','gnomADg_NFE_AF','gnomADg_AMR_AF','gnomADg_SAS_AF','phyloP100way_vertebrate_rankscore','phastCons100way_vertebrate_rankscore','SpliceAI_cutoff','CADD_phred','REVEL_score','ClinPred_score','am_class']
    rows=[]
    for _,row in expected.iterrows():
        d=row.to_dict(); k=(str(row.CHROM),str(row.POS),str(row.REF),str(row.ALT)); hit=lookup.get(k); d['#Uploaded_variation']=f'{k[0]}_{k[1]}_{k[2]}/{k[3]}'
        if hit is not None:
            for field in extras:d[field]=hit.get(field,'')
        rows.append(d)
    pd.DataFrame(rows).to_csv(a.output,sep='\t',index=False,quoting=csv.QUOTE_MINIMAL)
if __name__=='__main__':main()
