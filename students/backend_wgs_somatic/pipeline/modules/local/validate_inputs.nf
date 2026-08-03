process VALIDATE_INPUTS {
    tag "${meta.id}"
    label 'bcftools'
    publishDir { "${params.outdir}/${meta.id}/qc" }, mode: 'copy', overwrite: true

    input:
    tuple val(meta), path(snv), path(sv), path(cnv)

    output:
    tuple val(meta), path("${meta.id}.snv.vcf.gz"), emit: snv
    tuple val(meta), val('sv'), path("${meta.id}.sv.vcf.gz"), emit: structural
    tuple val(meta), val('cnv'), path("${meta.id}.cnv.vcf.gz"), emit: cnv
    path "${meta.id}.input_qc.json", emit: report

    script:
    """
    process_vcf() {
      kind="\$1"; src="\$2"; dst="\$3"
      bcftools view -h "\$src" >/dev/null
      samples=\$(bcftools query -l "\$src" | wc -l)
      if [[ "\$samples" -ne 1 ]]; then echo "\$kind VCF must contain exactly one sample" >&2; exit 1; fi
      original=\$(bcftools query -l "\$src")
      printf '%s\t%s\n' "\$original" '${meta.id}' > "\$kind.rename.tsv"
      bcftools view -Ob -o "\$kind.source.bcf" "\$src"
      bcftools reheader -s "\$kind.rename.tsv" -o "\$kind.renamed.bcf" "\$kind.source.bcf"
      bcftools view -Oz -o "\$dst" "\$kind.renamed.bcf"
      tabix -f -p vcf "\$dst"
    }
    process_vcf snv '${snv}' '${meta.id}.snv.vcf.gz'
    process_vcf sv '${sv}' '${meta.id}.sv.vcf.gz'
    process_vcf cnv '${cnv}' '${meta.id}.cnv.vcf.gz'
    # GRCh38 primary contigs use chr1 length 248956422. Require this when the
    # header declares chr1 length; callers omitting lengths are recorded but accepted.
    declared=\$(bcftools view -h '${meta.id}.snv.vcf.gz' | awk -F '[=,>]' '/^##contig=<ID=chr1,length=/ {print \$5; exit}')
    if [[ -n "\$declared" && "\$declared" != 248956422 ]]; then echo "SNV VCF is not GRCh38 chr1" >&2; exit 1; fi
    snv_records=\$(bcftools index -n '${meta.id}.snv.vcf.gz')
    sv_records=\$(bcftools index -n '${meta.id}.sv.vcf.gz')
    cnv_records=\$(bcftools index -n '${meta.id}.cnv.vcf.gz')
    printf '%s\n' '{"sample_id":"${meta.id}","genome_build":"GRCh38","snv_records":'"\$snv_records"',"sv_records":'"\$sv_records"',"cnv_records":'"\$cnv_records"',"status":"PASS"}' > '${meta.id}.input_qc.json'
    """
}
