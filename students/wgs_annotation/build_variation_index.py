#!/usr/bin/env python3
"""Build atomic, read-only lookup indexes from the existing VEP 112 cache."""
import argparse
import json
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from variation_index import build_chromosome, reference_identity


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--variation-cache', required=True)
    parser.add_argument('--reference', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--chromosomes', help='Comma-separated cache names; default all cache contigs')
    parser.add_argument('--workers', type=int, default=4)
    args = parser.parse_args()
    cache, output = Path(args.variation_cache), Path(args.output)
    chromosomes = args.chromosomes.split(',') if args.chromosomes else sorted(
        p.name for p in cache.iterdir() if p.is_dir() and any(p.glob('*_var.gz')))
    results = []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(build_chromosome, cache, args.reference, output, chrom) for chrom in chromosomes]
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            print(result['chromosome'], result['status'], result.get('counts', {}), flush=True)
    manifest = {'reference': reference_identity(args.reference), 'chromosomes': results}
    output.mkdir(parents=True, exist_ok=True)
    temporary = output / 'manifest.json.partial'
    temporary.write_text(json.dumps(manifest, indent=2) + '\n')
    temporary.replace(output / 'manifest.json')


if __name__ == '__main__':
    main()
