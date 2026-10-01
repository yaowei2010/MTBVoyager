"""Add display coordinates and tumor FORMAT values to SNV result rows."""
import gzip
import re

from .storage import read_json, write_json


def variant_parts(row):
    raw=str(row.get('#Uploaded_variation') or row.get('uploaded_variation') or row.get('variant') or row.get('variant_id') or '')
    match=re.fullmatch(r'(.+?)_(\d+)_([^_/]+)/(.+)',raw)
    if match:return match.groups()
    match=re.search(r'(chr[^:]+):g\.(\d+)([A-Za-z]+)>([A-Za-z]+)',str(row.get('HGVSg') or row.get('hgvsg') or ''))
    if match:return match.groups()
    match=re.fullmatch(r'([^:]+):(\d+):([^:]+):([^:]+)',raw)
    return match.groups() if match else None


def tumor_format_rows(directory,sample,rows):
    keyed={}
    for row in rows:
        parts=variant_parts(row)
        if parts:
            chrom,pos,ref,alt=parts;chrom=chrom if chrom.startswith('chr') else f'chr{chrom}'
            row['variant_id']=f'{chrom}:{pos}:{ref}:{alt}';keyed.setdefault((chrom,pos,ref,alt),[]).append(row)
        row['gnomad_eas_af']=row.get('gnomADg_EAS_AF') or row.get('gnomADe_EAS_AF') or row.get('gnomad_eas_af') or ''
    if not keyed:return rows
    cache_path=directory/'cache'/'tumor_format.json';cache=read_json(cache_path,{}) or {}
    missing={key for key in keyed if ':'.join(key) not in cache}
    vcf=directory/'results'/sample/'snv'/f'{sample}.somatic.filtered.vcf.gz'
    if missing and vcf.is_file():
        with gzip.open(vcf,'rt',encoding='utf-8',errors='replace') as handle:
            for line in handle:
                if line.startswith('#'):continue
                cols=line.rstrip('\n').split('\t')
                if len(cols)<10:continue
                chrom,pos,_,ref,alts=cols[:5];chrom=chrom if chrom.startswith('chr') else f'chr{chrom}'
                names=cols[8].split(':');values=cols[9].split(':');sample_data=dict(zip(names,values))
                alt_values=alts.split(',');af_values=sample_data.get('AF','').split(',')
                for index,alt in enumerate(alt_values):
                    candidates=[(chrom,pos,ref,alt)]
                    if alt.startswith(ref) and len(alt)>len(ref):
                        candidates.append((chrom,str(int(pos)+len(ref)),'-',alt[len(ref):]))
                    if ref.startswith(alt) and len(ref)>len(alt):
                        candidates.append((chrom,str(int(pos)+len(alt)),ref[len(alt):],'-'))
                    for key in candidates:
                        if key not in missing:continue
                        cache[':'.join(key)]={'tumor_af':af_values[index] if index<len(af_values) else '','tumor_dp':sample_data.get('DP','')};missing.remove(key)
                if not missing:break
        write_json(cache_path,cache)
    for key,matched_rows in keyed.items():
        for row in matched_rows:row.update(cache.get(':'.join(key),{}))
    return rows
