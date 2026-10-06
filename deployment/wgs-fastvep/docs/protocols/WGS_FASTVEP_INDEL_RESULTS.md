# INDEL 修正驗證結果

2026-10-06：程式與兩條 Nextflow 流程已接入 normalized cache index。
20 項單元/比對測試通過，完整 germline/somatic synthetic Nextflow 通過。
真實漏配案例 rs1481478962 已通過：gnomADg_AF 從缺失補回 0.0662（6.62%）。
測試使用原 cache 的 chr22 單一公開資料區塊，沒有引入新的 gnomAD 版本。

完整 cache 索引建置中；兩個樣本的重新比對尚未完成。

執行紀錄：`/home/hpz8g5/project/MTB-fastvep-indel-validation-20261006`。
最終結果會記錄於此文件；尚未有正式平台切換結論。
