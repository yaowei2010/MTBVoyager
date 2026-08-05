import pandas as pd
import base64
import os
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import csv
import re
from django.http import FileResponse, Http404
import psycopg2
import pandas as pd
import os

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
    cosmic_file_path = '/VEP/20241126Mondodatabase/COSMIC_database.tsv'
    cosmic_data = pd.read_csv(cosmic_file_path, sep="\t")
    folder_path = f'/miRTI/media/patient/{newJobID}'
    csv_file_path = os.path.join(folder_path, 'drug_combinations_result.csv')
   # csv_file_path = os.path.join(folder_path, 'drug_combinations_cosmic.csv')
    if os.path.exists(csv_file_path):
        print("exist!")
        
        with open(csv_file_path, mode='r', encoding='utf-8-sig') as csv_file:
            reader = csv.DictReader(csv_file)
            data = []

            for row in reader:
                new_row = {}
                # 填入各個欄位的資料
                new_row['Location'] = row['Location']
                new_row['Gene'] = row['Gene']
                new_row['RS ID'] = row['RS ID']
                new_row['MAF'] = eval(row['MAF'])
                new_row['Genotype / VAF'] = eval(row['MAF'])
                #new_row['Evidence'] = eval(row['Evidence'])
                new_row['Domain'] = row['Domain']
                new_row['Pathogenicity'] = str(row['Pathogenicity']).strip()

                #new_row['Splicing effect'] = eval(row['Splicing effect'])
                #new_row['OMIM_number'] = eval(row['OMIM_number'])
                new_row['DRUG_COMBINATION'] = row['DRUG_COMBINATION']
                new_row['Phenotype'] = row['Phenotype']
                data.append(new_row)

        return JsonResponse(data, safe=False)

    
    cosmic_data.columns = cosmic_data.columns.str.strip()
    phenotype_search_term = "lung"
    filtered_data_cosmic = cosmic_data[cosmic_data['DISEASE'].str.contains(phenotype_search_term, na=False)]
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
            # 如果沒有 drug_combinations，返回空的回應
            print("not found")
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
    """
    Check if elements in phenotype set can be assembled using elements in pathogenic set.

    Args:
        phenotype_set (set): The set of phenotype elements.
        pathogenic_set (set): The set of pathogenic elements.

    Returns:
        dict: A dictionary with phenotype elements as keys and boolean values indicating match.
    """
    results = {}
    standardized_pathogenic_set = {item.strip().upper() for item in pathogenic_set}
    for phenotype in phenotype_set:
        # 標準化單個 phenotype
        components = re.split(r'\\s+', phenotype.strip().upper())
        
        # 比對標準化後的 components 是否都在 pathogenic_set 中
        match = all(component in standardized_pathogenic_set for component in components)
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
    filtered_data = data[data['disease'].str.contains(disease_name, case=False, na=False)]

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
            (data['disease'].str.contains(disease_name, case=False, na=False))
        ]
        
        if not matching_rows.empty:
            therapies[phenotype] = matching_rows['therapies'].iloc[0]
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
        vcf_files = [file for file in os.listdir(folder_path) if file.endswith(".vcf")]
        csv_file_path = os.path.join(folder_path, 'mutiSNP_analysis_civic.csv')
        if os.path.exists(csv_file_path):
            with open(csv_file_path, mode='r', encoding='utf-8-sig') as csv_file:
                reader = csv.DictReader(csv_file)
                data = []

                for row in reader:
                    new_row = {}
                    # 填充各個欄位
                    new_row['Phenotype'] = row['Phenotype']
                    new_row['Therapies'] = row['Therapies']
                    new_row['civic_variant_name'] = row['civic_variant_name']
                    new_row['Location'] = row['Location']
                    new_row['Detailed_Location'] = row['Detailed_Location']
                    new_row['Gene'] = row['Gene']
                    new_row['RS ID'] = row['RS ID']
                    new_row['MAF'] = eval(row['MAF'])  # 將字串轉為字典
                    new_row['Domain'] = row['Domain']
                    new_row['Pathogenicity'] = row['Pathogenicity'].strip()
                    new_row['Prediction'] = eval(row['Prediction'])  # 將字串轉為字典

                    # 將整理後的資料加入結果清單
                    data.append(new_row)

            # 返回 JSON 結果
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

        input_file = '/VEP/drug_database/drug/CIVIC/civic_expanded.csv'
        data = pd.read_csv(input_file, encoding='latin1')  # Specify encoding if UTF-8 fails
        
        # Define the disease name to query
        disease_name = "Lung Non-small Cell Carcinoma"

        # Query and extract unique civic_new values
        phenotype_set = set(data[data['disease'] == disease_name]['civic_new'].dropna().unique())
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
def postgresql(request):
    if request.method == 'POST':

        # Load the CSV file
        data = json.loads(request.body.decode('utf-8'))
        newJobID = data.get('newjobid', '')
        #newJobID='tjsBHrCIwM'
        folder_path = f"/miRTI/media/patient/{newJobID}"
        vcf_files = [file for file in os.listdir(folder_path) if file.endswith(".vcf")]

        if vcf_files:
            print(f"找到 VCF 檔案: {vcf_files}")

            for vcf_file in vcf_files:
                uploadFile_url = os.path.join(folder_path, vcf_file)  # 完整檔案路徑

                file_name = os.path.basename(uploadFile_url)  # 例如 24C00131_main.vcf
                basename = os.path.splitext(file_name)[0]  # 例如 24C00131_main


        else:
            print("該資料夾中沒有 .vcf 檔案")
        load_csv_files_to_postgres_new(basename,newJobID)
        return JsonResponse({"status": "success", "message": "資料已成功載入 PostgreSQL"})




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

        filtered_variant=test_variants[filter_gnomad & filter_1000G & filter_VAF & filter_DP]
        print(filtered_variant[['Chr', 'Start', 'Ref', 'Alt']])
        print(filtered_variant.shape)  

        filtered_variant['variant_type']=filtered_variant.apply(lambda x: variant_type(x),axis=1)
        filtered_variant['variant_type'].value_counts()

        aa=filtered_variant[['Chr','Start','Ref','Alt']]
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


import psycopg2
import pandas as pd
import os

def load_csv_files_to_postgres_new(base_name, newjobID):
    """
    批次載入 CSV 檔案到 PostgreSQL：
    - `vep_annovar_merge_{newjobID}` 獨立載入
    - `drug_combinations_cosmic`, `mutiSNP_analysis_civic`, `somatic_result` 合併為 `somatic_result_{newjobID}`
    """

    # ======== PostgreSQL 連線資訊 ======== #
    DB_NAME = "somatic"
    DB_USER = "uuuwei0504"
    DB_PASSWORD = "REDACTED_SET_VIA_ENV"
    DB_HOST = "172.17.0.1"  # Docker 內部 IP
    DB_PORT = "5432"

    # ======== 定義要處理的檔案 ======== #
    VEP_FILE_TYPE = f"{base_name}_vep_annovar_merge"  # 這張表獨立載入
    MERGE_FILE_TYPES = [
        "drug_combinations_cosmic",
        "mutiSNP_analysis_civic",
        "somatic_result"
    ]

    # CSV 檔案路徑
    def get_csv_path(newjobID, file_type):
        return f"/miRTI/media/patient/{newjobID}/{file_type}.csv"

    # 產生表名
    def generate_table_name(file_type, newjobID):
        return f"{file_type}_{newjobID}"

    # 檢查表是否存在且有資料
    def check_table_exists(conn, table_name):
        query = f"SELECT COUNT(*) FROM information_schema.tables WHERE table_name = '{table_name}';"
        with conn.cursor() as cur:
            cur.execute(query)
            exists = cur.fetchone()[0] > 0
            if exists:
                cur.execute(f"SELECT COUNT(*) FROM \"{table_name}\";")
                count = cur.fetchone()[0]
                return count > 0  # 如果有資料則回傳 True
        return False

    # 創建 PostgreSQL 表
    def create_table_from_df(df, conn, table_name):
        """根據 DataFrame 建立 PostgreSQL 表"""
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

    # 將 DataFrame 匯入 PostgreSQL
    def load_df_to_postgres(df, conn, table_name):
        """將 DataFrame 匯入 PostgreSQL"""
        try:
            with conn.cursor() as cur:
                column_names = ", ".join([f'"{col}"' for col in df.columns])
                copy_sql = f"COPY \"{table_name}\" ({column_names}) FROM STDIN WITH CSV HEADER DELIMITER ',' NULL 'NaN'"

                temp_csv = f"/tmp/{table_name}.csv"
                df.to_csv(temp_csv, index=False)

                with open(temp_csv, 'r', encoding='utf-8') as f:
                    cur.copy_expert(copy_sql, f)

                os.remove(temp_csv)
                conn.commit()
                print(f"✅ 成功匯入: {table_name}")

        except Exception as e:
            conn.rollback()
            print(f"❌ 匯入失敗: {table_name}, 錯誤: {e}")

    # 連接 PostgreSQL
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        print("✅ 成功連接 PostgreSQL")

        # ========== 1. 獨立載入 vep_annovar_merge ========== #
        vep_csv_file = get_csv_path(newjobID, VEP_FILE_TYPE)
        vep_table_name = f"vep_annovar_merge_{newjobID}"

        if os.path.exists(vep_csv_file):
            if not check_table_exists(conn, vep_table_name):
                df_vep = pd.read_csv(vep_csv_file)
                create_table_from_df(df_vep, conn, vep_table_name)
                load_df_to_postgres(df_vep, conn, vep_table_name)
            else:
                print(f"⚠️ 資料表 {vep_table_name} 已存在且有資料，跳過...")
        else:
            print(f"⚠️ 找不到 CSV: {vep_csv_file}，跳過...")

        # ========== 2. 合併 3 張表為 somatic_result_{newjobID} ========== #
        dfs = []
        all_columns = set()

        # **1️⃣ 找出所有欄位**
        for file_type in MERGE_FILE_TYPES:
            csv_file = get_csv_path(newjobID, file_type)
            if os.path.exists(csv_file):
                df = pd.read_csv(csv_file)
                all_columns.update(df.columns)  # 記錄所有可能的欄位
                dfs.append(df)
            else:
                print(f"⚠️ 找不到 CSV: {csv_file}，跳過...")

        if dfs:
            # **2️⃣ 重新對齊所有 CSV 欄位**
            dfs = [df.reindex(columns=all_columns) for df in dfs]

            # **3️⃣ 合併 DataFrame**
            df_merged = pd.concat(dfs, ignore_index=True).fillna("NaN")
            merged_table_name = f"somatic_result_{newjobID}"

            # **4️⃣ 確保 PostgreSQL 表已經準備好**
            if not check_table_exists(conn, merged_table_name):
                create_table_from_df(df_merged, conn, merged_table_name)
                load_df_to_postgres(df_merged, conn, merged_table_name)
            else:
                print(f"⚠️ 資料表 {merged_table_name} 已存在且有資料，跳過...")
        else:
            print("⚠️ 沒有找到可合併的 CSV 檔案")

    except Exception as e:
        print(f"❌ PostgreSQL 連線失敗: {e}")

    finally:
        if 'conn' in locals():
            conn.close()
            print("🔌 已關閉 PostgreSQL 連線")



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
