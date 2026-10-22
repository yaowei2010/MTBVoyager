#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
WORK_DIR=${FASTVEP_WORK_DIR:-${ROOT_DIR}/work}
IMAGE=${FASTVEP_IMAGE:-mtb-fastvep:0.3.0-mtb-grch38-20261019}
VCF=${WORK_DIR}/sa-integration-positive.vcf
OUT=${WORK_DIR}/sa-integration-positive.json

mkdir -p "${WORK_DIR}"
cat > "${VCF}" <<'VCF'
##fileformat=VCFv4.2
##contig=<ID=chr1,length=248956422>
##contig=<ID=chr17,length=83257441>
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO
chr1	11994	gnomad_positive	T	C	.	PASS	.
chr1	35142	revel_positive	G	A	.	PASS	.
chr1	65565	dbnsfp_positive	A	C	.	PASS	.
chr1	66926	clinvar_positive	AG	A	.	PASS	.
chr1	69091	splice_snv_positive	A	C	.	PASS	.
chr1	69091	splice_indel_positive	A	AA	.	PASS	.
chr1	69094	primate_positive	G	A	.	PASS	.
chr17	137594	alphamissense_positive	A	C	.	PASS	.
VCF

FASTVEP_IMAGE="${IMAGE}" "${ROOT_DIR}/scripts/run-hg38.sh" \
    /work/sa-integration-positive.vcf \
    /work/sa-integration-positive.json json

python3 - "${OUT}" <<'PY'
import json, sys

with open(sys.argv[1], encoding="utf-8") as handle:
    data = json.load(handle)

keys = set()
def walk(value):
    if isinstance(value, dict):
        keys.update(value)
        for child in value.values():
            walk(child)
    elif isinstance(value, list):
        for child in value:
            walk(child)
walk(data)

expected = {
    "alphaMissense", "clinvar", "dbnsfp", "gnomad",
    "phylop", "primateAI", "revel", "spliceAI",
}
missing = sorted(expected - keys)
if missing:
    raise SystemExit("Missing supplementary annotation keys: " + ", ".join(missing))
print(f"PASS: {len(data)} variants; all {len(expected)} supplementary sources were observed")
PY
