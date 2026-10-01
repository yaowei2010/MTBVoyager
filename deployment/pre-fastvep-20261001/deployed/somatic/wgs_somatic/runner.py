import csv, os, subprocess, sys
from .storage import install_pipeline, job_dir

def launch(job_id,metadata):
    directory=job_dir(job_id); pipeline=install_pipeline(); inputs=directory/'inputs'; output=directory/'results'; work=directory/'work'
    output.mkdir(parents=True,exist_ok=True); work.mkdir(parents=True,exist_ok=True)
    sheet=directory/'samplesheet.csv'
    with sheet.open('w',newline='') as h:
        w=csv.DictWriter(h,fieldnames=['sample_id','snv_vcf','sv_vcf','cnv_vcf','callable_regions']); w.writeheader()
        files=metadata['files']
        w.writerow({'sample_id':metadata['subject']['subject_id'],'snv_vcf':inputs/files['snv'],'sv_vcf':inputs/files['sv'] if 'sv' in files else '','cnv_vcf':inputs/files['cnv'] if 'cnv' in files else '','callable_regions':inputs/files['callable'] if 'callable' in files else ''})
    settings=metadata['settings']; reference=os.environ.get('WGS_REFERENCE_FASTA','/wgs_reference/hg38.fa')
    cmd=['nextflow','run',str(pipeline/'main.nf'),'-resume','-profile','docker','-work-dir',str(work),'--input',str(sheet),'--outdir',str(output),'--reference',reference,
         '--vep_cache',os.environ.get('WGS_VEP_CACHE','/wgs_reference/vep'),'--vep_plugin_data',os.environ.get('WGS_VEP_PLUGIN_DATA','/wgs_reference/vep/Plugins'),
         '--vep_plugin_args',os.environ.get('WGS_VEP_PLUGIN_ARGS',''),'--vep_max_parallel',os.environ.get('WGS_VEP_MAX_PARALLEL','5'),'--vep_fork_per_shard',os.environ.get('WGS_VEP_FORK_PER_SHARD','6'),
         '--cancer_db',os.environ.get('WGS_CANCER_DB','/VEP/20241126Mondodatabase'),'--annotsv_annotations',os.environ.get('WGS_ANNOTSV_ANNOTATIONS','/annotsv/database/Annotations_Human'),
         '--oncovi_resources',os.environ.get('WGS_ONCOVI_RESOURCES','/oncovi/resources'),
         '--pass_only',str(settings['pass_only']).lower(),'--dp_min',str(settings['min_dp']),'--alt_reads_min',str(settings['min_alt_reads']),'--vaf_min',str(settings['min_vaf']),
         '--population_af_max',str(settings['population_af_max']),'-ansi-log','false']
    gtf=os.environ.get('WGS_GENCODE_GTF','').strip()
    if gtf: cmd.extend(['--gencode_gtf',gtf])
    cancer_type=str(settings.get('cancer_type','')).strip()
    if cancer_type: cmd.extend(['--cancer_type',cancer_type])
    log=(directory/'nextflow.log').open('ab',buffering=0)
    process=subprocess.Popen(cmd,cwd=pipeline,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    subprocess.Popen([sys.executable,'-m','wgs_somatic.monitor',job_id,str(process.pid)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
    return process.pid
