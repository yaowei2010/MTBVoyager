#!/usr/bin/env python3
"""Write aggregate benchmark evidence without case identifiers or variant lists."""
import argparse
import json
from collections import Counter
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    root = Path(args.run_dir)
    report = json.loads((root/'reports/comparison_summary.json').read_text())
    lines = ['# INDEL 修正驗證結果', '', '更新：2026-10-06。', '',
             '20 項單元/比對測試及兩條完整 synthetic Nextflow 流程通過。',
             '公開 cache 案例 rs1481478962：gnomADg_AF 從缺失補回 0.0662（6.62%）。', '',
             '本輪只重算 cache 欄位；consequence、transcript、HGVS、plugin 和 genotype 保留。',
             '以下為匿名彙總；病例級輸出不納入 Git。', '']
    for sample, data in report.items():
        kind = 'Germline' if 'all_candidates' in data['downstream'] else 'Somatic'
        counts = data['annotation']['counts']
        audit = Counter()
        for path in (root/'results'/sample/'annotation/shards').glob('*.annotation.summary.json'):
            summary = json.loads(path.read_text())
            audit.update(summary['cache_refresh_audit']['gnomADg_AF'])
        lines += ['## '+kind, '',
                  f"gnomADg_AF：修正前非缺失 {audit['old_nonmissing']}、修正後 {audit['new_nonmissing']}；補回 {audit['gained']}、失去 {audit['lost']}、不同 {audit['different']}。", '',
                  f"對舊 VEP 的匹配變異 {counts['matched_variants']}；舊側獨有 {counts.get('vep_only_variants',0)}、新側獨有 {counts.get('fastvep_only_variants',0)}。", '',
                  '| 下游項目 | 舊 VEP | 修正後 fastVEP | 保留 | 新增 | 失去 |',
                  '|---|---:|---:|---:|---:|---:|']
        for key, value in data['downstream'].items():
            lines.append(f"| {key} | {value['baseline']} | {value['fastvep']} | {value['shared']} | {value['gained']} | {value['lost']} |")
        lines += ['', '分級/欄位差異：', '```json',
                  json.dumps({key:value['field_differences'] for key,value in data['downstream'].items()},ensure_ascii=False,indent=2), '```', '']
    lines += ['## 結論與限制', '',
              '索引、cache refresh 與完整下游比對已完成；是否可正式切換仍需逐項審查差異。',
              '缺少的 SpliceAI indel chromosome coverage、other contig 身分、regulatory/motif 註解及 HGVS/transcript 差異尚未由此次頻率匹配修正解決。', '',
              '可重現操作見 WGS_FASTVEP_INDEL_MATCHING.md。',
              '本機完整輸出：/home/hpz8g5/project/MTB-fastvep-indel-validation-20261006。', '']
    Path(args.output).write_text('\n'.join(lines))


if __name__ == '__main__':
    main()
