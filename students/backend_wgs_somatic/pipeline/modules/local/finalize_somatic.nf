process FINALIZE_SOMATIC {
    tag "${meta.id}"
    label 'python'
    publishDir { "${params.outdir}/${meta.id}" }, mode: 'copy', overwrite: true
    input:
    tuple val(meta), path(snv_summary), val(kinds), path(structural_summaries)
    output:
    path 'pipeline_complete.json'
    script:
    """
    python - '${meta.id}' '${snv_summary}' ${structural_summaries.collect { "'${it}'" }.join(' ')} <<'PY'
import json, sys
sample, snv, *structural = sys.argv[1:]
result={'sample_id':sample,'analysis_type':'WGS Somatic Tumor-Only','genome_build':'GRCh38','status':'complete','snv':json.load(open(snv)),'structural':{}}
for path in structural:
    data=json.load(open(path)); result['structural'][data['kind']]=data
open('pipeline_complete.json','w').write(json.dumps(result,indent=2)+'\\n')
PY
    """
}
