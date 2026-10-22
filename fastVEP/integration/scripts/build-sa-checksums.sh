#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
SA_DIR=${FASTVEP_SA_DIR:-${ROOT_DIR}/data/sa-mtb}
MANIFEST_DIR=${FASTVEP_MANIFEST_DIR:-${ROOT_DIR}/manifests}
OUTPUT=${MANIFEST_DIR}/SA_MTB_SHA256SUMS.txt
TMP=${OUTPUT}.tmp
JOBS=${FASTVEP_CHECKSUM_JOBS:-4}

mkdir -p "${MANIFEST_DIR}"
cd "${SA_DIR}"
find . -maxdepth 1 -type f -name '*.osa2' -printf '%f\n' \
    | sort -V \
    | xargs -r -n 1 -P "${JOBS}" sha256sum \
    | sort -V -k2 > "${TMP}"
mv "${TMP}" "${OUTPUT}"
printf 'Wrote %s checksums to %s\n' "$(wc -l < "${OUTPUT}")" "${OUTPUT}"
