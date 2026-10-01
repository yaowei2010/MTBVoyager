import os,sys,time
from pathlib import Path
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','uploadfunction.settings'); django.setup()
from hw1.models import existJobs
from .storage import job_dir,read_json,write_json
def alive(pid):
    try: return Path(f'/proc/{pid}/stat').read_text().split()[2] != 'Z'
    except (OSError,ValueError,IndexError): return False
def main():
    job,pid=sys.argv[1],int(sys.argv[2])
    while alive(pid): time.sleep(10)
    directory=job_dir(job); metadata=read_json(directory/'metadata.json',{}); sample=metadata.get('subject',{}).get('subject_id','')
    success=(directory/'results'/sample/'pipeline_complete.json').exists(); metadata['status']='finished' if success else 'failed'; write_json(directory/'metadata.json',metadata)
    marker=directory/'pipeline.finished'
    if success: marker.touch()
    existJobs.jobs.filter(jobID=job).update(status=metadata['status'],resultFile_url=str(marker) if success else '')
if __name__=='__main__': main()
