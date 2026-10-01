#!/usr/bin/env python3
import argparse,bisect,csv,gzip,json,zipfile
from collections import defaultdict
from contextlib import contextmanager
from pathlib import Path

def merge(rows):
    out=[]
    for start,end in sorted(rows):
        if not out or start>out[-1][1]: out.append([start,end])
        else: out[-1][1]=max(out[-1][1],end)
    return out

@contextmanager
def bed_lines(path):
    path=Path(path)
    if path.suffix.lower()=='.zip':
        with zipfile.ZipFile(path) as archive:
            members=[n for n in archive.namelist() if not n.endswith('/')]
            if len(members)!=1: raise ValueError('Callable ZIP must contain exactly one BED file')
            with archive.open(members[0]) as raw: yield (line.decode('utf-8') for line in raw)
    elif str(path).endswith('.gz'):
        with gzip.open(path,'rt') as handle: yield handle
    else:
        with path.open() as handle: yield handle

def numeric(value):
    try: return float(value)
    except (TypeError,ValueError): return None

def main():
    p=argparse.ArgumentParser(); p.add_argument('--callable',required=True); p.add_argument('--gtf',required=True); p.add_argument('--variants',required=True); p.add_argument('--sample',required=True); a=p.parse_args()
    primary={f'chr{i}' for i in range(1,23)}; cds=defaultdict(list)
    op=gzip.open if str(a.gtf).endswith('.gz') else open
    with op(a.gtf,'rt') as handle:
        for line in handle:
            if line.startswith('#'): continue
            x=line.rstrip().split('\t')
            if len(x)>=5 and x[0] in primary and x[2]=='CDS': cds[x[0]].append((int(x[3])-1,int(x[4])))
    cds={chrom:merge(rows) for chrom,rows in cds.items()}; overlap=defaultdict(list); interval_count=0
    pointers=defaultdict(int)
    with bed_lines(a.callable) as lines:
        for line in lines:
            if line.startswith('#'): continue
            x=line.rstrip().split('\t')
            if len(x)<3 or x[0] not in primary: continue
            chrom,start,end=x[0],int(x[1]),int(x[2]); interval_count+=1
            coding=cds.get(chrom,[]); index=pointers[chrom]
            while index<len(coding) and coding[index][1]<=start: index+=1
            pointers[chrom]=index
            for left,right in coding[index:]:
                if left>=end: break
                lo,hi=max(start,left),min(end,right)
                if hi>lo: overlap[chrom].append((lo,hi))
    overlap={chrom:merge(rows) for chrom,rows in overlap.items()}; starts={chrom:[x[0] for x in rows] for chrom,rows in overlap.items()}
    selected={}
    with open(a.variants,newline='') as handle:
        for row in csv.DictReader(handle,delimiter='\t'):
            try: chrom,pos,_=row['#Uploaded_variation'].rsplit('_',2)
            except ValueError: continue
            af=[numeric(row.get(k)) for k in ('gnomADe_AF','gnomADg_AF','gnomAD_AF','AF')]; af=[x for x in af if x is not None]
            consequences=set(row.get('Consequence','').split(','))
            origin=' '.join(str(row.get(k,'')) for k in ('somatic_status','germline_status','ORIGIN','ClinVar_CLNORIGIN')).lower()
            if chrom not in primary or (af and max(af)>.001) or ('germline' in origin and 'somatic' not in origin) or not consequences.intersection({'missense_variant','frameshift_variant','stop_gained','stop_lost','start_lost','inframe_insertion','inframe_deletion','protein_altering_variant'}): continue
            point=int(pos)-1; index=bisect.bisect_right(starts.get(chrom,[]),point)-1; rows=overlap.get(chrom,[])
            if index>=0 and point<rows[index][1]: selected.setdefault(row['#Uploaded_variation'],row)
    selected=list(selected.values()); bp=sum(end-start for rows in overlap.values() for start,end in rows); mb=bp/1e6; estimate=len(selected)/mb if mb else None
    fields=['#Uploaded_variation','SYMBOL','Consequence','HGVSc','HGVSp','gnomADe_AF','gnomADg_AF','oncogenicity_classification']
    with open(f'{a.sample}.tmb_proxy_variants.tsv','w',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=fields,delimiter='\t',extrasaction='ignore'); writer.writeheader(); writer.writerows(selected)
    result={'sample_id':a.sample,'status':'exploratory_not_clinically_validated','genome_build':'GRCh38','method':'unique non-synonymous/protein-altering variants after germline-proxy exclusion, divided by callable GENCODE v47 coding territory','population_af_max':.001,'synonymous_variants_included':False,'duplicate_transcript_annotations_deduplicated':True,'callable_bed_intervals_autosomes':interval_count,'callable_coding_bp':bp,'callable_coding_mb':mb,'tmb_numerator_variants':len(selected),'tmb_proxy_mut_per_mb':estimate,'limitations':['Tumor-only; no matched normal, so private germline variants cannot be completely removed.','Germline exclusion uses population AF and explicit origin annotations as proxies.','Not calibrated to an FDA-approved TMB assay.']}
    Path(f'{a.sample}.tmb_proxy.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__': main()
