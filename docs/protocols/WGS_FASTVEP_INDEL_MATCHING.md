# WGS fastVEP INDEL 頻率匹配修正與驗證 protocol

更新日期：2026-10-06。此文件與實作保存在 MTB 更新分支；正式網站尚未切換。

## 問題與修正範圍

Adapter 0.1.2 將輸入 INDEL 縮成最小表示，但以 cache 的原始 start/end/REF/ALT
匹配，因此漏掉共同前後綴、重複序列和跨區塊的等價等位基因。0.1.3 建立
reference-normalized SQLite 索引，用同一份 GRCh38 FASTA 驗證 REF、移除共同
前後綴，並對純 insertion/deletion 做重複序列左對齊。每個 ALT 分開建立索引，
另保留 cache 原始 ALT，供 allele-specific ClinVar、gnomAD 頻率查詢。

此次沿用 Ensembl 112 cache 的 gnomAD exome r2.1.1 / genome v3.1.2，沒有換資料版本。
索引含所有可正規化的非單鹼基替換等位基因，包括縮短後成為 SNV 的 padded alleles。
一般 SNV 仍查原 cache，並檢查非 SNV 索引中的等價記錄。

查不到頻率維持缺失，不填 0。已知 scaffold 無 variation-cache 資料時，保留變異並
標記 `variation_cache_unavailable_contig`；未知 contig、缺少 primary cache block、
缺少/過期索引或輸入 REF 與 FASTA 不一致會中止。無法正規化的 cache allele
（REF 不一致、符號 allele 等）會記錄於索引 manifest 的 counts，不編造頻率。

## 實作位置

- `students/wgs_annotation/variation_index.py`：正規化、原子索引建立。
- `students/wgs_annotation/build_variation_index.py`：建置 CLI、多 contig 平行工作。
- `students/wgs_annotation/fastvep_to_mtb.py`：唯讀索引查詢、allele-specific 欄位回填。
- `students/wgs_annotation/validation/refresh_variation_annotations.py`：只重算 cache 欄位。
- `students/backend_wgs*/pipeline/modules/local/fastvep_annotate.nf`：傳入 FASTA 與索引。

索引建在原 cache 之外。每個 contig 完成後才將 `.sqlite.partial` 原子改名；
manifest 只在整輪建置成功後產生。索引記錄 cache info hash、block 檔案清單/
size/mtime、FASTA size/mtime 與 FAI hash，adapter 不接受不相符的資料。
更換 reference/cache 或正規化規則版本時，請建立新的索引目錄，勿覆寫舊索引。

## 建置

從 `/home/hpz8g5/project/MTB` 執行：

```bash
docker build -t mtb-wgs-fastvep:0.1.3 students/wgs_annotation

docker run --rm --network none -u "$(id -u):$(id -g)" \
  -v /home/hpz8g5/project:/home/hpz8g5/project \
  mtb-wgs-fastvep:0.1.3 build_variation_index.py \
  --variation-cache /home/hpz8g5/project/MTB/database/VEP/database/homo_sapiens/112_GRCh38 \
  --reference /home/hpz8g5/project/WGS/reference/hg38.fa \
  --output /home/hpz8g5/project/MTB/database/fastvep/vep112-normalized-variation-v1 \
  --workers 4
```

必要檔案：FASTA/FAI、原 cache info.txt/chr_synonyms.txt/variation blocks。
索引與各項資料必須掛載到實際執行 annotation 的容器，且路徑一致。

## Pipeline 與平台設定

- Annotation image：`mtb-wgs-fastvep:0.1.3`。
- Nextflow：`--fastvep_variation_index <索引目錄>`，並提供原有 `--reference`。
- Backend：`WGS_FASTVEP_VARIATION_INDEX=<索引目錄>`。
- CLI adapter 新增必要參數 `--reference <FASTA> --variation-index <索引目錄>`。
- 保留 `WGS_ANNOTATION_ENGINE=vep` 切回設定。

分支內 compose 會使用 `${DATA_ROOT}/fastvep/vep112-normalized-variation-v1`。
此次修改不會啟動 compose 或取代正式容器。

## 驗證

```bash
docker run --rm --network none \
  -v /home/hpz8g5/project/MTB/students/wgs_annotation:/src:ro \
  mtb-wgs-fastvep:0.1.3 python -m unittest discover -s /src/tests -v

bash students/wgs_annotation/validation/run_synthetic.sh
```

目前 20 項 adapter/comparison 測試通過，包含多 ALT、REF/ALT 共同前後綴、
反向序列、零頻率與缺失的區別、跨 1 Mb 區塊/長重複序列、過期索引與保留變異。
兩條完整 Nextflow 測試通過：`/tmp/mtb-fastvep-validation-20261006T023515`。

真實 cache 漏配案例與兩個樣本的驗證狀態見
`docs/protocols/WGS_FASTVEP_INDEL_RESULTS.md`。病例輸出不納入 Git。

## 真實樣本重跑與判讀

本輪結果目錄：`/home/hpz8g5/project/MTB-fastvep-indel-validation-20261006`。
前一輪：`/home/hpz8g5/project/MTB-fastvep-comparison-20261002`，保留不覆寫。

```bash
tmux attach -t mtb_fastvep_indel_20261006
```

依序建置索引、重算兩個樣本各染色體的 cache 衍生欄位、確認變異及 transcript
row 數完全保留，再以相同規則對舊 VEP 比對並重跑 germline prioritization / somatic
OncoVI。比較 refresh audit 中 AF 的 gained/lost/different，確認是否減少原有缺失；
逐項查明 somatic 分級與 reportable 變化。資料不足的 allele 不視為「頻率為零」。

此重跑保留既有 SpliceAI/plugin 註解，沒有以空值替換讀取錯誤。前次只修復 chr10
SpliceAI indel overlay；原 SpliceAI indel 檔案其他缺少的 contig coverage 並未全部補齊。
此資料缺口與 regulatory/motif 覆蓋、transcript/HGVS 差異仍是正式切換前的驗證項目。

完成標記、日誌及摘要報告需一起檢查；有 FAILED 標記時不可當作驗證通過。
正式切換前需確認候選清單、分級、reportable/actionable 和面板匯出結果。


## 2026-10-06 程式檢查補充

已修正 padded input 縮短後為 SNV 時漏查一般 SNV cache 的邊界情況，新增測試通過。
重跑工具會檢查 summary 的完成狀態、adapter/索引來源，以及比對報告的來源和時間，
不再只因檔案存在就跳過工作。真實資料索引/新比對完成前仍不可作正式切換依據。


## 2026-10-06 驗收範圍與 SpliceAI 資料盤點

依使用者目前只關注主要染色體的範圍，此輪驗收使用 `--primary-only`，比較
chr1–22、X、Y、M，共兩個樣本 50 個分段。other 的原始檔案/歷史結果保留，
不改正式 pipeline 的 contig 規則。other 是主染色體之外的序列，許多仍以 chr 開頭
（例如 chr11_GL383547v1_alt），不是根據有沒有 chr 前綴分類。

`run_cache_refresh_comparison.py --wait-for-index` 可在每個 contig 的索引原子完成後
先處理該 contig；每個索引仍會檢查 reference/cache 指紋，不使用 `.partial` 檔。
不必等全體索引 manifest 完成才開始。50 分段全完成且下游比對成功才標記驗證完成。

SpliceAI 現有來源為 `database/VEP/database/Plugins`：SNV 索引有 1–22/X/Y；indel
索引只有 1–10，而且壓縮檔在 chr10 被截斷。前次 chr10 替代資料已通過 checksum
與舊檔可讀區段比對，但不是全體 indel 資料補齊。

補齊方式：取得與原來源相符的 GRCh38 raw indel 完整 VCF 與 index，下載至獨立
資料目錄，核對來源/checksum、完整解壓縮檢查、tabix 查詢與可讀舊區段的分數一致性，
通過後才將新的 plugin data 路徑用於測試流程。不能只對被截斷的檔案重建 index，
也不能將 masked/raw 或不同版本混用。SNV 的 contig 名單不代表已完成全檔完整性檢查。

官方資料/格式說明：
https://github.com/Illumina/SpliceAI/blob/master/README.md
https://grch37.ensembl.org/info/docs/tools/vep/script/vep_plugins.html

預計算資料涵蓋基因內 SNV、1 bp insertion 和 1–4 bp deletion，不能保證所有長 INDEL
都有分數。未收錄不等於零分。fastVEP 可以查詢現有 VEP 用的 VCF，不需要執行 VEP
plugin 或另外訓練模型。此輪 INDEL AF 驗證保留先前 plugin 分數，沒有改動其來源。
