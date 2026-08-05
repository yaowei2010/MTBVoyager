import csv, json, os, re, shutil, uuid
from pathlib import Path

SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{8,64}$")

def root():
    path=Path(os.environ.get('WGS_SOMATIC_DATA_ROOT','/miRTI/media/wgs_somatic')).resolve(); path.mkdir(parents=True,exist_ok=True); return path
def new_id(prefix): return f"{prefix}_{uuid.uuid4().hex[:16]}"
def validate_id(value,prefix=None):
    if not value or not SAFE_ID.fullmatch(value) or (prefix and not value.startswith(prefix+'_')): raise ValueError('Invalid identifier')
    return value
def draft_dir(value): return root()/'drafts'/validate_id(value,'draft')
def job_dir(value): return root()/'jobs'/validate_id(value,'somwgs')
def read_json(path,default=None):
    try: return json.loads(Path(path).read_text())
    except (FileNotFoundError,json.JSONDecodeError): return default
def write_json(path,value):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True); tmp=path.with_suffix(path.suffix+'.tmp'); tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n'); os.replace(tmp,path)
def save_upload(upload,destination):
    destination=Path(destination); destination.parent.mkdir(parents=True,exist_ok=True)
    with destination.open('wb') as h:
        for chunk in upload.chunks(): h.write(chunk)
def install_pipeline():
    source=Path(os.environ.get('WGS_SOMATIC_PIPELINE_SOURCE','/opt/wgs-somatic-pipeline'))
    version=(source/'VERSION').read_text().strip(); destination=root()/'pipeline'/version
    if not destination.exists():
        tmp=destination.with_name(destination.name+'.tmp'); shutil.rmtree(tmp,ignore_errors=True)
        ignored=shutil.ignore_patterns('work','results','test-results*','.nextflow*','.pytest_cache','report-*','timeline-*','trace-*','dag-*','__pycache__','*.pyc')
        shutil.copytree(source,tmp,ignore=ignored); os.replace(tmp,destination)
    return destination
def tsv_rows(path,limit=10000):
    if not Path(path).exists(): return []
    with Path(path).open(encoding='utf-8',errors='replace',newline='') as h: return list(csv.DictReader(h,delimiter='\t'))[:limit]
