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
    if [[ \"\$sample_name\" != \"${meta.id}\" ]]; then
        echo \"Sample ID mismatch: samplesheet=${meta.id}, VCF=\$sample_name\" >&2
        exit 1
    fi
    ln -s '${vcf}' '${meta.id}.input.vcf.gz'
    records=\$(bcftools index -n '${vcf}' 2>/dev/null || bcftools view -H '${vcf}' | wc -l)
    cat > '${meta.id}.validation.json' <<JSON
{"sample_id":"${meta.id}","vcf_sample":"\$sample_name","sample_count":\$sample_count,"records":\$records,"status":"PASS"}
JSON
    bcftools --version | head -n 1 | awk '{print \"bcftools: \"\$2}' > versions.yml
    """
}
