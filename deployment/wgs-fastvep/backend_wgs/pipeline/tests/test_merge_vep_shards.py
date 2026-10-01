import gzip
import subprocess
import sys
from pathlib import Path

import pytest

STUDENTS = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize("backend", ["backend_wgs", "backend_wgs_somatic"])
def test_merge_rejects_incompatible_shards_and_duplicate_inputs(tmp_path, backend):
    script = STUDENTS / backend / "pipeline/bin/merge_vep_shards.py"
    paths = [tmp_path / f"S.{chrom}.vep.tsv.gz" for chrom in ("chr1", "other")]
    for path, header in zip(paths, ("#Uploaded_variation\tSYMBOL\n", "#Uploaded_variation\tGene\n")):
        with gzip.open(path, "wt") as handle:
            handle.write(header)
    common = [sys.executable, str(script), "--sample", "S", "--output", str(tmp_path / "out.gz")]
    result = subprocess.run(common + list(map(str, paths)), capture_output=True, text=True)
    assert result.returncode != 0 and "columns differ" in result.stderr
    result = subprocess.run(common + [str(paths[0]), str(paths[0])], capture_output=True, text=True)
    assert result.returncode != 0 and "Duplicate" in result.stderr


@pytest.mark.parametrize("backend", ["backend_wgs", "backend_wgs_somatic"])
def test_merge_keeps_rows_with_empty_shards_and_stable_chromosome_order(tmp_path, backend):
    script = STUDENTS / backend / "pipeline/bin/merge_vep_shards.py"
    paths = []
    for chrom, body in (("other", ""), ("chr2", "v2\tB\n"), ("chr1", "v1\tA\n")):
        path = tmp_path / f"S.{chrom}.vep.tsv.gz"
        with gzip.open(path, "wt") as handle:
            handle.write("## annotation_engine=fastvep\n#Uploaded_variation\tSYMBOL\n" + body)
        paths.append(str(path))
    output = tmp_path / "out.gz"
    subprocess.run([sys.executable, str(script), "--sample", "S", "--output", str(output)] + paths, check=True)
    with gzip.open(output, "rt") as handle:
        lines = list(handle)
    assert sum(line.startswith("#Uploaded_variation") for line in lines) == 1
    assert [line for line in lines if not line.startswith("#")] == ["v1\tA\n", "v2\tB\n"]
