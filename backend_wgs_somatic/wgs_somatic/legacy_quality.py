"""Shared, sample-specific quality gate for legacy tumor-only results."""
import json


DEFAULTS = {"min_dp": 20.0, "min_vaf": 0.05, "population_af_max": 0.01}


def number(value):
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def settings(directory):
    result = dict(DEFAULTS)
    path = directory / "summary.json"
    if path.is_file():
        try:
            saved = json.loads(path.read_text(encoding="utf-8"))
            result.update({
                "min_dp": number(saved.get("min_dp_cutoff")) or DEFAULTS["min_dp"],
                "min_vaf": number(saved.get("min_aaf")) or DEFAULTS["min_vaf"],
                "population_af_max": number(saved.get("maf_cutoff")) or DEFAULTS["population_af_max"],
            })
        except (OSError, ValueError, TypeError):
            pass
    return result


def population_af(row):
    values = [number(row.get(key)) for key in ("AF", "AF_popmax", "AF_eas")]
    values = [value for value in values if value is not None]
    return max(values) if values else None


def passes(row, thresholds):
    depth = number(row.get("DP") or row.get("depth"))
    vaf = number(row.get("VAF") or row.get("vaf"))
    population = population_af(row)
    return (
        depth is not None and depth >= thresholds["min_dp"]
        and vaf is not None and vaf >= thresholds["min_vaf"]
        and (population is None or population <= thresholds["population_af_max"])
    )
