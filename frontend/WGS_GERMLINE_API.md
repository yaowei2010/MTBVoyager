# WGS germline frontend API contract

The React pages under `src/component/Analysis/WGS_Germline` and
`src/component/Job_results/WGS_Germline_Detail` expect these endpoints under
`config.rootApiIP`.

## Analysis setup

- `POST /wgs-germline/subject`: saves subject metadata and returns `draft_id`.
- `POST /wgs-germline/upload`: multipart upload with `snv`, `sv`, `cnv`, and
  `draft_id`; returns `upload_id`.
- `GET /wgs-germline/mondo/search?q=...&limit=20`: returns `results`, each with
  `id`, `label`, optional `synonyms`, and optional `gene_count`.
- `POST /wgs-germline/jobs`: starts the analysis. The request includes the
  upload identifiers, `population`, filters, selected MONDO terms, and
  `phenotype_include_descendants`.

The backend must resolve and persist the actual MONDO/Monarch human gene set
used by the job, together with the MONDO and Monarch data release versions.

## Result endpoints

- `GET /wgs-germline/jobs/:analysisId`
- `GET /wgs-germline/jobs/:analysisId/snv?category=phenotype`
- `GET /wgs-germline/jobs/:analysisId/snv?category=known_pathogenic`
- `GET /wgs-germline/jobs/:analysisId/snv?category=acmg_sf`
- `GET /wgs-germline/jobs/:analysisId/snv?category=in_silico`
- `GET /wgs-germline/jobs/:analysisId/sv?category=known_pathogenic`
- `GET /wgs-germline/jobs/:analysisId/sv?category=acmg_sf`
- `GET /wgs-germline/jobs/:analysisId/pharmcat`

List endpoints may return an array directly or `{ "results": [...] }`.

## Pathogenic categories

The backend, rather than the browser, owns clinical classification. Normalize
ClinVar assertions before generating the result categories.

An eligible pathogenic variant is P, LP, or P/LP, has no conflicting
classification, and has a valid assertion (exclude no assertion, no assertion
criteria, and no classification). Preserve the raw clinical significance,
review status, review stars, conflict flag, evaluation date, and ClinVar ID in
the response.

- `phenotype`: eligible pathogenic variants whose gene is in the resolved
  MONDO/Monarch gene set.
- `known_pathogenic`: all eligible pathogenic variants, regardless of the
  selected phenotype. This intentionally includes the phenotype subset.

Do not return pre-rendered HTML. All result endpoints must return JSON for the
React/MUI tables.
