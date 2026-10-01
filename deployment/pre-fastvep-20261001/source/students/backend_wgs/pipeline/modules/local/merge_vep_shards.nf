process MERGE_VEP_SHARDS {
    tag "${meta.id}"
    publishDir { "${params.outdir}/${meta.id}/annotation" }, mode: 'copy', overwrite: true

    input:
    tuple val(meta), val(shard_names), path(shard_tsvs), path(gene_list)

    output:
    tuple val(meta), path("${meta.id}.vep.tsv.gz"), path(gene_list), emit: tsv

    script:
    """
    merge_vep_shards.py --sample '${meta.id}' --output '${meta.id}.vep.tsv.gz' ${shard_tsvs.collect { "'${it}'" }.join(' ')}
    """
}

