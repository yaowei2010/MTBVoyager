import pandas as pd
import base64
import os
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import csv
import re
import glob
import subprocess
import base64

def generate_onconpc_input(data_dir, output_path, age=25, sex=0):
    # === 1. 讀入主欄位名稱 ===
    main_df = pd.read_csv(('/miRTI/media/reference/onconpc/data/onconpc_processed_cups_data.csv'), index_col='RANDID')
    all_columns = main_df.columns
    #/miRTI/media/patient/PfYkAJOHgC/mutSig/Assignment/Assignment_Solution/Activities/Assignment_Solution_Activities.txt
    # === 2. 載入 SBS 檔案並轉為比例 ===
    sbs_df = pd.read_csv(os.path.join(data_dir, 'mutSig/Assignment/Assignment_Solution/Activities/Assignment_Solution_Activities.txt'), sep='\t', index_col=0)
    total = sbs_df.iloc[0].sum()
    sbs_ratio = sbs_df.iloc[0] / total
    sbs_columns = [col for col in all_columns if col.startswith("SBS")]
    filtered_row = sbs_ratio.reindex(sbs_columns, fill_value=0)

    # === 3. 載入 variant 資料並計數 Gene 數 ===
    #/miRTI/media/patient/PfYkAJOHgC/potential_treatment_df.csv
    variant_df = pd.read_csv(os.path.join(data_dir, 'potential_treatment_df.csv'))
    gene_counts = variant_df['Gene'].value_counts()
    gene_count_row = pd.Series(0, index=all_columns, dtype=int)
    for gene, count in gene_counts.items():
        if gene in gene_count_row:
            gene_count_row[gene] = count

    # === 4. 載入 VCF 並提取 CNA（CN - 2）===
    vcf_files = [file for file in os.listdir(data_dir) if file.endswith(".vcf")]

    if vcf_files:
        print(f"找到 VCF 檔案: {vcf_files}")

    # 去我目標的資料夾找到所有.vcf 檔案
        for vcf_file in vcf_files:
            uploadFile_url = os.path.join(data_dir, vcf_file)  

        # # 使用 os.path.basename 解析出檔案名稱
        #     file_name = os.path.basename(uploadFile_url)  # 例如 24C00131_main.vcf
    
    vcf_df = pd.read_csv(uploadFile_url, sep='\t', comment='#', header=None)
    if vcf_df.shape[1] < 8:
        raise ValueError("VCF 檔案格式錯誤，無法找到 INFO 欄。")

    info_col = vcf_df[7]
    cnv_gene_values = {}
    for info in info_col:
        parts = dict(item.split('=') for item in info.split(';') if '=' in item)
        gene = parts.get('ANT')
        cn = parts.get('CN')
        if gene and cn:
            try:
                gene += " CNA"
                delta = float(cn) - 2
                if delta < -2 or delta > 2:
                    delta = 0
                if gene in all_columns:
                    cnv_gene_values[gene] = cnv_gene_values.get(gene, 0) + delta
            except ValueError:
                continue

    cnv_row = pd.Series(0, index=all_columns, dtype=float)
    for gene, value in cnv_gene_values.items():
        cnv_row[gene] = value

    # === 5. 合併所有資料列 ===
    combined_row = pd.Series(0, index=all_columns, dtype=float)
    combined_row.update(filtered_row)
    combined_row += gene_count_row
    combined_row += cnv_row
    mean_age = 60.362025
    std_age = 13.034576
    combined_row['Age'] = (age - mean_age) / std_age  
    combined_row['Sex'] = int(sex)

    # === 6. 存成 DataFrame 並輸出 ===
    final_df = pd.DataFrame([combined_row], index=['filtered'])
    final_df.index.name = 'RANDID'
    print(output_path)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    final_df.to_csv(output_path)
    print('make dir')

    # === 7. 顯示非零值，方便檢查 ===
    print(final_df.loc['filtered'][final_df.loc['filtered'] != 0])


@csrf_exempt
def cancertype_prediction(request):
    if request.method != 'POST':
        return JsonResponse({"error": "只接受POST請求"}, status=400)

    data = json.loads(request.body.decode('utf-8'))
    newjobid = data.get('newjobid', '')
    print("收到 newjobid:", newjobid)

    folder_path = f"/miRTI/media/patient/{newjobid}"
    cancer_type_folder = os.path.join(folder_path, "cancer type")
    cancer_type_csv = os.path.join(cancer_type_folder, "cancer_type.csv")
    prediction_summary_csv = os.path.join(cancer_type_folder, "prediction_summary.csv")
    pdf_path = os.path.join(cancer_type_folder, "filtered.pdf")

    def load_results():
        cancer_type_preview = []
        prediction_summary_preview = []
        pdf_base64 = ""

        if os.path.exists(cancer_type_csv):
            df = pd.read_csv(cancer_type_csv)
            cancer_type_preview = df.to_dict(orient="records")

        if os.path.exists(prediction_summary_csv):
            df = pd.read_csv(prediction_summary_csv)
            prediction_summary_preview = df.to_dict(orient="records")

        if os.path.exists(pdf_path):
            with open(pdf_path, "rb") as f:
                pdf_base64 = base64.b64encode(f.read()).decode("utf-8")

        return cancer_type_preview, prediction_summary_preview, pdf_base64

    if os.path.isdir(cancer_type_folder):
        # 資料夾存在，直接讀取
        cancer_type_preview, prediction_summary_preview, pdf_base64 = load_results()
        return JsonResponse({
            "exists": True,
            "cancer_type_preview": cancer_type_preview,
            "prediction_summary_preview": prediction_summary_preview,
            "pdf_base64": pdf_base64
        })

    # 資料夾不存在，先產生
    generate_onconpc_input(folder_path, cancer_type_csv)
    try:
        subprocess.run([
            "mamba", "run",
            "-n", "onconpc_conda_env",
            "python3",
            "/miRTI/media/reference/onconpc/python_code/test.py",
            "--csv", cancer_type_csv,
            "--outdir", cancer_type_folder
        ], check=True)
    except subprocess.CalledProcessError as e:
        return JsonResponse({
            "error": "執行predict_and_explain_onconpc時出錯",
            "details": str(e)
        }, status=500)

    # 產生完再讀取
    cancer_type_preview, prediction_summary_preview, pdf_base64 = load_results()
    return JsonResponse({
        "exists": False,
        "cancer_type_preview": cancer_type_preview,
        "prediction_summary_preview": prediction_summary_preview,
        "pdf_base64": pdf_base64
    })

