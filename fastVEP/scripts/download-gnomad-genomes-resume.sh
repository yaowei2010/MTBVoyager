#!/usr/bin/env bash
set -euo pipefail

root=${FASTVEP_ROOT:-/home/hpz8g5/tools/fastVEP}
workers=${GNOMAD_DOWNLOAD_WORKERS:-3}
chromosomes=(4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 X Y)
log_dir=${root}/data/sources/logs/gnomad-genomes
mkdir -p "${log_dir}"

download_one() {
    local chrom=$1
    local final=${root}/data/sources/gnomad.genomes.v4.1.sites.chr${chrom}.vcf.bgz
    if [[ -s ${final} && -s ${final}.tbi ]]; then
        printf '%s\tchr%s\tSKIP_COMPLETE\n' "$(date -u +%FT%TZ)" "${chrom}"
        return
    fi
    printf '%s\tchr%s\tSTART\n' "$(date -u +%FT%TZ)" "${chrom}"
    if FASTVEP_ROOT=${root} CHROMS=${chrom} \
        "${root}/scripts/download-sa.sh" gnomad_genomes \
        >"${log_dir}/chr${chrom}.log" 2>&1; then
        printf '%s\tchr%s\tOK\n' "$(date -u +%FT%TZ)" "${chrom}"
    else
        printf '%s\tchr%s\tFAILED\n' "$(date -u +%FT%TZ)" "${chrom}" >&2
        return 1
    fi
}
export -f download_one
export root log_dir

printf '%s\tQUEUE\tSTART workers=%s\n' "$(date -u +%FT%TZ)" "${workers}"
printf '%s\n' "${chromosomes[@]}" | xargs -r -n1 -P "${workers}" bash -c 'download_one "$1"' _
printf '%s\tQUEUE\tCOMPLETE\n' "$(date -u +%FT%TZ)"
