include { VALIDATE_INPUTS } from '../modules/local/validate_inputs'
include { FILTER_NORMALIZE_SNV } from '../modules/local/filter_normalize_snv'
include { SPLIT_VCF_BY_CONTIG } from '../modules/local/split_vcf_by_contig'
include { VEP_ANNOTATE_SHARD } from '../modules/local/vep_annotate'
include { MERGE_VEP_SHARDS } from '../modules/local/merge_vep_shards'
include { TEST_ANNOTATION } from '../modules/local/test_annotation'
include { CALCULATE_ONCOGENICITY } from '../modules/local/calculate_oncogenicity'
include { SUMMARIZE_SNV } from '../modules/local/summarize_snv'
include { SUMMARIZE_STRUCTURAL } from '../modules/local/summarize_structural'
include { FINALIZE_SOMATIC } from '../modules/local/finalize_somatic'

workflow WGS_SOMATIC_TUMOR_ONLY {
    if (!params.input) error 'Missing --input samplesheet.csv'
    if (!params.reference) error 'Missing --reference GRCh38 FASTA'
    if (!params.cancer_db) error 'Missing --cancer_db directory'
    if (!params.annotsv_annotations) error 'Missing --annotsv_annotations directory'
    if (!params.oncovi_resources) error 'Missing --oncovi_resources directory'

    Channel.fromPath(params.input, checkIfExists: true).splitCsv(header: true).map { row ->
        if (!row.sample_id || !row.snv_vcf || !row.sv_vcf || !row.cnv_vcf) {
            error 'samplesheet requires sample_id,snv_vcf,sv_vcf,cnv_vcf'
        }
        if (!(row.sample_id ==~ /[A-Za-z0-9][A-Za-z0-9._-]*/)) error 'Invalid sample_id'
        tuple([id: row.sample_id], file(row.snv_vcf, checkIfExists: true),
              file(row.sv_vcf, checkIfExists: true), file(row.cnv_vcf, checkIfExists: true))
    }.set { samples_ch }

    VALIDATE_INPUTS(samples_ch)
    reference_ch = Channel.value(file(params.reference, checkIfExists: true))
    reference_fai_ch = Channel.value(file("${params.reference}.fai", checkIfExists: true))
    cancer_db_ch = Channel.value(file(params.cancer_db, checkIfExists: true, type: 'dir'))
    annotsv_annotations_ch = Channel.value(file(params.annotsv_annotations, checkIfExists: true, type: 'dir'))
    oncovi_resources_ch = Channel.value(file(params.oncovi_resources, checkIfExists: true, type: 'dir'))
    FILTER_NORMALIZE_SNV(VALIDATE_INPUTS.out.snv, reference_ch, reference_fai_ch)

    if (params.skip_vep.toString().toBoolean()) {
        TEST_ANNOTATION(FILTER_NORMALIZE_SNV.out.vcf)
        annotation_ch = TEST_ANNOTATION.out.tsv
    } else {
        if (!params.vep_cache || !params.vep_plugin_data) error 'VEP cache and plugin data are required'
        cache_ch = Channel.value(file(params.vep_cache, checkIfExists: true))
        plugin_ch = Channel.value(file(params.vep_plugin_data, checkIfExists: true, type: 'dir'))
        def shards = params.vep_contigs.split(',').collect { it.trim() }.findAll { it } + ['other']
        shard_ch = FILTER_NORMALIZE_SNV.out.vcf.flatMap { meta, vcf -> shards.collect { tuple(meta, it, vcf) } }
        SPLIT_VCF_BY_CONTIG(shard_ch)
        VEP_ANNOTATE_SHARD(SPLIT_VCF_BY_CONTIG.out.vcf, reference_ch, cache_ch, plugin_ch)
        grouped_ch = VEP_ANNOTATE_SHARD.out.tsv.groupTuple(by: 0)
        MERGE_VEP_SHARDS(grouped_ch)
        annotation_ch = MERGE_VEP_SHARDS.out.tsv
    }

    CALCULATE_ONCOGENICITY(annotation_ch, oncovi_resources_ch)
    SUMMARIZE_SNV(CALCULATE_ONCOGENICITY.out.tsv, cancer_db_ch)
    structural_ch = VALIDATE_INPUTS.out.structural.mix(VALIDATE_INPUTS.out.cnv)
    SUMMARIZE_STRUCTURAL(structural_ch, cancer_db_ch, annotsv_annotations_ch)
    structural_grouped = SUMMARIZE_STRUCTURAL.out.summary.groupTuple(by: 0).map { meta, kinds, files -> tuple(meta, kinds, files) }
    completion_ch = SUMMARIZE_SNV.out.summary.join(structural_grouped)
        .map { meta, snvSummary, kinds, structuralSummaries -> tuple(meta, snvSummary, kinds, structuralSummaries) }
    FINALIZE_SOMATIC(completion_ch)
}
