process SPLIT_VCF_BY_CONTIG {
    tag "${meta.id}:${shard}"

    input:
    tuple val(meta), val(shard), path(vcf)

    output:
    tuple val(meta), val(shard), path("${meta.id}.${shard}.vcf.gz"), path("${meta.id}.${shard}.vcf.gz.tbi"), emit: vcf

    script:
    def primary = params.vep_contigs.split(',').collect { it.trim() }.findAll { it }
    def regions = shard == 'other' ? "^${primary.join(',')}" : shard
    """
    # --targets streams the input and therefore does not require every parallel
    # task to stage or rebuild the same tabix index.
    bcftools view --targets '${regions}' --output-type z --output '${meta.id}.${shard}.vcf.gz' '${vcf}'
    tabix -f -p vcf '${meta.id}.${shard}.vcf.gz'
    """
}
