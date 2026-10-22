#!/usr/bin/env bash
set -uo pipefail

ROOT=/home/hpz8g5/tools/fastVEP
SOURCE_DIR=${FASTVEP_SOURCE_DIR:-${ROOT}/data/sources}
OUTPUT_DIR=${FASTVEP_MTB_SA_DIR:-${ROOT}/data/sa-mtb}
RUN_DIR=${FASTVEP_CONVERSION_RUN_DIR:-${ROOT}/work/sa-conversion-20261016}
IMAGE=${FASTVEP_IMAGE:-mtb-fastvep:0.3.0-mtb-grch38-20261016}
PLUGIN=/home/hpz8g5/project/MTB/database/plugin

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

record QUEUE START

step docker_build docker build \
    --build-arg FASTVEP_COMMIT=ac2e2b64a9c4c27163a3df16e0a559113af19625 \
    --build-arg FASTVEP_VERSION=0.3.0-mtb-grch38-20261016 \
    --tag "${IMAGE}" "${ROOT}"

if ! docker image inspect "${IMAGE}" >/dev/null 2>&1; then
    record QUEUE "STOPPED (image build failed)"
    exit 1
fi

step alphamissense_copy cp -f \
    "${ROOT}/data/sa/alphamissense.osa2" \
    "${OUTPUT_DIR}/alphamissense.osa2"
step clinvar build_sa clinvar "${SOURCE_DIR}/clinvar.vcf.gz" clinvar_grch38
step primateai build_sa primateai "${PLUGIN}/PrimateAI_scores_v0.2_GRCh38_sorted.tsv.bgz" primateai_grch38

REVEL_TSV="${SOURCE_DIR}/revel_with_transcript_ids.tsv"
if [[ ! -s "${REVEL_TSV}" ]]; then
    step revel_extract bash -c "unzip -p '${SOURCE_DIR}/revel-v1.3_all_chromosomes.zip' revel_with_transcript_ids > '${REVEL_TSV}'"
fi
[[ -s "${REVEL_TSV}" ]] && step revel build_sa revel "${REVEL_TSV}" revel_grch38

step spliceai_snv build_sa spliceai "${PLUGIN}/spliceai_scores.raw.snv.hg38.vcf.gz" spliceai_snv_grch38
step spliceai_indel build_sa spliceai "${PLUGIN}/spliceai_scores.raw.indel.hg38.vcf.gz" spliceai_indel_grch38
step dbnsfp_mtb build_sa dbnsfp "${PLUGIN}/dbNSFP5.3.1a_grch38.gz" dbnsfp531a_mtb_grch38

for chrom in {1..22} X Y; do
    input="${SOURCE_DIR}/gnomad.exomes.v4.1.sites.chr${chrom}.vcf.bgz"
    [[ -s "${input}" ]] && step "gnomad_exomes_chr${chrom}" build_sa gnomad "${input}" "gnomad_exomes_v4.1_chr${chrom}"
done

for chrom in {1..22} X Y; do
    input="${SOURCE_DIR}/chr${chrom}.phyloP100way.wigFix.gz"
    [[ -s "${input}" ]] && step "phylop_chr${chrom}" build_sa phylop "${input}" "phylop100way_chr${chrom}"
done

find "${OUTPUT_DIR}" -maxdepth 1 -type f -printf '%f\t%s\n' | sort > "${RUN_DIR}/outputs.tsv"
record QUEUE FINISHED
