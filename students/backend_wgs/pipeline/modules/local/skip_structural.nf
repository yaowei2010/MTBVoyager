process SKIP_STRUCTURAL {
    tag "${meta.id}"
    publishDir { "${params.outdir}/${meta.id}/sv" }, mode: 'copy', overwrite: true

    input:
    val(meta)

    output:
    tuple val(meta), path("${meta.id}.structural.summary.json"), emit: summary

    script:
    """
    printf '%s\n' '{"sample_id":"${meta.id}","status":"skipped","reason":"SV and CNV analysis was not requested"}' > '${meta.id}.structural.summary.json'
    """
}
