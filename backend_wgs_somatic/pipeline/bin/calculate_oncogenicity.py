#!/usr/bin/env python3
"""Deterministic ClinGen/CGC/VICC oncogenicity scoring for GRCh38 SNV/indel calls."""
import argparse, copy, csv, gzip, json, re
from collections import defaultdict
from pathlib import Path

POINTS={'OVS1':8,'OS1':4,'OS2':4,'OS3':4,'OM1':2,'OM2':2,'OM3':2,'OM4':2,
        'OP1':1,'OP2':1,'OP3':1,'OP4':1,'SBVS1':-8,'SBS1':-4,'SBS2':-4,'SBP1':-1,'SBP2':-1}
PROFILE='strict_sop_2022_with_oncovi_2026_resources'
REFERENCE_PROFILE='oncovi_2026_reference_99fa580'
REFERENCE_VALIDATION='classification_benchmark_93_of_93;score_exact_86_of_93;criteria_exact_85_of_93;vep112_20260804'
COMMIT='99fa5801163bb6bd32d97e916ca2249bb9429d81'
AA3={'Ala':'A','Arg':'R','Asn':'N','Asp':'D','Cys':'C','Gln':'Q','Glu':'E','Gly':'G','His':'H','Ile':'I','Leu':'L','Lys':'K','Met':'M','Phe':'F','Pro':'P','Ser':'S','Thr':'T','Trp':'W','Tyr':'Y','Val':'V','Ter':'*'}

def clean(value):
    value=str(value or '').strip()
    return '' if value.casefold() in ('-','.','nan','none','null') else value

def numbers(value):
    out=[]
    for token in re.split(r'[,|&]',clean(value)):
        try: out.append(float(token))
        except ValueError: pass
    return out

def classify(score):
    if score >= 10:return 'Oncogenic'
    if score >= 6:return 'Likely Oncogenic'
    if score >= 0:return 'VUS'
    if score >= -6:return 'Likely Benign'
    return 'Benign'

def collapse(rows):
    grouped=defaultdict(list)
    for i,row in enumerate(rows):
        key=clean(row.get('#Uploaded_variation',row.get('Uploaded_variation'))) or f'row:{i}'
        grouped[key].append(row)
    def rank(row):
        return (clean(row.get('PICK'))=='1',bool(clean(row.get('MANE_SELECT'))),clean(row.get('CANONICAL'))=='YES',bool(clean(row.get('SYMBOL'))),bool(clean(row.get('HGVSp'))))
    return [max(group,key=rank) for group in grouped.values()]

def one_letter_change(row):
    aa=clean(row.get('Amino_acids')); pos=clean(row.get('Protein_position')).split('-')[0]
    if '/' in aa and pos.isdigit():
        ref,alt=aa.split('/',1)
        if len(ref)==len(alt)==1:return ref.upper(),int(pos),alt.upper()
    hgvsp=clean(row.get('HGVSp'))
    match=re.search(r'p\.([A-Z][a-z]{2})(\d+)([A-Z][a-z]{2}|Ter)',hgvsp)
    return (AA3.get(match[1],''),int(match[2]),AA3.get(match[3],'')) if match else ('',None,'')

def protein_key(row):
    hgvsp=clean(row.get('HGVSp')).split(':')[-1]
    if hgvsp.startswith('p.'):
        return re.sub(r'Ala|Arg|Asn|Asp|Cys|Gln|Glu|Gly|His|Ile|Leu|Lys|Met|Phe|Pro|Ser|Thr|Trp|Tyr|Val|Ter',lambda m:AA3[m.group(0)],hgvsp[2:])
    ref,pos,alt=one_letter_change(row)
    return f'{ref}{pos}{alt}' if ref and pos and alt else ''

class Resources:
    def __init__(self,root):
        self.root=Path(root)
        self.bona_tsg=self.lines('bona_fide_tsg.txt'); self.tsg=self.lines('tsg_list.txt'); self.ogs=self.lines('ogs_list.txt')
        self.cgi=self.load('cgi_dictionary.txt'); self.hotspots=self.load('single_residue_dict.txt')
        self.indels=self.load('inframe_indel_dict.txt'); self.domains=self.load('domains_dictionary.txt'); self.mutsplice=self.load('mut_splice_dict.txt')
        self.grantham=self._grantham(); self.cgi_residue=defaultdict(list)
        self.os2_selected={x.strip('"') for x in self.lines('os2_manually_selected.txt')} if (self.root/'os2_manually_selected.txt').exists() else set()
        cosmic=self.root/'cosmic_all_dictionary.txt.gz'
        self.cosmic=json.load(gzip.open(cosmic,'rt',encoding='utf-8')) if cosmic.exists() else {}
        for key in self.cgi:
            m=re.fullmatch(r'([^:]+):p\.([A-Z])(\d+)([A-Z*])',key)
            if m:self.cgi_residue[(m[1].upper(),m[2],int(m[3]))].append(m[4])
    def lines(self,name): return {clean(x) for x in open(self.root/name,encoding='utf-8') if clean(x)}
    def load(self,name): return json.load(open(self.root/name,encoding='utf-8'))
    def _grantham(self):
        with open(self.root/'grantham.tsv',encoding='utf-8') as h:
            r=csv.DictReader(h,delimiter='\t'); return {(x[r.fieldnames[0]],aa):float(x[aa]) for x in r for aa in r.fieldnames[1:] if clean(x[aa])}
    def grantham_distance(self,ref,alt):
        return max(self.grantham.get((ref,alt),0),self.grantham.get((alt,ref),0))

def result(code,status,reason,source='',value=None,excluded_by=''):
    item={'code':code,'status':status,'points':POINTS[code] if status=='met' else 0,'reason':reason}
    if source:item['source']=source
    if value is not None:item['value']=value
    if excluded_by:item['excluded_by']=excluded_by
    return item

def evaluate(row,res,tumor_type=''):
    gene=clean(row.get('SYMBOL')).upper(); consequences=set(clean(row.get('Consequence')).split('&'))
    refaa,pos,altaa=one_letter_change(row); protein=f'{refaa}{pos}{altaa}' if pos and refaa and altaa else ''
    hgvsc=clean(row.get('HGVSc')); transcript=hgvsc.split(':')[0].split('.')[0] if ':' in hgvsc else ''
    cdna=hgvsc.split(':',1)[1] if ':' in hgvsc else ''
    ev={}; null={'stop_gained','frameshift_variant','start_lost','splice_donor_variant','splice_acceptor_variant'}
    if gene not in res.bona_tsg: ev['OVS1']=result('OVS1','not_met','Gene is not in the OncoVI bona-fide TSG resource','OncoVI/CGC/OncoKB')
    elif consequences & null: ev['OVS1']=result('OVS1','met','Predicted null variant in a bona-fide tumor suppressor gene','VEP+OncoVI gene roles',sorted(consequences & null))
    elif gene in res.mutsplice and cdna in res.mutsplice[gene].get(transcript,[]): ev['OVS1']=result('OVS1','met','Experimentally catalogued splice defect in MutSpliceDB','OncoVI MutSpliceDB',cdna)
    else: ev['OVS1']=result('OVS1','not_met','No qualifying null or curated splice consequence')

    cgi_protein=protein_key(row); cgi_key=f'{gene}:p.{cgi_protein}' if cgi_protein else ''
    ev['OS1']=result('OS1','met','Exact protein change is in the OncoVI CGI oncogenic seed','OncoVI CGI',cgi_key) if cgi_key in res.cgi else result('OS1','not_met','No exact protein match in the oncogenic seed','OncoVI CGI')
    ev['OS2']=result('OS2','not_assessable','Requires explicitly curated reproducible in-vitro/in-vivo functional evidence; germline ClinVar is not substituted')

    hotspot=res.hotspots.get(gene,{}).get(f'{refaa}{pos}',{}) if pos else {}; same=int(hotspot.get(altaa,0) or 0); total=sum(int(x or 0) for x in hotspot.values())
    if ev['OS1']['status']=='met':ev['OS3']=result('OS3','excluded','OS1 already applies','Cancer Hotspots',excluded_by='OS1')
    elif total>=50 and same>=10:ev['OS3']=result('OS3','met','Hotspot has at least 50 residue observations and 10 exact substitutions','Cancer Hotspots via OncoVI',{'residue_count':total,'exact_count':same})
    elif hotspot:ev['OS3']=result('OS3','not_met','Hotspot counts do not meet OS3','Cancer Hotspots via OncoVI',{'residue_count':total,'exact_count':same})
    else:ev['OS3']=result('OS3','not_met','Residue is absent from the staged Cancer Hotspots resource','Cancer Hotspots via OncoVI')
    if not hotspot and ev['OS1']['status']!='met' and pos and gene in res.cosmic:
        cosmic_residue=res.cosmic[gene].get(str(pos),{}); cosmic_total=sum(int(n) for changes in cosmic_residue.values() for n in changes.values())
        cosmic_exact=sum(int(n) for n in cosmic_residue.get(f'p.{protein}',{}).values())
        if cosmic_total>=50 and cosmic_exact>=10:
            ev['OS3']=result('OS3','met','COSMIC fallback has at least 50 residue observations and 10 exact substitutions','OncoVI COSMIC',{'residue_count':cosmic_total,'exact_count':cosmic_exact})

    domain_hits=[]
    protein_positions=[]
    if pos: protein_positions=[pos]
    else:
        protein_positions=[int(x) for x in re.findall(r'(?<=[A-Za-z])(\d+)',clean(row.get('HGVSp')))]
    if protein_positions:
        for domain in res.domains.get(gene,[]):
            coords=[int(x) for x in re.findall(r'\d+',domain)]
            if coords and min(protein_positions)<=max(coords) and max(protein_positions)>=min(coords):domain_hits.append(domain)
    if ev['OS1']['status']=='met' or ev['OS3']['status']=='met': ev['OM1']=result('OM1','excluded','Strong residue evidence already applies',excluded_by='OS1/OS3')
    elif domain_hits:ev['OM1']=result('OM1','met','Protein position overlaps a UniProt functional domain, following the OncoVI 2026 interpretation','OncoVI UniProt domains',domain_hits[:10])
    else:ev['OM1']=result('OM1','not_met','No staged UniProt domain overlap','OncoVI UniProt domains')

    length_change=bool(consequences & {'inframe_insertion','inframe_deletion','protein_altering_variant'})
    om2=(length_change and gene in (res.ogs|res.tsg)) or ('stop_lost' in consequences and gene in res.tsg)
    if ev['OVS1']['status']=='met':ev['OM2']=result('OM2','excluded','OVS1 already applies',excluded_by='OVS1')
    elif om2:ev['OM2']=result('OM2','met','Qualifying protein-length change in an oncogene or tumor suppressor','VEP+OncoVI gene roles')
    else:ev['OM2']=result('OM2','not_met','No qualifying protein-length change and gene-role combination')

    alternatives=res.cgi_residue.get((gene,refaa,pos),[]) if pos else []; comparable=[]
    for known_alt in alternatives:
        if known_alt!=altaa and res.grantham_distance(refaa,altaa)>=res.grantham_distance(refaa,known_alt): comparable.append(known_alt)
    blockers=[x for x in ('OS3','OM1') if ev[x]['status']=='met']
    if blockers:ev['OM3']=result('OM3','excluded','OS3 or OM1 already applies',excluded_by='/'.join(blockers))
    elif comparable:ev['OM3']=result('OM3','met','Different oncogenic substitution at the same residue has no greater Grantham distance','OncoVI CGI+Grantham',comparable)
    else:ev['OM3']=result('OM3','not_met','No qualifying alternative oncogenic substitution at this residue','OncoVI CGI+Grantham')
    if ev['OS3']['status']=='met' or ev['OM1']['status']=='met' or ev['OM3']['status']=='met':ev['OM4']=result('OM4','excluded','Higher-priority residue evidence already applies',excluded_by='OS3/OM1/OM3')
    elif total<50 and same>=10:ev['OM4']=result('OM4','met','Hotspot has fewer than 50 residue observations and at least 10 exact substitutions','Cancer Hotspots via OncoVI',{'residue_count':total,'exact_count':same})
    else:ev['OM4']=result('OM4','not_met','Hotspot counts do not meet OM4','Cancer Hotspots via OncoVI',{'residue_count':total,'exact_count':same})

    predictors=[]
    def add_pred(name,value,damaging):
        if value is not None:predictors.append({'name':name,'value':value,'effect':'damaging' if damaging else 'benign'})
    vals=numbers(row.get('CADD_phred')); add_pred('CADD',max(vals) if vals else None,bool(vals and max(vals)>=20))
    vals=numbers(row.get('REVEL_score')); add_pred('REVEL',max(vals) if vals else None,bool(vals and max(vals)>=.5))
    vals=numbers(row.get('ClinPred_score')); add_pred('ClinPred',max(vals) if vals else None,bool(vals and max(vals)>=.5))
    am=clean(row.get('am_class')).casefold(); add_pred('AlphaMissense',am if am else None,am in ('pathogenic','likely_pathogenic'))
    splice=clean(row.get('SpliceAI_cutoff')).upper(); add_pred('SpliceAI',splice if splice else None,splice=='PASS')
    if len(predictors)<2:ev['OP1']=result('OP1','not_assessable','Fewer than two independent predictor groups are available','VEP plugins',predictors)
    elif all(x['effect']=='damaging' for x in predictors):ev['OP1']=result('OP1','met','All available predictor groups support an oncogenic effect','VEP plugins',predictors)
    else:ev['OP1']=result('OP1','not_met','Available predictor groups are benign or conflicting','VEP plugins',predictors)
    ev['OP2']=result('OP2','not_assessable','Requires a curated tumor-type/single-genetic-etiology mapping',value=tumor_type or '')

    indel_hit=None
    if consequences & {'inframe_insertion','inframe_deletion'} and protein_positions:
        for key,changes in res.indels.get(gene,{}).items():
            coords=[int(x) for x in key.split('-')]
            if min(protein_positions)>=min(coords) and max(protein_positions)<=max(coords):
                change=re.sub(r'^p\.','',clean(row.get('HGVSp')).split(':')[-1]); change=re.sub(r'([A-Z][a-z]{2})',lambda m:{'Asn':'N','Pro':'P','Ala':'A','Lys':'K','Val':'V','Arg':'R','Trp':'W','Thr':'T','Gln':'Q','Ile':'I'}.get(m.group(1),m.group(1)),change)
                indel_hit=int(changes.get(change,0) or 0); break
    if ev['OS3']['status']=='met' or ev['OM4']['status']=='met':ev['OP3']=result('OP3','excluded','Higher-priority hotspot evidence already applies',excluded_by='OS3/OM4')
    elif indel_hit is not None and indel_hit<10:ev['OP3']=result('OP3','met','In-frame change occurs fewer than 10 times in Cancer Hotspots','OncoVI Cancer Hotspots',indel_hit)
    elif hotspot and 0<same<10:ev['OP3']=result('OP3','met','Exact substitution occurs between 1 and 9 times at a Cancer Hotspots residue','Cancer Hotspots via OncoVI',{'residue_count':total,'exact_count':same})
    else:ev['OP3']=result('OP3','not_met','No qualifying low-count hotspot evidence','Cancer Hotspots via OncoVI')

    af_fields=['gnomADe_AF','gnomADg_AF']; af=[x for k in af_fields for x in numbers(row.get(k))]
    ev['OP4']=result('OP4','met','Absent or at most 1% in staged gnomAD annotations, matching the OncoVI 2026 operational threshold','VEP gnomAD',max(af) if af else 'absent') if not af or max(af)<=.01 else result('OP4','not_met','Population frequency exceeds 1%','VEP gnomAD',max(af))
    continental=['gnomADe_AFR_AF','gnomADe_EAS_AF','gnomADe_NFE_AF','gnomADe_AMR_AF','gnomADe_SAS_AF','gnomADg_AFR_AF','gnomADg_EAS_AF','gnomADg_NFE_AF','gnomADg_AMR_AF','gnomADg_SAS_AF']
    pop=[x for k in continental for x in numbers(row.get(k))]
    if pop and max(pop)>.05:
        ev['SBVS1']=result('SBVS1','met','Continental population AF exceeds 5%','VEP gnomAD',max(pop)); ev['SBS1']=result('SBS1','excluded','SBVS1 captures the same population evidence',excluded_by='SBVS1')
    else:
        ev['SBVS1']=result('SBVS1','not_met' if pop else 'not_assessable','No continental AF exceeds 5%' if pop else 'Continental population frequencies are unavailable','VEP gnomAD',max(pop) if pop else None)
        ev['SBS1']=result('SBS1','met','Continental population AF exceeds 1%','VEP gnomAD',max(pop)) if pop and max(pop)>.01 else result('SBS1','not_met' if pop else 'not_assessable','No continental AF exceeds 1%' if pop else 'Continental population frequencies are unavailable','VEP gnomAD',max(pop) if pop else None)
    ev['SBS2']=result('SBS2','not_assessable','Requires explicitly curated reproducible functional evidence showing no oncogenic effect')
    if len(predictors)<2:ev['SBP1']=result('SBP1','not_assessable','Fewer than two independent predictor groups are available','VEP plugins',predictors)
    elif all(x['effect']=='benign' for x in predictors):ev['SBP1']=result('SBP1','met','All available predictor groups support no effect','VEP plugins',predictors)
    else:ev['SBP1']=result('SBP1','not_met','Available predictor groups are damaging or conflicting','VEP plugins',predictors)
    conservation=numbers(row.get('phyloP100way_vertebrate_rankscore'))+numbers(row.get('phastCons100way_vertebrate_rankscore'))
    splice_benign=splice=='FAIL'
    if 'synonymous_variant' not in consequences:ev['SBP2']=result('SBP2','not_met','Variant is not synonymous')
    elif not conservation or not splice:ev['SBP2']=result('SBP2','not_assessable','Splice and conservation annotations are both required','VEP dbNSFP/SpliceAI')
    elif splice_benign and all(x<.5 for x in conservation):ev['SBP2']=result('SBP2','met','Synonymous variant has benign splice prediction and low conservation','VEP dbNSFP/SpliceAI',conservation)
    else:ev['SBP2']=result('SBP2','not_met','Splice or conservation evidence does not support a benign effect','VEP dbNSFP/SpliceAI',conservation)
    score=sum(x['points'] for x in ev.values()); dual_role=gene in res.tsg and gene in res.ogs
    return score,classify(score),[ev[x] for x in POINTS],dual_role

def evaluate_reference(row,res,strict_evidence):
    """Compatibility profile for upstream OncoVI commit 99fa580."""
    ev={x['code']:copy.deepcopy(x) for x in strict_evidence}
    gene=clean(row.get('SYMBOL')).upper(); consequence=clean(row.get('Consequence')); hgvsc=clean(row.get('HGVSc'))
    if gene in res.bona_tsg and ('stop_lost' in consequence or ('splice' in consequence and re.search(r'[+-]([1-4])(?:\D|$)',hgvsc))):
        ev['OVS1']=result('OVS1','met','OncoVI 2026 null/splice operational rule','OncoVI 99fa580')
    review=clean(row.get('ClinVar_germline_ReviewStatus',row.get('ClinVar_review_status'))).casefold()
    clinvar=clean(row.get('ClinVar_germline',row.get('CLIN_SIG')))
    accepted={'practice guideline','reviewed by expert panel','criteria provided, single submitter','criteria provided, multiple submitters, no conflicts'}
    if review in accepted and (('Pathogenic' in clinvar) or ('Likely pathogenic' in clinvar) or clinvar in res.os2_selected):
        ev['OS2']=result('OS2','met','ClinVar germline classification and review level meet the upstream OncoVI rule','OncoVI 99fa580',{'classification':clinvar,'review_status':review})
    else: ev['OS2']=result('OS2','not_met','Upstream OncoVI ClinVar rule is not met','OncoVI 99fa580')
    if review in accepted and (('Benign' in clinvar) or ('Likely benign' in clinvar)):
        ev['SBS2']=result('SBS2','met','ClinVar germline classification and review level meet the upstream OncoVI rule','OncoVI 99fa580',{'classification':clinvar,'review_status':review})
    else: ev['SBS2']=result('SBS2','not_met','Upstream OncoVI ClinVar rule is not met','OncoVI 99fa580')
    phy=numbers(row.get('phyloP100way_vertebrate_rankscore')); phast=numbers(row.get('phastCons100way_vertebrate_rankscore')); splice=clean(row.get('SpliceAI_cutoff')).upper()
    damaging=(splice=='PASS') or bool(phy and max(phy)>=.5) or bool(phast and max(phast)>=.5)
    ev['OP1']=result('OP1','met' if damaging else 'not_met','At least one available upstream predictor supports an effect' if damaging else 'No available upstream predictor supports an effect','OncoVI 99fa580')
    benign=splice=='FAIL' and bool(phy) and max(phy)<.5 and bool(phast) and max(phast)<.5
    ev['SBP1']=result('SBP1','met' if benign else 'not_met','All three upstream predictors support no effect' if benign else 'Upstream benign predictor conjunction is not met','OncoVI 99fa580')
    synonymous='synonymous_variant' in consequence
    ev['SBP2']=result('SBP2','met' if synonymous and benign else 'not_met','Synonymous and upstream benign predictor conjunction is met' if synonymous and benign else 'Upstream synonymous benign rule is not met','OncoVI 99fa580')
    ev['OP2']=result('OP2','not_met','OP2 is not implemented by upstream OncoVI because no suitable resource was identified','OncoVI 99fa580')
    exome=numbers(row.get('gnomADe_AF')); genome=numbers(row.get('gnomADg_AF'))
    upstream_op4=(not exome and not genome) or bool(genome and min(genome)<=.01) or bool(exome and min(exome)<=.01)
    ev['OP4']=result('OP4','met' if upstream_op4 else 'not_met','At least one available gnomAD data set is at most 1%, following upstream ordering' if upstream_op4 else 'Neither available gnomAD data set is at most 1%','OncoVI 99fa580',{'gnomADe_AF':exome,'gnomADg_AF':genome})
    continental=['gnomADe_AFR_AF','gnomADe_EAS_AF','gnomADe_NFE_AF','gnomADe_AMR_AF','gnomADe_SAS_AF','gnomADg_AFR_AF','gnomADg_EAS_AF','gnomADg_NFE_AF','gnomADg_AMR_AF','gnomADg_SAS_AF']
    pop=[x for k in continental for x in numbers(row.get(k)) if x != 0]
    ev['SBVS1']=result('SBVS1','met' if pop and max(pop)>.05 else 'not_met','Continental AF exceeds 5%' if pop and max(pop)>.05 else 'No continental AF exceeds 5%','OncoVI 99fa580',max(pop) if pop else None)
    ev['SBS1']=result('SBS1','met' if pop and max(pop)>.01 else 'not_met','Continental AF exceeds 1%' if pop and max(pop)>.01 else 'No continental AF exceeds 1%','OncoVI 99fa580',max(pop) if pop else None)
    score=sum(x['points'] for x in ev.values())
    return score,classify(score),[ev[x] for x in POINTS]

def main():
    p=argparse.ArgumentParser(); p.add_argument('--input',required=True);p.add_argument('--output',required=True);p.add_argument('--summary',required=True);p.add_argument('--resources',required=True);p.add_argument('--tumor-type',default='');a=p.parse_args()
    opener=gzip.open if a.input.endswith(('.gz','.bgz')) else open
    with opener(a.input,'rt',encoding='utf-8',errors='replace') as h:
        reader=csv.DictReader((x for x in h if not x.startswith('##')),delimiter='\t'); fields=reader.fieldnames or []; rows=collapse(list(reader))
    res=Resources(a.resources); counts=defaultdict(int); reference_counts=defaultdict(int); review=0
    extra=['oncogenicity_score','oncogenicity_classification','oncogenicity_criteria','oncogenicity_review_required','oncogenicity_evidence','oncogenicity_profile','oncovi_resource_commit','oncovi_2026_score','oncovi_2026_classification','oncovi_2026_criteria','oncovi_2026_evidence','oncovi_2026_profile','oncovi_2026_validation_status','oncogenicity_profile_difference']
    for row in rows:
        score,label,evidence,dual=evaluate(row,res,a.tumor_type); met=[x['code'] for x in evidence if x['status']=='met']; unassessed=[x['code'] for x in evidence if x['status']=='not_assessable']
        ref_score,ref_label,ref_evidence=evaluate_reference(row,res,evidence); ref_met=[x['code'] for x in ref_evidence if x['status']=='met']
        strict_status={x['code']:x['status'] for x in evidence}; ref_status={x['code']:x['status'] for x in ref_evidence}; differences=[x for x in POINTS if strict_status[x]!=ref_status[x]]
        required=dual or bool(unassessed) or any(x['status']=='met' for x in evidence if x['code'].startswith('SB')) and any(x['status']=='met' for x in evidence if x['code'].startswith('O'))
        row.update({'oncogenicity_score':score,'oncogenicity_classification':label,'oncogenicity_criteria':'|'.join(met),'oncogenicity_review_required':'true' if required else 'false','oncogenicity_evidence':json.dumps(evidence,ensure_ascii=False,separators=(',',':')),'oncogenicity_profile':PROFILE,'oncovi_resource_commit':COMMIT,'oncovi_2026_score':ref_score,'oncovi_2026_classification':ref_label,'oncovi_2026_criteria':'|'.join(ref_met),'oncovi_2026_evidence':json.dumps(ref_evidence,ensure_ascii=False,separators=(',',':')),'oncovi_2026_profile':REFERENCE_PROFILE,'oncovi_2026_validation_status':REFERENCE_VALIDATION,'oncogenicity_profile_difference':'|'.join(differences)})
        counts[label]+=1; reference_counts[ref_label]+=1; review+=required
    outopen=gzip.open if a.output.endswith('.gz') else open
    with outopen(a.output,'wt',encoding='utf-8',newline='') as h:
        w=csv.DictWriter(h,fieldnames=fields+extra,delimiter='\t',extrasaction='ignore');w.writeheader();w.writerows(rows)
    Path(a.summary).write_text(json.dumps({'profile':PROFILE,'guideline':'ClinGen/CGC/VICC 2022','oncovi_2026_commit':COMMIT,'oncovi_2026_profile':REFERENCE_PROFILE,'oncovi_2026_validation_status':REFERENCE_VALIDATION,'variants':len(rows),'classification_counts':dict(counts),'oncovi_2026_classification_counts':dict(reference_counts),'review_required':review,'scope':'SNV and small indel; not general CNV/SV/fusion'},indent=2)+'\n')
if __name__=='__main__':main()
