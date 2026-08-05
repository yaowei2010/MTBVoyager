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

## Deterministic oncogenicity classification

SNV and small-indel VEP results are scored with the ClinGen/CGC/VICC 2022
oncogenicity point system before cancer-database matching. The implementation is
deterministic and emits the score, classification, applied criteria, manual-review
flag, and per-criterion audit JSON. It does not use generative AI inference.

The `strict_sop_2022_with_oncovi_2026_resources` profile uses selected resources
from OncoVI (DOI `10.1016/j.jmoldx.2026.03.004`) pinned to upstream commit
`99fa5801163bb6bd32d97e916ca2249bb9429d81`. Intentional differences from the
upstream reference implementation are recorded in
`pipeline/resources/oncovi_manifest.json`; in particular, missing functional
evidence is `not_assessable` and germline ClinVar is not substituted for OS2/SBS2.
The classification applies only to SNV/small indels, not general SV, CNV, or fusions.

Each row also includes an `oncovi_2026_*` compatibility result following the
operational decisions in pinned upstream commit `99fa580`, alongside a criteria
difference list. On the frozen official 93-variant example, final classification
reproduction was 93/93, exact score 86/93, and exact criteria set 85/93 using the
platform VEP 112 annotation stack. The versioned report is under
`pipeline/validation/`; this classification-reproduction result is distinct from
the paper's accuracy against manually curated SOP ground truth. The remaining
OM3/OM4 differences are recorded as frozen-output/resource drift.

The platform also exposes programmatic oncogenicity annotation for legacy
Tumor-Only results at `POST /wgs-somatic/legacy-oncogenicity`. It persists a TSV
and JSON summary beside the old result. Since that input contains GRCh37/hg19
gene/protein annotations instead of complete GRCh38 VEP fields, unavailable
evidence is never inferred and every legacy result is marked for manual review.
