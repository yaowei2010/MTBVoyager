# WGS Somatic Tumor-Only

Independent GRCh38 tumor-only workflow for caller-produced single-sample SNV,
SV and CNV VCFs. Nextflow owns validation, sample reheadering, SNV quality
filtering, parallel VEP annotation, deterministic evidence summaries and job
completion. Tumor-only results never assert that a variant is confirmed somatic.

The versioned pipeline is stored in `pipeline/` and is installed as an immutable
snapshot for each platform job.
