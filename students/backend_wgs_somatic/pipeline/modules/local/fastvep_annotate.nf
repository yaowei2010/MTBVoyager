process FASTVEP_ANNOTATE_SHARD {
    tag "${meta.id}:${shard}"
    publishDir { "${params.outdir}/${meta.id}/annotation/shards" }, mode: 'copy', overwrite: true

    input:
    tuple val(meta), val(shard), path(vcf), path(vcf_index)
    path reference
    path reference_fai
    path gff3
    path transcript_cache
    path transcript_metadata
    path cache
    path plugin_data

    output:
    tuple val(meta), val(shard), path("${meta.id}.${shard}.vep.tsv.gz"), emit: tsv
    tuple val(meta), val(shard), path("${meta.id}.${shard}.annotation.summary.json"), emit: summary

    script:
    """
    fastvep --version > fastvep.version.txt
    grep -q '0.3.0' fastvep.version.txt
    fastvep annotate \
        --input '${vcf}' --output annotations.json \
        --gff3 '${gff3}' --fasta '${reference}' \
        --transcript-cache '${transcript_cache}' \
        --hgvs --symbol --canonical --output-format json \
        --buffer-size ${params.buffer_size} --no-progress
    fastvep_to_mtb.py \
        --input-json annotations.json --vcf '${vcf}' \
        --output '${meta.id}.${shard}.vep.tsv.gz' \
        --summary '${meta.id}.${shard}.annotation.summary.json' \
        --plugin-data '${plugin_data}' \
        --variation-cache '${cache}/homo_sapiens/112_GRCh38' \
        --transcript-metadata '${transcript_metadata}'
    python -c "from pathlib import Path; Path('annotations.json').unlink()"
    """
}
