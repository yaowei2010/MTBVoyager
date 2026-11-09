#!/usr/bin/env bash
set -euo pipefail

fastvep_root=${FASTVEP_ROOT:-/home/hpz8g5/tools/fastVEP}
mtb_fastvep=${MTB_FASTVEP_ROOT:-/home/hpz8g5/project/MTB/fastVEP}
log_dir=${fastvep_root}/data/sources/logs/gnomad-genomes-retry
mkdir -p "${log_dir}"

echo "[$(date -u +%FT%TZ)] resume chr10 download"
FASTVEP_ROOT="${fastvep_root}" CHROMS=10 \
  "${fastvep_root}/scripts/download-sa.sh" gnomad_genomes \
  >"${log_dir}/chr10.log" 2>&1

echo "[$(date -u +%FT%TZ)] build chr10-Y"
FASTVEP_ROOT="${fastvep_root}" \
  "${mtb_fastvep}/scripts/build-gnomad-genomes-sa.sh" \
  10 11 12 13 14 15 16 17 18 19 20 21 22 X Y \
  >"${log_dir}/build-chr10-Y.log" 2>&1

echo "[$(date -u +%FT%TZ)] complete"
