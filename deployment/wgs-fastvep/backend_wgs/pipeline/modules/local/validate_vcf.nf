process VALIDATE_VCF {
    tag "${meta.id}"
    publishDir { "${params.outdir}/${meta.id}/qc" }, mode: 'copy', overwrite: true

    input:
    tuple val(meta), path(vcf), path(gene_list)

    output:
    tuple val(meta), path("${meta.id}.input.vcf.gz"), path(gene_list), emit: vcf
    tuple val(meta), path("${meta.id}.validation.json"), emit: report
    path 'versions.yml', emit: versions

    script:
    """
    bcftools view -h '${vcf}' >/dev/null
    sample_count=\$(bcftools query -l '${vcf}' | wc -l)
    sample_name=\$(bcftools query -l '${vcf}' | head -n 1)
    if [[ \"\$sample_count\" -ne 1 ]]; then
        echo \"Expected one sample, found \$sample_count\" >&2
        exit 1
    fi
    # The subject ID entered on the platform is authoritative. Preserve the
    # uploaded VCF header for audit, then reheader a normalized copy.
    printf '%s\t%s\n' \"\$sample_name\" '${meta.id}' > sample.rename.tsv
    bcftools view --output-type b --output source.bcf '${vcf}'
    bcftools reheader --samples sample.rename.tsv --output renamed.bcf source.bcf
    bcftools view --output-type z --output '${meta.id}.input.vcf.gz' renamed.bcf
    tabix -f -p vcf '${meta.id}.input.vcf.gz'
    renamed_sample=\$(bcftools query -l '${meta.id}.input.vcf.gz' | head -n 1)
    if [[ \"\$renamed_sample\" != \"${meta.id}\" ]]; then
        echo \"VCF reheader failed: expected ${meta.id}, found \$renamed_sample\" >&2
        exit 1
    fi
    records=\$(bcftools index -n '${vcf}' 2>/dev/null || bcftools view -H '${vcf}' | wc -l)
    cat > '${meta.id}.validation.json' <<JSON
{"sample_id":"${meta.id}","original_vcf_sample":"\$sample_name","vcf_sample":"\$renamed_sample","sample_count":\$sample_count,"records":\$records,"reheadered":true,"status":"PASS"}
JSON
    bcftools --version | head -n 1 | awk '{print \"bcftools: \"\$2}' > versions.yml
    """
}
