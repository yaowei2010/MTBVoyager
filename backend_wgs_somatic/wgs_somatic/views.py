import base64,csv,json,os,re,shutil
from datetime import datetime,timezone
from pathlib import Path
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from hw1.models import existJobs
from .runner import launch
from .storage import draft_dir,job_dir,new_id,read_json,save_upload,tsv_rows,validate_id,write_json
from .legacy_oncogenicity import annotate as annotate_legacy_oncogenicity, is_high_risk as is_legacy_high_risk
from .legacy_mtb_report import generate as generate_legacy_mtb_report
from .mtb_report import cached as cached_mtb_report, generate as generate_mtb_report, save_edits as save_mtb_report_edits
from .variant_display import tumor_format_rows

SUFFIXES={'snv':('.vcf.gz','.vcf.bgz'),'sv':('.vcf.gz','.vcf.bgz'),'cnv':('.vcf.gz','.vcf.bgz'),'callable':('.bed','.bed.gz','.zip')}
def body(request):
    try:return json.loads(request.body or '{}')
    except json.JSONDecodeError:raise ValueError('Invalid JSON body')
def error(detail,status=400):return JsonResponse({'detail':str(detail)},status=status)

@csrf_exempt
def subject(request):
    if request.method!='POST':return error('POST required',405)
    try:
        data=body(request); sample=str(data.get('subject_id','')).strip()
        if not sample or len(sample)>80:raise ValueError('Subject ID is required and must be at most 80 characters')
        draft=new_id('draft'); directory=draft_dir(draft); directory.mkdir(parents=True)
        metadata={'draft_id':draft,'created_at':datetime.now(timezone.utc).isoformat(),'subject':{'subject_id':sample,'dob':str(data.get('dob',''))[:20],'gender':str(data.get('gender','unknown'))[:20],'history':str(data.get('history',''))[:10000],'user_id':str(data.get('user_id') or 'N/A')[:100],'protocol':'WGS Somatic Tumor-Only','genome_build':'GRCh38'}}
        write_json(directory/'metadata.json',metadata); return JsonResponse({'draft_id':draft},status=201)
    except ValueError as exc:return error(exc)

@csrf_exempt
def upload(request):
    if request.method!='POST':return error('POST required',405)
    try:
        draft=validate_id(request.POST.get('draft_id',''),'draft'); directory=draft_dir(draft); metadata=read_json(directory/'metadata.json')
        if not metadata:return error('Draft not found',404)
        upload_id=new_id('upload'); files={}
        for kind,suffixes in SUFFIXES.items():
            item=request.FILES.get(kind)
            if not item:
                if kind=='snv':raise ValueError('SNV/Indel must be a non-empty .vcf.gz or .vcf.bgz')
                continue
            if not item.name.lower().endswith(suffixes) or item.size<=0:raise ValueError(f'{kind.upper()} has an unsupported or empty file')
            name=f'{kind}{next(s for s in suffixes if item.name.lower().endswith(s))}'; save_upload(item,directory/'uploads'/upload_id/name); files[kind]=name
        metadata.update({'upload_id':upload_id,'files':files}); write_json(directory/'metadata.json',metadata); return JsonResponse({'upload_id':upload_id},status=201)
    except ValueError as exc:return error(exc)

@csrf_exempt
def jobs(request):
    if request.method!='POST':return error('POST required',405)
    try:
        data=body(request); draft=validate_id(data.get('draft_id',''),'draft'); upload_id=validate_id(data.get('upload_id',''),'upload'); source=draft_dir(draft); metadata=read_json(source/'metadata.json')
        if not metadata or metadata.get('upload_id')!=upload_id:return error('Upload session not found',404)
        settings={'pass_only':bool(data.get('pass_only',True)),'min_dp':max(0,int(data.get('min_dp',20))),'min_alt_reads':max(0,int(data.get('min_alt_reads',5))),'min_vaf':min(max(float(data.get('min_vaf',.05)),0),1),'population_af_max':min(max(float(data.get('population_af_max',.01)),0),1),'cancer_type':str(data.get('cancer_type',''))[:200]}
        job=new_id('somwgs'); destination=job_dir(job); destination.mkdir(parents=True); shutil.move(str(source/'uploads'/upload_id),str(destination/'inputs'))
        metadata.update({'analysis_id':job,'status':'starting','settings':settings,'started_at':datetime.now(timezone.utc).isoformat()}); write_json(destination/'metadata.json',metadata)
        s=metadata['subject']; record=existJobs.jobs.create(jobID=job,subject_id=s['subject_id'],name='WGS Somatic Tumor-Only',dob=s['dob'],gender=s['gender'],history=s['history'],uploadFile_url=str(destination/'inputs'),resultFile_url=str(destination/'pipeline.finished'),user_id=s['user_id'],genome_build='hg38',status='running')
        try: pid=launch(job,metadata)
        except Exception:
            # Make a failed launch retryable: restore the uploaded files to the
            # draft and remove the half-created job/database record.
            restored=source/'uploads'/upload_id; restored.parent.mkdir(parents=True,exist_ok=True)
            if (destination/'inputs').exists() and not restored.exists(): shutil.move(str(destination/'inputs'),str(restored))
            record.delete(); shutil.rmtree(destination,ignore_errors=True); raise
        record.processID=str(pid);record.save(update_fields=['processID']);metadata.update({'status':'running','process_id':pid});write_json(destination/'metadata.json',metadata);shutil.rmtree(source,ignore_errors=True)
        return JsonResponse({'analysis_id':job,'status':'running'},status=202)
    except (ValueError,TypeError) as exc:return error(exc)
    except Exception as exc:return error(f'Unable to start WGS somatic pipeline: {exc}',500)

def metadata_for(job):
    try: directory=job_dir(job)
    except ValueError:return None,None
    return directory,read_json(directory/'metadata.json')
def job_detail(request,analysis_id):
    directory,metadata=metadata_for(analysis_id)
    if not metadata:return error('Analysis not found',404)
    result=dict(metadata);result['log_available']=(directory/'nextflow.log').exists();result['available_sections']=['high_risk','snv_actionable','oncogenicity_all','hereditary_high_risk','in_silico_candidates']+[kind for kind in ('sv','cnv') if kind in metadata.get('files',{})];return JsonResponse(result)

def results(request,analysis_id):
    directory,metadata=metadata_for(analysis_id)
    if not metadata:return error('Analysis not found',404)
    sample=metadata['subject']['subject_id'];section=request.GET.get('section','snv_actionable')
    paths={'snv_actionable':directory/'results'/sample/'interpretation'/f'{sample}.snv.actionable.tsv','high_risk':directory/'results'/sample/'interpretation'/f'{sample}.snv.reportable.tsv','oncogenicity_all':directory/'results'/sample/'interpretation'/f'{sample}.snv.all.tsv','hereditary_high_risk':directory/'results'/sample/'interpretation'/'hereditary_high_risk.tsv','in_silico_candidates':directory/'results'/sample/'interpretation'/'in_silico_candidates.tsv','sv':directory/'results'/sample/'sv'/f'{sample}.sv.all.tsv','cnv':directory/'results'/sample/'cnv'/f'{sample}.cnv.all.tsv'}
    if section not in paths:return error('Unsupported result section')
    if section in ('sv','cnv') and section not in metadata.get('files',{}):return error(f'{section.upper()} was not supplied for this analysis',404)
    rows=tsv_rows(paths[section])
    if section not in ('sv','cnv'):rows=tumor_format_rows(directory,sample,rows)
    return JsonResponse({'status':metadata['status'],'results':rows})
def summary(request,analysis_id):
    directory,metadata=metadata_for(analysis_id)
    if not metadata:return error('Analysis not found',404)
    sample=metadata['subject']['subject_id'];return JsonResponse(read_json(directory/'results'/sample/'pipeline_complete.json',{'status':metadata['status']}))

def downstream(request,analysis_id):
    directory,metadata=metadata_for(analysis_id)
    if not metadata:return error('Analysis not found',404)
    sample=metadata['subject']['subject_id']; root=directory/'results'/sample/'downstream'
    def table(name,delimiter=',',limit=100):
        path=root/name
        if not path.is_file():return {'available':False,'rows':[]}
        with path.open(errors='replace',newline='') as handle:
            rows=[]
            for row in csv.DictReader(handle,delimiter=delimiter):
                rows.append(row)
                if len(rows)>=limit:break
        return {'available':True,'rows':rows,'file':name}
    manifest=read_json(root/'summary.json',{})
    tmb=read_json(root/f'{sample}.tmb_proxy.json',{})
    descriptions={}
    description_path=Path('/home/hpz8g5/project/MTB/database/VEP/20241126Mondodatabase/aetiology_map.tsv')
    if description_path.is_file():
        with description_path.open(errors='replace',newline='') as handle:
            descriptions={row.get('signature',''):row.get('aetiology','') for row in csv.DictReader(handle,delimiter='\t')}
    top=manifest.get('top_mutational_signatures',[]); total=sum(float(x.get('activity',0) or 0) for x in top)
    signature_activities=[{**item,'proportion':(float(item.get('activity',0) or 0)/total if total else 0),'description':descriptions.get(item.get('signature',''),'')} for item in top]
    def encoded(name):
        path=root/name
        return base64.b64encode(path.read_bytes()).decode('ascii') if path.is_file() else ''
    return JsonResponse({
        'status':'ready' if root.is_dir() else 'not_available',
        'manifest':manifest,
        'mutation_signature':table('mutation_signature.activities.tsv','\t'),
        'signature_activities':signature_activities,
        'signature_plot_pdf_base64':encoded('mutation_signature.sbs96.pdf'),
        'signature_activity_pdf_base64':encoded('mutation_signature.activities.pdf'),
        'signature_pie_pdf_base64':encoded('mutation_signature.pie.pdf'),
        'cancer_prediction_pdf_base64':encoded('cancer_type_prediction.pdf'),
        'tmb_estimate':tmb,
        'tmb_variants':table(f'{sample}.tmb_proxy_variants.tsv','\t'),
        'cancer_type_prediction':table('cancer_type_prediction.csv'),
        'pathway':table('pathway.results.csv'),
    })

@csrf_exempt
def mtb_report(request,analysis_id):
    directory,metadata=metadata_for(analysis_id)
    if not metadata:return error('Analysis not found',404)
    if request.method=='GET':return JsonResponse(cached_mtb_report(directory,metadata))
    if request.method=='PUT':
        try:return JsonResponse(save_mtb_report_edits(directory,metadata,body(request).get('narrative')))
        except ValueError as exc:return error(exc)
        except Exception as exc:return error(f'Unable to save MTB draft edits: {exc}',500)
    if request.method!='POST':return error('GET, POST, or PUT required',405)
    if metadata.get('status')!='finished':return error('The analysis must finish before an MTB draft can be generated',409)
    try:
        refresh=bool(body(request).get('refresh',False));return JsonResponse(generate_mtb_report(directory,metadata,refresh=refresh))
    except Exception as exc:return error(f'Unable to generate MTB draft: {exc}',500)

@csrf_exempt
def legacy_oncogenicity(request):
    if request.method!='POST':return error('POST required',405)
    try:
        job=str(body(request).get('newjobid','')).strip()
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',job):raise ValueError('Invalid legacy job identifier')
        directory=Path(os.environ.get('LEGACY_PATIENT_ROOT','/miRTI/media/patient'))/job
        merged=sorted(directory.glob('*_main_vep_annovar_merge.csv'))
        source=merged[0] if merged else directory/'somatic_result.csv'
        if not source.is_file():return error('Legacy somatic result not found',404)
        output=directory/'legacy_candidates.oncogenicity.tsv';summary_path=directory/'legacy_candidates.oncogenicity.summary.json'
        if not output.exists() or output.stat().st_mtime < source.stat().st_mtime:
            rows,summary_data=annotate_legacy_oncogenicity(source,output,summary_path)
        else:
            rows=tsv_rows(output);summary_data=read_json(summary_path,{})
        high_risk=[row for row in rows if is_legacy_high_risk(row)]
        summary_data={**summary_data,'high_risk':len(high_risk),'reporting_gate':'non-synonymous AND (ClinVar P/LP OR oncogenicity O/LO)','quality_filter':'unchanged legacy pipeline output'}
        return JsonResponse({'status':'success','data':high_risk,'summary':summary_data})
    except ValueError as exc:return error(exc)
    except Exception as exc:return error(f'Unable to calculate legacy oncogenicity: {exc}',500)

def legacy_mtb_report(request,analysis_id):
    if request.method!='GET':return error('GET required',405)
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',analysis_id):return error('Invalid legacy job identifier')
    directory=Path(os.environ.get('LEGACY_PATIENT_ROOT','/miRTI/media/patient'))/analysis_id
    if not directory.is_dir():return error('Legacy tumor-only result not found',404)
    try:return JsonResponse(generate_legacy_mtb_report(directory))
    except FileNotFoundError as exc:return error(exc,404)
    except Exception as exc:return error(f'Unable to generate legacy MTB draft: {exc}',500)
