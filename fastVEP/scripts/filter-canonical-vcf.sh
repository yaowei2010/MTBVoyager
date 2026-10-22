#!/usr/bin/env bash
set -euo pipefail

if (( $# != 2 )); then
    echo "Usage: $0 INPUT.vcf[.gz] OUTPUT.vcf" >&2
    exit 2
fi

input=$1
output=$2
reader=(cat "${input}")
if [[ "${input}" == *.gz ]]; then
    reader=(gzip -dc "${input}")
fi

"${reader[@]}" | awk 'BEGIN{FS=OFS="\t"}
    /^#/ {print; next}
    $1 ~ /^(chr)?([1-9]|1[0-9]|2[0-2]|X|Y)$/ || $1 ~ /^(chrM|MT)$/ {print}' > "${output}"
