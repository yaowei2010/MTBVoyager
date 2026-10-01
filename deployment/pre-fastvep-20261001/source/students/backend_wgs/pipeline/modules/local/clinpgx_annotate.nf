process CLINPGX_ANNOTATE {
    tag "${meta.id}"
    publishDir { "${params.outdir}/${meta.id}/pharmcat/clinpgx" }, mode: 'copy', overwrite: true

    input:
    tuple val(meta), path(pharmcat_dir)
    path variant_annotations

    output:
    path "${meta.id}.clinpgx.*"

    script:
    """
    phenotype_json=\$(find '${pharmcat_dir}' -name '*.phenotype.json' -print -quit)
    test -n "\${phenotype_json}"
    annotate_clinpgx.py --pharmcat-phenotype "\${phenotype_json}" \
      --variant-annotations '${variant_annotations}' --sample '${meta.id}' \
      --release '${params.clinpgx_release}' --output-prefix '${meta.id}'
    """
}
