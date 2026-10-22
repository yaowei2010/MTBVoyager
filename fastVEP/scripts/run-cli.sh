#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
IMAGE=${FASTVEP_IMAGE:-mtb-fastvep:0.3.0-ac2e2b6}
DATA_DIR=${FASTVEP_DATA_DIR:-${ROOT_DIR}/data}
WORK_DIR=${FASTVEP_WORK_DIR:-${ROOT_DIR}/work}
MTB_HG38_DIR=${MTB_HG38_DIR:-/home/hpz8g5/project/WGS/reference}

mkdir -p "${DATA_DIR}/reference" "${DATA_DIR}/sa" "${WORK_DIR}"

if [[ ! -r "${MTB_HG38_DIR}/hg38.fa" || ! -r "${MTB_HG38_DIR}/hg38.fa.fai" ]]; then
    echo "ERROR: MTB GRCh38 FASTA or FAI is unavailable under ${MTB_HG38_DIR}" >&2
    exit 1
fi

exec docker run --rm \
    --user "$(id -u):$(id -g)" \
    --read-only \
    --security-opt no-new-privileges:true \
    --tmpfs /tmp:size=1g,mode=1777 \
    --volume "${DATA_DIR}:/data:ro" \
    --volume "${MTB_HG38_DIR}:/mtb-reference:ro" \
    --volume "${WORK_DIR}:/work" \
    --workdir /work \
    "${IMAGE}" "$@"
