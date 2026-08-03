import gzip
import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "bin" / "summarize_somatic.py"
spec = importlib.util.spec_from_file_location("summarize_somatic", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_truthy_requires_explicit_evidence():
    assert module.truthy({"CLIN_SIG": "Pathogenic"}, ["CLIN_SIG"])
    assert not module.truthy({"CLIN_SIG": "uncertain_significance"}, ["CLIN_SIG"])


def test_gzip_opener(tmp_path):
    path = tmp_path / "input.tsv.gz"
    with gzip.open(path, "wt") as handle:
        handle.write("a\tb\n1\t2\n")
    with module.opener(path) as handle:
        assert handle.readline().strip() == "a\tb"
