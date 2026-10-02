#!/usr/bin/env bash
set -euo pipefail

annotation_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
students_root="$(dirname "$annotation_root")"
run_dir="${RUN_DIR:-/tmp/mtb-fastvep-validation-$(date -u +%Y%m%dT%H%M%S)}"
annotation_image="${ANNOTATION_IMAGE:-mtb-wgs-fastvep:0.1.1}"
launcher_image="${LAUNCHER_IMAGE:-takeshi945/nckumtb:backend-wgs-germline-20260722-acmg-sf-v33}"
mkdir -p "$run_dir"
run_dir="$(cd "$run_dir" && pwd)"

docker run --rm -i --network none -u "$(id -u):$(id -g)" \
    -v "$annotation_root:/src:ro" -v "$run_dir:$run_dir" \
    "$annotation_image" python - "$run_dir" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, '/src/tests')
from test_adapter import fixture
root = Path(sys.argv[1])
fixture(root)
(root / 'genes.txt').write_text('GENEA\n')
(root / 'germline.csv').write_text('sample_id,snv_vcf,sv_vcf,cnv_vcf,gene_list,sex\nFASTVEP_TEST,' + str(root / 'input.vcf') + ',,,' + str(root / 'genes.txt') + ',unknown\n')
(root / 'somatic.csv').write_text('sample_id,snv_vcf,sv_vcf,cnv_vcf,callable_regions\nFASTVEP_TEST,' + str(root / 'input.vcf') + ',,,\n')
(root / 'cancer_db').mkdir()
(root / 'cancer_db' / 'oncokb_final_database.csv').write_text('Chr,Start,Ref,Alt,oncoKB_annotation\n')
(root / 'cancer_db' / 'CIVic.2024.clinicalevidence.csv').write_text('gene,variant,reference_build\n')
(root / 'cancer_db' / 'COSMIC_filtered.tsv').write_text('GENE\tMUTATION_AA_SYNTAX\n')
for name in ('CGI_database.json', 'MyCancerGenome_Biomarker.json'):
    (root / 'cancer_db' / name).write_text('{}\n')
PY
docker run --rm --network none -u "$(id -u):$(id -g)" -v "$run_dir:$run_dir" \
    "$annotation_image" fastvep cache --gff3 "$run_dir/reference.gff3" \
    --fasta "$run_dir/reference.fa" --output "$run_dir/transcripts.cache" --no-progress

for kind in germline somatic; do
    if [[ "$kind" == germline ]]; then
        pipeline="$students_root/backend_wgs/pipeline"
        extras=(--skip_structural true --skip_pharmcat true)
    else
        pipeline="$students_root/backend_wgs_somatic/pipeline"
        extras=(--cancer_db "$run_dir/cancer_db" --annotsv_annotations "$run_dir/cancer_db" \
            --oncovi_resources "$pipeline/tests/data/oncovi_resources")
    fi
    mkdir -p "$run_dir/$kind-run"
    docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
        -v "$students_root:$students_root:ro" -v "$run_dir:$run_dir" \
        -w "$run_dir/$kind-run" --entrypoint nextflow "$launcher_image" \
        run "$pipeline/main.nf" -profile docker -work-dir "$run_dir/$kind-work" \
        --input "$run_dir/$kind.csv" --outdir "$run_dir/$kind-results" \
        --annotation_engine fastvep --fastvep_image "$annotation_image" \
        --reference "$run_dir/reference.fa" --vep_cache "$run_dir/cache" \
        --vep_plugin_data "$run_dir/plugins" --fastvep_gff3 "$run_dir/reference.gff3" \
        --fastvep_transcript_cache "$run_dir/transcripts.cache" \
        --fastvep_transcript_metadata "$run_dir/transcripts.jsonl" \
        --fastvep_cpus 1 --fastvep_memory '2 GB' --vep_contigs chr1 \
        "${extras[@]}" -ansi-log false
done

docker run --rm -i --network none -v "$run_dir:$run_dir:ro" "$annotation_image" python - "$run_dir" <<'PY'
import csv, gzip, json, sys
from pathlib import Path
root = Path(sys.argv[1])
for kind in ('germline', 'somatic'):
    result = root / (kind + '-results') / 'FASTVEP_TEST'
    completion = json.loads((result / 'pipeline_complete.json').read_text())
    assert completion['status'] == 'complete'
    assert completion['annotation_engine'] == 'fastvep'
    with gzip.open(result / 'annotation' / 'FASTVEP_TEST.vep.tsv.gz', 'rt') as f:
        rows = list(csv.DictReader((line for line in f if not line.startswith('##')), delimiter='\t'))
    assert len(rows) == 1, rows
    row = rows[0]
    assert row['SYMBOL'] == 'GENEA' and row['Consequence'] == 'missense_variant', row
    assert row['IND'] == 'FASTVEP_TEST' and row['ZYG'] == 'HET', row
    assert row['CADD_phred'] == '25' and row['SpliceAI_cutoff'] == 'PASS', row
    assert row['gnomADg_AF'] == '0.002' and row['CLIN_SIG'] == 'pathogenic', row
    if kind == 'somatic':
        interpreted = result / 'interpretation' / 'FASTVEP_TEST.snv.all.tsv'
        with interpreted.open() as f:
            classified = list(csv.DictReader(f, delimiter='\t'))
        assert classified and classified[0]['oncovi_2026_validation_status'].startswith('pending_fastvep_')
        assert classified[0]['oncogenicity_review_required'] == 'true'
print('Both complete Nextflow workflows passed:', root)
PY
