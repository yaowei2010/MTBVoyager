process SUMMARIZE_STRUCTURAL {
    tag "${meta.id}:${kind}"
    label 'python'
    publishDir { "${params.outdir}/${meta.id}/${kind}" }, mode: 'copy', overwrite: true
    input:
    tuple val(meta), val(kind), path(vcf)
    path cancer_db
    path annotsv_annotations
    output:
    tuple val(meta), val(kind), path("${meta.id}.${kind}.summary.json"), emit: summary
    path "${meta.id}.${kind}.all.tsv", emit: all
    path "${meta.id}.${kind}.actionable.tsv", emit: actionable
    script:
    """
    summarize_somatic.py structural --input '${vcf}' --sample '${meta.id}' --kind '${kind}' --output-prefix '${meta.id}.${kind}' --cancer-db '${cancer_db}' --annotsv-annotations '${annotsv_annotations}' --cancer-type '${params.cancer_type}'
    """
}
