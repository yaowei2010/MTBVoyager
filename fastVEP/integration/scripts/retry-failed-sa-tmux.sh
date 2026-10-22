#!/usr/bin/env bash
set -uo pipefail

ROOT=/home/hpz8g5/tools/fastVEP
SOURCE_DIR=${FASTVEP_SOURCE_DIR:-${ROOT}/data/sources}
OUTPUT_DIR=${FASTVEP_MTB_SA_DIR:-${ROOT}/data/sa-mtb}
RUN_DIR=${FASTVEP_RETRY_RUN_DIR:-${ROOT}/work/sa-retry-20261019}
IMAGE=${FASTVEP_IMAGE:-mtb-fastvep:0.3.0-mtb-grch38-20261019}
PLUGIN=/home/hpz8g5/project/MTB/database/plugin
SPLICE_ORIGINAL=${PLUGIN}/spliceai_scores.raw.indel.hg38.vcf.gz
SPLICE_REPAIRED=${SOURCE_DIR}/spliceai_scores.raw.indel.hg38.repaired.vcf.gz
BGZF_LAST_COMPLETE=39771176389
BGZF_EOF_B64=H4sIBAAAAAAA/wYAQkMCABsAAwAAAAAAAAAAAA==

mkdir -p "${OUTPUT_DIR}" "${RUN_DIR}/logs"
: > "${RUN_DIR}/status.tsv"

record() { printf '%s\t%s\t%s\n' "$(date -u +%FT%TZ)" "$1" "$2" | tee -a "${RUN_DIR}/status.tsv"; }
step() {
    local name=$1; shift
    record "${name}" START
    if "$@" >"${RUN_DIR}/logs/${name}.log" 2>&1; then
        record "${name}" OK
    else
        record "${name}" FAILED
    fi
}
build_sa() {
    local source=$1 input=$2 output=$3
    FASTVEP_IMAGE="${IMAGE}" FASTVEP_SA_DIR="${OUTPUT_DIR}" \
        "${ROOT}/scripts/build-sa.sh" "${source}" "${input}" "${output}" GRCh38
}
repair_spliceai() {
    cp --reflink=auto "${SPLICE_ORIGINAL}" "${SPLICE_REPAIRED}"
    truncate -s "${BGZF_LAST_COMPLETE}" "${SPLICE_REPAIRED}"
    printf '%s' "${BGZF_EOF_B64}" | base64 -d >> "${SPLICE_REPAIRED}"
    bgzip -t "${SPLICE_REPAIRED}"
}

record QUEUE START
if docker image inspect "${IMAGE}" >/dev/null 2>&1; then
    record docker_build SKIPPED_EXISTING
else
    step docker_build docker build \
        --build-arg FASTVEP_COMMIT=ac2e2b64a9c4c27163a3df16e0a559113af19625 \
        --build-arg FASTVEP_VERSION=0.3.0-mtb-grch38-20261019 \
        --tag "${IMAGE}" "${ROOT}"
fi

if ! docker image inspect "${IMAGE}" >/dev/null 2>&1; then
    record QUEUE "STOPPED (image build failed)"
    exit 1
fi

if [[ $(stat -c %s "${OUTPUT_DIR}/primateai_grch38.osa2" 2>/dev/null || echo 0) -gt 1000000 ]]; then
    record primateai SKIPPED_VALID_EXISTING
else
    step primateai build_sa primateai \
        "${PLUGIN}/PrimateAI_scores_v0.2_GRCh38_sorted.tsv.bgz" primateai_grch38
fi

for chrom in {1..22} X Y; do
    input="${SOURCE_DIR}/gnomad.exomes.v4.1.sites.chr${chrom}.vcf.bgz"
    [[ -s "${input}" ]] && step "gnomad_exomes_chr${chrom}" \
        # Do not put a dot in OUTPUT_BASE: Rust Path::with_extension() treats
        # everything after the final dot as an extension and would collapse
        # every `v4.1_chrN` shard to the same `v4.osa2` path.
        build_sa gnomad "${input}" "gnomad_exomes_v4_1_chr${chrom}"
done

step spliceai_indel_repair repair_spliceai
if [[ -s "${SPLICE_REPAIRED}" ]]; then
    step spliceai_indel build_sa spliceai \
        "${SPLICE_REPAIRED}" spliceai_indel_grch38
fi

find "${OUTPUT_DIR}" -maxdepth 1 -type f -printf '%f\t%s\n' | sort > "${RUN_DIR}/outputs.tsv"
record QUEUE FINISHED
