# MTB baseline before fastVEP migration — 2026-10-01

This snapshot preserves the Ensembl VEP 112 WGS baseline.

- `source/`: Git-tracked germline and somatic backend source, Dockerfiles, Nextflow pipelines and test fixtures from the MTB repository.
- `deployed/`: WGS modules and pipelines copied from the running backend container; these are the deployment baseline.
- `deployment/`: current tracked Docker Compose and gateway configuration. The frontend baseline is the parent commit of this backup branch.
- `manifest.json`: source commits, running image IDs, WGS configuration and mount paths.
- `SHA256SUMS`: checksums of snapshot files.

Patient inputs, job outputs, database contents, annotation databases, .env credentials and Python caches are excluded. Preserve the existing host data separately; this is a code/configuration backup, not a complete database or Docker image archive.

## Restore

Check out the `pre-fastvep-20261001` tag in a separate worktree. Restore the backed-up source and deployment configuration into their original locations. For exact WGS code parity, use the `deployed/` pipeline and Python module snapshots in the backend build. Keep the original .env and host database/reference files. Prefer the recorded existing Docker image IDs when available locally; rebuilding mutable base-image tags may produce a different image. Recreate only the backend after checking that no WGS jobs are active. Do not overwrite old installed pipeline version directories or historical jobs.

## Secret redactions

Existing hardcoded credentials in legacy overlay source were replaced with `REDACTED_RESTORE_FROM_LOCAL_ENV`. Keep the original credentials locally or supply them through environment configuration when restoring. The active WGS pipeline snapshots required no such redactions.
