nextflow.enable.dsl = 2

include { GERMLINE_SNV } from './workflows/germline_snv'

workflow {
    GERMLINE_SNV()
}
