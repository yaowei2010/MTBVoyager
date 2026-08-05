# WGS Germline backend overlay

This directory extends the current platform backend image without replacing
the existing WES, trio, somatic, VUS or blacklist code.

## API

The Django app implements the frontend contract at
`/ncku_hospital/wgs-germline/`: subject draft, three VCF uploads, MONDO search,
job launch/status, SNV/SV candidate tables and PharmCAT results.

## Execution model

Nextflow 26.04.6 runs in the backend controller container. Every analysis task
runs in Docker through the mounted host Docker socket:

- bcftools 1.20: validation and normalization
- Ensembl VEP 112: SNV/INDEL annotation
- ncku-wgs-python: clinical bucketing and final audit manifest
- PharmCAT 3.3.0: pharmacogenomics

All execution state is under `WGS_DATA_ROOT`, including immutable pipeline
snapshots, uploads, work directories, logs and published results.

## MONDO and Monarch data

Download `mondo.json` from the official MONDO download page and a Monarch
disease-gene association TSV, then build the runtime indexes:

```bash
python tools/prepare_mondo.py \
  --mondo-json mondo.json \
  --mondo-rare-json mondo-rare.json \
  --gene-associations gene_disease.all.tsv \
  --outdir /path/to/DATA_ROOT/mondo \
  --mondo-release YYYY-MM-DD \
  --monarch-release YYYY-MM-DD
```

MONDO supplies ontology terms, ancestry, and the official rare-disease subset. Monarch supplies the human gene
associations. Both release values are persisted in every job.

## Local literature RAG

The literature service uses a persistent SQLite FTS5 database. Seed it from a
bounded, reviewed gene list (the ACMG SF list is recommended):

```bash
python tools/build_literature_rag.py \
  --genes acmg_sf_genes.txt \
  --retmax 3 \
  --database /path/to/DATA_ROOT/literature_rag/literature.sqlite3
```

New genes are added on demand when a result-table user requests an insight.
Set `LITERATURE_RAG_DB` to the database path. Narrative generation uses an
OpenAI-compatible local endpoint configured with `LITERATURE_LLM_URL`; the
Compose `literature-llm` profile provides a CPU-based llama.cpp server after a
GGUF model is placed in `LITERATURE_MODEL_ROOT`.
