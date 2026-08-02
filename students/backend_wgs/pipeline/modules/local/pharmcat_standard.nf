process PHARMCAT_STANDARD {
    tag "${meta.id}"
    publishDir { "${params.outdir}/${meta.id}/pharmcat" }, mode: 'copy', overwrite: true

    input:
    tuple val(meta), path(vcf)

    output:
    path "pharmcat_${meta.id}/**", emit: results

    script:
    """
    mkdir -p pharmcat_${meta.id}
    cp '${vcf}' pharmcat_${meta.id}/${meta.id}.vcf.gz
    cd pharmcat_${meta.id}
    pharmcat_pipeline '${meta.id}.vcf.gz'
    """
}
