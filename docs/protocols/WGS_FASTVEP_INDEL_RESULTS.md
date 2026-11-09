# INDEL 修正驗證結果

更新：2026-10-06。

20 項單元/比對測試及兩條完整 synthetic Nextflow 流程通過。
公開 cache 案例 rs1481478962：gnomADg_AF 從缺失補回 0.0662（6.62%）。

本輪只重算 cache 欄位；consequence、transcript、HGVS、plugin 和 genotype 保留。
以下為匿名彙總；病例級輸出不納入 Git。

驗收範圍：chr1–22、X、Y、M；other 不納入此次驗收。

## Germline

gnomADg_AF：修正前非缺失 3692975、修正後 4471269；補回 778294、失去 0、不同 778294。

對舊 VEP 的匹配變異 4502495；舊側獨有 0、新側獨有 0。

| 下游項目 | 舊 VEP | 修正後 fastVEP | 保留 | 新增 | 失去 |
|---|---:|---:|---:|---:|---:|
| all_candidates | 5 | 5 | 5 | 0 | 0 |
| known_clinvar_plp | 1 | 1 | 1 | 0 | 0 |
| insilico | 5 | 5 | 5 | 0 | 0 |
| acmg_sf | 0 | 0 | 0 | 0 | 0 |
| acmg_sf_inheritance_matched | 0 | 0 | 0 | 0 | 0 |

分級/欄位差異：
```json
{
  "all_candidates": {
    "Feature": 0,
    "Consequence": 0,
    "HGVSc": 0,
    "HGVSp": 4,
    "candidate_categories": 0,
    "damaging_predictor_count": 0,
    "normalized_pathogenicity": 0
  },
  "known_clinvar_plp": {
    "Feature": 0,
    "Consequence": 0,
    "HGVSc": 0,
    "HGVSp": 1,
    "candidate_categories": 0,
    "damaging_predictor_count": 0,
    "normalized_pathogenicity": 0
  },
  "insilico": {
    "Feature": 0,
    "Consequence": 0,
    "HGVSc": 0,
    "HGVSp": 4,
    "candidate_categories": 0,
    "damaging_predictor_count": 0,
    "normalized_pathogenicity": 0
  },
  "acmg_sf": {},
  "acmg_sf_inheritance_matched": {}
}
```

## Somatic

gnomADg_AF：修正前非缺失 4375996、修正後 5011732；補回 635736、失去 0、不同 635736。

對舊 VEP 的匹配變異 5519157；舊側獨有 0、新側獨有 0。

| 下游項目 | 舊 VEP | 修正後 fastVEP | 保留 | 新增 | 失去 |
|---|---:|---:|---:|---:|---:|
| oncogenicity | 14016 | 14016 | 14016 | 0 | 0 |
| reportable | 13 | 19 | 13 | 6 | 0 |
| actionable | 0 | 0 | 0 | 0 | 0 |
| oncogenic | 2 | 2 | 2 | 0 | 0 |

分級/欄位差異：
```json
{
  "oncogenicity": {
    "oncogenicity_score": 353,
    "oncogenicity_classification": 345,
    "oncogenicity_criteria": 353,
    "oncovi_2026_score": 364,
    "oncovi_2026_classification": 305
  },
  "reportable": {
    "oncogenicity_classification": 0,
    "high_risk_basis": 0,
    "cancer_actionable": 0,
    "Consequence": 1
  },
  "actionable": {},
  "oncogenic": {
    "oncogenicity_classification": 0,
    "high_risk_basis": 0,
    "cancer_actionable": 0,
    "Consequence": 0
  }
}
```

## 結論與限制

索引、cache refresh 與完整下游比對已完成；是否可正式切換仍需逐項審查差異。
缺少的 SpliceAI indel chromosome coverage、other contig 身分、regulatory/motif 註解及 HGVS/transcript 差異尚未由此次頻率匹配修正解決。

可重現操作見 WGS_FASTVEP_INDEL_MATCHING.md。
本機完整輸出：/home/hpz8g5/project/MTB-fastvep-indel-validation-20261006。
