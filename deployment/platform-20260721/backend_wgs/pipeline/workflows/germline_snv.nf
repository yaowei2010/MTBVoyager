include { VALIDATE_VCF } from '../modules/local/validate_vcf'
include { NORMALIZE_VCF } from '../modules/local/normalize_vcf'
include { SPLIT_VCF_BY_CONTIG } from '../modules/local/split_vcf_by_contig'
include { VEP_ANNOTATE_SHARD } from '../modules/local/vep_annotate'
include { MERGE_VEP_SHARDS } from '../modules/local/merge_vep_shards'
include { PRIORITIZE_VARIANTS } from '../modules/local/prioritize_variants'
include { PRIORITIZE_STRUCTURAL } from '../modules/local/prioritize_structural'
include { PHARMCAT_STANDARD } from '../modules/local/pharmcat_standard'
include { FINALIZE } from '../modules/local/finalize'
include { TEST_PRIORITIZE } from '../modules/local/test_prioritize'

workflow GERMLINE_SNV {
    if (!params.input) error "Missing --input samplesheet.csv"
    def skipVep = params.skip_vep.toString().toBoolean()
    def skipPharmcat = params.skip_pharmcat.toString().toBoolean()

    Channel.fromPath(params.input, checkIfExists: true)
        .splitCsv(header: true)
        .map { row ->
            if (!row.sample_id || !row.snv_vcf || !row.sv_vcf || !row.cnv_vcf) {
                error "samplesheet requires sample_id, snv_vcf, sv_vcf and cnv_vcf"
            }
            def meta = [id: row.sample_id, sex: row.sex ?: 'unknown']
            def geneList = row.gene_list ? file(row.gene_list, checkIfExists: true) : []
            tuple(meta, file(row.snv_vcf, checkIfExists: true), file(row.sv_vcf, checkIfExists: true), file(row.cnv_vcf, checkIfExists: true), geneList)
        }
        .set { all_samples_ch }

    snv_samples_ch = all_samples_ch.map { meta, snv, sv, cnv, genes -> tuple(meta, snv, genes) }
    structural_ch = all_samples_ch.map { meta, snv, sv, cnv, genes -> tuple(meta, sv, cnv, genes) }
    PRIORITIZE_STRUCTURAL(structural_ch)
    VALIDATE_VCF(snv_samples_ch)

    if (!params.reference) error "Missing --reference GRCh38 FASTA"
    reference_ch = Channel.value(file(params.reference, checkIfExists: true))
    reference_fai_ch = Channel.value(file("${params.reference}.fai", checkIfExists: true))
    NORMALIZE_VCF(VALIDATE_VCF.out.vcf, reference_ch, reference_fai_ch)

    if (skipVep) {
        TEST_PRIORITIZE(NORMALIZE_VCF.out.vcf)
        snv_summary_ch = TEST_PRIORITIZE.out.summary
    } else {
        if (!params.vep_cache || !params.vep_plugin_data) error "VEP cache and plugin data are required"
        cache_ch = Channel.value(file(params.vep_cache, checkIfExists: true))
        plugin_data_ch = Channel.value(file(params.vep_plugin_data, checkIfExists: true, type: 'dir'))
        def shards = params.vep_contigs.split(',').collect { it.trim() }.findAll { it } + ['other']
        vep_gene_ch = NORMALIZE_VCF.out.vcf.map { meta, vcf, geneList -> tuple(meta, geneList) }
        vep_shard_input_ch = NORMALIZE_VCF.out.vcf.flatMap { meta, vcf, geneList ->
            shards.collect { shard -> tuple(meta, shard, vcf) }
        }
        SPLIT_VCF_BY_CONTIG(vep_shard_input_ch)
        VEP_ANNOTATE_SHARD(SPLIT_VCF_BY_CONTIG.out.vcf, reference_ch, cache_ch, plugin_data_ch)
        vep_grouped_ch = VEP_ANNOTATE_SHARD.out.tsv.groupTuple(by: 0)
        vep_merge_input_ch = vep_grouped_ch
            .join(vep_gene_ch)
            .map { meta, shardNames, shardTsvs, geneList -> tuple(meta, shardNames, shardTsvs, geneList) }
        MERGE_VEP_SHARDS(vep_merge_input_ch)
        PRIORITIZE_VARIANTS(MERGE_VEP_SHARDS.out.tsv)
        snv_summary_ch = PRIORITIZE_VARIANTS.out.summary
    }

    if (!skipPharmcat) {
        pharmcatInput = VALIDATE_VCF.out.vcf.map { meta, vcf, geneList -> tuple(meta, vcf) }
        PHARMCAT_STANDARD(pharmcatInput)
    }

    completion_ch = snv_summary_ch
        .join(PRIORITIZE_STRUCTURAL.out.summary)
        .map { meta, snv_summary, structural_summary -> tuple(meta, snv_summary, structural_summary) }
    FINALIZE(completion_ch)
}
