process CALCULATE_ONCOGENICITY {
    tag "${meta.id}"
    label 'python'
    publishDir { "${params.outdir}/${meta.id}/oncogenicity" }, mode: 'copy', overwrite: true
    input:
    tuple val(meta), path(tsv)
    path oncovi_resources
    output:
    tuple val(meta), path("${meta.id}.oncogenicity.tsv.gz"), emit: tsv
    tuple val(meta), path("${meta.id}.oncogenicity.summary.json"), emit: summary
    script:
    """
    calculate_oncogenicity.py \
      --input '${tsv}' \
      --output '${meta.id}.oncogenicity.tsv.gz' \
      --summary '${meta.id}.oncogenicity.summary.json' \
      --resources '${oncovi_resources}' \
      --tumor-type '${params.cancer_type}'
    """
}
