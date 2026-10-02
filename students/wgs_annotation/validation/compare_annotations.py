#!/usr/bin/env python3
"""Bounded-memory comparison of paired VEP/fastVEP annotation shards.

Variant identity is normalized from Uploaded_variation so VCF anchors do not
create false insertion/deletion mismatches. Raw field differences remain visible.
Outputs may contain patient information; keep them outside the source repository.
"""
import argparse
import csv
import gzip
import itertools
import json
import math
import re
from collections import Counter, defaultdict, deque
from pathlib import Path

FIELDS = ['Consequence', 'IMPACT', 'SYMBOL', 'BIOTYPE', 'HGVSc', 'HGVSp',
          'HGVSg', 'MANE_SELECT', 'CANONICAL', 'PICK', 'CLIN_SIG', 'ZYG',
          'gnomADe_AF', 'gnomADg_AF', 'gnomADe_EAS_AF', 'gnomADg_EAS_AF',
          'CADD_phred', 'REVEL_score', 'ClinPred_score', 'SIFT', 'PolyPhen',
          'am_pathogenicity', 'PrimateAI', 'SpliceAI_pred', 'SpliceAI_cutoff']
SETS = {'Consequence', 'CLIN_SIG'}
NUMERIC = {f for f in FIELDS if f.endswith('_AF')} | {
    'CADD_phred', 'REVEL_score', 'ClinPred_score', 'am_pathogenicity', 'PrimateAI'}
CODING = {'missense_variant', 'stop_gained', 'stop_lost', 'start_lost',
          'frameshift_variant', 'inframe_deletion', 'inframe_insertion',
          'splice_acceptor_variant', 'splice_donor_variant',
          'protein_altering_variant', 'transcript_ablation'}


def clean(value):
    value = str(value or '').strip()
    return '' if value in ('-', '.', 'None', 'nan') else value


def variant_key(row):
    text = row.get('#Uploaded_variation', row.get('Uploaded_variation', ''))
    chrom, pos, alleles = text.rsplit('_', 2)
    ref, alt = alleles.split('/', 1)
    pos = int(pos)
    ref, alt = ref.replace('-', ''), alt.replace('-', '')
    while ref and alt and ref[-1] == alt[-1]:
        ref, alt = ref[:-1], alt[:-1]
    while ref and alt and ref[0] == alt[0]:
        pos += 1
        ref, alt = ref[1:], alt[1:]
    chrom = chrom.removeprefix('chr')
    return chrom, pos, ref or '-', alt or '-'


def reader(path):
    with gzip.open(path, 'rt') if str(path).endswith('.gz') else open(path) as f:
        yield from csv.DictReader((line for line in f if not line.startswith('##')), delimiter='\t')


def groups(path):
    for key, rows in itertools.groupby(reader(path), key=variant_key):
        yield key, list(rows)


def align(left, right, window=64):
    """Allow missing variants or bounded local order changes without a huge index."""
    a, b = deque(), deque()
    left, right = iter(left), iter(right)
    exhausted = [False, False]
    while True:
        for queue, source, side in ((a, left, 0), (b, right, 1)):
            while len(queue) < window and not exhausted[side]:
                item = next(source, None)
                if item is None:
                    exhausted[side] = True
                else:
                    queue.append(item)
        if not a and not b:
            return
        if not a:
            key, rows = b.popleft(); yield key, [], rows; continue
        if not b:
            key, rows = a.popleft(); yield key, rows, []; continue
        if a[0][0] == b[0][0]:
            key, old = a.popleft(); _, new = b.popleft(); yield key, old, new
            continue
        match = next((i for i, item in enumerate(b) if item[0] == a[0][0]), None)
        if match is not None:
            key, old = a.popleft(); _, new = b[match]; del b[match]
            yield key, old, new
        else:
            # Otherwise a novel fastVEP record can pin the right window forever.
            # Both files follow the same input chromosome/position ordering.
            def order(key):
                chrom, pos, ref, alt = key
                rank = int(chrom) if chrom.isdigit() else {'X': 23, 'Y': 24, 'MT': 25}.get(chrom, 26)
                return rank, chrom if rank == 26 else '', pos, ref, alt
            if order(a[0][0]) <= order(b[0][0]):
                key, old = a.popleft(); yield key, old, []
            else:
                key, new = b.popleft(); yield key, [], new


def equivalent(field, old, new):
    old, new = clean(old), clean(new)
    if old == new:
        return True
    if field in SETS:
        return set(re.split('[,&|]', old)) == set(re.split('[,&|]', new))
    if field in NUMERIC and old and new:
        try:
            a = sorted(float(x) for x in re.split('[,;&|]', old))
            b = sorted(float(x) for x in re.split('[,;&|]', new))
            return len(a) == len(b) and all(math.isclose(x, y, rel_tol=1e-6, abs_tol=1e-9) for x, y in zip(a, b))
        except ValueError:
            pass
    return False


def hgvs_reference_version_only(old, new):
    old, new = clean(old), clean(new)
    if not old or not new or old == new:
        return False
    normalize = lambda v: re.sub(r'^(ENS[TP]\d+)\.\d+(?=:)', r'\1', v.replace(' ', ''))
    return normalize(old) == normalize(new)


def row_key(row):
    return tuple(clean(row.get(f)) for f in ('Gene', 'Feature_type', 'Feature'))


def chosen(rows):
    return max(rows, key=lambda r: (clean(r.get('PICK')) == '1',
               bool(clean(r.get('MANE_SELECT'))), clean(r.get('CANONICAL')) == 'YES',
               bool(clean(r.get('SYMBOL'))), bool(clean(r.get('HGVSp'))))) if rows else None


def run(args):
    prefix = Path(args.output_prefix); prefix.parent.mkdir(parents=True, exist_ok=True)
    cohort = {variant_key(r) for r in reader(args.cohort)} if args.cohort else set()
    counts, types_old, types_new = Counter(), Counter(), Counter()
    field_stats = {f: Counter() for f in FIELDS}
    selected_stats = {f: Counter() for f in FIELDS}
    mismatch_examples = []
    handles = [gzip.open(str(prefix) + f'.{side}.cohort.tsv.gz', 'wt') for side in ('vep', 'fastvep')]
    writers = [None, None]
    coding_handles = [gzip.open(str(prefix) + f'.{side}.coding_union.tsv.gz', 'wt') for side in ('vep', 'fastvep')]
    coding_writers = [None, None]
    try:
        for key, old_rows, new_rows in align(groups(args.baseline), groups(args.fastvep)):
            counts['vep_variants'] += bool(old_rows); counts['fastvep_variants'] += bool(new_rows)
            counts['vep_rows'] += len(old_rows); counts['fastvep_rows'] += len(new_rows)
            for side, rows, types in (('vep', old_rows, types_old), ('fastvep', new_rows, types_new)):
                for row in rows:
                    types[clean(row.get('Feature_type')) or 'intergenic'] += 1
                    for f in FIELDS:
                        field_stats[f][side + '_nonmissing'] += bool(clean(row.get(f)))
            if not old_rows or not new_rows:
                counts['vep_only_variants' if old_rows else 'fastvep_only_variants'] += 1
                if len(mismatch_examples) < 20:
                    mismatch_examples.append({'variant': key, 'reason': 'variant_missing', 'side': 'vep' if old_rows else 'fastvep'})
                continue
            counts['matched_variants'] += 1
            old_map, new_map = defaultdict(list), defaultdict(list)
            for row in old_rows: old_map[row_key(row)].append(row)
            for row in new_rows: new_map[row_key(row)].append(row)
            for transcript in old_map.keys() | new_map.keys():
                a, b = old_map[transcript], new_map[transcript]
                counts['vep_only_rows'] += max(0, len(a) - len(b))
                counts['fastvep_only_rows'] += max(0, len(b) - len(a))
                for old, new in zip(a, b):
                    counts['matched_rows'] += 1
                    for f in FIELDS:
                        stats = field_stats[f]; x, y = clean(old.get(f)), clean(new.get(f))
                        stats['compared'] += 1
                        stats['both_nonmissing'] += bool(x and y)
                        stats['lost_value'] += bool(x and not y)
                        stats['gained_value'] += bool(y and not x)
                        stats['equivalent' if equivalent(f, x, y) else 'different'] += 1
                        if f in ('HGVSc', 'HGVSp'):
                            stats['reference_version_only'] += hgvs_reference_version_only(x, y)
            # PICK must be compared per gene, as in flag_pick_allele_gene.
            old_pick = {clean(r.get('Gene')): clean(r.get('Feature')) for r in old_rows if clean(r.get('PICK')) == '1' and clean(r.get('Gene'))}
            new_pick = {clean(r.get('Gene')): clean(r.get('Feature')) for r in new_rows if clean(r.get('PICK')) == '1' and clean(r.get('Gene'))}
            for gene in old_pick.keys() | new_pick.keys():
                counts['pick_gene_pairs'] += 1
                counts['pick_same' if old_pick.get(gene) == new_pick.get(gene) else 'pick_different'] += 1
            old, new = chosen(old_rows), chosen(new_rows)
            coding = key in cohort or any(set(re.split('[,&]', r.get('Consequence', ''))) & CODING
                                         for r in old_rows + new_rows)
            if coding:
                counts['coding_union_variants'] += 1
                for i, row in enumerate((old, new)):
                    if coding_writers[i] is None:
                        coding_writers[i] = csv.DictWriter(coding_handles[i], fieldnames=list(row), delimiter='\t')
                        coding_writers[i].writeheader()
                    coding_writers[i].writerow(row)
            for f in FIELDS:
                selected_stats[f]['compared'] += 1
                selected_stats[f]['equivalent' if equivalent(f, old.get(f), new.get(f)) else 'different'] += 1
                if f in ('HGVSc', 'HGVSp'):
                    selected_stats[f]['reference_version_only'] += hgvs_reference_version_only(old.get(f), new.get(f))
            if key in cohort:
                counts['cohort_matched_variants'] += 1
                for i, row in enumerate((old, new)):
                    if writers[i] is None:
                        writers[i] = csv.DictWriter(handles[i], fieldnames=list(row), delimiter='\t')
                        writers[i].writeheader()
                    writers[i].writerow(row)
                changed = [f for f in FIELDS if not equivalent(f, old.get(f), new.get(f))]
                if changed and len(mismatch_examples) < 20:
                    mismatch_examples.append({'variant': key, 'reason': 'cohort_selected_fields', 'fields': changed})
    finally:
        for f in handles + coding_handles: f.close()
    report = {'baseline': str(args.baseline), 'fastvep': str(args.fastvep),
              'variant_identity': 'minimal forward-strand Uploaded_variation alleles',
              'counts': dict(counts), 'baseline_feature_types': dict(types_old),
              'fastvep_feature_types': dict(types_new), 'matched_transcript_fields': field_stats,
              'selected_variant_fields': selected_stats, 'original_cohort_size': len(cohort),
              'examples': mismatch_examples,
              'numeric_tolerance': {'relative': 1e-6, 'absolute': 1e-9}}
    Path(str(prefix) + '.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'output': str(prefix), 'counts': counts}))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--baseline', required=True); p.add_argument('--fastvep', required=True)
    p.add_argument('--output-prefix', required=True); p.add_argument('--cohort')
    run(p.parse_args())
