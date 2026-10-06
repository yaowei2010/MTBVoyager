# INDEL 修正驗證結果

2026-10-06：程式與兩條 Nextflow 流程已接入 normalized cache index。
20 項單元/比對測試通過，完整 germline/somatic synthetic Nextflow 通過。
真實漏配案例 rs1481478962 已通過：gnomADg_AF 從缺失補回 0.0662（6.62%）。
測試使用原 cache 的 chr22 單一公開資料區塊，沒有引入新的 gnomAD 版本。

完整 cache 索引建置已完成；兩個樣本 50/50 個主要染色體分段的 cache refresh
與分段比對已完成。整體下游驗收尚未完成，不代表已可切換正式平台。

執行紀錄：`/home/hpz8g5/project/MTB-fastvep-indel-validation-20261006`。
最終結果會記錄於此文件；尚未有正式平台切換結論。

本輪驗收範圍調整為 chr1–22/X/Y/M，共 50 分段；other 保留但不列為此次阻擋項目。
gnomADg_AF 新增取得分數的變異：26GF0138 為 635,736；26T00013 為 778,294；
兩個樣本原有 gnomADg_AF 遺失均為 0。此數字來自全分段 refresh audit，
不是下游候選數，也不是與舊 VEP 完全一致的結論。

完整 germline 註解檔已合併，現正執行下游流程；接續檢查 germline 候選篩選、
somatic OncoVI 與可報告結果。最終 comparison_summary.json 及完成標記尚未產生。
SpliceAI 缺少資料依使用者決定不補齊，保留缺值。
