#!/usr/bin/env bash
set -euo pipefail

if (( $# < 3 || $# > 4 )); then
    echo "Usage: $0 SOURCE INPUT OUTPUT_BASE [ASSEMBLY]" >&2
    echo "Example: $0 alphamissense /path/AlphaMissense_hg38.tsv.gz alphamissense GRCh38" >&2
    exit 2
fi

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
IMAGE=${FASTVEP_IMAGE:-mtb-fastvep:0.3.0-ac2e2b6}
SOURCE=$1
INPUT=$(realpath "$2")
OUTPUT_BASE=$3
ASSEMBLY=${4:-GRCh38}
OUTPUT_DIR=${FASTVEP_SA_DIR:-${ROOT_DIR}/data/sa-mtb}

mkdir -p "${OUTPUT_DIR}"

docker run --rm \
    --user "$(id -u):$(id -g)" \
    --read-only \
    --security-opt no-new-privileges:true \
    --tmpfs /tmp:size=2g,mode=1777 \
    --volume "$(dirname "${INPUT}"):/input:ro" \
    --volume "${OUTPUT_DIR}:/output" \
    "${IMAGE}" \
    fastvep sa-build \
    --source "${SOURCE}" \
    --input "/input/$(basename "${INPUT}")" \
    --output "/output/${OUTPUT_BASE}" \
    --assembly "${ASSEMBLY}"

find "${OUTPUT_DIR}" -maxdepth 1 -type f -name "${OUTPUT_BASE}.*" -printf '%f\t%s bytes\n'
