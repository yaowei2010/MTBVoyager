#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
MTB_HG38_DIR=${MTB_HG38_DIR:-/home/hpz8g5/project/WGS/reference}
DATA_DIR=${FASTVEP_DATA_DIR:-${ROOT_DIR}/data}
SA_SUBDIR=${FASTVEP_SA_SUBDIR:-sa-mtb}
SA_CHECKSUMS=${FASTVEP_SA_CHECKSUMS:-${ROOT_DIR}/manifests/SA_MTB_SHA256SUMS.txt}

declare -A expected=(
  ["${MTB_HG38_DIR}/hg38.fa"]="5be01555d98347fdb3714dc84c6f77c9d8bc774adcf32c6f7a8fa06f5baf5e51"
  ["${DATA_DIR}/reference/Homo_sapiens.GRCh38.112.representative.gff3"]="10864779a12f0a932bcb29fdc6feba7329d4d02a3e131ea6d078c5c80a464048"
  ["${DATA_DIR}/reference/grch38_ensembl112.representative.mtb.cache"]="7e746c067bb065fb175303415a262f7db5f8a66f2aed32981c6e07fd91a8e02b"
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
