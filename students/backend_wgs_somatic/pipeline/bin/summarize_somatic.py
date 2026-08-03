#!/usr/bin/env python3
import argparse, csv, gzip, json, re
from pathlib import Path

def opener(path):
    return gzip.open(path, 'rt', encoding='utf-8', errors='replace') if str(path).endswith(('.gz','.bgz')) else open(path, encoding='utf-8', errors='replace')

def truthy(row, names):
    text=' '.join(str(row.get(n,'')) for n in names).casefold()
    return any(x in text for x in ('pathogenic','oncogenic','actionable','sensitive','resistant','level 1','level 2'))

def write_rows(path, fields, rows):
    with open(path,'w',newline='',encoding='utf-8') as h:
        w=csv.DictWriter(h,fieldnames=fields,delimiter='\t',extrasaction='ignore'); w.writeheader(); w.writerows(rows)

def snv(args):
    with opener(args.input) as h:
        reader=csv.DictReader((line for line in h if not line.startswith('##')),delimiter='\t')
        rows=list(reader); fields=reader.fieldnames or []
    evidence=['CLIN_SIG','ClinVar_CLNSIG','CIVIC','CIVIC_annotation','OncoKB','oncoKB_annotation','CGI_annotation','COSMIC','Existing_variation']
    actionable=[r for r in rows if truthy(r,evidence)]
    af_fields=['gnomADe_AF','gnomADg_AF','gnomAD_AF','AF']
    possible=[]
    for r in rows:
        vals=[]
        for k in af_fields:
            for token in re.split('[,&]',str(r.get(k,''))):
                try: vals.append(float(token))
                except ValueError: pass
        if vals and max(vals) >= float(args.population_af_max): possible.append(r)
    write_rows(f'{args.output_prefix}.snv.all.tsv',fields,rows)
    write_rows(f'{args.output_prefix}.snv.actionable.tsv',fields,actionable)
    write_rows(f'{args.output_prefix}.snv.possible_germline.tsv',fields,possible)
    json.dump({'all_variants':len(rows),'actionable':len(actionable),'possible_germline':len(possible),'somatic_status_note':'Tumor-only; somatic origin is not confirmed.'},open(f'{args.output_prefix}.snv.summary.json','w'),indent=2)

def structural(args):
    rows=[]
    with opener(args.input) as h:
        for line in h:
            if line.startswith('#'): continue
            cols=line.rstrip('\n').split('\t'); info={}
            for item in cols[7].split(';'):
                k,_,v=item.partition('='); info[k]=v or 'true'
            rows.append({'chrom':cols[0],'pos':cols[1],'id':cols[2],'ref':cols[3],'alt':cols[4],
                         'filter':cols[6],'kind':args.kind,'svtype':info.get('SVTYPE',info.get('TYPE','')),
                         'end':info.get('END',''),'gene':info.get('GENE',info.get('SYMBOL','')),
                         'clinical_evidence':info.get('CLNSIG',info.get('CIVIC',info.get('ONCOKB',''))), 'info':cols[7]})
    fields=['chrom','pos','end','id','ref','alt','filter','kind','svtype','gene','clinical_evidence','info']
    actionable=[r for r in rows if truthy(r,['clinical_evidence'])]
    write_rows(f'{args.output_prefix}.all.tsv',fields,rows); write_rows(f'{args.output_prefix}.actionable.tsv',fields,actionable)
    json.dump({'kind':args.kind,'all_variants':len(rows),'actionable':len(actionable)},open(f'{args.output_prefix}.summary.json','w'),indent=2)

def main():
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest='mode',required=True)
    a=sub.add_parser('snv'); a.add_argument('--input',required=True); a.add_argument('--sample',required=True); a.add_argument('--output-prefix',required=True); a.add_argument('--population-af-max',default=.01)
    b=sub.add_parser('structural'); b.add_argument('--input',required=True); b.add_argument('--sample',required=True); b.add_argument('--kind',choices=['sv','cnv'],required=True); b.add_argument('--output-prefix',required=True)
    args=p.parse_args(); snv(args) if args.mode=='snv' else structural(args)
if __name__=='__main__': main()
