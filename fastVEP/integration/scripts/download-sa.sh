#!/usr/bin/env bash
# Download GRCh38 supplementary annotation inputs; does not build fastSA databases.
# Public URL references: src/docs/ACMG_SETUP.md and upstream download portals.
set -euo pipefail

usage() {
    cat <<'EOF'
Usage: download-sa.sh [--dry-run] [--output-dir DIR] SOURCE...

Public sources:
  revel clinvar clinvar_protein gnomad_exomes gnomad_genomes
  gnomad_genes clingen phylop repeatmasker dbsnp
  core  = revel clinvar clinvar_protein gnomad_genes clingen repeatmasker
  all   = all public sources, plus any supplied SOURCE_URL sources
  cadd phastcons have public default URLs (GRCh38 v1.7 / UCSC 100way).

Sources requiring a supplied DIRECT file URL (not a website/login page):
  spliceai_snv spliceai_indel primateai dbnsfp cosmic onekg topmed
  gerp dann mitomap omim cadd clinpred phastcons
Set the uppercase source name plus _URL, e.g. DBNSFP_URL.
Optionally set SOURCE_FILENAME to retain the actual upstream extension.
Default destination: fastVEP/data/sources (override FASTVEP_ROOT or --output-dir).

Examples:
  ./scripts/download-sa.sh --dry-run core
  ./scripts/download-sa.sh core
  CHROMS='22 X' ./scripts/download-sa.sh gnomad_exomes phylop
  SPLICEAI_SNV_URL='https://.../file.vcf.gz' ./scripts/download-sa.sh spliceai_snv

Options/environment:
  CHROMS          Space-separated chromosomes; default 1..22 X Y.
  CLINVAR_URL     Override with a dated GRCh38 VCF URL; .md5 is fetched too.
  REVEL_URL       Override the v1.3 ZIP URL.
  DBSNP_URL       Override the GRCh38 dbSNP URL.
  CURL_CONFIG    Optional curl config containing authentication; never printed.

Existing final files are validated and skipped; .part files are resumed.
Record download history in downloads.tsv (URLs omitted to protect signed links).
Checks gzip/BGZF/ZIP integrity and rejects empty files and HTML login/error pages.
Verify GRCh38 assembly, field schema, and downloaded release before sa-build.
Full gnomAD downloads are hundreds of GB; choose CHROMS explicitly if needed.

Official gated portals:
  SpliceAI: https://basespace.illumina.com/s/otSPW8hnhaZR
  PrimateAI: https://basespace.illumina.com/s/yYGFdGih1rXL
  dbNSFP: https://www.dbnsfp.org/download/
  COSMIC: https://www.cosmickb.org/
  1000G: https://www.internationalgenome.org/data/
  TOPMed: https://bravo.sph.umich.edu/
  OMIM: https://www.omim.org/downloads
  CADD: https://cadd.bihealth.org/download

Format notes:
  REVEL: unzip then build the CSV with --source revel.
  PrimateAI: normalize to chr,pos,ref,alt,score TSV; ensure hg38 coordinates.
  ClinGen: run src/analysis/acmg_benchmark/scripts/sa_sources/clingen_gdv_to_oga.py.
  RepeatMasker: run repeatmasker_to_bed.py from that same directory.
  PhyloP: build chromosome wigFix.gz files separately with --source phylop.
  GERP/bigWig: convert to WIG or per-base TSV before building.
  dbNSFP: built-in parser extracts SIFT/PolyPhen only.
  CADD/ClinPred/phastCons need a custom conversion or downstream annotation.
  DANN: current built-in source matches positions, not individual ALT alleles.
  MITOMAP: normalize to pos,ref,alt,disease,status TSV.
EOF
}

ROOT=${FASTVEP_ROOT:-/home/hpz8g5/tools/fastVEP}
OUT=${FASTVEP_SOURCE_DIR:-$ROOT/data/sources}
DRY=0
sources=()
while (( $# )); do
    case "$1" in
        --dry-run) DRY=1; shift ;;
        --output-dir) [[ $# -ge 2 ]] || { usage >&2; exit 2; }; OUT=$2; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        --*) echo "Unknown option: $1" >&2; exit 2 ;;
        core) sources+=(revel clinvar clinvar_protein gnomad_genes clingen repeatmasker); shift ;;
        all)
            sources+=(revel clinvar clinvar_protein gnomad_genes clingen repeatmasker dbsnp phylop cadd phastcons gnomad_exomes gnomad_genomes)
            for optional in spliceai_snv spliceai_indel primateai dbnsfp cosmic onekg topmed gerp dann mitomap omim clinpred; do
                key=${optional^^}_URL
                if [[ -n ${!key:-} ]]; then sources+=("$optional"); else printf '[unconfigured] %s: set %s\n' "$optional" "$key" >&2; fi
            done
            shift ;;
        *) sources+=("$1"); shift ;;
    esac
done
(( ${#sources[@]} )) || { usage >&2; exit 2; }
read -r -a chromosomes <<< "${CHROMS:-1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 X Y}"
for c in "${chromosomes[@]}"; do
    [[ $c =~ ^([1-9]|1[0-9]|2[0-2]|X|Y|M)$ ]] || { echo "Invalid chromosome: $c" >&2; exit 2; }
done

validate() {
    local file=$1
    [[ -s $file ]] || { echo "Empty download: $file" >&2; return 1; }
    if head -c 1024 "$file" | LC_ALL=C grep -aEi '<!doctype html|<html([ >])' >/dev/null; then
        echo "HTML received instead of data: $file" >&2; return 1
    fi
    case "$file" in
        *.gz|*.bgz|*.gz.part|*.bgz.part) gzip -t "$file" ;;
        *.zip|*.zip.part) unzip -tq "$file" >/dev/null ;;
    esac
}

download() {
    local source=$1 url=$2 name=$3 dest
    [[ $url == https://* ]] || { echo "$source requires an HTTPS direct file URL" >&2; exit 2; }
    [[ $name != */* && $name != .* ]] || { echo "Invalid filename for $source" >&2; exit 2; }
    dest=$OUT/$name
    if (( DRY )); then printf '[dry-run] %s -> %s\n' "$source" "$dest"; return; fi
    mkdir -p "$OUT"
    if [[ -f $dest ]]; then validate "$dest"; printf '[skip] %s\n' "$dest"; return; fi
    printf '[download] %s -> %s\n' "$source" "$dest"
    local args=(--location --fail --retry 3 --retry-delay 3 --connect-timeout 30
        --proto '=https' --proto-redir '=https' --continue-at - --output "$dest.part")
    if [[ -n ${CURL_CONFIG:-} ]]; then args+=(--config "$CURL_CONFIG"); fi
    curl "${args[@]}" "$url"
    validate "$dest.part"
    mv "$dest.part" "$dest"
    printf '%s\t%s\t%s\t%s\n' "$(date -u +%FT%TZ)" "$source" "$name" "$(wc -c < "$dest")" >> "$OUT/downloads.tsv"
}

ncbi=https://ftp.ncbi.nlm.nih.gov
gnomad=https://storage.googleapis.com/gcp-public-data--gnomad/release/4.1
ucsc=https://hgdownload.soe.ucsc.edu/goldenPath/hg38
for source in "${sources[@]}"; do
    case "$source" in
        revel) download "$source" "${REVEL_URL:-https://rothsj06.dmz.hpc.mssm.edu/revel-v1.3_all_chromosomes.zip}" revel-v1.3_all_chromosomes.zip ;;
        clinvar)
            url=${CLINVAR_URL:-$ncbi/pub/clinvar/vcf_GRCh38/clinvar.vcf.gz}
            download "$source" "$url" clinvar.vcf.gz
            download "$source" "$url.md5" clinvar.vcf.gz.md5
            if (( ! DRY )); then
                expected=$(LC_ALL=C grep -Eo '[a-fA-F0-9]{32}' "$OUT/clinvar.vcf.gz.md5" | head -n 1)
                actual=$(md5sum "$OUT/clinvar.vcf.gz"); actual=${actual%% *}
                [[ -n $expected && ${actual,,} == ${expected,,} ]] || { echo 'ClinVar MD5 mismatch' >&2; exit 1; }
            fi ;;
        clinvar_protein) download "$source" "$ncbi/pub/clinvar/tab_delimited/variant_summary.txt.gz" variant_summary.txt.gz ;;
        gnomad_genes) download "$source" "$gnomad/constraint/gnomad.v4.1.constraint_metrics.tsv" gnomad.v4.1.constraint_metrics.tsv ;;
        clingen) download "$source" https://search.clinicalgenome.org/kb/gene-validity/download clingen_gene_validity.csv ;;
        repeatmasker) download "$source" "$ucsc/database/rmsk.txt.gz" rmsk.txt.gz ;;
        dbsnp) download "$source" "${DBSNP_URL:-$ncbi/snp/latest_release/VCF/GCF_000001405.40.gz}" GCF_000001405.40.gz ;;
        gnomad_exomes|gnomad_genomes)
            kind=${source#gnomad_}
            for c in "${chromosomes[@]}"; do
                [[ $c != M ]] || continue
                name=gnomad.$kind.v4.1.sites.chr$c.vcf.bgz
                download "$source" "$gnomad/vcf/$kind/$name" "$name"
                download "$source" "$gnomad/vcf/$kind/$name.tbi" "$name.tbi"
            done ;;
        cadd)
            base=https://kircherlab.bihealth.org/download/CADD/v1.7/GRCh38
            for name in whole_genome_SNVs.tsv.gz gnomad.genomes.r4.0.indel.tsv.gz; do
                download "$source" "$base/$name" "cadd.v1.7.$name"
                download "$source" "$base/$name.tbi" "cadd.v1.7.$name.tbi"
            done ;;
        phastcons)
            download "$source" "${PHASTCONS_URL:-$ucsc/phastCons100way/hg38.phastCons100way.bw}" hg38.phastCons100way.bw ;;
        phylop)
            for c in "${chromosomes[@]}"; do
                name=chr$c.phyloP100way.wigFix.gz
                download "$source" "$ucsc/phyloP100way/hg38.100way.phyloP100way/$name" "$name"
            done ;;
        spliceai_snv|spliceai_indel|primateai|dbnsfp|cosmic|onekg|topmed|gerp|dann|mitomap|omim|clinpred)
            variable=${source^^}_URL
            filename_variable=${source^^}_FILENAME
            url=${!variable:-}
            [[ -n $url ]] || { echo "Set $variable to a direct GRCh38 file URL; see --help." >&2; exit 2; }
            path=${url%%\?*}; path=${path%%\#*}
            name=${!filename_variable:-${path##*/}}
            download "$source" "$url" "$name" ;;
        *) echo "Unknown source: $source (see --help)" >&2; exit 2 ;;
    esac
done
