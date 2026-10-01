#!/usr/bin/env bash
set -euo pipefail
script_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
reference_root="${FASTVEP_REFERENCE_ROOT:-/home/hpz8g5/tools/fastVEP/data/reference}"
reference_fasta="${WGS_REFERENCE_FASTA:-/home/hpz8g5/project/WGS/reference/hg38.fa}"
vep_cache="${WGS_VEP_CACHE:-/home/hpz8g5/project/MTB/database/VEP/database}"
gff3="$reference_root/Homo_sapiens.GRCh38.112.gff3"
test -s "$gff3"
test -s "$reference_fasta"
test -s "$reference_fasta.fai"
test -s "$vep_cache/homo_sapiens/112_GRCh38/info.txt"
mkdir -p "$reference_root"

docker run --rm --network none -u "$(id -u):$(id -g)" \
    -v "$script_root:/scripts:ro" -v "$vep_cache/homo_sapiens/112_GRCh38:/cache/112_GRCh38:ro" \
    --entrypoint perl ensemblorg/ensembl-vep:release_112.0 \
    /scripts/export_transcript_metadata.pl /cache/112_GRCh38 \
    > "$reference_root/vep112.transcript_metadata.jsonl.partial"
mv "$reference_root/vep112.transcript_metadata.jsonl.partial" "$reference_root/vep112.transcript_metadata.jsonl"
python3 "$script_root/complete_transcript_metadata.py" \
    --metadata "$reference_root/vep112.transcript_metadata.jsonl" --gff3 "$gff3" \
    --output "$reference_root/vep112.transcript_metadata.complete.jsonl.partial"
mv "$reference_root/vep112.transcript_metadata.complete.jsonl.partial" "$reference_root/vep112.transcript_metadata.complete.jsonl"
python3 - "$reference_root/mtb.chrom_synonyms.txt" <<'PY'
from pathlib import Path
import sys
Path(sys.argv[1]).write_text(''.join(f'{i} chr{i}\n' for i in range(1, 23)) + 'X chrX\nY chrY\nMT chrM M\n')
PY
docker run --rm --network none -u "$(id -u):$(id -g)" \
    -v "$reference_root:/reference" -v "$(dirname "$reference_fasta"):/platform:ro" \
    mtb-wgs-fastvep:0.1.0 fastvep cache \
    --gff3 /reference/Homo_sapiens.GRCh38.112.gff3 \
    --fasta "/platform/$(basename "$reference_fasta")" \
    --synonyms /reference/mtb.chrom_synonyms.txt \
    --output /reference/grch38_ensembl112.mtb.cache.partial --no-progress
mv "$reference_root/grch38_ensembl112.mtb.cache.partial" "$reference_root/grch38_ensembl112.mtb.cache"
python3 - "$reference_root" "$reference_fasta" <<'PY'
import hashlib, json, sys
from pathlib import Path
root = Path(sys.argv[1])
files = [root / 'Homo_sapiens.GRCh38.112.gff3', Path(sys.argv[2]),
         root / 'grch38_ensembl112.mtb.cache', root / 'vep112.transcript_metadata.complete.jsonl']
def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()
manifest = {'ensembl_release': 112, 'assembly': 'GRCh38', 'files':
            [{'path': str(p), 'sha256': digest(p)} for p in files]}
(root / 'mtb.reference_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
PY
