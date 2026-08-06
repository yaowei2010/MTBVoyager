process PRIORITIZE_VARIANTS {
    tag "${meta.id}"
    publishDir { "${params.outdir}/${meta.id}/candidates" }, mode: 'copy', overwrite: true

    input:
    tuple val(meta), path(vep_tsv), path(gene_list)

    output:
    path "${meta.id}.all_candidates.tsv", emit: all
    path "${meta.id}.known_clinvar_plp.tsv", emit: known
    path "${meta.id}.phenotype_variants.tsv", emit: phenotype
    path "${meta.id}.acmg_sf.tsv", emit: acmg
    path "${meta.id}.insilico.tsv", emit: insilico
    tuple val(meta), path("${meta.id}.prioritization.summary.json"), emit: summary

    script:
    """
    prioritize_variants.py \
        --input '${vep_tsv}' \
        --sample '${meta.id}' \
        --output-prefix '${meta.id}' \
        --population '${params.population}' \
        --population-af-max ${params.population_af_max} \
        --predictor-min ${params.predictor_min} \
        --acmg-genes '${params.acmg_genes}' \
        ${gene_list ? "--gene-list '${gene_list}'" : ''}
    """
}
