#!/usr/bin/env bash
set -euo pipefail

if (( $# < 2 || $# > 3 )); then
    echo "Usage: $0 INPUT_VCF OUTPUT [tab|json|vcf]" >&2
    echo "INPUT_VCF and OUTPUT must be paths below this installation's work/ directory." >&2
    exit 2
fi

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
INPUT=$1
OUTPUT=$2
FORMAT=${3:-tab}
WORK_DIR=${FASTVEP_WORK_DIR:-${ROOT_DIR}/work}
SA_SUBDIR=${FASTVEP_SA_SUBDIR:-sa-mtb}

case "${FORMAT}" in
    tab|json|vcf) ;;
    *) echo "ERROR: output format must be tab, json, or vcf" >&2; exit 2 ;;
esac

if [[ "${INPUT}" != /work/* ]]; then
    echo "ERROR: INPUT_VCF must use a /work/... container path" >&2
    exit 2
fi
host_input="${WORK_DIR}/${INPUT#/work/}"
if [[ ! -r "${host_input}" ]]; then
    echo "ERROR: input is not readable: ${host_input}" >&2
    exit 1
fi
filtered_host=$(mktemp "${WORK_DIR}/.fastvep-canonical-XXXXXX.vcf")
filtered_container="/work/$(basename "${filtered_host}")"
trap 'rm -f "${filtered_host}"' EXIT
"${ROOT_DIR}/scripts/filter-canonical-vcf.sh" "${host_input}" "${filtered_host}"

"${ROOT_DIR}/scripts/run-cli.sh" fastvep annotate \
    --input "${filtered_container}" \
    --output "${OUTPUT}" \
    --fasta /mtb-reference/hg38.fa \
    --transcript-cache /data/reference/grch38_ensembl112.representative.mtb.cache \
    --sa-dir "/data/${SA_SUBDIR}" \
    --hgvs \
    --symbol \
    --canonical \
    --output-format "${FORMAT}"
