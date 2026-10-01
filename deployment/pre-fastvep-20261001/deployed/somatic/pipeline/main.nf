nextflow.enable.dsl = 2

include { WGS_SOMATIC_TUMOR_ONLY } from './workflows/wgs_somatic'

workflow {
    WGS_SOMATIC_TUMOR_ONLY()
}
