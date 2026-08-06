import os
import pickle
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'uploadfunction.settings')  # 替换 'myproject.settings' 为您的实际设置模块路径
django.setup()
import pandas as pd
from hw1.models import existJobs
from django.core.files.storage import FileSystemStorage 
from django.core.files.storage import FileSystemStorage
from django.shortcuts import render
from django.http import HttpResponse
from django.core.files.storage import FileSystemStorage
from hw1.preprocessForAvinput_v1 import preprocessor
from hw1.WES_layering_pipeline2_5_2 import WES_layering
import os
import random
import string
import json
import pickle
import re
from django.http import JsonResponse
from django.shortcuts import render
import os
import random
import psycopg2
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

import shutil

global_newJobID=None
def react_send_page4():
    start=time.time()
    
    newJobID ="twkGvKMDTx"
    print(newJobID)
    try:
        job = existJobs.jobs.get(jobID=newJobID)
    except existJobs.jobs.DoesNotExist:
        return JsonResponse({'error': 'Job not found'}, status=404)    
    sampleID = job.subject_id
    uploadFile_url =f"/miRTI/media/patient/{newJobID}/24C00131_main.vcf"
    resultFile_url = job.resultFile_url
    print(sampleID)
    print(uploadFile_url)
    print(resultFile_url)


def load_parameters1(pickle_path):
    
    if not os.path.exists(pickle_path):
        raise FileNotFoundError(f"Pickle file not found: {pickle_path}")
    
  
    with open(pickle_path, 'rb') as file:
        parameters = pickle.load(file)
    
    return parameters

def modify_table1(parameters, df_names):
    for df_name in df_names:
        parameters[df_name].columns = parameters[df_name].columns.str.replace('.', '_', regex=False)

        parameters[df_name] = parameters[df_name].rename(columns={'1000G_ALL': 'AF_1000G'})
        parameters[df_name] = parameters[df_name].apply(summarize_known_clinical_evidence1, axis=1)

    return parameters

def summarize_known_clinical_evidence1(x):
    clinvar_alleleID = x['CLNALLELEID']
    clinvar_review_stat = x['CLNREVSTAT']
    clinvar_SIG = x['CLNSIG']
    tmp_lovd = x['LOVD_all_clinical']

    review_star_dict = {'no_assertion_provided': '0★',
                        'no_assertion_criteria_provided': '0★',
                        'no_assertion_for_the_individual_variant': '0★',
                        'criteria_provided,_conflicting_interpretations': '1★',
                        'criteria_provided,_single_submitter': '1★',
                        'criteria_provided,_multiple_submitters,_no_conflicts': '2★',
                        'reviewed_by_expert_panel': '3★',
                        'practice_guideline': '4★'}

    if (clinvar_alleleID != '.') & (clinvar_SIG != '.'):
        summary_string = clinvar_SIG.replace("_", " ") + '(' + review_star_dict[clinvar_review_stat] + ')'
    else:
        summary_string = '.'

    if tmp_lovd != '.':
        tmp_lovd = tmp_lovd.split(sep="ID=")
        LOVD_SIG = tmp_lovd[0]
        LOVD_ID = tmp_lovd[1]
    else:
        LOVD_SIG = '.'
        LOVD_ID = '.'

    x['clinvar_summary'] = summary_string
    x['LOVD_ID'] = LOVD_ID
    x['LOVD_SIG'] = LOVD_SIG

    return x

def rearrange_location1(variant_table):
    canonical_table = pd.read_csv('hw1/DB/Canonical_gene_table.csv')
    Chr = str(variant_table['Chr'])
    Start = str(variant_table['Start'])
    Ref = variant_table['Ref']
    Alt = variant_table['Alt']

    AAchange = variant_table['AAChange.refGene']
    GeneDetail = variant_table['GeneDetail.refGene']
    gene_name = variant_table['Gene.refGene']
    canonical = canonical_table[canonical_table['Gene'] == gene_name]['Transcript'].values

    if AAchange != '.':
        if 'NM' in AAchange:
            if len(canonical) != 0:
                canonical = canonical[0]
                matching = [s for s in AAchange.split(',') if canonical in s]
                if len(matching) != 0:
                    presentString = ':'.join(matching[0].split(':')[1:])
                # No matching transcript
                else:
                    canonical = AAchange.split(',')[0].split(':')[1]
                    presentString = ':'.join(AAchange.split(',')[0].split(':')[1:])
                    presentString += '\n(*Noncanonical transcript)'
            else:
                canonical = AAchange.split(',')[0].split(':')[1]
                presentString = ':'.join(AAchange.split(',')[0].split(':')[1:])
                presentString += '\n(*Noncanonical transcript)'
        else:
            presentString = AAchange

    elif GeneDetail != '.':
        if 'NM' in GeneDetail:
            if len(canonical) != 0:
                canonical = canonical[0]
                matching = [s for s in GeneDetail.split(';') if canonical in s]

                if len(matching) != 0:
                    presentString = matching[0]
                else:
                    canonical = GeneDetail.split(';')[0].split(':')[1]
                    presentString = GeneDetail.split(';')[0]
                    presentString += '\n(*Noncanonical transcript)'

            else:
                canonical = GeneDetail.split(';')[0].split(':')[1]
                presentString = GeneDetail.split(';')[0]
                presentString += '\n(*Noncanonical transcript)'
        else:
            presentString = GeneDetail
    else:
        canonical = 'None'
        presentString = variant_table['Func.refGene']

    location = Chr + ':' + Start + Ref + '>' + Alt + '\n' + presentString
    variant_table['Location'] = location
    variant_table['Canonical'] = canonical
    return variant_table


import os
import pickle
import pandas as pd
import os
import pickle
import pandas as pd
def savePickle_somatic(jobID, new_df, table_name):
    # 獲取 sampleID
    first_record = existJobs.jobs.filter(jobID=jobID).first()
    if not first_record:
        raise ValueError(f"No job found for jobID: {jobID}")

    sampleID = first_record.subject_id
    resultFile_path = f"media/patient/{jobID}/result_table/"
    
    # **確保目錄存在**
    os.makedirs(resultFile_path, exist_ok=True)
    
    pickle_file_path = os.path.join(resultFile_path, f"{sampleID}.pickle")
    print(f"🔹 儲存表格: {table_name}")
    print(f"📂 Pickle 路徑: {pickle_file_path}")

    # **如果 pickle 檔案存在，則讀取內容，否則建立新字典**
    existing_data = {}
    if os.path.exists(pickle_file_path):
        with open(pickle_file_path, 'rb') as rf:
            try:
                existing_data = pickle.load(rf)
                print("✅ 讀取現有 Pickle 檔案")
            except Exception as e:
                print(f"❌ 讀取 Pickle 檔案失敗: {e}")
                existing_data = {}

    # **確保 new_df 是 DataFrame**
    if not isinstance(new_df, pd.DataFrame):
        raise ValueError("New data is not a DataFrame.")

    # **轉換 DataFrame 內的 NaN 為 '.'**
    new_df = new_df.fillna('.')

    # **合併新資料**
    if table_name in existing_data:
        existing_df = existing_data[table_name]

        # **確保合併時不補 NaN 欄位**
        common_columns = list(set(existing_df.columns) & set(new_df.columns))
        existing_df = existing_df[common_columns]
        new_df = new_df[common_columns]

        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        combined_df = combined_df.drop_duplicates(subset='Location', keep='first')  # 依據 'Location' 欄位去重
        combined_df = combined_df.fillna('.')  # 再次確保 NaN 轉換為 '.'
        existing_data[table_name] = combined_df
    else:
        existing_data[table_name] = new_df

    # **存入 pickle**
    with open(pickle_file_path, 'wb') as wf:
        pickle.dump(existing_data, wf)
    
    print(f"✅ {table_name} 已成功儲存至 {pickle_file_path}")

def savePickle(jobID, new_df, table_name):
    # 獲取 sampleID
    sampleID = existJobs.jobs.all().filter(jobID=jobID)[0].subject_id
    resultFile_path = f"media/patient/{jobID}/result_table/"
    
    # **確保目錄存在**
    os.makedirs(resultFile_path, exist_ok=True)
    
    pickle_file_path = os.path.join(resultFile_path, f"{sampleID}.pickle")
    print(f"this is table name------------{table_name}")
    print(f"Pickle file path: {pickle_file_path}")

    # **如果 pickle 檔案存在，則讀取內容，否則建立新字典**
    if os.path.exists(pickle_file_path):
        with open(pickle_file_path, 'rb') as rf:
            existing_data = pickle.load(rf)
        print("Existing pickle data loaded.")
    else:
        print("Pickle not found. Creating a new one.")
        existing_data = {}

    # **檢查 new_df 是否為 DataFrame**
    if not isinstance(new_df, pd.DataFrame):
        raise ValueError("New data is not a DataFrame.")

    # **合併新資料**
    if table_name in existing_data:
        existing_df = existing_data[table_name]
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        combined_df = combined_df.drop_duplicates(subset='Location', keep='first')  # 依據 'Location' 欄位去重
        existing_data[table_name] = combined_df
    else:
        existing_data[table_name] = new_df

    # **存入 pickle**
    with open(pickle_file_path, 'wb') as wf:
        pickle.dump(existing_data, wf)
    
    print(f"DataFrame saved successfully to {pickle_file_path}")



@csrf_exempt
def get_newjobid(request):
    if request.method == 'POST':
        data = json.loads(request.body.decode('utf-8'))
        newJobID = data.get('newjobid', '')
        
        globals.global_newJobID = newJobID
        print(globals.global_newJobID)
        print(newJobID)
        print("success")

        first_record = existJobs.jobs.filter(jobID=newJobID).first()

        if first_record:
            annotated_file = first_record.resultFile_url
            input_file = first_record.uploadFile_url
            sampleID = first_record.subject_id

            print("************************")
            print(annotated_file)
            print(input_file)
            print(sampleID)

            return JsonResponse({
                'annotated_file': annotated_file,
                'input_file': input_file,
                'sampleID': sampleID
            })
        else:
            return JsonResponse({'error': 'No record found'}, status=404)
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=400)
    
#------------------------------------POSTGRESQL紀錄刪除 連接DELETE_JOB-------------

def delete_tables_with_newjobid(newJobID):
    DB_NAME = "somatic"
    DB_USER = "uuuwei0504"
    DB_PASSWORD = "REDACTED_SET_VIA_ENV"
    DB_HOST = "172.17.0.1"
    DB_PORT = "5432"
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cur = conn.cursor()

        # 找出所有包含 newJobID 的表名
        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema='public'
              AND table_name LIKE %s;
        """, (f"%{newJobID}%",))

        tables = cur.fetchall()

        for (table,) in tables:
            cur.execute(f'DROP TABLE IF EXISTS "{table}";')
            print(f"已刪除資料表: {table}")

        conn.commit()
        cur.close()
        conn.close()
        print("✅ 已刪除所有包含 newJobID 的資料表")

    except Exception as e:
        print(f"❌ 刪除資料表時發生錯誤: {e}")

#------------------------------------POSTGRESQL紀錄刪除 連接DELETE_JOB-------------
import psycopg2

def delete_tables_with_newjobid(newJobID):
    DB_NAME = "somatic"
    DB_USER = "uuuwei0504"
    DB_PASSWORD = "REDACTED_SET_VIA_ENV"
    DB_HOST = "172.17.0.1"
    DB_PORT = "5432"

    # 明確列出你會建立的表
    explicit_tables = [
        f'vep_annovar_merge_{newJobID}',
        f'somatic_result_{newJobID}',
        f'{newJobID}_COSMIC',
        f'{newJobID}_somaticResult',
    ]

    try:
        conn = psycopg2.connect(
            dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD,
            host=DB_HOST, port=DB_PORT
        )
        conn.autocommit = False
        cur = conn.cursor()

        # 先刪明確表
        for t in explicit_tables:
            cur.execute(f'DROP TABLE IF EXISTS "{t}" CASCADE;')

        # 保底：再找任何包含 newJobID 的表（大小寫不敏感）
        cur.execute("""
            SELECT table_schema, table_name
            FROM information_schema.tables
            WHERE table_type='BASE TABLE'
              AND table_schema='public'
              AND LOWER(table_name) LIKE LOWER(%s);
        """, (f"%{newJobID}%",))
        rows = cur.fetchall()
        for schema, tname in rows:
            cur.execute(f'DROP TABLE IF EXISTS "{tname}" CASCADE;')

        conn.commit()
        print(f"✅ 已清理與 {newJobID} 相關的 PostgreSQL 資料表")
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
        print(f"❌ 刪除 PostgreSQL 表失敗：{e}")
        raise
    finally:
        if 'conn' in locals():
            conn.close()
def safe_rmtree(target_path, must_under="/miRTI/media/patient"):
    if not target_path:
        print("⚠️ 空路徑，不刪。")
        return
    real_target = os.path.realpath(target_path)
    real_base = os.path.realpath(must_under)
    if not real_target.startswith(real_base + os.sep):
        print(f"⚠️ 路徑不在白名單根目錄下：{real_target}")
        return
    if os.path.exists(real_target):
        shutil.rmtree(real_target)
        print(f"🗑️ 已刪除資料夾：{real_target}")
    else:
        print(f"ℹ️ 找不到資料夾：{real_target}")
@csrf_exempt
def delete_job(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=405)

    try:
        data = json.loads(request.body.decode('utf-8'))
        newJobID = data.get('newjobid', '').strip()

        if not newJobID:
            return JsonResponse({'error': 'newjobid is required'}, status=400)

        job_record = existJobs.jobs.filter(jobID=newJobID).first()
        if not job_record:
            return JsonResponse({'error': 'No record found'}, status=404)

        # 可能是本機路徑或 URL；若是 URL，請自行轉成本機路徑
        uploadFile_url = job_record.uploadFile_url or ""
        path = os.path.dirname(uploadFile_url) if uploadFile_url else f"/miRTI/media/patient/{newJobID}"

        print("************************")
        print("jobID:", newJobID)
        print("Upload File URL:", uploadFile_url)
        print("Delete Dir Path:", path)

        # 1) 先刪 PostgreSQL 表（避免檔案刪掉後查不到 log）
        try:
            delete_tables_with_newjobid(newJobID)
        except Exception as e:
            # 不中斷整體流程，但回傳時告知
            pg_err = str(e)
        else:
            pg_err = None

        # 2) 再刪資料夾（安全白名單檢查）
        safe_rmtree(path, must_under="/miRTI/media/patient")

        # 3) 刪 Django ORM 紀錄
        job_record.delete()

        resp = {'message': 'Job deleted successfully'}
        if pg_err:
            resp['postgres_warning'] = pg_err
            return JsonResponse(resp, status=207)  # Multi-Status：部分成功
        return JsonResponse(resp)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        print(f"An error occurred: {e}")
        return JsonResponse({'error': str(e)}, status=500)
#---------------------------------
@csrf_exempt
def get_summary_info(request):
    if request.method == 'POST':
        data = json.loads(request.body.decode('utf-8'))

        newJobID = data.get('newJobID', '')
        table_name=data.get('table_name','')
        dataframe=data.get('dataframe','')
        print("----------------------table name---------")
        
        print(table_name)
        print("----------------------table name---------")
        globals.global_newJobID = newJobID
        print(globals.global_newJobID)
        print(newJobID)
        print("success")
        print("----------------------dataframe---------")
        print(dataframe)
        print("----------------------dataframe end ----")

        first_record = existJobs.jobs.filter(jobID=newJobID).first()

        if first_record:
            annotated_file = first_record.resultFile_url
            input_file = first_record.uploadFile_url
            sampleID = first_record.subject_id

            print("************************")
            print(annotated_file)
            print(input_file)
            print(sampleID)
        else:
    # 處理沒有找到記錄的情況
            raise ValueError(f"No records found for jobID: {newJobID}")


        print(table_name)
        # result_table=f'/miRTI/media/patient/{newJobID}/result_table'
        # data=pd.read_csv(f'{result_table}/{table_name}')
        # print(data)


        # ----------------------------------json to dataframe-----------------------------------

        df = pd.DataFrame(dataframe)
        print(df)
        for table in df['table_name'].unique():
            table_df = df[df['table_name'] == table]
            savePickle(newJobID, table_df, table)



@csrf_exempt
def get_summary_info_somatic(request):
    if request.method == 'POST':
        data = json.loads(request.body.decode('utf-8'))

        newJobID = data.get('newJobID', '')
        table_name=data.get('table_name','')
        dataframe=data.get('dataframe','')
        print("----------------------table name---------")
        
        print(table_name)
        print("----------------------table name---------")
        globals.global_newJobID = newJobID
        print(globals.global_newJobID)
        print(newJobID)
        print("success")
        print("----------------------dataframe---------")
        print(dataframe)
        print("----------------------dataframe end ----")

        first_record = existJobs.jobs.filter(jobID=newJobID).first()

        if first_record:
            annotated_file = first_record.resultFile_url
            input_file = first_record.uploadFile_url
            sampleID = first_record.subject_id

            print("************************")
            print(annotated_file)
            print(input_file)
            print(sampleID)
        else:
    # 處理沒有找到記錄的情況
            raise ValueError(f"No records found for jobID: {newJobID}")


        print(table_name)
        # result_table=f'/miRTI/media/patient/{newJobID}/result_table'
        # data=pd.read_csv(f'{result_table}/{table_name}')
        # print(data)


        # ----------------------------------json to dataframe-----------------------------------

        df = pd.DataFrame(dataframe)
        print(df)
        for table in df['table_name'].unique():
            table_df = df[df['table_name'] == table]
            savePickle_somatic(newJobID, table_df, table)

@csrf_exempt
def summary_page(request):
    if request.method == 'POST':
        # 確定 pickle 檔案的路徑
        data = json.loads(request.body.decode('utf-8'))

        newJobID = data.get('newJobID', '')
        first_record = existJobs.jobs.filter(jobID=newJobID).first()
        print(f"{newJobID}")


        if first_record:
            annotated_file = first_record.resultFile_url
            input_file = first_record.uploadFile_url
            sampleID = first_record.subject_id
        
        resultFile_path = f"/miRTI/media/patient/{newJobID}/result_table/{sampleID}"
        pickle_file_path = f"{resultFile_path}.pickle"
        json_file_path = f"/miRTI/media/patient/{newJobID}/summary.json"
        # 檢查 pickle 檔案是否存在
        if not os.path.exists(pickle_file_path):
            print(f"Pickle file {pickle_file_path} not found.")
            return JsonResponse({'error': 'Pickle file not found'}, status=404)
        # 讀取 pickle 檔案中的資料
        with open(pickle_file_path, 'rb') as rf:
            data = pickle.load(rf)
            print(data)
        try:
            with open(json_file_path, 'r') as jf:
                json_data = json.load(jf)
                print(json_data)
        except FileNotFoundError:
            print(f"JSON file {json_file_path} not found, proceeding with empty data.")
            json_data = {}  # 如果文件不存在，使用空字典作为默认值
        # 檢查 data 類型
        if isinstance(data, dict):
            # data 是字典，不需要轉換
            data2 = data
        else:
            # 如果 data 是 DataFrame，則需要轉換
            data2 = data.to_dict(orient='records')


        print('--------------------for test---------------------------------')
        print('--------------------for test---------------------------------')
        

        # 初始化空列表來儲存所有資料
        combined_data = []

        # 定義要處理的表格名稱
        table_names = [
            'Other Variants',
            'Known Pathogenic ACMG',
            'Known Pathogenic Other',
            'Known Pathogenic Pheno',
            'Predicted Suspect ACMG',
            'Predicted Suspect Other',
            'Predicted Suspect Pheno',
            'ACMG Variants',
            'Drug Responses'
        ]
        # table_names = [
        #     'single_snp_actionable',
        #     'single_snp_hereidty',
        #     'single_snp_germline_prediction',
        #     'single_snp_cosmic',
        #     'single_snp_prediction',
        # ]        
        # 逐個處理表格
        for table_name in table_names:
            table_data = data.get(table_name)
            if table_data is not None:
                if isinstance(table_data, pd.DataFrame):
                    combined_data.extend(table_data.to_dict(orient='records'))
                else:
                    combined_data.extend(table_data)
        response_data = {
            'combinedData': combined_data,
            'jsonData': json_data
        }
        print(response_data)

        return JsonResponse(response_data, safe=False)

@csrf_exempt
def summary_page_somatic(request):
    if request.method == 'POST':
        # 確定 pickle 檔案的路徑
        data = json.loads(request.body.decode('utf-8'))

        newJobID = data.get('newJobID', '')
        first_record = existJobs.jobs.filter(jobID=newJobID).first()
        print(f"{newJobID}")
        print("-------------------------------------------------------summary_page------------------------------")
        print("-------------------------------------------------------summary_page------------------------------")
        print("-------------------------------------------------------summary_page------------------------------")
        print("-------------------------------------------------------summary_page------------------------------")
        print("-------------------------------------------------------summary_page------------------------------")



        if first_record:
            annotated_file = first_record.resultFile_url
            input_file = first_record.uploadFile_url
            sampleID = first_record.subject_id
        
        resultFile_path = f"/miRTI/media/patient/{newJobID}/result_table/{sampleID}"
        pickle_file_path = f"{resultFile_path}.pickle"
        json_file_path = f"/miRTI/media/patient/{newJobID}/summary.json"
        # 檢查 pickle 檔案是否存在
        if not os.path.exists(pickle_file_path):
            print(f"Pickle file {pickle_file_path} not found.")
            return JsonResponse({'error': 'Pickle file not found'}, status=404)
        # 讀取 pickle 檔案中的資料
        with open(pickle_file_path, 'rb') as rf:
            data = pickle.load(rf)
            print(data)
        try:
            with open(json_file_path, 'r') as jf:
                json_data = json.load(jf)
                print(json_data)
        except FileNotFoundError:
            print(f"JSON file {json_file_path} not found, proceeding with empty data.")
            json_data = {}  # 如果文件不存在，使用空字典作为默认值
        # 檢查 data 類型
        if isinstance(data, dict):
            # data 是字典，不需要轉換
            data2 = data
        else:
            # 如果 data 是 DataFrame，則需要轉換
            data2 = data.to_dict(orient='records')


        print('--------------------for test---------------------------------')
        print('--------------------for test---------------------------------')
        print('--------------------for test---------------------------------')
        print('--------------------for test---------------------------------')

        # 初始化空列表來儲存所有資料
        combined_data = []

        # 定義要處理的表格名稱
        table_names = [
            'single_snp_actionable',
            'single_snp_hereidty',
            'single_snp_germline_prediction',
            'single_snp_cosmic',
            'single_snp_prediction',
        ]

        # 逐個處理表格
        for table_name in table_names:
            table_data = data.get(table_name)
            if table_data is not None:
                if isinstance(table_data, pd.DataFrame):
                    combined_data.extend(table_data.to_dict(orient='records'))
                else:
                    combined_data.extend(table_data)
        response_data = {
            'combinedData': combined_data,
            'jsonData': json_data
        }
        print(response_data)

        return JsonResponse(response_data, safe=False)

# ------------------------
@csrf_exempt
def delete_variant_germline(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
            newJobID = data.get('newJobID', '')
            location_to_delete = data.get('Location', '')

            # 確保提供了必要的參數
            if not newJobID or not location_to_delete:
                return JsonResponse({'error': 'Missing required parameters'}, status=400)

            # 獲取 sampleID
            first_record = existJobs.jobs.filter(jobID=newJobID).first()
            if not first_record:
                return JsonResponse({'error': 'Job not found'}, status=404)

            sampleID = first_record.subject_id
            pickle_file_path = f"/miRTI/media/patient/{newJobID}/result_table/{sampleID}.pickle"

            # 檢查 pickle 是否存在
            if not os.path.exists(pickle_file_path):
                return JsonResponse({'error': 'Pickle file not found'}, status=404)

            # 讀取 pickle 檔案
            with open(pickle_file_path, 'rb') as rf:
                existing_data = pickle.load(rf)
            # 遍歷所有表格，尋找包含該 Location 的表
            tables_to_update = []
            for table_name, df in existing_data.items():
                if isinstance(df, pd.DataFrame) and location_to_delete in df['Location'].values:
                    updated_df = df[df['Location'] != location_to_delete]  # 移除該筆資料
                    existing_data[table_name] = updated_df
                    tables_to_update.append(table_name)

            # 如果沒找到該 Location，返回錯誤
            if not tables_to_update:
                return JsonResponse({'error': 'Location not found in any table'}, status=404)

            # 更新 pickle 檔案
            with open(pickle_file_path, 'wb') as wf:
                pickle.dump(existing_data, wf)

            # 回傳更新後的資料
            return JsonResponse({
                'message': 'Variant deleted successfully',
                'updated_tables': tables_to_update
            }, safe=False)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
# ----------------------------------------------delete前端需要傳的格式
# {
    # "newJobID": "12345",
    # "Location": "chr1:1000A>T"
# }
# ---------------------------------------------------------------------

# ------------------------
@csrf_exempt
def HPO_search(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
            hpo_id = data.get('HPO', '')
            df = pd.read_csv("/miRTI/media/reference/Germline_analysis/phenotype_to_genes_20250721.txt", sep="\t")

            result = df[df['hpo_id'] == hpo_id]

            if result.empty:
                return JsonResponse({"error": f"No data found for HPO ID: {hpo_id}"}, status=404)

            hpo_name = result.iloc[0]['hpo_name']
            gene_list = result['gene_symbol'].unique().tolist()

            response = {
                "hpo_id": hpo_id,
                "hpo_name": hpo_name,
                "gene_list": gene_list
            }
            return JsonResponse(response)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)




import csv

import csv
from django.http import JsonResponse
from django.core.files.storage import FileSystemStorage





@csrf_exempt
def known_pathogenic_to_json(request):
    if request.method == 'POST':
        finished_jobs = existJobs.jobs.all().filter(status="finished")
        newJobID = globals.global_newJobID
        folder_path = f'/miRTI/media/patient/{newJobID}/result_table'
        csv_file_path = os.path.join(folder_path, 'known_pheno_variant.csv')

        # 檢查 CSV 文件是否已經存在
        if os.path.exists(csv_file_path):
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
                    new_row['Genotype / VAF'] = eval(row['Genotype / VAF'])
                    new_row['Evidence'] = eval(row['Evidence'])
                    new_row['Domain'] = row['Domain']
                    new_row['Pathogenicity'] = eval(row['Pathogenicity'])
                    new_row['Splicing effect'] = eval(row['Splicing effect'])
                    new_row['OMIM_number'] = eval(row['OMIM_number'])
                    new_row['Amelie Max score'] = row['Amelie Max score']
                    new_row['Amelie Mean score'] = row['Amelie Mean score']
                    data.append(new_row)

            return JsonResponse(data, safe=False)

        print(newJobID)

        first_record = existJobs.jobs.filter(jobID=newJobID).first()
        select_job = first_record.jobID
        gender= first_record.gender
        sampleID = finished_jobs.filter(jobID=select_job)[0].subject_id
        fs = FileSystemStorage()
        parm_pickle = os.path.join(fs.location, 'patient', select_job, f'{sampleID}.pickle')
        print("****")
     
        parameters = load_parameters1(parm_pickle)
        # print(parameters['known_pheno_variant'])
        parameters['known_pheno_variant'] = parameters['known_pheno_variant'].apply(rearrange_location1, axis=1)

        parameters = modify_table1(parameters, ['known_pheno_variant'])
        print("**************************************")
        print(parameters['known_pheno_variant'])

        folder_path = f'/miRTI/media/patient/{newJobID}/result_table'
        os.makedirs(folder_path, exist_ok=True)  # 新增這行來確保目錄存在
        
        parameters['known_pheno_variant'].to_csv(f'/miRTI/media/patient/{newJobID}/result_table/known_pheno_variant.csv', index=False)
        data = []
        with open(f'/miRTI/media/patient/{newJobID}/result_table/known_pheno_variant.csv', mode='r', encoding='utf-8-sig') as original_file:
            reader = csv.DictReader(original_file)

            for row in reader:
                new_row = {}

                # 1. Location
                new_row['Location'] = f"{row['Chr']}:{row['Start']}_{row['End']}{row['Ref']}>{row['Alt']}"

                # 2. Gene
                new_row['Gene'] = row['Gene_refGene']

                # 3. RS ID
                if row['avsnp150'] == '.':
                    new_row['RS ID'] = row['avsnp150']
                else:
                    new_row['RS ID'] = row['avsnp150']

                # 4. MAF
                new_row['MAF'] = {
                    'gnomAD': row['AF'],
                    '1000G': row['AF_1000G'],
                    'TW Biobank': row['TaiwanBioBank']
                }

                # 5. Genotype / VAF
                new_row['Genotype / VAF'] = {
                    'GT': row['GT'],
                    'VAF': float(row['VAF']),
                    'AD': row['AD'],
                    'Otherinfo10': row['Otherinfo10']
                }

                # 6. Evidence
                new_row['Evidence'] = {
                    'Clinvar': '.' if row['clinvar_summary'] == '.' else row['clinvar_summary'],
                    'LOVD': '.' if row['LOVD_all_clinical'] == '.' else row['LOVD_SIG']
                }

                # 7. Domain
                new_row['Domain'] = row['Interpro_domain']

                # 8. Pathogenicity
                new_row['Pathogenicity'] = {
                    'Summary': f"({row['deleterious_agreed']}/{row['deleterious_tools']})",
                    'Polyphen2_HVAR': row['Polyphen2_HVAR_pred'],
                    'SIFT': row['SIFT_pred'],
                    'VEST3': row['VEST3_score'],
                    'MutationTaster': row['MutationTaster_pred'],
                    'MetaSVM': row['MetaSVM_pred'],
                    'MetaLR': row['MetaLR_pred'],
                    'CADD': row['CADD_phred'],
                    'DANN': row['DANN_score']
                }

                # 9. Splicing effect
                new_row['Splicing effect'] = {
                    'Summary': f"({row['splicing_effect_agreed']}/{row['splicing_effect_tools']})",
                    'dbscsnv ADA score': row['dbscSNV_ADA_SCORE'],
                    'dbscsnv RF score': row['dbscSNV_RF_SCORE'],
                    'SPIDEX zscore': row['dpsi_zscore']
                }

                # 10. OMIM
                if row['Phenotype'] == -1 :
                    result = 'X'
                else:
                    omim_chromosome = row['Phenotype'].split('(')[-1].split(')')[0]
                    print(omim_chromosome)
                    genotype = new_row['Genotype / VAF']['GT']
                    print(genotype)
                    result = 'X'

                    if omim_chromosome in ['AD', 'AR']:
                        if omim_chromosome == 'AD':
                            if genotype in ['hom', 'het']:
                                result = 'O'
                        elif omim_chromosome == 'AR':
                            if genotype == 'hom':
                                result = 'O'
                    elif omim_chromosome == 'XLR':
                        if gender == 'Male' and genotype in ['het', 'hom']:
                            result = 'O'
                        elif gender == 'Female' and genotype == 'het':
                            result = 'O'
                    elif omim_chromosome == 'XLD':
                        if gender == 'Male' and genotype in ['het', 'hom']:
                            result = 'O'
                        elif gender == 'Female' and genotype == 'hom':
                            result = 'O'


                new_row['OMIM_number'] = {
                    'Phenotype': row['Phenotype'],
                    'OMIM_number': row['OMIM_number'] if row['OMIM_number'] != 'None' else '',
                    '符合條件': result
                }

                # 11. Amelie Max score
                new_row['Amelie Max score'] = row['Max_Score']

                # 12. Amelie Mean score
                new_row['Amelie Mean score'] = row['Mean_Score']

                data.append(new_row)
                print(data)
        folder_path = f'/miRTI/media/patient/{newJobID}/result_table'

        print("hello")        
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            print(f"資料夾 '{folder_path}' 建立成功")
        else:
            print(f"資料夾 '{folder_path}' 已存在，跳過建立")
        with open(f'{folder_path}/known_pheno_variant.csv', mode='w', encoding='utf-8-sig', newline='') as csv_file:
            fieldnames = ['Location', 'Gene', 'RS ID', 'MAF', 'Genotype / VAF', 'Evidence', 
                        'Domain', 'Pathogenicity', 'Splicing effect', 'OMIM_number', 
                        'Amelie Max score', 'Amelie Mean score']
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)

            writer.writeheader()
            for row in data:
                writer.writerow(row)

        return JsonResponse(data, safe=False)
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)
    

@csrf_exempt
def known_pathogenic_to_json_trio(request):
    if request.method == 'POST':
        finished_jobs = existJobs.jobs.all().filter(status="finished")
        newJobID = globals.global_newJobID
        folder_path = f'/miRTI/media/patient/{newJobID}/result_table'
        csv_file_path = os.path.join(folder_path, 'known_pheno_variant.csv')

        # 檢查 CSV 文件是否已經存在
        if os.path.exists(csv_file_path):
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
                    new_row['Genotype / VAF'] = eval(row['Genotype / VAF'])
                    new_row['Evidence'] = eval(row['Evidence'])
                    new_row['Domain'] = row['Domain']
                    new_row['Pathogenicity'] = eval(row['Pathogenicity'])
                    new_row['Splicing effect'] = eval(row['Splicing effect'])
                    new_row['OMIM_number'] = eval(row['OMIM_number'])
                    new_row['Amelie Max score'] = row['Amelie Max score']
                    new_row['Amelie Mean score'] = row['Amelie Mean score']
                    new_row['INH'] = row['INH']
                    data.append(new_row)

            return JsonResponse(data, safe=False)

        print(newJobID)

        first_record = existJobs.jobs.filter(jobID=newJobID).first()
        select_job = first_record.jobID
        gender= first_record.gender
        sampleID = finished_jobs.filter(jobID=select_job)[0].subject_id
        fs = FileSystemStorage()
        parm_pickle = os.path.join(fs.location, 'patient', select_job, f'{sampleID}.pickle')
        print("****")
     
        parameters = load_parameters1(parm_pickle)
        # print(parameters['known_pheno_variant'])
        parameters['known_pheno_variant'] = parameters['known_pheno_variant'].apply(rearrange_location1, axis=1)

        parameters = modify_table1(parameters, ['known_pheno_variant'])
        print("**************************************")
        print(parameters['known_pheno_variant'])

        folder_path = f'/miRTI/media/patient/{newJobID}/result_table'
        os.makedirs(folder_path, exist_ok=True)  # 新增這行來確保目錄存在
        
        parameters['known_pheno_variant'].to_csv(f'/miRTI/media/patient/{newJobID}/result_table/known_pheno_variant.csv', index=False)
        data = []
        with open(f'/miRTI/media/patient/{newJobID}/result_table/known_pheno_variant.csv', mode='r', encoding='utf-8-sig') as original_file:
            reader = csv.DictReader(original_file)

            for row in reader:
                new_row = {}

                # 1. Location
                new_row['Location'] = f"{row['Chr']}:{row['Start']}_{row['End']}{row['Ref']}>{row['Alt']}"

                # 2. Gene
                new_row['Gene'] = row['Gene_refGene']

                # 3. RS ID
                if row['avsnp150'] == '.':
                    new_row['RS ID'] = row['avsnp150']
                else:
                    new_row['RS ID'] = row['avsnp150']

                # 4. MAF
                new_row['MAF'] = {
                    'gnomAD': row['AF'],
                    '1000G': row['AF_1000G'],
                    'TW Biobank': row['TaiwanBioBank']
                }

                # 5. Genotype / VAF
                new_row['Genotype / VAF'] = {
                    'GT': row['GT'],
                    'VAF': float(row['VAF']),
                    'AD': row['AD'],
                    'Otherinfo10': row['Otherinfo10']
                }

                # 6. Evidence
                new_row['Evidence'] = {
                    'Clinvar': '.' if row['clinvar_summary'] == '.' else row['clinvar_summary'],
                    'LOVD': '.' if row['LOVD_all_clinical'] == '.' else row['LOVD_SIG']
                }

                # 7. Domain
                new_row['Domain'] = row['Interpro_domain']

                # 8. Pathogenicity
                new_row['Pathogenicity'] = {
                    'Summary': f"({row['deleterious_agreed']}/{row['deleterious_tools']})",
                    'Polyphen2_HVAR': row['Polyphen2_HVAR_pred'],
                    'SIFT': row['SIFT_pred'],
                    'VEST3': row['VEST3_score'],
                    'MutationTaster': row['MutationTaster_pred'],
                    'MetaSVM': row['MetaSVM_pred'],
                    'MetaLR': row['MetaLR_pred'],
                    'CADD': row['CADD_phred'],
                    'DANN': row['DANN_score']
                }

                # 9. Splicing effect
                new_row['Splicing effect'] = {
                    'Summary': f"({row['splicing_effect_agreed']}/{row['splicing_effect_tools']})",
                    'dbscsnv ADA score': row['dbscSNV_ADA_SCORE'],
                    'dbscsnv RF score': row['dbscSNV_RF_SCORE'],
                    'SPIDEX zscore': row['dpsi_zscore']
                }

                # 10. OMIM
                if row['Phenotype'] == -1 :
                    result = 'X'
                else:
                    omim_chromosome = row['Phenotype'].split('(')[-1].split(')')[0]
                    print(omim_chromosome)
                    genotype = new_row['Genotype / VAF']['GT']
                    print(genotype)
                    result = 'X'

                    if omim_chromosome in ['AD', 'AR']:
                        if omim_chromosome == 'AD':
                            if genotype in ['hom', 'het']:
                                result = 'O'
                        elif omim_chromosome == 'AR':
                            if genotype == 'hom':
                                result = 'O'
                    elif omim_chromosome == 'XLR':
                        if gender == 'Male' and genotype in ['het', 'hom']:
                            result = 'O'
                        elif gender == 'Female' and genotype == 'het':
                            result = 'O'
                    elif omim_chromosome == 'XLD':
                        if gender == 'Male' and genotype in ['het', 'hom']:
                            result = 'O'
                        elif gender == 'Female' and genotype == 'hom':
                            result = 'O'


                new_row['OMIM_number'] = {
                    'Phenotype': row['Phenotype'],
                    'OMIM_number': row['OMIM_number'] if row['OMIM_number'] != 'None' else '',
                    '符合條件': result
                }

                # 11. Amelie Max score
                new_row['Amelie Max score'] = row['Max_Score']

                # 12. Amelie Mean score
                new_row['Amelie Mean score'] = row['Mean_Score']

                # 13. INH
                new_row['INH'] = row['INH']

                data.append(new_row)
                print(data)
        folder_path = f'/miRTI/media/patient/{newJobID}/result_table'

        print("hello")        
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            print(f"資料夾 '{folder_path}' 建立成功")
        else:
            print(f"資料夾 '{folder_path}' 已存在，跳過建立")
        with open(f'{folder_path}/known_pheno_variant.csv', mode='w', encoding='utf-8-sig', newline='') as csv_file:
            fieldnames = ['Location', 'Gene', 'RS ID', 'MAF', 'Genotype / VAF', 'Evidence', 
                        'Domain', 'Pathogenicity', 'Splicing effect', 'OMIM_number', 
                        'Amelie Max score', 'Amelie Mean score', 'INH']
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)

            writer.writeheader()
            for row in data:
                writer.writerow(row)

        return JsonResponse(data, safe=False)
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)
    

    
@csrf_exempt
def known_ACMG_variant(request):
    if request.method == 'POST':
        finished_jobs = existJobs.jobs.all().filter(status="finished")
        newJobID = globals.global_newJobID
        folder_path = f'/miRTI/media/patient/{newJobID}/result_table'
        csv_file_path = os.path.join(folder_path, 'known_ACMG_variant.csv')

        # 檢查 CSV 文件是否已經存在
        if os.path.exists(csv_file_path):
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
                    new_row['Genotype / VAF'] = eval(row['Genotype / VAF'])
                    new_row['Evidence'] = eval(row['Evidence'])
                    new_row['Domain'] = row['Domain']
                    new_row['Pathogenicity'] = eval(row['Pathogenicity'])
                    new_row['Splicing effect'] = eval(row['Splicing effect'])
                    new_row['OMIM_number'] = eval(row['OMIM_number'])
                    new_row['Amelie Max score'] = row['Amelie Max score']
                    new_row['Amelie Mean score'] = row['Amelie Mean score']
                    data.append(new_row)

            return JsonResponse(data, safe=False)

        print(newJobID)

        first_record = existJobs.jobs.filter(jobID=newJobID).first()
        select_job = first_record.jobID
        gender= first_record.gender
        sampleID = finished_jobs.filter(jobID=select_job)[0].subject_id
        fs = FileSystemStorage()
        parm_pickle = os.path.join(fs.location, 'patient', select_job, f'{sampleID}.pickle')
        print("****")
     
        parameters = load_parameters1(parm_pickle)
        # print(parameters['known_pheno_variant'])
        parameters['known_ACMG_variant'] = parameters['known_ACMG_variant'].apply(rearrange_location1, axis=1)

        parameters = modify_table1(parameters, ['known_ACMG_variant'])
        print("**************************************")
        print(parameters['known_ACMG_variant'])
        parameters['known_ACMG_variant'].to_csv(f'/miRTI/media/patient/{newJobID}/result_table/known_ACMG_variant.csv', index=False)
        data = []
        with open(f'/miRTI/media/patient/{newJobID}/result_table/known_ACMG_variant.csv', mode='r', encoding='utf-8-sig') as original_file:
            reader = csv.DictReader(original_file)

            for row in reader:
                new_row = {}

                # 1. Location
                new_row['Location'] = f"{row['Chr']}:{row['Start']}_{row['End']}{row['Ref']}>{row['Alt']}"

                # 2. Gene
                new_row['Gene'] = row['Gene_refGene']

                # 3. RS ID
                if row['avsnp150'] == '.':
                    new_row['RS ID'] = row['avsnp150']
                else:
                    new_row['RS ID'] = row['avsnp150']

                # 4. MAF
                new_row['MAF'] = {
                    'gnomAD': row['AF'],
                    '1000G': row['AF_1000G'],
                    'TW Biobank': row['TaiwanBioBank']
                }

                # 5. Genotype / VAF
                new_row['Genotype / VAF'] = {
                    'GT': row['GT'],
                    'VAF': float(row['VAF']),
                    'AD': row['AD'],
                    'Otherinfo10': row['Otherinfo10']
                }

                # 6. Evidence
                new_row['Evidence'] = {
                    'Clinvar': '.' if row['clinvar_summary'] == '.' else row['clinvar_summary'],
                    'LOVD': '.' if row['LOVD_all_clinical'] == '.' else row['LOVD_SIG']
                }

                # 7. Domain
                new_row['Domain'] = row['Interpro_domain']

                # 8. Pathogenicity
                new_row['Pathogenicity'] = {
                    'Summary': f"({row['deleterious_agreed']}/{row['deleterious_tools']})",
                    'Polyphen2_HVAR': row['Polyphen2_HVAR_pred'],
                    'SIFT': row['SIFT_pred'],
                    'VEST3': row['VEST3_score'],
                    'MutationTaster': row['MutationTaster_pred'],
                    'MetaSVM': row['MetaSVM_pred'],
                    'MetaLR': row['MetaLR_pred'],
                    'CADD': row['CADD_phred'],
                    'DANN': row['DANN_score']
                }

                # 9. Splicing effect
                new_row['Splicing effect'] = {
                    'Summary': f"({row['splicing_effect_agreed']}/{row['splicing_effect_tools']})",
                    'dbscsnv ADA score': row['dbscSNV_ADA_SCORE'],
                    'dbscsnv RF score': row['dbscSNV_RF_SCORE'],
                    'SPIDEX zscore': row['dpsi_zscore']
                }

                # 10. OMIM
                if row['Phenotype'] == -1 :
                    result = 'X'
                else:
                    omim_chromosome = row['Phenotype'].split('(')[-1].split(')')[0]
                    print(omim_chromosome)
                    genotype = new_row['Genotype / VAF']['GT']
                    print(genotype)
                    result = 'X'

                    if omim_chromosome in ['AD', 'AR']:
                        if omim_chromosome == 'AD':
                            if genotype in ['hom', 'het']:
                                result = 'O'
                        elif omim_chromosome == 'AR':
                            if genotype == 'hom':
                                result = 'O'
                    elif omim_chromosome == 'XLR':
                        if gender == 'Male' and genotype in ['het', 'hom']:
                            result = 'O'
                        elif gender == 'Female' and genotype == 'het':
                            result = 'O'
                    elif omim_chromosome == 'XLD':
                        if gender == 'Male' and genotype in ['het', 'hom']:
                            result = 'O'
                        elif gender == 'Female' and genotype == 'hom':
                            result = 'O'


                new_row['OMIM_number'] = {
                    'Phenotype': row['Phenotype'],
                    'OMIM_number': row['OMIM_number'] if row['OMIM_number'] != 'None' else '',
                    '符合條件': result
                }

                # 11. Amelie Max score
                new_row['Amelie Max score'] = row['Max_Score']

                # 12. Amelie Mean score
                new_row['Amelie Mean score'] = row['Mean_Score']

                data.append(new_row)
                print(data)
        folder_path = f'/miRTI/media/patient/{newJobID}/result_table'

        print("hello")        
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            print(f"資料夾 '{folder_path}' 建立成功")
        else:
            print(f"資料夾 '{folder_path}' 已存在，跳過建立")
        with open(f'{folder_path}/known_ACMG_variant.csv', mode='w', encoding='utf-8-sig', newline='') as csv_file:
            fieldnames = ['Location', 'Gene', 'RS ID', 'MAF', 'Genotype / VAF', 'Evidence', 
                        'Domain', 'Pathogenicity', 'Splicing effect', 'OMIM_number', 
                        'Amelie Max score', 'Amelie Mean score']
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)

            writer.writeheader()
            for row in data:
                writer.writerow(row)

        return JsonResponse(data, safe=False)
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)

@csrf_exempt
def known_other_variant(request):
    if request.method == 'POST':
        finished_jobs = existJobs.jobs.all().filter(status="finished")
        newJobID = globals.global_newJobID
        folder_path = f'/miRTI/media/patient/{newJobID}/result_table'
        csv_file_path = os.path.join(folder_path, 'known_other_variant.csv')

        # 檢查 CSV 文件是否已經存在
        if os.path.exists(csv_file_path):
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
                    new_row['Genotype / VAF'] = eval(row['Genotype / VAF'])
                    new_row['Evidence'] = eval(row['Evidence'])
                    new_row['Domain'] = row['Domain']
                    new_row['Pathogenicity'] = eval(row['Pathogenicity'])
                    new_row['Splicing effect'] = eval(row['Splicing effect'])
                    new_row['OMIM_number'] = eval(row['OMIM_number'])
                    new_row['Amelie Max score'] = row['Amelie Max score']
                    new_row['Amelie Mean score'] = row['Amelie Mean score']
                    data.append(new_row)

            return JsonResponse(data, safe=False)

        print(newJobID)

        first_record = existJobs.jobs.filter(jobID=newJobID).first()
        select_job = first_record.jobID
        gender= first_record.gender
        sampleID = finished_jobs.filter(jobID=select_job)[0].subject_id
        fs = FileSystemStorage()
        parm_pickle = os.path.join(fs.location, 'patient', select_job, f'{sampleID}.pickle')
        print("****")
     
        parameters = load_parameters1(parm_pickle)
        # print(parameters['known_pheno_variant'])
        parameters['known_other_variant'] = parameters['known_other_variant'].apply(rearrange_location1, axis=1)

        parameters = modify_table1(parameters, ['known_other_variant'])
        print("**************************************")
        print(parameters['known_other_variant'])
        parameters['known_other_variant'].to_csv(f'/miRTI/media/patient/{newJobID}/result_table/known_other_variant.csv', index=False)
        data = []
        with open(f'/miRTI/media/patient/{newJobID}/result_table/known_other_variant.csv', mode='r', encoding='utf-8-sig') as original_file:
            reader = csv.DictReader(original_file)

            for row in reader:
                new_row = {}

                # 1. Location
                new_row['Location'] = f"{row['Chr']}:{row['Start']}_{row['End']}{row['Ref']}>{row['Alt']}"

                # 2. Gene
                new_row['Gene'] = row['Gene_refGene']

                # 3. RS ID
                if row['avsnp150'] == '.':
                    new_row['RS ID'] = row['avsnp150']
                else:
                    new_row['RS ID'] = row['avsnp150']

                # 4. MAF
                new_row['MAF'] = {
                    'gnomAD': row['AF'],
                    '1000G': row['AF_1000G'],
                    'TW Biobank': row['TaiwanBioBank']
                }

                # 5. Genotype / VAF
                new_row['Genotype / VAF'] = {
                    'GT': row['GT'],
                    'VAF': float(row['VAF']),
                    'AD': row['AD'],
                    'Otherinfo10': row['Otherinfo10']
                }

                # 6. Evidence
                new_row['Evidence'] = {
                    'Clinvar': '.' if row['clinvar_summary'] == '.' else row['clinvar_summary'],
                    'LOVD': '.' if row['LOVD_all_clinical'] == '.' else row['LOVD_SIG']
                }

                # 7. Domain
                new_row['Domain'] = row['Interpro_domain']

                # 8. Pathogenicity
                new_row['Pathogenicity'] = {
                    'Summary': f"({row['deleterious_agreed']}/{row['deleterious_tools']})",
                    'Polyphen2_HVAR': row['Polyphen2_HVAR_pred'],
                    'SIFT': row['SIFT_pred'],
                    'VEST3': row['VEST3_score'],
                    'MutationTaster': row['MutationTaster_pred'],
                    'MetaSVM': row['MetaSVM_pred'],
                    'MetaLR': row['MetaLR_pred'],
                    'CADD': row['CADD_phred'],
                    'DANN': row['DANN_score']
                }

                # 9. Splicing effect
                new_row['Splicing effect'] = {
                    'Summary': f"({row['splicing_effect_agreed']}/{row['splicing_effect_tools']})",
                    'dbscsnv ADA score': row['dbscSNV_ADA_SCORE'],
                    'dbscsnv RF score': row['dbscSNV_RF_SCORE'],
                    'SPIDEX zscore': row['dpsi_zscore']
                }

                # 10. OMIM
                if row['Phenotype'] == -1 :
                    result = 'X'
                else:
                    omim_chromosome = row['Phenotype'].split('(')[-1].split(')')[0]
                    print(omim_chromosome)
                    genotype = new_row['Genotype / VAF']['GT']
                    print(genotype)
                    result = 'X'

                    if omim_chromosome in ['AD', 'AR']:
                        if omim_chromosome == 'AD':
                            if genotype in ['hom', 'het']:
                                result = 'O'
                        elif omim_chromosome == 'AR':
                            if genotype == 'hom':
                                result = 'O'
                    elif omim_chromosome == 'XLR':
                        if gender == 'Male' and genotype in ['het', 'hom']:
                            result = 'O'
                        elif gender == 'Female' and genotype == 'het':
                            result = 'O'
                    elif omim_chromosome == 'XLD':
                        if gender == 'Male' and genotype in ['het', 'hom']:
                            result = 'O'
                        elif gender == 'Female' and genotype == 'hom':
                            result = 'O'


                new_row['OMIM_number'] = {
                    'Phenotype': row['Phenotype'],
                    'OMIM_number': row['OMIM_number'] if row['OMIM_number'] != 'None' else '',
                    '符合條件': result
                }

                # 11. Amelie Max score
                new_row['Amelie Max score'] = row['Max_Score']

                # 12. Amelie Mean score
                new_row['Amelie Mean score'] = row['Mean_Score']

                data.append(new_row)
                print(data)
        folder_path = f'/miRTI/media/patient/{newJobID}/result_table'

        print("hello")        
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            print(f"資料夾 '{folder_path}' 建立成功")
        else:
            print(f"資料夾 '{folder_path}' 已存在，跳過建立")
        with open(f'{folder_path}/known_other_variant.csv', mode='w', encoding='utf-8-sig', newline='') as csv_file:
            fieldnames = ['Location', 'Gene', 'RS ID', 'MAF', 'Genotype / VAF', 'Evidence', 
                        'Domain', 'Pathogenicity', 'Splicing effect', 'OMIM_number', 
                        'Amelie Max score', 'Amelie Mean score']
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)

            writer.writeheader()
            for row in data:
                writer.writerow(row)

        return JsonResponse(data, safe=False)
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)
import csv

# def other_variant():
#         finished_jobs = existJobs.jobs.all().filter(status="finished")
#         global global_newJobID
#         newJobID = 'LyvnWreaTh'  # Replace with your actual job ID
#         first_record = finished_jobs.filter(jobID=newJobID).first()
#         gender=first_record

#         if first_record is None:
#             return JsonResponse({'error': 'No finished job found with the given job ID'}, status=404)

#         select_job = first_record.jobID

#         sampleID = finished_jobs.filter(jobID=select_job)[0].subject_id
#         fs = FileSystemStorage()
#         parm_pickle = os.path.join(fs.location, 'patient', select_job, f'{sampleID}.pickle')
#         print("****")

#         parameters = load_parameters1(parm_pickle)

#         parameters['other_variant'] = parameters['other_variant'].apply(rearrange_location1, axis=1)

#         parameters = modify_table1(parameters, ['other_variant'])
#         print("**************************************")
#         print(parameters['other_variant'])
#         parameters['other_variant'].to_csv('other_variant.csv', index=False)

#         data = []
#         with open('other_variant.csv', mode='r', encoding='utf-8-sig') as original_file:
#             reader = csv.DictReader(original_file)

#             for row in reader:
#                 new_row = {}

#                 # 1. Location
#                 new_row['Location'] = f"{row['Chr']}:{row['Start']}_{row['End']}{row['Ref']}>{row['Alt']}"

#                 # 2. Gene
#                 new_row['Gene'] = row['Gene_refGene']

#                 # 3. RS ID
#                 if row['avsnp150'] == '.':
#                     new_row['RS ID'] = row['avsnp150']
#                 else:
#                     new_row['RS ID'] = row['avsnp150']

#                 # 4. MAF
#                 new_row['MAF'] = {
#                     'gnomAD': row['AF'],
#                     '1000G': row['AF_1000G'],
#                     'TW Biobank': row['TaiwanBioBank']
#                 }

#                 # 5. Genotype / VAF
#                 new_row['Genotype / VAF'] = {
#                     'GT': row['GT'],
#                     'VAF': float(row['VAF']),
#                     'AD': row['AD'],
#                     'Otherinfo10': row['Otherinfo10']
#                 }

#                 # 6. Evidence
#                 new_row['Evidence'] = {
#                     'Clinvar': '.' if row['clinvar_summary'] == '.' else row['clinvar_summary'],
#                     'LOVD': '.' if row['LOVD_all_clinical'] == '.' else row['LOVD_SIG']
#                 }

#                 # 7. Domain
#                 new_row['Domain'] = row['Interpro_domain']

#                 # 8. Pathogenicity
#                 new_row['Pathogenicity'] = {
#                     'Summary': f"({row['deleterious_agreed']}/{row['deleterious_tools']})",
#                     'Polyphen2_HVAR': row['Polyphen2_HVAR_pred'],
#                     'SIFT': row['SIFT_pred'],
#                     'VEST3': row['VEST3_score'],
#                     'MutationTaster': row['MutationTaster_pred'],
#                     'MetaSVM': row['MetaSVM_pred'],
#                     'MetaLR': row['MetaLR_pred'],
#                     'CADD': row['CADD_phred'],
#                     'DANN': row['DANN_score']
#                 }

#                 # 9. Splicing effect
#                 new_row['Splicing effect'] = {
#                     'Summary': f"({row['splicing_effect_agreed']}/{row['splicing_effect_tools']})",
#                     'dbscsnv ADA score': row['dbscSNV_ADA_SCORE'],
#                     'dbscsnv RF score': row['dbscSNV_RF_SCORE'],
#                     'SPIDEX zscore': row['dpsi_zscore']
#                 }

#                 # 10. OMIM
#                 new_row['OMIM'] = {
#                     'Phenotype': row['Phenotype'],
#                     'OMIM_number': row['OMIM_number'] if row['OMIM_number'] != 'None' else ''
#                 }

#                 # 11. Amelie Max score
#                 new_row['Amelie Max score'] = row['Max_Score']

#                 # 12. Amelie Mean score
#                 new_row['Amelie Mean score'] = row['Mean_Score']

#                 data.append(new_row)


#         # Writing data to CSV file
#         with open('result_table/other_variant_result.csv', mode='w', encoding='utf-8-sig', newline='') as csv_file:
#             fieldnames = ['Location', 'Gene', 'RS ID', 'MAF', 'Genotype / VAF', 'Evidence', 
#                         'Domain', 'Pathogenicity', 'Splicing effect', 'OMIM', 
#                         'Amelie Max score', 'Amelie Mean score']
#             writer = csv.DictWriter(csv_file, fieldnames=fieldnames)

#             writer.writeheader()
#             for row in data:
#                 writer.writerow(row)

#         return JsonResponse(data, safe=False)
@csrf_exempt
def other_variant(request):
    if request.method == 'POST':
        finished_jobs = existJobs.jobs.all().filter(status="finished")
        newJobID = globals.global_newJobID

        folder_path = f'/miRTI/media/patient/{newJobID}/result_table'
        csv_file_path = os.path.join(folder_path, 'other_variant_result.csv')

        # 如果CSV檔案已經存在，直接讀取並返回
        if os.path.exists(csv_file_path):
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
                    new_row['Genotype / VAF'] = eval(row['Genotype / VAF'])
                    new_row['Evidence'] = eval(row['Evidence'])
                    new_row['Domain'] = row['Domain']
                    new_row['Pathogenicity'] = eval(row['Pathogenicity'])
                    new_row['Splicing effect'] = eval(row['Splicing effect'])
                    new_row['OMIM_number'] = eval(row['OMIM_number'])
                    new_row['Amelie Max score'] = row['Amelie Max score']
                    new_row['Amelie Mean score'] = row['Amelie Mean score']
                    data.append(new_row)

            return JsonResponse(data, safe=False)
        print(newJobID)
        first_record = finished_jobs.filter(jobID=newJobID).first()
        gender = first_record

        if first_record is None:
            return JsonResponse({'error': 'No finished job found with the given job ID'}, status=404)

        select_job = first_record.jobID
        sampleID = finished_jobs.filter(jobID=select_job)[0].subject_id
        fs = FileSystemStorage()
        parm_pickle = os.path.join(fs.location, 'patient', select_job, f'{sampleID}.pickle')

        parameters = load_parameters1(parm_pickle)
        parameters['other_variant'] = parameters['other_variant'].apply(rearrange_location1, axis=1)
        parameters = modify_table1(parameters, ['other_variant'])
        print(parameters['other_variant'])
        print("----------------------------this is other_variant")
        other_variant_path = f'/miRTI/media/patient/{newJobID}/result_table/other_variant.csv'
        parameters['other_variant'].to_csv(other_variant_path, index=False, encoding='utf-8-sig')
        print(f"[INFO] 成功儲存：{other_variant_path}")
        # Prepare data for writing to CSV
        data = []
        with open(f'/miRTI/media/patient/{newJobID}/result_table/other_variant.csv', mode='r', encoding='utf-8-sig') as original_file:
            reader = csv.DictReader(original_file)
            
            for row in reader:
                new_row = {}

                # 1. Location
                new_row['Location'] = f"{row['Chr']}:{row['Start']}_{row['End']}{row['Ref']}>{row['Alt']}"

                # 2. Gene
                new_row['Gene'] = row['Gene_refGene']

                # 3. RS ID
                new_row['RS ID'] = row['avsnp150']

                # 4. MAF
                new_row['MAF'] = {
                    'gnomAD': row['AF'],
                    '1000G': row['AF_1000G'],
                    'TW Biobank': row['TaiwanBioBank']
                }

                # 5. Genotype / VAF (with error handling)
                genotype_vaf = row.get('Genotype / VAF', {})
                new_row['Genotype / VAF'] = {
                        'GT': row['GT'],
                        'VAF': float(row['VAF']),
                        'AD': row['AD'],
                        'Otherinfo10': row['Otherinfo10']
                    }

                # 6. Evidence
                new_row['Evidence'] = {
                    'Clinvar': '.' if row['clinvar_summary'] == '.' else row['clinvar_summary'],
                    'LOVD': '.' if row['LOVD_all_clinical'] == '.' else row['LOVD_SIG']
                }

                # 7. Domain
                new_row['Domain'] = row['Interpro_domain']

                # 8. Pathogenicity
                new_row['Pathogenicity'] = {
                    'Summary': f"({row['deleterious_agreed']}/{row['deleterious_tools']})",
                    'Polyphen2_HVAR': row['Polyphen2_HVAR_pred'],
                    'SIFT': row['SIFT_pred'],
                    'VEST3': row['VEST3_score'],
                    'MutationTaster': row['MutationTaster_pred'],
                    'MetaSVM': row['MetaSVM_pred'],
                    'MetaLR': row['MetaLR_pred'],
                    'CADD': row['CADD_phred'],
                    'DANN': row['DANN_score']
                }

                # 9. Splicing effect
                new_row['Splicing effect'] = {
                    'Summary': f"({row['splicing_effect_agreed']}/{row['splicing_effect_tools']})",
                    'dbscsnv ADA score': row['dbscSNV_ADA_SCORE'],
                    'dbscsnv RF score': row['dbscSNV_RF_SCORE'],
                    'SPIDEX zscore': row['dpsi_zscore']
                }

                # 10. OMIM_number (renamed from OMIM)
                if row['Phenotype'] == -1 :
                    result = 'X'
                else:
                    omim_chromosome = row['Phenotype'].split('(')[-1].split(')')[0]
                    print(omim_chromosome)
                    genotype = new_row['Genotype / VAF']['GT']
                    print(genotype)
                    result = 'X'

                    if omim_chromosome in ['AD', 'AR']:
                        if omim_chromosome == 'AD':
                            if genotype in ['hom', 'het']:
                                result = 'O'
                        elif omim_chromosome == 'AR':
                            if genotype == 'hom':
                                result = 'O'
                    elif omim_chromosome == 'XLR':
                        if gender == 'Male' and genotype in ['het', 'hom']:
                            result = 'O'
                        elif gender == 'Female' and genotype == 'het':
                            result = 'O'
                    elif omim_chromosome == 'XLD':
                        if gender == 'Male' and genotype in ['het', 'hom']:
                            result = 'O'
                        elif gender == 'Female' and genotype == 'hom':
                            result = 'O'


                new_row['OMIM_number'] = {
                    'Phenotype': row['Phenotype'],
                    'OMIM_number': row['OMIM_number'] if row['OMIM_number'] != 'None' else '',
                    '符合條件': result
                }

                # 11. Amelie Max score
                new_row['Amelie Max score'] = row['Max_Score']

                # 12. Amelie Mean score
                new_row['Amelie Mean score'] = row['Mean_Score']

                data.append(new_row)
        folder_path = f'/miRTI/media/patient/{newJobID}/result_table'

        # 
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            print(f"資料夾 '{folder_path}' 建立成功")
        else:
            print(f"資料夾 '{folder_path}' 已存在，跳過建立")
        # Writing data to CSV file
        with open(f'{folder_path}/other_variant_result.csv', mode='w', encoding='utf-8-sig', newline='') as csv_file:
            fieldnames = ['Location', 'Gene', 'RS ID', 'MAF', 'Genotype / VAF', 'Evidence', 
                        'Domain', 'Pathogenicity', 'Splicing effect', 'OMIM_number', 
                        'Amelie Max score', 'Amelie Mean score']
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)

            writer.writeheader()
            for row in data:
                writer.writerow(row)

        return JsonResponse(data, safe=False)
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)


@csrf_exempt
def other_variant_trio(request):
    if request.method == 'POST':
        finished_jobs = existJobs.jobs.all().filter(status="finished")
        newJobID = globals.global_newJobID

        folder_path = f'/miRTI/media/patient/{newJobID}/result_table'
        csv_file_path = os.path.join(folder_path, 'other_variant_result.csv')

        # 如果CSV檔案已經存在，直接讀取並返回
        if os.path.exists(csv_file_path):
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
                    new_row['Genotype / VAF'] = eval(row['Genotype / VAF'])
                    new_row['Evidence'] = eval(row['Evidence'])
                    new_row['Domain'] = row['Domain']
                    new_row['Pathogenicity'] = eval(row['Pathogenicity'])
                    new_row['Splicing effect'] = eval(row['Splicing effect'])
                    new_row['OMIM_number'] = eval(row['OMIM_number'])
                    new_row['Amelie Max score'] = row['Amelie Max score']
                    new_row['Amelie Mean score'] = row['Amelie Mean score']
                    new_row['INH'] = row['INH']
                    data.append(new_row)

            return JsonResponse(data, safe=False)
        print(newJobID)
        first_record = finished_jobs.filter(jobID=newJobID).first()
        gender = first_record

        if first_record is None:
            return JsonResponse({'error': 'No finished job found with the given job ID'}, status=404)

        select_job = first_record.jobID
        sampleID = finished_jobs.filter(jobID=select_job)[0].subject_id
        fs = FileSystemStorage()
        parm_pickle = os.path.join(fs.location, 'patient', select_job, f'{sampleID}.pickle')

        parameters = load_parameters1(parm_pickle)
        parameters['other_variant'] = parameters['other_variant'].apply(rearrange_location1, axis=1)
        parameters = modify_table1(parameters, ['other_variant'])
        print(parameters['other_variant'])
        print("----------------------------this is other_variant")
        other_variant_path = f'/miRTI/media/patient/{newJobID}/result_table/other_variant.csv'
        parameters['other_variant'].to_csv(other_variant_path, index=False, encoding='utf-8-sig')
        print(f"[INFO] 成功儲存：{other_variant_path}")
        # Prepare data for writing to CSV
        data = []
        with open(f'/miRTI/media/patient/{newJobID}/result_table/other_variant.csv', mode='r', encoding='utf-8-sig') as original_file:
            reader = csv.DictReader(original_file)
            
            for row in reader:
                new_row = {}

                # 1. Location
                new_row['Location'] = f"{row['Chr']}:{row['Start']}_{row['End']}{row['Ref']}>{row['Alt']}"

                # 2. Gene
                new_row['Gene'] = row['Gene_refGene']

                # 3. RS ID
                new_row['RS ID'] = row['avsnp150']

                # 4. MAF
                new_row['MAF'] = {
                    'gnomAD': row['AF'],
                    '1000G': row['AF_1000G'],
                    'TW Biobank': row['TaiwanBioBank']
                }

                # 5. Genotype / VAF (with error handling)
                genotype_vaf = row.get('Genotype / VAF', {})
                new_row['Genotype / VAF'] = {
                        'GT': row['GT'],
                        'VAF': float(row['VAF']),
                        'AD': row['AD'],
                        'Otherinfo10': row['Otherinfo10']
                    }

                # 6. Evidence
                new_row['Evidence'] = {
                    'Clinvar': '.' if row['clinvar_summary'] == '.' else row['clinvar_summary'],
                    'LOVD': '.' if row['LOVD_all_clinical'] == '.' else row['LOVD_SIG']
                }

                # 7. Domain
                new_row['Domain'] = row['Interpro_domain']

                # 8. Pathogenicity
                new_row['Pathogenicity'] = {
                    'Summary': f"({row['deleterious_agreed']}/{row['deleterious_tools']})",
                    'Polyphen2_HVAR': row['Polyphen2_HVAR_pred'],
                    'SIFT': row['SIFT_pred'],
                    'VEST3': row['VEST3_score'],
                    'MutationTaster': row['MutationTaster_pred'],
                    'MetaSVM': row['MetaSVM_pred'],
                    'MetaLR': row['MetaLR_pred'],
                    'CADD': row['CADD_phred'],
                    'DANN': row['DANN_score']
                }

                # 9. Splicing effect
                new_row['Splicing effect'] = {
                    'Summary': f"({row['splicing_effect_agreed']}/{row['splicing_effect_tools']})",
                    'dbscsnv ADA score': row['dbscSNV_ADA_SCORE'],
                    'dbscsnv RF score': row['dbscSNV_RF_SCORE'],
                    'SPIDEX zscore': row['dpsi_zscore']
                }

                # 10. OMIM_number (renamed from OMIM)
                if row['Phenotype'] == -1 :
                    result = 'X'
                else:
                    omim_chromosome = row['Phenotype'].split('(')[-1].split(')')[0]
                    print(omim_chromosome)
                    genotype = new_row['Genotype / VAF']['GT']
                    print(genotype)
                    result = 'X'

                    if omim_chromosome in ['AD', 'AR']:
                        if omim_chromosome == 'AD':
                            if genotype in ['hom', 'het']:
                                result = 'O'
                        elif omim_chromosome == 'AR':
                            if genotype == 'hom':
                                result = 'O'
                    elif omim_chromosome == 'XLR':
                        if gender == 'Male' and genotype in ['het', 'hom']:
                            result = 'O'
                        elif gender == 'Female' and genotype == 'het':
                            result = 'O'
                    elif omim_chromosome == 'XLD':
                        if gender == 'Male' and genotype in ['het', 'hom']:
                            result = 'O'
                        elif gender == 'Female' and genotype == 'hom':
                            result = 'O'


                new_row['OMIM_number'] = {
                    'Phenotype': row['Phenotype'],
                    'OMIM_number': row['OMIM_number'] if row['OMIM_number'] != 'None' else '',
                    '符合條件': result
                }

                # 11. Amelie Max score
                new_row['Amelie Max score'] = row['Max_Score']

                # 12. Amelie Mean score
                new_row['Amelie Mean score'] = row['Mean_Score']

                # 13. INH
                new_row['INH'] = row['INH']

                data.append(new_row)
        folder_path = f'/miRTI/media/patient/{newJobID}/result_table'

        # 
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            print(f"資料夾 '{folder_path}' 建立成功")
        else:
            print(f"資料夾 '{folder_path}' 已存在，跳過建立")
        # Writing data to CSV file
        with open(f'{folder_path}/other_variant_result.csv', mode='w', encoding='utf-8-sig', newline='') as csv_file:
            fieldnames = ['Location', 'Gene', 'RS ID', 'MAF', 'Genotype / VAF', 'Evidence', 
                        'Domain', 'Pathogenicity', 'Splicing effect', 'OMIM_number', 
                        'Amelie Max score', 'Amelie Mean score', 'INH']
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)

            writer.writeheader()
            for row in data:
                writer.writerow(row)

        return JsonResponse(data, safe=False)
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)

@csrf_exempt
def predicted_suspect_variant(request):
    if request.method == 'POST':
        finished_jobs = existJobs.jobs.all().filter(status="finished")
        newJobID = globals.global_newJobID
        print(newJobID)
        output_csv_path = f'/miRTI/media/patient/{newJobID}/result_table/predicted_suspect_variant_result.csv'
        if os.path.exists(output_csv_path):
            with open(output_csv_path, mode='r', encoding='utf-8-sig') as csv_file:
                reader = csv.DictReader(csv_file)
                data = []

                for row in reader:
                    new_row = {}
                    # 填入各個欄位的資料
                    new_row['Location'] = row['Location']
                    new_row['Gene'] = row['Gene']
                    new_row['RS ID'] = row['RS ID']
                    new_row['MAF'] = eval(row['MAF'])
                    new_row['Genotype / VAF'] = eval(row['Genotype / VAF'])
                    new_row['Evidence'] = eval(row['Evidence'])
                    new_row['Domain'] = row['Domain']
                    new_row['Pathogenicity'] = eval(row['Pathogenicity'])
                    new_row['Splicing effect'] = eval(row['Splicing effect'])
                    new_row['OMIM_number'] = eval(row['OMIM_number'])
                    new_row['Amelie Max score'] = row['Amelie Max score']
                    new_row['Amelie Mean score'] = row['Amelie Mean score']
                    data.append(new_row)

            return JsonResponse(data, safe=False)


        first_record = finished_jobs.filter(jobID=newJobID).first()

        if first_record is None:
            return JsonResponse({'error': 'No finished job found with the given job ID'}, status=404)

        select_job = first_record.jobID
        gender=first_record.gender

        sampleID = finished_jobs.filter(jobID=select_job)[0].subject_id
        fs = FileSystemStorage()
        parm_pickle = os.path.join(fs.location, 'patient', select_job, f'{sampleID}.pickle')
        print("****")

        parameters = load_parameters1(parm_pickle)

        parameters['suspect_pheno_variant'] = parameters['suspect_pheno_variant'].apply(rearrange_location1, axis=1)

        parameters = modify_table1(parameters, ['suspect_pheno_variant'])
        print("**************************************")
        print(parameters['suspect_pheno_variant'])
        parameters['suspect_pheno_variant'].to_csv(f'/miRTI/media/patient/{newJobID}/result_table/predicted_suspect_variant.csv', index=False)

        # Process data
        data = []
        with open(f'/miRTI/media/patient/{newJobID}/result_table/predicted_suspect_variant.csv', mode='r', encoding='utf-8-sig') as original_file:
            reader = csv.DictReader(original_file)

            for row in reader:
                new_row = {}

                # 1. Location
                new_row['Location'] = f"{row['Chr']}:{row['Start']}_{row['End']}{row['Ref']}>{row['Alt']}"

                # 2. Gene
                new_row['Gene'] = row['Gene_refGene']

                # 3. RS ID
                new_row['RS ID'] = row['avsnp150']

                # 4. MAF
                new_row['MAF'] = {
                    'gnomAD': row['AF'],
                    '1000G': row['AF_1000G'],
                    'TW Biobank': row['TaiwanBioBank']
                }

                # 5. Genotype / VAF
                new_row['Genotype / VAF'] = {
                    'GT': row['GT'],
                    'VAF': float(row['VAF']),
                    'AD': row['AD'],
                    'Otherinfo10': row['Otherinfo10']
                }

                # 6. Evidence
                new_row['Evidence'] = {
                    'Clinvar': '.' if row['clinvar_summary'] == '.' else row['clinvar_summary'],
                    'LOVD': '.' if row['LOVD_all_clinical'] == '.' else row['LOVD_SIG']
                }

                # 7. Domain
                new_row['Domain'] = row['Interpro_domain']

                # 8. Pathogenicity
                new_row['Pathogenicity'] = {
                    'Summary': f"({row['deleterious_agreed']}/{row['deleterious_tools']})",
                    'Polyphen2_HVAR': row['Polyphen2_HVAR_pred'],
                    'SIFT': row['SIFT_pred'],
                    'VEST3': row['VEST3_score'],
                    'MutationTaster': row['MutationTaster_pred'],
                    'MetaSVM': row['MetaSVM_pred'],
                    'MetaLR': row['MetaLR_pred'],
                    'CADD': row['CADD_phred'],
                    'DANN': row['DANN_score']
                }

                # 9. Splicing effect
                new_row['Splicing effect'] = {
                    'Summary': f"({row['splicing_effect_agreed']}/{row['splicing_effect_tools']})",
                    'dbscsnv ADA score': row['dbscSNV_ADA_SCORE'],
                    'dbscsnv RF score': row['dbscSNV_RF_SCORE'],
                    'SPIDEX zscore': row['dpsi_zscore']
                }

                # 10. OMIM
                if row['Phenotype'] == -1:
                    result ='X'
                else :
                    omim_chromosome = row['Phenotype'].split('(')[-1].split(')')[0]
                    print(omim_chromosome)
                    genotype = new_row['Genotype / VAF']['GT']
                    print(genotype)
                    result = 'X'

                    if omim_chromosome in ['AD', 'AR']:
                        if omim_chromosome == 'AD':
                            if genotype in ['hom', 'het']:
                                result = 'O'
                        elif omim_chromosome == 'AR':
                            if genotype == 'hom':
                                result = 'O'
                    elif omim_chromosome == 'XLR':
                        if gender == 'Male' and genotype in ['het', 'hom']:
                            result = 'O'
                        elif gender == 'Female' and genotype == 'het':
                            result = 'O'
                    elif omim_chromosome == 'XLD':
                        if gender == 'Male' and genotype in ['het', 'hom']:
                            result = 'O'
                        elif gender == 'Female' and genotype == 'hom':
                            result = 'O'

                new_row['OMIM_number'] = {
                    'Phenotype': row['Phenotype'],
                    'OMIM_number': row['OMIM_number'] if row['OMIM_number'] != 'None' else '',
                    '符合條件': result
                }

                # 11. Amelie Max score
                new_row['Amelie Max score'] = row['Max_Score']

                # 12. Amelie Mean score
                new_row['Amelie Mean score'] = row['Mean_Score']

                data.append(new_row)

        folder_path = f'/miRTI/media/patient/{newJobID}/result_table'

        # 
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            print(f"資料夾 '{folder_path}' 建立成功")
        else:
            print(f"資料夾 '{folder_path}' 已存在，跳過建立")

        with open(f'{folder_path}/predicted_suspect_variant_result.csv', mode='w', encoding='utf-8-sig', newline='') as csv_file:
            fieldnames = ['Location', 'Gene', 'RS ID', 'MAF', 'Genotype / VAF', 'Evidence', 
                        'Domain', 'Pathogenicity', 'Splicing effect', 'OMIM_number', 
                        'Amelie Max score', 'Amelie Mean score']
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)

            writer.writeheader()
            for row in data:
                writer.writerow(row)

        return JsonResponse(data, safe=False)
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)


@csrf_exempt
def predicted_suspect_variant_trio(request):
    if request.method == 'POST':
        finished_jobs = existJobs.jobs.all().filter(status="finished")
        newJobID = globals.global_newJobID
        print(newJobID)
        output_csv_path = f'/miRTI/media/patient/{newJobID}/result_table/predicted_suspect_variant_result.csv'
        if os.path.exists(output_csv_path):
            with open(output_csv_path, mode='r', encoding='utf-8-sig') as csv_file:
                reader = csv.DictReader(csv_file)
                data = []

                for row in reader:
                    new_row = {}
                    # 填入各個欄位的資料
                    new_row['Location'] = row['Location']
                    new_row['Gene'] = row['Gene']
                    new_row['RS ID'] = row['RS ID']
                    new_row['MAF'] = eval(row['MAF'])
                    new_row['Genotype / VAF'] = eval(row['Genotype / VAF'])
                    new_row['Evidence'] = eval(row['Evidence'])
                    new_row['Domain'] = row['Domain']
                    new_row['Pathogenicity'] = eval(row['Pathogenicity'])
                    new_row['Splicing effect'] = eval(row['Splicing effect'])
                    new_row['OMIM_number'] = eval(row['OMIM_number'])
                    new_row['Amelie Max score'] = row['Amelie Max score']
                    new_row['Amelie Mean score'] = row['Amelie Mean score']
                    new_row['INH'] = row['INH']
                    data.append(new_row)

            return JsonResponse(data, safe=False)


        first_record = finished_jobs.filter(jobID=newJobID).first()

        if first_record is None:
            return JsonResponse({'error': 'No finished job found with the given job ID'}, status=404)

        select_job = first_record.jobID
        gender=first_record.gender

        sampleID = finished_jobs.filter(jobID=select_job)[0].subject_id
        fs = FileSystemStorage()
        parm_pickle = os.path.join(fs.location, 'patient', select_job, f'{sampleID}.pickle')
        print("****")

        parameters = load_parameters1(parm_pickle)

        parameters['suspect_pheno_variant'] = parameters['suspect_pheno_variant'].apply(rearrange_location1, axis=1)

        parameters = modify_table1(parameters, ['suspect_pheno_variant'])
        print("**************************************")
        print(parameters['suspect_pheno_variant'])
        parameters['suspect_pheno_variant'].to_csv(f'/miRTI/media/patient/{newJobID}/result_table/predicted_suspect_variant.csv', index=False)

        # Process data
        data = []
        with open(f'/miRTI/media/patient/{newJobID}/result_table/predicted_suspect_variant.csv', mode='r', encoding='utf-8-sig') as original_file:
            reader = csv.DictReader(original_file)

            for row in reader:
                new_row = {}

                # 1. Location
                new_row['Location'] = f"{row['Chr']}:{row['Start']}_{row['End']}{row['Ref']}>{row['Alt']}"

                # 2. Gene
                new_row['Gene'] = row['Gene_refGene']

                # 3. RS ID
                new_row['RS ID'] = row['avsnp150']

                # 4. MAF
                new_row['MAF'] = {
                    'gnomAD': row['AF'],
                    '1000G': row['AF_1000G'],
                    'TW Biobank': row['TaiwanBioBank']
                }

                # 5. Genotype / VAF
                new_row['Genotype / VAF'] = {
                    'GT': row['GT'],
                    'VAF': float(row['VAF']),
                    'AD': row['AD'],
                    'Otherinfo10': row['Otherinfo10']
                }

                # 6. Evidence
                new_row['Evidence'] = {
                    'Clinvar': '.' if row['clinvar_summary'] == '.' else row['clinvar_summary'],
                    'LOVD': '.' if row['LOVD_all_clinical'] == '.' else row['LOVD_SIG']
                }

                # 7. Domain
                new_row['Domain'] = row['Interpro_domain']

                # 8. Pathogenicity
                new_row['Pathogenicity'] = {
                    'Summary': f"({row['deleterious_agreed']}/{row['deleterious_tools']})",
                    'Polyphen2_HVAR': row['Polyphen2_HVAR_pred'],
                    'SIFT': row['SIFT_pred'],
                    'VEST3': row['VEST3_score'],
                    'MutationTaster': row['MutationTaster_pred'],
                    'MetaSVM': row['MetaSVM_pred'],
                    'MetaLR': row['MetaLR_pred'],
                    'CADD': row['CADD_phred'],
                    'DANN': row['DANN_score']
                }

                # 9. Splicing effect
                new_row['Splicing effect'] = {
                    'Summary': f"({row['splicing_effect_agreed']}/{row['splicing_effect_tools']})",
                    'dbscsnv ADA score': row['dbscSNV_ADA_SCORE'],
                    'dbscsnv RF score': row['dbscSNV_RF_SCORE'],
                    'SPIDEX zscore': row['dpsi_zscore']
                }

                # 10. OMIM
                if row['Phenotype'] == -1:
                    result ='X'
                else :
                    omim_chromosome = row['Phenotype'].split('(')[-1].split(')')[0]
                    print(omim_chromosome)
                    genotype = new_row['Genotype / VAF']['GT']
                    print(genotype)
                    result = 'X'

                    if omim_chromosome in ['AD', 'AR']:
                        if omim_chromosome == 'AD':
                            if genotype in ['hom', 'het']:
                                result = 'O'
                        elif omim_chromosome == 'AR':
                            if genotype == 'hom':
                                result = 'O'
                    elif omim_chromosome == 'XLR':
                        if gender == 'Male' and genotype in ['het', 'hom']:
                            result = 'O'
                        elif gender == 'Female' and genotype == 'het':
                            result = 'O'
                    elif omim_chromosome == 'XLD':
                        if gender == 'Male' and genotype in ['het', 'hom']:
                            result = 'O'
                        elif gender == 'Female' and genotype == 'hom':
                            result = 'O'

                new_row['OMIM_number'] = {
                    'Phenotype': row['Phenotype'],
                    'OMIM_number': row['OMIM_number'] if row['OMIM_number'] != 'None' else '',
                    '符合條件': result
                }

                # 11. Amelie Max score
                new_row['Amelie Max score'] = row['Max_Score']

                # 12. Amelie Mean score
                new_row['Amelie Mean score'] = row['Mean_Score']

                # 13. INH
                new_row['INH'] = row['INH']

                data.append(new_row)

        folder_path = f'/miRTI/media/patient/{newJobID}/result_table'

        # 
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            print(f"資料夾 '{folder_path}' 建立成功")
        else:
            print(f"資料夾 '{folder_path}' 已存在，跳過建立")

        with open(f'{folder_path}/predicted_suspect_variant_result.csv', mode='w', encoding='utf-8-sig', newline='') as csv_file:
            fieldnames = ['Location', 'Gene', 'RS ID', 'MAF', 'Genotype / VAF', 'Evidence', 
                        'Domain', 'Pathogenicity', 'Splicing effect', 'OMIM_number', 
                        'Amelie Max score', 'Amelie Mean score', 'INH']
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)

            writer.writeheader()
            for row in data:
                writer.writerow(row)

        return JsonResponse(data, safe=False)
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)




@csrf_exempt
def predicted_ACMG_variant(request):
    if request.method == 'POST':
        finished_jobs = existJobs.jobs.all().filter(status="finished")
        newJobID = globals.global_newJobID
        print(newJobID)
        output_csv_path = f'/miRTI/media/patient/{newJobID}/result_table/predicted_ACMG_variant_result.csv'
        if os.path.exists(output_csv_path):
            with open(output_csv_path, mode='r', encoding='utf-8-sig') as csv_file:
                reader = csv.DictReader(csv_file)
                data = []

                for row in reader:
                    new_row = {}
                    # 填入各個欄位的資料
                    new_row['Location'] = row['Location']
                    new_row['Gene'] = row['Gene']
                    new_row['RS ID'] = row['RS ID']
                    new_row['MAF'] = eval(row['MAF'])
                    new_row['Genotype / VAF'] = eval(row['Genotype / VAF'])
                    new_row['Evidence'] = eval(row['Evidence'])
                    new_row['Domain'] = row['Domain']
                    new_row['Pathogenicity'] = eval(row['Pathogenicity'])
                    new_row['Splicing effect'] = eval(row['Splicing effect'])
                    new_row['OMIM_number'] = eval(row['OMIM_number'])
                    new_row['Amelie Max score'] = row['Amelie Max score']
                    new_row['Amelie Mean score'] = row['Amelie Mean score']
                    data.append(new_row)

            return JsonResponse(data, safe=False)


        first_record = finished_jobs.filter(jobID=newJobID).first()

        if first_record is None:
            return JsonResponse({'error': 'No finished job found with the given job ID'}, status=404)

        select_job = first_record.jobID
        gender=first_record.gender

        sampleID = finished_jobs.filter(jobID=select_job)[0].subject_id
        fs = FileSystemStorage()
        parm_pickle = os.path.join(fs.location, 'patient', select_job, f'{sampleID}.pickle')
        print("****")

        parameters = load_parameters1(parm_pickle)

        parameters['suspect_ACMG_variant'] = parameters['suspect_ACMG_variant'].apply(rearrange_location1, axis=1)

        parameters = modify_table1(parameters, ['suspect_ACMG_variant'])
        print("**************************************")
        print(parameters['suspect_ACMG_variant'])
        parameters['suspect_ACMG_variant'].to_csv(f'/miRTI/media/patient/{newJobID}/result_table/predicted_ACMG_variant.csv', index=False)

        # Process data
        data = []
        with open(f'/miRTI/media/patient/{newJobID}/result_table/predicted_ACMG_variant.csv', mode='r', encoding='utf-8-sig') as original_file:
            reader = csv.DictReader(original_file)

            for row in reader:
                new_row = {}

                # 1. Location
                new_row['Location'] = f"{row['Chr']}:{row['Start']}_{row['End']}{row['Ref']}>{row['Alt']}"

                # 2. Gene
                new_row['Gene'] = row['Gene_refGene']

                # 3. RS ID
                new_row['RS ID'] = row['avsnp150']

                # 4. MAF
                new_row['MAF'] = {
                    'gnomAD': row['AF'],
                    '1000G': row['AF_1000G'],
                    'TW Biobank': row['TaiwanBioBank']
                }

                # 5. Genotype / VAF
                new_row['Genotype / VAF'] = {
                    'GT': row['GT'],
                    'VAF': float(row['VAF']),
                    'AD': row['AD'],
                    'Otherinfo10': row['Otherinfo10']
                }

                # 6. Evidence
                new_row['Evidence'] = {
                    'Clinvar': '.' if row['clinvar_summary'] == '.' else row['clinvar_summary'],
                    'LOVD': '.' if row['LOVD_all_clinical'] == '.' else row['LOVD_SIG']
                }

                # 7. Domain
                new_row['Domain'] = row['Interpro_domain']

                # 8. Pathogenicity
                new_row['Pathogenicity'] = {
                    'Summary': f"({row['deleterious_agreed']}/{row['deleterious_tools']})",
                    'Polyphen2_HVAR': row['Polyphen2_HVAR_pred'],
                    'SIFT': row['SIFT_pred'],
                    'VEST3': row['VEST3_score'],
                    'MutationTaster': row['MutationTaster_pred'],
                    'MetaSVM': row['MetaSVM_pred'],
                    'MetaLR': row['MetaLR_pred'],
                    'CADD': row['CADD_phred'],
                    'DANN': row['DANN_score']
                }

                # 9. Splicing effect
                new_row['Splicing effect'] = {
                    'Summary': f"({row['splicing_effect_agreed']}/{row['splicing_effect_tools']})",
                    'dbscsnv ADA score': row['dbscSNV_ADA_SCORE'],
                    'dbscsnv RF score': row['dbscSNV_RF_SCORE'],
                    'SPIDEX zscore': row['dpsi_zscore']
                }

                # 10. OMIM
                if row['Phenotype'] == -1:
                    result ='X'
                else :
                    omim_chromosome = row['Phenotype'].split('(')[-1].split(')')[0]
                    print(omim_chromosome)
                    genotype = new_row['Genotype / VAF']['GT']
                    print(genotype)
                    result = 'X'

                    if omim_chromosome in ['AD', 'AR']:
                        if omim_chromosome == 'AD':
                            if genotype in ['hom', 'het']:
                                result = 'O'
                        elif omim_chromosome == 'AR':
                            if genotype == 'hom':
                                result = 'O'
                    elif omim_chromosome == 'XLR':
                        if gender == 'Male' and genotype in ['het', 'hom']:
                            result = 'O'
                        elif gender == 'Female' and genotype == 'het':
                            result = 'O'
                    elif omim_chromosome == 'XLD':
                        if gender == 'Male' and genotype in ['het', 'hom']:
                            result = 'O'
                        elif gender == 'Female' and genotype == 'hom':
                            result = 'O'

                new_row['OMIM_number'] = {
                    'Phenotype': row['Phenotype'],
                    'OMIM_number': row['OMIM_number'] if row['OMIM_number'] != 'None' else '',
                    '符合條件': result
                }

                # 11. Amelie Max score
                new_row['Amelie Max score'] = row['Max_Score']

                # 12. Amelie Mean score
                new_row['Amelie Mean score'] = row['Mean_Score']

                data.append(new_row)

        folder_path = f'/miRTI/media/patient/{newJobID}/result_table'

        # 
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            print(f"資料夾 '{folder_path}' 建立成功")
        else:
            print(f"資料夾 '{folder_path}' 已存在，跳過建立")

        with open(f'{folder_path}/predicted_ACMG_variant_result.csv', mode='w', encoding='utf-8-sig', newline='') as csv_file:
            fieldnames = ['Location', 'Gene', 'RS ID', 'MAF', 'Genotype / VAF', 'Evidence', 
                        'Domain', 'Pathogenicity', 'Splicing effect', 'OMIM_number', 
                        'Amelie Max score', 'Amelie Mean score']
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)

            writer.writeheader()
            for row in data:
                writer.writerow(row)

        return JsonResponse(data, safe=False)
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)
    
@csrf_exempt
def predicted_ACMG_variant_trio(request):
    if request.method == 'POST':
        finished_jobs = existJobs.jobs.all().filter(status="finished")
        newJobID = globals.global_newJobID
        print(newJobID)
        output_csv_path = f'/miRTI/media/patient/{newJobID}/result_table/predicted_ACMG_variant_result.csv'
        if os.path.exists(output_csv_path):
            with open(output_csv_path, mode='r', encoding='utf-8-sig') as csv_file:
                reader = csv.DictReader(csv_file)
                data = []

                for row in reader:
                    new_row = {}
                    # 填入各個欄位的資料
                    new_row['Location'] = row['Location']
                    new_row['Gene'] = row['Gene']
                    new_row['RS ID'] = row['RS ID']
                    new_row['MAF'] = eval(row['MAF'])
                    new_row['Genotype / VAF'] = eval(row['Genotype / VAF'])
                    new_row['Evidence'] = eval(row['Evidence'])
                    new_row['Domain'] = row['Domain']
                    new_row['Pathogenicity'] = eval(row['Pathogenicity'])
                    new_row['Splicing effect'] = eval(row['Splicing effect'])
                    new_row['OMIM_number'] = eval(row['OMIM_number'])
                    new_row['Amelie Max score'] = row['Amelie Max score']
                    new_row['Amelie Mean score'] = row['Amelie Mean score']
                    new_row['INH'] = row['INH']
                    data.append(new_row)

            return JsonResponse(data, safe=False)


        first_record = finished_jobs.filter(jobID=newJobID).first()

        if first_record is None:
            return JsonResponse({'error': 'No finished job found with the given job ID'}, status=404)

        select_job = first_record.jobID
        gender=first_record.gender

        sampleID = finished_jobs.filter(jobID=select_job)[0].subject_id
        fs = FileSystemStorage()
        parm_pickle = os.path.join(fs.location, 'patient', select_job, f'{sampleID}.pickle')
        print("****")

        parameters = load_parameters1(parm_pickle)

        parameters['suspect_ACMG_variant'] = parameters['suspect_ACMG_variant'].apply(rearrange_location1, axis=1)

        parameters = modify_table1(parameters, ['suspect_ACMG_variant'])
        print("**************************************")
        print(parameters['suspect_ACMG_variant'])
        parameters['suspect_ACMG_variant'].to_csv(f'/miRTI/media/patient/{newJobID}/result_table/predicted_ACMG_variant.csv', index=False)

        # Process data
        data = []
        with open(f'/miRTI/media/patient/{newJobID}/result_table/predicted_ACMG_variant.csv', mode='r', encoding='utf-8-sig') as original_file:
            reader = csv.DictReader(original_file)

            for row in reader:
                new_row = {}

                # 1. Location
                new_row['Location'] = f"{row['Chr']}:{row['Start']}_{row['End']}{row['Ref']}>{row['Alt']}"

                # 2. Gene
                new_row['Gene'] = row['Gene_refGene']

                # 3. RS ID
                new_row['RS ID'] = row['avsnp150']

                # 4. MAF
                new_row['MAF'] = {
                    'gnomAD': row['AF'],
                    '1000G': row['AF_1000G'],
                    'TW Biobank': row['TaiwanBioBank']
                }

                # 5. Genotype / VAF
                new_row['Genotype / VAF'] = {
                    'GT': row['GT'],
                    'VAF': float(row['VAF']),
                    'AD': row['AD'],
                    'Otherinfo10': row['Otherinfo10']
                }

                # 6. Evidence
                new_row['Evidence'] = {
                    'Clinvar': '.' if row['clinvar_summary'] == '.' else row['clinvar_summary'],
                    'LOVD': '.' if row['LOVD_all_clinical'] == '.' else row['LOVD_SIG']
                }

                # 7. Domain
                new_row['Domain'] = row['Interpro_domain']

                # 8. Pathogenicity
                new_row['Pathogenicity'] = {
                    'Summary': f"({row['deleterious_agreed']}/{row['deleterious_tools']})",
                    'Polyphen2_HVAR': row['Polyphen2_HVAR_pred'],
                    'SIFT': row['SIFT_pred'],
                    'VEST3': row['VEST3_score'],
                    'MutationTaster': row['MutationTaster_pred'],
                    'MetaSVM': row['MetaSVM_pred'],
                    'MetaLR': row['MetaLR_pred'],
                    'CADD': row['CADD_phred'],
                    'DANN': row['DANN_score']
                }

                # 9. Splicing effect
                new_row['Splicing effect'] = {
                    'Summary': f"({row['splicing_effect_agreed']}/{row['splicing_effect_tools']})",
                    'dbscsnv ADA score': row['dbscSNV_ADA_SCORE'],
                    'dbscsnv RF score': row['dbscSNV_RF_SCORE'],
                    'SPIDEX zscore': row['dpsi_zscore']
                }

                # 10. OMIM
                if row['Phenotype'] == -1:
                    result ='X'
                else :
                    omim_chromosome = row['Phenotype'].split('(')[-1].split(')')[0]
                    print(omim_chromosome)
                    genotype = new_row['Genotype / VAF']['GT']
                    print(genotype)
                    result = 'X'

                    if omim_chromosome in ['AD', 'AR']:
                        if omim_chromosome == 'AD':
                            if genotype in ['hom', 'het']:
                                result = 'O'
                        elif omim_chromosome == 'AR':
                            if genotype == 'hom':
                                result = 'O'
                    elif omim_chromosome == 'XLR':
                        if gender == 'Male' and genotype in ['het', 'hom']:
                            result = 'O'
                        elif gender == 'Female' and genotype == 'het':
                            result = 'O'
                    elif omim_chromosome == 'XLD':
                        if gender == 'Male' and genotype in ['het', 'hom']:
                            result = 'O'
                        elif gender == 'Female' and genotype == 'hom':
                            result = 'O'

                new_row['OMIM_number'] = {
                    'Phenotype': row['Phenotype'],
                    'OMIM_number': row['OMIM_number'] if row['OMIM_number'] != 'None' else '',
                    '符合條件': result
                }

                # 11. Amelie Max score
                new_row['Amelie Max score'] = row['Max_Score']

                # 12. Amelie Mean score
                new_row['Amelie Mean score'] = row['Mean_Score']

                # 13. INH
                new_row['INH'] = row['INH']

                data.append(new_row)

        folder_path = f'/miRTI/media/patient/{newJobID}/result_table'

        # 
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            print(f"資料夾 '{folder_path}' 建立成功")
        else:
            print(f"資料夾 '{folder_path}' 已存在，跳過建立")

        with open(f'{folder_path}/predicted_ACMG_variant_result.csv', mode='w', encoding='utf-8-sig', newline='') as csv_file:
            fieldnames = ['Location', 'Gene', 'RS ID', 'MAF', 'Genotype / VAF', 'Evidence', 
                        'Domain', 'Pathogenicity', 'Splicing effect', 'OMIM_number', 
                        'Amelie Max score', 'Amelie Mean score', 'INH']
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)

            writer.writeheader()
            for row in data:
                writer.writerow(row)

        return JsonResponse(data, safe=False)
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)


@csrf_exempt
def predicted_other_variant(request):
    if request.method == 'POST':
        finished_jobs = existJobs.jobs.all().filter(status="finished")
        newJobID = globals.global_newJobID
        print(newJobID)
        output_csv_path = f'/miRTI/media/patient/{newJobID}/result_table/predicted_other_variant_result.csv'
        if os.path.exists(output_csv_path):
            with open(output_csv_path, mode='r', encoding='utf-8-sig') as csv_file:
                reader = csv.DictReader(csv_file)
                data = []

                for row in reader:
                    new_row = {}
                    # 填入各個欄位的資料
                    new_row['Location'] = row['Location']
                    new_row['Gene'] = row['Gene']
                    new_row['RS ID'] = row['RS ID']
                    new_row['MAF'] = eval(row['MAF'])
                    new_row['Genotype / VAF'] = eval(row['Genotype / VAF'])
                    new_row['Evidence'] = eval(row['Evidence'])
                    new_row['Domain'] = row['Domain']
                    new_row['Pathogenicity'] = eval(row['Pathogenicity'])
                    new_row['Splicing effect'] = eval(row['Splicing effect'])
                    new_row['OMIM_number'] = eval(row['OMIM_number'])
                    new_row['Amelie Max score'] = row['Amelie Max score']
                    new_row['Amelie Mean score'] = row['Amelie Mean score']
                    data.append(new_row)

            return JsonResponse(data, safe=False)


        first_record = finished_jobs.filter(jobID=newJobID).first()

        if first_record is None:
            return JsonResponse({'error': 'No finished job found with the given job ID'}, status=404)

        select_job = first_record.jobID
        gender=first_record.gender

        sampleID = finished_jobs.filter(jobID=select_job)[0].subject_id
        fs = FileSystemStorage()
        parm_pickle = os.path.join(fs.location, 'patient', select_job, f'{sampleID}.pickle')
        print("****")

        parameters = load_parameters1(parm_pickle)

        parameters['suspect_other_variant'] = parameters['suspect_other_variant'].apply(rearrange_location1, axis=1)

        parameters = modify_table1(parameters, ['suspect_other_variant'])
        print("**************************************")
        print(parameters['suspect_other_variant'])
        parameters['suspect_other_variant'].to_csv(f'/miRTI/media/patient/{newJobID}/result_table/predicted_other_variant.csv', index=False)

        # Process data
        data = []
        with open(f'/miRTI/media/patient/{newJobID}/result_table/predicted_other_variant.csv', mode='r', encoding='utf-8-sig') as original_file:
            reader = csv.DictReader(original_file)

            for row in reader:
                new_row = {}

                # 1. Location
                new_row['Location'] = f"{row['Chr']}:{row['Start']}_{row['End']}{row['Ref']}>{row['Alt']}"

                # 2. Gene
                new_row['Gene'] = row['Gene_refGene']

                # 3. RS ID
                new_row['RS ID'] = row['avsnp150']

                # 4. MAF
                new_row['MAF'] = {
                    'gnomAD': row['AF'],
                    '1000G': row['AF_1000G'],
                    'TW Biobank': row['TaiwanBioBank']
                }

                # 5. Genotype / VAF
                new_row['Genotype / VAF'] = {
                    'GT': row['GT'],
                    'VAF': float(row['VAF']),
                    'AD': row['AD'],
                    'Otherinfo10': row['Otherinfo10']
                }

                # 6. Evidence
                new_row['Evidence'] = {
                    'Clinvar': '.' if row['clinvar_summary'] == '.' else row['clinvar_summary'],
                    'LOVD': '.' if row['LOVD_all_clinical'] == '.' else row['LOVD_SIG']
                }

                # 7. Domain
                new_row['Domain'] = row['Interpro_domain']

                # 8. Pathogenicity
                new_row['Pathogenicity'] = {
                    'Summary': f"({row['deleterious_agreed']}/{row['deleterious_tools']})",
                    'Polyphen2_HVAR': row['Polyphen2_HVAR_pred'],
                    'SIFT': row['SIFT_pred'],
                    'VEST3': row['VEST3_score'],
                    'MutationTaster': row['MutationTaster_pred'],
                    'MetaSVM': row['MetaSVM_pred'],
                    'MetaLR': row['MetaLR_pred'],
                    'CADD': row['CADD_phred'],
                    'DANN': row['DANN_score']
                }

                # 9. Splicing effect
                new_row['Splicing effect'] = {
                    'Summary': f"({row['splicing_effect_agreed']}/{row['splicing_effect_tools']})",
                    'dbscsnv ADA score': row['dbscSNV_ADA_SCORE'],
                    'dbscsnv RF score': row['dbscSNV_RF_SCORE'],
                    'SPIDEX zscore': row['dpsi_zscore']
                }

                # 10. OMIM
                if row['Phenotype'] == -1:
                    result ='X'
                else :
                    omim_chromosome = row['Phenotype'].split('(')[-1].split(')')[0]
                    print(omim_chromosome)
                    genotype = new_row['Genotype / VAF']['GT']
                    print(genotype)
                    result = 'X'

                    if omim_chromosome in ['AD', 'AR']:
                        if omim_chromosome == 'AD':
                            if genotype in ['hom', 'het']:
                                result = 'O'
                        elif omim_chromosome == 'AR':
                            if genotype == 'hom':
                                result = 'O'
                    elif omim_chromosome == 'XLR':
                        if gender == 'Male' and genotype in ['het', 'hom']:
                            result = 'O'
                        elif gender == 'Female' and genotype == 'het':
                            result = 'O'
                    elif omim_chromosome == 'XLD':
                        if gender == 'Male' and genotype in ['het', 'hom']:
                            result = 'O'
                        elif gender == 'Female' and genotype == 'hom':
                            result = 'O'

                new_row['OMIM_number'] = {
                    'Phenotype': row['Phenotype'],
                    'OMIM_number': row['OMIM_number'] if row['OMIM_number'] != 'None' else '',
                    '符合條件': result
                }

                # 11. Amelie Max score
                new_row['Amelie Max score'] = row['Max_Score']

                # 12. Amelie Mean score
                new_row['Amelie Mean score'] = row['Mean_Score']

                data.append(new_row)

        folder_path = f'/miRTI/media/patient/{newJobID}/result_table'

        # 
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            print(f"資料夾 '{folder_path}' 建立成功")
        else:
            print(f"資料夾 '{folder_path}' 已存在，跳過建立")

        with open(f'{folder_path}/predicted_other_variant_result.csv', mode='w', encoding='utf-8-sig', newline='') as csv_file:
            fieldnames = ['Location', 'Gene', 'RS ID', 'MAF', 'Genotype / VAF', 'Evidence', 
                        'Domain', 'Pathogenicity', 'Splicing effect', 'OMIM_number', 
                        'Amelie Max score', 'Amelie Mean score']
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)

            writer.writeheader()
            for row in data:
                writer.writerow(row)

        return JsonResponse(data, safe=False)
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)
    
@csrf_exempt
def predicted_other_variant_trio(request):
    if request.method == 'POST':
        finished_jobs = existJobs.jobs.all().filter(status="finished")
        newJobID = globals.global_newJobID
        print(newJobID)
        output_csv_path = f'/miRTI/media/patient/{newJobID}/result_table/predicted_other_variant_result.csv'
        if os.path.exists(output_csv_path):
            with open(output_csv_path, mode='r', encoding='utf-8-sig') as csv_file:
                reader = csv.DictReader(csv_file)
                data = []

                for row in reader:
                    new_row = {}
                    # 填入各個欄位的資料
                    new_row['Location'] = row['Location']
                    new_row['Gene'] = row['Gene']
                    new_row['RS ID'] = row['RS ID']
                    new_row['MAF'] = eval(row['MAF'])
                    new_row['Genotype / VAF'] = eval(row['Genotype / VAF'])
                    new_row['Evidence'] = eval(row['Evidence'])
                    new_row['Domain'] = row['Domain']
                    new_row['Pathogenicity'] = eval(row['Pathogenicity'])
                    new_row['Splicing effect'] = eval(row['Splicing effect'])
                    new_row['OMIM_number'] = eval(row['OMIM_number'])
                    new_row['Amelie Max score'] = row['Amelie Max score']
                    new_row['Amelie Mean score'] = row['Amelie Mean score']
                    new_row['INH'] = row['INH']
                    data.append(new_row)

            return JsonResponse(data, safe=False)


        first_record = finished_jobs.filter(jobID=newJobID).first()

        if first_record is None:
            return JsonResponse({'error': 'No finished job found with the given job ID'}, status=404)

        select_job = first_record.jobID
        gender=first_record.gender

        sampleID = finished_jobs.filter(jobID=select_job)[0].subject_id
        fs = FileSystemStorage()
        parm_pickle = os.path.join(fs.location, 'patient', select_job, f'{sampleID}.pickle')
        print("****")

        parameters = load_parameters1(parm_pickle)

        parameters['suspect_other_variant'] = parameters['suspect_other_variant'].apply(rearrange_location1, axis=1)

        parameters = modify_table1(parameters, ['suspect_other_variant'])
        print("**************************************")
        print(parameters['suspect_other_variant'])
        parameters['suspect_other_variant'].to_csv(f'/miRTI/media/patient/{newJobID}/result_table/predicted_other_variant.csv', index=False)

        # Process data
        data = []
        with open(f'/miRTI/media/patient/{newJobID}/result_table/predicted_other_variant.csv', mode='r', encoding='utf-8-sig') as original_file:
            reader = csv.DictReader(original_file)

            for row in reader:
                new_row = {}

                # 1. Location
                new_row['Location'] = f"{row['Chr']}:{row['Start']}_{row['End']}{row['Ref']}>{row['Alt']}"

                # 2. Gene
                new_row['Gene'] = row['Gene_refGene']

                # 3. RS ID
                new_row['RS ID'] = row['avsnp150']

                # 4. MAF
                new_row['MAF'] = {
                    'gnomAD': row['AF'],
                    '1000G': row['AF_1000G'],
                    'TW Biobank': row['TaiwanBioBank']
                }

                # 5. Genotype / VAF
                new_row['Genotype / VAF'] = {
                    'GT': row['GT'],
                    'VAF': float(row['VAF']),
                    'AD': row['AD'],
                    'Otherinfo10': row['Otherinfo10']
                }

                # 6. Evidence
                new_row['Evidence'] = {
                    'Clinvar': '.' if row['clinvar_summary'] == '.' else row['clinvar_summary'],
                    'LOVD': '.' if row['LOVD_all_clinical'] == '.' else row['LOVD_SIG']
                }

                # 7. Domain
                new_row['Domain'] = row['Interpro_domain']

                # 8. Pathogenicity
                new_row['Pathogenicity'] = {
                    'Summary': f"({row['deleterious_agreed']}/{row['deleterious_tools']})",
                    'Polyphen2_HVAR': row['Polyphen2_HVAR_pred'],
                    'SIFT': row['SIFT_pred'],
                    'VEST3': row['VEST3_score'],
                    'MutationTaster': row['MutationTaster_pred'],
                    'MetaSVM': row['MetaSVM_pred'],
                    'MetaLR': row['MetaLR_pred'],
                    'CADD': row['CADD_phred'],
                    'DANN': row['DANN_score']
                }

                # 9. Splicing effect
                new_row['Splicing effect'] = {
                    'Summary': f"({row['splicing_effect_agreed']}/{row['splicing_effect_tools']})",
                    'dbscsnv ADA score': row['dbscSNV_ADA_SCORE'],
                    'dbscsnv RF score': row['dbscSNV_RF_SCORE'],
                    'SPIDEX zscore': row['dpsi_zscore']
                }

                # 10. OMIM
                if row['Phenotype'] == -1:
                    result ='X'
                else :
                    omim_chromosome = row['Phenotype'].split('(')[-1].split(')')[0]
                    print(omim_chromosome)
                    genotype = new_row['Genotype / VAF']['GT']
                    print(genotype)
                    result = 'X'

                    if omim_chromosome in ['AD', 'AR']:
                        if omim_chromosome == 'AD':
                            if genotype in ['hom', 'het']:
                                result = 'O'
                        elif omim_chromosome == 'AR':
                            if genotype == 'hom':
                                result = 'O'
                    elif omim_chromosome == 'XLR':
                        if gender == 'Male' and genotype in ['het', 'hom']:
                            result = 'O'
                        elif gender == 'Female' and genotype == 'het':
                            result = 'O'
                    elif omim_chromosome == 'XLD':
                        if gender == 'Male' and genotype in ['het', 'hom']:
                            result = 'O'
                        elif gender == 'Female' and genotype == 'hom':
                            result = 'O'

                new_row['OMIM_number'] = {
                    'Phenotype': row['Phenotype'],
                    'OMIM_number': row['OMIM_number'] if row['OMIM_number'] != 'None' else '',
                    '符合條件': result
                }

                # 11. Amelie Max score
                new_row['Amelie Max score'] = row['Max_Score']

                # 12. Amelie Mean score
                new_row['Amelie Mean score'] = row['Mean_Score']

                # 13. INH
                new_row['INH'] = row['INH']

                data.append(new_row)

        folder_path = f'/miRTI/media/patient/{newJobID}/result_table'

        # 
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            print(f"資料夾 '{folder_path}' 建立成功")
        else:
            print(f"資料夾 '{folder_path}' 已存在，跳過建立")

        with open(f'{folder_path}/predicted_other_variant_result.csv', mode='w', encoding='utf-8-sig', newline='') as csv_file:
            fieldnames = ['Location', 'Gene', 'RS ID', 'MAF', 'Genotype / VAF', 'Evidence', 
                        'Domain', 'Pathogenicity', 'Splicing effect', 'OMIM_number', 
                        'Amelie Max score', 'Amelie Mean score', 'INH']
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)

            writer.writeheader()
            for row in data:
                writer.writerow(row)

        return JsonResponse(data, safe=False)
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)
    
@csrf_exempt
def incidental_finding_variant(request):
    if request.method == 'POST':
        finished_jobs = existJobs.jobs.all().filter(status="finished")
        newJobID = globals.global_newJobID
        print(newJobID)
        output_csv_path1 = f'/miRTI/media/patient/{newJobID}/result_table/known_acmg_variant_result.csv'
        output_csv_path2 = f'/miRTI/media/patient/{newJobID}/result_table/known_other_variant_result.csv'
        if os.path.exists(output_csv_path1) and os.path.exists(output_csv_path2):
            data1 = []
            data2 = []

            # 讀取並處理第一份CSV
            with open(output_csv_path1, mode='r', encoding='utf-8-sig') as csv_file1:
                reader1 = csv.DictReader(csv_file1)
                for row in reader1:
                    new_row = {
                        'Location': row['Location'],
                        'Gene': row['Gene'],
                        'RS ID': row['RS ID'],
                        'MAF': eval(row['MAF']),
                        'Genotype / VAF': eval(row['Genotype / VAF']),
                        'Evidence': eval(row['Evidence']),
                        'Domain': row['Domain'],
                        'Pathogenicity': eval(row['Pathogenicity']),
                        'Splicing effect': eval(row['Splicing effect']),
                        'OMIM_number': eval(row['OMIM_number']),
                        'Amelie Max score': row['Amelie Max score'],
                        'Amelie Mean score': row['Amelie Mean score'],
                        
                    }
                    data1.append(new_row)
                    print(data1)
            # 讀取並處理第二份CSV
            with open(output_csv_path2, mode='r', encoding='utf-8-sig') as csv_file2:
                reader2 = csv.DictReader(csv_file2)
                for row in reader2:
                    new_row = {
                        'Location': row['Location'],
                        'Gene': row['Gene'],
                        'RS ID': row['RS ID'],
                        'MAF': eval(row['MAF']),
                        'Genotype / VAF': eval(row['Genotype / VAF']),
                        'Evidence': eval(row['Evidence']),
                        'Domain': row['Domain'],
                        'Pathogenicity': eval(row['Pathogenicity']),
                        'Splicing effect': eval(row['Splicing effect']),
                        'OMIM_number': eval(row['OMIM_number']),
                        'Amelie Max score': row['Amelie Max score'],
                        'Amelie Mean score': row['Amelie Mean score'],
                        
                    }
                    data2.append(new_row)
                    print(data2)
            # 同時返回兩份資料
            return JsonResponse({
                'data1': data1,
                'data2': data2
            }, safe=False)



        first_record = finished_jobs.filter(jobID=newJobID).first()

        if first_record is None:
            return JsonResponse({'error': 'No finished job found with the given job ID'}, status=404)

        select_job = first_record.jobID
        gender=first_record.gender
        print(gender)
        sampleID = finished_jobs.filter(jobID=select_job)[0].subject_id
        fs = FileSystemStorage()
        parm_pickle = os.path.join(fs.location, 'patient', select_job, f'{sampleID}.pickle')
        print("****")

        parameters = load_parameters1(parm_pickle)

        parameters['known_other_variant'] = parameters['known_other_variant'].apply(rearrange_location1, axis=1)
        parameters['known_ACMG_variant'] = parameters['known_ACMG_variant'].apply(rearrange_location1, axis=1)

        parameters = modify_table1(parameters, ['known_other_variant', 'known_ACMG_variant'])

        parameters['here_df_list'] = zip([parameters['known_ACMG_variant'], parameters['known_other_variant']],
                                        ['ACMG variants', 'Other pathogenic variants'])


        acmg_data = []
        for row in parameters['known_ACMG_variant'].itertuples():
            new_row = {}
            new_row['Location'] = f"{row.Chr}:{row.Start}_{row.End}{row.Ref}>{row.Alt}"
            new_row['Gene'] = row.Gene_refGene
            new_row['RS ID'] = row.avsnp150 if row.avsnp150 != '.' else ''
            new_row['MAF'] = {
                'gnomAD': row.AF,
                '1000G': row.AF_1000G,
                'TW Biobank': row.TaiwanBioBank
            }
            new_row['Genotype / VAF'] = {
                'GT': row.GT,
                'VAF': float(row.VAF),
                'AD': row.AD,
                'Otherinfo10': row.Otherinfo10
            }
            new_row['Evidence'] = {
                'Clinvar': '.' if row.clinvar_summary == '.' else row.clinvar_summary,
                'LOVD': '.' if row.LOVD_all_clinical == '.' else row.LOVD_SIG
            }
            new_row['Domain'] = row.Interpro_domain
            new_row['Pathogenicity'] = {
                'Summary': f"({row.deleterious_agreed}/{row.deleterious_tools})",
                'Polyphen2_HVAR': row.Polyphen2_HVAR_pred,
                'SIFT': row.SIFT_pred,
                'VEST3': row.VEST3_score,
                'MutationTaster': row.MutationTaster_pred,
                'MetaSVM': row.MetaSVM_pred,
                'MetaLR': row.MetaLR_pred,
                'CADD': row.CADD_phred,
                'DANN': row.DANN_score
            }
            new_row['Splicing effect'] = {
                'Summary': f"({row.splicing_effect_agreed}/{row.splicing_effect_tools})",
                'dbscsnv ADA score': row.dbscSNV_ADA_SCORE,
                'dbscsnv RF score': row.dbscSNV_RF_SCORE,
                'SPIDEX zscore': row.dpsi_zscore
            }
            
            # new_row['OMIM'] = row.OMIM_number if row.OMIM_number != 'None' else ''
            if row.Phenotype == -1:
                result = 'X'
            else:
                omim_chromosome = row.Phenotype.split('(')[-1].split(')')[0]
                print(omim_chromosome)
                genotype = new_row['Genotype / VAF']['GT']
                print(genotype)
                result = 'X'

                if omim_chromosome in ['AD', 'AR']:
                    if omim_chromosome == 'AD':
                        if genotype in ['hom', 'het']:
                            result = 'O'
                    elif omim_chromosome == 'AR':
                        if genotype == 'hom':
                            result = 'O'
                elif omim_chromosome == 'XLR':
                    if gender == 'Male' and genotype in ['het', 'hom']:
                        result = 'O'
                    elif gender == 'Female' and genotype == 'het':
                        result = 'O'
                elif omim_chromosome == 'XLD':
                    if gender == 'male' and genotype in ['het', 'hom']:
                        result = 'O'
                    elif gender == 'Female' and genotype == 'hom':
                        result = 'O'
            print(result)
            new_row['OMIM_number'] = {
                'Phenotype': row.Phenotype,
                'OMIM_number': row.OMIM_number if row.OMIM_number != -1 else '',
                '符合條件': result
            }
            new_row['Amelie Max score'] = row.Max_Score
            new_row['Amelie Mean score'] = row.Mean_Score
           

            acmg_data.append(new_row)
        folder_path = f'/miRTI/media/patient/{newJobID}/result_table'

        # 
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            print(f"資料夾 '{folder_path}' 建立成功")
        else:
            print(f"資料夾 '{folder_path}' 已存在，跳過建立")
    
        with open(f'{folder_path}/known_acmg_variant_result.csv', mode='w', encoding='utf-8-sig', newline='') as csv_file:
            fieldnames = ['Location', 'Gene', 'RS ID', 'MAF', 'Genotype / VAF', 'Evidence', 
                        'Domain', 'Pathogenicity', 'Splicing effect', 'OMIM_number', 
                        'Amelie Max score', 'Amelie Mean score']
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)

            writer.writeheader()
            for row in acmg_data:
                writer.writerow(row)


        other_data = []
        for row in parameters['known_other_variant'].itertuples():
            new_row = {}
            new_row['Location'] = f"{row.Chr}:{row.Start}_{row.End}{row.Ref}>{row.Alt}"
            new_row['Gene'] = row.Gene_refGene
            new_row['RS ID'] = row.avsnp150 if row.avsnp150 != '.' else ''
            new_row['MAF'] = {
                'gnomAD': row.AF,
                '1000G': row.AF_1000G,
                'TW Biobank': row.TaiwanBioBank
            }
            new_row['Genotype / VAF'] = {
                'GT': row.GT,
                'VAF': float(row.VAF),
                'AD': row.AD,
                'Otherinfo10': row.Otherinfo10
            }
            new_row['Evidence'] = {
                'Clinvar': '.' if row.clinvar_summary == '.' else row.clinvar_summary,
                'LOVD': '.' if row.LOVD_all_clinical == '.' else row.LOVD_SIG
            }
            new_row['Domain'] = row.Interpro_domain
            new_row['Pathogenicity'] = {
                'Summary': f"({row.deleterious_agreed}/{row.deleterious_tools})",
                'Polyphen2_HVAR': row.Polyphen2_HVAR_pred,
                'SIFT': row.SIFT_pred,
                'VEST3': row.VEST3_score,
                'MutationTaster': row.MutationTaster_pred,
                'MetaSVM': row.MetaSVM_pred,
                'MetaLR': row.MetaLR_pred,
                'CADD': row.CADD_phred,
                'DANN': row.DANN_score
            }
            new_row['Splicing effect'] = {
                'Summary': f"({row.splicing_effect_agreed}/{row.splicing_effect_tools})",
                'dbscsnv ADA score': row.dbscSNV_ADA_SCORE,
                'dbscsnv RF score': row.dbscSNV_RF_SCORE,
                'SPIDEX zscore': row.dpsi_zscore
            }
            # new_row['OMIM'] = row.OMIM_number if row.OMIM_number != 'None' else ''
            if row.Phenotype == -1:
                result = 'X'
            else:
                omim_chromosome = row.Phenotype.split('(')[-1].split(')')[0]
                print(omim_chromosome)
                genotype = new_row['Genotype / VAF']['GT']
                print(genotype)
                result = 'X'

                if omim_chromosome in ['AD', 'AR']:
                    if omim_chromosome == 'AD':
                        if genotype in ['hom', 'het']:
                            result = 'O'
                    elif omim_chromosome == 'AR':
                        if genotype == 'hom':
                            result = 'O'
                elif omim_chromosome == 'XLR':
                    if gender == 'male' and genotype in ['het', 'hom']:
                        result = 'O'
                    elif gender == 'Female' and genotype == 'het':
                        result = 'O'
                elif omim_chromosome == 'XLD':
                    if gender == 'Male' and genotype in ['het', 'hom']:
                        result = 'O'
                    elif gender == 'Female' and genotype == 'hom':
                        result = 'O'
            new_row['OMIM_number'] = {
                'Phenotype': row.Phenotype,
                'OMIM_number': row.OMIM_number if row.OMIM_number != -1 else '',
                '符合條件': result
            }
            new_row['Amelie Max score'] = row.Max_Score
            new_row['Amelie Mean score'] = row.Mean_Score
            

            other_data.append(new_row)

        with open(f'{folder_path}/known_other_variant_result.csv', mode='w', encoding='utf-8-sig', newline='') as csv_file:
            fieldnames = ['Location', 'Gene', 'RS ID', 'MAF', 'Genotype / VAF', 'Evidence', 
                        'Domain', 'Pathogenicity', 'Splicing effect', 'OMIM_number', 
                        'Amelie Max score', 'Amelie Mean score']
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)

            writer.writeheader()
            for row in other_data:
                writer.writerow(row)
        return JsonResponse({'acmg_data': acmg_data, 'other_data': other_data}, safe=False)
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)


@csrf_exempt
def incidental_finding_variant_trio(request):
    if request.method == 'POST':
        finished_jobs = existJobs.jobs.all().filter(status="finished")
        newJobID = globals.global_newJobID
        print(newJobID)
        output_csv_path1 = f'/miRTI/media/patient/{newJobID}/result_table/known_acmg_variant_result.csv'
        output_csv_path2 = f'/miRTI/media/patient/{newJobID}/result_table/known_other_variant_result.csv'
        if os.path.exists(output_csv_path1) and os.path.exists(output_csv_path2):
            data1 = []
            data2 = []

            # 讀取並處理第一份CSV
            with open(output_csv_path1, mode='r', encoding='utf-8-sig') as csv_file1:
                reader1 = csv.DictReader(csv_file1)
                for row in reader1:
                    new_row = {
                        'Location': row['Location'],
                        'Gene': row['Gene'],
                        'RS ID': row['RS ID'],
                        'MAF': eval(row['MAF']),
                        'Genotype / VAF': eval(row['Genotype / VAF']),
                        'Evidence': eval(row['Evidence']),
                        'Domain': row['Domain'],
                        'Pathogenicity': eval(row['Pathogenicity']),
                        'Splicing effect': eval(row['Splicing effect']),
                        'OMIM_number': eval(row['OMIM_number']),
                        'Amelie Max score': row['Amelie Max score'],
                        'Amelie Mean score': row['Amelie Mean score'],
                        'INH': row['INH']
                    }
                    data1.append(new_row)
                    print(data1)
            # 讀取並處理第二份CSV
            with open(output_csv_path2, mode='r', encoding='utf-8-sig') as csv_file2:
                reader2 = csv.DictReader(csv_file2)
                for row in reader2:
                    new_row = {
                        'Location': row['Location'],
                        'Gene': row['Gene'],
                        'RS ID': row['RS ID'],
                        'MAF': eval(row['MAF']),
                        'Genotype / VAF': eval(row['Genotype / VAF']),
                        'Evidence': eval(row['Evidence']),
                        'Domain': row['Domain'],
                        'Pathogenicity': eval(row['Pathogenicity']),
                        'Splicing effect': eval(row['Splicing effect']),
                        'OMIM_number': eval(row['OMIM_number']),
                        'Amelie Max score': row['Amelie Max score'],
                        'Amelie Mean score': row['Amelie Mean score'],
                        'INH': row['INH']
                    }
                    data2.append(new_row)
                    print(data2)
            # 同時返回兩份資料
            return JsonResponse({
                'data1': data1,
                'data2': data2
            }, safe=False)



        first_record = finished_jobs.filter(jobID=newJobID).first()

        if first_record is None:
            return JsonResponse({'error': 'No finished job found with the given job ID'}, status=404)

        select_job = first_record.jobID
        gender=first_record.gender
        print(gender)
        sampleID = finished_jobs.filter(jobID=select_job)[0].subject_id
        fs = FileSystemStorage()
        parm_pickle = os.path.join(fs.location, 'patient', select_job, f'{sampleID}.pickle')
        print("****")

        parameters = load_parameters1(parm_pickle)

        parameters['known_other_variant'] = parameters['known_other_variant'].apply(rearrange_location1, axis=1)
        parameters['known_ACMG_variant'] = parameters['known_ACMG_variant'].apply(rearrange_location1, axis=1)

        parameters = modify_table1(parameters, ['known_other_variant', 'known_ACMG_variant'])

        parameters['here_df_list'] = zip([parameters['known_ACMG_variant'], parameters['known_other_variant']],
                                        ['ACMG variants', 'Other pathogenic variants'])


        acmg_data = []
        for row in parameters['known_ACMG_variant'].itertuples():
            new_row = {}
            new_row['Location'] = f"{row.Chr}:{row.Start}_{row.End}{row.Ref}>{row.Alt}"
            new_row['Gene'] = row.Gene_refGene
            new_row['RS ID'] = row.avsnp150 if row.avsnp150 != '.' else ''
            new_row['MAF'] = {
                'gnomAD': row.AF,
                '1000G': row.AF_1000G,
                'TW Biobank': row.TaiwanBioBank
            }
            new_row['Genotype / VAF'] = {
                'GT': row.GT,
                'VAF': float(row.VAF),
                'AD': row.AD,
                'Otherinfo10': row.Otherinfo10
            }
            new_row['Evidence'] = {
                'Clinvar': '.' if row.clinvar_summary == '.' else row.clinvar_summary,
                'LOVD': '.' if row.LOVD_all_clinical == '.' else row.LOVD_SIG
            }
            new_row['Domain'] = row.Interpro_domain
            new_row['Pathogenicity'] = {
                'Summary': f"({row.deleterious_agreed}/{row.deleterious_tools})",
                'Polyphen2_HVAR': row.Polyphen2_HVAR_pred,
                'SIFT': row.SIFT_pred,
                'VEST3': row.VEST3_score,
                'MutationTaster': row.MutationTaster_pred,
                'MetaSVM': row.MetaSVM_pred,
                'MetaLR': row.MetaLR_pred,
                'CADD': row.CADD_phred,
                'DANN': row.DANN_score
            }
            new_row['Splicing effect'] = {
                'Summary': f"({row.splicing_effect_agreed}/{row.splicing_effect_tools})",
                'dbscsnv ADA score': row.dbscSNV_ADA_SCORE,
                'dbscsnv RF score': row.dbscSNV_RF_SCORE,
                'SPIDEX zscore': row.dpsi_zscore
            }
            
            # new_row['OMIM'] = row.OMIM_number if row.OMIM_number != 'None' else ''
            if row.Phenotype == -1:
                result = 'X'
            else:
                omim_chromosome = row.Phenotype.split('(')[-1].split(')')[0]
                print(omim_chromosome)
                genotype = new_row['Genotype / VAF']['GT']
                print(genotype)
                result = 'X'

                if omim_chromosome in ['AD', 'AR']:
                    if omim_chromosome == 'AD':
                        if genotype in ['hom', 'het']:
                            result = 'O'
                    elif omim_chromosome == 'AR':
                        if genotype == 'hom':
                            result = 'O'
                elif omim_chromosome == 'XLR':
                    if gender == 'Male' and genotype in ['het', 'hom']:
                        result = 'O'
                    elif gender == 'Female' and genotype == 'het':
                        result = 'O'
                elif omim_chromosome == 'XLD':
                    if gender == 'male' and genotype in ['het', 'hom']:
                        result = 'O'
                    elif gender == 'Female' and genotype == 'hom':
                        result = 'O'
            print(result)
            new_row['OMIM_number'] = {
                'Phenotype': row.Phenotype,
                'OMIM_number': row.OMIM_number if row.OMIM_number != -1 else '',
                '符合條件': result
            }
            new_row['Amelie Max score'] = row.Max_Score
            new_row['Amelie Mean score'] = row.Mean_Score
            new_row['INH'] = row.INH

            acmg_data.append(new_row)
        folder_path = f'/miRTI/media/patient/{newJobID}/result_table'

        # 
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            print(f"資料夾 '{folder_path}' 建立成功")
        else:
            print(f"資料夾 '{folder_path}' 已存在，跳過建立")
    
        with open(f'{folder_path}/known_acmg_variant_result.csv', mode='w', encoding='utf-8-sig', newline='') as csv_file:
            fieldnames = ['Location', 'Gene', 'RS ID', 'MAF', 'Genotype / VAF', 'Evidence', 
                        'Domain', 'Pathogenicity', 'Splicing effect', 'OMIM_number', 
                        'Amelie Max score', 'Amelie Mean score', 'INH']
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)

            writer.writeheader()
            for row in acmg_data:
                writer.writerow(row)


        other_data = []
        for row in parameters['known_other_variant'].itertuples():
            new_row = {}
            new_row['Location'] = f"{row.Chr}:{row.Start}_{row.End}{row.Ref}>{row.Alt}"
            new_row['Gene'] = row.Gene_refGene
            new_row['RS ID'] = row.avsnp150 if row.avsnp150 != '.' else ''
            new_row['MAF'] = {
                'gnomAD': row.AF,
                '1000G': row.AF_1000G,
                'TW Biobank': row.TaiwanBioBank
            }
            new_row['Genotype / VAF'] = {
                'GT': row.GT,
                'VAF': float(row.VAF),
                'AD': row.AD,
                'Otherinfo10': row.Otherinfo10
            }
            new_row['Evidence'] = {
                'Clinvar': '.' if row.clinvar_summary == '.' else row.clinvar_summary,
                'LOVD': '.' if row.LOVD_all_clinical == '.' else row.LOVD_SIG
            }
            new_row['Domain'] = row.Interpro_domain
            new_row['Pathogenicity'] = {
                'Summary': f"({row.deleterious_agreed}/{row.deleterious_tools})",
                'Polyphen2_HVAR': row.Polyphen2_HVAR_pred,
                'SIFT': row.SIFT_pred,
                'VEST3': row.VEST3_score,
                'MutationTaster': row.MutationTaster_pred,
                'MetaSVM': row.MetaSVM_pred,
                'MetaLR': row.MetaLR_pred,
                'CADD': row.CADD_phred,
                'DANN': row.DANN_score
            }
            new_row['Splicing effect'] = {
                'Summary': f"({row.splicing_effect_agreed}/{row.splicing_effect_tools})",
                'dbscsnv ADA score': row.dbscSNV_ADA_SCORE,
                'dbscsnv RF score': row.dbscSNV_RF_SCORE,
                'SPIDEX zscore': row.dpsi_zscore
            }
            # new_row['OMIM'] = row.OMIM_number if row.OMIM_number != 'None' else ''
            if row.Phenotype == -1:
                result = 'X'
            else:
                omim_chromosome = row.Phenotype.split('(')[-1].split(')')[0]
                print(omim_chromosome)
                genotype = new_row['Genotype / VAF']['GT']
                print(genotype)
                result = 'X'

                if omim_chromosome in ['AD', 'AR']:
                    if omim_chromosome == 'AD':
                        if genotype in ['hom', 'het']:
                            result = 'O'
                    elif omim_chromosome == 'AR':
                        if genotype == 'hom':
                            result = 'O'
                elif omim_chromosome == 'XLR':
                    if gender == 'male' and genotype in ['het', 'hom']:
                        result = 'O'
                    elif gender == 'Female' and genotype == 'het':
                        result = 'O'
                elif omim_chromosome == 'XLD':
                    if gender == 'Male' and genotype in ['het', 'hom']:
                        result = 'O'
                    elif gender == 'Female' and genotype == 'hom':
                        result = 'O'
            new_row['OMIM_number'] = {
                'Phenotype': row.Phenotype,
                'OMIM_number': row.OMIM_number if row.OMIM_number != -1 else '',
                '符合條件': result
            }
            new_row['Amelie Max score'] = row.Max_Score
            new_row['Amelie Mean score'] = row.Mean_Score
            new_row['INH'] = row.INH

            other_data.append(new_row)

        with open(f'{folder_path}/known_other_variant_result.csv', mode='w', encoding='utf-8-sig', newline='') as csv_file:
            fieldnames = ['Location', 'Gene', 'RS ID', 'MAF', 'Genotype / VAF', 'Evidence', 
                        'Domain', 'Pathogenicity', 'Splicing effect', 'OMIM_number', 
                        'Amelie Max score', 'Amelie Mean score', 'INH']
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)

            writer.writeheader()
            for row in other_data:
                writer.writerow(row)
        return JsonResponse({'acmg_data': acmg_data, 'other_data': other_data}, safe=False)
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)
    

@csrf_exempt
def drug_response_variant(request):
    if request.method == 'POST':
        # 確保 job ID 和其他變量的正確性
        finished_jobs = existJobs.jobs.all().filter(status="finished")
        newJobID = globals.global_newJobID
        print(newJobID)
        output_csv_path = f'/miRTI/media/patient/{newJobID}/result_table/drug_response_demo.csv'
        if os.path.exists(output_csv_path):
            with open(output_csv_path, mode='r', encoding='utf-8-sig') as csv_file:
                reader = csv.DictReader(csv_file)
                data = []

                for row in reader:
                    new_row = {
                        'Location': row['Location'],
                        'Gene': row['Gene'],
                        'RS ID': row['RS ID'],
                        'Drug evidence': row['Drug evidence'],
                        'Chemical': row['Chemical'],
                        'ClinVar': row['ClinVar'],
                    }
                    data.append(new_row)

            return JsonResponse(data, safe=False)

        first_record = finished_jobs.filter(jobID=newJobID).first()

        if first_record is None:
            return JsonResponse({'error': 'No finished job found with the given job ID'}, status=404)

        select_job = first_record.jobID
        gender = first_record.gender

        sampleID = finished_jobs.filter(jobID=select_job)[0].subject_id
        fs = FileSystemStorage()
        parm_pickle = os.path.join(fs.location, 'patient', select_job, f'{sampleID}.pickle')

        # 載入參數
        parameters = load_parameters1(parm_pickle)

        # 修改表格
        parameters['drug_response_demo'] = parameters['drug_response_demo'].apply(rearrange_location1, axis=1)
        parameters = modify_table1(parameters, ['drug_response_demo'])

        # 將修改後的數據寫入 CSV 文件
        csv_filename = 'drug_response_demo.csv'
        csv_filepath = os.path.join(fs.location, 'result_table', csv_filename)

        parameters['drug_response_demo'].to_csv(csv_filepath, index=False, encoding='utf-8-sig')

        # 讀取 CSV 文件內容並轉換為 JSON 格式
        data = []
        with open(csv_filepath, mode='r', encoding='utf-8-sig') as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                new_row = {
                    'Location': f"{row.get('Chr', '')}:{row.get('Start', '')}_{row.get('End', '')}{row.get('Ref', '')}>{row.get('Alt', '')}",
                    'Gene': row.get('Gene_refGene', ''),
                    'RS ID': row.get('avsnp150', ''),
                    'Drug evidence': row.get('response_summary', ''),
                    'Chemical': row.get('Chemicals', ''),
                    'ClinVar': row.get('clinvar_summary', '.')
                }
                data.append(new_row)


        folder_path = f'/miRTI/media/patient/{newJobID}/result_table'
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            print(f"資料夾 '{folder_path}' 建立成功")
        else:
            print(f"資料夾 '{folder_path}' 已存在，跳過建立")

        # 確保所有字段都存在於 data 中，即使它們的值為空
        fieldnames = ['Location', 'Gene', 'RS ID', 'Drug evidence', 'Chemical', 'ClinVar']
        for row in data:
            for field in fieldnames:
                if field not in row:
                    row[field] = ''

        # 將數據寫入 CSV 文件
        output_csv_file = f'{folder_path}/drug_response_variant.csv'
        with open(output_csv_file, mode='w', encoding='utf-8-sig', newline='') as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)

        # 返回 JSON 響應
        return JsonResponse({'data': data, 'message': 'CSV file generated successfully'}, status=200)
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)




@csrf_exempt
def drug_response_variant_trio(request):
    if request.method == 'POST':
        # 確保 job ID 和其他變量的正確性
        finished_jobs = existJobs.jobs.all().filter(status="finished")
        newJobID = globals.global_newJobID
        print(newJobID)
        output_csv_path = f'/miRTI/media/patient/{newJobID}/result_table/drug_response_demo.csv'
        if os.path.exists(output_csv_path):
            with open(output_csv_path, mode='r', encoding='utf-8-sig') as csv_file:
                reader = csv.DictReader(csv_file)
                data = []

                for row in reader:
                    new_row = {
                        'Location': row['Location'],
                        'Gene': row['Gene'],
                        'RS ID': row['RS ID'],
                        'Drug evidence': row['Drug evidence'],
                        'Chemical': row['Chemical'],
                        'ClinVar': row['ClinVar'],
                        'INH': row['INH'],
                    }
                    data.append(new_row)

            return JsonResponse(data, safe=False)

        first_record = finished_jobs.filter(jobID=newJobID).first()

        if first_record is None:
            return JsonResponse({'error': 'No finished job found with the given job ID'}, status=404)

        select_job = first_record.jobID
        gender = first_record.gender

        sampleID = finished_jobs.filter(jobID=select_job)[0].subject_id
        fs = FileSystemStorage()
        parm_pickle = os.path.join(fs.location, 'patient', select_job, f'{sampleID}.pickle')

        # 載入參數
        parameters = load_parameters1(parm_pickle)

        # 修改表格
        parameters['drug_response_demo'] = parameters['drug_response_demo'].apply(rearrange_location1, axis=1)
        parameters = modify_table1(parameters, ['drug_response_demo'])

        # 將修改後的數據寫入 CSV 文件
        csv_filename = 'drug_response_demo.csv'
        csv_filepath = os.path.join(fs.location, 'result_table', csv_filename)

        parameters['drug_response_demo'].to_csv(csv_filepath, index=False, encoding='utf-8-sig')

        # 讀取 CSV 文件內容並轉換為 JSON 格式
        data = []
        with open(csv_filepath, mode='r', encoding='utf-8-sig') as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                new_row = {
                    'Location': f"{row.get('Chr', '')}:{row.get('Start', '')}_{row.get('End', '')}{row.get('Ref', '')}>{row.get('Alt', '')}",
                    'Gene': row.get('Gene_refGene', ''),
                    'RS ID': row.get('avsnp150', ''),
                    'Drug evidence': row.get('response_summary', ''),
                    'Chemical': row.get('Chemicals', ''),
                    'ClinVar': row.get('clinvar_summary', '.'),
                    'INH': row.get('INH', '')
                }
                data.append(new_row)


        folder_path = f'/miRTI/media/patient/{newJobID}/result_table'
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            print(f"資料夾 '{folder_path}' 建立成功")
        else:
            print(f"資料夾 '{folder_path}' 已存在，跳過建立")

        # 確保所有字段都存在於 data 中，即使它們的值為空
        fieldnames = ['Location', 'Gene', 'RS ID', 'Drug evidence', 'Chemical', 'ClinVar', 'INH']
        for row in data:
            for field in fieldnames:
                if field not in row:
                    row[field] = ''

        # 將數據寫入 CSV 文件
        output_csv_file = f'{folder_path}/drug_response_variant.csv'
        with open(output_csv_file, mode='w', encoding='utf-8-sig', newline='') as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)

        # 返回 JSON 響應
        return JsonResponse({'data': data, 'message': 'CSV file generated successfully'}, status=200)
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)
