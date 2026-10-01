"""Resolve exact GRCh38 SNVs against the current NCBI ClinVar record."""
import json
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime,timezone

from .storage import read_json,write_json

ACCESSIONS={
    '1':'NC_000001.11','2':'NC_000002.12','3':'NC_000003.12','4':'NC_000004.12','5':'NC_000005.10',
    '6':'NC_000006.12','7':'NC_000007.14','8':'NC_000008.11','9':'NC_000009.12','10':'NC_000010.11',
    '11':'NC_000011.10','12':'NC_000012.12','13':'NC_000013.11','14':'NC_000014.9','15':'NC_000015.10',
    '16':'NC_000016.10','17':'NC_000017.11','18':'NC_000018.10','19':'NC_000019.10','20':'NC_000020.11',
    '21':'NC_000021.9','22':'NC_000022.11','X':'NC_000023.11','Y':'NC_000024.10','M':'NC_012920.1','MT':'NC_012920.1',
}

def _json(url,params):
    query=urllib.parse.urlencode(params)
    request=urllib.request.Request(f'{url}?{query}',headers={'User-Agent':'NCKU-MTB/1.0'})
    with urllib.request.urlopen(request,timeout=20) as response:return json.loads(response.read())

def _resolve(variant_id):
    try:chrom,pos,ref,alt=variant_id.removeprefix('chr').split(':',3)
    except ValueError:return None
    accession=ACCESSIONS.get(chrom)
    if not accession or not ref.isalpha() or not alt.isalpha():return None
    term=f'{accession}:g.{pos}{ref}>{alt}'
    search=_json('https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi',{'db':'clinvar','retmode':'json','retmax':2,'term':term})
    ids=search.get('esearchresult',{}).get('idlist',[])
    if len(ids)!=1:return {'verified':True,'classification':'','variation_id':'','review_status':'','url':f'https://www.ncbi.nlm.nih.gov/clinvar/?term={urllib.parse.quote(term)}'}
    variation_id=ids[0]
    summary=_json('https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi',{'db':'clinvar','retmode':'json','id':variation_id}).get('result',{}).get(variation_id,{})
    germline=summary.get('germline_classification',{})
    return {'verified':True,'classification':str(germline.get('description','')),'variation_id':variation_id,'review_status':str(germline.get('review_status','')),'url':f'https://www.ncbi.nlm.nih.gov/clinvar/variation/{variation_id}/'}

def annotate(directory,rows):
    path=directory/'cache'/'clinvar_current.json';cache=read_json(path,{}) or {};variants=cache.get('variants',{})
    changed=False
    for row in rows:
        key=str(row.get('variant_id') or '')
        if not key or key in variants:continue
        try:variants[key]=_resolve(key) or {'verified':False}
        except Exception as exc:variants[key]={'verified':False,'error':str(exc)[:200]}
        changed=True;time.sleep(.35)
    if changed:write_json(path,{'checked_at':datetime.now(timezone.utc).isoformat(),'variants':variants})
    for row in rows:
        current=variants.get(str(row.get('variant_id') or ''),{})
        row['clinvar_current_verified']=bool(current.get('verified'))
        if current.get('verified'):
            row['clinvar']=current.get('classification','')
            row['clinvar_variation_id']=current.get('variation_id','')
            row['clinvar_review_status']=current.get('review_status','')
            row['clinvar_url']=current.get('url','')
    return rows
