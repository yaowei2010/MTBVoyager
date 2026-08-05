process VEP_ANNOTATE_SHARD {
    tag "${meta.id}:${shard}"
    publishDir { "${params.outdir}/${meta.id}/annotation/shards" }, mode: 'copy', overwrite: true

    input:
    tuple val(meta), val(shard), path(vcf), path(vcf_index)
    path reference
    path cache
    path plugin_data

    output:
    tuple val(meta), val(shard), path("${meta.id}.${shard}.vep.tsv.gz"), emit: tsv
    tuple val(meta), val(shard), path("${meta.id}.${shard}.vep.summary.html"), emit: summary

    script:
    def pluginArgs = params.vep_plugin_args ? params.vep_plugin_args.split(';').collect { "--plugin '${it}'" }.join(' ') : ''
    """
    if [[ -z '${pluginArgs}' ]]; then
        echo 'No VEP plugin specifications configured; refusing annotation.' >&2
        exit 1
    fi
    vep \
        --input_file '${vcf}' \
        --output_file STDOUT \
        --format vcf \
        --tab --force_overwrite \
        --species homo_sapiens --assembly GRCh38 \
        --cache --offline --cache_version 112 \
        --dir_cache '${cache}' --fasta '${reference}' \
        --fork ${params.vep_fork_per_shard} --buffer_size ${params.buffer_size} \
        --everything --mane --canonical --appris --tsl --ccds \
        --hgvs --hgvsg --symbol --numbers --protein --uniprot \
        --flag_pick_allele_gene \
        --pick_order mane_select,mane_plus_clinical,canonical,appris,tsl,biotype,ccds,rank,length \
        --dir_plugins /plugins \
        ${pluginArgs} \
        --stats_file '${meta.id}.${shard}.vep.summary.html' | \
      gzip -c > '${meta.id}.${shard}.vep.tsv.gz'
    """
}

