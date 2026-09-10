import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent))
from wgs_somatic import legacy_mtb_report as report


def test_tso500_proxy_deduplicates_transcripts_and_excludes_population_variants():
    rows = [
        {"Chr": "chr7", "Start": "1", "Ref": "A", "Alt": "T", "Consequence": "missense_variant", "AF": "0", "Feature": "tx1"},
        {"Chr": "chr7", "Start": "1", "Ref": "A", "Alt": "T", "Consequence": "missense_variant", "AF": "0", "Feature": "tx2"},
        {"Chr": "chr8", "Start": "2", "Ref": "C", "Alt": "G", "Consequence": "synonymous_variant", "AF": "0"},
        {"Chr": "chr9", "Start": "3", "Ref": "G", "Alt": "A", "Consequence": "missense_variant", "AF": "0.02"},
        {"Chr": "chr10", "Start": "4", "Ref": "T", "Alt": "C", "Consequence": "intron_variant", "AF": "0"},
    ]
    result = report.estimate_tso500_tmb(rows)
    assert result["assay_profile"] == "Illumina TruSight Oncology 500 proxy"
    assert result["panel_size_mb"] == 1.94
    assert result["tmb_numerator_variants"] == 2
    assert result["tmb_proxy_mut_per_mb"] == 1.03
    assert result["status"] == "exploratory_not_clinically_validated"
