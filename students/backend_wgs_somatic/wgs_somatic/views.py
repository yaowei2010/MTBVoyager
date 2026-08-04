import json,os,re,shutil
from datetime import datetime,timezone
from pathlib import Path
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from hw1.models import existJobs
from .runner import launch
from .storage import draft_dir,job_dir,new_id,read_json,save_upload,tsv_rows,validate_id,write_json
from .legacy_oncogenicity import annotate as annotate_legacy_oncogenicity

SUFFIXES={'snv':('.vcf.gz','.vcf.bgz'),'sv':('.vcf.gz','.vcf.bgz'),'cnv':('.vcf.gz','.vcf.bgz')}
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
            if not item or not item.name.lower().endswith(suffixes) or item.size<=0:raise ValueError(f'{kind.upper()} must be a non-empty .vcf.gz or .vcf.bgz')
            name=f'{kind}.vcf.gz'; save_upload(item,directory/'uploads'/upload_id/name); files[kind]=name
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
    result=dict(metadata);result['log_available']=(directory/'nextflow.log').exists();return JsonResponse(result)
def results(request,analysis_id):
    directory,metadata=metadata_for(analysis_id)
    if not metadata:return error('Analysis not found',404)
    sample=metadata['subject']['subject_id'];section=request.GET.get('section','snv_actionable')
    paths={'snv_all':directory/'results'/sample/'interpretation'/f'{sample}.snv.all.tsv','snv_actionable':directory/'results'/sample/'interpretation'/f'{sample}.snv.actionable.tsv','oncogenicity_all':directory/'results'/sample/'interpretation'/f'{sample}.snv.all.tsv','oncogenicity':directory/'results'/sample/'interpretation'/f'{sample}.snv.oncogenic.tsv','possible_germline':directory/'results'/sample/'interpretation'/f'{sample}.snv.possible_germline.tsv','sv':directory/'results'/sample/'sv'/f'{sample}.sv.all.tsv','cnv':directory/'results'/sample/'cnv'/f'{sample}.cnv.all.tsv'}
    if section not in paths:return error('Unsupported result section')
    return JsonResponse({'status':metadata['status'],'results':tsv_rows(paths[section])})
def summary(request,analysis_id):
    directory,metadata=metadata_for(analysis_id)
    if not metadata:return error('Analysis not found',404)
    sample=metadata['subject']['subject_id'];return JsonResponse(read_json(directory/'results'/sample/'pipeline_complete.json',{'status':metadata['status']}))

@csrf_exempt
def legacy_oncogenicity(request):
    if request.method!='POST':return error('POST required',405)
    try:
        job=str(body(request).get('newjobid','')).strip()
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',job):raise ValueError('Invalid legacy job identifier')
        directory=Path(os.environ.get('LEGACY_PATIENT_ROOT','/miRTI/media/patient'))/job
        source=directory/'somatic_result.csv'
        if not source.is_file():return error('Legacy somatic result not found',404)
        output=directory/'somatic_result.oncogenicity.tsv';summary_path=directory/'somatic_result.oncogenicity.summary.json'
        if not output.exists() or output.stat().st_mtime < source.stat().st_mtime:
            rows,summary_data=annotate_legacy_oncogenicity(source,output,summary_path)
        else:
            rows=tsv_rows(output);summary_data=read_json(summary_path,{})
        return JsonResponse({'status':'success','data':rows,'summary':summary_data})
    except ValueError as exc:return error(exc)
    except Exception as exc:return error(f'Unable to calculate legacy oncogenicity: {exc}',500)
