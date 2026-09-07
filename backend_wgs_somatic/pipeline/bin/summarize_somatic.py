#!/usr/bin/env python3
import argparse, csv, gzip, json, re
from contextlib import ExitStack
from collections import defaultdict
from pathlib import Path

def opener(path):
    return gzip.open(path, 'rt', encoding='utf-8', errors='replace') if str(path).endswith(('.gz','.bgz')) else open(path, encoding='utf-8', errors='replace')

def truthy(row, names):
    text=' '.join(str(row.get(n,'')) for n in names).casefold()
    return any(x in text for x in ('pathogenic','oncogenic','actionable','sensitive','resistant','level 1','level 2'))

def consequence_terms(row):
    return {term.strip().casefold() for term in re.split(r'[,;&|]',clean(row.get('Consequence'))) if term.strip()}

def is_non_synonymous(row):
    terms=consequence_terms(row)
    return bool(terms) and any(term not in ('synonymous_variant','stop_retained_variant') for term in terms)

def clinvar_pathogenic(row):
    value=clean(row.get('CLIN_SIG',row.get('ClinVar_CLNSIG',''))).casefold().replace('_',' ')
    if any(term in value for term in ('conflict','uncertain','benign')): return False
    return 'pathogenic' in value

def oncogenic_high_risk(row):
    return clean(row.get('oncogenicity_classification')) in ('Oncogenic','Likely Oncogenic')

def reportable_high_risk(row):
    return is_non_synonymous(row) and (clinvar_pathogenic(row) or oncogenic_high_risk(row))

def write_rows(path, fields, rows):
    with open(path,'w',newline='',encoding='utf-8') as h:
        w=csv.DictWriter(h,fieldnames=fields,delimiter='\t',extrasaction='ignore'); w.writeheader(); w.writerows(rows)

def clean(value):
    value=str(value or '').strip()
    return '' if value.casefold() in ('nan','none','null','-') else value

def number(value):
    values=[]
    for token in re.split(r'[,;|&]',str(value or '')):
        try: values.append(float(token))
        except ValueError: pass
    return max(values) if values else None

def secondary_categories(rows, gene_file):
    genes={line.split('\t',1)[0].strip() for line in open(gene_file,encoding='utf-8') if line.strip() and not line.lower().startswith('gene')}
    hereditary={}; insilico={}
    for row in rows:
        variant=clean(row.get('#Uploaded_variation',row.get('Uploaded_variation',''))); gene=clean(row.get('SYMBOL'))
        clin=clean(row.get('CLIN_SIG',row.get('ClinVar_CLNSIG',''))).lower().replace('_',' ')
        afs=[x for x in (number(row.get('gnomADe_AF')),number(row.get('gnomADg_AF'))) if x is not None]; maxaf=max(afs) if afs else 0
        pathogenic='pathogenic' in clin and not any(x in clin for x in ('conflicting','benign','uncertain'))
        base={'variant':variant,'gene':gene,'hgvsc':clean(row.get('HGVSc')),'hgvsp':clean(row.get('HGVSp')),'consequence':clean(row.get('Consequence')),'clinvar':clean(row.get('CLIN_SIG',row.get('ClinVar_CLNSIG',''))),'max_population_af':maxaf,'tumor_only_status':'germline confirmation required'}
        if gene in genes and pathogenic and maxaf<=.01:
            hereditary[variant]={**base,'hereditary_condition':'ACMG SF hereditary-cancer gene','evidence':'ClinVar P/LP; confirm with constitutional specimen'}
        if pathogenic or maxaf>.01: continue
        supports=[]
        for field,threshold,label in [('CADD_phred',20,'CADD'),('REVEL_score',.5,'REVEL'),('ClinPred_score',.5,'ClinPred')]:
            score=number(row.get(field))
            if score is not None and score>=threshold: supports.append(f'{label}={score:g}')
        if 'pathogenic' in clean(row.get('am_class')).lower(): supports.append('AlphaMissense=pathogenic')
        if 'deleterious' in clean(row.get('SIFT')).lower(): supports.append('SIFT=deleterious')
        if 'damaging' in clean(row.get('PolyPhen')).lower(): supports.append('PolyPhen=damaging')
        if clean(row.get('SpliceAI_pred')).upper()=='PASS': supports.append('SpliceAI=PASS')
        if len(supports)>=2:
            item={**base,'prediction_support_count':len(supports),'prediction_support':'; '.join(supports),'evidence':'in-silico only; not clinically classified'}
            if variant not in insilico or len(supports)>insilico[variant]['prediction_support_count']: insilico[variant]=item
    return list(hereditary.values()),list(insilico.values())

def compact(source, row, fields, match):
    values={k:clean(row.get(k,'')) for k in fields if clean(row.get(k,''))}
    values.update({'source':source,'match':match})
    if source=='OncoKB': values['actionable']=True
    elif source=='CIViC': values['actionable']=bool(clean(row.get('therapies'))) and clean(row.get('evidence_direction')).casefold()=='supports'
    elif source=='COSMIC': values['actionable']=bool(clean(row.get('DRUG_COMBINATION')))
    return values

def evidence_text(items):
    return json.dumps(items,ensure_ascii=False,separators=(',',':')) if items else ''

def mark_tumor_context(items, cancer_type):
    query=clean(cancer_type).casefold()
    for item in items:
        haystack=' '.join(str(v) for k,v in item.items() if k not in ('source','match','actionable')).casefold()
        item['tumor_type_match']='unknown' if not query else ('true' if query in haystack else 'false')
    return items

def collapse_vep_annotations(rows):
    grouped=defaultdict(list)
    for index,row in enumerate(rows):
        key=clean(row.get('#Uploaded_variation',row.get('Uploaded_variation',''))) or f'row:{index}'
        grouped[key].append(row)
    def rank(row):
        return (clean(row.get('PICK'))=='1',bool(clean(row.get('MANE_SELECT'))),clean(row.get('CANONICAL'))=='YES',bool(clean(row.get('SYMBOL'))),bool(clean(row.get('HGVSp'))))
    return [max(group,key=rank) for group in grouped.values()]

def protein_change(row):
    aa=clean(row.get('Amino_acids')); pos=clean(row.get('Protein_position')).split('-')[0]
    if '/' in aa and pos.isdigit():
        ref,alt=aa.split('/',1)
        if len(ref)==1 and len(alt)==1 and ref!='-' and alt!='-': return f'{ref}{pos}{alt}'.upper()
    hgvsp=clean(row.get('HGVSp'))
    match=re.search(r'p\.([A-Z][a-z]{2})(\d+)([A-Z][a-z]{2}|Ter)',hgvsp)
    if match:
        code={'Ala':'A','Arg':'R','Asn':'N','Asp':'D','Cys':'C','Gln':'Q','Glu':'E','Gly':'G','His':'H','Ile':'I','Leu':'L','Lys':'K','Met':'M','Phe':'F','Pro':'P','Ser':'S','Thr':'T','Trp':'W','Tyr':'Y','Val':'V','Ter':'*'}
        return code.get(match[1],'')+match[2]+code.get(match[3],'')
    return ''

class CancerEvidence:
    def __init__(self, directory):
        self.root=Path(directory); self.oncokb=defaultdict(list); self.civic_coord=defaultdict(list)
        self.civic_protein=defaultdict(list); self.cgi={}; self.mcg={}; self.cosmic=defaultdict(list)
        self._load()

    def _load(self):
        with open(self.root/'oncokb_final_database.csv',encoding='utf-8-sig',errors='replace') as h:
            for r in csv.DictReader(h):
                key=(r['Chr'].removeprefix('chr'),int(float(r['Start'])),r['Ref'].upper(),r['Alt'].upper())
                self.oncokb[key].append(compact('OncoKB',r,['oncoKB_annotation'],'GRCh38_exact'))
        with open(self.root/'CIVic.2024.clinicalevidence.csv',encoding='utf-8-sig',errors='replace') as h:
            for r in csv.DictReader(h):
                item=compact('CIViC',r,['gene','variant','disease','therapies','evidence_type','evidence_direction','evidence_level','significance','citation_id','evidence_id'],'')
                gene=clean(r.get('gene')).upper(); variant=clean(r.get('variant')).upper().removeprefix('P.')
                if gene and re.fullmatch(r'[A-Z*]\d+[A-Z*]',variant):
                    x=dict(item); x['match']='protein_exact'; self.civic_protein[(gene,variant)].append(x)
                if r.get('reference_build')=='GRCh38' and clean(r.get('chromosome')) and clean(r.get('start')) and clean(r.get('reference_bases')):
                    key=(clean(r['chromosome']).removeprefix('chr'),int(float(r['start'])),r['reference_bases'].upper(),r['variant_bases'].upper())
                    x=dict(item); x['match']='GRCh38_exact'; self.civic_coord[key].append(x)
        self.cgi={k.casefold():v for k,v in json.load(open(self.root/'CGI_database.json',encoding='utf-8')).items()}
        self.mcg={k.casefold():v for k,v in json.load(open(self.root/'MyCancerGenome_Biomarker.json',encoding='utf-8')).items()}
        with open(self.root/'COSMIC_filtered.tsv',encoding='utf-8-sig',errors='replace') as h:
            for r in csv.DictReader(h,delimiter='\t'):
                gene=clean(r.get('GENE')).upper()
                tokens=' '.join((clean(r.get('MUTATION_REMARK')),clean(r.get('MUTATION_REMARK_split')),clean(r.get('MUTATION_AA_SYNTAX'))))
                for variant in set(re.findall(rf'(?i)(?:{re.escape(gene)}[_ :.-]*)?([A-Z]\d+[A-Z*])',tokens)):
                    self.cosmic[(gene,variant.upper())].append(compact('COSMIC',r,['DISEASE','ACTIONABILITY_RANK','DEVELOPMENT_STATUS','DRUG_COMBINATION','TRIAL_ID','SOURCE','CLASSIFICATION_ID'],'protein_exact'))

    def snv(self,row):
        uploaded=clean(row.get('#Uploaded_variation',row.get('Uploaded_variation','')))
        m=re.match(r'(?:chr)?([^_]+)_(\d+)_([^/]+)/(.+)',uploaded)
        coord=(m[1],int(m[2]),m[3].upper(),m[4].upper()) if m else None
        gene=clean(row.get('SYMBOL')).upper(); protein=protein_change(row); found=[]
        if coord: found.extend(self.oncokb.get(coord,[])); found.extend(self.civic_coord.get(coord,[]))
        if gene and protein:
            found.extend(self.civic_protein.get((gene,protein),[])); found.extend(self.cosmic.get((gene,protein),[]))
            cgi_key=f'{gene}.p.{protein}'.casefold(); mcg_key=f'{gene} {protein}'.casefold()
            if cgi_key in self.cgi: found.extend(self._json_items('CGI',self.cgi[cgi_key],f'{gene}.p.{protein}','protein_exact'))
            if mcg_key in self.mcg: found.extend(self._json_items('MyCancerGenome',self.mcg[mcg_key],f'{gene} {protein}','protein_exact'))
        return self._unique(found)

    def structural(self,genes,event):
        found=[]
        for gene in genes:
            candidates=[]
            if event=='amplification': candidates=[f'{gene} amplification']
            elif event=='fusion': candidates=[f'{gene} fusion']
            elif event=='deletion': candidates=[f'{gene} deletion',f'{gene} loss']
            for key in candidates:
                if key.casefold() in self.cgi: found.extend(self._json_items('CGI',self.cgi[key.casefold()],key,'gene_event_exact'))
                if key.casefold() in self.mcg: found.extend(self._json_items('MyCancerGenome',self.mcg[key.casefold()],key,'gene_event_exact'))
        return self._unique(found)

    def _json_items(self,source,value,key,match):
        values=value if isinstance(value,list) else [value]; out=[]
        for v in values[:25]:
            if not isinstance(v,dict): continue
            fields=['Drug','Drug status','Association','Evidence level','Primary Tumor type full name','Source','Page','Variant Type','Description','Clinical Trials']
            item={k:clean(v.get(k,'')) for k in fields if clean(v.get(k,''))}
            therapies=v.get('Biomarker-Directed Therapies',{})
            if therapies:
                item['therapies']=[{'drug':drug,'diseases':sorted((details.get('disease') or {}).keys())} for drug,details in list(therapies.items())[:50]]
            drug=clean(v.get('Drug'))
            item.update({'source':source,'match':match,'key':key,'actionable':drug not in ('','[]') if source=='CGI' else bool(therapies)})
            out.append(item)
        return out

    @staticmethod
    def _unique(items):
        seen=set(); out=[]
        for x in items:
            key=json.dumps(x,sort_keys=True,ensure_ascii=False)
            if key not in seen: seen.add(key); out.append(x)
        return out

    def manifest(self):
        return {'directory':self.root.name,'sources':{'OncoKB_exact_GRCh38':sum(map(len,self.oncokb.values())),'CIViC_exact_GRCh38':sum(map(len,self.civic_coord.values())),'CIViC_protein':sum(map(len,self.civic_protein.values())),'CGI_biomarkers':len(self.cgi),'COSMIC_protein_records':sum(map(len,self.cosmic.values())),'MyCancerGenome_biomarkers':len(self.mcg)},'matching':'deterministic_exact','coordinate_build':'GRCh38'}

def overlap_genes(path,chrom,start,end):
    chrom=chrom.removeprefix('chr'); genes=set()
    with open(Path(path)/'Genes'/'GRCh38'/'genes.RefSeq.sorted.bed',encoding='utf-8',errors='replace') as h:
        for line in h:
            cols=line.rstrip().split('\t')
            if cols[0]!=chrom: continue
            left,right=int(cols[1]),int(cols[2])
            if left>=end: break
            if right>start: genes.add(cols[4])
    return sorted(genes)

def snv(args):
    db=CancerEvidence(args.cancer_db)
    evidence=['CLIN_SIG','ClinVar_CLNSIG','CIVIC','CIVIC_annotation','OncoKB','oncoKB_annotation','CGI_annotation','COSMIC','Existing_variation','cancer_actionable']
    af_fields=['gnomADe_AF','gnomADg_AF','gnomAD_AF','AF']
    counts={'all':0,'reportable_high_risk':0,'actionable':0,'oncogenic':0,'possible':0}; onco_counts={}; oncovi_counts={}
    category_rows=[]
    with opener(args.input) as source, ExitStack() as stack:
        reader=csv.DictReader((line for line in source if not line.startswith('##')),delimiter='\t')
        fields=list(reader.fieldnames or [])+['high_risk','high_risk_basis','cancer_evidence_sources','cancer_actionable','cancer_type_match','cancer_evidence']
        outputs={name:stack.enter_context(open(f'{args.output_prefix}.snv.{suffix}.tsv','w',encoding='utf-8',newline='')) for name,suffix in [('all','all'),('reportable','reportable'),('actionable','actionable'),('oncogenic','oncogenic'),('possible','possible_germline')]}
        writers={name:csv.DictWriter(handle,fieldnames=fields,delimiter='\t',extrasaction='ignore') for name,handle in outputs.items()}
        for writer in writers.values():writer.writeheader()
        for row in reader:
            category_rows.append(dict(row))
            high_risk=reportable_high_risk(row); bases=[]
            if high_risk and clinvar_pathogenic(row): bases.append('ClinVar Pathogenic/Likely pathogenic')
            if high_risk and oncogenic_high_risk(row): bases.append(clean(row.get('oncogenicity_classification')))
            # Drug matching is deliberately downstream of the reportable-risk gate.
            items=mark_tumor_context(db.snv(row),args.cancer_type) if high_risk else []
            row['high_risk']='true' if high_risk else 'false'; row['high_risk_basis']='|'.join(bases)
            row['cancer_evidence_sources']='|'.join(sorted({x['source'] for x in items})); row['cancer_evidence']=evidence_text(items); row['cancer_actionable']='true' if high_risk and any(x.get('actionable') for x in items) else 'false'; row['cancer_type_match']='true' if any(x.get('tumor_type_match')=='true' for x in items) else ('false' if items and args.cancer_type else 'unknown')
            writers['all'].writerow(row); counts['all']+=1
            if high_risk: writers['reportable'].writerow(row); counts['reportable_high_risk']+=1
            if row.get('cancer_actionable')=='true':writers['actionable'].writerow(row);counts['actionable']+=1
            label=clean(row.get('oncogenicity_classification'))
            if label in ('Oncogenic','Likely Oncogenic'):writers['oncogenic'].writerow(row);counts['oncogenic']+=1
            if label:onco_counts[label]=onco_counts.get(label,0)+1
            ref_label=clean(row.get('oncovi_2026_classification'))
            if ref_label:oncovi_counts[ref_label]=oncovi_counts.get(ref_label,0)+1
            vals=[]
            for key in af_fields:
                for token in re.split('[,&]',str(row.get(key,''))):
                    try: vals.append(float(token))
                    except ValueError: pass
            if vals and max(vals)>=float(args.population_af_max):writers['possible'].writerow(row);counts['possible']+=1
    hereditary,insilico=secondary_categories(category_rows,args.acmg_genes)
    for name,rows in [('hereditary_high_risk',hereditary),('in_silico_candidates',insilico)]:
        fields=list(rows[0]) if rows else ['variant','gene','hgvsc','hgvsp','consequence','evidence','tumor_only_status']
        write_rows(f'{name}.tsv',fields,rows)
    json.dump({'all_variants':counts['all'],'vep_transcript_annotations':counts['all'],'reportable_high_risk':counts['reportable_high_risk'],'actionable_high_risk':counts['actionable'],'oncogenic_or_likely_oncogenic':counts['oncogenic'],'possible_germline':counts['possible'],'hereditary_high_risk':len(hereditary),'in_silico_candidates':len(insilico),'reporting_gate':'non_synonymous AND (ClinVar P/LP OR oncogenicity O/LO); drug matching occurs after this gate','oncogenicity_classification_counts':onco_counts,'oncogenicity_profile':'strict_sop_2022_with_oncovi_2026_resources','oncovi_2026_classification_counts':oncovi_counts,'oncovi_2026_profile':'oncovi_2026_reference_99fa580','oncovi_2026_validation_status':'classification_benchmark_93_of_93;score_exact_86_of_93;criteria_exact_85_of_93;vep112_20260804','cancer_databases':db.manifest(),'somatic_status_note':'Tumor-only; somatic origin is not confirmed.'},open(f'{args.output_prefix}.snv.summary.json','w'),indent=2)

def structural(args):
    db=CancerEvidence(args.cancer_db)
    rows=[]
    with opener(args.input) as h:
        for line in h:
            if line.startswith('#'): continue
            cols=line.rstrip('\n').split('\t'); info={}
            for item in cols[7].split(';'):
                k,_,v=item.partition('='); info[k]=v or 'true'
            start=int(cols[1]); end=int(info.get('END',start)); svtype=info.get('SVTYPE',info.get('TYPE','')).upper()
            genes=set(filter(None,re.split(r'[,|&;]',info.get('GENE',info.get('SYMBOL','')))))
            genes.update(overlap_genes(args.annotsv_annotations,cols[0],max(0,start-1),end))
            event='amplification' if svtype in ('DUP','GAIN','AMP','CNV_GAIN') else 'deletion' if svtype in ('DEL','LOSS','CNV_LOSS') else 'fusion' if svtype in ('BND','TRA','INV','FUSION') else ''
            items=mark_tumor_context(db.structural(sorted(genes),event),args.cancer_type)
            rows.append({'chrom':cols[0],'pos':cols[1],'id':cols[2],'ref':cols[3],'alt':cols[4],
                         'filter':cols[6],'kind':args.kind,'svtype':info.get('SVTYPE',info.get('TYPE','')),
                         'end':info.get('END',''),'gene':'|'.join(sorted(genes)), 'annotsv_gene_count':len(genes),
                         'clinical_evidence':info.get('CLNSIG',info.get('CIVIC',info.get('ONCOKB',''))),
                         'cancer_evidence_sources':'|'.join(sorted({x['source'] for x in items})),'cancer_actionable':'true' if any(x.get('actionable') for x in items) else 'false','cancer_type_match':'true' if any(x.get('tumor_type_match')=='true' for x in items) else ('false' if items and args.cancer_type else 'unknown'),'cancer_evidence':evidence_text(items),'info':cols[7]})
    fields=['chrom','pos','end','id','ref','alt','filter','kind','svtype','gene','annotsv_gene_count','clinical_evidence','cancer_evidence_sources','cancer_actionable','cancer_type_match','cancer_evidence','info']
    actionable=[r for r in rows if r.get('cancer_actionable')=='true' or truthy(r,['clinical_evidence'])]
    write_rows(f'{args.output_prefix}.all.tsv',fields,rows); write_rows(f'{args.output_prefix}.actionable.tsv',fields,actionable)
    json.dump({'kind':args.kind,'all_variants':len(rows),'actionable':len(actionable),'cancer_databases':db.manifest(),'gene_annotation':'AnnotSV Annotations_Human/Genes/GRCh38/genes.RefSeq.sorted.bed'},open(f'{args.output_prefix}.summary.json','w'),indent=2)

def main():
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest='mode',required=True)
    a=sub.add_parser('snv'); a.add_argument('--input',required=True); a.add_argument('--sample',required=True); a.add_argument('--output-prefix',required=True); a.add_argument('--population-af-max',default=.01); a.add_argument('--cancer-db',required=True); a.add_argument('--cancer-type',default=''); a.add_argument('--acmg-genes',required=True)
    b=sub.add_parser('structural'); b.add_argument('--input',required=True); b.add_argument('--sample',required=True); b.add_argument('--kind',choices=['sv','cnv'],required=True); b.add_argument('--output-prefix',required=True); b.add_argument('--cancer-db',required=True); b.add_argument('--annotsv-annotations',required=True); b.add_argument('--cancer-type',default='')
    args=p.parse_args(); snv(args) if args.mode=='snv' else structural(args)
if __name__=='__main__': main()
