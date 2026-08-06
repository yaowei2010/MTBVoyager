import os

def check_paths(newJobID, file_name):
    paths_to_check = [
        # VEP 相關
        "/VEP/database/",
        "/VEP/hg19/",
        "/VEP/hg19/ucsc.hg19.fasta",

        # ANNOVAR 相關
        "/annovar/",
        "/annovar/humandb/",
        "/annovar/humandb/ucsc_hg19.fa",
        "/annovar/humandb/annovar_to_approved_symbol.json",

        # Blacklist
        "/miRTI/media/reference/Blacklist/blacklist_V8.1.xlsx",

        # Patient job VCF
        f"/miRTI/media/patient/{newJobID}/{file_name}"
    ]

    print("🔍 開始檢查路徑...\n")
    all_exist = True
    for path in paths_to_check:
        if os.path.exists(path):
            print(f"✅ 存在: {path}")
        else:
            print(f"❌ 缺失: {path}")
            all_exist = False

    if all_exist:
        print("\n🎉 所有必要路徑都存在，可以安全執行！")
    else:
        print("\n⚠️ 有缺失的路徑，請先確認後再執行 run_vep_and_annovar。")

if __name__ == "__main__":
    # 這裡修改成你要測試的 newJobID 和 VCF 檔案
    check_paths(newJobID="rNuMzfSCBJ", file_name="main.vcf")
