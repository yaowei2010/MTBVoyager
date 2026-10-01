process FINALIZE {
    tag "${meta.id}"
    publishDir { "${params.outdir}/${meta.id}" }, mode: 'copy', overwrite: true

    input:
    tuple val(meta), path(snv_summary), path(structural_summary)

    output:
    path "pipeline_complete.json"

    script:
    """
    python - '${meta.id}' '${snv_summary}' '${structural_summary}' > pipeline_complete.json <<'PY'
import json, sys
sample, snv_path, structural_path = sys.argv[1:]
print(json.dumps({"sample_id": sample, "status": "complete", "snv": json.load(open(snv_path)), "structural": json.load(open(structural_path))}, indent=2))
PY
    """
}

