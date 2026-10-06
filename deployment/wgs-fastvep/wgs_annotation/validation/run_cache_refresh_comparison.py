#!/usr/bin/env python3
"""Refresh cache fields and compare a previously prepared WGS benchmark run."""
import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['baseline-run', 'output-dir', 'project-root', 'reference', 'variation-cache', 'variation-index']:
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--image', default='mtb-wgs-fastvep:0.1.3')
    parser.add_argument('--jobs', type=int, default=8)
    args = parser.parse_args()
    baseline, root = Path(args.baseline_run), Path(args.output_dir)
    source = Path(__file__).resolve().parent
    manifest = json.loads((baseline/'inputs.json').read_text())
    root.mkdir(parents=True, exist_ok=True)
    (root/'inputs.json').write_text(json.dumps(manifest, indent=2)+'\n')
    tasks = []
    for item in manifest:
        sample = item['sample']
        job = Path(item['job'])
        cohort = job/'results'/sample/('candidates' if item['mode']=='germline' else 'oncogenicity')/(sample+('.all_candidates.tsv' if item['mode']=='germline' else '.oncogenicity.tsv.gz'))
        for shard in item['shards']:
            tasks.append((sample, shard, cohort))

    def execute(task):
        sample, shard, cohort = task
        name = f"{sample}.{shard['shard']}"
        old = baseline/'results'/sample/'annotation/shards'
        target = root/'results'/sample/'annotation/shards'
        target.mkdir(parents=True, exist_ok=True)
        summary = target/(name+'.annotation.summary.json')
        log = root/'logs'/name
        log.parent.mkdir(exist_ok=True)
        if not summary.exists():
            command = ['docker','run','--rm','--network','none','-u','1000:1000',
                       '-v', args.project_root+':'+args.project_root, args.image,
                       'python',str(source/'refresh_variation_annotations.py'),
                       '--input',str(old/(name+'.vep.tsv.gz')),
                       '--input-summary',str(old/(name+'.annotation.summary.json')),
                       '--output',str(target/(name+'.vep.tsv.gz')),'--summary',str(summary),
                       '--variation-cache',args.variation_cache,'--reference',args.reference,
                       '--variation-index',args.variation_index]
            with Path(str(log)+'.refresh.log').open('w') as handle:
                subprocess.run(command,stdout=handle,stderr=subprocess.STDOUT,check=True)
        prefix = root/'comparison'/sample/shard['shard']
        prefix.parent.mkdir(parents=True, exist_ok=True)
        if not prefix.with_suffix('.json').exists():
            with Path(str(log)+'.compare.log').open('w') as handle:
                subprocess.run([sys.executable,str(source/'compare_annotations.py'),
                                '--baseline',shard['baseline'],'--fastvep',str(target/(name+'.vep.tsv.gz')),
                                '--output-prefix',str(prefix),'--cohort',str(cohort)],
                               stdout=handle,stderr=subprocess.STDOUT,check=True)
        print('Refreshed and compared',name,flush=True)

    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        for future in as_completed([pool.submit(execute,t) for t in tasks]):
            future.result()
    (root/'ANNOTATION_COMPLETE.json').write_text(json.dumps({'successful':len(tasks),'failed':0,'cache_refresh':True})+'\n')


if __name__ == '__main__':
    main()
