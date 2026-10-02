# WGS fastVEP branch validation

Date: 2026-10-01. Engine: fastVEP 0.3.0, upstream commit
`ac2e2b64a9c4c27163a3df16e0a559113af19625`; adapter 0.1.0.
Reference: platform hg38 FASTA, Ensembl 112 GFF3 and VEP 112 GRCh38 cache.
The live website has not been deployed from this branch.

## Completed checks

- Nine adapter unit tests passed, including allele-specific ClinVar, phased
  genotype preservation, peptide/gene matching, PICK, indels and failure checks.
- Thirty-eight downstream regression and shard-merge tests passed.
- Both complete germline and somatic Nextflow synthetic workflows passed,
  including real fastVEP annotation, empty shards, prioritization, oncogenicity
  and final summary. Somatic results require review and carry a pending benchmark.
- A non-patient smoke input with 173 upstream GRCh38 example variants plus BRAF
  V600E completed: 174 variants produced 1,593 transcript rows. ClinVar appeared
  in 675 rows, gnomAD genome AF in 1,519, CADD in 369, REVEL in 368,
  AlphaMissense in 201 and SpliceAI in 1,140. These are availability counts,
  not concordance measurements. Metadata came from VEP cache in 1,590 rows
  and GFF3-only models in 3 rows.
- Four simulated insertions/deletions at BRAF/BRCA1 coordinates completed after
  bcftools normalization, producing 84 transcript rows, 82 with HGVSc and 62
  with HGVSp. This verifies conversion, not equivalence with VEP.
- Annotation and backend Docker images built successfully. Backend versions:
  germline 0.4.0-fastvep and somatic 0.6.0-fastvep.

Local artifacts: `/tmp/mtb-fastvep-validation-20261001T094414` and
`/home/hpz8g5/project/fastvep-public-validation-20261001`.
Databases, generated reference caches and raw results are excluded from Git.
Reference preparation writes a SHA256 manifest separately.

## Before production rollout

A complete WGS comparison using the same normalized input with VEP 112 remains
required for HGVS, consequences, PICK, prediction availability, candidate lists,
classification, wall time and memory. SIFT/PolyPhen now use transcript-matched
dbNSFP. There are 2,118 GFF3-only transcripts with explicit fallback metadata,
and 1,640 cache-only transcripts absent from GFF3. The platform FASTA lacks
22 GFF3 scaffold aliases. Coverage policy and exact PICK ties require review.
Generic COSMIC/HGMD wildcard cache entries are not treated as exact allele
matches. No full-WGS speed improvement or clinical concordance is claimed.

Rollback: `WGS_ANNOTATION_ENGINE=vep` or baseline tag `pre-fastvep-20261001`.
See README.md for build and reference preparation instructions.

## Real-data reader correction (2026-10-02)

The dbNSFP source contains UTF-8 text in additional columns. Adapter 0.1.1
sets UTF-8 explicitly for tabix readers, avoiding the pysam ASCII default.
The synthetic source now includes non-ASCII text. Fourteen adapter/comparison
tests and 25 targeted downstream regression tests passed. Somatic summary
provenance retains the pending fastVEP benchmark status. These checks do not
establish clinical concordance for the new engine. Patient comparisons and
raw output remain in local directories outside Git.

Adapter 0.1.2 reads the cache's `chr_synonyms.txt` as a bidirectional alias graph,
including assembly accession names for non-primary contigs. Known non-primary
contigs absent from the cache retain their input variants and are explicitly
marked `variation_cache_unavailable_contig` in `ANNOTATION_DATA_STATUS`; summary
`variation_cache_unavailable_contigs` counts affected variants by contig. Missing
primary chromosomes, unknown contig names, and missing blocks still fail.
This behavior does not imply that missing ClinVar/gnomAD annotations were recovered.

The real-sample chr10 failures were caused by a truncated existing SpliceAI raw
indel BGZF file, not by a fastVEP consequence error. Do not suppress this read error
or substitute empty scores. Replacement sources must preserve raw GRCh38 scores,
pass their published checksums, and match readable original regions before use.
The comparison repair uses a separate chr10 data overlay; production databases
are not overwritten. The original indel frequency normalization limitation remains.
