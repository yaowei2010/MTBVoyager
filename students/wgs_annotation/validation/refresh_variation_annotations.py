#!/usr/bin/env python3
"""Recompute cache-derived fields while retaining existing fastVEP/plugin rows."""
import argparse
import csv
import gzip
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastvep_to_mtb import VariationCache, AF_FIELDS, clean, ADAPTER_VERSION

CACHE_FIELDS = ['Existing_variation', 'CLIN_SIG', 'SOMATIC', 'PHENO', 'PUBMED', 'AF'] + AF_FIELDS


def refresh(args):
    source = VariationCache(args.variation_cache, args.reference, args.variation_index)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.name + '.partial')
    counts, audit = Counter(), {field: Counter() for field in CACHE_FIELDS}
    summary = json.loads(Path(args.input_summary).read_text()) if args.input_summary else {}
    nonmissing_delta = Counter()
    last = None
    try:
        with gzip.open(args.input, 'rt') as original, gzip.open(temporary, 'wt', newline='') as target:
            target.write('## annotation_engine=fastvep\n## adapter_version=' + ADAPTER_VERSION + '\n')
            target.write('## variation_matching=reference-normalized-cache-index-v1\n')
            reader = csv.DictReader((line for line in original if not line.startswith('##')), delimiter='\t')
            assert set(CACHE_FIELDS + ['REF', 'ALT', 'ANNOTATION_DATA_STATUS', '#Uploaded_variation']) <= set(reader.fieldnames)
            writer = csv.DictWriter(target, fieldnames=reader.fieldnames, delimiter='\t', lineterminator='\n')
            writer.writeheader()
            for row in reader:
                key = row['#Uploaded_variation']
                if key != last:
                    chrom, pos, pair = key.rsplit('_', 2)
                    assert pair == row['REF'] + '/' + row['ALT'], key
                    v = dict(chrom=chrom, pos=int(pos), ref=row['REF'], alt=row['ALT'])
                    values = source.annotate(v)
                    status = ('variation_cache_unavailable_contig' if chrom in source.unavailable_contigs else 'sources_loaded')
                    counts['variants'] += 1
                    for field in CACHE_FIELDS:
                        old, new = clean(row[field]), clean(values.get(field))
                        audit[field]['compared'] += 1
                        audit[field]['old_nonmissing'] += bool(old)
                        audit[field]['new_nonmissing'] += bool(new)
                        audit[field]['lost'] += bool(old and not new)
                        audit[field]['gained'] += bool(new and not old)
                        audit[field]['different'] += old != new
                    last = key
                for field in CACHE_FIELDS:
                    value = values.get(field) or '-'
                    nonmissing_delta[field] += bool(clean(value)) - bool(clean(row[field]))
                    row[field] = value
                row['ANNOTATION_DATA_STATUS'] = status
                writer.writerow(row)
                counts['transcript_rows'] += 1
        assert not summary.get("counts") or summary["counts"] == dict(counts), "Variant/row counts changed during cache refresh"
        temporary.replace(output)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    if 'nonmissing_rows' in summary:
        for field, delta in nonmissing_delta.items():
            summary['nonmissing_rows'][field] = summary['nonmissing_rows'].get(field, 0) + delta
    summary.update({'status': 'complete', 'adapter_version': ADAPTER_VERSION, 'counts': dict(counts),
                    'variation_matching': 'reference-checked minimal alleles and repeat-left-aligned indels',
                    'variation_cache_unavailable_contigs': dict(source.unavailable_contigs),
                    'cache_refresh_audit': audit,
                    'cache_refresh_scope': 'cache fields only; fastVEP consequences and plugin values retained'})
    summary.setdefault('sources', {})['normalized_variation_index'] = str(source.index)
    summary_path = Path(args.summary)
    temporary_summary = summary_path.with_name(summary_path.name + '.partial')
    temporary_summary.write_text(json.dumps(summary, indent=2) + '\n')
    temporary_summary.replace(summary_path)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['input', 'output', 'summary', 'variation-cache', 'reference', 'variation-index']:
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--input-summary')
    print(json.dumps(refresh(parser.parse_args())['counts']), flush=True)
