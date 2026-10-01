# WGS fastVEP update branch

The germline (`0.4.0-fastvep`) and somatic (`0.6.0-fastvep`) pipelines support
`--annotation_engine fastvep|vep`, with fastVEP as the new branch default.
This branch has not been deployed to the live website.

## Annotation contract

`FASTVEP_ANNOTATE_SHARD` runs pinned fastVEP 0.3.0 (`ac2e2b6`) on each normalized,
single-ALT shard, then streams its JSON through `fastvep_to_mtb.py`. Outputs keep
the existing `.vep.tsv.gz` filenames for the current downstream consumers, with
an explicit `ANNOTATION_ENGINE=fastvep` column. Every input record must match an
output record in order, coordinates and alleles. Genotype and sample identity
come from the normalized VCF. PICK is marked per allele/gene; all transcripts
are retained. Empty shards still emit the complete schema.

The adapter reuses the existing GRCh38 indexed plugin files and reads VEP's
original one-million-base variation gzip blocks for ClinVar and gnomAD. It does
not invoke Ensembl VEP for consequences or HGVS and does not mutate the source
databases. Missing databases, indexes, required headers, chromosome cache blocks
or transcript metadata fail the task. Per-task JSON summaries record sources,
cache releases, missing-value counts and transcript metadata provenance.

Baseline transcript metadata is exported once from the VEP 112 transcript
cache. Transcripts present only in GFF3 are retained with
`TRANSCRIPT_METADATA_SOURCE=gff3_only`, not silently represented as equivalent
to the old cache. Protein-length and APPRIS/TSL selection data are retained for
the cached transcripts. Exact ranking ties use transcript ID as a deterministic
final tie-break and need comparison against the old VEP behavior.

## Build and prepare reference data

The pinned standalone image `mtb-fastvep:0.3.0-ac2e2b6` must already exist locally
(build instructions are in `/home/hpz8g5/tools/fastVEP/README.md`). From MTB:

```bash
docker build -t mtb-wgs-fastvep:0.1.0 students/wgs_annotation
bash students/wgs_annotation/prepare_reference.sh
```

The preparation script uses the website's reference FASTA, Ensembl 112 GFF3 and
the current cache. It writes only new fastVEP reference artifacts, including a
SHA256 manifest; raw annotation databases stay in their current locations.
Paths may be overridden with `FASTVEP_REFERENCE_ROOT`, `WGS_REFERENCE_FASTA`
and `WGS_VEP_CACHE`. Rebuild reference artifacts whenever an input changes.

## Website deployment configuration

Both runners now pass the annotation-engine parameters. The feature branch's
Compose configuration mounts fastVEP references at the same absolute host and
backend path because Nextflow launches tasks through the host Docker daemon.
Use the source packaged in `deployment/wgs-fastvep` of the GitHub feature branch
for reproducible build contexts. Set `MTB_SOURCE_ROOT` only to deliberately build
from a different source checkout.

Environment variables:

- `WGS_ANNOTATION_ENGINE`: `fastvep` or `vep`.
- `WGS_FASTVEP_IMAGE`: annotation image, default `mtb-wgs-fastvep:0.1.0`.
- `FASTVEP_REFERENCE_ROOT`: host reference directory for Compose.
- `WGS_FASTVEP_GFF3`, `WGS_FASTVEP_TRANSCRIPT_CACHE`,
  `WGS_FASTVEP_TRANSCRIPT_METADATA`: optional per-file runner overrides.
- `WGS_FASTVEP_MAX_PARALLEL`, `WGS_FASTVEP_CPUS`, `WGS_FASTVEP_MEMORY`: default
  two shards, eight CPUs and 20 GB per shard. These are initial allocations,
  not full-WGS performance tuning results.
- The existing `WGS_VEP_CACHE` and `WGS_VEP_PLUGIN_DATA` remain required as data
  sources. `WGS_VEP_PLUGIN_ARGS` is used only by the rollback VEP engine.

The backend image must be rebuilt to include both new pipeline VERSION files
and runner modules. Updating source without rebuilding the image is insufficient.
Old installed pipeline version directories and historical jobs are preserved.
The fastVEP web/API server is not required. SV/CNV, PharmCAT and ClinPGx retain
their existing workflows.

## Validation

```bash
docker run --rm --network none \
  -v "$PWD/students/wgs_annotation:/src:ro" mtb-wgs-fastvep:0.1.0 \
  python -m unittest discover -s /src/tests -v
bash students/wgs_annotation/validation/run_synthetic.sh
```

The synthetic integration script executes both complete Nextflow workflows,
including real fastVEP annotation, adapter conversion, candidate prioritization,
oncogenicity and finalization. It also covers an empty `other` shard. Fixtures
contain no patient data. Regression tests for existing downstream rules should
be run with the MONDO fixtures mounted at the expected repository path.

## Remaining production validation

- SIFT/PolyPhen now use transcript-matched dbNSFP predictions, rather than
  predictions bundled with VEP transcript objects. Availability and numerical
  values can differ. The predictor thresholds themselves are unchanged.
- GFF3 and cache transcript sets differ. GFF-only rows and exact PICK ties need
  review on the same normalized input; not every old cache transcript exists
  in the GFF3 model.
- The existing platform FASTA lacks 22 GFF3 scaffold aliases. fastVEP warns about
  them when loading the full cache. Primary-chromosome smoke tests work; inputs
  on those scaffolds need an explicit reference-coverage policy before rollout.
- ClinVar uses the current VEP cache release (202310), with allele-specific
  assertions, preserving the staged source rather than introducing a silent
  ClinVar update. Existing cache fields do not provide review-star status.
- HGVS differences and indel equivalence need full comparison against VEP 112.
- The somatic output records `pending_fastvep_annotation_benchmark` and requires
  review for fastVEP results; it does not claim that the old 93-case benchmark
  validates the new annotation engine. Scoring rules remain unchanged.
- Full-WGS wall time, memory and downstream candidate/classification agreement
  are not yet established. The previous standalone six-minute run excluded this
  compatibility adapter and the full supplementary-data workload.

Use `WGS_ANNOTATION_ENGINE=vep` to return to the old consequence caller in this
branch. The complete pre-migration GitHub baseline is tagged
`pre-fastvep-20261001`. Do not recreate the live backend while jobs are active.
