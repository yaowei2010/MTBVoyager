import os
import pickle
import django
#os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'uploadfunction.settings')  # 替换 'myproject.settings' 为您的实际设置模块路径
#django.setup()
import pandas as pd
#from hw1.models import existJobs
#from django.core.files.storage import FileSystemStorage 
from django.core.files.storage import FileSystemStorage
from django.shortcuts import render
from django.http import HttpResponse
from django.core.files.storage import FileSystemStorage
import os
import random
import string
import json
import pickle
import re
import ast
from django.http import JsonResponse
from django.shortcuts import render
import os
import random
import string
from django.core.files.storage import FileSystemStorage
import subprocess
import pandas as pd
from django.db import connection
import time
from django.core.serializers import serialize
import json
from django.views.decorators.csrf import csrf_exempt
import globals

import os
import pandas as pd
from django.http import JsonResponse


def run_pipeline(newjobID):
    import os
    import pandas as pd
    import json
    import re
    import ast
    
    # 设置目录路径
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.join(script_dir)

    file_path = os.path.join("media", "patient", newjobID, "somatic_result.csv")
    file_path1 = os.path.join("media", "patient", newjobID, "summary.json")
    file_path2 = os.path.join("media", "patient", newjobID, "function_df.csv")
    with open(file_path1, 'r', encoding='utf-8') as f:
        config_data = json.load(f)
    phenotype_mycancergenome = [config_data.get('diagnosis', '').strip()]
    print("hello")
    print("hello")
    print("hello")
    print(phenotype_mycancergenome)
    print(f"Checking if file exists: {file_path}")

    if os.path.exists(file_path):
        print("File exists. Attempting to read it.")
        try:
            df = pd.read_csv(file_path)
            columns_to_convert = ['MAF', 'Pathogenicity', 'Prediction', 'Avalibility']
            def safe_eval(x):
                try:
                    return ast.literal_eval(x)
                except (ValueError, SyntaxError):
                    return x  
            for col in columns_to_convert:
                df[col] = df[col].apply(lambda x: safe_eval(x) if pd.notnull(x) else x)

            data = df.to_dict(orient="records")
            print(data)
            print("this is Avalibility")
            print(data['Avalibility'])
            print("this is description")
            #print(data['Avalibility']['Description'])
            return JsonResponse(data, safe=False)

        except Exception as e:
            print(f"Error reading or processing the file: {e}")
            return JsonResponse({"error": "An error occurred while processing the file."}, status=500)








    # 如果檔案不存在，繼續執行後續邏輯
    print("File does not exist. Proceeding with the pipeline.")  # 除錯訊息




    # 定義資料夾名稱
    subfolders = {
        "CGI": ["cancer_acronyms.tsv", "processed_biomarkers.json"],
        "CIVIC": ["CIVic.2024.clinicalevidence_moodo.csv", "CIVic.assertion.2024_moodo.csv"],
        "COSMIC": ["COSMIC_database.tsv"],
        "Mycancergenome": ["MyCancerGenome_Biomarker_mondo_new.json"],
        "oncoKB": [
            "hg19_oncoKB_without_position_20200110.txt",
            "hg19_oncoKB_with_position_20200110.txt",
            "oncokb_final_database.csv"
        ],
    }

    # 掃描路徑並匹配檔案
    file_paths = {}
    for folder, expected_files in subfolders.items():
        folder_path = os.path.join(base_dir, folder)  

        if not os.path.exists(folder_path):
            print(f"目錄不存在: {folder_path}")
            continue

        matched_files = {
            file_name: os.path.join(folder_path, file_name)
            for file_name in expected_files
            if os.path.exists(os.path.join(folder_path, file_name))
        }

        if matched_files:
            file_paths[folder] = matched_files
        else:
            print(f"目錄 {folder_path} 中沒有匹配的檔案。")


    if file_paths:
        for folder, paths in file_paths.items():
            print(f"{folder}:")
            for name, path in paths.items():
                print(f"  - {name}: {path}")



    # 動態獲取各資料夾內檔案的路徑
    cgi_cancer_acronyms_path = file_paths['CGI'].get('cancer_acronyms.tsv')
    cgi_processed_biomarkers_path = file_paths['CGI'].get('processed_biomarkers.json')

    civic_clinical_evidence_path = file_paths['CIVIC'].get('CIVic.2024.clinicalevidence_moodo.csv')
    civic_assertion_path = file_paths['CIVIC'].get('CIVic.assertion.2024_moodo.csv')

    cosmic_database_path = file_paths['COSMIC'].get('COSMIC_database.tsv')

    mycancergenome_biomarker_path = file_paths['Mycancergenome'].get('MyCancerGenome_Biomarker_mondo_new.json')

    oncokb_without_position_path = file_paths['oncoKB'].get('hg19_oncoKB_without_position_20200110.txt')
    oncokb_with_position_path = file_paths['oncoKB'].get('hg19_oncoKB_with_position_20200110.txt')
    oncokb_final_database_path = file_paths['oncoKB'].get('oncokb_final_database.csv')

    # 列印所有動態路徑
    print("CGI:")
    print(f"  cancer_acronyms.tsv: {cgi_cancer_acronyms_path}")
    print(f"  processed_biomarkers.json: {cgi_processed_biomarkers_path}")
    print("CIVIC:")
    print(f"  CIVic.2024.clinicalevidence.csv: {civic_clinical_evidence_path}")
    print(f"  CIVic.assertion.2024.csv: {civic_assertion_path}")
    print("COSMIC:")
    print(f"  COSMIC_database.tsv: {cosmic_database_path}")
    print("Mycancergenome:")
    print(f"  MyCancerGenome_Biomarker.json: {mycancergenome_biomarker_path}")
    print("OncoKB:")
    print(f"  hg19_oncoKB_without_position_20200110.txt: {oncokb_without_position_path}")
    print(f"  hg19_oncoKB_with_position_20200110.txt: {oncokb_with_position_path}")
    print(f"  oncokb_final_database.csv: {oncokb_final_database_path}")




    # ---------------------------------------------------------------------------------輸入functional_df.csv 新增variant欄位--------------------------------------------------------------------------
    import pandas as pd
    folder_path = f"/miRTI/media/patient/{newjobID}"
    print(newjobID)
    vcf_files = [file for file in os.listdir(folder_path) if file.endswith(".vcf")]
    print(vcf_files)
    if vcf_files:
        print(f"找到 VCF 檔案: {vcf_files}")

    # 遍歷每個找到的 .vcf 檔案
        for vcf_file in vcf_files:
            uploadFile_url = os.path.join(folder_path, vcf_file)  # 完整檔案路徑

            file_name = os.path.basename(uploadFile_url)  # 例如 24C00131_main.vcf
            file_name_without_ext = os.path.splitext(file_name)[0]  # 例如 24C00131_main

    vep_annovar_file=f'/miRTI/media/patient/{newjobID}/{file_name_without_ext}_vep_annovar_merge.csv'
    functional_df=f'/miRTI/media/patient/{newjobID}/functional_df.csv'
    print(vep_annovar_file)
    store_file =f'/miRTI/media/patient/{newjobID}/drug_with_annotated_file.csv'

    input_file =vep_annovar_file  
    output_file = store_file


    df = pd.read_csv(input_file, encoding='ISO-8859-1', low_memory=False)
    print(df)
    # 建立三字母到單字母的對照表
    three_to_one = {
        "Ala": "A", "Cys": "C", "Asp": "D", "Glu": "E", "Phe": "F", "Gly": "G", 
        "His": "H", "Ile": "I", "Lys": "K", "Leu": "L", "Met": "M", "Asn": "N", 
        "Pro": "P", "Gln": "Q", "Arg": "R", "Ser": "S", "Thr": "T", "Val": "V", 
        "Trp": "W", "Tyr": "Y", "Ter": "*"
    }

    # 提取變異的前半部分和後半部分，並將結果賦值到兩個新欄位
    df[['variant_start', 'variant_end']] = df['enasmbl_HGVSp'].str.extract(r'p\.([A-Za-z]{3}\d+)([A-Za-z]{3})?')
    print(df)
    # 定義轉換函數，將前後兩部分轉換為單字母並組合
    def convert_to_single_letter(row):
        if pd.notnull(row['variant_start']):
            # 前半部分 (e.g., Trp251)
            amino_acid = row['variant_start'][:3]
            position = row['variant_start'][3:]
            single_letter_start = three_to_one.get(amino_acid, amino_acid)
            result = f"{single_letter_start}{position}"
            
            # 後半部分 (e.g., Arg)，如果存在且對應到單字母表
            if pd.notnull(row['variant_end']) and row['variant_end'] in three_to_one:
                single_letter_end = three_to_one[row['variant_end']]
                result += single_letter_end
            
            return result
        return None

    # 應用轉換函數以生成最終的 variant 欄位
    df['variant'] = df.apply(convert_to_single_letter, axis=1)

    # 移除中間的輔助欄位
    df.drop(columns=['variant_start', 'variant_end'], inplace=True)

    # 顯示結果
    print(df[['enasmbl_HGVSp', 'variant']])

    df = df[df["Func.refGene"].isin(["exonic", "splicing"])]
    # df = df[df["CLNSIG"].isin(["Pathogenic"])]

    print(df)
    print("THIS IS CLINSIG")
    print("THIS IS CLINSIG")
    print("THIS IS CLINSIG")
    print("THIS IS CLINSIG")
    print("THIS IS CLINSIG")
    print("THIS IS CLINSIG")
    print("THIS IS CLINSIG")
    print("THIS IS CLINSIG")
    # 保存處理後的資料到新的 CSV 檔案，保留所有原始資料並新增 variant 欄位
    df.to_csv(output_file, index=False)
    import json

    # -------------------------------------------------------------CIVIC-----------------------------------------------------------------------------------------------------------
    # -------------------------------------------------------------CIVIC-----------------------------------------------------------------------------------------------------------
    import pandas as pd

    CIVICdb1 = pd.read_csv(civic_assertion_path, sep=',', header=0, encoding='ISO-8859-1')
    CIVICdb1['Mark'] = (CIVICdb1['gene'] + " " + CIVICdb1['variant']).str.strip().str.lower()
    CIVICdb1 = CIVICdb1[['Mark','gene','variant','chromosome','start','end','reference_bases','variant_bases','chromosome2','start2','end2','variant_types','hgvs_descriptions','variant_aliases','disease','phenotypes','therapies','assertion_type','assertion_type','assertion_direction','significance','acmg_codes','amp_category','nccn_guideline','assertion_summary','assertion_description','combined_disease_name']]
    CIVICdb2 = pd.read_csv(civic_clinical_evidence_path , sep=',', header=0, encoding='ISO-8859-1')

    CIVICdb2['Mark'] = (CIVICdb2['gene'] + " " + CIVICdb2['variant']).str.strip().str.lower()
    CIVICdb2 = CIVICdb2[['Mark','gene','variant','chromosome','start','end','reference_bases','variant_bases','chromosome2','start2','end2','variant_types','hgvs_descriptions','variant_aliases','clinvar_ids','disease','phenotypes','therapies','evidence_type','evidence_direction','evidence_level','significance','evidence_statement','citation','combined_disease_name']]
    input_df = pd.read_csv(store_file, encoding='ISO-8859-1') 


    def changeMark(gene, variant, tag, geneA=None, geneB=None):
        if tag == 'SNV':  # Variant Example: ERBB2.pT862A
            snv = variant.split('.', 1)[1]
            snv = snv.strip()  # 去除多餘空白
            if len(snv) == 0:
                return ""  # 若去除空白後無任何字元，則返回空字串
            return f"{gene} {snv.replace('p', '')}".strip().lower()
        elif tag == 'Fusion':
            if geneA and geneB:
                return f"{geneA} {geneB}::{geneA}".strip().lower()
            else:
                return f"{gene} Fusion".strip().lower()
        elif tag == 'CNV':  # ERBB2 Amplification / Deletion
            return f"{gene} {variant}".strip().lower()
        elif tag == 'SV':
            return f"{gene} {variant}".strip().lower()
        elif tag == 'Mutation':
            return f"{gene} Mutation".strip().lower()
        elif tag == 'splice':
            return f"{gene} splice".strip().lower()

    def findCIViC(query, assertion, evidence, phenotype=None):
        # 標準化查詢
        query = query.strip().lower()  
        print(f"Query: {query}")
        print(f"Available Marks: {assertion['Mark'].unique()[:5]}")  # 檢查前五個 Mark 以驗證格式

        def filter_result(df, query, phenotype=None):
            result = df[df['Mark'] == query]
            if phenotype:  # 如果有提供 phenotype 則進行篩選
                result = result[result['phenotypes'].str.contains(phenotype, case=False, na=False)]
            result = result[~pd.isna(result['therapies'])]  # 移除沒有藥物治療的紀錄
            return result

        # 嘗試在 assertion 中查詢
        result = filter_result(assertion, query, phenotype)
        if not result.empty:
            # 將 amp_category 映射成相應的階級
            ranks = result['amp_category'].map({
                'Tier I - Level A': 'Tier 1A',
                'Tier I - Level B': 'Tier 1B',
                'Tier II - Level C': 'Tier 2C',
                'Tier II - Level D': 'Tier 2D'
            })
            result = result[['Mark', 'therapies', 'disease', 'assertion_description']]
            result['Rank'] = ranks
            result.columns = ['Variant', 'Therapy', 'Disease', 'Detail', 'Rank']
            result['ClinicalDB'] = 'CIViC-assertion'
            return result

        # 如果 assertion 沒有找到，再去 evidence 中查找
        result = filter_result(evidence, query, phenotype)
        if not result.empty:
            ranks = result['evidence_level'].map({
                'A': 'Tier 1A',
                'B': 'Tier 1B',
                'C': 'Tier 2C',
                'D': 'Tier 2D',
                'E': 'Tier 3'
            }).fillna('Tier 4')
            result = result[['Mark', 'therapies', 'disease', 'evidence_statement']]
            result['Rank'] = ranks
            result.columns = ['Variant', 'Therapy', 'Disease', 'Detail', 'Rank']
            result['ClinicalDB'] = 'CIViC-evidence'
            return result

        print(f"No match found for query: {query}")
        return "Not found clinical evidence record"
    def process_csv(input_file, CIVICdb1, CIVICdb2, phenotype=None):
        import pandas as pd

        # 讀取 CSV 文件
        df = pd.read_csv(input_file, encoding='ISO-8859-1', low_memory=False)

        # 新增欄位
        df['CIVIC_result'] = 'Not found clinical evidence record'
        df['Match'] = ''
        print(f"🎯 Global Phenotype filter = {phenotype if phenotype else 'None (no filtering)'}")

        # 遍歷每一行資料
        for idx, row in df.iterrows():
            try:
                gene = row['Gene.refGene'] if pd.notna(row['Gene.refGene']) else None
                tag = row['VARIANT_CLASS'] if pd.notna(row['VARIANT_CLASS']) else None
                variant = f"{row['Gene.refGene']}.p{row['variant']}" if pd.notna(row['Gene.refGene']) and pd.notna(row['variant']) else None

                if not gene or not tag or not variant:
                    print(f"⚠️ Skipping row {idx} due to missing gene, tag, or variant.")
                    continue

                query = changeMark(gene, variant, tag)
                print(f"🧬 Row {idx}: Query = {query}")

                if not phenotype:
                    result_assertion = CIVICdb1[CIVICdb1['Mark'] == query]
                    print(f"🔍 Assertion match before phenotype: {len(result_assertion)}")
                    if not result_assertion.empty:
                        if 'combined_disease_name' in result_assertion.columns:
                            print(f"🧾 Assertion diseases: {result_assertion['combined_disease_name'].tolist()}")
                        else:
                            print("⚠️ No 'combined_disease_name' column found in assertion result")
                        result = {
                            'Variant': query,
                            'Therapy': result_assertion.iloc[0].get('therapies', 'N/A'),
                            'Disease': result_assertion.iloc[0].get('disease', 'N/A'),
                            'Detail': result_assertion.iloc[0].get('assertion_description', 'N/A'),
                            'Rank': result_assertion.iloc[0].get('amp_category', 'N/A'),
                            'ClinicalDB': 'CIViC-assertion'
                        }
                        df.at[idx, 'CIVIC_result'] = str(result)
                        df.at[idx, 'Match'] += 'CIViC Match; '
                        continue

                    result_evidence = CIVICdb2[CIVICdb2['Mark'] == query]
                    print(f"🔍 Evidence match before phenotype: {len(result_evidence)}")
                    if not result_evidence.empty:
                        if 'combined_disease_name' in result_evidence.columns:
                            print(f"🧾 Evidence diseases: {result_evidence['combined_disease_name'].tolist()}")
                        else:
                            print("⚠️ No 'combined_disease_name' column found in evidence result")
                        result = {
                            'Variant': query,
                            'Therapy': result_evidence.iloc[0].get('therapies', 'N/A'),
                            'Disease': result_evidence.iloc[0].get('disease', 'N/A'),
                            'Detail': result_evidence.iloc[0].get('evidence_statement', 'N/A'),
                            'Rank': result_evidence.iloc[0].get('evidence_level', 'N/A'),
                            'ClinicalDB': 'CIViC-evidence'
                        }
                        df.at[idx, 'CIVIC_result'] = str(result)
                        df.at[idx, 'Match'] += 'CIViC Match; '
                else:
                    result_evidence = CIVICdb2[CIVICdb2['Mark'] == query]
                    print(f"🔍 Evidence match before phenotype: {len(result_evidence)}")
                    if not result_evidence.empty and 'combined_disease_name' in result_evidence.columns:
                        print(f"🧾 Evidence diseases: {result_evidence['combined_disease_name'].tolist()}")
                        result_evidence = result_evidence[
                            result_evidence['combined_disease_name'].str.contains(phenotype, na=False)
                        ]
                        print(f"🎯 Evidence match after phenotype: {len(result_evidence)}")
                    else:
                        print(f"⚠️ Row {idx}: No evidence match or missing combined_disease_name column")

                    if not result_evidence.empty:
                        result = {
                            'Variant': query,
                            'Therapy': result_evidence.iloc[0].get('therapies', 'N/A'),
                            'Disease': result_evidence.iloc[0].get('disease', 'N/A'),
                            'Detail': result_evidence.iloc[0].get('evidence_statement', 'N/A'),
                            'Rank': result_evidence.iloc[0].get('evidence_level', 'N/A'),
                            'ClinicalDB': 'CIViC-evidence'
                        }
                        df.at[idx, 'CIVIC_result'] = str(result)
                        df.at[idx, 'Match'] += 'CIViC Match; '
                        continue

                    result_assertion = CIVICdb1[CIVICdb1['Mark'] == query]
                    print(f"🔍 Assertion match before phenotype: {len(result_assertion)}")
                    if not result_assertion.empty and 'combined_disease_name' in result_assertion.columns:
                        print(f"🧾 Assertion diseases: {result_assertion['combined_disease_name'].tolist()}")
                        result_assertion = result_assertion[
                            result_assertion['combined_disease_name'].str.contains(phenotype, na=False)
                        ]
                        print(f"🎯 Assertion match after phenotype: {len(result_assertion)}")
                    else:
                        print(f"⚠️ Row {idx}: No assertion match or missing combined_disease_name column")

                    if not result_assertion.empty:
                        result = {
                            'Variant': query,
                            'Therapy': result_assertion.iloc[0].get('therapies', 'N/A'),
                            'Disease': result_assertion.iloc[0].get('disease', 'N/A'),
                            'Detail': result_assertion.iloc[0].get('assertion_description', 'N/A'),
                            'Rank': result_assertion.iloc[0].get('amp_category', 'N/A'),
                            'ClinicalDB': 'CIViC-assertion'
                        }
                        df.at[idx, 'CIVIC_result'] = str(result)
                        df.at[idx, 'Match'] += 'CIViC Match; '
            except Exception as e:
                print(f"❌ Error on row {idx}: {e}")

        # 清除尾端分號
        df['Match'] = df['Match'].str.rstrip('; ')
        print("Finished CSV processing. Saving results...")
        matched = df[df['CIVIC_result'] != 'Not found clinical evidence record']
        print(f"✅ 共找到 {len(matched)} 筆有 CIVIC 記錄的變異")
        result_indices = matched.index.tolist()
        print(f"✅ Rows with CIVIC results: {result_indices}")

        # 儲存結果
        df.to_csv(input_file, index=False)
        print("✅ CIVIC 資料查詢結果已保存至原始 CSV。")

    print("this is CIVICdb2......................................................................")
    print(CIVICdb2)
    print("CIVICdb1 columns:", CIVICdb1.columns.tolist())





    # def process_csv(input_file, CIVICdb1, CIVICdb2):
    #     # 讀取 CSV 文件
    #     df = pd.read_csv(input_file, encoding='ISO-8859-1', low_memory=False)

    #     # 新增 CIVIC_result 欄位
    #     df['CIVIC_result'] = 'Not found clinical evidence record'
    #     df['Match'] = ''
    #     # 遍歷每一行資料
    #     print("Starting CSV processing...")
    #     for idx, row in df.iterrows():
    #         gene = row['Gene.refGene'] if pd.notna(row['Gene.refGene']) else None
    #         tag = row['VARIANT_CLASS'] if pd.notna(row['VARIANT_CLASS']) else None
    #         variant = f"{row['Gene.refGene']}.p{row['variant']}" if pd.notna(row['Gene.refGene']) and pd.notna(row['variant']) else None
            
    #         # 如果其中一個值為空，則跳過
    #         if not gene or not tag or not variant:
    #             print(f"Skipping row {idx} due to missing gene, tag, or variant.")
    #             continue

    #         # 使用 changeMark 函數生成查詢字串
    #         query = changeMark(gene, variant, tag)
    #         print(f"Row {idx}: Generated query = {query}")
            
    #         # 在 CIVICdb1 中查找
    #         result_assertion = CIVICdb1[CIVICdb1['Mark'] == query]
    #         print(f"Row {idx}: Searching CIVICdb1 for {query}")
            
    #         # if not result_assertion.empty:
    #         #     print(f"Row {idx}: Found match in CIVICdb1, updating row {idx}")
                
    #         #     df.at[idx, 'CIVIC_result'] = result_assertion.iloc[0].to_dict()
    #         #     df.at[idx, 'Match'] += 'CIViC Match; '
    #         #     continue
    #         if not result_assertion.empty:
    #             print(f"Row {idx}: Found match in CIVICdb1, updating row {idx}")
    #             result = {
    #                 'Variant': query,
    #                 'Therapy': result_assertion.iloc[0].get('therapies', 'N/A'),
    #                 'Disease': result_assertion.iloc[0].get('disease', 'N/A'),
    #                 'Detail': result_assertion.iloc[0].get('assertion_description', 'N/A'),
    #                 'Rank': result_assertion.iloc[0].get('amp_category', 'Unknown'),
    #                 'ClinicalDB': 'CIViC'
    #             }
    #             df.at[idx, 'CIVIC_result'] = str(result)
    #             df.at[idx, 'Match'] += 'CIViC Match; '
    #             continue

    #         # 在 CIVICdb2 中查找

    #         result_evidence = CIVICdb2[CIVICdb2['Mark'] == query]
    #         print(f"Row {idx}: Searching CIVICdb2 for {query}")
    #         # if not result_evidence.empty:
    #         #     print(f"Row {idx}: Found match in CIVICdb2, updating row {idx}")
    #         #     df.at[idx, 'CIVIC_result'] = result_evidence.iloc[0].to_dict()
    #         #     df.at[idx, 'Match'] += 'CIViC Match; '
    #         if not result_evidence.empty:
    #             print(f"Row {idx}: Found match in CIVICdb2, updating row {idx}")
    #             result = {
    #                 'Variant': query,
    #                 'Therapy': result_evidence.iloc[0].get('therapies', 'N/A'),
    #                 'Disease': result_evidence.iloc[0].get('disease', 'N/A'),
    #                 'Detail': result_evidence.iloc[0].get('evidence_statement', 'N/A'),
    #                 'Rank': result_evidence.iloc[0].get('evidence_level', 'Unknown'),
    #                 'ClinicalDB': 'CIViC'
    #             }
    #             df.at[idx, 'CIVIC_result'] = str(result)
    #             df.at[idx, 'Match'] += 'CIViC Match; '
    #     df['Match'] = df['Match'].str.rstrip('; ')
    #     print("Finished CSV processing. Saving results...")
    #     # 打印所有有 CIVIC 結果的行數
    #     result_indices = df[df['CIVIC_result'] != 'Not found clinical evidence record'].index.tolist()
    #     print(f"Rows with CIVIC results: {result_indices}")
    #     # 保存到新的 CSV 文件
    #     df.to_csv(input_file, index=False)





    process_csv(store_file, CIVICdb1, CIVICdb2,phenotype=phenotype_mycancergenome)
    print("CIViC 資料查詢結果已成功保存至 CSV。")


    # ----------------------------------------------------------------------------------MYCANCERGENOME--------------------------------------------------
    import json
    import pandas as pd
    input_df = pd.read_csv(store_file, encoding='ISO-8859-1') 
    # 讀取 JSON 檔案
    
    with open(mycancergenome_biomarker_path , 'r', encoding='utf-8') as file:
        myCancerGenome = json.load(file)
    files_to_check = [
        store_file,
        mycancergenome_biomarker_path
    ]

    # 檢查是否存在
    for file in files_to_check:
        if os.path.exists(file):
            print(f"✅ 檔案存在: {file}")
        else:
            print(f"❌ 檔案不存在: {file}")
# ── AMP Tier 判定工具 ─────────────────────────────────────────────
    def determine_amp_tier_from_clinical_setting(setting_list):
        if not setting_list:
            return "Tier Unknown"
        txt = ", ".join(setting_list).lower()

        if "(fda" in txt:
            return "Tier 1A"
        if "(nccn" in txt or "guideline" in txt:
            return "Tier 1B"

        # 新增 " mcg" 關鍵字 ⇒ 2C
        if " mcg" in txt or "metastatic (mcg" in txt:
            return "Tier 2D"

        if "clinical trial" in txt or "ongoing" in txt or "nct" in txt:
            return "Tier 2D"
        return "Tier Unknown"

    # 更正類別名稱
    class searchMyCancerGenome:
        def __init__(self, gene, variant, tag, reference, phenotypes=None, geneA=None, geneB=None):
            self.gene = gene
            self.variant = variant
            self.tag = tag
            self.reference = reference
            self.phenotypes = phenotypes if phenotypes else []  # 設置 phenotype 列表
            self.geneA = geneA
            self.geneB = geneB

        # 根據 tag 改變標記格式
        def changeMark(self):
            if self.tag == 'SNV':  # 例如：ERBB2.pT862A
                snv = self.variant.split('.')[1]
                return self.gene + ' ' + snv.replace('p', '')
            elif self.tag == 'Fusion':
                if self.geneA and self.geneB:
                    return self.geneA + '-' + self.geneB + ' Fusion'
                else:
                    return self.gene + ' Fusion'
            elif self.tag == 'CNV':  # 例如：ERBB2 放大
                return self.gene + ' ' + self.variant
            elif self.tag == 'SV':
                return self.gene + ' ' + self.variant
            elif self.tag == 'Mutation':
                return self.gene + ' Mutation'
            elif self.tag == 'splice':
                return self.gene + ' splice'


                # 查找 MyCancerGenome 資料
        def findMyCancerGenome(self):
            therapies_data = []
            query = self.changeMark()

            for var_key, var_detail in self.reference.items():
                if query not in var_key:
                    continue

                # 1) Biomarker-Directed Therapies
                for therapy, t_detail in var_detail.get("Biomarker-Directed Therapies", {}).items():
                    # phenotype 篩選



                    disease_keys = list(t_detail.get("disease", {}).keys())
                    # debug log
                    print(f"🔍 查詢變異：{query}")
                    print(f"📌 輸入 phenotype：{self.phenotypes}")
                    print(f"📌 MCG disease keys：{disease_keys}")

                    if self.phenotypes:
                        match_found = any(
                            ph.strip().lower() == d.strip().lower()
                            for ph in self.phenotypes
                            for d in disease_keys
                        )
                        print(f"🎯 是否命中：{match_found}")
                        if not match_found:
                            continue



                    
                    for dis, dis_info in t_detail.get("disease", {}).items():
                        clin = dis_info.get("Clinical Setting(s)", [])
                        tier = determine_amp_tier_from_clinical_setting(clin)
                        therapies_data.append(
                            dict(Variant=query, Therapy=therapy,
                                Disease=dis, Rank=tier, Detail=dis_info)
                        )

                # 2) Clinical Trials → Tier 2D
                if var_detail.get("Clinical Trials"):
                    if self.phenotypes and not any(
                        ph.lower() in d.lower()
                        for ph in self.phenotypes
                        for d in var_detail.get("Significant Associated Diseases", [])
                    ):
                        continue
                    therapies_data.append(
                        dict(Variant=query, Therapy="ClinicalTrial",
                            Disease="", Rank="Tier 2D",
                            Detail=var_detail["Clinical Trials"])
                    )

            return pd.DataFrame(therapies_data) if therapies_data else None
        # # 查找 MyCancerGenome 資料
        # def findMyCancerGenome(self):
        #     therapies_data = []
        #     query = self.changeMark()
        #     if not isinstance(self.reference, dict):
        #         print(f"Error: self.reference is not a dictionary. Found type: {type(self.reference)}")
        #         return None
        #     # 使用 changeMark 格式化查詢，搜尋資料
        #     for variant, details in self.reference.items():
        #         if query in variant:
        #             # 檢查 'Biomarker-Directed Therapies'
        #             if 'Biomarker-Directed Therapies' in details and details['Biomarker-Directed Therapies']:
        #                 for therapy, therapy_details in details['Biomarker-Directed Therapies'].items():
        #                     # 如果有 phenotype，進行篩選
        #                     if self.phenotypes:
        #                         phenotype_match = False
        #                         for phenotype in self.phenotypes:
        #                             if 'disease' in therapy_details:
        #                                 for disease in therapy_details['disease'].keys():
        #                                     if phenotype.lower() in disease.lower():
        #                                         phenotype_match = True
        #                                         break
        #                         if not phenotype_match:
        #                             continue  # 若無匹配 phenotype，則跳過該療法

        #                     therapy_info = {'Variant': query, 'Therapy': therapy, 'Rank': 'Tier 1A'}
        #                     diseases = therapy_details.get('disease', [])
        #                     if diseases:
        #                         for key, value in therapy_details['disease'].items():
        #                             therapy_info['Disease'] = key
        #                             therapy_info['Detail'] = value
        #                         therapies_data.append(therapy_info)
        #             # 檢查 'Clinical Trials'
        #             elif 'Clinical Trials' in details and details['Clinical Trials']:
        #                 # 如果有 phenotype，進行篩選
        #                 if self.phenotypes:
        #                     phenotype_match = False
        #                     for phenotype in self.phenotypes:
        #                         if 'Significant Associated Diseases' in details:
        #                             for disease in details['Significant Associated Diseases']:
        #                                 if phenotype.lower() in disease.lower():
        #                                     phenotype_match = True
        #                                     break
        #                     if not phenotype_match:
        #                         continue  # 若無匹配 phenotype，則跳過

        #                 therapy_info = {'Variant': query, 'Therapy': 'ClinicalTrial', 'Rank': 'Tier 2D', 'Disease': '', 'Detail': details['Clinical Trials']}
        #                 therapies_data.append(therapy_info)
            
        #     # 若找到療法資料，返回 DataFrame
        #     if therapies_data:
        #         df = pd.DataFrame(therapies_data)
        #         return df
        #     else:
        #         print("No therapies found for the given variant.")
        #         return None



    # 將查詢結果添加到 DataFrame 的邏輯
    results = []
    

    for index, row in input_df.iterrows():
        gene = row['Gene.refGene'].strip()
        variant_value = row['variant'].strip() if 'variant' in row and pd.notnull(row['variant']) else ''
        data = f"{gene}.p{variant_value}"  # 組合成完整的變異格式
        tag = row['VARIANT_CLASS'].strip()  # 提取標籤

        # 使用 SearchMyCancerGenome 類進行搜尋
        search_instance = searchMyCancerGenome(gene, data, tag, myCancerGenome,phenotype_mycancergenome)

        try:
            search_instance.changeMark()  # 呼叫變異標記轉換函數
            df = search_instance.findMyCancerGenome()  # 查詢 MyCancerGenome

            if df is not None:
                # 如果有結果，將 DataFrame 轉換為字典並存入結果
                results.append(df.to_dict(orient='records'))
                input_df.at[index, 'Match'] = input_df.at[index, 'Match'] + ', MyCancerGenome Match' if pd.notna(input_df.at[index, 'Match']) else 'MyCancerGenome Match'
            else:
                results.append(None)  # 沒有結果則追加 None

        except Exception as e:
            print(f"Error processing {data}: {e}")
            results.append(None)  # 如果出現錯誤也追加 None
    print("✅ MyCancerGenome finished processing. Proceeding to COSMIC...")
    # 將結果轉換為 JSON 格式並追加到輸入的 DataFrame 中
    input_df['MyCancerGenome_Result'] = results
    input_df['MyCancerGenome_Result'] = input_df['MyCancerGenome_Result'].apply(
        lambda x: json.dumps(x, ensure_ascii=False) if x is not None else "No result"
    )

    # 檢測資料長度，如果超過限制，則分到新的欄位
    max_length = 32000  # 設定欄位的合理長度限制
    for index in input_df.index:
        result_str = input_df.at[index, 'MyCancerGenome_Result']
        if len(result_str) > max_length:
            # 如果資料超過長度，將多餘的資料分到新欄位中
            input_df.at[index, 'MyCancerGenome_Result'] = result_str[:max_length]
            if 'MyCancerGenome_Result_2' not in input_df.columns:
                input_df['MyCancerGenome_Result_2'] = ""  # 動態創建新的欄位
            input_df.at[index, 'MyCancerGenome_Result_2'] = result_str[max_length:]

    # 將結果寫回 CSV 檔案
    # output_path = r"C:\Users\a5619\OneDrive\桌面\生物及金融大數據實驗室\林醫師VCF團隊\20240820資料\searchCIViC\22W00198_S33_gpu_HF_final_merge_variant_lastest_version1.csv"
    input_df.to_csv(store_file, encoding='ISO-8859-1', index=False)

    print("結果已成功保存至 CSV。")

    # ---------------------------------------------------------------------------------COSMIC------------------------------------------------------------

    import pandas as pd
    import re
    import json

    df = pd.read_csv(cosmic_database_path , sep='\t', header=0, low_memory=False)
    print("cosmic start")
    print("cosmic start")
    print("cosmic start")
    print("cosmic start")

    def process_expression(expression):
        def parse_or(part):
        
            return part.split(' or ')

        def parse_and(lhs_items, rhs_items):
    
            results = [f"{item}:{rhs_item}" for item in lhs_items for rhs_item in rhs_items]
            return results

        def parse_all_and(items):
        
            if not items:
                return []
            results = [items[0]]
            for item in items[1:]:
                results = [f"{result}:{item}" for result in results]
            return results

        def simplify_parentheses(expression):
        
            pattern = re.compile(r'\(([^)]+)\)')
            while '(' in expression:
                match = pattern.search(expression)
                if match:
                    inner_expression = match.group(1)
                    if 'and' in inner_expression and 'or' not in inner_expression:
                        simplified_expression = inner_expression.replace(' and ', ':')
                        expression = expression[:match.start()] + simplified_expression + expression[match.end():]
                    else:
                        break
                else:
                    break
            return expression

        def handle_parentheses(expression):
            
            pattern = re.compile(r'\(([^)]+)\) and \(([^)]+)\)')
            while '(' in expression:
                match = pattern.search(expression)
                if match:
                    inner_expression1 = match.group(1)
                    inner_expression2 = match.group(2)
                    lhs_items = parse_or(inner_expression1)
                    rhs_items = parse_or(inner_expression2)
                    result = ', '.join(parse_and(lhs_items, rhs_items))
                    expression = expression[:match.start()] + result + expression[match.end():]
                else:
                    break
            return expression

        def extract_parts(expression):
        
            if 'and' in expression:
                if 'or' in expression:
                    pattern = re.compile(r'\(([^)]+)\) and (.+)')
                    match = pattern.match(expression)
                    if match:
                        or_part = match.group(1).strip()
                        and_part = match.group(2).strip()
                        return or_part, and_part.split(' and ')
                    else:
                        return None, expression.split(' and ')
                else:
                    return None, expression.split(' and ')
            else:
                return expression, None

        def remove_unnecessary_parentheses(expression):
        
            pattern = re.compile(r'\(([^)]+)\)')
            simplified_expression = pattern.sub(r'\1', expression)
            if simplified_expression.startswith('(') and simplified_expression.endswith(')'):
                simplified_expression = simplified_expression[1:-1]
            return simplified_expression

        def process_until_done(expression):
            prev_expression = ""
            iteration_count = 0 
            while expression != prev_expression and iteration_count < 100:
                iteration_count += 1
                prev_expression = expression
                expression = simplify_parentheses(expression)
                expression = handle_parentheses(expression)
                or_part, and_parts = extract_parts(expression)
                if or_part:
                    lhs_items = parse_or(or_part)
                    if and_parts:
                        results = parse_and(lhs_items, and_parts)
                    else:
                        results = lhs_items
                    results = [remove_unnecessary_parentheses(result) for result in results]
                else:
                    results = parse_all_and(and_parts)
                
                expression = ', '.join(results)
                expression = remove_unnecessary_parentheses(expression)
            
            if iteration_count >= 100:
                raise ValueError("Too many iterations, possible infinite loop.")

        
            result_dict = {item: {} for item in expression.split(', ')}
            return result_dict

        try:
            final_result = process_until_done(expression)
            return final_result
        except Exception as e:
            print(f"Error processing expression: {e}")
            return expression




    '''
    def parse_mutation_remark(remark):
        parsed = {}
        
        # Check if 'and' is in the remark to decide if we need nested structure
        if ' and ' in remark:
            # Split on 'and' to separate out the different layers
            and_parts = [part.strip() for part in remark.split(' and ')]
            print('-----',and_parts,'-----')    
            for part in and_parts:
                if '(' in part and ')' in part:
                    # Handle content inside parentheses
                    inner_or_parts = re.findall(r'\(([^)]+)\)', part)[0].split(' or ')
                    for item in inner_or_parts:
                        item = item.strip()
                        if item not in parsed:
                            parsed[item] = {}
                else:
                    part = part.strip()
                    # Assign nested entry for each 'and' part after handling 'or' parts
                    for key in parsed:
                        parsed[key][part] = {}
        else:
            # If no 'and', just split on 'or' and add to parsed dictionary
            or_parts = remark.split(' or ')
            for part in or_parts:
                parsed[part.strip()] = {}
        


        return parsed
    '''
    # Test the function with the provided input


    # 假設 df 是您的資料表
    mutation_dict = {}
    
    for _, row in df.iterrows():
        gene = row['GENE']
        remark = row['MUTATION_REMARK']
        therapies = row['DRUG_COMBINATION']
        combined_disease_name = row['combined_disease_name']  # 新增這行來獲取 combined_disease_name 欄位

        # 建立 additional_info 字典，包含所有需要的欄位
        additional_info = {
            'Therapies': therapies,
            'TRIAL_STATUS': row['TRIAL_STATUS'],
            'ACTIONABILITY_RANK': row['ACTIONABILITY_RANK'], 
            'CLASSIFICATION_ID': row['CLASSIFICATION_ID'],
            'combined_disease_name': combined_disease_name  # 新增 combined_disease_name 欄位
        }

        if pd.notna(gene) and pd.notna(remark):
            # 處理 MUTATION_REMARK，得到 parsed_remark
            parsed_remark = process_expression(remark)

            if gene not in mutation_dict:
                mutation_dict[gene] = {}

            # 更新 mutation_dict
            for key, value in parsed_remark.items():
                if key not in mutation_dict[gene]:
                    mutation_dict[gene][key] = value

                # 添加額外信息到最內層字典
                current_level = mutation_dict[gene][key]
                
                # 確保最內層是字典
                if not isinstance(current_level, dict):
                    mutation_dict[gene][key] = {}
                    current_level = mutation_dict[gene][key]

                # 更新最內層字典
                current_level.update(additional_info)
                

    # 将结果保存为 JSON 文件
    mutation_json = json.dumps(mutation_dict, indent=4)
    with open('/miRTI/media/reference/single_snp/mutation_dictionary_query.json', 'w') as f:
        f.write(mutation_json)

    def query_mutation_dict(mutation_dict, gene_variant_str, phenotype=None):
        results = {}

        for gene, mutations in mutation_dict.items():
            for key, value in mutations.items():
                # 檢查基因變異是否符合
                if gene_variant_str == key:
                    if phenotype:
                        # 獲取 combined_disease_name 欄位的值
                        combined_disease_names = value.get('combined_disease_name', '')

                        # 將 combined_disease_name 分割，去除多餘空白，轉換為小寫
                        phenotypes_list = [item.strip().lower() for item in combined_disease_names.split('/')]

                        # 檢查查詢的 phenotype 是否存在於 phenotypes_list 中
                        if phenotype.strip().lower() in phenotypes_list:
                            results[gene] = mutations[key]
                    else:
                        # 如果沒有指定 phenotype，就加入結果
                        results[gene] = mutations[key]


        return results or "No matching mutation found."

    # # 查询示例
    # query_result_1 = query_mutation_dict(mutation_dict, "BRAF_V600E")
    # print(query_result_1)

    # query_result_2 = query_mutation_dict(mutation_dict, ["KRAS_G12D", "TP53_R273H"])
    # print(query_result_2)

    # 读取输入 CSV 文件
    input_csv_file = r"C:\Users\a5619\OneDrive\桌面\生物及金融大數據實驗室\林醫師VCF團隊\20240820資料\searchCIViC\22W00198_S33_gpu_HF_final_merge_variant_lastest_version1.csv"
    input_df = pd.read_csv(store_file, encoding='ISO-8859-1')

    # 添加 COSMIC_Result 列
    input_df['COSMIC_Result'] = ""
    input_df['Match'] = input_df.get('Match', "")
    # 遍历输入文件并查询
    for index, row in input_df.iterrows():
        gene = row['Gene.refGene']  # 获取基因名称
        if pd.notnull(variant_value) and isinstance(variant_value, str):
            variant_replace = variant_value.strip()
        else:
            variant_replace = ''

        # 构建类似 BRAF_V600E 的查询字符串
        gene_variant_str = f"{gene}_{variant_value}"
        print(f"COSMIC: {gene_variant_str}")
          # 查询 mutation_dict，获取结果
        query_result = query_mutation_dict(mutation_dict, gene_variant_str)
        print(query_result)
        # 将查询结果转为字符串格式，以便写入 CSV
        if isinstance(query_result, dict):
            # 将字典转换为 JSON 字符串格式
            result_str = json.dumps(query_result, ensure_ascii=False)
            input_df.at[index, 'COSMIC_Result'] = result_str
            input_df.at[index, 'Match'] = (input_df.at[index, 'Match'] + ', ' if input_df.at[index, 'Match'] else '') + 'COSMIC Match'
        else:
            # 直接使用查询结果字符串
            result_str = query_result

        # 将查询结果存入 'COSMIC_Result' 列
        input_df.at[index, 'COSMIC_Result'] = result_str


    input_df.to_csv(store_file, index=False, encoding='ISO-8859-1')

    # 打印 DataFrame 结果
    print(input_df)



    # ------------------------------------------------------------------------------------uncleKB-----------------------------------------------------------

    import pandas as pd
    import ast

    def parse_biomarker_info(biomarker_info):
        # 將資料以 ; 分隔
        fields = biomarker_info.split(';')
        data = {}
        
        for field in fields:
            try:
                key, value = field.split('=')
                data[key] = value.split('|')  # 使用 | 分隔多個值
            except ValueError:
                # 如果分隔失敗，跳過該欄位
                continue
        
        # 確保所有必要的鍵存在
        required_keys = ['Biomarker', 'Evidence_level', 'Drug', 'Tumor_type']
        for key in required_keys:
            if key not in data:
                data[key] = ['NA']
        
        biomarker = data['Biomarker']
        evidence_levels = data['Evidence_level']
        drugs = data['Drug']
        tumor_types = data['Tumor_type']
        
        paired_results = []
        for ev, dr, tt in zip(evidence_levels, drugs, tumor_types):
            tt = tt.replace('_', ' ')
            drug_list = dr.split('/')
            tumor_list = tt.split('/')
            
            paired_results.append({
                'Biomarker': biomarker,
                'Evidence_level': ev,
                'Drug': drug_list,
                'Tumor_type': tumor_list
            })
        
        return paired_results

    def update_actionability(row):
        # 檢查 row 是否是字串形式，如果是則轉換成列表
        if isinstance(row, str):
            try:
                row = ast.literal_eval(row)  # 將字串轉換為真正的列表/字典
            except (ValueError, SyntaxError):
                return row  # 如果解析失敗，保持原樣

        # 現在 row 應該是列表，進行更新處理
        if isinstance(row, list):
            for item in row:
                if isinstance(item, dict) and item.get('Actionability') == 'NA':
                    level = item.get('oncoKBEvidenceLevel')
                    if level in ['1', '2A', 'R1']:
                        item['Actionability'] = 'Tier 1A'
                    elif level in ['2B', '3B']:
                        item['Actionability'] = 'Tier 2C'
                    elif level == '3A':
                        item['Actionability'] = 'Tier 1B'
                    elif level in ['4', 'R2']:
                        item['Actionability'] = 'Tier 2D'
        return row

    #def convert_marker(row):
        #return f"{row['Chr']}_{row['Start']}-{row['End']}_{row['Ref']}>{row['Alt']}"
    def convert_marker(row):
        # 確保 Start 和 End 被處理為整數
        try:
            start = int(float(row['Start']))  # 將任何浮點數或整數轉為純整數
            end = int(float(row['End']))
        except (ValueError, TypeError):
            # 如果無法轉換，保留原始值
            start = row['Start']
            end = row['End']
        
        return f"{row['Chr']}_{start}-{end}_{row['Ref']}>{row['Alt']}"

    def retrieveMarker(item, search_tumor_type):
        if not isinstance(search_tumor_type, str):
            raise ValueError("search_tumor_type 必須是字串")
        
        biomarker = item['Biomarker'][0] if isinstance(item['Biomarker'], list) else item['Biomarker']
        drug = item['Drug'][0] if isinstance(item['Drug'], list) else item['Drug']
        level = item.get('Evidence_level', 'NA')

        # 優先顯示符合搜尋條件的 Tumor_type，然後顯示其餘的
        tumor_types = item['Tumor_type'] if isinstance(item['Tumor_type'], list) else [item['Tumor_type']]
        tumor_types = [tt.replace('_', ' ') for tt in tumor_types]  # 格式化
        # 將符合條件的排在前面
        sorted_tumor_types = sorted(tumor_types, key=lambda tt: search_tumor_type in tt, reverse=True)
        tumor_types_str = ', '.join(sorted_tumor_types)

        return biomarker, drug, level, tumor_types_str

    def search_variant_tumor_type(variant_dict, variant, type, tumor_type):
        """
        搜尋指定的變異和單一腫瘤類型。
        
        :param variant_dict: OncoKB 字典
        :param variant: 要搜尋的變異
        :param type: 變異類型（'Mutation', 'Truncated', 'deletion'）
        :param tumor_type: 要搜尋的單一腫瘤類型（字串）
        :return: 搜尋結果的列表或 None
        """
        output = []
        if type == 'Mutation':
            if variant in variant_dict['Mutation']:
                for entry in variant_dict['Mutation'][variant]:  # Fit the specific variant on drugs
                    tumor_types = entry.get('Tumor_type', [])
                    # 檢查是否有任意一個tumor_type符合搜尋條件
                    if any(tumor_type in tt.replace('_', ' ') for tt in tumor_types):
                        entry = [entry] if isinstance(entry, dict) else entry
                        for vd in entry:
                            biomarker, drug, level, tumortype = retrieveMarker(vd, tumor_type)  # 傳入單一 tumor_type
                            tier = oncoEvidence.get(level, 'NA')
                            output.append({
                                'Biomarker': biomarker,
                                'Drug': drug,
                                'Actionability': tier,
                                'Phenotype': tumortype,
                                'oncoKBEvidenceLevel': level
                            })
                        return output  # No search for the following drugs
                    else:  # No match to the phenotype in oncoKB
                        entry = [entry] if isinstance(entry, dict) else entry
                        for vd in entry:
                            biomarker, drug, level, tumortype = retrieveMarker(vd, tumor_type)  # 傳入單一 tumor_type
                            if level in ['1', '2', '3A']:
                                tier = 'Tier 2C'
                            else:
                                tier = oncoEvidence.get(level, 'NA')
                            output.append({
                                'Biomarker': biomarker,
                                'Drug': drug,
                                'Actionability': tier,
                                'Phenotype': tumortype,
                                'oncoKBEvidenceLevel': level
                            })
                        return output
        elif type in ['Truncated', 'deletion']:
            if variant in variant_dict['Biomarker']:
                for entry in variant_dict['Biomarker'][variant]:
                    tumor_types = entry.get('Tumor_type', [])
                    if any(tumor_type in tt.replace('_', ' ') for tt in tumor_types):
                        entry = [entry] if isinstance(entry, dict) else entry
                        for vd in entry:
                            biomarker, drug, level, tumortype = retrieveMarker(vd, tumor_type)  # 傳入單一 tumor_type
                            tier = oncoEvidence.get(level, 'NA')
                            output.append({
                                'Biomarker': biomarker,
                                'Drug': drug,
                                'Actionability': tier,
                                'Phenotype': tumortype,
                                'oncoKBEvidenceLevel': level
                            })
                        return output  # No search for the following drugs
                    else:  # No match to the phenotype in oncoKB
                        entry = [entry] if isinstance(entry, dict) else entry
                        for vd in entry:
                            biomarker, drug, level, tumortype = retrieveMarker(vd, tumor_type)  # 傳入單一 tumor_type
                            if level in ['1', '2', '3A']:
                                tier = 'Tier 2C'
                            else:
                                tier = oncoEvidence.get(level, 'NA')
                            output.append({
                                'Biomarker': biomarker,
                                'Drug': drug,
                                'Actionability': tier,
                                'Phenotype': tumortype,
                                'oncoKBEvidenceLevel': level
                            })
                        return output
        else:
            return None
        return output if output else None

    # 定義 OncoKB 的證據等級對應
    oncoEvidence = {
        '1': 'Tier 1A',
        '2A': 'Tier 1A',
        '3A': 'Tier 1B',
        '2B': 'Tier 2C',
        '3B': 'Tier 2C',
        '4': 'Tier 2D',
        'R1': 'Tier 1A',
        'R2': 'Tier 2D'
    }
    
    # 讀取帶位置資訊的資料
    df = pd.read_csv(oncokb_final_database_path, sep=',', header=0)
    df['Variant'] = df.apply(convert_marker, axis=1)
    df['oncoKB'] = df['oncoKB_annotation'].apply(parse_biomarker_info)

    # 讀取不帶位置資訊的資料
    df1 = pd.read_csv(oncokb_without_position_path, sep='\t', header=0)
    df1['oncoKB'] = df1['oncoKB_annotation'].apply(parse_biomarker_info)

    # 建立 OncoKB 字典
    oncoKB = {}
    variant_oncokb_dict = df.set_index('Variant')['oncoKB'].to_dict()
    oncoKB['Mutation'] = variant_oncokb_dict
    variant_oncokb_dict2 = df1.set_index('tag')['oncoKB'].to_dict()
    oncoKB['Biomarker'] = variant_oncokb_dict2

    # 讀取 input_df
    input_df = pd.read_csv(store_file, encoding='ISO-8859-1') 
    input_df['Variant'] = input_df.apply(convert_marker, axis=1)

    # 定義要搜尋的腫瘤類型列表
    tumor_type_search_list = ['lymphoma']#這裡要改成搜尋phenotype


    if 'Match' not in input_df.columns:
        input_df['Match'] = ''
    # 初始化搜尋結果的欄位
    for tumor in tumor_type_search_list:
        column_name = f'OncoKB_Result_{tumor.replace(" ", "_")}'
        input_df[column_name] = None

    # 執行搜尋並儲存結果
    for tumor in tumor_type_search_list:
        results = []
        for index, row in input_df.iterrows():
            variant = row['Variant']
            print(f"oncoKB_variant:{variant}")
            result = search_variant_tumor_type(oncoKB, variant, 'Mutation', tumor)
            print(result)
            if result:
                results.append(result)
                if pd.notna(input_df.at[index, 'Match']) and input_df.at[index, 'Match'] != '':
                    input_df.at[index, 'Match'] += f'; OncoKB ({tumor}) Match'
                else:
                    input_df.at[index, 'Match'] = f'OncoKB ({tumor}) Match'
            else:
                results.append("No match Drug")
        # 將結果新增到 DataFrame
        column_name = f'OncoKB_Result_{tumor.replace(" ", "_")}'
        input_df[column_name] = results
        # 更新 Actionability
        input_df[column_name] = input_df[column_name].apply(update_actionability)


    columns_to_display = ['Variant', 'Match'] + [f'OncoKB_Result_{tumor.replace(" ", "_")}' for tumor in tumor_type_search_list]
    print(input_df[columns_to_display])


    input_df.to_csv(store_file, index=False)

    # 測試搜尋
    search_variant = 'chr7_140453136-140453136_A>T'
    search_tumor_type = 'lymphoma'
    result = search_variant_tumor_type(oncoKB, search_variant, 'Mutation', search_tumor_type)
    print(result)
    if result:
        print("Find Match Drug:")
        print(pd.DataFrame(result))
    else:
        print("No match Drug")


    # -------------------------------------------------------------------------------------------CGIdatabase--------------------------------------------------------------------------
    import json
    import pandas as pd
    import re    

    # Make the dictionary of cancer acronyms term
    disdf = pd.read_csv(cgi_cancer_acronyms_path, sep = '\t', header = 0)
    disease = dict()
    for acronym, des in zip(disdf['cancer_acronym'], disdf['description']):
        if acronym not in disease:
            disease[acronym] = des

    with open(cgi_processed_biomarkers_path, 'rt') as f:
        CGI = json.load(f)

    amino_acids = {
        'A': 'Ala', 'C': 'Cys', 'D': 'Asp', 'E': 'Glu', 'F': 'Phe',
        'G': 'Gly', 'H': 'His', 'I': 'Ile', 'K': 'Lys', 'L': 'Leu',
        'M': 'Met', 'N': 'Asn', 'P': 'Pro', 'Q': 'Gln', 'R': 'Arg',
        'S': 'Ser', 'T': 'Thr', 'V': 'Val', 'W': 'Trp', 'Y': 'Tyr'
    }

    def is_hgvs_protein_variant(testvariant):
        hgvs_pattern = re.compile(r'^([A-Z0-9]+)\.p\.([A-Z])(\d+)([A-Z\*]?)$')
        match = hgvs_pattern.match(testvariant)
        if match:
            gene, ref_aa, pos, alt_aa = match.groups()
            if ref_aa in amino_acids and (alt_aa in amino_acids or alt_aa == '' or alt_aa == '*'):
                return True
        return False

    # Fusion pattern
    fusion_pattern = re.compile(r'^(\w+)-(\w+)')

    import re





    def searchCGI(query, variantType, gene, phenotype):
        record = []

        # 處理 phenotype 縮寫轉換（如果 des 有提供對應）
        if isinstance(phenotype, str) and phenotype.isupper() and phenotype in des:
            phenotype = des[phenotype]

        if variantType in ['SNV', 'Mutation']:
            query_amino_acid = query.split('.')[-1]  # 取 R132C
            query_residue = None

            match = re.match(r"[A-Z](\d+)[A-Z]", query_amino_acid)
            if match:
                query_residue = match.group(1)  # 抓 132

            if not query_residue:
                return [{'code': 400, 'Msg': 'Invalid variant format'}]

            for key, entries in CGI.items():
                for entry in entries:
                    alt = entry.get("Alteration", "")
                    entry_gene = entry.get("Gene", "")

                    # 跳過不是該基因的紀錄
                    if entry_gene != gene:
                        continue

                    # 檢查是否為精準比對
                    if not (alt == f"{gene}:{query_amino_acid}" or alt == f"{gene}:R{query_residue}"):
                        continue

                    # 資料擷取
                    drug = entry.get("Drug", "")
                    drugfullname = entry.get("Drug full name", "")
                    approval = entry.get("Drug status", "")
                    evidence = entry.get("Evidence level", "")
                    source = entry.get("Source", "")
                    pheno = entry.get("Primary Tumor type full name", "")

                    # 分級邏輯
                    if phenotype and phenotype.lower() == pheno.lower():

                        tier = 'Tier 1A' if approval == 'Approved' else 'Tier 1B'
                    else:
                        tier = 'Tier 2C' if approval == 'Approved' else 'Tier 2D'

                    record.append({
                        'code': 200,
                        'Msg': {
                            "Gene": entry_gene,
                            "Drug": drug,
                            "DrugName": drugfullname,
                            "Approval": approval,
                            "Evidence": evidence,
                            "Source": source,
                            "Phenotype": pheno,
                            "Tier": tier
                        }
                    })

        elif variantType == 'Fusion':
            fusion_query = query + ' Fusion'
            for key, entries in CGI.items():
                if fusion_query in key:
                    for entry in entries:
                        entry_gene = entry.get("Gene", "")
                        drug = entry.get("Drug", "")
                        drugfullname = entry.get("Drug full name", "")
                        approval = entry.get("Drug status", "")
                        evidence = entry.get("Evidence level", "")
                        source = entry.get("Source", "")
                        pheno = entry.get("Primary Tumor type full name", "")

                        if phenotype and phenotype.lower() == pheno.lower():

                            tier = 'Tier 1A' if approval == 'Approved' else 'Tier 1B'
                        else:
                            tier = 'Tier 2C' if approval == 'Approved' else 'Tier 2D'

                        record.append({
                            'code': 200,
                            'Msg': {
                                "Gene": entry_gene,
                                "Drug": drug,
                                "DrugName": drugfullname,
                                "Approval": approval,
                                "Evidence": evidence,
                                "Source": source,
                                "Phenotype": pheno,
                                "Tier": tier
                            }
                        })

        elif variantType == 'CNV':
            # 例如：EGFR amplification
            parts = query.split(' ')
            if len(parts) != 2:
                return [{'code': 400, 'Msg': 'Invalid CNV query format'}]

            gene = parts[0]
            cnv_type = parts[1].lower()
            if cnv_type in ['amplification', 'gain']:
                cnv_type = 'amplication'
            elif cnv_type in ['deletion', 'loss']:
                cnv_type = 'deletion'
            else:
                return [{'code': 400, 'Msg': 'Unknown CNV type'}]

            for key, entries in CGI.items():
                if f"{gene} {cnv_type}" in key:
                    for entry in entries:
                        entry_gene = entry.get("Gene", "")
                        drug = entry.get("Drug", "")
                        drugfullname = entry.get("Drug full name", "")
                        approval = entry.get("Drug status", "")
                        evidence = entry.get("Evidence level", "")
                        source = entry.get("Source", "")
                        pheno = entry.get("Primary Tumor type full name", "")

                        if phenotype and phenotype.lower() == pheno.lower():

                            tier = 'Tier 1A' if approval == 'Approved' else 'Tier 1B'
                        else:
                            tier = 'Tier 2C' if approval == 'Approved' else 'Tier 2D'

                        record.append({
                            'code': 200,
                            'Msg': {
                                "Gene": entry_gene,
                                "Drug": drug,
                                "DrugName": drugfullname,
                                "Approval": approval,
                                "Evidence": evidence,
                                "Source": source,
                                "Phenotype": pheno,
                                "Tier": tier
                            }
                        })

        if not record:
            record.append({'code': 404, 'Msg': 'No match in CGI'})

        return record

       
    # 處理 CSV 文件並進行搜尋
    def build_record(item, tier):
        gene = item['Gene']
        drug = item['Drug']
        drugfullname = item['Drug full name']
        approval = item['Drug status']
        evidence = item['Evidence level']
        source = item['Source']
        pheno = item['Primary Tumor type full name']
        return {
            'code': 200,
            'Msg': {
                'Gene': gene,
                'Drug': drug,
                'DrugName': drugfullname,
                'Approval': approval,
                'Evidence': evidence,
                'Source': source,
                'Phenotype': pheno,
                'Tier': tier
            }
        }
    df = pd.read_csv(store_file, encoding='ISO-8859-1') 
    df['Match'] = df.get('Match', "")
    cgi_results = []
    phenotype = "cholangiocarcinoma"  # 使用指定的 phenotype
    for index, row in df.iterrows():
        gene = row.get('Gene.refGene')  # 確保列名正確
        variant = row.get('variant')
        variant_class = row.get('VARIANT_CLASS')
        
        # 構造 query_variant
        query_variant = f"{gene}.p.{variant}"
        print(query_variant)
        # 查詢 CGI
        try:
            print(f"🔍 查詢變異: {query_variant}, 類型: {variant_class}, 基因: {gene}, phenotype: {phenotype}")
            result = searchCGI(query_variant, variant_class, gene, phenotype)
            print("this is CGI")
            print(result)
            if not result:  # 如果沒有結果
                result = [{'code': 404, 'Msg': 'No result'}]
            else:  # 如果有結果，更新 Match 欄位
                df.at[index, 'Match'] = (df.at[index, 'Match'] + ', ' if df.at[index, 'Match'] else '') + 'CGI Match'
        except Exception as e:
            result = [{'code': 500, 'Msg': f"Error: {str(e)}"}]  # 捕捉例外

        # 將結果追加到列表
        cgi_results.append(result)
    # 將結果寫入 CSV 文件
    if len(cgi_results) == len(df):
        df['CGI_Result'] = cgi_results
        df.to_csv(store_file, index=False)
        print("END")
    data=pd.read_csv(store_file)
    filtered_data = data[data['Match'].notnull() & (data['Match'] != '')]
    filtered_data.to_csv(store_file,index=False)
    # filtered_data.to_csv(f"/miRTI/media/patient/{newjobID}/somatic_test.csv",index=False)
    filtered_CIVIC = data[data['Match'].str.contains('CIViC Match', na=False)]
    filtered_Mycancergenome=data[data['Match'].str.contains('MyCancerGenome Match', na=False)]

    print(filtered_CIVIC)
    print(filtered_Mycancergenome)



#----------------
def pipeline(csv_filename, output_csv_filename, newjobID):
    import json
    import re
    import pandas as pd
    from collections import defaultdict

    # 定義資料來源及其對應的鍵和值，新增描述鍵
    data_sources = {
        'CIVIC_result': {
            'key': 'therapies',
            'tier_key': 'Rank',
            'database': 'CIVIC',
            'description_key': 'Detail'  # 新增描述鍵
        },
        'MyCancerGenome_Result': {
            'key': 'Therapy',
            'tier_key': 'Rank',
            'database': 'MyCancerGenome',
            'description_key': 'Detail'  # 新增描述鍵
        },
        'COSMIC_Result': {
            'key': 'Therapies',
            'tier_key': 'ACTIONABILITY_RANK',
            'database': 'COSMIC'
            # 沒有描述鍵
        },
        'OncoKB_Result_lymphoma': {
            'key': 'Drug',
            'tier_key': 'Actionability',
            'database': 'OncoKB'
            # 沒有描述鍵
        },
        'CGI_Result': {
            'key': 'Drug',
            'nested_key': 'Msg',
            'tier_key': 'Tier',
            'database': 'CGI'
            # 沒有描述鍵
        }
    }

    # Tier 等級映射表
    tier_mapping = {
        'A': 'Tier 1A',
        'B': 'Tier 1B',
        'C': 'Tier 2C',
        'D': 'Tier 2D',
        'Tier I - Level A': 'Tier 1A',
        'Tier I - Level B': 'Tier 1B',
        'Tier II - Level C': 'Tier 2C',
        'Tier II - Level D': 'Tier 2D',
        'Tier 1A': 'Tier 1A',
        'Tier 1B': 'Tier 1B',
        'Tier 2C': 'Tier 2C',
        'Tier 2D': 'Tier 2D',
        'Tier 1': 'Tier 1A',
        'Tier 2': 'Tier 1B',
        'Tier 3': 'Tier 2C',
        'Tier 4': 'Tier 2D',
        '3A': 'Tier 3A',
        '3B': 'Tier 3B',
        '3C': 'Tier 3C',
        '3': 'Tier 2C',
        '4': 'Tier 2D',
        'Unknown': 'Unknown',
    }

    def standardize_tier(tier):
        """
        將不同表示方式的 Tier 等級標準化。
        """
        if pd.isna(tier):  # 處理 NaN
            return 'Unknown'
        tier = str(tier).strip()  # 去除左右空白
        return tier_mapping.get(tier, 'Unknown')  # 映射不到就標記為 Unknown

    def process_json_field(field_value, therapies_key='Therapies', nested_key=None, tier_key=None, description_key=None):
        """
        處理 JSON 字段，提取藥物名稱、Tier 等級和描述資訊。
        """
        drug_tier_list = []
        if field_value and field_value != 'nan':
            result_str = re.sub(r"'", '"', str(field_value))
            result_str = re.sub(r'(\s)\.\.\.(\s)', ' ', result_str)
            result_str = result_str.replace('nan', 'null')

            try:
                data = json.loads(result_str)
            except json.JSONDecodeError:
                try:
                    data = eval(result_str)
                except Exception:
                    data = []

            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except Exception:
                    data = [data]

            if isinstance(data, dict):
                if all(isinstance(v, dict) for v in data.values()):
                    data = list(data.values())
                else:
                    data = [data]
            elif not isinstance(data, list):
                data = []

            for item in data:
                if nested_key and isinstance(item, dict):
                    item = item.get(nested_key, {})
                therapies = None
                possible_keys = [therapies_key, 'Therapies', 'therapies', 'Therapy', 'therapy', 'Drug', 'drug']
                for key in possible_keys:
                    if isinstance(item, dict):
                        therapies = item.get(key)
                    if therapies:
                        break

                tier = None
                possible_tier_keys = [tier_key, 'Rank', 'Tier', 'Actionability', 'ACTIONABILITY_RANK']
                for key in possible_tier_keys:
                    if isinstance(item, dict):
                        tier = item.get(key)
                    if tier:
                        break

                description = None
                if description_key and isinstance(item, dict):
                    description = item.get(description_key)
                    # 如果描述是字典或列表，將其轉換為 JSON 字串
                    if isinstance(description, (dict, list)):
                        description = json.dumps(description, ensure_ascii=False)
                    elif description is not None:
                        description = str(description)

                if therapies:
                    if isinstance(therapies, list):
                        therapies_split = therapies
                    else:
                        therapies_split = re.split(r'[+,;/]', therapies)
                    therapies_clean = [t.strip() for t in therapies_split if t.strip()]
                    for drug in therapies_clean:
                        if not isinstance(drug, str):
                            print(f"[⚠️] 非預期的藥物格式：{drug}，已跳過")
                            continue

                        print(f"[🧪] Raw tier before standardization: {tier!r}")
                        tier_str = tier if tier else 'Unknown'
                        tier_standard = standardize_tier(tier_str)
                        print(f"[✅] After standardization: {tier_standard}")
                        drug_tier_list.append({
                            'Drug': drug.strip().upper(),
                            'Tier': tier_standard,
                            'Description': description
                        })
        return drug_tier_list

    def extract_drug_info(df):
        """
        從 DataFrame 中提取藥物資訊，創建一個包含 Tier、Drug、Database、Description 的新 DataFrame，並統計每個組合的出現次數。
        """
        records = []

        for index, row in df.iterrows():
            row = row.fillna('')
            for source, info in data_sources.items():
                field_value = row.get(source, '')
                therapies_key = info['key']
                nested_key = info.get('nested_key', None)
                tier_key = info.get('tier_key', None)
                database = info.get('database', '')
                description_key = info.get('description_key', None)
                drugs_tiers = process_json_field(
                    field_value,
                    therapies_key,
                    nested_key,
                    tier_key,
                    description_key
                )
                invalid_drugs = set(['CLINICALTRIAL', 'NONE', 'UNKNOWN', '', 'N/A', 'NOT AVAILABLE', 'NULL', '[]'])
                for item in drugs_tiers:
                    drug = item['Drug']
                    tier = item['Tier']
                    description = item.get('Description')
                    if drug and drug not in invalid_drugs:
                        records.append({
                            'Tier': tier,
                            'Drug': drug,
                            'Database': database,
                            'Description': description
                        })

        # 創建 DataFrame
        drug_df = pd.DataFrame(records)

        # 將 Description 中的 NaN 轉換為空字串，避免分組時出現問題
        drug_df['Description'] = drug_df['Description'].fillna('')

        # 分組統計
        count_series = drug_df.groupby(['Tier', 'Drug', 'Database', 'Description']).size().reset_index(name='Count')

        return count_series
        # summary_df = (
        #     drug_df
        #     .groupby('Drug')
        #     .agg({
        #         'Tier': lambda x: ', '.join(sorted(set(x))),
        #         'Database': lambda x: ', '.join(sorted(set(x))),
        #         'Description': lambda x: ' || '.join(sorted(set(filter(None, x)))),
        #         'Drug': 'count'
        #     })
        #     .rename(columns={'Drug': 'Count'})
        #     .reset_index()
        # )

        # return summary_df


    df = pd.read_csv(csv_filename, encoding='utf-8')

    drug_info_df = extract_drug_info(df)

    drug_info_df.to_csv(output_csv_filename, index=False, encoding='utf-8')

    # 將結果添加到原始 DataFrame 中作為一個列
    def add_result_column(df, drug_info_df):
        """
        將提取的藥物資訊添加到原始 DataFrame 中，作為 'result' 列。
        """
        # 將 Description 中的 NaN 轉換為空字串，避免鍵錯誤
        drug_info_df['Description'] = drug_info_df['Description'].fillna('')

        # 創建一個字典，方便快速查找 Count 值
        drug_info_dict = {}
        for idx, row in drug_info_df.iterrows():
            key = (row['Tier'], row['Drug'], row['Database'], row['Description'])
            drug_info_dict[key] = row['Count']

        def process_row(row):
            row_records = []
            for source, info in data_sources.items():
                field_value = row.get(source, '')
                therapies_key = info['key']
                nested_key = info.get('nested_key', None)
                tier_key = info.get('tier_key', None)
                database = info.get('database', '')
                description_key = info.get('description_key', None)
                drugs_tiers = process_json_field(
                    field_value,
                    therapies_key,
                    nested_key,
                    tier_key,
                    description_key
                )
                invalid_drugs = set(['CLINICALTRIAL', 'NONE', 'UNKNOWN', '', 'N/A', 'NOT AVAILABLE', 'NULL', '[]'])
                for item in drugs_tiers:
                    drug = item['Drug']
                    tier = item['Tier']
                    description = item.get('Description')
                    if description is None:
                        description = ''
                    if drug and drug not in invalid_drugs:
                        key = (tier, drug, database, description)
                        count = drug_info_dict.get(key, 1)  # 默認值為 1
                        # 將每條記錄作為字典添加到列表中
                        row_records.append({
                            'Tier': tier,
                            'Drug': drug,
                            'Database': database,
                            'Description': description,
                            'Count': count
                        })
            return row_records

        df['result'] = df.apply(process_row, axis=1)
        return df

    df = add_result_column(df, drug_info_df)

    df.to_csv(output_csv_filename, index=False, encoding='utf-8')
    # df.to_csv(f"/miRTI/media/patient/{newjobID}/somatic_test_pipeline.csv", index=False, encoding='utf-8')

    # 輸出結果 DataFrame
    print(df[['result']].head())



#----------------






import psycopg2
import pandas as pd
import io

def final_result_somatic(file_path,newjobID):
        
    data = pd.read_csv(file_path)
    data['Match'] = data['Match'].apply(simplify_match_field)
    print(data)
    # 篩選出 Match 欄位包含 "CIViC Match" 的行
    filtered_data = data[data['result'].apply(lambda x: x != '[]')]
    filtered_data.to_csv(f"/miRTI/media/patient/{newjobID}/somatic_result_delete_list_final_result.csv")
    #+=============================load 藥物資訊進postgresql 要統計黑名單用===============================
    # buffer = io.StringIO()
    # filtered_data.to_csv(buffer, index=False, header=False)
    # buffer.seek(0)
    # DB_NAME = "somatic"
    # DB_USER = "uuuwei0504"
    # DB_PASSWORD = "REDACTED_SET_VIA_ENV"
    # DB_HOST = "172.17.0.1"
    # DB_PORT = "5432"
    # # === 建立連線 ===
    # conn = psycopg2.connect(
    #     dbname=DB_NAME,
    #     user=DB_USER,
    #     password=DB_PASSWORD,
    #     host=DB_HOST,
    #     port=DB_PORT
    # )
    # cur = conn.cursor()

    # # === 建立新表格 ===
    # table_name = f"{newjobID}_blacklist"
    # columns = ', '.join([f'"{col}" TEXT' for col in filtered_data.columns])  # 所有欄位設為 TEXT
    # create_table_sql = f'CREATE TABLE IF NOT EXISTS "{table_name}" ({columns});'
    # cur.execute(create_table_sql)
    # conn.commit()

    # # === 匯入資料 ===
    # cur.copy_from(buffer, table_name, sep=',', null='')

    # # === 收尾 ===
    # conn.commit()
    # cur.close()
    # conn.close()
    
    #+=============================load 藥物資訊進postgresql 要統計黑名單用===============================
    # print("filtered_data:")
    # print(filtered_data)
    def extract_disease(row):
        """
        如果 Match 欄位包含 MyCancerGenome，提取 MyCancerGenome_Result 中的 Disease 資訊。
        """
        if 'MyCancerGenome' in row['Match']:
            try:
                # 將 MyCancerGenome_Result 解析為 JSON
                result_list = json.loads(row['MyCancerGenome_Result'])
                # 提取 Disease 資訊
                diseases = [entry.get("Disease", "") for entry in result_list if "Disease" in entry]
                return "; ".join(diseases) if diseases else None
            except (json.JSONDecodeError, TypeError):
                return None
        return None
    filtered_data['description'] = filtered_data.apply(extract_disease, axis=1)
    # print("this is discription")
    # print(filtered_data['description'])


    # data1 = data[data['Match'].str.contains('CIViC', na=False)] #如果想要保留原本的 就把這邊弄回來 把下面那個data1改回來 並且去1871行那邊開始改
    data1 = data[data['Match'].notna() & (data['Match'].str.strip() != '')]

    #data1 = data[data['result'].apply(lambda x: x != '[]')]

    # print("data1")
    # print(data1)
    new_data = []
    for _, row in data1.iterrows():
        new_row = {}
        # 1. Location
        #new_row['Location'] = f"{row['Chr']}:{row['Start']}_{row['End']}{row['Ref']}>{row['Alt']} transcript:{row['Feature']}"
        
        new_row['Location'] = (
                        f"{row.get('Chr', '')}:"
                        f"{int(row.get('Start')) if isinstance(row.get('Start'), (int, float)) else row.get('Start')}_"
                        f"{int(row.get('End')) if isinstance(row.get('End'), (int, float)) else row.get('End')}"
                        f"{row.get('Ref', '')}>{row.get('Alt', '')} "
                        f"transcript:{row.get('Feature', '').split('.')[0] if isinstance(row.get('Feature', str), str) else row.get('Feature')}"
                        )
        # 2. Gene
        new_row['Gene'] = row['Gene.refGene']

        # 3. RS ID
        new_row['RS ID'] = row['avsnp150'] if row['avsnp150'] != '.' else None

        # 4. MAF
        new_row['MAF'] = {
            'gnomAD': row.get('AF', None),
            '1000G': row.get('AF_1000G', None),
            'TW Biobank': row.get('TaiwanBioBank', None)
        }
        # 7. Domain
        new_row['Domain'] = row['Interpro_domain']
        # 8. Pathogenicity
        new_row['Pathogenicity']={
            'CLNSIG': row['CLNSIG']
        }
        new_row['Prediction'] = {
                        'Polyphen2_HVAR': row['Polyphen2_HVAR_pred'],
                        'SIFT': row['SIFT_pred'],
                        'VEST3': row['VEST3_score'],
                        'MutationTaster': row['MutationTaster_pred'],
                        'MetaSVM': row['MetaSVM_pred'],
                        'MetaLR': row['MetaLR_pred'],
                        'CADD': row['CADD_phred'],
                        'DANN': row['DANN_score']
                    }
        new_row['Match'] = row['Match']  # 包含 Match 欄位
        new_row['Amino acid change'] = row['variant']  # 包含 Match 欄位
        new_row['Avalibility'] = row['result']

        
        # 將新行加入列表
        new_data.append(new_row)

    # 將新資料轉為 DataFrame
    new_df = pd.DataFrame(new_data)

    print(new_df)
    print("---------------------------------------------------------------------------------------------------")
    print("---------------------------------------------------------------------------------------------------")
    print("---------------------------------------------------------------------------------------------------")
    print("---------------------------------------------------------------------------------------------------")
    print("---------------------------------------------------------------------------------------------------")
    print("---------------------------------------------------------------------------------------------------")
    new_df.to_csv(f'/miRTI/media/patient/{newjobID}/somatic_result.csv')     
    print(new_df)
    print("---------------------------------------------------------------------------------------------------")
    print("---------------------------------------------------------------------------------------------------")
    print("---------------------------------------------------------------------------------------------------")
    print("---------------------------------------------------------------------------------------------------")
    print("---------------------------------------------------------------------------------------------------")

def simplify_match_field(match_value):
    if pd.isna(match_value):
        return ''  # 如果是 NaN，返回空字串
    # 刪除 " Match" 後綴，只保留前面的名稱
    return match_value.replace(' Match', '')

def parse_result(result_str):
    try:
        return ast.literal_eval(result_str)
    except Exception:
        return []

def merge_result_entries(result_list):
    merged = {}
    for entry in result_list:
        key = (entry['Tier'], entry['Drug'], entry['Database'])
        description = entry.get('Description', '').strip()
        count = entry.get('Count', 1)

        if key not in merged:
            merged[key] = {
                'Tier': key[0],
                'Drug': key[1],
                'Database': key[2],
                'Descriptions': set(),
                'Count': 0
            }

        if description:
            merged[key]['Descriptions'].add(description)
        merged[key]['Count'] += count

    final_list = []
    for val in merged.values():
        combined_desc = ' || '.join(sorted(val['Descriptions']))
        final_list.append({
            'Tier': val['Tier'],
            'Drug': val['Drug'],
            'Database': val['Database'],
            'Description': combined_desc,
            'Count': val['Count']
        })
    return final_list
import time

@csrf_exempt
def somatic_result(request):
    if request.method == 'POST':
        try:
    
            print("work")
            start_time = time.time()
            data = json.loads(request.body.decode('utf-8'))
            newjobID = data.get('newjobid', '')
            #newjobID='FsEVMcOCZJ'
            print(newjobID)
            if not newjobID:
                return JsonResponse({"status": "error", "message": "Missing 'newjobid' in request."})

            # 將 newjobID 儲存在全域變數中
            globals.global_newJobID = newjobID
            print("---------------------------------------------------------------------------------")
            print("---------------------------------------------------------------------------------")
            print("---------------------------------------------------------------------------------")
            print("---------------------------------------------------------------------------------")
            print("---------------------------------------------------------------------------------")
            print("---------------------------------------------------------------------------------")
            print("---------------------------------------------------------------------------------")
            # 執行 pipeline
            store_file = f'/miRTI/media/patient/{newjobID}/drug_with_annotated_file.csv'
            run_pipeline(newjobID)
            print("---------------------------------------------------------------------------------")
            print("---------------------------------------------------------------------------------")
            print("---------------------------------------------------------------------------------")
            print("---------------------------------------------------------------------------------")
            print("---------------------------------------------------------------------------------")
            print("---------------------------------------------------------------------------------")
            print("---------------------------------------------------------------------------------")
# --------------------------------------------------------------------------------------------------
            pipeline(store_file, store_file, newjobID)
            # 讀入檔案
            df = pd.read_csv(store_file)

            # 合併 result 欄位資訊
            df['result'] = df['result'].apply(parse_result).apply(merge_result_entries)

            # 輸出新檔案
            df.to_csv(store_file, index=False, encoding='utf-8')


# --------------------------------------------------------------------------------------------------

            print("final_result_start")
            print("---------------------------------------------------------------------------------")
            print("---------------------------------------------------------------------------------")
            print("---------------------------------------------------------------------------------")
            print("---------------------------------------------------------------------------------")
            print("---------------------------------------------------------------------------------")
            print("---------------------------------------------------------------------------------")
            print("---------------------------------------------------------------------------------")
            final_result_somatic(store_file, newjobID)
            print("final_result end")
            # 準備讀取 somatic_result.csv
            result_file_path = f'/miRTI/media/patient/{newjobID}/somatic_result.csv'
            if not os.path.exists(result_file_path):
                return JsonResponse({"status": "error", "message": f"Result file not found: {result_file_path}"})

            # 將檔案內容讀取為 DataFrame
            df = pd.read_csv(result_file_path)
            df = df.fillna('.')
            # df['Avalibility'] = df['Avalibility'].apply(
            #     lambda x: ast.literal_eval(x) if isinstance(x, str) and x.startswith('[') else x
            # )
            # df = df[df['Avalibility'].apply(lambda x: isinstance(x, list) and len(x) > 0)]
            df = df[df['Avalibility'] != '[]']
            end_time = time.time()  # 記錄結束時間
            execution_time = end_time - start_time  # 計算執行時間
            print(f"程式執行時間: {execution_time:.5f} 秒")
            # 將 DataFrame 轉換為 JSON 格式並返回
            result_data = df.to_dict(orient='records')

            result_data = [
                item for item in result_data
                if 'pathogenic' in str(item.get('Pathogenicity', '')).lower()
            ]


            print("THIS is result_data")
            print(result_data)
            return JsonResponse({"status": "success", "data": result_data})

        except Exception as e:
            # 捕捉任何異常並返回錯誤訊息
            return JsonResponse({"status": "error", "message": str(e)})

    else:
        return JsonResponse({"status": "error", "message": "Invalid request method. Use POST."})
    

def somatic_result_test():


        newjobID = 'wieGKkRWfV'

        if not newjobID:
            return JsonResponse({"status": "error", "message": "Missing 'newjobid' in request."})
        print(newjobID)
           
        globals.global_newJobID = newjobID

           
        store_file = f'/miRTI/media/patient/{newjobID}/drug_with_annotated_file.csv'
        print("run_pipeline")
        run_pipeline(newjobID)
        print("pipeline")
        pipeline(store_file, store_file, newjobID)
        print("final_result_somatic")
        final_result_somatic(store_file, newjobID)


        
        result_file_path = f'/miRTI/media/patient/{newjobID}/somatic_result.csv'
        if not os.path.exists(result_file_path):
            return JsonResponse({"status": "error", "message": f"Result file not found: {result_file_path}"})

            # 將檔案內容讀取為 DataFrame
        df = pd.read_csv(result_file_path)
        print(df)
            # 將 DataFrame 轉換為 JSON 格式並返回
        result_data = df.to_dict(orient='records')
#somatic_result_test()


@csrf_exempt
def read_heredity(request):
    if request.method == 'POST':
        try:
            # 解析請求中的 JSON 數據
            data = json.loads(request.body.decode('utf-8'))
            newjobID = data.get('newjobid', '')

            # 檢查 newjobID 是否為空
            if not newjobID:
                return JsonResponse({"status": "error", "message": "Missing 'newjobid' in request."})

            # 定義檔案路徑
            file_path = f"/miRTI/media/patient/{newjobID}/heredity.csv"

            # 檢查檔案是否存在
            if not os.path.exists(file_path):
                return JsonResponse({"status": "error", "message": f"File not found: {file_path}"})

            # 讀取 CSV 檔案為 DataFrame
            heredity_df = pd.read_csv(file_path)

            # 重組數據
            new_data = []
            for _, row in heredity_df.iterrows():
                new_row = {}
                # 1. Location
                new_row['Location'] = f"{row.get('Chr', '')}:{row.get('Start', '')}_{row.get('End', '')}{row.get('Ref', '')}>{row.get('Alt', '')} transcript:{row.get('Feature', '')}"

                # 2. Gene
                new_row['Gene'] = row.get('Gene.refGene', '')

                # 3. RS ID
                new_row['RS ID'] = row['avsnp150'] if row.get('avsnp150', '.') != '.' else None

                # 4. MAF
                new_row['MAF'] = {
                    'gnomAD': row.get('AF', None),
                    '1000G': row.get('AF_1000G', None),
                    'TW Biobank': row.get('TaiwanBioBank', None)
                }

                # 5. Domain
                new_row['Domain'] = row.get('Interpro_domain', '')

                # 6. Pathogenicity
                new_row['Pathogenicity'] = {
                    'CLNSIG': row.get('CLNSIG', '')
                }

                # 7. Prediction
                new_row['Prediction'] = {
                    'Polyphen2_HVAR': row.get('Polyphen2_HVAR_pred', ''),
                    'SIFT': row.get('SIFT_pred', ''),
                    'VEST3': row.get('VEST3_score', ''),
                    'MutationTaster': row.get('MutationTaster_pred', ''),
                    'MetaSVM': row.get('MetaSVM_pred', ''),
                    'MetaLR': row.get('MetaLR_pred', ''),
                    'CADD': row.get('CADD_phred', ''),
                    'DANN': row.get('DANN_score', '')
                }

                # 8. Amino acid change
                new_row['Amino acid change'] = row.get('variant', '')

                # 將新行加入列表
                new_data.append(new_row)

            # 將新資料轉為 JSON 格式並返回
            return JsonResponse({"status": "success", "data": new_data})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)})
    else:
        return JsonResponse({"status": "error", "message": "只接受 POST 請求"})


@csrf_exempt
def read_cosmic(request):
    if request.method == 'POST':
        try:
            # 解析請求中的 JSON 數據
            data = json.loads(request.body.decode('utf-8'))
            newjobID = data.get('newjobid', '')

            # 檢查 newjobID 是否為空
            if not newjobID:
                return JsonResponse({"status": "error", "message": "Missing 'newjobid' in request."})

            # 定義檔案路徑
            file_path = f"/miRTI/media/patient/{newjobID}/COSMIC.csv"

            # 檢查檔案是否存在
            if not os.path.exists(file_path):
                return JsonResponse({"status": "error", "message": f"File not found: {file_path}"})

            # 讀取 CSV 檔案為 DataFrame
            cosmic_df = pd.read_csv(file_path)

            # 重組數據
            new_data = []
            for _, row in cosmic_df.iterrows():
                new_row = {}
                # 1. Location
                new_row['Location'] = f"{row.get('Chr', '')}:{row.get('Start', '')}_{row.get('End', '')}{row.get('Ref', '')}>{row.get('Alt', '')} transcript:{row.get('Feature', '')}"

                # 2. Gene
                new_row['Gene'] = row.get('Gene.refGene', '')

                # 3. RS ID
                new_row['RS ID'] = row['avsnp150'] if row.get('avsnp150', '.') != '.' else None

                # 4. MAF
                new_row['MAF'] = {
                    'gnomAD': row.get('AF', None),
                    '1000G': row.get('AF_1000G', None),
                    'TW Biobank': row.get('TaiwanBioBank', None)
                }

                # 5. Domain
                new_row['Domain'] = row.get('Interpro_domain', '')

                # 6. Pathogenicity
                new_row['Pathogenicity'] = {
                    'CLNSIG': row.get('CLNSIG', '')
                }

                # 7. Prediction
                new_row['Prediction'] = {
                    'Polyphen2_HVAR': row.get('Polyphen2_HVAR_pred', ''),
                    'SIFT': row.get('SIFT_pred', ''),
                    'VEST3': row.get('VEST3_score', ''),
                    'MutationTaster': row.get('MutationTaster_pred', ''),
                    'MetaSVM': row.get('MetaSVM_pred', ''),
                    'MetaLR': row.get('MetaLR_pred', ''),
                    'CADD': row.get('CADD_phred', ''),
                    'DANN': row.get('DANN_score', '')
                }

                # 8. Amino acid change
                new_row['Amino acid change'] = row.get('variant', '')

                # 將新行加入列表
                new_data.append(new_row)

            # 將重組後的數據轉為 JSON 格式並返回
            return JsonResponse({"status": "success", "data": new_data})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)})
    else:
        return JsonResponse({"status": "error", "message": "只接受 POST 請求"})








@csrf_exempt
def read_suspect(request):
    if request.method == 'POST':
        try:
            # 解析請求中的 JSON 數據
            data = json.loads(request.body.decode('utf-8'))
            newjobID = data.get('newjobid', '')

            # 檢查 newjobID 是否為空
            if not newjobID:
                return JsonResponse({"status": "error", "message": "Missing 'newjobid' in request."})

            # 定義檔案路徑
            file_path = f"/miRTI/media/patient/{newjobID}/suspect.csv"

            # 檢查檔案是否存在
            if not os.path.exists(file_path):
                return JsonResponse({"status": "error", "message": f"File not found: {file_path}"})

            # 讀取 CSV 檔案為 DataFrame
            suspect_df = pd.read_csv(file_path)

            # 重組數據
            new_data = []
            for _, row in suspect_df.iterrows():
                new_row = {}
                # 1. Location
                new_row['Location'] = f"{row.get('Chr', '')}:{row.get('Start', '')}_{row.get('End', '')}{row.get('Ref', '')}>{row.get('Alt', '')} transcript:{row.get('Feature', '')}"

                # 2. Gene
                new_row['Gene'] = row.get('Gene.refGene', '')

                # 3. RS ID
                new_row['RS ID'] = row['avsnp150'] if row.get('avsnp150', '.') != '.' else None

                # 4. MAF
                new_row['MAF'] = {
                    'gnomAD': row.get('AF', None),
                    '1000G': row.get('AF_1000G', None),
                    'TW Biobank': row.get('TaiwanBioBank', None)
                }

                # 5. Domain
                new_row['Domain'] = row.get('Interpro_domain', '')

                # 6. Pathogenicity
                new_row['Pathogenicity'] = {
                    'CLNSIG': row.get('CLNSIG', '')
                }

                # 7. Prediction
                new_row['Prediction'] = {
                    'Polyphen2_HVAR': row.get('Polyphen2_HVAR_pred', ''),
                    'SIFT': row.get('SIFT_pred', ''),
                    'VEST3': row.get('VEST3_score', ''),
                    'MutationTaster': row.get('MutationTaster_pred', ''),
                    'MetaSVM': row.get('MetaSVM_pred', ''),
                    'MetaLR': row.get('MetaLR_pred', ''),
                    'CADD': row.get('CADD_phred', ''),
                    'DANN': row.get('DANN_score', '')
                }

                # 8. Amino acid change
                new_row['Amino acid change'] = row.get('variant', '')

                # 將新行加入列表
                new_data.append(new_row)

            # 返回重組後的數據
            return JsonResponse({"status": "success", "data": new_data})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)})
    else:
        return JsonResponse({"status": "error", "message": "只接受 POST 請求"})



@csrf_exempt
def read_germline_prediction(request):
    if request.method == 'POST':
        try:
            # 解析請求中的 JSON 數據
            data = json.loads(request.body.decode('utf-8'))
            newjobID = data.get('newjobid', '')

            # 檢查 newjobID 是否為空
            if not newjobID:
                return JsonResponse({"status": "error", "message": "Missing 'newjobid' in request."})

            # 定義檔案路徑
            file_path = f"/miRTI/media/patient/{newjobID}/heridty1.csv"

            # 檢查檔案是否存在
            if not os.path.exists(file_path):
                return JsonResponse({"status": "error", "message": f"File not found: {file_path}"})

            # 讀取 CSV 檔案為 DataFrame
            heredity_df = pd.read_csv(file_path)

            # 重組數據
            new_data = []
            for _, row in heredity_df.iterrows():
                new_row = {}
                # 1. Location
                new_row['Location'] = f"{row.get('Chr', '')}:{row.get('Start', '')}_{row.get('End', '')}{row.get('Ref', '')}>{row.get('Alt', '')} transcript:{row.get('Feature', '')}"

                # 2. Gene
                new_row['Gene'] = row.get('Gene.refGene', '')

                # 3. RS ID
                new_row['RS ID'] = row['avsnp150'] if row.get('avsnp150', '.') != '.' else None

                # 4. MAF
                new_row['MAF'] = {
                    'gnomAD': row.get('AF', None),
                    '1000G': row.get('AF_1000G', None),
                    'TW Biobank': row.get('TaiwanBioBank', None)
                }

                # 5. Domain
                new_row['Domain'] = row.get('Interpro_domain', '')

                # 6. Pathogenicity
                new_row['Pathogenicity'] = {
                    'CLNSIG': row.get('CLNSIG', '')
                }

                # 7. Prediction
                new_row['Prediction'] = {
                    'Polyphen2_HVAR': row.get('Polyphen2_HVAR_pred', ''),
                    'SIFT': row.get('SIFT_pred', ''),
                    'VEST3': row.get('VEST3_score', ''),
                    'MutationTaster': row.get('MutationTaster_pred', ''),
                    'MetaSVM': row.get('MetaSVM_pred', ''),
                    'MetaLR': row.get('MetaLR_pred', ''),
                    'CADD': row.get('CADD_phred', ''),
                    'DANN': row.get('DANN_score', '')
                }

                # 8. Amino acid change
                new_row['Amino acid change'] = row.get('variant', '')

                # 將新行加入列表
                new_data.append(new_row)

            # 將新資料轉為 JSON 格式並返回
            return JsonResponse({"status": "success", "data": new_data})

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)})
    else:
        return JsonResponse({"status": "error", "message": "只接受 POST 請求"})
