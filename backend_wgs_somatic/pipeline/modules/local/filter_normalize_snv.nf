process FILTER_NORMALIZE_SNV {
    tag "${meta.id}"
    label 'bcftools'
    publishDir { "${params.outdir}/${meta.id}/snv" }, mode: 'copy', overwrite: true

    input:
    tuple val(meta), path(vcf)
    path reference
    path reference_fai

    output:
    tuple val(meta), path("${meta.id}.somatic.filtered.vcf.gz"), emit: vcf
    path "${meta.id}.somatic.filtered.vcf.gz.tbi", emit: index
    path "${meta.id}.quality_filter.json", emit: report

    script:
    """
    expr='${params.pass_only.toString().toBoolean() ? "FILTER=\"PASS\"" : "1"}'
    header=\$(bcftools view -h '${vcf}')
    if grep -q '^##FORMAT=<ID=DP,' <<<"\$header"; then expr="\$expr && FMT/DP>=${params.dp_min}"; fi
    if grep -q '^##FORMAT=<ID=AD,' <<<"\$header"; then
      expr="\$expr && FMT/AD[0:1]>=${params.alt_reads_min} && FMT/AD[0:1]/FMT/DP>=${params.vaf_min}"
    elif grep -q '^##FORMAT=<ID=AF,' <<<"\$header"; then
      expr="\$expr && FMT/AF[0]>=${params.vaf_min}"
    elif grep -q '^##FORMAT=<ID=VAF,' <<<"\$header"; then
      expr="\$expr && FMT/VAF[0]>=${params.vaf_min}"
    fi
    bcftools norm -f '${reference}' -m -any -Ou '${vcf}' | \
      bcftools view -i "\$expr" -Oz -o '${meta.id}.somatic.filtered.vcf.gz'
    tabix -f -p vcf '${meta.id}.somatic.filtered.vcf.gz'
    retained=\$(bcftools index -n '${meta.id}.somatic.filtered.vcf.gz')
    printf '%s\n' '{"sample_id":"${meta.id}","stage":"pre_vep","pass_only":${params.pass_only.toString().toBoolean()},"dp_min":${params.dp_min},"alt_reads_min":${params.alt_reads_min},"vaf_min":${params.vaf_min},"retained_records":'"\$retained"',"status":"PASS"}' > '${meta.id}.quality_filter.json'
    """
}
