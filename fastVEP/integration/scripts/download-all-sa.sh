#!/usr/bin/env bash
# Detached queue: source failures do not prevent the other sources downloading.
set -uo pipefail
root=/home/hpz8g5/tools/fastVEP
out=$root/data/sources
mkdir -p "$out/logs"
exec 9>"$out/download-all.lock"
flock -n 9 || { echo 'A download queue is already active.' >&2; exit 1; }
printf '%s\n' "$$" > "$out/download-all.pid"
sources=(revel clinvar clinvar_protein gnomad_genes clingen repeatmasker phylop phastcons dbsnp cadd gnomad_exomes gnomad_genomes)
for source in spliceai_snv spliceai_indel primateai dbnsfp cosmic onekg topmed gerp dann mitomap omim clinpred; do
    key=${source^^}_URL
    if [[ -n ${!key:-} ]]; then sources+=("$source"); else printf '%s\t%s\tUNCONFIGURED (%s)\n' "$(date -u +%FT%TZ)" "$source" "$key" >> "$out/download-status.tsv"; fi
done
failed=0
for source in "${sources[@]}"; do
    printf '%s\t%s\tSTART\n' "$(date -u +%FT%TZ)" "$source" >> "$out/download-status.tsv"
    if bash "$root/scripts/download-sa.sh" "$source" > "$out/logs/$source.log" 2>&1; then
        status=OK
    else
        status=FAILED
        failed=1
    fi
    printf '%s\t%s\t%s\n' "$(date -u +%FT%TZ)" "$source" "$status" >> "$out/download-status.tsv"
done
printf '%s\tQUEUE\tFINISHED (failed=%s)\n' "$(date -u +%FT%TZ)" "$failed" >> "$out/download-status.tsv"
exit "$failed"
