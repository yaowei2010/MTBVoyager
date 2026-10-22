#!/usr/bin/env bash
set -euo pipefail

if (( $# < 3 || $# > 4 )); then
    echo "Usage: $0 GFF3 FASTA OUTPUT_CACHE [SYNONYMS]" >&2
    exit 2
fi

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
IMAGE=${FASTVEP_IMAGE:-mtb-fastvep:0.3.0-ac2e2b6}
GFF3=$(realpath "$1")
FASTA=$(realpath "$2")
OUTPUT_CACHE=$(realpath -m "$3")
SYNONYMS=${4:-}

mkdir -p "$(dirname "${OUTPUT_CACHE}")"

args=(fastvep cache --gff3 "/gff/$(basename "${GFF3}")" --fasta "/fasta/$(basename "${FASTA}")" --output "/output/$(basename "${OUTPUT_CACHE}")")
mounts=(--volume "$(dirname "${GFF3}"):/gff:ro" --volume "$(dirname "${FASTA}"):/fasta:ro" --volume "$(dirname "${OUTPUT_CACHE}"):/output")

if [[ -n "${SYNONYMS}" ]]; then
    SYNONYMS=$(realpath "${SYNONYMS}")
    args+=(--synonyms "/synonyms/$(basename "${SYNONYMS}")")
    mounts+=(--volume "$(dirname "${SYNONYMS}"):/synonyms:ro")
fi

docker run --rm \
    --user "$(id -u):$(id -g)" \
    --read-only \
    --security-opt no-new-privileges:true \
    --tmpfs /tmp:size=2g,mode=1777 \
    "${mounts[@]}" \
    "${IMAGE}" "${args[@]}"

ls -lh "${OUTPUT_CACHE}"
