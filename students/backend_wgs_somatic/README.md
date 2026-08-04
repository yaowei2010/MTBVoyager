# WGS Somatic Tumor-Only

Independent deterministic GRCh38 workflow for caller-produced SNV/Indel, SV and CNV VCFs.

Cancer evidence is matched locally without AI inference:

- OncoKB: exact GRCh38 chromosome/position/ref/alt.
- CIViC: exact GRCh38 coordinates or exact gene/protein change.
- CGI, COSMIC and MyCancerGenome: exact gene/protein change for SNV/Indel.
- SV/CNV: genes overlapping the local AnnotSV GRCh38 RefSeq intervals, followed by exact gene/event matching for amplification, deletion/loss or fusion.

GRCh37-only coordinates are never directly matched to GRCh38 calls. Every evidence item records its source and match method. Tumor-only results remain screening annotations and do not establish somatic origin or treatment eligibility.

Independent GRCh38 tumor-only workflow for caller-produced single-sample SNV,
SV and CNV VCFs. Nextflow owns validation, sample reheadering, SNV quality
filtering, parallel VEP annotation, deterministic evidence summaries and job
completion. Tumor-only results never assert that a variant is confirmed somatic.

The versioned pipeline is stored in `pipeline/` and is installed as an immutable
snapshot for each platform job.
