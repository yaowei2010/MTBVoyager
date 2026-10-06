#!/usr/bin/env python3
"""Refresh cache fields and compare a previously prepared WGS benchmark run."""
import argparse
import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


def completed_refresh(summary, output, index):
    try:
        data = json.loads(summary.read_text())
        return (output.is_file() and data.get('status') == 'complete'
                and data.get('adapter_version') == '0.1.3'
                and 'cache_refresh_audit' in data
                and data.get('sources', {}).get('normalized_variation_index') == str(index))
    except (OSError, ValueError, TypeError, AttributeError):
        return False


def completed_comparison(report, baseline, output):
    try:
        data = json.loads(report.read_text())
        return (report.stat().st_mtime_ns >= output.stat().st_mtime_ns
                and data.get('baseline') == str(baseline)
                and data.get('fastvep') == str(output)
                and 'counts' in data and 'selected_variant_fields' in data)
    except (OSError, ValueError, TypeError, AttributeError):
        return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['baseline-run', 'output-dir', 'project-root', 'reference', 'variation-cache', 'variation-index']:
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--image', default='mtb-wgs-fastvep:0.1.3')
    parser.add_argument('--jobs', type=int, default=8)
    parser.add_argument("--primary-only", action="store_true")
    parser.add_argument("--wait-for-index", action="store_true")
    parser.add_argument("--index-build-container", default="mtb-fastvep-variation-index")
    args = parser.parse_args()
    baseline, root = Path(args.baseline_run), Path(args.output_dir)
    source = Path(__file__).resolve().parent
    manifest = json.loads((baseline/'inputs.json').read_text())
    if args.primary_only:
        for item in manifest:
            item['shards'] = [s for s in item['shards'] if s['shard'] != 'other']
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
        output = target/(name+".vep.tsv.gz")
        refreshed = not completed_refresh(summary, output, Path(args.variation_index))
        if refreshed:
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
        if refreshed or not completed_comparison(prefix.with_suffix('.json'), Path(shard['baseline']), output):
            with Path(str(log)+'.compare.log').open('w') as handle:
                subprocess.run([sys.executable,str(source/'compare_annotations.py'),
                                '--baseline',shard['baseline'],'--fastvep',str(target/(name+'.vep.tsv.gz')),
                                '--output-prefix',str(prefix),'--cohort',str(cohort)],
                               stdout=handle,stderr=subprocess.STDOUT,check=True)
        print('Refreshed and compared',name,flush=True)

    pending = tasks[:]
    running = {}
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        while pending or running:
            for future in list(running):
                if future.done():
                    future.result()
                    del running[future]
            for task in pending[:]:
                if len(running) >= args.jobs:
                    break
                chrom = task[1]['shard'].removeprefix('chr')
                chrom = 'MT' if chrom == 'M' else chrom
                ready = chrom == 'other' or (Path(args.variation_index)/(chrom+'.sqlite')).is_file()
                if not ready and args.wait_for_index:
                    continue
                if not ready:
                    raise RuntimeError('Missing normalized variation index: '+chrom)
                pending.remove(task)
                running[pool.submit(execute,task)] = task
            if pending and args.wait_for_index:
                build = subprocess.run(['docker','inspect',args.index_build_container],
                                       stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                if build.returncode and not running:
                    raise RuntimeError('Index build stopped with missing required indexes')
            if pending or running:
                time.sleep(10)
    (root/'ANNOTATION_COMPLETE.json').write_text(json.dumps({'successful':len(tasks),'failed':0,'cache_refresh':True,'scope':'primary_only' if args.primary_only else 'all_shards'})+'\n')


if __name__ == '__main__':
    main()
