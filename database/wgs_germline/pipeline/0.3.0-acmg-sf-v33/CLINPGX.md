# ClinPGx allele–drug annotation

This workflow adds a deterministic evidence layer to the PharmCAT result. It
does not use AI, NLP, or free-text inference. A ClinPGx annotation is reported
as `allele_match` only when a structured allele/genotype field matches the
PharmCAT call. Records without a structured allele are retained as
`variant_match_allele_unresolved` and must not be interpreted as patient-level
drug response.

## Build a versioned snapshot

Run this separately from patient analysis. No patient data is sent to ClinPGx.

```bash
bin/sync_clinpgx.py --output /path/to/clinpgx --release YYYY-MM-DD
```

The snapshot records source, retrieval time, attribution, and CC BY-SA 4.0
license information. ClinPGx asks API clients to stay below two requests per
second; the sync command enforces that limit.

## Nextflow parameters

```text
--clinpgx_variant_annotations /path/to/variantAnnotation.json
--clinpgx_clinical_annotations /path/to/clinicalAnnotation.json
--clinpgx_release YYYY-MM-DD
```

All three parameters must identify the same frozen release. Outputs are written
under `<sample>/pharmcat/clinpgx/`:

- `<sample>.clinpgx.tsv`: review-friendly allele–drug evidence
- `<sample>.clinpgx.json`: structured evidence plus summary
- `<sample>.clinpgx.summary.json`: counts and explicit `ai_inference: false`

Clinical prescribing recommendations remain the responsibility of PharmCAT's
CPIC/DPWG/FDA report. Variant annotations are supporting study evidence and can
be conflicting; the workflow does not collapse them into a synthetic
"tolerant/not tolerant" label.
