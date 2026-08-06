process NORMALIZE_VCF {
    tag "${meta.id}"
    publishDir { "${params.outdir}/${meta.id}/normalized" }, mode: 'copy', overwrite: true

    input:
    tuple val(meta), path(vcf), path(gene_list)
    path reference
    path reference_fai

    output:
    tuple val(meta), path("${meta.id}.normalized.vcf.gz"), path(gene_list), emit: vcf
    path "${meta.id}.normalized.vcf.gz.tbi", emit: index
    path "${meta.id}.normalization.stats.txt", emit: stats
    path "${meta.id}.excluded_contigs.txt", emit: excluded_contigs

    script:
    """
    # DRAGEN HLA calling can add allele-named contigs that do not exist in the
    # baseline FASTA. Normalize only the VCF/FASTA contig intersection and keep
    # an explicit audit file listing everything excluded.
    bcftools view -h '${vcf}' | \
        sed -n 's/^##contig=<ID=\\([^,>]*\\).*/\\1/p' | \
        sort -u > vcf.contigs.txt
    cut -f1 '${reference_fai}' | sort -u > reference.contigs.txt
    comm -12 vcf.contigs.txt reference.contigs.txt > compatible.contigs.txt
    comm -23 vcf.contigs.txt reference.contigs.txt > '${meta.id}.excluded_contigs.txt'
    awk 'NR==FNR { keep[\$1]=1; next } (\$1 in keep) { print \$1 "\t0\t" \$2 }' \
        compatible.contigs.txt '${reference_fai}' > compatible_contigs.bed

    if [[ ! -s compatible.contigs.txt ]]; then
        echo 'VCF and reference FASTA have no contigs in common' >&2
        exit 1
    fi

    filter_expr='${params.pass_only.toString().toBoolean() ? "FILTER=\"PASS\" && " : ""}GT!="mis" && FORMAT/DP>=${params.dp_min} && FORMAT/GQ>=${params.gq_min}'
    if bcftools view -h '${vcf}' | grep -q '^##FORMAT=<ID=AD,'; then
        filter_expr="\${filter_expr} && FORMAT/AD[0:1]/FORMAT/DP>=${params.vaf_min}"
    fi

    bcftools view \
        --targets-file compatible_contigs.bed \
        --output-type u '${vcf}' | \
    bcftools norm \
        --fasta-ref '${reference}' \
        --multiallelics -any \
        --check-ref warn \
        --output-type u | \
    bcftools view \
        --include "\${filter_expr}" \
        --output-type z \
        --output '${meta.id}.normalized.vcf.gz'
    tabix -f -p vcf '${meta.id}.normalized.vcf.gz'
    bcftools stats '${meta.id}.normalized.vcf.gz' > '${meta.id}.normalization.stats.txt'
    """
}
