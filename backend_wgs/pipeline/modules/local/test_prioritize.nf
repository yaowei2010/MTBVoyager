process TEST_PRIORITIZE {
    tag "${meta.id}"
    publishDir { "${params.outdir}/${meta.id}/candidates" }, mode: 'copy', overwrite: true

    input:
    tuple val(meta), path(vcf), path(gene_list)

    output:
    tuple val(meta), path("${meta.id}.prioritization.summary.json"), emit: summary

    script:
    """
    printf '{"all_candidates":0,"known_clinvar_plp":0,"phenotype_variants":0,"acmg_sf":0,"acmg_sf_inheritance_matched":0,"insilico":0}\n' > '${meta.id}.prioritization.summary.json'
    """
}
