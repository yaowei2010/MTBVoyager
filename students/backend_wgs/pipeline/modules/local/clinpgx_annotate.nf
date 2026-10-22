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
    # Nextflow stages a directory input as a symlink; follow it to locate
    # PharmCAT's phenotype JSON inside the published directory.
    phenotype_json=\$(find -L '${pharmcat_dir}' -name '*.phenotype.json' -print -quit)
    test -n "\${phenotype_json}"
    annotate_clinpgx.py --pharmcat-phenotype "\${phenotype_json}" \
      --variant-annotations '${variant_annotations}' --sample '${meta.id}' \
      --release '${params.clinpgx_release}' --output-prefix '${meta.id}'
    """
}
