process ESTIMATE_TMB {
    tag "${meta.id}"
    label 'python'
    publishDir { "${params.outdir}/${meta.id}/downstream" }, mode: 'copy', overwrite: true
    input:
    tuple val(meta), path(callable), path(variants)
    path gtf
    output:
    tuple val(meta), path("${meta.id}.tmb_proxy.json"), emit: json
    path "${meta.id}.tmb_proxy_variants.tsv", emit: variants
    script:
    """
    estimate_tmb.py --callable '${callable}' --gtf '${gtf}' --variants '${variants}' --sample '${meta.id}'
    """
}
