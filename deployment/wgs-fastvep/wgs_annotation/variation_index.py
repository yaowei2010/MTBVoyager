"""Reference-normalized non-SNV cache index; raw ALT is retained for AF lookup."""
import gzip
import hashlib
import json
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

import pysam

INDEX_VERSION = 1


def aliases(chrom):
    body = chrom.removeprefix('chr')
    body = 'MT' if body in ('M', 'MT') else body
    return [chrom, body, 'chr' + body] + (['M', 'chrM'] if body == 'MT' else [])


def synonyms(cache):
    result = defaultdict(set)
    path = Path(cache) / 'chr_synonyms.txt'
    if path.exists():
        for line in path.read_text().splitlines():
            fields = line.split()
            if len(fields) == 2 and not line.startswith('#'):
                a, b = fields
                result[a].add(b)
                result[b].add(a)
    return result


def candidates(chrom, graph):
    names = aliases(chrom)
    seen = set(names)
    for name in names:
        for other in sorted(graph.get(name, ())):
            if other not in seen:
                names.append(other)
                seen.add(other)
    return names


def reference_identity(path):
    path = Path(path)
    stat = path.stat()
    return {'size': stat.st_size, 'mtime_ns': stat.st_mtime_ns,
            'fai_sha256': hashlib.sha256(Path(str(path) + '.fai').read_bytes()).hexdigest()}


class Normalizer:
    def __init__(self, reference, graph):
        self.fasta = pysam.FastaFile(str(reference))
        self.graph = graph
        self.names = {}
        self.window = None
        self.sequence = ''

    def chromosome(self, chrom):
        if chrom not in self.names:
            self.names[chrom] = next((c for c in candidates(chrom, self.graph)
                                     if c in self.fasta.references), None)
        return self.names[chrom]

    def base(self, chrom, offset):
        # Cache reference windows; homopolymer left shifts can cross any boundary.
        start = offset // 65536 * 65536
        if self.window != (chrom, start):
            self.sequence = self.fasta.fetch(chrom, start, start + 65536).upper()
            self.window = chrom, start
        return self.sequence[offset - start]

    def key(self, chrom, pos, ref, alt):
        chrom = self.chromosome(chrom)
        if chrom is None:
            raise ValueError('Reference has no matching contig')
        ref, alt = ref.replace('-', '').upper(), alt.replace('-', '').upper()
        if not re.fullmatch('[ACGTN]*', ref) or not re.fullmatch('[ACGTN]*', alt):
            raise ValueError('Non-sequence allele')
        if pos < 1 or pos - 1 + len(ref) > self.fasta.get_reference_length(chrom):
            raise ValueError('Allele outside reference bounds')
        if ref and self.fasta.fetch(chrom, pos - 1, pos - 1 + len(ref)).upper() != ref:
            raise ValueError('REF differs from reference')
        while ref and alt and ref[-1] == alt[-1]:
            ref, alt = ref[:-1], alt[:-1]
        while ref and alt and ref[0] == alt[0]:
            pos += 1
            ref, alt = ref[1:], alt[1:]
        if not ref and not alt:
            raise ValueError('Identical REF and ALT')
        if not ref or not alt:
            sequence = ref or alt
            # N is ambiguous; never rotate through an ambiguous reference base.
            while pos > 1 and sequence[-1] != 'N' and self.base(chrom, pos - 2) == sequence[-1]:
                pos -= 1
                sequence = sequence[-1] + sequence[:-1]
            ref, alt = (sequence, '') if ref else ('', sequence)
        return pos, ref or '-', alt or '-'


def build_chromosome(cache, reference, output, chrom):
    cache, output = Path(cache), Path(output)
    output.mkdir(parents=True, exist_ok=True)
    graph = synonyms(cache)
    normalizer = Normalizer(reference, graph)
    if normalizer.chromosome(chrom) is None:
        return {'chromosome': chrom, 'status': 'reference_contig_absent'}
    columns = dict(line.split('\t', 1) for line in (cache / 'info.txt').read_text().splitlines()
                   if '\t' in line and not line.startswith('#'))['variation_cols'].split(',')
    files = sorted((cache / chrom).glob('*_var.gz'), key=lambda p: int(p.name.split('-')[0]))
    metadata = {'index_version': INDEX_VERSION, 'chromosome': chrom,
                'cache_info_sha256': hashlib.sha256((cache / 'info.txt').read_bytes()).hexdigest(),
                'reference': reference_identity(reference),
                'blocks': [[p.name, p.stat().st_size, p.stat().st_mtime_ns] for p in files]}
    target = output / (chrom + '.sqlite')
    if target.exists():
        with sqlite3.connect(target.as_uri() + '?mode=ro', uri=True) as db:
            existing = json.loads(db.execute('select value from metadata').fetchone()[0])
        if all(existing.get(k) == v for k, v in metadata.items()):
            return existing
        raise ValueError(f'Stale index exists: {target}; build in a new directory')
    temporary = target.with_suffix('.sqlite.partial')
    temporary.unlink(missing_ok=True)
    db = sqlite3.connect(temporary)
    db.execute('pragma journal_mode=OFF')
    db.execute('create table records (id integer primary key, raw text not null)')
    db.execute('create table alleles (pos integer, ref text, alt text, record_id integer, allele text)')
    db.execute('create table metadata (value text)')
    counts = Counter()
    positions = {name: columns.index(name) for name in ['failed', 'allele_string', 'strand', 'start']}
    head_size = max(positions.values()) + 1
    try:
        for file in files:
            with gzip.open(file, 'rt') as handle:
                for line in handle:
                    raw = line.rstrip('\n')
                    if raw.count(' ') != len(columns) - 1:
                        raise ValueError(f'Malformed variation cache block: {file}')
                    head = raw.split(' ', head_size)
                    counts['cache_records'] += 1
                    if head[positions['failed']] not in ('', '0', '-', '.'):
                        continue
                    alleles = head[positions['allele_string']].split('/')
                    if len(alleles) < 2:
                        continue
                    record_id = None
                    for allele in alleles[1:]:
                        ref, alt = alleles[0], allele
                        if len(ref) == len(alt) == 1 and ref in 'ACGTN' and alt in 'ACGTN':
                            continue
                        if head[positions['strand']] == '-1':
                            ref, alt = (a.translate(str.maketrans('ACGTN', 'TGCAN'))[::-1]
                                        for a in (ref, alt))
                        try:
                            pos, ref, alt = normalizer.key(chrom, int(head[positions['start']]), ref, alt)
                        except ValueError as error:
                            counts['skipped: ' + str(error)] += 1
                            continue
                        if record_id is None:
                            record_id = db.execute('insert into records(raw) values (?)', (raw,)).lastrowid
                        db.execute('insert into alleles values (?,?,?,?,?)', (pos, ref, alt, record_id, allele))
                        counts['indexed_alleles'] += 1
            db.commit()
        db.execute('create index variant_key on alleles(pos,ref,alt)')
        metadata.update({'status': 'complete', 'counts': dict(counts)})
        db.execute('insert into metadata values (?)', (json.dumps(metadata),))
        db.commit()
        assert db.execute('pragma integrity_check').fetchone()[0] == 'ok'
        db.close()
        temporary.replace(target)
        return metadata
    except BaseException:
        db.close()
        temporary.unlink(missing_ok=True)
        raise
