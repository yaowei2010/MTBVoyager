import pandas as pd
import base64
import os
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import csv
import re
import ast
from django.http import FileResponse, Http404
import psycopg2
import pandas as pd
import os
from .models import existJobs  # 依你的實際路徑調整
import glob

def filter_zero_values(activity_dict, key_to_keep='Samples'):
    """
    篩選掉 activity_dict 中值為 '0' 或 '0.0' 的欄位，同時保留指定的關鍵欄位。
    
    :param activity_dict: 原始資料的字典
    :param key_to_keep: 要保留的關鍵欄位名稱（預設為 'Samples'）
    :return: 篩選後的字典
    """
    filtered_activity = {}
    
    # 保留關鍵欄位
    if key_to_keep in activity_dict:
        filtered_activity[key_to_keep] = activity_dict[key_to_keep]
    
    # 遍歷其他欄位，篩選值不為 '0' 或 '0.0' 的資料
    for key, value in activity_dict.items():
        if key != key_to_keep:
            # 嘗試將值轉換為浮點數進行比較
            try:
                numeric_value = float(value)
                if numeric_value != 0:
                    filtered_activity[key] = value
            except ValueError:
                # 如果轉換失敗，保留原始字串
                if value != '0' and value != '0.0':
                    filtered_activity[key] = value
    
    return filtered_activity


def generate_cosmic_preprocessor(row):
    gene = row['Gene.refGene']  
    variant = row['variant'] if 'variant' in row else None  
    if pd.isna(variant) or variant == "":  
        return f"{gene}_unspecified"
    else:  
        return f"{gene}_{variant}"
        
def parse_combination(combination):
    return set(combination.split(":"))
# --------------------------------------------------------
# 把 COSMIC 的 phenotype 變成一個 set，把藥物組合全部抓出來
# --------------------------------------------------------

# 載入 COSMIC 資料
@csrf_exempt
def process_cosmic(request):
  if request.method == 'POST':
    data = json.loads(request.body.decode('utf-8'))
    newJobID = data.get('newjobid', '')

    print("success")
    cosmic_file_path = '/VEP/20241126Mondodatabase/COSMIC_filtered.tsv'
    cosmic_data = pd.read_csv(cosmic_file_path, sep="\t")
    folder_path = f'/miRTI/media/patient/{newJobID}'
    # csv_file_path = os.path.join(folder_path, 'drug_combinations_result.csv')
    csv_file_path = os.path.join(folder_path, 'drug_combinations_cosmic.csv')
    if os.path.exists(csv_file_path):
        print("exist!")

        with open(csv_file_path, mode='r', encoding='utf-8-sig') as csv_file:
            reader = csv.DictReader(csv_file)
            data = []

            for row in reader:
                new_row = {
                    "Phenotype": row.get("Phenotype", ""),
                    "DRUG_COMBINATION": row.get("DRUG_COMBINATION", ""),
                    "cosmic_preprocessor": row.get("cosmic_preprocessor", ""),
                    "Location": row.get("Location", ""),
                    "Detailed_Location": row.get("Detailed_Location", ""),
                    "Gene": row.get("Gene", ""),
                    "RS ID": row.get("RS ID", ""),
                    "MAF": row.get("MAF", ""),  # ❗保留字串
                    "Domain": row.get("Domain", ""),
                    "Pathogenicity": str(row.get("Pathogenicity", "")).strip(),
                    "Prediction": row.get("Prediction", "")  # ❗保留字串
                }

                data.append(new_row)

            print(data)
            return JsonResponse({"status": "success", "data": data}, safe=False)

    json_file=f"/miRTI/media/patient/{newJobID}/summary.json"
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    diagnosis = data["diagnosis"]
    print("diagnosis:", diagnosis)
    cosmic_data.columns = cosmic_data.columns.str.strip()
    phenotype_search_term = diagnosis
    filtered_data_cosmic = cosmic_data[cosmic_data['combined_disease_name'].str.contains(phenotype_search_term, na=False)]
    mutation_remark_set = set(filtered_data_cosmic['MUTATION_REMARK_split'].dropna())
    
    
    print("篩選出的資料：")
    print(filtered_data_cosmic)
    print("\nMUTATION_REMARK_split set：")
    print(mutation_remark_set)
    
    # -------------------------------------------------
    # 篩出病人的 pathogenic set
    # -------------------------------------------------
    
    
    
    #newJobID='RYAIrEXwdu'
    
    
    folder_path = f"/miRTI/media/patient/{newJobID}"
    vcf_files = [file for file in os.listdir(folder_path) if file.endswith(".vcf")]
    
    if vcf_files:
        print(f"找到 VCF 檔案: {vcf_files}")
    
        # 遍歷每個找到的 .vcf 檔案
        for vcf_file in vcf_files:
            uploadFile_url = os.path.join(folder_path, vcf_file)  # 完整檔案路徑
    
            # 使用 os.path.basename 解析出檔案名稱
            file_name = os.path.basename(uploadFile_url)  # 例如 24C00131_main.vcf
            file_name_without_ext = os.path.splitext(file_name)[0]  # 例如 24C00131_main
            new_file_name = f"{file_name_without_ext}_vep_annovar_merge.csv"
            new_file_name1=f"{file_name_without_ext}_vep_annovar_merge1.csv"
            # 打印相關訊息
            print(f'file_name : {file_name}')
            print(f'file_name_withouttxt: {file_name_without_ext}')
            print(f'uploadFile_target: {new_file_name}')
            print('---------------------VEP start-------------')
    else:
        print("該資料夾中沒有 .vcf 檔案")
    
    
    
    
    
    input_file = f"/miRTI/media/patient/{newJobID}/{new_file_name}"
    output_file = f"/miRTI/media/patient/{newJobID}/{new_file_name1}"
    
    # 檢查輸出檔案是否存在
    if os.path.exists(output_file):
        print(f"輸出檔案已存在，跳過處理：{output_file}")
    else:
        # 載入資料，加入 low_memory=False 解決 DtypeWarning 問題
        df = pd.read_csv(input_file, encoding='ISO-8859-1', low_memory=False)
    
        three_to_one = {
            "Ala": "A", "Cys": "C", "Asp": "D", "Glu": "E", "Phe": "F", "Gly": "G",
            "His": "H", "Ile": "I", "Lys": "K", "Leu": "L", "Met": "M", "Asn": "N",
            "Pro": "P", "Gln": "Q", "Arg": "R", "Ser": "S", "Thr": "T", "Val": "V",
            "Trp": "W", "Tyr": "Y", "Ter": "*"
        }
    
        # 使用正則表達式提取 ensembl_HGVSp 資訊
        df[['variant_start', 'variant_end']] = df['enasmbl_HGVSp'].str.extract(r'p\.([A-Za-z]{3}\d+)([A-Za-z]{3})?')
    
        # 定義轉換函數
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
    
        # 應用轉換函數
        df['variant'] = df.apply(convert_to_single_letter, axis=1)
    
        # 移除中間欄位
        df.drop(columns=['variant_start', 'variant_end'], inplace=True)
    
        # 打印部分結果以檢查
        print(df[['enasmbl_HGVSp', 'variant']])
    
        # 保存處理後的檔案
        df.to_csv(output_file, index=False)
        print(f"處理完成，已保存至 {output_file}")
    
    
    
    
    
    
    
    
    annotation_file_path = f'/miRTI/media/patient/{newJobID}/{new_file_name1}'
    annotation_data = pd.read_csv(annotation_file_path, encoding='ISO-8859-1')
    
    
    filtered_data = annotation_data[annotation_data['CLNSIG'].str.contains("Pathogenic", case=False, na=False)]
    filtered_data['cosmic_preprocessor'] = filtered_data.apply(generate_cosmic_preprocessor, axis=1)    
    filtered_data['Location'] = (
    filtered_data['Chr'].astype(str) + ":" +
    filtered_data['Start'].astype(str) + "_" +
    filtered_data['End'].astype(str) +
    filtered_data['Ref'] + ">" + filtered_data['Alt']
)
    filtered_data['Detailed_Location'] = filtered_data.apply(lambda row: (
    f"{row.get('Chr', '')}:"
    f"{int(row.get('Start')) if isinstance(row.get('Start'), (int, float)) else row.get('Start')}_"
    f"{int(row.get('End')) if isinstance(row.get('End'), (int, float)) else row.get('End')}"
    f"{row.get('Ref', '')}>{row.get('Alt', '')} "
    f"transcript:{row.get('Feature', '').split('.')[0] if isinstance(row.get('Feature', str), str) else row.get('Feature')}"
), axis=1)
    print("篩選出的資料：")
    print(filtered_data)
    print("\nCLNSIG Pathogenic set：")
    print(set(filtered_data['CLNSIG'].dropna()))
    print("----------------------------------------------------------")
    
    
    print(filtered_data[['Gene.refGene', 'variant', 'cosmic_preprocessor']])
    
    # -------------------------------------------------
    # 開始比對 phenotype 跟 pathogenic set 去找藥物
    # -------------------------------------------------
    
    
    
    matched_items = set()  
    unmatched_items = set()  
    drug_combinations = []  
    
    # 初始化集合來記錄成功與無法拼湊的項目
    successfully_matched = set()
    unsuccessfully_matched = set()

    for phenotype in mutation_remark_set:
        components = parse_combination(phenotype)
        
        if components.issubset(set(filtered_data['cosmic_preprocessor'])):
            matched_items.add(phenotype)
            successfully_matched.add(phenotype)
            
            cosmic_row = cosmic_data[cosmic_data['MUTATION_REMARK_split'] == phenotype]
            
            if not cosmic_row.empty:
                matching_rows = filtered_data[filtered_data['cosmic_preprocessor'].isin(components)]
                drug_combinations.append({
                    "Phenotype": phenotype_search_term,
                    "DRUG_COMBINATION": cosmic_row['DRUG_COMBINATION'].values[0],
                    "cosmic_preprocessor": ", ".join(components),
                    "Location": "; ".join(matching_rows['Location']),
                    "Detailed_Location": "; ".join(matching_rows['Detailed_Location']),
                    "Gene": "; ".join(matching_rows['Gene.refGene']),
                    "RS ID": "; ".join(matching_rows['avsnp150'].fillna('N/A')),
                    "MAF": "; ".join(matching_rows.apply(lambda row: str({
                        'gnomAD': row.get('AF', None),
                        '1000G': row.get('AF_1000G', None),
                        'TW Biobank': row.get('TaiwanBioBank', None)
                    }), axis=1)),
                    "Domain": "; ".join(matching_rows['Interpro_domain'].fillna('N/A')),
                    "Pathogenicity": "; ".join(matching_rows['CLNSIG']),
                    "Prediction": "; ".join(matching_rows.apply(lambda row: str({
                        'Polyphen2_HVAR': row.get('Polyphen2_HVAR_pred', None),
                        'SIFT': row.get('SIFT_pred', None),
                        'VEST3': row.get('VEST3_score', None),
                        'MutationTaster': row.get('MutationTaster_pred', None),
                        'MetaSVM': row.get('MetaSVM_pred', None),
                        'MetaLR': row.get('MetaLR_pred', None),
                        'CADD': row.get('CADD_phred', None),
                        'DANN': row.get('DANN_score', None)
                    }), axis=1))
                })
        else:
            unmatched_items.add(phenotype)
            unsuccessfully_matched.add(phenotype)

    # 最後統一輸出成功與無法拼湊的項目
    print(f"成功拼湊的項目 ({len(successfully_matched)}): {successfully_matched}")
    print(f"無法拼湊的項目 ({len(unsuccessfully_matched)}): {unsuccessfully_matched}")
    output_file = f"/miRTI/media/patient/{newJobID}/drug_combinations_cosmic.csv"
    if drug_combinations:

            drug_combination_df = pd.DataFrame(drug_combinations)
            output_file = f"/miRTI/media/patient/{newJobID}/drug_combinations_cosmic.csv"
            drug_combination_df.to_csv(output_file, index=False, encoding='utf-8-sig')
            print(f"\n成功將對應的 DRUG_COMBINATION 儲存至：{output_file}")
            print(drug_combination_df)
            saved_data = pd.read_csv(output_file)
            result_json = saved_data.to_dict(orient='records')
            return JsonResponse({"status": "success", "data": result_json}, safe=False)
    else:
            # 生成一個空的 CSV 檔案，包含欄位名稱（防呆用）
            empty_columns = [
                "Phenotype", "DRUG_COMBINATION", "cosmic_preprocessor", "Location", "Detailed_Location",
                "Gene", "RS ID", "MAF", "Domain", "Pathogenicity", "Prediction"
            ]
            pd.DataFrame(columns=empty_columns).to_csv(output_file, index=False, encoding='utf-8-sig')
            
            print(f"未找到對應項目，已建立空的檔案：{output_file}")
            return JsonResponse({"status": "success", "message": "No drug combinations available."}, status=404)
#    if drug_combinations:
 #       for result in drug_combinations:
  #          print(f"Phenotype: {result['Phenotype']}, DRUG_COMBINATION: {result['DRUG_COMBINATION']}")
    
    
        #drug_combination_df = pd.DataFrame(drug_combinations)
        #output_file = r"C:\Users\user\Desktop\林醫師VCF團隊\2024-08-29資料\20241209task\drug_combinations_results.csv"
        #drug_combination_df.to_csv(output_file, index=False, encoding='utf-8-sig')  # 使用 UTF-8-SIG 避免中文亂碼
        
        #print(f"\n成功將對應的 DRUG_COMBINATION 儲存至：{output_file}")
        #print(drug_combination_df)
   # else:
    #    print("沒有成功匹配的 DRUG_COMBINATION。")

















#-------------------------------------------MutiSNP_analysis_CIVIC---------------------------------------------------------
def check_phenotype_in_pathogenic(phenotype_set, pathogenic_set):
    results = {}
    standardized_pathogenic_set = {item.strip().upper() for item in pathogenic_set}

    for phenotype in phenotype_set:
        pheno = phenotype.strip().upper()

        if ' OR ' in pheno:
            components = [x.strip() for x in pheno.split(' OR ')]
            match = any(comp in standardized_pathogenic_set for comp in components)
        elif ' AND ' in pheno:
            components = [x.strip() for x in pheno.split(' AND ')]
            match = all(comp in standardized_pathogenic_set for comp in components)
        elif '*' in pheno:  # 新增這段
            components = [x.strip() for x in pheno.split('*')]
            match = all(comp in standardized_pathogenic_set for comp in components)
        else:
            match = pheno in standardized_pathogenic_set

        results[phenotype] = match

    return results

def query_disease_and_extract_civic_new(data, disease_name):
    """
    Query rows with a specific disease name and extract unique values from the 'civic_new' column.

    Args:
        data (pd.DataFrame): The input DataFrame.
        disease_name (str): The disease name to query.

    Returns:
        set: A set of unique values from the 'civic_new' column.
    """
    # Filter rows where the disease column contains the specified disease name
    filtered_data = data[data['combined_disease_name'].str.contains(disease_name, case=False, na=False)]

    # Extract the 'civic_new' column and convert it to a set of unique values
    civic_new_set = set(filtered_data['civic_new'].dropna().unique())

    return civic_new_set

def find_therapies_for_phenotypes(data, phenotypes, disease_name):
    """
    Find therapy information for given phenotypes and a specific disease in the CIViC dataset.

    Args:
        data (pd.DataFrame): The CIViC dataset.
        phenotypes (list or set): A list/set of phenotypes (civic_new variants) to search for.
        disease_name (str): The disease name to query.

    Returns:
        dict: A dictionary mapping phenotypes to their therapy information.
    """
    therapies = {}
    for phenotype in phenotypes:
        matching_rows = data[
            (data['civic_new'].str.strip().str.upper() == phenotype.strip().upper()) &
            (data['combined_disease_name'].str.contains(disease_name, case=False, na=False))
        ]
        
        if not matching_rows.empty:
            # therapies[phenotype] = matching_rows['therapies'].iloc[0]
            therapies[phenotype] = "\n\n".join(matching_rows['therapies'].dropna().unique())
        else:
            therapies[phenotype] = "No therapy information found"
    return therapies



def extract_drug_combinations(filtered_data, phenotype, components, disease_name, therapies):
    """
    Extract detailed drug combination information for a specific phenotype and disease.

    Args:
        filtered_data (pd.DataFrame): Filtered data containing patient-related information.
        phenotype (str): The current phenotype being processed.
        components (list): Components of the phenotype.
        disease_name (str): The disease name.
        therapies (dict): A dictionary of therapies for the given phenotypes and disease.

    Returns:
        dict: A dictionary containing detailed drug combination information.
    """

    matching_rows = filtered_data[
        (filtered_data['civic_search'].str.strip().str.upper() == phenotype.strip().upper())
    ]

    return {
        "Phenotype": disease_name,
        "DRUG_COMBINATION": matching_rows['DRUG_COMBINATION'].values[0] if 'DRUG_COMBINATION' in matching_rows.columns and not matching_rows.empty else "N/A",
        "Therapies": therapies.get(phenotype, "No therapy information found"),
        "civic_variant_name": ", ".join(components),
        "Location": "; ".join(matching_rows['Location']),
        "Detailed_Location": "; ".join(matching_rows['Detailed_Location']),
        "Gene": "; ".join(matching_rows['Gene.refGene']),
        "RS ID": "; ".join(matching_rows['avsnp150'].fillna('N/A')),
        "MAF": "; ".join(matching_rows.apply(lambda row: str({
            'gnomAD': row.get('AF', None),
            '1000G': row.get('AF_1000G', None),
            'TW Biobank': row.get('TaiwanBioBank', None)
        }), axis=1)),
        "Domain": "; ".join(matching_rows['Interpro_domain'].fillna('N/A')),
        "Pathogenicity": "; ".join(matching_rows['CLNSIG']),
        "Prediction": "; ".join(matching_rows.apply(lambda row: str({
            'Polyphen2_HVAR': row.get('Polyphen2_HVAR_pred', None),
            'SIFT': row.get('SIFT_pred', None),
            'VEST3': row.get('VEST3_score', None),
            'MutationTaster': row.get('MutationTaster_pred', None),
            'MetaSVM': row.get('MetaSVM_pred', None),
            'MetaLR': row.get('MetaLR_pred', None),
            'CADD': row.get('CADD_phred', None),
            'DANN': row.get('DANN_score', None)
        }), axis=1))
    }


@csrf_exempt
def mutisnp_civic(request):
    if request.method == 'POST':
        """
        Perform analysis for CIVIC and pathogenic data, matching phenotypes and generating drug combinations.
        """

        # Load the CSV file
        data = json.loads(request.body.decode('utf-8'))
        newJobID = data.get('newjobid', '')
        #newJobID='tjsBHrCIwM'
        folder_path = f"/miRTI/media/patient/{newJobID}"
        # json_file=f"/miRTI/media/patient/{newJobID}/summary.json"
        # with open(json_file, 'r', encoding='utf-8') as f:
        #     data = json.load(f)
        # diagnosis = data["diagnosis"]
        # print("diagnosis:", diagnosis)
        vcf_files = [file for file in os.listdir(folder_path) if file.endswith(".vcf")]
        csv_file_path = os.path.join(folder_path, 'mutiSNP_analysis_civic.csv')
        if os.path.exists(csv_file_path):
            with open(csv_file_path, mode='r', encoding='utf-8-sig') as csv_file:
                reader = csv.DictReader(csv_file)
                data = []

                for row in reader:
                    new_row = {}
                    new_row['Phenotype'] = row['Phenotype']
                    new_row['Therapies'] = row['Therapies']
                    new_row['civic_variant_name'] = row['civic_variant_name']
                    new_row['Location'] = row['Location']
                    new_row['Detailed_Location'] = row['Detailed_Location']
                    new_row['Gene'] = row['Gene']
                    new_row['RS ID'] = row['RS ID']

                    # 安全解析 MAF 欄位
                    maf_str = row.get('MAF', '')
                    try:
                        new_row['MAF'] = ast.literal_eval(maf_str)
                    except Exception:
                        new_row['MAF'] = {'gnomAD': None, '1000G': None, 'TW Biobank': None}

                    new_row['Domain'] = row['Domain']
                    new_row['Pathogenicity'] = row['Pathogenicity'].strip()

                    # 安全解析 Prediction 欄位
                    pred_str = row.get('Prediction', '')
                    try:
                        new_row['Prediction'] = ast.literal_eval(pred_str)
                    except Exception:
                        new_row['Prediction'] = {
                            'Polyphen2_HVAR': None, 'SIFT': None, 'VEST3': None,
                            'MutationTaster': None, 'MetaSVM': None, 'MetaLR': None,
                            'CADD': None, 'DANN': None
                        }

                    data.append(new_row)

            return JsonResponse(data, safe=False)
        if vcf_files:
            print(f"找到 VCF 檔案: {vcf_files}")

            # 遍歷每個找到的 .vcf 檔案
            for vcf_file in vcf_files:
                uploadFile_url = os.path.join(folder_path, vcf_file)  # 完整檔案路徑

                # 使用 os.path.basename 解析出檔案名稱
                file_name = os.path.basename(uploadFile_url)  # 例如 24C00131_main.vcf
                file_name_without_ext = os.path.splitext(file_name)[0]  # 例如 24C00131_main
                new_file_name = f"{file_name_without_ext}_vep_annovar_merge.csv"
                new_file_name1 = f"{file_name_without_ext}_vep_annovar_merge1.csv"
                # 打印相關訊息
                print(f'file_name : {file_name}')
                print(f'file_name_withouttxt: {file_name_without_ext}')
                print(f'uploadFile_target: {new_file_name}')
                print('---------------------VEP start-------------')
        else:
            print("該資料夾中沒有 .vcf 檔案")

        input_file = '/VEP/drug_database/drug/CIVIC/civic_filtered_profiles.csv'
        data = pd.read_csv(input_file, encoding='latin1')  # Specify encoding if UTF-8 fails
        json_file=f"/miRTI/media/patient/{newJobID}/summary.json"
        with open(json_file, 'r', encoding='utf-8') as f:
            data1 = json.load(f)
        diagnosis = data1["diagnosis"]
        print("diagnosis:", diagnosis)

        # Define the disease name to query
        disease_name = diagnosis

        # Query and extract unique civic_new values
        phenotype_set = set(data[data['combined_disease_name'] == disease_name]['civic_new'].dropna().unique())
        print(f"Unique civic_new values for disease '{disease_name}':")
        print(phenotype_set)

        # ======================== Pathogenic Processing ============================
        def generate_cosmic_preprocessor(row):
            gene = row['Gene.refGene']  
            variant = row['variant'] if 'variant' in row else None  
            if pd.isna(variant) or variant == "":  
                return f"{gene}"
            else:  
                return f"{gene} {variant}"

        # Load the annotation file
        annotation_file_path = f"/miRTI/media/patient/{newJobID}/{new_file_name1}"
        output_file = f"/miRTI/media/patient/{newJobID}/mutiSNP_analysis_civic.csv"
        annotation_data = pd.read_csv(annotation_file_path, encoding='ISO-8859-1')

        # Filter for pathogenic variants
        filtered_data = annotation_data[annotation_data['CLNSIG'].str.contains("Pathogenic", case=False, na=False)]
        filtered_data['civic_search'] = filtered_data.apply(generate_cosmic_preprocessor, axis=1)
        print("Pathogenic set")
        print(filtered_data)
        # Add detailed location information
        filtered_data['Location'] = (
            filtered_data['Chr'].astype(str) + ":" +
            filtered_data['Start'].astype(str) + "_" +
            filtered_data['End'].astype(str) +
            filtered_data['Ref'] + ">" + filtered_data['Alt']
        )
        filtered_data['Detailed_Location'] = filtered_data.apply(lambda row: (
            f"{row.get('Chr', '')}:" +
            f"{int(row.get('Start')) if isinstance(row.get('Start'), (int, float)) else row.get('Start')}_"
            f"{int(row.get('End')) if isinstance(row.get('End'), (int, float)) else row.get('End')}"
            f"{row.get('Ref', '')}>{row.get('Alt', '')} "
            f"transcript:{row.get('Feature', '').split('.')[0] if isinstance(row.get('Feature', str), str) else row.get('Feature')}"
        ), axis=1)
        print(filtered_data['civic_search'])

        # ======================== Matching and Result Analysis =======================
        pathogenic_set = set(filtered_data['civic_search'].dropna().unique())
        matching_results = check_phenotype_in_pathogenic(phenotype_set, pathogenic_set)
        therapies = find_therapies_for_phenotypes(data, phenotype_set, disease_name)
        can_be_assembled = []
        cannot_be_assembled = []
        drug_combinations = []


#        for phenotype, is_match in matching_results.items():
 #           if is_match:
  #              can_be_assembled.append(phenotype)
   #             components = [phenotype.strip().upper()]
    #            matching_rows = filtered_data[filtered_data['civic_search'].str.strip().str.upper() == phenotype.strip().upper()]
     #           drug_combinations.append(extract_drug_combinations(filtered_data, phenotype, components, matching_rows, therapies,disease_name))
      #      else:
       #         cannot_be_assembled.append(phenotype)
        for phenotype, is_match in matching_results.items():
            if is_match:
                can_be_assembled.append(phenotype)
                components = [phenotype.strip().upper()]
                # 在呼叫 extract_drug_combinations 時帶上 disease_name
                drug_combinations.append(extract_drug_combinations(filtered_data, phenotype, components, disease_name, therapies))
            else:
                cannot_be_assembled.append(phenotype)
        therapies = find_therapies_for_phenotypes(data, can_be_assembled, disease_name)

        # ========================== Output Results ===========================
        print("Phenotypes that CAN be assembled from pathogenic set:")
        for phenotype in can_be_assembled:
            print(f"- {phenotype} (Therapies: {therapies.get(phenotype, 'No therapy information found')})")

        # Save detailed drug combination information to a CSV file
        drug_combinations_df = pd.DataFrame(drug_combinations)
        output_file = f"/miRTI/media/patient/{newJobID}/mutiSNP_analysis_civic.csv"
        drug_combinations_df.to_csv(output_file, index=False)

#------------------------------------------------------------
        # Prepare JSON response

        response_data = {
            "drug_combinations": drug_combinations
        }

        return JsonResponse(response_data, safe=False)

#-------------------------------------------------------postgresql---------------------------------------------------------------
@csrf_exempt
# def postgresql(request):
#     if request.method == 'POST':

#         # Load the CSV file
#         data = json.loads(request.body.decode('utf-8'))
#         newJobID = data.get('newjobid', '')
#         #newJobID='tjsBHrCIwM'
#         folder_path = f"/miRTI/media/patient/{newJobID}"
#         vcf_files = [file for file in os.listdir(folder_path) if file.endswith(".vcf")]

#         if vcf_files:
#             print(f"找到 VCF 檔案: {vcf_files}")

#             for vcf_file in vcf_files:
#                 uploadFile_url = os.path.join(folder_path, vcf_file)  # 完整檔案路徑

#                 file_name = os.path.basename(uploadFile_url)  # 例如 24C00131_main.vcf
#                 basename = os.path.splitext(file_name)[0]  # 例如 24C00131_main


#         else:
#             print("該資料夾中沒有 .vcf 檔案")
#         load_csv_files_to_postgres_new(basename,newJobID)
#         return JsonResponse({"status": "success", "message": "資料已成功載入 PostgreSQL"})


@csrf_exempt
def postgresql(request):
    if request.method != 'POST':
        return JsonResponse({"status": "error", "message": "POST only"}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({"status": "error", "message": "invalid json"}, status=400)

    newJobID = data.get('newjobid', '')
    if not newJobID:
        return JsonResponse({"status": "error", "message": "newjobid required"}, status=400)

    folder_path = f"/miRTI/media/patient/{newJobID}"
    if not os.path.isdir(folder_path):
        return JsonResponse({"status": "error", "message": f"folder not found: {folder_path}"}, status=404)

    # 從 DB 拿 base_name(=subject_id) 與 user_id，比自己猜檔名更穩
    try:
        job = existJobs.jobs.get(jobID=newJobID)
        base_name = job.subject_id
        user_id = job.user_id
    except existJobs.jobs.model.DoesNotExist:
        # 退而求其次：從目錄裡找 vcf 檔名
        vcf_files = [f for f in os.listdir(folder_path) if f.endswith(".vcf")]
        if not vcf_files:
            return JsonResponse({"status": "error", "message": "no .vcf in folder and job not found"}, status=404)
        file_name = os.path.splitext(os.path.basename(vcf_files[0]))[0]
        base_name = file_name
        user_id = 0  # 無法辨識使用者時給個預設，或直接 return error

    # 呼叫匯入
    try:
        load_csv_files_to_postgres_new(
            base_name=base_name,
            newjobID=newJobID,
            user_id=user_id,
            media_root="/miRTI/media",
            # dsn= {...}  # 如需覆蓋環境變數在此傳入
        )
        return JsonResponse({"status": "success", "message": "資料已成功載入 PostgreSQL"})
    except Exception as e:
        return JsonResponse({"status": "error", "message": f"import failed: {e}"}, status=500)





#--------------------------------------------------------MUTATION Signature-------------------------------------------------------
from SigProfilerAssignment import Analyzer as Analyze
import matplotlib.pyplot as plt


def extract_DP_and_VF(tmp):
    #print(tmp)
    tmp_content=tmp['Otherinfo13'].split(':')
    tmp_header=tmp['Otherinfo12'].split(':')
    tmp_dict = {key: val for key, val in zip(tmp_header, tmp_content)}
    return int(tmp_dict['DP']), float(tmp_dict['VF'])
def variant_type(tmp):
    if((tmp['Ref']=='-') | (tmp['Alt']=='-')):
        return('INDEL')
    elif((tmp['Ref'] in ['A','T','C','G']) & (tmp['Alt'] in ['A','T','C','G'])):
        return('SNP')
    else:
        return('MNP')




@csrf_exempt
def mutation_signature(request):
    if request.method == 'POST':
        data = json.loads(request.body.decode('utf-8'))
        newjobid = data.get('newjobid', '')
        #newjobid='WGUIvPqaMA'
        folder_path = f"/miRTI/media/patient/{newjobid}"
        vcf_files = [file for  file in os.listdir(folder_path) if file.endswith(".vcf")]
        mut_filestore = f"/miRTI/media/patient/{newjobid}/mutSig"
        pdf_path= f'/miRTI/media/patient/{newjobid}/mutSig/pie_chart.pdf'
        SBS_file=pd.read_csv('/miRTI/hw1/mutational_signature/aetiology_map.tsv',sep='\t')
        pdf_path1=f'/miRTI/media/patient/{newjobid}/mutSig/Assignment/Assignment_Solution/Activities/Assignment_Solution_Activity_Plots.pdf'
        pdf_path2=f'/miRTI/media/patient/{newjobid}/mutSig/Assignment/Assignment_Solution/Activities/Assignment_Solution_TMB_plot.pdf'
        #---------------------------------------如果本身就跑好的話就直接讀取檔案----------------------------------------------------
        activities_path = f"{mut_filestore}/Assignment/Assignment_Solution/Activities/Assignment_Solution_Activities.txt"
        if os.path.exists(pdf_path) and os.path.exists(pdf_path1) and os.path.exists(pdf_path2) and os.path.exists(activities_path):
            print("🔹 檢測到已存在的分析結果，直接讀取檔案。")
        #------------------------------------------------activities_path是讀取套件跑好的SBS分布----------------------------
            activities_path = f"{mut_filestore}/Assignment/Assignment_Solution/Activities/Assignment_Solution_Activities.txt"
            signature_to_description = dict(zip(SBS_file['signature'], SBS_file['aetiology']))
            print(signature_to_description)
       #--------------------------------------------用base64解碼pdf檔案 此為圓餅圖-----------------------------------
            with open(pdf_path, 'rb') as pdf_file:
                pdf_base64 = base64.b64encode(pdf_file.read()).decode('utf-8')
       #-------------------------------------------用base64解碼pdf檔案 此為第二張圖pdf圖片
            with open(pdf_path1, 'rb') as pdf_file:
                pdf_base64_activity_plot = base64.b64encode(pdf_file.read()).decode('utf-8')
           #---------------------------------------用base64解碼第三張pdf 
            with open(pdf_path2, 'rb') as pdf_file:
                pdf_base64_TMB_plot = base64.b64encode(pdf_file.read()).decode('utf-8')

      #---------------------------------------------打開txt文件檔 SBS分布-------------------
            with open(activities_path, 'r') as activities_file:
                activities_content = activities_file.readlines()

            enhanced_activities_data = []
    #--------------------------------------------------------------------------- 這邊去把sbs文件內的資料去跟sbs的病徵說明去合併 ex: SBS1 : SBS_description 然後輸出成json檔案
            activities_data = []

            headers = activities_content[0].strip().split('\t')
            for line in activities_content[1:]:
                values = line.strip().split('\t')
                activity_dict = dict(zip(headers, values))
                filtered_activity = filter_zero_values(activity_dict, key_to_keep='Samples')

                # 計算所有 SBS 的總和
                total_sbs = sum(int(value) for key, value in filtered_activity.items() if key.startswith("SBS") and value.isdigit())

                # 建立新字典，將 description 和 rate 插入對應的 SBS 後面
                ordered_activity = {}
                for key, value in filtered_activity.items():
                    ordered_activity[key] = value  # 保留原有鍵值
                    if key.startswith("SBS") and key in signature_to_description:
                        # 插入描述
                        ordered_activity[f"{key}_description"] = signature_to_description[key]
                        # 計算比例並插入
                        if total_sbs > 0:
                            rate = int(value) / total_sbs  # 計算比例
                            ordered_activity[f"{key}_rate"] = f"{rate:.2f}"  # 格式化為小數點兩位數
                        else:
                            ordered_activity[f"{key}_rate"] = "0.00"  # 總和為 0 時的處理

                activities_data.append(ordered_activity)
                print(activities_data)
      #-------------------------------------------------------------------------------
            try:

                response_data = {
                    'activities': activities_data,
                    'pdf_base64': pdf_base64,  # Base64 編碼的 PDF
                    'pdf_base64_activity_plot': pdf_base64_activity_plot,
                    'pdf_base64_TMB_plot': pdf_base64_TMB_plot,
                }
                return JsonResponse(response_data, safe=False)
            except Exception as e:
                error_response = {'error': str(e)}
                return JsonResponse(error_response, status=500)

        print("🔹 沒有找到已分析的結果，開始執行 mutation signature 分析...")
        if vcf_files:
            print(f"找到 VCF 檔案: {vcf_files}")

                # 遍歷每個找到的 .vcf 檔案
            for vcf_file in vcf_files:
                uploadFile_url = os.path.join(folder_path, vcf_file)  # 完整檔案路徑

                    # 使用 os.path.basename 解析出檔案名稱
                file_name = os.path.basename(uploadFile_url)  # 例如 24C00131_main.vcf
                file_name_without_ext = os.path.splitext(file_name)[0]  # 例如 24C00131_main
                new_file_name = f"{file_name_without_ext}_vep_annovar_merge.csv"
                new_file_name1=f"{file_name_without_ext}_vep_annovar_merge1.csv"
                    # 打印相關訊息
                print(f'file_name : {file_name}')
                print(f'file_name_withouttxt: {file_name_without_ext}')
                print(f'uploadFile_target: {new_file_name}')
                print('---------------------VEP start-------------')
            else:
                print("該資料夾中沒有 .vcf 檔案")
        #--------------------------------------------------------讀取病人頁面中的已經註解好的檔案當作輸入---------------------
        test_variants = pd.read_csv(f'/miRTI/media/patient/{newjobid}/{file_name_without_ext}_annovar_final.txt', sep="\t")
        if 'DP' in test_variants.columns and 'VAF' in test_variants.columns:
            print("Columns 'DP' and 'VAF' already exist.")
        else:

            test_variants[['DP', 'VAF']] = test_variants.apply(lambda x: pd.Series(extract_DP_and_VF(x)), axis=1)

#---------------------------------------------------------檔案去篩選allele frequency<1 persent  意思就是去篩somatic發生點------
        filter_gnomad=test_variants['AF'].apply(lambda x: -1 if x=='.' else float(x))<0.01
        filter_1000G=test_variants['1000g2015aug_all'].apply(lambda x: -1 if x=='.' else float(x))<0.01
        filter_VAF=test_variants['VAF']>=0
        filter_DP=test_variants['DP']>=0
#--------------------------------------------------------篩完後只需要這四個欄位------------------------------------------------
        filtered_population1=pd.read_csv(f'/miRTI/media/patient/{newjobid}/df_population.csv')
        print(filtered_population1)



        filtered_population=test_variants[filter_gnomad & filter_1000G & filter_VAF & filter_DP]
        print(filtered_population[['Chr', 'Start', 'Ref', 'Alt']])
        print(filtered_population.shape)  

        filtered_population['variant_type']=filtered_population.apply(lambda x: variant_type(x),axis=1)
        filtered_population['variant_type'].value_counts()

        aa=filtered_population[['Chr','Start','Ref','Alt']]
        aa['sample']='sample'
#-------------------------------------------------------指定套件輸出的目標文件夾-------------------------------------------------
        # result_path=r"C:\Users\user\Desktop\林醫師VCF團隊\20241223task\sigProfilerAssignment\sigProfilerAssignment\data\22C00022_TSO500\mutSig"
        result_path=f'/miRTI/media/patient/{newjobid}/mutSig'


        if not os.path.exists(result_path):
            os.mkdir(result_path)
        aa[['Chr','Start','sample','Ref','Alt']].to_csv(f"{result_path}/filtered.vcf",sep='\t',index=None,header=None)
#--------------------------------------------------------用套件去跑就可以得到mutation siganature的資料----------------------------
        Analyze.cosmic_fit(samples=result_path, 
                        output=f"{result_path}/Assignment",
                        input_type="vcf",
                        context_type="96",
                        genome_build="GRCh37",
                        make_plots=True,
                        sample_reconstruction_plots=True,
                        exclude_signature_subgroups=None,
                        cosmic_version=3.4)

        aetiology=pd.read_csv('/miRTI/hw1/mutational_signature/aetiology_map.tsv',sep='\t')
        tmp_signature_assignment=pd.read_csv(f"{result_path}/Assignment/Assignment_Solution/Activities/Assignment_Solution_Activities.txt",sep='\t')
        tmp_signature_assignment={tmp_signature_assignment.columns[i]:tmp_signature_assignment.iloc[0,i] for i in range(1,tmp_signature_assignment.shape[1]) }
        tmp_signature_assignment={i:round(tmp_signature_assignment[i]/sum(tmp_signature_assignment.values()),2)  for i in tmp_signature_assignment.keys()}

        plotdata=pd.DataFrame.from_dict({'signature':tmp_signature_assignment.keys(),'freq':tmp_signature_assignment.values()})
        plotdata=plotdata[plotdata['freq']!=0]
        plotdata=pd.merge(plotdata,aetiology,on='signature',how='left')
        plotdata.loc[plotdata['aetiology'].isnull(),'aetiology']='Possible sequencing artefact'

        labels = list(tmp_signature_assignment.keys())
        sizes = list(tmp_signature_assignment.values())
        fig1, ax1 = plt.subplots()
        ax1.pie(plotdata['freq'], labels=plotdata['signature']+'\n'+plotdata['aetiology'], autopct='%1.1f%%', startangle=90)
        plt.savefig(f"{result_path}/pie_chart.pdf", format="pdf", bbox_inches="tight")
        plt.close()



# --------------------------------------------------讀取txt檔案 就是mutation signature分布--------------------------------------
        #activities_path = f"{result_path}/Assignment/Assignment_Solution/Activities/Assignment_Solution_Activities.txt"


        #with open(activities_path, 'r') as activities_file:
         #   activities_content = activities_file.readlines()

        #activities_data = []
       # headers = activities_content[0].strip().split('\t')
        #for line in activities_content[1:]:
         #   values = line.strip().split('\t')
          #  activities_data.append(dict(zip(headers, values)))
           # filtered_activity = filter_zero_values(activity_dict, key_to_keep='Samples')
     #       print(filtered_activity)
      #      activities_data.append(filtered_activity)
        #------------------------------------------------activities_path是讀取套件跑好的SBS分布----------------------------
        activities_path = f"{mut_filestore}/Assignment/Assignment_Solution/Activities/Assignment_Solution_Activities.txt"
        signature_to_description = dict(zip(SBS_file['signature'], SBS_file['aetiology']))
        print(signature_to_description)
       #--------------------------------------------用base64解碼pdf檔案 此為圓餅圖-----------------------------------
        with open(pdf_path, 'rb') as pdf_file:
            pdf_base64 = base64.b64encode(pdf_file.read()).decode('utf-8')
       #-------------------------------------------用base64解碼pdf檔案 此為第二張圖pdf圖片
        with open(pdf_path1, 'rb') as pdf_file:
            pdf_base64_activity_plot = base64.b64encode(pdf_file.read()).decode('utf-8')
           #---------------------------------------用base64解碼第三張pdf
        with open(pdf_path2, 'rb') as pdf_file:
            pdf_base64_TMB_plot = base64.b64encode(pdf_file.read()).decode('utf-8')

      #---------------------------------------------打開txt文件檔 SBS分布-------------------
        with open(activities_path, 'r') as activities_file:
            activities_content = activities_file.readlines()

        enhanced_activities_data = []
    #--------------------------------------------------------------------------- 這邊去把sbs文件內的資料去跟sbs的病徵說明去合併 ex: SBS1 : SBS_description 然後輸出成json檔案
        activities_data = []

        headers = activities_content[0].strip().split('\t')
        for line in activities_content[1:]:
            values = line.strip().split('\t')
            activity_dict = dict(zip(headers, values))
            filtered_activity = filter_zero_values(activity_dict, key_to_keep='Samples')

                # 計算所有 SBS 的總和
            total_sbs = sum(int(value) for key, value in filtered_activity.items() if key.startswith("SBS") and value.isdigit())

                # 建立新字典，將 description 和 rate 插入對應的 SBS 後面
            ordered_activity = {}
            for key, value in filtered_activity.items():
                ordered_activity[key] = value  # 保留原有鍵值
                if key.startswith("SBS") and key in signature_to_description:
                        # 插入描述
                    ordered_activity[f"{key}_description"] = signature_to_description[key]
                        # 計算比例並插入
                    if total_sbs > 0:
                        rate = int(value) / total_sbs  # 計算比例
                        ordered_activity[f"{key}_rate"] = f"{rate:.2f}"  # 格式化為小數點兩位數
                    else:
                        ordered_activity[f"{key}_rate"] = "0.00"  # 總和為 0 時的處理

            activities_data.append(ordered_activity)
            print(activities_data)


        try:
            with open(pdf_path, 'rb') as pdf_file:
                pdf_base64 = base64.b64encode(pdf_file.read()).decode('utf-8')
            response_data = {
                'activities': activities_data,
                'pdf_base64': pdf_base64,
                'pdf_base64_activity_plot': pdf_base64_activity_plot,
                'pdf_base64_TMB_plot': pdf_base64_TMB_plot,
            }
            #response_data = {
             #   'activities': activities_data,
              #  'pdf_base64': pdf_base64,  # Base64 編碼的 PDF
            #}
            return JsonResponse(response_data, safe=False)
        except Exception as e:
            error_response = {'error': str(e)}
            return JsonResponse(error_response, status=500)




#--------------------------------------------------------MUTATION Signature END---------------------------------------------------
#--------------------------------------------------------postgresql load表備用def--------------------------------------------------
import psycopg2
import pandas as pd
import os

def load_csv_files_to_postgres(base_name, newjobID):
    """
    批次載入 4 個 CSV 檔案到 PostgreSQL，表名格式為 {base_name}_{file_type}_{newjobID}

    :param base_name: 病人識別碼
    :param newjobID: 任務 ID
    """

    DB_NAME = "somatic"
    DB_USER = "uuuwei0504"
    DB_PASSWORD = "REDACTED_SET_VIA_ENV"
    DB_HOST = "172.17.0.1"  # Docker 內部 IP
    DB_PORT = "5432"

    FILE_TYPES = [
        f'{base_name}_vep_annovar_merge',
        "drug_combinations_cosmic",
        "mutiSNP_analysis_civic",
        "somatic_result"
    ]

    def get_csv_path(newjobID, file_type):
        """取得 CSV 檔案的路徑"""
        return f"/miRTI/media/patient/{newjobID}/{file_type}.csv"

    def generate_table_name(base_name, file_type, newjobID):
        """根據 base_name, file_type, newjobID 產生表名"""
        return f"{file_type}_{newjobID}"

    def check_table_exists(conn, table_name):
        """檢查 PostgreSQL 是否已經有該表且有資料"""
        query = f"SELECT COUNT(*) FROM information_schema.tables WHERE table_name = '{table_name}';"
        with conn.cursor() as cur:
            cur.execute(query)
            exists = cur.fetchone()[0] > 0
            if exists:
                cur.execute(f"SELECT COUNT(*) FROM \"{table_name}\";")
                count = cur.fetchone()[0]
                return count > 0  # 如果有資料，則回傳 True
        return False

    def create_table_from_csv(csv_file, conn, table_name):
        """根據 CSV 建立 PostgreSQL 表"""
        df = pd.read_csv(csv_file, nrows=5)  # 讀取前 5 行確認欄位名稱
        columns = df.columns

        column_definitions = ", ".join([f'"{col}" TEXT' for col in columns])

        create_table_query = f"""
        DROP TABLE IF EXISTS "{table_name}";
        CREATE TABLE "{table_name}" (
            {column_definitions}
        );
        """

        with conn.cursor() as cur:
            cur.execute(create_table_query)
            conn.commit()
        print(f"✅ 創建表: {table_name}")

    def load_csv_to_postgres(csv_file, conn, table_name):
        """將 CSV 匯入 PostgreSQL"""
        try:
            with conn.cursor() as cur:
                with open(csv_file, 'r', encoding='utf-8') as f:
                    cur.copy_expert(
                        f"COPY \"{table_name}\" FROM STDIN WITH CSV HEADER DELIMITER ',' NULL ''", f
                    )
                conn.commit()
                print(f"✅ 成功匯入: {csv_file} 到 {table_name}")
        except Exception as e:
            conn.rollback()
            print(f"❌ 匯入失敗: {csv_file}, 錯誤: {e}")

    # 🚀 連接 PostgreSQL 並載入 CSV
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        print("✅ 成功連接 PostgreSQL")

        for file_type in FILE_TYPES:
            csv_file = get_csv_path(newjobID, file_type)
            table_name = generate_table_name(base_name, file_type, newjobID)

            if check_table_exists(conn, table_name):
                print(f"⚠️ 資料表 {table_name} 已存在且有資料，跳過...")
                continue  

            if not os.path.exists(csv_file):
                print(f"⚠️ 找不到 CSV: {csv_file}，跳過...")
                continue


            create_table_from_csv(csv_file, conn, table_name)


            load_csv_to_postgres(csv_file, conn, table_name)

    except Exception as e:
        print(f"❌ PostgreSQL 連線失敗: {e}")
    finally:
        if 'conn' in locals():
            conn.close()
            print("🔌 已關閉 PostgreSQL 連線")


#--------------------------------------------------------postgresql END-----------------------------------------------------


import os
import re
import os.path as osp
import datetime
import pandas as pd
import psycopg2
from psycopg2 import sql

def _sanitize_ident(name: str) -> str:
    s = re.sub(r'[^a-zA-Z0-9_]+', '_', str(name).strip())
    s = s.strip('_')
    if not s:
        s = 'id'
    if s[0].isdigit():
        s = f'c_{s}'
    return s.lower()

def _dedup(names):
    seen, out = {}, []
    for n in names:
        k = (str(n).strip() or "col")
        if k not in seen:
            seen[k] = 0
            out.append(k)
        else:
            seen[k] += 1
            out.append(f"{k}_{seen[k]}")
    return out

def load_csv_files_to_postgres_new(base_name, newjobID, *, user_id,
                                   media_root="/miRTI/media",
                                   log_path="/miRTI/logs/postgres_import.log",
                                   dsn=None):
    """
    批次載入 CSV 檔案到 PostgreSQL
    以 user_id 建立 schema：user_<user_id>

    ✅ 改用 dbpool.py 的連線池：with PgConn() as conn
    """

    import os, re, glob, datetime, pandas as pd, os.path as osp
    from psycopg2 import sql

    # ✅ 改用你自己的 dbpool（集中管理連線資訊）
    from .postgressql_setting.dbpool import PgConn

    MERGE_FILE_TYPES = ["drug_combinations_cosmic", "mutiSNP_analysis_civic", "somatic_result"]
    CLASSIFICATION_FILES = ["COSMIC.csv", "suspect.csv", "heredity.csv"]

    def _dedup(seq):
        seen = set()
        res = []
        for x in seq:
            if x not in seen:
                seen.add(x)
                res.append(x)
        return res

    def _sanitize_ident(s):
        return re.sub(r'[^A-Za-z0-9_]', '_', str(s))

    def get_csv_path(job_id, file_type):
        if file_type.endswith(".csv"):
            fname = file_type
        else:
            fname = f"{file_type}.csv"
        return f"{media_root}/patient/{job_id}/{fname}"

    def make_table_name(name: str) -> str:
        s = re.sub(r'[^A-Za-z0-9_]', '_', str(name))
        if not re.match(r'^[A-Za-z_]', s):
            s = f'X_{s}'
        return s

    schema_name = _sanitize_ident(f"user_{user_id}")
    base_dir = f"{media_root}/patient/{newjobID}"

    # ======== 建 schema & trigger function ======== #
    def ensure_schema(conn):
        with conn.cursor() as cur:
            cur.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(schema_name)))

    def ensure_time_trigger_func(conn, schema):
        with conn.cursor() as cur:
            cur.execute(sql.SQL("""
            CREATE OR REPLACE FUNCTION {}.touch_updated_at()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = NOW();
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            """).format(sql.Identifier(schema)))

    # ======== 查表與建立表 ======== #
    def table_exists_with_rows(conn, schema, table):
        with conn.cursor() as cur:
            cur.execute(
                sql.SQL("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=%s AND table_name=%s"),
                (schema, table)
            )
            exists = cur.fetchone()[0] > 0
            if not exists:
                return False
            cur.execute(sql.SQL("SELECT COUNT(*) FROM {}.{}")
                        .format(sql.Identifier(schema), sql.Identifier(table)))
            cnt = cur.fetchone()[0]
            return cnt > 0

    def create_table_from_df(df, conn, schema, table):
        data_cols = _dedup(list(df.columns))
        for c in ("created_at", "updated_at"):
            if c in data_cols:
                data_cols = [f"{c}_orig" if x == c else x for x in data_cols]

        col_defs = sql.SQL(", ").join(
            sql.SQL("{} TEXT").format(sql.Identifier(c)) for c in data_cols
        )

        with conn.cursor() as cur:
            cur.execute(sql.SQL("DROP TABLE IF EXISTS {}.{}")
                        .format(sql.Identifier(schema), sql.Identifier(table)))
            cur.execute(sql.SQL("""
                CREATE TABLE {}.{} (
                    {},
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
            """).format(sql.Identifier(schema), sql.Identifier(table), col_defs))

            cur.execute(sql.SQL("CREATE INDEX IF NOT EXISTS {} ON {}.{} (created_at)")
                        .format(
                            sql.Identifier(f"{table}_created_at_idx"),
                            sql.Identifier(schema),
                            sql.Identifier(table)
                        ))

            cur.execute(sql.SQL("""
                DROP TRIGGER IF EXISTS {} ON {}.{};
                CREATE TRIGGER {}
                BEFORE UPDATE ON {}.{}
                FOR EACH ROW
                EXECUTE FUNCTION {}.touch_updated_at();
            """).format(
                sql.Identifier(f"{table}_touch_updated_at"),
                sql.Identifier(schema), sql.Identifier(table),
                sql.Identifier(f"{table}_touch_updated_at"),
                sql.Identifier(schema), sql.Identifier(table),
                sql.Identifier(schema)
            ))

        return data_cols

    def copy_df(df, conn, schema, table, data_cols):
        tmp_csv = f"/tmp/{schema}.{table}.csv"
        df[data_cols].to_csv(tmp_csv, index=False)
        with conn.cursor() as cur, open(tmp_csv, "r", encoding="utf-8") as f:
            cols_sql = sql.SQL(", ").join(sql.Identifier(c) for c in data_cols)
            copy_sql = sql.SQL("COPY {}.{} ({}) FROM STDIN WITH CSV HEADER DELIMITER ',' NULL ''") \
                       .format(sql.Identifier(schema), sql.Identifier(table), cols_sql)
            cur.copy_expert(copy_sql.as_string(conn), f)
        os.remove(tmp_csv)

    # ======== 驗證 & Log ======== #
    def verify_and_log(conn, created_tables, skipped_files, section):
        rows_info = []
        with conn.cursor() as cur:
            for sch, tbl in created_tables:
                cur.execute(sql.SQL("SELECT COUNT(*) FROM {}.{}")
                            .format(sql.Identifier(sch), sql.Identifier(tbl)))
                cnt = cur.fetchone()[0]
                rows_info.append((sch, tbl, cnt))
                print(f"📊 驗證：{sch}.{tbl} → {cnt} rows")

        try:
            os.makedirs(osp.dirname(log_path), exist_ok=True)
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(log_path, "a", encoding="utf-8") as logf:
                logf.write(f"[{now}] IMPORT ({section}) job={newjobID} user={user_id} schema={schema_name}\n")
                for sch, tbl, cnt in rows_info:
                    logf.write(f"  - {sch}.{tbl}: {cnt} rows\n")
                if skipped_files:
                    logf.write(f"  - skipped: {len(skipped_files)} files\n")
        except Exception as e:
            print(f"⚠️ 寫入 log 失敗：{e}")

    # ======== 主流程 ======== #
    created_tables = []
    skipped_files = []

    try:
        # ✅ 改用 pool 取得連線；讓 PgConn 幫你做 commit/rollback
        with PgConn(autocommit=False) as conn:
            print("✅ 成功連接 PostgreSQL（dbpool）")
            ensure_schema(conn)
            ensure_time_trigger_func(conn, schema_name)
            print(f"✅ 使用 schema: {schema_name}")

            # === (1) vep_annovar_merge_{newjobID} ===
            vep_table = make_table_name(f"vep_annovar_merge_{newjobID}")
            vep_candidates = glob.glob(osp.join(base_dir, "*_vep_annovar_merge.csv"))

            if not vep_candidates:
                print(f"⚠️ 找不到任何 VEP 檔案，跳過")
                skipped_files.append(f"{base_dir}/*_vep_annovar_merge.csv")
            else:
                vep_csv = vep_candidates[0]
                print(f"✅ 偵測到 VEP 檔案：{vep_csv}")
                if table_exists_with_rows(conn, schema_name, vep_table):
                    print(f"⚠️ {schema_name}.{vep_table} 已存在且有資料，跳過")
                else:
                    df_vep = pd.read_csv(vep_csv, encoding="utf-8-sig", skip_blank_lines=True)
                    if df_vep.empty or len(df_vep.columns) == 0:
                        print(f"⚠️ 檔案為空或無欄位，跳過")
                    else:
                        data_cols = create_table_from_df(df_vep, conn, schema_name, vep_table)
                        copy_df(df_vep, conn, schema_name, vep_table, data_cols)
                        created_tables.append((schema_name, vep_table))

            # === (2) 合併三張成 somatic_result_{newjobID} ===
            dfs, all_cols = [], set()
            for ft in MERGE_FILE_TYPES:
                csv_file = get_csv_path(newjobID, ft)
                if osp.exists(csv_file):
                    try:
                        df = pd.read_csv(csv_file, encoding="utf-8-sig", skip_blank_lines=True)
                        if df.empty or len(df.columns) == 0:
                            print(f"⚠️ 檔案為空或無欄位：{csv_file}")
                            continue
                        all_cols.update(df.columns)
                        dfs.append(df)
                        print(f"✅ 讀取 {csv_file}：{len(df)} rows")
                    except Exception as e:
                        print(f"❌ 讀取 {csv_file} 失敗：{e}")
                else:
                    skipped_files.append(csv_file)

            if dfs:
                aligned = [d.reindex(columns=list(all_cols)) for d in dfs]
                df_merged = pd.concat(aligned, ignore_index=True)
                merged_table = make_table_name(f"somatic_result_{newjobID}")
                if table_exists_with_rows(conn, schema_name, merged_table):
                    print(f"⚠️ {schema_name}.{merged_table} 已存在且有資料，跳過")
                else:
                    data_cols = create_table_from_df(df_merged, conn, schema_name, merged_table)
                    copy_df(df_merged, conn, schema_name, merged_table, data_cols)
                    created_tables.append((schema_name, merged_table))
            else:
                print("⚠️ 沒有可合併的 CSV")

            # === (3) classification ===
            dfs_cls = []
            for fname in CLASSIFICATION_FILES:
                csv_file = get_csv_path(newjobID, fname)
                if osp.exists(csv_file):
                    try:
                        df = pd.read_csv(csv_file, encoding="utf-8-sig", skip_blank_lines=True)
                        if df.empty or len(df.columns) == 0:
                            print(f"⚠️ {fname} 為空或無欄位")
                        else:
                            dfs_cls.append(df)
                            print(f"✅ 讀取 {fname}：{len(df)} rows")
                    except Exception as e:
                        print(f"❌ 讀取 {fname} 失敗：{e}")
                else:
                    skipped_files.append(csv_file)

            if dfs_cls:
                df_cls = pd.concat(dfs_cls, ignore_index=True)
                cls_table = make_table_name(f"{newjobID}_classification")
                if table_exists_with_rows(conn, schema_name, cls_table):
                    print(f"⚠️ {schema_name}.{cls_table} 已存在且有資料，跳過")
                else:
                    data_cols = create_table_from_df(df_cls, conn, schema_name, cls_table)
                    copy_df(df_cls, conn, schema_name, cls_table, data_cols)
                    created_tables.append((schema_name, cls_table))
            else:
                print("⚠️ 無 classification CSV 可載入")

            # === (4) somatic_result_delete_list_final_result ===
            sr_file = get_csv_path(newjobID, "somatic_result_delete_list_final_result")
            sr_table = make_table_name(f"{newjobID}_somaticResult")
            if osp.exists(sr_file):
                if table_exists_with_rows(conn, schema_name, sr_table):
                    print(f"⚠️ {schema_name}.{sr_table} 已存在且有資料，跳過")
                else:
                    try:
                        df_sr = pd.read_csv(sr_file, encoding="utf-8-sig", skip_blank_lines=True)
                        if df_sr.empty or len(df_sr.columns) == 0:
                            print(f"⚠️ somaticResult 為空或無欄位")
                        else:
                            data_cols = create_table_from_df(df_sr, conn, schema_name, sr_table)
                            copy_df(df_sr, conn, schema_name, sr_table, data_cols)
                            created_tables.append((schema_name, sr_table))
                    except Exception as e:
                        print(f"❌ 讀取 {sr_file} 失敗：{e}")
            else:
                skipped_files.append(sr_file)

            # ✅ 不需要 conn.commit()：離開 with PgConn() 時會自動 commit（沒 exception）
            print("🎉 匯入流程完成（準備提交）")

            # 仍然可以在同一個 conn 裡做驗證（交易提交前也能查到）
            verify_and_log(conn, created_tables, skipped_files, section="pipeline-import")

    except Exception as e:
        # ✅ rollback 由 PgConn.__exit__ 自動處理（發生 exception）
        try:
            os.makedirs(osp.dirname(log_path), exist_ok=True)
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(log_path, "a", encoding="utf-8") as logf:
                logf.write(f"[{now}] ❌ IMPORT FAILED job={newjobID} user={user_id} schema={schema_name} err={e}\n")
        except Exception:
            pass
        print(f"❌ 匯入流程失敗：{e}")
        raise




# def load_csv_files_to_postgres_new(base_name, newjobID):
#     """
#     批次載入 CSV 檔案到 PostgreSQL：
#     - `vep_annovar_merge_{newjobID}` 獨立載入
#     - `drug_combinations_cosmic`, `mutiSNP_analysis_civic`, `somatic_result` 合併為 `somatic_result_{newjobID}`
#     """

#     # ======== PostgreSQL 連線資訊 ======== #
#     DB_NAME = "somatic"
#     DB_USER = "uuuwei0504"
#     DB_PASSWORD = "REDACTED_SET_VIA_ENV"
#     DB_HOST = "140.116.214.138"  # Docker 內部 IP
#     DB_PORT = "5432"

#     # ======== 定義要處理的檔案 ======== #
#     VEP_FILE_TYPE = f"{base_name}_vep_annovar_merge"  # 這張表獨立載入
#     MERGE_FILE_TYPES = [
#         "drug_combinations_cosmic",
#         "mutiSNP_analysis_civic",
#         "somatic_result"
#     ]

#     # CSV 檔案路徑
#     def get_csv_path(newjobID, file_type):
#         return f"/miRTI/media/patient/{newjobID}/{file_type}.csv"

#     # 產生表名
#     def generate_table_name(file_type, newjobID):
#         return f"{file_type}_{newjobID}"

#     # 檢查表是否存在且有資料
#     def check_table_exists(conn, table_name):
#         query = f"SELECT COUNT(*) FROM information_schema.tables WHERE table_name = '{table_name}';"
#         with conn.cursor() as cur:
#             cur.execute(query)
#             exists = cur.fetchone()[0] > 0
#             if exists:
#                 cur.execute(f"SELECT COUNT(*) FROM \"{table_name}\";")
#                 count = cur.fetchone()[0]
#                 return count > 0  # 如果有資料則回傳 True
#         return False

#     # 創建 PostgreSQL 表
#     def create_table_from_df(df, conn, table_name):
#         """根據 DataFrame 建立 PostgreSQL 表"""
#         columns = df.columns
#         column_definitions = ", ".join([f'"{col}" TEXT' for col in columns])

#         create_table_query = f"""
#         DROP TABLE IF EXISTS "{table_name}";
#         CREATE TABLE "{table_name}" (
#             {column_definitions}
#         );
#         """

#         with conn.cursor() as cur:
#             cur.execute(create_table_query)
#             conn.commit()
#         print(f"✅ 創建表: {table_name}")

#     # 將 DataFrame 匯入 PostgreSQL
#     def load_df_to_postgres(df, conn, table_name):
#         """將 DataFrame 匯入 PostgreSQL"""
#         try:
#             with conn.cursor() as cur:
#                 column_names = ", ".join([f'"{col}"' for col in df.columns])
#                 copy_sql = f"COPY \"{table_name}\" ({column_names}) FROM STDIN WITH CSV HEADER DELIMITER ',' NULL 'NaN'"

#                 temp_csv = f"/tmp/{table_name}.csv"
#                 df.to_csv(temp_csv, index=False)

#                 with open(temp_csv, 'r', encoding='utf-8') as f:
#                     cur.copy_expert(copy_sql, f)

#                 os.remove(temp_csv)
#                 conn.commit()
#                 print(f"✅ 成功匯入: {table_name}")

#         except Exception as e:
#             conn.rollback()
#             print(f"❌ 匯入失敗: {table_name}, 錯誤: {e}")

#     # 連接 PostgreSQL
#     try:
#         conn = psycopg2.connect(
#             dbname=DB_NAME,
#             user=DB_USER,
#             password=DB_PASSWORD,
#             host=DB_HOST,
#             port=DB_PORT
#         )
#         print("✅ 成功連接 PostgreSQL")

#         # ========== 1. 獨立載入 vep_annovar_merge ========== #
#         vep_csv_file = get_csv_path(newjobID, VEP_FILE_TYPE)
#         vep_table_name = f"vep_annovar_merge_{newjobID}"

#         if os.path.exists(vep_csv_file):
#             if not check_table_exists(conn, vep_table_name):
#                 df_vep = pd.read_csv(vep_csv_file)
#                 create_table_from_df(df_vep, conn, vep_table_name)
#                 load_df_to_postgres(df_vep, conn, vep_table_name)
#             else:
#                 print(f"⚠️ 資料表 {vep_table_name} 已存在且有資料，跳過...")
#         else:
#             print(f"⚠️ 找不到 CSV: {vep_csv_file}，跳過...")

#         # ========== 2. 合併 3 張表為 somatic_result_{newjobID} ========== #
#         dfs = []
#         all_columns = set()

#         # **1️⃣ 找出所有欄位**
#         for file_type in MERGE_FILE_TYPES:
#             csv_file = get_csv_path(newjobID, file_type)
#             if os.path.exists(csv_file):
#                 try:
#                     df = pd.read_csv(csv_file, encoding='utf-8-sig', skip_blank_lines=True)
#                     if df.empty or len(df.columns) == 0:
#                         print(f"⚠️ 檔案為空或無欄位：{csv_file}，跳過")
#                         continue
#                     all_columns.update(df.columns)
#                     dfs.append(df)
#                     print(f"✅ 讀取 {csv_file} 成功，共 {len(df)} 筆")
#                 except Exception as e:
#                     print(f"❌ 讀取 {csv_file} 時發生錯誤：{e}")
#             else:
#                 print(f"⚠️ 找不到 CSV: {csv_file}，跳過...")


#         if dfs:
#             # **2️⃣ 重新對齊所有 CSV 欄位**
#             dfs = [df.reindex(columns=all_columns) for df in dfs]

#             # **3️⃣ 合併 DataFrame**
#             df_merged = pd.concat(dfs, ignore_index=True).fillna("NaN")
#             merged_table_name = f"somatic_result_{newjobID}"

#             # **4️⃣ 確保 PostgreSQL 表已經準備好**
#             if not check_table_exists(conn, merged_table_name):
#                 create_table_from_df(df_merged, conn, merged_table_name)
#                 load_df_to_postgres(df_merged, conn, merged_table_name)
#             else:
#                 print(f"⚠️ 資料表 {merged_table_name} 已存在且有資料，跳過...")
#         else:
#             print("⚠️ 沒有找到可合併的 CSV 檔案")
#         #===================================================COSMIC.csv=======================
#         # ========== 3. 載入 COSMIC.csv 至 {newjobID}_COSMIC 表 ==========
#         # cosmic_name = "COSMIC"
#         # cosmic_csv_file = get_csv_path(newjobID, cosmic_name)
#         # cosmic_table_name = f"{newjobID}_COSMIC"

#         # if os.path.exists(cosmic_csv_file):
#         #     if not check_table_exists(conn, cosmic_table_name):
#         #         try:
#         #             df_cosmic = pd.read_csv(cosmic_csv_file, encoding='utf-8-sig', skip_blank_lines=True)
#         #             if df_cosmic.empty or len(df_cosmic.columns) == 0:
#         #                 print(f"⚠️ COSMIC.csv 為空或無欄位，跳過：{cosmic_csv_file}")
#         #             else:
#         #                 create_table_from_df(df_cosmic, conn, cosmic_table_name)
#         #                 load_df_to_postgres(df_cosmic, conn, cosmic_table_name)
#         #                 print(f"✅ 成功載入資料表：{cosmic_table_name}")
#         #         except Exception as e:
#         #             print(f"❌ 讀取 {cosmic_csv_file} 發生錯誤：{e}")
#         #     else:
#         #         print(f"⚠️ 資料表 {cosmic_table_name} 已存在且有資料，跳過...")
#         # else:
#         #     print(f"⚠️ 找不到 COSMIC.csv：{cosmic_csv_file}")
#         classification_files = ["COSMIC.csv", "suspect.csv", "heredity.csv"]
#         dfs_classification = []

#         for fname in classification_files:
#             csv_file = get_csv_path(newjobID, fname.replace(".csv", ""))
#             if os.path.exists(csv_file):
#                 try:
#                     df = pd.read_csv(csv_file, encoding='utf-8-sig', skip_blank_lines=True)
#                     if df.empty or len(df.columns) == 0:
#                         print(f"⚠️ {fname} 為空或無欄位，跳過：{csv_file}")
#                     else:
#                         dfs_classification.append(df)
#                         print(f"✅ 成功讀取 {fname}：{len(df)} 筆")
#                 except Exception as e:
#                     print(f" 讀取 {fname} 發生錯誤：{e}")
#             else:
#                 print(f" 找不到 {fname}：{csv_file}")

#         # 如果至少有一張表讀成功才處理
#         if dfs_classification:
#             df_classification = pd.concat(dfs_classification, ignore_index=True).fillna("NaN")
#             classification_table_name = f"{newjobID}_classification"

#             if not check_table_exists(conn, classification_table_name):
#                 create_table_from_df(df_classification, conn, classification_table_name)
#                 load_df_to_postgres(df_classification, conn, classification_table_name)
#                 print(f"✅ 成功載入資料表：{classification_table_name}")
#             else:
#                 print(f"⚠️ 資料表 {classification_table_name} 已存在且有資料，跳過...")
#         else:
#             print("⚠️ 沒有找到任何 classification CSV 檔案，跳過載入")
#         #=============================================Somatic_result資料表load進postgresql==============
#         #=============================================Somatic_result資料表load進postgresql==============
#                 # ========== 4. 載入 somatic_result.csv 至 {newjobID}_somaticResult 表 ========== #
#         somatic_result_file = get_csv_path(newjobID, "somatic_result_delete_list_final_result")
#         somatic_result_table = f"{newjobID}_somaticResult"

#         if os.path.exists(somatic_result_file):
#             if not check_table_exists(conn, somatic_result_table):
#                 try:
#                     df_somatic_result = pd.read_csv(somatic_result_file, encoding='utf-8-sig', skip_blank_lines=True)
#                     if df_somatic_result.empty or len(df_somatic_result.columns) == 0:
#                         print(f"⚠️ somatic_result.csv 為空或無欄位，跳過：{somatic_result_file}")
#                     else:
#                         create_table_from_df(df_somatic_result, conn, somatic_result_table)
#                         load_df_to_postgres(df_somatic_result, conn, somatic_result_table)
#                         print(f"✅ 成功載入資料表：{somatic_result_table}")
#                 except Exception as e:
#                     print(f"❌ 讀取 {somatic_result_file} 發生錯誤：{e}")
#             else:
#                 print(f"⚠️ 資料表 {somatic_result_table} 已存在且有資料，跳過...")
#         else:
#             print(f"⚠️ 找不到 somatic_result.csv：{somatic_result_file}")

#     except Exception as e:
#         print(f"❌ PostgreSQL 連線失敗: {e}")
    
#     finally:
#         if 'conn' in locals():
#             conn.close()
#             print("🔌 已關閉 PostgreSQL 連線")



# ---------------------------------------舊版pipeline--------------------------------------------------------------------
# import pandas as pd
# def generate_cosmic_preprocessor(row):
#     gene = row['Gene.refGene']  # 抓取基因
#     variant = row['variant'] if 'variant' in row else None  # 確保有 variant 欄位
#     if pd.isna(variant) or variant == "":  # 如果 variant 是空值
#         return f"{gene}_unspecified"
#     else:  # 如果 variant 有值
#         return f"{gene}_{variant}"
    
# # --------------------------------------------------------把COSMIC的phenotype變成一個set 把藥物組合全部抓出來-----------------------------------

# import pandas as pd

# # 載入資料
# file_path = r"C:\Users\user\Desktop\林醫師VCF團隊\2024-08-29資料\20241209task\Actionability_AllData_v12_GRCh37___split_version.tsv"  # 替換成您的資料檔案路徑
# data = pd.read_csv(file_path, sep="\t")  # 若使用 Tab 分隔

# print(data.columns)
# data.columns = data.columns.str.strip()  # 去除多餘空白
# print(data.columns)  # 確認是否有隱藏問題
# # 定義搜尋的 phenotype
# phenotype = "lung"

# # 篩選 DISEASE 欄位包含 phenotype 的資料
# filtered_data_cosmic = data[data['DISEASE'].str.contains(phenotype, na=False)]

# # 提取 MUTATION_REMARK_split 欄位，並將其轉為 set
# mutation_remark_set = set(filtered_data_cosmic['MUTATION_REMARK_split'].dropna())

# # 顯示結果
# print("篩選出的資料：")
# print(filtered_data_cosmic)
# print("\nMUTATION_REMARK_split set：")
# print(mutation_remark_set)
# # -------------------------------------------------篩出病人的pathogenc set -----------------------------------------
# annotatation =r"C:\Users\user\Desktop\林醫師VCF團隊\2024-08-29資料\20241209task\22W00198_S33_gpu_HF_final_merge_variant_lastest_version1.csv"
# data = pd.read_csv(annotatation,encoding='ISO-8859-1')

# # 篩選出 CLNSIG 欄位包含 "Pathogenic" 的資料
# filtered_data = data[data['CLNSIG'].str.contains("Pathogenic", case=False, na=False)]


# pathogenic_set = set(filtered_data['CLNSIG'].dropna())


# print("篩選出的資料：")
# print(filtered_data)
# print("\nCLNSIG Pathogenic set：")
# print(pathogenic_set)
# print("----------------------------------------------------------")
# filtered_data['cosmic_preprocessor'] = filtered_data.apply(generate_cosmic_preprocessor, axis=1)

# # 查看處理結果
# print(filtered_data[['Gene.refGene', 'variant', 'cosmic_preprocessor']])

# # --------------------------------------------開始比對phenotype跟pathogenic set去找藥物-----------------------------------
# def parse_combination(combination):
#     return set(combination.split(":"))
# # 初始化匹配結果
# matched_items = set()  # 成功拼湊的項目
# unmatched_items = set()  # 無法拼湊的項目
# drug_combinations = []  # 用於存儲成功匹配的 DRUG_COMBINATION

# # 遍歷 Phenotype set
# for phenotype in mutation_remark_set:
#     # 1. 將組合拆解為基因變異的集合
#     components = parse_combination(phenotype)
    
#     # 2. 確認 components 是否為 filtered_data['cosmic_preprocessor'] 的子集
#     if components.issubset(set(filtered_data['cosmic_preprocessor'])):
#         matched_items.add(phenotype)  # 加入匹配集
        
#         # 查找組合對應的 DRUG_COMBINATION
#         if 'MUTATION_REMARK_split' in data.columns:
#             # 過濾資料
#             cosmic_row = data[data['MUTATION_REMARK_split'] == phenotype]
#         else:
#             print(f"欄位 MUTATION_REMARK_split 不存在，請檢查數據！")
#             continue  # 如果欄位不存在，跳過該 phenotype

#         # 如果找到匹配數據
#         if not cosmic_row.empty:
#             # 提取 DRUG_COMBINATION 值並存入 drug_combinations 列表
#             drug_combinations.append({
#                 "Phenotype": phenotype,
#                 "DRUG_COMBINATION": cosmic_row['DRUG_COMBINATION'].values[0]  # 提取 DRUG_COMBINATION
#             })
#         else:
#             print(f"未找到匹配數據：Phenotype = {phenotype}")
#     else:
#         # 如果 components 不在 filtered_data 中，記錄為未匹配
#         unmatched_items.add(phenotype)
# # 成功拼湊的項目
# print("成功拼湊的項目：")
# print(matched_items)

# # 無法拼湊的項目
# print("\n無法拼湊的項目：")
# print(unmatched_items)

# # 對應的 DRUG_COMBINATION
# print("\n對應的 DRUG_COMBINATION：")

# # 如果 drug_combinations 非空，打印對應的結果，並存成 CSV 檔案
# if drug_combinations:
#     for result in drug_combinations:
#         print(f"Phenotype: {result['Phenotype']}, DRUG_COMBINATION: {result['DRUG_COMBINATION']}")

#     # 創建 DataFrame 並存檔
#     drug_combination_df = pd.DataFrame(drug_combinations)
    
#     # 確認存檔目錄和檔案名
#     output_file = r"C:\Users\user\Desktop\林醫師VCF團隊\2024-08-29資料\20241209task\drug_combinations_results.csv"
#     drug_combination_df.to_csv(output_file, index=False, encoding='utf-8-sig')  # 使用 UTF-8-SIG 避免中文亂碼
    
#     print(f"\n成功將對應的 DRUG_COMBINATION 儲存至：{output_file}")
#     print(drug_combination_df)
# else:
#     # 如果 drug_combinations 為空，打印提示
#     print("沒有成功匹配的 DRUG_COMBINATION。")

# print("篩選出的資料：")
# print(filtered_data_cosmic)
# --------------------------------------------解析ensambl id 變成variant--------------------------------------------------




# input_file = r"C:\Users\user\Desktop\林醫師VCF團隊\2024-08-29資料\20241209task\22W00198_S33_gpu_HF_vep_annovar_merge.csv"
# output_file = r"C:\Users\user\Desktop\林醫師VCF團隊\2024-08-29資料\20241209task\22W00198_S33_gpu_HF_final_merge_variant_lastest_version1.csv"  # 請更改為你想保存的路徑

# # 載入資料，加入 low_memory=False 解決 DtypeWarning 問題
# df = pd.read_csv(input_file, encoding='ISO-8859-1', low_memory=False)


# three_to_one = {
#     "Ala": "A", "Cys": "C", "Asp": "D", "Glu": "E", "Phe": "F", "Gly": "G", 
#     "His": "H", "Ile": "I", "Lys": "K", "Leu": "L", "Met": "M", "Asn": "N", 
#     "Pro": "P", "Gln": "Q", "Arg": "R", "Ser": "S", "Thr": "T", "Val": "V", 
#     "Trp": "W", "Tyr": "Y", "Ter": "*"
# }


# df[['variant_start', 'variant_end']] = df['enasmbl_HGVSp'].str.extract(r'p\.([A-Za-z]{3}\d+)([A-Za-z]{3})?')


# def convert_to_single_letter(row):
#     if pd.notnull(row['variant_start']):
#         # 前半部分 (e.g., Trp251)
#         amino_acid = row['variant_start'][:3]
#         position = row['variant_start'][3:]
#         single_letter_start = three_to_one.get(amino_acid, amino_acid)
#         result = f"{single_letter_start}{position}"
        
#         # 後半部分 (e.g., Arg)，如果存在且對應到單字母表
#         if pd.notnull(row['variant_end']) and row['variant_end'] in three_to_one:
#             single_letter_end = three_to_one[row['variant_end']]
#             result += single_letter_end
        
#         return result
#     return None


# df['variant'] = df.apply(convert_to_single_letter, axis=1)


# df.drop(columns=['variant_start', 'variant_end'], inplace=True)

# print(df[['enasmbl_HGVSp', 'variant']])

# df.to_csv(output_file, index=False)

# print(f"處理完成，已保存至 {output_file}")


# --------------------------------------------------------------------------------------------------------------



# import pandas as pd

# # 假設 Phenotype set 和 Pathogenic set 已經存在
# phenotype_set = {"BCL2_unspecified:MYC_unspecified", "BCL6_unspecified:MYC_unspecified", "BCL2_unspecified"}
# pathogenic_set = {"BCL2_unspecified", "MYC_unspecified"}

# # 將 Phenotype set 分解為基因-變異組合的標準格式
# def parse_combination(combination):
#     return set(combination.split(":"))

# # 檢查是否能用 Pathogenic set 重組出 Phenotype set 的項目
# matched_items = set()  # 存放能重組成功的項目
# unmatched_items = set()  # 存放無法重組的項目

# for phenotype in phenotype_set:
#     components = parse_combination(phenotype)  # 將組合拆解為基因變異的集合
#     if components.issubset(pathogenic_set):  # 檢查是否能用 Pathogenic set 拼湊出該組合
#         matched_items.add(phenotype)
#     else:
#         unmatched_items.add(phenotype)

# # 顯示結果
# print("成功拼湊的項目：")
# print(matched_items)

# print("\n無法拼湊的項目：")
# print(unmatched_items)
