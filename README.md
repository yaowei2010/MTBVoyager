# MTB platform source backup — 2026-08-05

This directory is a source-code snapshot of the MTB platform deployed at
`140.116.66.190` on 2026-08-05 (UTC). It is intended for version recovery and
rebuilding the application containers.

## Included

- `backend_legacy/`: legacy Django Somatic/MTB code extracted from the running
  backend container, including the fixed Somatic job-status handling.
- `backend_wgs/`: WGS Germline API and Nextflow workflow source.
- `backend_wgs_somatic/`: WGS Somatic Tumor-Only API and Nextflow workflow.
- `frontend/`: React source, public assets, package manifests, and Dockerfiles.
- `deployment/`: Docker Compose, nginx/gateway configuration, and sanitized
  environment examples.

## Deliberately excluded

- PostgreSQL and SQLite databases, SQL dumps, database volumes.
- Uploaded patient data, `media`, job inputs/results, Nextflow `work`, reports,
  timelines, traces, and logs.
- Annotation/reference databases, language models, and prediction model files.
- `node_modules`, compiled frontend `build`, Python caches, and bundled
  Nextflow executables.
- `.env`, TLS private keys, passwords, tokens, and Django secret keys.

Legacy source strings containing the deployed database password or Django
secret were replaced with `REDACTED_SET_VIA_ENV` and
`REDACTED_SET_DJANGO_SECRET_KEY`. Configure secrets outside Git before use.

## Deployed image identity

- Backend image: `takeshi945/nckumtb:backend-wgs-germline-20260722-acmg-sf-v33`
- Backend image ID: `sha256:ef2da7bd4449b54195e05840a228c9c2586119c2e1e293b89e735ba26901a0c5`
- Frontend/gateway image: `takeshi945/nckumtb:frontend-clinical-ui-20260722-acmg-sf-v33`
- Frontend image ID: `sha256:07941ded9772dece1daa2fbd16e0e4fb01486a37dc99361883e3febf121525ba`
- MTB repository source commit at snapshot: `22720c08919bd482a9fc605a339e931bf630608a`
- Frontend nested repository source commit: `02a8958ed62ba2d400b788e90148efe940db7d95`

The frontend snapshot includes its uncommitted working-tree changes because
those files are the source used for the currently deployed platform version.
