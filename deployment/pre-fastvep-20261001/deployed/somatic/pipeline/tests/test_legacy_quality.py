import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent))

from wgs_somatic.legacy_quality import passes


THRESHOLDS = {"min_dp": 20, "min_vaf": .05, "population_af_max": .01}


def test_quality_gate_requires_depth_and_vaf_and_allows_rare_variant():
    assert passes({"DP": "20", "VAF": ".05", "AF": ".001"}, THRESHOLDS)
    assert not passes({"DP": "19", "VAF": ".05", "AF": ".001"}, THRESHOLDS)
    assert not passes({"DP": "20", "VAF": ".049", "AF": ".001"}, THRESHOLDS)
    assert not passes({"DP": "20", "VAF": ".05", "AF": ".02"}, THRESHOLDS)
