#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
MTB_HG38_DIR=${MTB_HG38_DIR:-/home/hpz8g5/project/WGS/reference}
DATA_DIR=${FASTVEP_DATA_DIR:-${ROOT_DIR}/data}
SA_SUBDIR=${FASTVEP_SA_SUBDIR:-sa-mtb}
SA_CHECKSUMS=${FASTVEP_SA_CHECKSUMS:-${ROOT_DIR}/manifests/SA_MTB_SHA256SUMS.txt}

declare -A expected=(
  ["${MTB_HG38_DIR}/hg38.fa"]="5be01555d98347fdb3714dc84c6f77c9d8bc774adcf32c6f7a8fa06f5baf5e51"
  ["${DATA_DIR}/reference/Homo_sapiens.GRCh38.112.canonical.gff3"]="6848f42e1d1f2d239389ee3bd050fbb3ce8685a19ebc919f73006695c6d7fa06"
  ["${DATA_DIR}/reference/grch38_ensembl112.canonical.mtb.cache"]="3b94c6b324021dd34254840aac1b49d053a885bc6a23b3e5e8900ba79df7c451"
)

failed=0
for path in "${!expected[@]}"; do
    if [[ ! -r "${path}" ]]; then
        echo "MISSING  ${path}"
        failed=1
        continue
    fi
    actual=$(sha256sum "${path}" | awk '{print $1}')
    if [[ "${actual}" == "${expected[$path]}" ]]; then
        echo "OK       ${path}"
    else
        echo "MISMATCH ${path}"
        echo "         expected=${expected[$path]}"
        echo "         actual=${actual}"
        failed=1
    fi
done

if [[ ! -r "${SA_CHECKSUMS}" ]]; then
    echo "MISSING  ${SA_CHECKSUMS}"
    failed=1
else
    echo "VERIFY   supplementary annotations in ${DATA_DIR}/${SA_SUBDIR}"
    if ! (cd "${DATA_DIR}/${SA_SUBDIR}" && sha256sum --check "${SA_CHECKSUMS}"); then
        failed=1
    fi
fi

exit "${failed}"
