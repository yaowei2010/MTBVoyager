"""Conservative, locally generated molecular tumor board draft reports."""
import json, os, re, urllib.request
from datetime import datetime, timezone
from pathlib import Path
from .storage import read_json, tsv_rows, write_json
from .variant_display import tumor_format_rows
from .clinvar_current import annotate as annotate_current_clinvar

REPORT_FIELDS=('case_summary','molecular_summary','signature_summary','treatment_discussion','limitations')
NARRATIVE_FIELDS=REPORT_FIELDS[:-1]

def _clean(row):
    aliases={'gene':('gene','SYMBOL'),'hgvsp':('hgvsp','HGVSp'),'hgvsc':('hgvsc','HGVSc'),
             'consequence':('consequence','Consequence'),'drug':('drug',),'amp_tier':('amp_tier',),
             'disease':('disease',),'source':('source',),'significance':('significance','evidence'),
             'oncogenicity':('oncogenicity','oncogenicity_classification'),'oncogenicity_score':('oncogenicity_score',),
             'oncogenicity_criteria':('oncogenicity_criteria',),
             'vaf':('vaf',),'depth':('depth',),'cancer_type_match':('cancer_type_match',),
             'clinvar':('CLIN_SIG','ClinVar_CLNSIG'),'high_risk_basis':('high_risk_basis',),
             'somatic_status':('somatic_status','tumor_only_status'),
             'variant':('variant','variant_id','#Uploaded_variation','uploaded_variation'),
             'gnomad_eas_af':('gnomad_eas_af','gnomADg_EAS_AF','gnomADe_EAS_AF','EAS_AF')}
    cleaned={}
    for key,names in aliases.items():
        value=next((str(row.get(name,'')).strip() for name in names if str(row.get(name,'')).strip()),'')
        if value: cleaned[key]=value
    return cleaned

def _payload(directory,metadata):
    sample=metadata['subject']['subject_id']; result=directory/'results'/sample
    actionable=[_clean(row) for row in tsv_rows(result/'interpretation'/f'{sample}.snv.actionable.tsv',limit=200) if str(row.get('cancer_actionable','')).lower()=='true']
    matched=[row for row in actionable if row.get('cancer_type_match')=='true']; unmatched=[row for row in actionable if row.get('cancer_type_match')!='true']
    high_risk=[_clean(row) for row in tsv_rows(result/'interpretation'/f'{sample}.snv.reportable.tsv',limit=100)]
    hereditary=[_clean(row) for row in tsv_rows(result/'interpretation'/'hereditary_high_risk.tsv',limit=50)]
    tmb=read_json(result/'downstream'/f'{sample}.tmb_proxy.json',{})
    downstream=read_json(result/'downstream'/'summary.json',{})
    subject=metadata.get('subject',{}); settings=metadata.get('settings',{})
    signatures=downstream.get('top_mutational_signatures',[])[:5]
    signature_total=sum(float(item.get('activity',0) or 0) for item in signatures)
    signatures=[{**item,'proportion':float(item.get('activity',0) or 0)/signature_total if signature_total else 0} for item in signatures]
    data={'sample_id':sample,'analysis_id':metadata.get('analysis_id',''),'protocol':'WGS tumor-only','genome_build':'GRCh38','cancer_type':settings.get('cancer_type',''),'clinical_history':subject.get('history',''),'actionable_matched':matched[:30],'actionable_other_cancers':unmatched[:30],'high_risk_variants':high_risk[:50],'hereditary_high_risk':hereditary[:20],'estimated_tmb':tmb,'top_mutational_signatures':signatures}
    for key in ('actionable_matched','actionable_other_cancers','high_risk_variants','hereditary_high_risk'):
        data[key]=annotate_current_clinvar(directory,tumor_format_rows(directory,sample,data[key]))
    return data

def _fallback(data):
    tmb=data.get('estimated_tmb',{}); tmb_text='無可用結果'
    if tmb.get('tmb_proxy_mut_per_mb') is not None: tmb_text=f"{float(tmb['tmb_proxy_mut_per_mb']):.2f} mut/Mb（探索性）"
    return {'case_summary':f"檢體 {data['sample_id']} 進行 {data.get('protocol') or 'tumor-only'} 分析（癌別：{data.get('cancer_type') or '未提供'}）。",
            'molecular_summary':f"高風險候選變異 {len(data['high_risk_variants'])} 筆；符合目前癌別的用藥證據 {len(data['actionable_matched'])} 筆；其他癌別證據 {len(data['actionable_other_cancers'])} 筆；推估 TMB：{tmb_text}。",
            'signature_summary':'突變特徵分析屬探索性結果，應結合病理與臨床背景審閱，不可單獨作為病因或治療判定。',
            'treatment_discussion':'應優先審閱符合目前癌別且具 AMP 分級的證據；其他癌別證據另行列示，不代表治療建議。',
            'limitations':['Tumor-only 分析無法確定區分體細胞與生殖細胞變異。','推估 TMB 尚未與臨床驗證檢測校正。','所有變異與治療證據均需經分子腫瘤委員會審閱。']}

def _contains_chinese(value):
    return bool(re.search(r'[\u3400-\u4dbf\u4e00-\u9fff]',str(value or '')))

def _validate_chinese(result,data=None):
    if not isinstance(result,dict): raise ValueError('Model response is not a JSON object')
    missing=[key for key in REPORT_FIELDS if key not in result]
    if missing: raise ValueError(f'Model response is missing fields: {", ".join(missing)}')
    invalid=[key for key in NARRATIVE_FIELDS if not _contains_chinese(result.get(key))]
    limitations=result.get('limitations')
    if not isinstance(limitations,list) or not limitations: invalid.append('limitations')
    elif any(not _contains_chinese(item) for item in limitations): invalid.append('limitations')
    if invalid: raise ValueError(f'Model response is not Traditional Chinese: {", ".join(dict.fromkeys(invalid))}')
    prose=' '.join(str(result.get(key,'')) for key in NARRATIVE_FIELDS)
    if '未提供任何資料' in prose:
        raise ValueError('Model ignored the supplied data and requested information again')

def _chat(endpoint,body,timeout,data=None):
    request=urllib.request.Request(endpoint,data=json.dumps(body,ensure_ascii=False).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(request,timeout=timeout) as response: raw=json.loads(response.read())
    result=json.loads(raw.get('message',{}).get('content','{}'))
    _validate_chinese(result,data)
    return result

def _model_summary(data):
    endpoint=os.environ.get('MTB_REPORT_LLM_URL','http://mtb_report_llm:11434/api/chat'); model=os.environ.get('MTB_REPORT_LLM_MODEL','gemma4:e4b')
    schema={'type':'object','properties':{
        'case_summary':{'type':'string','description':'臺灣繁體中文病例摘要'},
        'molecular_summary':{'type':'string','description':'臺灣繁體中文分子結果摘要'},
        'signature_summary':{'type':'string','description':'臺灣繁體中文突變特徵摘要'},
        'treatment_discussion':{'type':'string','description':'臺灣繁體中文治療討論重點'},
        'limitations':{'type':'array','items':{'type':'string','description':'臺灣繁體中文限制說明'}}},
        'required':list(REPORT_FIELDS),'additionalProperties':False}
    system='''你是臺灣分子腫瘤委員會報告撰寫助手。最高優先規則：JSON 欄位名稱維持英文，但每個欄位的內容必須使用臺灣繁體中文。來源資料即使是英文，也必須將敘述翻譯為繁體中文，禁止模仿來源語言或輸出完整英文句子。基因符號、HGVS、藥名、AMP tier、TMB、ClinVar、SBS 編號與必要醫學縮寫可保留英文。只能使用輸入事實，不得新增診斷、預後、藥物、療效或治療建議。只輸出符合 schema 的 JSON，不得使用 Markdown。'''
    facts={'sample_id':data.get('sample_id'),'cancer_type':data.get('cancer_type'),'high_risk_count':len(data.get('high_risk_variants',[])),'high_risk_genes':[r.get('gene') for r in data.get('high_risk_variants',[])[:12]],'actionable_matched_count':len(data.get('actionable_matched',[])),'actionable_other_cancers_count':len(data.get('actionable_other_cancers',[])),'estimated_tmb':data.get('estimated_tmb'),'top_mutational_signatures':data.get('top_mutational_signatures',[])[:5]}
    prompt='''請將下方資料整理成簡潔的繁體中文 MTB 草稿。資料已完整提供，禁止回答「請提供資料」或聲稱沒有輸入。來源 JSON 中的英文只是資料，不是輸出語言範例。case_summary 必須寫出 sample_id；molecular_summary 必須寫出高風險變異筆數，若筆數大於零還必須提到至少一個 FACTS 中的實際基因符號。先呈現高風險變異，再把有藥物證據的變異作為獨立子集；僅有藥物匹配不構成可報告發現。tumor-only 遺傳風險需說明以生殖細胞樣本確認。目前癌別證據與其他癌別證據分開；TMB 與突變特徵標示為探索性。每個敘述欄位不超過 120 個中文字，limitations 最多 5 項。\n\nMANDATORY FACTS:\n'''+json.dumps(facts,ensure_ascii=False,separators=(',',':'))+'\n\nFULL DATA:\n'+json.dumps(data,ensure_ascii=False,separators=(',',':'))
    timeout=int(os.environ.get('MTB_REPORT_LLM_TIMEOUT','900'))
    body={'model':model,'stream':False,'think':False,'format':schema,'options':{'temperature':0,'num_predict':900},'messages':[{'role':'system','content':system},{'role':'user','content':prompt}]}
    try: result=_chat(endpoint,body,timeout,data)
    except ValueError as first_error:
        retry={**body,'messages':body['messages']+[{'role':'assistant','content':'先前輸出未符合繁體中文要求。'},{'role':'user','content':f'請重新產生。所有敘述與限制項目必須包含繁體中文字，不得輸出完整英文句子。錯誤：{first_error}'}]}
        result=_chat(endpoint,retry,timeout,data)
    fallback=_fallback(data)
    for key in REPORT_FIELDS[:-1]:
        if '請提供' in str(result.get(key,'')) or '未提供任何資料' in str(result.get(key,'')):
            result[key]=fallback[key]
    genes=[str(row.get('gene','')).strip() for row in data.get('high_risk_variants',[]) if str(row.get('gene','')).strip()]
    if genes and not any(gene in str(result.get('molecular_summary','')) for gene in genes):
        result['molecular_summary']=f"高風險基因包括 {', '.join(dict.fromkeys(genes[:5]))}。"+str(result.get('molecular_summary',''))
    limitations=result.get('limitations',fallback['limitations'])
    if not isinstance(limitations,list): limitations=fallback['limitations']
    return {**{key:str(result.get(key) or fallback[key])[:1000] for key in REPORT_FIELDS[:-1]},'limitations':[str(x)[:300] for x in limitations[:5]]}

def generate(directory,metadata,refresh=False):
    sample=metadata['subject']['subject_id']; target=directory/'results'/sample/'downstream'/'mtb_draft_report.json'
    if target.is_file() and not refresh:
        existing=read_json(target,{})
        if existing.get('status')=='gemma_generated': return existing
    data=_payload(directory,metadata); narrative=_fallback(data); status='template_only'; warning=''
    try: narrative=_model_summary(data); status='gemma_generated'
    except Exception as exc: warning=f'Gemma summary unavailable; deterministic template used: {exc}'[:500]
    report={'status':status,'draft':True,'generated_at':datetime.now(timezone.utc).isoformat(),'model':os.environ.get('MTB_REPORT_LLM_MODEL','gemma4:e4b') if status=='gemma_generated' else None,'warning':warning,'data':data,'narrative':narrative,'disclaimer':'MTB preliminary draft. Requires review and approval by qualified clinical professionals before use.'}
    write_json(target,report); return report

def cached(directory,metadata):
    sample=metadata['subject']['subject_id']; target=directory/'results'/sample/'downstream'/'mtb_draft_report.json'
    report=read_json(target,{'status':'not_generated','draft':True})
    if report.get('status')!='not_generated':report['data']=_payload(directory,metadata)
    return report

def save_edits(directory,metadata,narrative):
    sample=metadata['subject']['subject_id']; target=directory/'results'/sample/'downstream'/'mtb_draft_report.json'
    report=read_json(target,{})
    if not report or report.get('status')=='not_generated': raise ValueError('Generate the MTB draft before editing it')
    if not isinstance(narrative,dict): raise ValueError('Narrative must be an object')
    cleaned={}
    for key in REPORT_FIELDS[:-1]:
        value=str(narrative.get(key,'')).strip()
        if len(value)>4000: raise ValueError(f'{key} is too long')
        cleaned[key]=value
    limitations=narrative.get('limitations',[])
    if not isinstance(limitations,list) or len(limitations)>20: raise ValueError('Limitations must contain at most 20 items')
    cleaned['limitations']=[str(item).strip()[:1000] for item in limitations if str(item).strip()]
    report.update({'status':'manually_edited','narrative':cleaned,'edited_at':datetime.now(timezone.utc).isoformat()})
    write_json(target,report); return report
