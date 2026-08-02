process CLINPGX_ANNOTATE {
    tag "${meta.id}"
    publishDir { "${params.outdir}/${meta.id}/pharmcat/clinpgx" }, mode: 'copy', overwrite: true

    input:
    tuple val(meta), path(pharmcat_dir)
    path variant_annotations
    path clinical_annotations

    output:
    tuple val(meta), path("${meta.id}.clinpgx.tsv"), emit: tsv
    tuple val(meta), path("${meta.id}.clinpgx.json"), emit: json
    tuple val(meta), path("${meta.id}.clinpgx.summary.json"), emit: summary

    script:
    """
    phenotype_json=\$(find '${pharmcat_dir}' -maxdepth 1 -name '*.phenotype.json' -print -quit)
    test -n "\${phenotype_json}"
    annotate_clinpgx.py \
        --pharmcat-phenotype "\${phenotype_json}" \
        --variant-annotations '${variant_annotations}' \
        --clinical-annotations '${clinical_annotations}' \
        --sample '${meta.id}' --release '${params.clinpgx_release}' \
        --output-prefix '${meta.id}'
    """
}
