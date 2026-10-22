# fastVEP standalone Docker PoC

This directory contains an isolated fastVEP environment for validation. It does
not modify or deploy into the MTB production pipelines.

## Pinned upstream

- Repository: <https://github.com/Huang-lab/fastVEP>
- fastVEP version: `0.3.0`
- Commit: `ac2e2b64a9c4c27163a3df16e0a559113af19625`
- Image: `mtb-fastvep:0.3.0-ac2e2b6`

The source checkout is stored under `src/` in detached-HEAD mode. The image
build uses `Cargo.lock` and `cargo build --locked` for reproducibility.

## Layout

```text
fastVEP/
├── Dockerfile
├── compose.yaml
├── src/                    # pinned upstream source
├── data/
│   ├── reference/          # GFF3, FASTA, FAI, transcript cache
│   └── sa/                 # .osa/.osa2/.osi/.oga files
├── work/                   # VCF input and annotation output
└── scripts/
    ├── build-image.sh
    ├── run-cli.sh
    ├── smoke-test.sh
    ├── build-sa.sh
    └── build-transcript-cache.sh
```

Reference and annotation data are deliberately excluded from the image. They
are mounted read-only at runtime, allowing database updates without rebuilding
the executable image.

## Build and verify

```bash
cd /home/hpz8g5/tools/fastVEP
chmod +x scripts/*.sh
./scripts/build-image.sh
./scripts/smoke-test.sh
```

Inspect the version and image metadata:

```bash
docker run --rm mtb-fastvep:0.3.0-ac2e2b6 fastvep --version
docker image inspect mtb-fastvep:0.3.0-ac2e2b6
```

## Reference setup

For a fair comparison with the current MTB platform, use Ensembl release 112
GRCh38 GFF3 and a matching GRCh38 FASTA. Do not compare release 112 VEP output
to release 115 fastVEP output.

Place files in `data/reference/`:

```text
data/reference/Homo_sapiens.GRCh38.112.gff3
data/reference/hg38.fa
data/reference/hg38.fa.fai
```

Build a reusable transcript cache:

```bash
./scripts/build-transcript-cache.sh \
  data/reference/Homo_sapiens.GRCh38.112.gff3 \
  data/reference/hg38.fa \
  data/reference/grch38_ensembl112.fastvep.cache
```

## Build supplementary annotation databases

The converter writes into `data/sa-mtb/` by default:

```bash
./scripts/build-sa.sh \
  alphamissense \
  /absolute/path/AlphaMissense_hg38.tsv.gz \
  alphamissense \
  GRCh38
```

Additional examples:

```bash
./scripts/build-sa.sh primateai /absolute/path/PrimateAI.tsv.gz primateai GRCh38
./scripts/build-sa.sh spliceai /absolute/path/spliceai.vcf.gz spliceai GRCh38
./scripts/build-sa.sh revel /absolute/path/revel.tsv.gz revel GRCh38
./scripts/build-sa.sh clinvar /absolute/path/clinvar.vcf.gz clinvar GRCh38
./scripts/build-sa.sh cosmic /absolute/path/CosmicCodingMuts.vcf.gz cosmic GRCh38
```

After every conversion, verify that the output is not an unexpectedly tiny
file. fastVEP may otherwise load an empty database without making the pipeline
fail.

## Run CLI annotation

### Pinned MTB GRCh38 profile

Use `run-hg38.sh` for MTB-compatible testing. It pins the Ensembl 112 canonical
transcript cache, the official MTB `hg38.fa`, and the converted supplementary
annotation directory (`data/sa-mtb` by default):

```bash
./scripts/verify-hg38.sh
./scripts/run-hg38.sh \
  /work/input.vcf.gz \
  /work/input.fastvep.tsv \
  tab
```

The host directory `/home/hpz8g5/project/WGS/reference` is mounted read-only
as `/mtb-reference`. Do not use the historical `data/reference/hg38.fa`
symlink for MTB comparison: it resolves to a different FASTA checksum.

### Quick start: repeat the tested GRCh38 VCF run

The following command was run successfully with the non-patient example VCF
bundled in this checkout. It annotated all 173 input variants on 2026-09-21.
Run it from `/home/hpz8g5/tools/fastVEP`:

```bash
cp src/validation/human/vep_example_GRCh38.vcf work/vep_example_GRCh38.vcf
./scripts/run-cli.sh fastvep annotate \
  --input /work/vep_example_GRCh38.vcf \
  --output /work/vep_example_GRCh38.fastvep.json \
  --gff3 /data/reference/Homo_sapiens.GRCh38.112.gff3 \
  --fasta /data/reference/Homo_sapiens.GRCh38.dna.primary_assembly.fa \
  --sa-dir /data/sa-mtb \
  --hgvs --symbol --canonical --output-format json
```

The output is `work/vep_example_GRCh38.fastvep.json` on the host. A quick
check of the JSON record count:

```bash
python3 -c 'import json; p="work/vep_example_GRCh38.fastvep.json"; print(len(json.load(open(p))), "variants")'
```

Expected for this example: `173 variants`. The test produced 83
`missense_variant` and 90 `synonymous_variant` records. The current MTB profile
loads 55 `.osa2` files from `data/sa-mtb`: AlphaMissense, ClinVar, dbNSFP,
REVEL, PrimateAI, SpliceAI SNV/indel, and chromosome shards for gnomAD exomes
v4.1 and phyloP100way.

To annotate your own **GRCh38** VCF, copy it into `work/`, then change the
`--input` and `--output` names above. Paths inside `run-cli.sh`'s Docker
container use `/work` for this folder's `work/` and `/data` for `data/`.
Use a different reference/annotation setup for a GRCh37 VCF; do not label it
GRCh38. The first full run loads about 254,129 transcripts and may take a few
minutes. The data mount is read-only, so a warning about not saving the
transcript cache under `/data/reference` is expected; annotation still
completed successfully.

### General CLI usage

Copy or link the input VCF under `work/`, then run:

```bash
./scripts/run-cli.sh fastvep annotate \
  --input /work/input.vcf.gz \
  --output /work/input.fastvep.json \
  --gff3 /data/reference/Homo_sapiens.GRCh38.112.gff3 \
  --fasta /data/reference/hg38.fa \
  --sa-dir /data/sa-mtb \
  --hgvs \
  --symbol \
  --canonical \
  --output-format json
```

To test supplementary annotation without replacing the current Ensembl VEP
consequence/HGVS output:

```bash
./scripts/run-cli.sh fastvep annotate \
  --input /work/already_annotated.vcf.gz \
  --output /work/supplemented.vcf \
  --sa-dir /data/sa-mtb \
  --sa-only
```

The wrapper runs as the invoking host user, mounts data read-only, uses a
read-only container root filesystem, and permits writes only under `work/` and
the temporary filesystem.

### Validate the complete MTB supplementary set

The positive fixture covers all eight supplementary source types. It also
checks that all 55 files can be opened together and queried from one run:

```bash
FASTVEP_IMAGE=mtb-fastvep:0.3.0-mtb-grch38-20261019 \
  ./scripts/integration-test-sa.sh
```

Expected result:

```text
PASS: 8 variants; all 8 supplementary sources were observed
```

Generate and verify the complete checksum inventory with:

```bash
./scripts/build-sa-checksums.sh
./scripts/verify-hg38.sh
```

The Illumina SpliceAI raw indel source available on this host ended in one
truncated BGZF block. `spliceai_indel_grch38.osa2` was built from a preserved
repair copy with that final incomplete block removed. Obtain a fresh licensed
BaseSpace copy before treating this artifact as an archival upstream release.

## Run the local web/API service

Create `.env` from `.env.example` and update the two filenames if needed:

```bash
cp .env.example .env
docker compose up -d fastvep-web
curl -s http://127.0.0.1:8080/api/status | python3 -m json.tool
```

If `id -u` or `id -g` is not `1000`, also set `FASTVEP_UID` and
`FASTVEP_GID` in `.env` to those values so the service can write its statistics
file under `work/`.

Stop it with:

```bash
docker compose down
```

The port is published only on `127.0.0.1`. fastVEP has no built-in
authentication, so do not expose it directly to the hospital network or the
public internet.

## Validation before MTB integration

Run the current VEP and fastVEP in parallel on the same normalized VCF and
compare at least:

- uploaded variant and allele
- gene, transcript, and canonical/MANE selection
- consequence and impact
- HGVSc, HGVSp, and HGVSg
- AlphaMissense, REVEL, PrimateAI, and SpliceAI
- missing-value rates and output record counts
- cold-start and warm-run wall time and peak RSS

The current MTB dbNSFP plugin additionally requests CADD, ClinPred, PhyloP, and
phastCons fields. Do not replace the production VEP stage until these fields
have an equivalent fastVEP source or a documented downstream fallback.
