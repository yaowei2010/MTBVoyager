process SUMMARIZE_SNV {
    tag "${meta.id}"
    label 'python'
    publishDir { "${params.outdir}/${meta.id}/interpretation" }, mode: 'copy', overwrite: true
    input:
    tuple val(meta), path(tsv)
    path cancer_db
    output:
    tuple val(meta), path("${meta.id}.snv.summary.json"), emit: summary
    path "${meta.id}.snv.all.tsv", emit: all
    path "${meta.id}.snv.actionable.tsv", emit: actionable
    path "${meta.id}.snv.oncogenic.tsv", emit: oncogenic
    path "${meta.id}.snv.possible_germline.tsv", emit: possible_germline
    script:
    """
    summarize_somatic.py snv --input '${tsv}' --sample '${meta.id}' --output-prefix '${meta.id}' --population-af-max '${params.population_af_max}' --cancer-db '${cancer_db}' --cancer-type '${params.cancer_type}'
    """
}
