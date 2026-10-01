process PRIORITIZE_STRUCTURAL {
    tag "${meta.id}"
    publishDir { "${params.outdir}/${meta.id}/sv" }, mode: 'copy', overwrite: true

    input:
    tuple val(meta), path(sv_vcf), path(cnv_vcf), path(gene_list)

    output:
    path "${meta.id}.sv.known_pathogenic.tsv", emit: known
    path "${meta.id}.sv.acmg_sf.tsv", emit: acmg
    path "${meta.id}.cnv.input.vcf.gz", emit: cnv
    tuple val(meta), path("${meta.id}.structural.summary.json"), emit: summary

    script:
    """
    prioritize_structural.py \
      --sv '${sv_vcf}' --cnv '${cnv_vcf}' --sample '${meta.id}' \
      --output-prefix '${meta.id}' --acmg-genes '${params.acmg_genes}'
    """
}
