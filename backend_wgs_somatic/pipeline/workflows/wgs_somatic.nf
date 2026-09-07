include { VALIDATE_INPUTS; VALIDATE_OPTIONAL_STRUCTURAL } from '../modules/local/validate_inputs'
include { FILTER_NORMALIZE_SNV } from '../modules/local/filter_normalize_snv'
include { SPLIT_VCF_BY_CONTIG } from '../modules/local/split_vcf_by_contig'
include { VEP_ANNOTATE_SHARD } from '../modules/local/vep_annotate'
include { MERGE_VEP_SHARDS } from '../modules/local/merge_vep_shards'
include { TEST_ANNOTATION } from '../modules/local/test_annotation'
include { CALCULATE_ONCOGENICITY } from '../modules/local/calculate_oncogenicity'
include { SUMMARIZE_SNV } from '../modules/local/summarize_snv'
include { SUMMARIZE_STRUCTURAL } from '../modules/local/summarize_structural'
include { FINALIZE_SOMATIC } from '../modules/local/finalize_somatic'
include { ESTIMATE_TMB } from '../modules/local/estimate_tmb'

workflow WGS_SOMATIC_TUMOR_ONLY {
    if (!params.input) error 'Missing --input samplesheet.csv'
    if (!params.reference) error 'Missing --reference GRCh38 FASTA'
    if (!params.cancer_db) error 'Missing --cancer_db directory'
    if (!params.annotsv_annotations) error 'Missing --annotsv_annotations directory'
    if (!params.oncovi_resources) error 'Missing --oncovi_resources directory'

    rows_ch = Channel.fromPath(params.input, checkIfExists: true).splitCsv(header: true).map { row ->
        if (!row.sample_id || !row.snv_vcf) {
            error 'samplesheet requires sample_id and snv_vcf; sv_vcf and cnv_vcf are optional'
        }
        if (!(row.sample_id ==~ /[A-Za-z0-9][A-Za-z0-9._-]*/)) error 'Invalid sample_id'
        row
    }
    samples_ch = rows_ch.map { row -> tuple([id: row.sample_id], file(row.snv_vcf, checkIfExists: true)) }
    optional_structural_ch = rows_ch.flatMap { row ->
        def inputs=[]
        if (row.sv_vcf?.trim()) inputs << tuple([id: row.sample_id], 'sv', file(row.sv_vcf, checkIfExists: true))
        if (row.cnv_vcf?.trim()) inputs << tuple([id: row.sample_id], 'cnv', file(row.cnv_vcf, checkIfExists: true))
        inputs
    }
    callable_ch = rows_ch.flatMap { row -> row.callable_regions?.trim() ? [tuple([id:row.sample_id],file(row.callable_regions,checkIfExists:true))] : [] }

    VALIDATE_INPUTS(samples_ch)
    VALIDATE_OPTIONAL_STRUCTURAL(optional_structural_ch)
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
    if (params.gencode_gtf) {
        tmb_inputs = callable_ch.join(SUMMARIZE_SNV.out.all,by:0).map { meta, callable, variants -> tuple(meta,callable,variants) }
        ESTIMATE_TMB(tmb_inputs,Channel.value(file(params.gencode_gtf,checkIfExists:true)))
    }
    SUMMARIZE_STRUCTURAL(VALIDATE_OPTIONAL_STRUCTURAL.out.vcf, cancer_db_ch, annotsv_annotations_ch)
    empty_structural_summary = file("${projectDir}/resources/empty_structural.json", checkIfExists: true)
    structural_collected_ch = SUMMARIZE_STRUCTURAL.out.summary.collect(flat:false)
        .map { summaries -> [items:summaries] }
        .ifEmpty([items:[[[id:'none'], 'none', empty_structural_summary]]])
    completion_ch = SUMMARIZE_SNV.out.summary.combine(structural_collected_ch).map { meta, snvSummary, structural ->
        tuple(meta, snvSummary, structural.items.collect { it[1] }, structural.items.collect { it[2] })
    }
    FINALIZE_SOMATIC(completion_ch)
}
