#!/usr/bin/env bash
set -euo pipefail

IMAGE=${FASTVEP_IMAGE:-mtb-fastvep:0.3.0-ac2e2b6}

version=$(docker run --rm "${IMAGE}" fastvep --version)
echo "${version}"

output=$(docker run --rm --entrypoint /bin/sh "${IMAGE}" -c '
    cp /opt/fastvep/tests/test.vcf /work/test.vcf
    cp /opt/fastvep/tests/test.gff3 /work/test.gff3
    exec fastvep annotate \
        --input /work/test.vcf \
        --gff3 /work/test.gff3 \
        --output-format tab
')

record_count=$(printf '%s\n' "${output}" | awk '!/^#/{count++} END{print count+0}')
if (( record_count < 1 )); then
    echo "ERROR: smoke test produced no annotation records" >&2
    exit 1
fi

echo "Smoke test passed: ${record_count} annotation records"
