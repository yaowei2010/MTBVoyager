#!/usr/bin/env bash
set -euo pipefail

if (( $# < 4 || $# > 5 )); then
    echo "Usage: $0 INPUT_GFF3 FASTA OUTPUT_GFF3 OUTPUT_CACHE [SYNONYMS]" >&2
    exit 2
fi

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
INPUT_GFF3=$1
FASTA=$2
OUTPUT_GFF3=$3
OUTPUT_CACHE=$4
SYNONYMS=${5:-}

mkdir -p "$(dirname "${OUTPUT_GFF3}")" "$(dirname "${OUTPUT_CACHE}")"
python3 "${ROOT_DIR}/scripts/select-representative-transcripts.py" "${INPUT_GFF3}" "${OUTPUT_GFF3}"

args=("${ROOT_DIR}/scripts/build-transcript-cache.sh" "${OUTPUT_GFF3}" "${FASTA}" "${OUTPUT_CACHE}")
if [[ -n "${SYNONYMS}" ]]; then
    args+=("${SYNONYMS}")
fi
"${args[@]}"
