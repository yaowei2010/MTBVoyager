import json
import subprocess
from pathlib import Path


PIPELINE = Path(__file__).parents[1]


def test_profile_uses_user_sample_id(tmp_path):
    """The uploaded VCF header must not override the user-provided ID."""
    work = tmp_path / "work"
    results = tmp_path / "results"
    subprocess.run([
        "nextflow", "run", str(PIPELINE), "-profile", "test", "-ansi-log", "false",
        "-work-dir", str(work), "--outdir", str(results),
    ], check=True, cwd=PIPELINE)
    validation = json.loads((results / "Custom_Test_01/qc/Custom_Test_01.validation.json").read_text())
    assert validation["sample_id"] == "Custom_Test_01"
    assert validation["original_vcf_sample"] == "TEST"
    assert validation["vcf_sample"] == "Custom_Test_01"
    assert validation["reheadered"] is True
    completed = json.loads((results / "Custom_Test_01/pipeline_complete.json").read_text())
    assert completed["sample_id"] == "Custom_Test_01"
