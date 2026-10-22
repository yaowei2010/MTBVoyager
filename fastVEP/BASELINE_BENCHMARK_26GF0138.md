# 26GF0138 fastVEP 全量測試與原 VEP 比較

執行日期：2026-09-21（UTC）。測試在 tmux `fastvep-26GF0138` 執行；比較在 `fastvep-26GF0138-compare` 執行。所有輸出僅在此本機目錄。

## 輸入與設定

- fastVEP 輸入：`/home/hpz8g5/project/WGS_Tumor/26GF0138.hard-filtered.vcf.gz`，GRCh38，9,950,549 筆 VCF 記錄。
- fastVEP 0.3.0，Docker 映像 `mtb-fastvep:0.3.0-ac2e2b6`；Ensembl release 112 GRCh38 GFF3、GRCh38 primary assembly FASTA；載入目前唯一已建好的 AlphaMissense `.osa2`。
- 原 VEP：`/home/hpz8g5/project/MTB/database/wgs_somatic/jobs/somwgs_f07ed28decd74372/results/26GF0138/annotation/26GF0138.vep.tsv.gz`，Ensembl VEP 112、GRCh38。**原平台先對 VCF 做了額外篩選，VEP 輸入是 `snv/26GF0138.somatic.filtered.vcf.gz`，約 5,519,157 筆；與此次 fastVEP 的 hard-filtered 輸入不是同一份檔案。** 因此下述一致率只針對兩邊共同的鍵，不能視為端到端同輸入 benchmark，也不能由此推算原 VEP 與 fastVEP 的速度比。

實際執行的指令在 `run.sh`；核心命令為：

```bash
./scripts/run-cli.sh fastvep annotate \
  --input /work/26GF0138_benchmark/input.vcf.gz \
  --output /work/26GF0138_benchmark/fastvep.tsv \
  --gff3 /data/reference/Homo_sapiens.GRCh38.112.gff3 \
  --fasta /data/reference/Homo_sapiens.GRCh38.dna.primary_assembly.fa \
  --sa-dir /data/sa \
  --hgvs --symbol --canonical --output-format tab
```

## 結果與時間

| 指標 | 結果 |
| --- | ---: |
| fastVEP 處理 VCF 記錄 | 9,950,549／9,950,549 |
| fastVEP transcript rows | 42,685,827 |
| fastVEP 命令整體 wall time（含 Docker 啟動、GFF3/FASTA 載入及輸出） | **6 分 26.38 秒** |
| fastVEP 程式記錄的位點處理階段 | 約 3.5 分鐘 |
| fastVEP 命令 exit status | 0 |
| 比較／外部排序額外耗時（不計入上列註解時間） | 33 分 57.33 秒 |

原平台的 Nextflow `work/*/*/.command.begin`、`.exitcode` 與 `.command.trace` 顯示：26 個 `VEP_ANNOTATE_SHARD` 分片自 2026-08-18 09:11:33 UTC 至 2026-08-19 01:48:26 UTC，牆鐘時間 **16 小時 36 分 53 秒**；`MERGE_VEP_SHARDS` 自 01:48:26 至 02:01:34，約 **13 分 8 秒**。兩者串接的 VEP 註解與合併階段約 **16 小時 50 分 1 秒**。與本次 fastVEP 命令的 6 分 26.38 秒相比，觀察到約 **156.8 倍**的牆鐘時間差（差 **16 小時 43 分 35 秒**）。

**此數字只是兩次實際流程的觀察差，不是軟體本身的同條件加速比。** 原 VEP 使用額外篩選後約 552 萬筆輸入、26 個分片、每片 `--fork 6`、`--everything` 與 dbNSFP／AlphaMissense／PrimateAI／SpliceAI plugin；本次 fastVEP 使用 995 萬筆原指定 VCF、單次 Docker 執行，並只載入 AlphaMissense。原 VEP 的分片也受 Nextflow 佇列和多工排程影響。兩者輸出欄位及外掛覆蓋不同。

詳細時間：`time.txt`；執行狀態：`status.txt`；執行日誌：`run.log`；fastVEP 輸出：`fastvep.tsv`；機器可讀比較：`comparison.json`；比較程式：`compare_vep.py`。

## 一致性：僅在可直接比較的鍵上

比較時以 `Location + Allele` 定義位點鍵，以 `Location + Allele + Feature` 定義轉錄本鍵；後者再加 `Consequence` 或 `IMPACT` 做精確字串比較。先去重，再算交集。

| 指標 | 原 VEP | fastVEP | 精確交集 |
| --- | ---: | ---: | ---: |
| 不同位點鍵 | 5,519,157 | 9,950,549 | **5,156,827** |
| 不同位點／轉錄本鍵 | 24,655,385 | 42,685,827 | **21,940,592** |
| 上述共同鍵中，Consequence 完全相同 | — | — | **21,940,519／21,940,592 = 99.999667%**；73 個不同 |
| 上述共同鍵中，IMPACT 完全相同 | — | — | **21,940,584／21,940,592 = 99.999964%**；8 個不同 |

原 VEP 未能以 `Location + Allele` 精確對上的 **362,330 個鍵全部是座標區間表示的 indel**（例如 `chr10:100001413-100001414`）；fastVEP 保留輸入 VCF 的另一種 indel 表示。因此這些鍵未進入精確 consequence／IMPACT 比較，**不能判定為缺失或不一致**。原 VEP 的非區間位點鍵在 fastVEP 中均有精確對應。此次未做 indel 左對齊／等位基因標準化後的等價性比較。

`--output-format tab` 的共同欄位可用於這次 Consequence、IMPACT 與轉錄本比較；**HGVS、SIFT、PolyPhen、REVEL、CADD、ClinPred、ClinVar 等欄位尚未逐項驗證一致性**。兩套系統的附加資料庫配置也不同：本次 fastVEP 只載入 AlphaMissense，原 VEP 使用平台既有 cache／plugin。上述高一致率不代表臨床註解全欄位等價。

## 後續核對

1. 將兩邊輸入統一為平台篩選後的同一份 GRCh38 VCF，再跑嚴格的同輸入比較。
2. 對 indel 做相同的左對齊與最簡等位基因表示後，重算覆蓋與 consequence 一致率。
3. 逐筆檢查 73 個 consequence、8 個 IMPACT 不同的共同轉錄本鍵；再比較 HGVS 與所需 plugin 欄位。
