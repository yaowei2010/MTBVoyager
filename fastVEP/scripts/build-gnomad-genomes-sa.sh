#!/usr/bin/env bash
set -euo pipefail

root=${FASTVEP_ROOT:-/home/hpz8g5/tools/fastVEP}
image=${FASTVEP_IMAGE:-mtb-fastvep:0.3.0-ac2e2b6}
source_dir=${root}/data/sources
output_dir=${FASTVEP_SA_DIR:-${root}/data/sa-mtb}
chromosomes=("${@:-1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 X Y}")
info_fields=AF,AF_afr,AF_ami,AF_amr,AF_asj,AF_eas,AF_fin,AF_mid,AF_nfe,AF_remaining,AF_sas

mkdir -p "${output_dir}" "${source_dir}/logs/gnomad-genomes-build"
for chrom in ${chromosomes[*]}; do
    input=${source_dir}/gnomad.genomes.v4.1.sites.chr${chrom}.vcf.bgz
    output=gnomad_genomes_v4_1_chr${chrom}
    [[ -s ${input} && -s ${input}.tbi ]] || { echo "Missing complete chr${chrom} VCF/index" >&2; exit 1; }
    [[ ! -s ${output_dir}/${output}.osa2 ]] || { echo "[skip] chr${chrom}"; continue; }
    echo "[build] chr${chrom}"
    docker run --rm --user "$(id -u):$(id -g)" --read-only \
      --security-opt no-new-privileges:true --tmpfs /tmp:size=4g,mode=1777 \
      -v "${source_dir}:/input:ro" -v "${output_dir}:/output" "${image}" \
      fastvep sa-build --source custom_vcf \
      --name gnomadGenomes --info-fields "${info_fields}" --format osa2 \
      --input "/input/$(basename "${input}")" --output "/output/${output}" --assembly GRCh38 \
      >"${source_dir}/logs/gnomad-genomes-build/chr${chrom}.log" 2>&1
    [[ -s ${output_dir}/${output}.osa2 ]] || { echo "Build failed for chr${chrom}" >&2; exit 1; }
done
