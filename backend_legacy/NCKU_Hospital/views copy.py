import multiprocessing
import subprocess
import pysam
import multiprocessing as mp
import vcfpy
from Bio import SeqIO
from django.shortcuts import render
from django.shortcuts import render, redirect
from django.utils.html import escapejs
from hw1.prediction_germline.Germline_variants_Predictor import run
# Create your views here.
import os
from datetime import timedelta

# from django.http import HttpResponse
import random
import string
import psycopg2
import requests
from .models import existJobs
from django.core.files.storage import FileSystemStorage
from django.shortcuts import render
from django.http import HttpResponse
from django.core.files.storage import FileSystemStorage
from hw1.preprocessForAvinput_v1 import preprocessor
from hw1.WES_layering_pipeline2_5_2 import WES_layering
import os, gzip
import random
import string
import json
import pickle
import re
from django.shortcuts import render
import os
import random
import string
from django.core.files.storage import FileSystemStorage
import subprocess
import pandas as pd
from django.db import connection
import time
import json
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

from django.core.serializers import serialize
import glob
import pandas as pd
import os
import argparse
import re
from Bio import SeqIO
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord
from typing import List, Tuple, Union
import vcfpy
import subprocess
import json
import shutil
import time
from media.reference.fusionGene.pipeline import *
from cyvcf2 import VCF, Writer
from pathlib import Path
from collections import defaultdict
import json
from django.test import RequestFactory
from .find_db import somatic_result
from .analysis_cosmic import mutisnp_civic,process_cosmic

global_newJobID = None


def run_command(cmd):
    subprocess.run(cmd, shell=True, check=True)




@csrf_exempt
def react_send_page1(request):
    if request.method == 'POST':
        print("success")
        

        data = json.loads(request.body.decode('utf-8')) 
        sampleID = data.get('subject_id', '')  
        syndrome = data.get('name', '')  
        dob = data.get('dob', '')  
        gender = data.get('gender', '')  
        history = data.get('history', '')  

        data_dict = {
            'subject_id': sampleID,
            'name': syndrome,
            'dob': dob,
            'gender': gender,
            'history': history,
        }
        print(data_dict)


        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        global global_newJobID
        newJobID = ''.join(random.sample(string.ascii_letters, 10))
        global_newJobID = newJobID
        folder_path = os.path.join(project_root, 'media', 'patient', newJobID)
        os.makedirs(folder_path, exist_ok=True)

        print(f"newJobID is: {newJobID}")
        request.session['newJobID'] = newJobID
        print(f"newJobID is: {newJobID}")
        print("session keys:", request.session.keys())
        print(newJobID)
        json_file_path = os.path.join(folder_path, f'file.json')
        
 
        print("JSON file name:", f'{sampleID}.json')
        
        # 打印 JSON 檔案內容
        print("JSON file content:", json.dumps(data_dict, ensure_ascii=False, indent=4))
        
        # 將數據寫入 JSON 檔案
        with open(json_file_path, 'w', encoding='utf-8') as json_file:
            json.dump(data_dict, json_file, ensure_ascii=False, indent=4)
        
        # 新增的代碼
        cwd = os.getcwd()
        print('*************************cwd')
        print(cwd)
        
        info_file_path = os.path.join(folder_path, 'info.txt')
        log_file_path = os.path.join(folder_path, 'logFile.txt')
        
        with open(log_file_path, 'w') as logfile:
           pass 

        with open(info_file_path, 'w') as file:
            file.write(f'Subject ID: {sampleID}\n')
            file.write(f'Name: {syndrome}\n')
            file.write(f'Date of Birth: {dob}\n')
            file.write(f'Gender: {gender}\n')
            file.write(f'History/Description: {history}\n')

        
        return JsonResponse({'newJobID': newJobID, 'message': 'JSON file and info.txt created successfully', 'json_file_path': json_file_path, 'info_file_path': info_file_path, 'log_file_path': log_file_path})        
    

    return JsonResponse({'error': 'Invalid request method'}, status=400)

@csrf_exempt
def react_send_page2_trio(request):
    if request.method == 'POST':

        global global_newJobID
        newJobID = global_newJobID
        json_file_path = os.path.join('media', 'patient', newJobID, 'file.json')
        with open(json_file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        sampleID = data.get('subject_id')
        syndrome = data.get('name')
        dob = data.get('dob')
        gender = data.get('gender')
        history = data.get('history')

        # 輸出結果
        print(f"Subject ID: {sampleID}")
        print(f"Name: {syndrome}")
        print(f"DOB: {dob}")
        print(f"Gender: {gender}")
        print(f"History: {history}")

        print('start get file')

         # -------- 1. 取得三個 BAM 檔 --------
        bam_ic_file = request.FILES.get('BAM_ic_file')   # child
        print('bam_ic_file')
        bam_f_file  = request.FILES.get('BAM_f_file')    # father
        print('bam_f_file')
        bam_m_file  = request.FILES.get('BAM_m_file')    # mother
        print('bam_m_file')

        print(newJobID)
        
        if not all([bam_ic_file, bam_f_file, bam_m_file]):
            return JsonResponse({'error': 'Missing one or more BAM files'}, status=400)
        
        # -------- 2. 儲存檔案到專屬目錄 --------
        folder_path = os.path.join('media', 'patient', newJobID)
        os.makedirs(folder_path, exist_ok=True)
        print(f"newJobID is : {newJobID}")
        
        bam_paths = {}                                      # 存絕對路徑
        label_map  = {'ic': 'child', 'f': 'father', 'm': 'mother'}

        for label, bam_file in zip(['ic', 'f', 'm'],
                                   [bam_ic_file, bam_f_file, bam_m_file]):
            rel_path = os.path.join(folder_path, bam_file.name)
            with open(rel_path, 'wb+') as dst:
                for chunk in bam_file.chunks():
                    dst.write(chunk)
            abs_path = os.path.abspath(rel_path)         # 轉絕對路徑
            bam_paths[label] = abs_path
            print(f"Saved {label_map[label]} BAM ➜ {abs_path}")

            # 對應 label（ic, f, m）轉成 sample name
            sample_name_map = {
                'ic': f"{sampleID}",                 # child
                'f':  f"{sampleID}_f",               # father
                'm':  f"{sampleID}_m",               # mother
            }
            new_bam = abs_path.replace('.bam', '_fixed.bam')
            sample_name = sample_name_map[label]

            # 用 GATK/Picard 修正 BAM 的 sample name
            gatk_path = "/miRTI/media/reference/Germline_trio/gatk/gatk-4.5.0.0/gatk"
            subprocess.run([
                gatk_path, "AddOrReplaceReadGroups",
                "-I", abs_path,
                "-O", new_bam,
                "-RGID", "1", "-RGLB", "lib1",
                "-RGPL", "illumina", "-RGPU", "unit1",
                "-RGSM", sample_name
            ], check=True)

            # 更新為 fixed BAM
            bam_paths[label] = new_bam
            print(f"Fixed BAM sample name ➜ {sample_name}")


        # 將三條絕對路徑寫進 JSON（供 page3 直接讀）
        with open(os.path.join(folder_path, "bam_paths.json"), "w") as jf:
            json.dump(bam_paths, jf, indent=2)
        
        resultFile_url = folder_path + "/" + sampleID + "_ann.txt"

        # ✅ 儲存 job 紀錄（假設用 ic 的 gVCF 作為主檔名）
        newJob = existJobs.jobs.create(
            jobID=newJobID,
            subject_id=sampleID,
            name=syndrome,
            dob=dob,
            gender=gender,
            history=history,
            uploadFile_url=bam_paths['ic'],
            resultFile_url=resultFile_url
        )
        print("New job created with the following details:")
        print("Job ID:", newJob.jobID)
        print("Subject ID:", newJob.subject_id)
        print("Name:", newJob.name)
        print("DOB:", newJob.dob)
        print("Gender:", newJob.gender)
        print("History:", newJob.history)
        print("Upload File URL:", newJob.uploadFile_url)
        print("Result File URL:", newJob.resultFile_url)
        

        existJobs.jobs.filter(jobID=newJobID).update(status="running")

        
        return JsonResponse({
            'message': 'Trio gVCF files uploaded and processed successfully',
            'gVCF_ic_path': bam_paths['ic'],
            'gVCF_f_path': bam_paths['f'],
            'gVCF_m_path': bam_paths['m']
        })

    return JsonResponse({'error': 'Invalid request method'}, status=400)


@csrf_exempt
def react_send_page2(request):
    if request.method == 'POST':

        global global_newJobID
        newJobID = global_newJobID
        json_file_path = os.path.join('media', 'patient', newJobID, 'file.json')
        with open(json_file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        sampleID = data.get('subject_id')
        syndrome = data.get('name')
        dob = data.get('dob')
        gender = data.get('gender')
        history = data.get('history')

        # 輸出結果
        print(f"Subject ID: {sampleID}")
        print(f"Name: {syndrome}")
        print(f"DOB: {dob}")
        print(f"Gender: {gender}")
        print(f"History: {history}")






        myfile = request.FILES.get('myfile')
        mybam = request.FILES.get('mybam')
        print(newJobID)
        
        if not myfile:
            return JsonResponse({'error': 'No file uploaded'}, status=400)

        
        
        folder_path = os.path.join('media', 'patient', newJobID)
        os.makedirs(folder_path, exist_ok=True)
        print(f"newJobID is : {newJobID}")
        
        file_path = os.path.join(folder_path, myfile.name)
        with open(file_path, 'wb+') as destination:
            for chunk in myfile.chunks():
                destination.write(chunk)
        if mybam:  # 如果有檔案才處理
            file_bam_path = os.path.join(folder_path, mybam.name)
        # 接著儲存或處理 bam 檔案
            with open(file_bam_path, 'wb+') as destination:
                for chunk in mybam.chunks():
                    destination.write(chunk)
        else:
            print("🔔 沒有上傳 BAM 檔案，跳過處理。")

        print("---------------------this is bam file----------")

        print(file_path)  # media/patient/ILZqTykfeg/22W00407_S2_gpu_HF.vcf
        print(folder_path)  # media/patient/ILZqTykfeg
        uploadFile_url = file_path
        resultFile_url = folder_path + "/" + sampleID + "_ann.txt"
        newJob = existJobs.jobs.create(
            jobID=newJobID,
            subject_id=sampleID,
            name=syndrome,
            dob=dob,
            gender=gender,
            history=history,
            uploadFile_url=uploadFile_url,
            resultFile_url=resultFile_url
            )
        print("New job created with the following details:")
        print("Job ID:", newJob.jobID)
        print("Subject ID:", newJob.subject_id)
        print("Name:", newJob.name)
        print("DOB:", newJob.dob)
        print("Gender:", newJob.gender)
        print("History:", newJob.history)
        print("Upload File URL:", newJob.uploadFile_url)
        print("Result File URL:", newJob.resultFile_url)
        

        vep_result_path = os.path.join('/VEP', 'result', myfile.name)
        os.makedirs(os.path.dirname(vep_result_path), exist_ok=True)
        with open(vep_result_path, 'wb+') as destination:
            for chunk in myfile.chunks():
                destination.write(chunk)
        print('vep_result_path',vep_result_path)  # /VEP/result/22W00407_S2_gpu_HF.vcf

        x = existJobs.jobs.get(jobID=newJobID) 
        existJobs.jobs.filter(jobID=newJobID).update(status="running")

        
        

        # 返回成功信息
        return JsonResponse({
            'message': 'File uploaded and processed successfully',
            'file_path': file_path,

        })
    
    # 返回錯誤信息
    return JsonResponse({'error': 'Invalid request method'}, status=400)


@csrf_exempt
def react_send_page4(request):
    start=time.time()
    global global_newJobID
    newJobID = global_newJobID
    print(newJobID)
    try:
        job = existJobs.jobs.get(jobID=newJobID)
    except existJobs.jobs.DoesNotExist:
        return JsonResponse({'error': 'Job not found'}, status=404)    
    sampleID = job.subject_id
    uploadFile_url =job.uploadFile_url
    resultFile_url = job.resultFile_url
    print(sampleID)
    print(uploadFile_url)
    print(resultFile_url)

    filename_with_ext = os.path.basename(uploadFile_url)  # 這裡得到 '24C00131_main.vcf'

    basename, _ = os.path.splitext(filename_with_ext)  # 這裡得到 '24C00131_main'

    path = os.path.dirname(uploadFile_url)  # 這裡得到 '/miRTI/media/patient/twkGvKMDTx'

    new_uploadFile_url = os.path.join(path, basename)

    print(new_uploadFile_url)

    annovar_path = "/annovar"
    humandb = "/annovar/humandb"
    clinicaldb_path = "/annovar/somatic/clinicaldb/"
    
    

    # Test flatten function
    fasta_file = '/annovar/humandb/ucsc_hg19.fa'
    reference = SeqIO.to_dict(SeqIO.parse(fasta_file, 'fasta'))
    with open(os.path.join(humandb, "annovar_to_approved_symbol.json"), 'r') as file:
        genedict = json.load(file)

    # Test usage
    # input_vcf = '//home/willis/project/mtb/bin/24C00131_main.vcf'
    # Setting essential parameters
    # uploadFile_url = os.path.basename(input_vcf).split('.')[0]
    tmp_output_avinput = new_uploadFile_url + '.output.avinput'
    tmp_annovar = new_uploadFile_url + '_annotate'
    print(tmp_output_avinput)
    print(tmp_annovar)
    # Make ANNOVAR Input format AVINPUT file
    avinputdf = prepareAVINPUT(uploadFile_url, tmp_output_avinput)

    # Run the ANNOVAR program in server 
    annovar_cmd = (
    f"perl {annovar_path}/table_annovar.pl "
    f"{tmp_output_avinput} "
    f"{humandb} "
    f"-buildver hg19 -out {tmp_annovar} -remove "
    f"-protocol refGene,avsnp150,ClinGen_annotation,gnomad211_genome,Taiwan_Biobank,LOVD_all,clinvar_20240407,cosmic90_coding,dbnsfp35a,CIVIC_annotation,OCP_ver2 "
    f"-operation g,f,f,f,f,f,f,f,f,f,f "
    f"-nastring . --thread 16 --otherinfo "
)

    # Check com
    # Check command line for annovar and then run
    print(annovar_cmd)
    subprocess.run(annovar_cmd, shell=True)

    # Reading the result
    #tmp_annovar = "00228512_OCPv1_annotate"
    multianno = pd.read_csv(f"""{tmp_annovar}.hg19_multianno.txt""", sep = '\t', header = 0)
    annovardf = process_annovar_results(multianno, avinputdf, os.path.join(uploadFile_url, uploadFile_url + '_annovar_final.txt'))
    annovardf['Gene'] = annovardf['Gene.refGene'].apply(lambda x: genedict(x) if x in genedict else x)

    # Annotate another clinical database
    CGIdf = annotate_CGI(annovardf, clinicaldb_path)
    Oncodf = annotate_oncoKB(CGIdf, clinicaldb_path)
    predictdf = process_predictions(Oncodf)
    predictdf = predictdf.dropna()
    predictdf.to_csv('/miRTI/media/reference/views/tmp.test.txt', sep = '\t', index=False)
    # Somatic SNV Filtering from annotation predictdf
    actionable_df, heredity_df, COSMIC_df, suspect_df, potential_treatment_df= filter(predictdf)
    actionable_num = len(actionable_df)
    heredity_num = len(heredity_df)
    cosmic_num = len(COSMIC_df)
    suspect_num = len(suspect_df)
    potential_treatment_num=len(potential_treatment_df)

    # Check point usage
    print('------------------------The Number of each section-------------------------')
    print(actionable_num, heredity_num, cosmic_num, suspect_num) 
    print('------------------------actionable-------------------------')
    print(actionable_df)
    print('------------------------Heredity-------------------------')
    print(heredity_df)
    print('------------------------COSMIC-------------------------')
    print(COSMIC_df)
    print('------------------------Suspect-------------------------')
    print(suspect_df)
    print('-----------------------potential_treatment_df-----------')
    print(potential_treatment_df)
    print('------------------------END-------------------------')
    end=time.time()
    execution_time = end - start
    print(f"speed : {execution_time} /second")
# -------------------------------------VEPVEPVEPVEPVEPVEP---------------------------------------------
    print("Start Vep")
    os.environ['vep_db_path'] = '/VEP/database'
    os.environ['ref_fasta_path'] = '/VEP/hg19/'
    vep_db_path = os.getenv('vep_db_path')
    ref_fasta_path = os.getenv('ref_fasta_path')
    print("VEP Database Path:", vep_db_path)
    print("Reference FASTA Path:", ref_fasta_path)
    # 構建 docker 指令




@csrf_exempt
def react_send_page5(request):
    global global_newJobID
    newJobID = 'dpYnGVZyrA'
    print(newJobID)


    uploadFile_name = '24C00131_main.vcf'  # 文件名
    uploadFile_source_path = f'/miRTI/media/patient/{newJobID}/{uploadFile_name}'
    uploadFile_target_path = f'/VEP/newjobid/'
    print(f'VEP::uploadFile_name: {uploadFile_name}')
    print(f'VEP::uploadFile_source_path: {uploadFile_source_path}')
    print(f'VEP::uploadFile_target_path: {uploadFile_target_path}')

    # 確保目標目錄存在	
    os.makedirs(os.path.dirname(uploadFile_target_path), exist_ok=True)

    # 複製文件
    shutil.copy(uploadFile_source_path, uploadFile_target_path)
    print(f'File copied to: {uploadFile_target_path}')


    print('VEP start')
# -------------------------------------VEPVEPVEPVEPVEPVEP---------------------------------------------
    os.environ['vep_db_path'] = '/media/disk2/uuuwei0504/VEP/database/'
    os.environ['ref_fasta_path'] = '/media/disk2/uuuwei0504/VEP/hg19/'
    vep_db_path = os.getenv('vep_db_path')
    ref_fasta_path = os.getenv('ref_fasta_path')
    print("VEP Database Path:", vep_db_path)
    print("Reference FASTA Path:", ref_fasta_path)
    # 構建 docker 指令
    docker_command = [
         'docker', 'run', '--rm',
         '-v', f'/media/disk2/uuuwei0504/VEP:/workdir',
         '-v', f'{vep_db_path}:/opt/vep/.vep/',
         '-v', f'{ref_fasta_path}:/opt/vep/.vep/Ref/',
         'ensemblorg/ensembl-vep:release_112.0',
         'vep', '--offline',
         '-i', f'/workdir/newjobid/{uploadFile_url}',
         '--fasta', 'Ref/ucsc.hg19.fasta',
         '--no_stats', '--hgvs', '--numbers',
         '--biotype', '--canonical', '--symbol',
         '--total_length', '--variant_class',
         '--tab', '--output_file', '/workdir/newjobid/{uploadFile_name}.vep.txt',
         '--force_overwrite', '--fork', '4',
         '--warning_file', '/workdir/result/warnings.log'
     ]

    # # 執行 docker 指令
    subprocess.run(docker_command, check=True)
    print("-------------------------VEP end---------------------")


#------------------------------------
    

import stat

@csrf_exempt
def vep_test_page4(request):
    if request.method == 'POST':
        global global_newJobID
        newJobID = global_newJobID
        print(newJobID)
#-----------------------------------------------------------------------------------
        json_file_path = os.path.join('media', 'patient', newJobID, 'file.json')
        start_time = time.time()
        with open(json_file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        sampleID = data.get('subject_id')
        data = json.loads(request.body.decode('utf-8'))
        MAF_cutoff = data.get('maf_cutoff', '')  
        Min_DP_cutoff = data.get('min_dp_cutoff', '')
        Min_AAF = data.get('min_aaf', '')
        config_name = data.get('configName', '')
        frontendJson = data.get('genePanelList', '')
        diagnosis=data.get('diagnosis','')
        response_data = {
        "subject_id": sampleID,
        "maf_cutoff": MAF_cutoff,
        "min_dp_cutoff": Min_DP_cutoff,
        "min_aaf": Min_AAF,
        "config_name": config_name,
        "gene_panel_list": frontendJson,
        "diagnosis": diagnosis
        }
        existJobs.objects.filter(jobID=newJobID).update(diagnosis=diagnosis)

        
        print(f"maf cutoff is :{MAF_cutoff}")
        try:
            MAF_cutoff = float(MAF_cutoff)
        except ValueError:
            print("錯誤：MAF_cutoff 的值無法轉換為浮點數，請提供有效的數值。")


        json_file_path = f"/miRTI/media/patient/{newJobID}/summary.json"
        with open(json_file_path, 'w', encoding='utf-8') as file:
            json.dump(response_data, file, ensure_ascii=False, indent=4)

#--------------------------------------fusion_result---------------------------------
        #-------------------------讀取資料路徑--------------------------------
        folder_path = f"/miRTI/media/patient/{newJobID}"
        fusion_gene_folder = f'{folder_path}/fusion_gene'
        os.makedirs(fusion_gene_folder, exist_ok=True)
        bam_files = glob.glob(os.path.join(folder_path, "*.bam"))
        if len(bam_files) == 1:
            bam_file = bam_files[0]
            print("找到唯一的 BAM 檔案:", bam_file)
            exons_bed = "/miRTI/media/reference/fusionGene/factera/exons.bed"
            ref_2bit = "/miRTI/media/reference/fusionGene/factera/hg19.2bit"
            #-------------------------產生bai檔----------------------------------
            bai_file = bam_file + ".bai"
            try:
                subprocess.run(["samtools", "index", bam_file,bai_file], check=True)
                print(f"索引建立成功: {bai_file}")
                print('--------------------run factera-----------------')
                run_factera(bam_file, exons_bed, ref_2bit,fusion_gene_folder)
                print('--------------------process_fusion-----------------')
                run_process_fusion(fusion_gene_folder,folder_path)
                remove_duplicate_rows(fusion_gene_folder)
                print('------------------run arriba-------------------')
                run_draw_fusions(fusion_gene_folder)
                
            except subprocess.CalledProcessError:
                print("執行 samtools index 時發生錯誤")
        elif len(bam_files) == 0:
            print("資料夾中沒有 BAM 檔案")
        else:
            print("資料夾中有多個 BAM 檔案，請確認只保留一個")


#-----------------------------------------------------確認檔案位置-------------------------------
        folder_path = f"/miRTI/media/patient/{newJobID}"
        vcf_files = [file for file in os.listdir(folder_path) if file.endswith(".vcf")]

        if vcf_files:
            print(f"找到 VCF 檔案: {vcf_files}")


            for vcf_file in vcf_files:
                uploadFile_url = os.path.join(folder_path, vcf_file)  
                file_name = os.path.basename(uploadFile_url)  # 例如 24C00131_main.vcf
                file_name_without_ext = os.path.splitext(file_name)[0]  # 例如 24C00131_main
                uploadFile_target_path = os.path.join('/VEP/newjobid', newJobID)  # 子目錄路徑
                os.makedirs(uploadFile_target_path, exist_ok=True)  # 創建目錄
                os.chmod(uploadFile_target_path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
                uploadFile_target_file_path = os.path.join(uploadFile_target_path, file_name)
                shutil.copy(uploadFile_url, uploadFile_target_file_path)



                print(f'File copied to: {uploadFile_target_file_path}')
                print(f'file_name : {file_name}')
                print(f'file_name_withouttxt: {file_name_without_ext}')
                print(f'uploadFile_target: {uploadFile_target_path}')
                print('---------------------VEP start-------------')
        else:
            print("該資料夾中沒有 .vcf 檔案")
        job = existJobs.jobs.get(jobID=newJobID)
        sampleID = job.subject_id
        uploadFile_url = job.uploadFile_url
        resultFile_url = job.resultFile_url

        filename_with_ext = os.path.basename(uploadFile_url)
        basename, _ = os.path.splitext(filename_with_ext)
        path = os.path.dirname(uploadFile_url)
        germline = os.path.dirname(uploadFile_url)
        new_uploadFile_url = os.path.join(path, basename)

        annovar_path = "/annovar"
        humandb = "/annovar/humandb"
        clinicaldb_path = "/annovar/somatic/clinicaldb/"

        fasta_file = '/annovar/humandb/ucsc_hg19.fa'
        reference = SeqIO.to_dict(SeqIO.parse(fasta_file, 'fasta'))
        with open(os.path.join(humandb, "annovar_to_approved_symbol.json"), 'r') as file:
            genedict = json.load(file)

        tmp_output_avinput = new_uploadFile_url + '.output.avinput'
        tmp_output_annovar = new_uploadFile_url + '_annovar_final.txt'
        tmp_annovar = new_uploadFile_url + '_annotate'
        tmp_annovar_merge_vep = new_uploadFile_url + '_vep_annovar_merge.csv'

        tmp_germline_prediction = f'{germline}/germline/{filename_with_ext}_germline_prediction.csv'
        existJobs.jobs.filter(jobID=newJobID).update(resultFile_url=tmp_annovar_merge_vep)
        output_csv_file_path = f'{tmp_annovar_merge_vep}'
    # -------------------------------------VEP AND ANNOVAR Merge--------------------------------------------
        run_vep_and_annovar(newJobID, file_name, MAF_cutoff, uploadFile_url,Min_AAF,Min_DP_cutoff)

#------------------------------------------vep_final_merge-----------------------------------------
        end_time = time.time()
        execution_time = end_time - start_time
        print(f"程式執行時間: {execution_time:.5f} 秒")
#-----------------------------------------Germline prediction--------------------------
        run_germline_prediction(newJobID, output_csv_file_path, tmp_germline_prediction, request, filename_with_ext, basename)
#-------------------------------------------MAF_cutoff
        df = pd.read_csv(output_csv_file_path)
        filtered_df = df
        filtered_df.to_csv(output_csv_file_path, index=False)

        print("finally : ",filtered_df.head())
        print("-----------------------------------------------Somatic Pipeline-------------------------------------------------")
        print("-----------------------------------------------Somatic Pipeline-------------------------------------------------")
        print("-----------------------------------------------Somatic Pipeline-------------------------------------------------")
        print("-----------------------------------------------Somatic Pipeline-------------------------------------------------")
        print("-----------------------------------------------Somatic Pipeline-------------------------------------------------")
        print("-----------------------------------------------Somatic Pipeline-------------------------------------------------")
        results = somatic_pipeline(newJobID)
        print(results["mutisnp_civic"])
        print(results["process_cosmic"])
        print(results["somatic_result"])
        print("-----------------------------------------------Somatic Pipeline-------------------------------------------------")
        print("-----------------------------------------------Somatic Pipeline-------------------------------------------------")
        print("-----------------------------------------------Somatic Pipeline-------------------------------------------------")
        print("-----------------------------------------------Somatic Pipeline-------------------------------------------------")

        return JsonResponse(response_data)


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

            if not os.path.exists(csv_file):
                print(f"⚠️ 找不到 CSV: {csv_file}，跳過...")
                continue

            # 1️⃣ 創建表
            create_table_from_csv(csv_file, conn, table_name)

            # 2️⃣ 載入 CSV 到表
            load_csv_to_postgres(csv_file, conn, table_name)

    except Exception as e:
        print(f"❌ PostgreSQL 連線失敗: {e}")
    finally:
        if 'conn' in locals():
            conn.close()
            print("🔌 已關閉 PostgreSQL 連線")


def add_ensambl_variant(csv1_path, csv2_path, output_path):
    print("add_ensambl_variant !")
    df1 = pd.read_csv(csv1_path, encoding='ISO-8859-1')
    df2 = pd.read_csv(csv2_path, encoding='ISO-8859-1')

    # 從 CSV1 中選擇 #Uploaded_variation 和 HGVSp 欄位，並將 HGVSp 重命名為 enasmbl_HGVSp
    df1_selected = df1[['#Uploaded_variation', 'HGVSp']].rename(columns={'HGVSp': 'enasmbl_HGVSp'})
    # 合併 df2 和 df1_selected，保留 df2 的所有資料
    merged_df = pd.merge(df2, df1_selected, on='#Uploaded_variation', how='left')
    # 合併完成後，去除 #Uploaded_variation 欄位的重複資料，只保留第一筆
    merged_df = merged_df.drop_duplicates(subset=['#Uploaded_variation'])
    merged_df.to_csv(output_path, index=False)
    print(f"合併完成，已保存至 {output_path}")




def ensure_directory_exists(path):
    if not os.path.exists(path):
        os.makedirs(path)
def maneselect_and_vep(HGNC_main_path, docker_csv1, output_path):
    df1 = pd.read_csv(HGNC_main_path)
    df2 = pd.read_csv(docker_csv1)
    # 刪除 'MANE_Select_RefSeq_transcript_ID_(supplied_by_NCBI)' 欄位中的缺失值
    df1 = df1.dropna(subset=['MANE_Select_RefSeq_transcript_ID_(supplied_by_NCBI)'])
    # 刪除 'Feature' 欄位中的缺失值
    df2 = df2.dropna(subset=['Feature'])
    # 合併兩個 DataFrame，保留 'Feature' 在 df1 中的變異位點
    merged_df = df2[df2['Feature'].isin(df1['MANE_Select_RefSeq_transcript_ID_(supplied_by_NCBI)'])]
    print(merged_df)
    # 分離重複的 MANE select 資料
    df = merged_df.dropna(subset=['#Uploaded_variation'])
    unique_df = df.drop_duplicates(subset=['#Uploaded_variation'])
    output_dir = os.path.dirname(output_path)
    ensure_directory_exists(output_dir)
    # 將結果保存到 CSV 文件
    unique_df.to_csv(output_path, index=False)
    print(unique_df)


def veptxt_to_csv(txt_vep, csv_vep):
    # 讀取 .txt 文件並過濾掉以 '##' 開頭的註釋行，但保留欄位行
    cleaned_lines = []
    with open(txt_vep, 'r', encoding='utf-8') as file:
        for line in file:
            if not line.startswith('##'):
                cleaned_lines.append(line)

    # 生成臨時清理的文件
    cleaned_file_path = 'cleaned_file.txt'
    with open(cleaned_file_path, 'w', encoding='utf-8') as file:
        file.writelines(cleaned_lines)

    # 讀取清理過的文件並轉換為 .csv 文件
    df_vepfile = pd.read_csv(cleaned_file_path, delimiter='\t', skip_blank_lines=True)
    df_vepfile.to_csv(csv_vep, index=False)

    # 刪除臨時清理的文件
    os.remove(cleaned_file_path)

    # 刪除原始 .txt 文件
    os.remove(txt_vep)
def compare(merge_menaselect_vep, pick_orfer_vep_csv, output_path):
    # 讀取 MANE select 和 VEP 結果 CSV 文件
    df1 = pd.read_csv(merge_menaselect_vep)
    df2 = pd.read_csv(pick_orfer_vep_csv)
    # df2是原本經過pick的資料

    # 然後它們會去比較df1跟df2的資料 誰缺失這樣 df2會是要對照的 然後df1缺少的就是被排除掉的資料 由df2給 找到缺失補回去df1後 就完成mane_select跟--pick的合併版

    # 所以df1需要maneselect做完並排除的資料 就是要經過maneselect_and_vep() 然後另一版是df2是要跑vep 並用--pick來跑得到
    
    df1 = df1.dropna(subset=['#Uploaded_variation'])
    df2 = df2.dropna(subset=['#Uploaded_variation'])

    
    unique_df1 = df1.drop_duplicates(subset=['#Uploaded_variation'])
    unique_df2 = df2.drop_duplicates(subset=['#Uploaded_variation'])

    
    set1 = set(unique_df1['#Uploaded_variation'])
    set2 = set(unique_df2['#Uploaded_variation'])

    
    missing_in_df1 = set2 - set1

    
    missing_in_df1_df = pd.DataFrame(missing_in_df1, columns=['#Uploaded_variation'])

   
    missing_in_df1_full_df = pd.merge(missing_in_df1_df, df2, on='#Uploaded_variation', how='left')

    # 合併 df1 和缺少的變異位點
    updated_df1 = pd.concat([unique_df1, missing_in_df1_full_df], ignore_index=True)
    updated_df1 = updated_df1.drop_duplicates(subset=['#Uploaded_variation'])

    # 將更新後的 DataFrame 保存到 CSV 文件
    updated_df1.to_csv(output_path, index=False)
    print(updated_df1)
    print(f"缺少的變異位點已添加並儲存至 '{output_path}'")

#=============前端hpo id查詢api並返回===============================
@csrf_exempt
def HPO_term(request):
    if request.method == 'GET':
        try:
            # body = json.loads(request.body)
            # hpo_id = body.get('hpo_id', '').strip()
            hpo_id ="HP:0009826"
        except (json.JSONDecodeError, AttributeError):
            return JsonResponse({'error': 'Invalid JSON or missing hpo_id'}, status=400)

        if not hpo_id.startswith('HP:') or len(hpo_id) != 10:
            return JsonResponse({'error': 'Invalid HPO-Term ID format (e.g., HP:0001250)'}, status=400)

        try:
            # 使用正確的 Monarch API 路徑
            api_url = f"https://ontology.jax.org/api/hp/terms/HP%3A0009826"
            response = requests.get(api_url)
            response.raise_for_status()
            data = response.json()

            # 擷取 gene symbols
            gene_list = [
                assoc['object']['label']
                for assoc in data.get('associations', [])
                if assoc.get('object', {}).get('label')
            ]
            return JsonResponse(data, safe=False)
            # return JsonResponse({
            #     'hpo_id': hpo_id,
            #     'term_name': 'Seizure',  # 寫死或之後補查
            #     'gene_list': gene_list
            # })

        except Exception as e:
            return JsonResponse({'error': f'API error: {str(e)}'}, status=500)

    return JsonResponse({'error': 'Only POST method allowed'}, status=405)
#=============前端hpo id查詢api並返回===============================


@csrf_exempt
def react_send_page3(request):
    if request.method == 'POST':
        print("success")
        

         
        # 从全局变量获取 newJobID
        global global_newJobID
        newJobID = global_newJobID
        json_file_path = os.path.join('media', 'patient', newJobID, 'file.json')
        with open(json_file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        sampleID = data.get('subject_id')
        syndrome = data.get('name')
        dob = data.get('dob')
        gender = data.get('gender')
        history = data.get('history')

        # 輸出結果
        print(f"Subject ID: {sampleID}")
        print(f"Name: {syndrome}")
        print(f"DOB: {dob}")
        print(f"Gender: {gender}")
        print(f"History: {history}")


        data = json.loads(request.body.decode('utf-8'))
        MAF_cutoff = data.get('maf_cutoff', '')  
        Min_DP_cutoff = data.get('min_dp_cutoff', '')
        Min_AAF = data.get('min_aaf', '')
                        # filtering = request.POST['filteringOptions']
        config_name = data.get('configName', '')

                        # print(f'Strategy is: {strategy}')
                        # print(f'Review status is: {review_status}')
        print(f'MAF cutoff is : {MAF_cutoff}')
        print(f'Min dp cutoff is : {Min_DP_cutoff}')
        print(f'Min aaf is : {Min_AAF}')
                        # print(f'Filtering options is : {filtering}')
        print(f'Save config as : {config_name}')   

        if not newJobID:
            return JsonResponse({'error': 'Job ID not found'}, status=400)

        
        try:
            job = existJobs.jobs.get(jobID=newJobID)
        except existJobs.jobs.DoesNotExist:
            return JsonResponse({'error': 'Job not found'}, status=404)

        sampleID = job.subject_id
        uploadFile_url = job.uploadFile_url
        resultFile_url = job.resultFile_url
        print(sampleID)
        print(uploadFile_url)
        print(resultFile_url)
        frontendJson = data.get('genePanelList', '')
        response_data = {
        "subject_id": sampleID,
        "maf_cutoff": MAF_cutoff,
        "min_dp_cutoff": Min_DP_cutoff,
        "min_aaf": Min_AAF,
        "gene_panel_list": frontendJson
        }
        # filename_with_ext = os.path.basename(uploadFile_url)  # 這裡得到 '24C00131_main.vcf'
        # VCF_file = f"/miRTI/media/patient/{newJobID}/{filename_with_ext}"
        # resultFile_url_new = "/miRTI/" + resultFile_url
        # print(resultFile_url_new)
        # print(VCF_file)
        json_file_path = f"/miRTI/media/patient/{newJobID}/summary.json"
        with open(json_file_path, 'w', encoding='utf-8') as file:
            json.dump(response_data, file, ensure_ascii=False, indent=4)


        log_file_path = os.path.join('media', 'patient', newJobID, 'logFile.txt')

        # 根据文件类型选择命令
        if uploadFile_url.endswith(".vcf"):
            ann_command = f"python3 /miRTI/annovar_pipeline0_3.py -input {uploadFile_url} -output {resultFile_url}"
        else:
            ann_command = f"python3 /miRTI/hw1/annovar_pipeline0_3.py -input {uploadFile_url} -output {resultFile_url}"

        command = f"nohup {ann_command} > {log_file_path} &"


        # 更新任务状态为 "running"
        existJobs.jobs.filter(jobID=newJobID).update(status="running")

        # 运行外部脚本
        if command:
            os.system(command)
            print("command executed")

        # 通过轮询或其他方式检测任务完成状态（这里使用轮询作为示例）
        if poll_annovar_completion('media/patient/' + newJobID, sampleID):
            print("annovar.py 已经执行完毕。")
            existJobs.jobs.filter(jobID=newJobID).update(status="finished")

            # 更新状态为 finished 后，立即执行 select_job_for_interpretation 的逻辑
            finished_jobs = existJobs.jobs.filter(status="finished")
            print("这是已经完成的工作！")
            print(finished_jobs)
            try:
                select_job = request.session['select_ID']
            except (NameError, KeyError):
                select_job = "none"

            if finished_jobs.exists():
                first_record = finished_jobs.filter(jobID=newJobID).first()
                if first_record:
                    select_job = first_record.jobID
                    print(f'current job is : {select_job}')
                else:
                    print('No job found with the specified jobID.')
                if select_job == "none":
                    parameters = {'finished_jobs': finished_jobs, 'select_ID': select_job}

                else:
                    pickle_exist = check_pickle_exist(select_job)
                    config_list = getConfig(select_job)

                    if pickle_exist:
                        parameters = load_parameters(request)
                        parameters['syndrome'] = first_record.name
                        parameters['pickle_exist'] = pickle_exist
                        parameters['config_list'] = config_list
                    else:
                        parameters = {
                            'finished_jobs': finished_jobs,
                            'select_ID': select_job,
                            'sampleID': first_record.subject_id,
                            'syndrome': first_record.name,
                            'pickle_exist': pickle_exist,
                            'config_list': config_list
                        }


                print(parameters)

                # if request.method == "POST":
                    # btn_load = request.POST.get("btn_load", "False")
                # btn_layer = request.POST.get("btn_layer", "False")
                

                    # print("btn_load :" + btn_load)
                    # print("btn_layer :" + btn_layer)

                    # if btn_load == "True":
                    #     select_config = request.POST['tmpConfig']
                    #     print(f'select config : {select_config}')

                    #     if select_config == 'none':
                    #         for key in ['strategy', 'review_status', 'MAF_cutoff', 'Min_DP_cutoff', 'Min_AAF', 'gene_panel', 'gene_panel_string', 'select_config']:
                    #             parameters.pop(key, None)
                    #         return render(request, 'select_job-test_v2.html', parameters)
                    #     else:
                    #         config = loadConfig(select_job, select_config)
                    #         config['select_config'] = select_config
                    #         parameters.update(config)
                    #         GenePanelListJson = json.dumps({'GenePanelList': parameters['GenePanelList']})
                    #         parameters["GenePanelList"] = escapejs(GenePanelListJson)
                    #         return render(request, 'select_job-test_v2.html', parameters)

                if select_job != 'none':
                        strategy = 'A'
                        review_status = '0'
                        # sampleID = data.get('subject_id', '')  
                        MAF_cutoff = data.get('maf_cutoff', '')  
                        Min_DP_cutoff = data.get('min_dp_cutoff', '')
                        Min_AAF = data.get('min_aaf', '')
                        filtering = 'False'
                        config_name = data.get('configName', '')

                        print(f'Strategy is: {strategy}')
                        # print(f'Review status is: {review_status}')
                        print(f'MAF cutoff is : {MAF_cutoff}')
                        print(f'Min dp cutoff is : {Min_DP_cutoff}')
                        print(f'Min aaf is : {Min_AAF}')
                        # print(f'Filtering options is : {filtering}')
                        print(f'Save config as : {config_name}')
                        if strategy != "Cancer":

                            # 從前端表單獲取json資料
                            frontendJson = data.get('genePanelList', '')
                            print(frontendJson)
                            if(frontendJson==''):
                                print("fuck")
                            frontendJsonContent = frontendJson
                            # type(frontendJsonContent) # dict
                            # print(frontendJsonContent.keys())  # ['HPOterm', 'GenePanelList']
                            
                            # 處理gene panel list
                            aggregateDict = genePanelListProcessing(frontendJsonContent['GenePanelList'])

                            print(aggregateDict)
                            gene_panel = aggregateDict['genes']
                            panelNames = aggregateDict['panelNames']
                            genePanelDataFrame = aggregateDict['result']

                            hpoTermIds = extractHpoIds(panelNames)


                            print("*****************test")
                            print(gene_panel)
                            print("****************************")
                            print(panelNames)
                            print("****************************")
                            print(genePanelDataFrame)
                            print("****************************")
                            print(hpoTermIds)
                            if isinstance(frontendJson, str):
                                try:
                                    frontendJsonContent = frontendJson
                                except json.JSONDecodeError:
                                    # 如果解析失敗，frontendJson 可能已經是一個字典
                                    print("frontendJson 解析失敗，請檢查輸入數據。")
                                    frontendJsonContent = {}
                            elif isinstance(frontendJson, dict):
                                # 如果 frontendJson 已經是一個字典，直接使用它
                                frontendJsonContent = frontendJson
                            else:
                                raise TypeError("Invalid type for JSON content")

                            # 確認 frontendJsonContent 是字典，避免後續操作報錯
                            if not isinstance(frontendJsonContent, dict):
                                raise ValueError("Parsed JSON content is not a dictionary")

                            # 處理 gene panel list
                            aggregateDict = genePanelListProcessing(frontendJsonContent.get('GenePanelList', []))

                            print(aggregateDict)
                            gene_panel = aggregateDict['genes']
                            panelNames = aggregateDict['panelNames']
                            genePanelDataFrame = aggregateDict['result']

                            hpoTermIds = extractHpoIds(panelNames)

                            print("*****************test")
                            print(gene_panel)
                            print("****************************")
                            print(panelNames)
                            print("****************************")
                            print(genePanelDataFrame)
                            print("****************************")
                            print(hpoTermIds)
                            if len(hpoTermIds)!=0:
                                # request Amelie phenotype driven ranking score from API
                                amelieResultDict = requestAmelieAPI(request,hpoTermIds,gene_panel)

                                # post-processing for requested result
                                amelieResultTable = pd.DataFrame({'Genes':amelieResultDict.keys()})
                                amelieResultTable['Max_Score'] = amelieResultTable['Genes'].apply(lambda x: round(max(dict(amelieResultDict[x]).values()),2))
                                amelieResultTable['Mean_Score'] = amelieResultTable['Genes'].apply(lambda x: round(sum(dict(amelieResultDict[x]).values())/len(dict(amelieResultDict[x]).values()),2))
                                amelieResultTable['Number_of_References'] = amelieResultTable['Genes'].apply(lambda x: len(dict(amelieResultDict[x]).values()))
                                amelieResultTable['References_List'] = amelieResultTable['Genes'].apply(lambda x: list(dict(amelieResultDict[x]).keys()))
                                amelieResultTable['Scores_List'] = amelieResultTable['Genes'].apply(lambda x: list(dict(amelieResultDict[x]).values()))

                                # merge result
                                genePanelDataFrame = genePanelDataFrame.merge(amelieResultTable,on='Genes',how='outer').fillna(-1)
                                genePanelDataFrame['Number_of_References'] = genePanelDataFrame['Number_of_References'].to_numpy(int)
                                # hpoTermIds 為空時，新增同樣的欄位並塞空值
                            else:
                                genePanelDataFrame['Max_Score'] = -1
                                genePanelDataFrame['Mean_Score'] = -1
                                genePanelDataFrame['Number_of_References'] = -1
                                genePanelDataFrame['References_List'] = -1
                                genePanelDataFrame['Scores_List'] = -1
                            
                            # 輸出整理完的表格
                            genePanelDataFrame.to_csv('media/patient/'+select_job+'/GenePanelDataFrame.tsv',sep='\t',index=None)

                            # 將新表格塞回去
                            aggregateDict['result'] = genePanelDataFrame

                            #gene_panel = adjust_genePanel(gene_panel_text)
                            print('gene panel is :')
                            print(gene_panel)
                        config_values = [strategy, review_status, MAF_cutoff, Min_DP_cutoff, Min_AAF, filtering]
                        config_keys = ['strategy',  'review_status','MAF_cutoff', 'Min_DP_cutoff', 'Min_AAF','filtering']
                        config = dict(zip(config_keys, config_values))
                        # 將json資料加入config中
                        config.update(frontendJsonContent)
                        print("***********config,select_job,config_name")
                        print(config)
                        print("**********")
                        print(select_job)
                        print("**********")
                        print(config_name)
                        # save config as json
                        try:
                            print("success")
                            min_aaf_value = float(Min_AAF)
                        except ValueError:
                            print("false Min_aaf")
                        

                        # 檢查並轉換 Min_DP_cutoff
                        try:
                            print("success")
                            min_dp_cutoff_value = int(Min_DP_cutoff)
                        except ValueError:
                            print("false Min_DP")
                         

                        saveConfig(config, select_job, config_name)
                        
                        #### load annotated table and genotype table ####
                        finished_job = finished_jobs.filter(jobID=select_job)[0]
                        annotated_file = finished_job.resultFile_url
                        input_file = finished_job.uploadFile_url
                        sampleID = finished_job.subject_id

                        annot_table = pd.read_csv(annotated_file, sep='\t')
                        
                        regex = re.compile('.vcf$')
                        if regex.search(input_file):
                            gt_input_file = regex.sub('_tmp.avinput', input_file)
                            gt_input = pd.read_csv(gt_input_file, sep='\t', header=None, usecols=[0, 1, 2, 3, 4, 5, 6, 7, 9, 14, 16, 17])
                            
                            av_processor = preprocessor(gt_input, min_aaf_value, min_dp_cutoff_value)
                            start_time = time.time()
                            gt_input = av_processor.start_processing()
                            print('Elapse time:' + str(time.time() - start_time))
                        else:
                            gt_input_file = input_file
                            gt_input = pd.read_csv(gt_input_file, sep='\t', header=None)
                            gt_input = gt_input.rename(
                                columns={0: 'Chr', 1: 'Start', 2: 'End', 3: 'Ref', 4: 'Alt', 5: 'GT', 6: 'QUAL', 7: 'DP'})
                            gt_input['VAF'] = 0.5
                            gt_input['AD'] = '250,250'
                        print("*********gt_input_file")
                        print(gt_input_file)
                        
                        if strategy != "Cancer":
                            WES_layer = WES_layering(annotation_table=annot_table,
                                                    genotype_table=gt_input,
                                                    gene_panel=gene_panel,
                                                    MAF_cutoff=MAF_cutoff,
                                                    review_status=review_status,
                                                    phenotypeDrivenRanking=genePanelDataFrame)
                            
                            parameters = WES_layer.layering()
                            print("---------------------------------------------WES_layer END")
                            print(parameters)
                            print("****************parameters\n")
                            print(parameters['known_pheno_variant'])
                            # x=parameters['known_pheno_variant']
                            # x.to_csv('/home/uuuwei0504/下載/VIP_germline-main/VIP/test/known_variants,csv',index=False)
                            print("****************test\n")
                            for tmp_key in ['known_pheno_variant', 'suspect_pheno_variant', 'other_variant',
                                            'two_hit_pheno_variant', 'homo_pheno_variant']:
                                if parameters[tmp_key].shape[0] != 0:
                                    parameters[tmp_key].index = parameters[tmp_key].apply(createVariantIndex, axis=1)
                                    parameters[tmp_key]['checked'] = 'off'
                        else:
                            Somatic_layer = Somatic_layering(annotation_table=annot_table, genotype_table=gt_input,
                                                            MAF_cutoff=MAF_cutoff)
                            tmp_gene_panel = Somatic_layer.load_cancer_associated_genes()['Gene Symbol']
                            gene_panel = [tmp_gene_panel[i] for i in tmp_gene_panel.index]
                            parameters = Somatic_layer.layering()
                        variantIndices = list()
                        for tmp_key in ['known_pheno_variant', 'suspect_pheno_variant', 'other_variant', 'two_hit_pheno_variant',
                                        'homo_pheno_variant']:
                            if parameters[tmp_key].shape[0] != 0:
                                variantIndices = variantIndices + list(parameters[tmp_key].index)
                            # print(aggregateDict)
                        reportIndex = pd.DataFrame(index=pd.unique(variantIndices))
                        reportIndex['report'] = 'off'
                        parameters['reportIndex'] = reportIndex

                        ## count number of variants in each layer and put it into parameter
                        number_of_phenotype_associated_variant = parameters['known_pheno_variant'].shape[0]
                        number_of_incidental_finding_variant = parameters['known_other_variant'].shape[0] + \
                                                            parameters['known_ACMG_variant'].shape[0]
                        number_of_drug_response_variant = parameters['drug_response_variant'].shape[0]
                        number_of_predicted_suspect_variant = parameters['suspect_pheno_variant'].shape[0]
                        number_of_other_variant = parameters['other_variant'].shape[0]

                        parameters['number_of_phenotype_associated_variant'] = number_of_phenotype_associated_variant
                        parameters['number_of_incidental_finding_variant'] = number_of_incidental_finding_variant
                        parameters['number_of_drug_response_variant'] = number_of_drug_response_variant
                        parameters['number_of_predicted_suspect_variant'] = number_of_predicted_suspect_variant
                        parameters['number_of_other_variant'] = number_of_other_variant

                        # other information
                        parameters['gene_panel'] = gene_panel
                        parameters['aggregateDict'] = aggregateDict
                        parameters['maf_cutoff'] = MAF_cutoff
                        parameters['min_aaf'] = Min_AAF
                        parameters['passOnly'] = filtering
                        parameters['min_dp_cutoff'] = Min_DP_cutoff
                        parameters['strategy'] = strategy
                        parameters['review_status'] = review_status

                        # pack these information into pickle file
                        resultFile_path = "media/patient/" + select_job + "/" + sampleID
                        with open(resultFile_path + '.pickle', 'wb') as wf:
                            pickle.dump(parameters, wf)

                        parameters['finished_jobs'] = finished_jobs
                        parameters['select_ID'] = select_job
                        parameters['sampleID'] = sampleID
                        parameters['syndrome'] = finished_jobs.filter(jobID=select_job)[0].name

                        get_summary_excel(parameters, select_job, sampleID)

                        print(parameters)

                        print("page3 finished !")



        return JsonResponse(response_data)
    
    return JsonResponse({'error': 'Invalid request method'}, status=400)


# ====================================================
#===================完整版============================
# ====================================================
@csrf_exempt
def react_send_page3_trio(request):
    # ---------- 0. CORS & method ----------
    if request.method == 'OPTIONS':
        return HttpResponse(status=200)
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=400)

    # ---------- 1. 讀前端參數 ----------
    body          = json.loads(request.body)
    MAF_cutoff    = body.get('maf_cutoff', '')
    Min_DP_cutoff = body.get('min_dp_cutoff', '')
    Min_AAF       = body.get('min_aaf', '')
    frontendJson  = body.get('genePanelList', {})

    
    global global_newJobID
    newJobID = global_newJobID
    if not newJobID:
        return JsonResponse({'error': 'Job ID not found'}, status=400)

    base_dir = os.path.abspath(os.path.join('media', 'patient', newJobID))

    # ---------- 2. Job metadata ----------
    with open(os.path.join(base_dir, 'file.json'), encoding='utf-8') as f:
        info = json.load(f)
    sampleID     = info.get('subject_id', 'Sample')
    child_gender = info.get('gender', 'unknown').lower()
    print("Sample:", sampleID)

    with open(os.path.join(base_dir, "bam_paths.json")) as jf:
        bp = json.load(jf)
    bam_ic, bam_f, bam_m = bp['ic'], bp['f'], bp['m']

    gatk  = "/miRTI/media/reference/Germline_trio/gatk/gatk-4.5.0.0/gatk"
    ref   = pick_reference(bam_ic)

    # ---------- 3. BAM ➜ gVCF ----------
    gvcf_paths = {}

    for label, bam in [('ic', bam_ic), ('f', bam_f), ('m', bam_m)]:
        with pysam.AlignmentFile(bam, "rb") as bamfile:
            alias = bamfile.header["RG"][0]["SM"]  # 從 @RG 取得 BAM 中的 sample name             
        raw_gvcf   = os.path.join(base_dir, f"{alias}.tmp.g.vcf.gz") 
        final_gvcf = os.path.join(base_dir, f"{alias}.g.vcf.gz")     


        # 3-a. index BAM
        if not os.path.exists(bam + ".bai"):
            subprocess.run(["samtools", "index", bam], check=True)


        # 3-b. HaplotypeCaller（**不再帶 --sample-name**） ← 修改
        if not os.path.exists(raw_gvcf):
            subprocess.run([
                gatk, "HaplotypeCaller",
                "-R", ref, "-I", bam,
                "-O", raw_gvcf, "-ERC", "GVCF"
            ], check=True)
        

        # 3-c. 改 gVCF header (bcftools reheader)  ← 新增
        if not os.path.exists(final_gvcf):
            rename_file = os.path.join(base_dir, f"rename_{alias}.txt")
            with open(rename_file, "w") as fh:
                fh.write(f"sample\t{alias}\n")      # sample 改成 alias
            subprocess.run([
                "bcftools", "reheader", "-s", rename_file,
                "-o", final_gvcf, raw_gvcf
            ], check=True)
            subprocess.run(["tabix", "-f", final_gvcf], check=True)

        gvcf_paths[label] = final_gvcf


    ic_gvcf, f_gvcf, m_gvcf = gvcf_paths['ic'], gvcf_paths['f'], gvcf_paths['m']

    # ---------- 4. Joint Genotyping ----------
    joint_vcf = run_joint_genotyping(gatk, ref, ic_gvcf, f_gvcf, m_gvcf, base_dir)

    # ---------- 5. WhatsHap phase ----------
    ped_path  = os.path.join(base_dir, "trio.ped")
    child_id  = sample_id(ic_gvcf)
    father_id = sample_id(f_gvcf)
    mother_id = sample_id(m_gvcf)
    sex_code  = 1 if child_gender.startswith("m") else 2 if child_gender.startswith("f") else 0

    write_ped(child_id, father_id, mother_id, sex_code, ped_path)

    phased_gz = os.path.join(base_dir, "joint_genotyped.phased.vcf.gz")
    if not os.path.exists(phased_gz):
        phased_vcf = phased_gz[:-3]
        subprocess.run(["whatshap", "phase", "--reference", ref,
                        "--ped", ped_path, "-o", phased_vcf,
                        joint_vcf, bam_ic, bam_f, bam_m], check=True)
        subprocess.run(["bgzip", "-f", phased_vcf], check=True)
        subprocess.run(["tabix", "-f", phased_gz], check=True)

    # --- 5-b. multiallelic split & sample reorder ----------------------------
    tmp_split_gz = os.path.join(base_dir, "joint_genotyped.phased.split.tmp.vcf.gz")
    if not os.path.exists(tmp_split_gz):
        subprocess.run([
            "bcftools", "norm", "-m-any", "-Oz",
            "-o", tmp_split_gz, phased_gz
        ], check=True)
        subprocess.run(["tabix", "-f", tmp_split_gz], check=True)

    # ======= ❶ 先把會受影響的下游檔案整批刪掉 =========================
    for f in [
        "joint_genotyped.phased.split.ordered.vcf.gz",
        "joint_genotyped.phased.annot.vcf.gz",
        "child_only.vcf.gz"
    ]:
        fpath = os.path.join(base_dir, f)
        if os.path.exists(fpath):
            os.remove(fpath)
        if os.path.exists(fpath + ".tbi"):
            os.remove(fpath + ".tbi")

    # ======= ❷ 正確寫 sample_order：子、父、母 ===========================
    order_txt = os.path.join(base_dir, "sample_order.txt")
    with open(order_txt, "w") as fh:
        fh.write(f"{child_id}\n{father_id}\n{mother_id}\n")

    split_gz = os.path.join(base_dir, "joint_genotyped.phased.split.ordered.vcf.gz")
    subprocess.run([
        "bcftools", "view",
        "-S", order_txt,          # 真的換欄位
        "--force-samples",
        "-Oz", "-o", split_gz, tmp_split_gz
    ], check=True)
    subprocess.run(["tabix", "-f", split_gz], check=True)

    # ---------------------- 6. Trio inheritance annotation -------------------
    annot_gz = os.path.join(base_dir, "joint_genotyped.phased.annot.vcf.gz")
    tmp_vcf  = annot_gz[:-3]
    annotate_trio_inheritance(split_gz, tmp_vcf, child_gender)
    subprocess.run(["bcftools", "sort", "-Oz", "-o", annot_gz, tmp_vcf], check=True)
    subprocess.run(["tabix", "-f", annot_gz], check=True)


    # ---------------------- 7. VCF → CSV -------------------------------------
    vcf_to_csv(annot_gz, os.path.join(base_dir, "joint_genotyped.phased.annot.csv"))


    # ---------------------- 8. 切子女樣本 & ANNOVAR --------------------------
    child_only_gz = os.path.join(base_dir, "child_only.vcf.gz")
    if not os.path.exists(child_only_gz):
        subprocess.run(["bcftools", "view", "-s", child_id, "-Oz",
                        "-o", child_only_gz, annot_gz], check=True)
        subprocess.run(["tabix", "-f", child_only_gz], check=True)

    # gunzip for ANNOVAR
    vcf4ann = child_only_gz[:-3] if child_only_gz.endswith(".vcf.gz") else child_only_gz
    if child_only_gz.endswith(".vcf.gz") and not os.path.exists(vcf4ann):
        subprocess.run(["gunzip", "-c", child_only_gz], stdout=open(vcf4ann, "wb"), check=True)

    result_txt = os.path.join(base_dir, f"{sampleID}_ann.txt")
    log_path   = os.path.join(base_dir, "logFile.txt")
    ann_cmd    = f"python3 /miRTI/hw1/annovar_pipeline0_3.py -input {vcf4ann} -output {result_txt}"
    subprocess.Popen(f"nohup {ann_cmd} > {log_path} 2>&1 &", shell=True)

    print("ANNOVAR started, waiting for completion...")

    if not poll_annovar_completion(base_dir, sampleID):
        return JsonResponse({"error": "ANNOVAR timeout，請檢查 logFile.txt"}, status=500)
    
    print("ANNOVAR completed.")

    annot_table = pd.read_csv(result_txt, sep="\t")
    if "Otherinfo11" in annot_table.columns:
        annot_table["INH"] = annot_table["Otherinfo11"].str.extract(r"INH=([^;]+)", expand=False).fillna("")

    # ---------------------- 9. Genotype 前處理 -------------------------------
    avinput = re.sub(r".vcf(.gz)?$", "_tmp.avinput", child_only_gz)
    gt_df   = pd.read_csv(avinput, sep="\t", header=None,
                          usecols=[0,1,2,3,4,5,6,7,9,14,16,17])
    gt_df   = preprocessor(gt_df, float(Min_AAF), int(Min_DP_cutoff)).start_processing()

    # ---------------------- 10. Gene panel / Amelie ---------------------------
    panels       = genePanelListProcessing(frontendJson.get("GenePanelList", []))
    gene_panel   = panels["genes"]
    panelNames   = panels["panelNames"]
    genePanelDF  = panels["result"]

    hpo_ids = extractHpoIds(panelNames)
    if hpo_ids:
        amelie = requestAmelieAPI(request, hpo_ids, gene_panel)
        am_df  = pd.DataFrame({"Genes": amelie.keys()})
        am_df["Max_Score"]            = am_df["Genes"].apply(lambda g: round(max(amelie[g].values()), 2))
        am_df["Mean_Score"]           = am_df["Genes"].apply(lambda g: round(sum(amelie[g].values())/len(amelie[g]), 2))
        am_df["Number_of_References"] = am_df["Genes"].apply(lambda g: len(amelie[g]))
        am_df["References_List"]      = am_df["Genes"].apply(lambda g: list(amelie[g].keys()))
        am_df["Scores_List"]          = am_df["Genes"].apply(lambda g: list(amelie[g].values()))
        genePanelDF = (
            genePanelDF.merge(am_df, on="Genes", how="outer")
                       .fillna(-1).astype({"Number_of_References": int})
        )
    else:
        for col in ["Max_Score", "Mean_Score", "Number_of_References", "References_List", "Scores_List"]:
            genePanelDF[col] = -1

    genePanelDF.to_csv(os.path.join(base_dir, f"{sampleID}_GenePanelDataFrame.tsv"), sep="\t", index=False)

    # ---------------------- 11. WES layering ---------------------------------
    wes = WES_layering(annotation_table=annot_table,
                       genotype_table=gt_df,
                       gene_panel=gene_panel,
                       MAF_cutoff=MAF_cutoff,
                       review_status="0",
                       phenotypeDrivenRanking=genePanelDF)
    parameters = wes.layering()

    # ---------------------- 12. 後處理 (沿用第二段) ---------------------------
    aggregateDict = panels
    aggregateDict["result"] = genePanelDF

    for key in [
        "known_pheno_variant", "suspect_pheno_variant",
        "other_variant", "two_hit_pheno_variant", "homo_pheno_variant"
    ]:
        if parameters[key].shape[0]:
            parameters[key].index = parameters[key].apply(createVariantIndex, axis=1)
            parameters[key]["checked"] = "off"

    # reportIndex
    variantIndices = []
    for key in [
        "known_pheno_variant", "suspect_pheno_variant",
        "other_variant", "two_hit_pheno_variant", "homo_pheno_variant"
    ]:
        if parameters[key].shape[0]:
            variantIndices += list(parameters[key].index)
    reportIndex = pd.DataFrame(index=pd.unique(variantIndices))
    reportIndex["report"] = "off"
    parameters["reportIndex"] = reportIndex

    # 層別計數
    parameters["number_of_phenotype_associated_variant"] = parameters["known_pheno_variant"].shape[0]
    parameters["number_of_incidental_finding_variant"]   = (
        parameters.get("known_other_variant", pd.DataFrame()).shape[0] +
        parameters.get("known_ACMG_variant", pd.DataFrame()).shape[0]
    )
    parameters["number_of_drug_response_variant"]        = parameters.get("drug_response_variant", pd.DataFrame()).shape[0]
    parameters["number_of_predicted_suspect_variant"]    = parameters["suspect_pheno_variant"].shape[0]
    parameters["number_of_other_variant"]                = parameters["other_variant"].shape[0]

    # 其餘欄位
    parameters.update({
        "gene_panel"   : gene_panel,
        "aggregateDict": aggregateDict,
        "maf_cutoff"   : MAF_cutoff,
        "min_aaf"      : Min_AAF,
        "min_dp_cutoff": Min_DP_cutoff,
        "passOnly"     : "False",
        "strategy"     : "A",
        "review_status": "0",
    })

    # ---------------------- 13. 序列化 & Excel -------------------------------
    pickle_path = os.path.join(base_dir, f"{sampleID}.pickle")
    with open(pickle_path, "wb") as pf:
        pickle.dump(parameters, pf)

    get_summary_excel(parameters, newJobID, sampleID)

    # ---------------------- 14. 更新 Job 狀態 -------------------------------
    existJobs.jobs.filter(jobID=newJobID).update(status="finished")

    return JsonResponse({"message": "Trio analysis complete"})








def pick_reference(bam_path:str)->str:
    """根據 BAM header 判斷要用哪份 FASTA。"""
    
    REF_B37  = "/miRTI/media/reference/Germline_trio_b37/human_g1k_v37.fasta"
    REF_HG19 = "/miRTI/media/reference/Germline_trio_hg19/hg19.fa"

    with pysam.AlignmentFile(bam_path, "rb") as bam:
        first_ctg = bam.header.references[0]
    return REF_HG19 if first_ctg.startswith("chr") else REF_B37




def sample_id(vcf_path: str, idx: int = 0) -> str:
    """
    讀取 VCF / gVCF 最後欄 sample name
    idx – 第幾個 sample，預設 0
    """
    v = VCF(vcf_path)
    name = v.samples[idx]
    v.close()
    return name

# ────────────────────────────────────────────────
# 工具：寫 Trio PED（6 欄、無標頭）
# ────────────────────────────────────────────────
def write_ped(child_id, father_id, mother_id, sex_code, ped_path):
    fam = "FAM1"
    with open(ped_path, "w") as pf:
        pf.write(f"{fam}\t{father_id}\t0\t0\t1\t0\n")
        pf.write(f"{fam}\t{mother_id}\t0\t0\t2\t0\n")
        pf.write(f"{fam}\t{child_id}\t{father_id}\t{mother_id}\t{sex_code}\t0\n")


def vcf_to_csv(vcf_file: str, csv_file: str):
    """將已加註 INH 的 VCF 轉成 CSV，僅保留必要欄位。"""
    def gcode(gt): a, b = gt; return '' if -1 in (a, b) else f"'{a}/{b}"

    rows = []
    v = VCF(vcf_file)
    for rec in v:
        gts, gb = rec.genotypes, rec.gt_bases
        DP = rec.format("DP") if 'DP' in rec.FORMAT else None
        AD = rec.format("AD") if 'AD' in rec.FORMAT else None
        PS = rec.format("PS") if 'PS' in rec.FORMAT else None

        def f(x, i): return '' if x is None else str(x[i][0])

        rows.append(dict(
            CHROM=rec.CHROM,
            POS=rec.POS,
            REF=rec.REF,
            ALT=",".join(rec.ALT),
            QUAL=rec.QUAL,
            FILTER=rec.FILTER or "PASS",
            INH=rec.INFO.get('INH', ''),
            child_PS=f(PS, 0),
            child_GT=gb[0], child_GT01=gcode(gts[0][:2]),
            child_DP=f(DP, 0), child_AD='' if AD is None else ",".join(map(str, AD[0])),
            father_GT=gb[1], father_GT01=gcode(gts[1][:2]),
            father_DP=f(DP, 1), father_AD='' if AD is None else ",".join(map(str, AD[1])) if AD is not None else '',
            mother_GT=gb[2], mother_GT01=gcode(gts[2][:2]),
            mother_DP=f(DP, 2), mother_AD='' if AD is None else ",".join(map(str, AD[2])) if AD is not None else '',
        ))
    v.close()
    pd.DataFrame(rows).to_csv(csv_file, index=False)
    print(f"✅ VCF → CSV 完成：{csv_file}")


def run_joint_genotyping(gatk_path, reference, gvcf_ic, gvcf_f, gvcf_m, out_dir):
    """CombineGVCFs ➜ GenotypeGVCFs。"""
    combined = os.path.join(out_dir, "combined.g.vcf.gz")
    joint_vcf = os.path.join(out_dir, "joint_genotyped.vcf.gz")

    subprocess.run([
        gatk_path, "CombineGVCFs",
        "-R", reference,
        "--variant", gvcf_ic, "--variant", gvcf_f, "--variant", gvcf_m,
        "-O", combined
    ], check=True)

    subprocess.run([
        gatk_path, "GenotypeGVCFs",
        "-R", reference, "-V", combined, "-O", joint_vcf,
        "--allow-old-rms-mapping-quality-annotation-data"
    ], check=True)

    print("✅ Joint Genotyping:", joint_vcf)
    return joint_vcf



def annotate_trio_inheritance(vcf_in: str, vcf_out: str, gender: str) -> str:
    v = VCF(vcf_in)
    v.add_info_to_header({
        "ID": "INH",
        "Description": ("DE NOVO | INHERITED_PAT | INHERITED_MAT | "
                        "INHERITED | MENDELIAN_ERR | MISSING_GT"),
        "Type": "String", "Number": "1"
    })
    w = Writer(vcf_out, v)

    def is_missing(gt): return -1 in gt or gt == [-1, -1]
    def het(gt): return gt.count(1) == 1
    def hom_alt(gt): return gt == [1, 1]
    def contains_alt(gt): return 1 in gt

    def assign_tag(gt_c, gt_f, gt_m, phased=False):
        if is_missing(gt_c) or (is_missing(gt_f) and is_missing(gt_m)):
            return "MISSING_GT"

        # DE NOVO: child has ALT, both parents REF
        if contains_alt(gt_c) and not contains_alt(gt_f) and not contains_alt(gt_m):
            return "DE NOVO"

        # HOM_ALT child
        if hom_alt(gt_c):
            if hom_alt(gt_f) and hom_alt(gt_m):
                return "INHERITED"
            elif contains_alt(gt_f) and contains_alt(gt_m):
                return "INHERITED"
            elif contains_alt(gt_f):
                return "INHERITED_PAT"
            elif contains_alt(gt_m):
                return "INHERITED_MAT"
            else:
                return "MENDELIAN_ERR"

        # Het child, subset of parents
        if set(gt_c).issubset(set(gt_f) | set(gt_m)):
            if phased and het(gt_c):
                if gt_c[0] == 1 and contains_alt(gt_f):
                    return "INHERITED_PAT"
                elif gt_c[1] == 1 and contains_alt(gt_m):
                    return "INHERITED_MAT"
                else:
                    return "INHERITED"
            return "INHERITED"

        # Single-parent only
        if is_missing(gt_m) and contains_alt(gt_c) and contains_alt(gt_f):
            return "INHERITED_PAT"
        if is_missing(gt_f) and contains_alt(gt_c) and contains_alt(gt_m):
            return "INHERITED_MAT"

        return "MENDELIAN_ERR"

    for rec in v:
        gts = rec.genotypes
        if len(gts) < 3:
            rec.INFO['INH'] = "MISSING_GT"
            w.write_record(rec)
            continue

        gt_c, gt_f, gt_m = gts[0][:2], gts[1][:2], gts[2][:2]
        phased_flag = gts[0][2]  # child GT is phased (True) or not (False)

        ps_val = rec.format("PS")[0][0] if 'PS' in rec.FORMAT else None

        # Use phased info if either phased_flag or PS exists
        tag = assign_tag(gt_c, gt_f, gt_m, phased=phased_flag or ps_val is not None)
        rec.INFO['INH'] = tag
        w.write_record(rec)

    v.close()
    w.close()
    return vcf_out




@csrf_exempt
def react_send_page3_trio_shortcut(request):
    if request.method == 'OPTIONS':
        return HttpResponse(status=200)
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=400)

    # ---------- 1. 前端參數 ----------
    body          = json.loads(request.body)
    MAF_cutoff    = body.get('maf_cutoff', '')
    Min_DP_cutoff = body.get('min_dp_cutoff', '')
    Min_AAF       = body.get('min_aaf', '')
    frontendJson  = body.get('genePanelList', {})

    # ---------- 2. Job 資訊 ----------
    
    newJobID = 'UWXBSzmxPk'
    if not newJobID:
        return JsonResponse({'error': 'Job ID not found'}, status=400)

    base_dir = os.path.abspath(os.path.join('media', 'patient', newJobID))
    with open(os.path.join(base_dir, 'file.json'), encoding='utf-8') as f:
        info = json.load(f)
    sampleID     = info.get('subject_id', 'Sample')
    child_gender = info.get('gender', 'unknown').lower()
    print("Sample:", sampleID)

    # ---------- 2-b. 載入修正後 BAM 路徑 ----------
    with open(os.path.join(base_dir, "bam_paths.json")) as jf:
        bp = json.load(jf)
    bam_ic, bam_f, bam_m = bp['ic'], bp['f'], bp['m']

    

    # ---------- 3. 指定 gVCF 檔案 ----------
    gvcf_paths = {
        'ic': os.path.join(base_dir, f"{sampleID}.g.vcf.gz"),
        'f' : os.path.join(base_dir, f"{sampleID}_f.g.vcf.gz"),
        'm' : os.path.join(base_dir, f"{sampleID}_m.g.vcf.gz")
    }

    gatk = "/miRTI/media/reference/Germline_trio/gatk/gatk-4.5.0.0/gatk"
    ref = pick_reference(bam_ic)  # ✅ 對：傳的是 BAM

    ic_gvcf, f_gvcf, m_gvcf = gvcf_paths['ic'], gvcf_paths['f'], gvcf_paths['m']

    # ---------- 4. Joint Genotyping ----------
    joint_vcf = run_joint_genotyping(gatk, ref, ic_gvcf, f_gvcf, m_gvcf, base_dir)

    # ---------- 5. 產生 PED（子父母 ID）----------
    child_id  = sample_id(ic_gvcf)
    father_id = sample_id(f_gvcf)
    mother_id = sample_id(m_gvcf)
    sex_code  = 1 if child_gender.startswith("m") else 2 if child_gender.startswith("f") else 0
    ped_path  = os.path.join(base_dir, "trio.ped")
    write_ped(child_id, father_id, mother_id, sex_code, ped_path)

    phased_gz = os.path.join(base_dir, "joint_genotyped.phased.vcf.gz")
    if not os.path.exists(phased_gz):
        phased_vcf = phased_gz[:-3]
        subprocess.run(["whatshap", "phase", "--reference", ref,
                        "--ped", ped_path, "-o", phased_vcf,
                        joint_vcf, bam_ic, bam_f, bam_m], check=True)
        subprocess.run(["bgzip", "-f", phased_vcf], check=True)
        subprocess.run(["tabix", "-f", phased_gz], check=True)

    # --- 5-b. multiallelic split & sample reorder ----------------------------
    tmp_split_gz = os.path.join(base_dir, "joint_genotyped.phased.split.tmp.vcf.gz")
    if not os.path.exists(tmp_split_gz):
        subprocess.run([
            "bcftools", "norm", "-m-any", "-Oz",
            "-o", tmp_split_gz, phased_gz
        ], check=True)
        subprocess.run(["tabix", "-f", tmp_split_gz], check=True)

    # ======= ❶ 先把會受影響的下游檔案整批刪掉 =========================
    for f in [
        "joint_genotyped.phased.split.ordered.vcf.gz",
        "joint_genotyped.phased.annot.vcf.gz",
        "child_only.vcf.gz"
    ]:
        fpath = os.path.join(base_dir, f)
        if os.path.exists(fpath):
            os.remove(fpath)
        if os.path.exists(fpath + ".tbi"):
            os.remove(fpath + ".tbi")

    # ======= ❷ 正確寫 sample_order：子、父、母 ===========================
    order_txt = os.path.join(base_dir, "sample_order.txt")
    with open(order_txt, "w") as fh:
        fh.write(f"{child_id}\n{father_id}\n{mother_id}\n")

    split_gz = os.path.join(base_dir, "joint_genotyped.phased.split.ordered.vcf.gz")
    subprocess.run([
        "bcftools", "view",
        "-S", order_txt,          # 真的換欄位
        "--force-samples",
        "-Oz", "-o", split_gz, tmp_split_gz
    ], check=True)
    subprocess.run(["tabix", "-f", split_gz], check=True)

    # ---------------------- 6. Trio inheritance annotation -------------------
    annot_gz = os.path.join(base_dir, "joint_genotyped.phased.annot.vcf.gz")
    tmp_vcf  = annot_gz[:-3]
    annotate_trio_inheritance(split_gz, tmp_vcf, child_gender)
    subprocess.run(["bcftools", "sort", "-Oz", "-o", annot_gz, tmp_vcf], check=True)
    subprocess.run(["tabix", "-f", annot_gz], check=True)


    # ---------------------- 7. VCF → CSV -------------------------------------
    vcf_to_csv(annot_gz, os.path.join(base_dir, "joint_genotyped.phased.annot.csv"))


    # ---------------------- 8. 切子女樣本 & ANNOVAR --------------------------
    child_only_gz = os.path.join(base_dir, "child_only.vcf.gz")
    if not os.path.exists(child_only_gz):
        subprocess.run(["bcftools", "view", "-s", child_id, "-Oz",
                        "-o", child_only_gz, annot_gz], check=True)
        subprocess.run(["tabix", "-f", child_only_gz], check=True)

    # gunzip for ANNOVAR
    vcf4ann = child_only_gz[:-3] if child_only_gz.endswith(".vcf.gz") else child_only_gz
    if child_only_gz.endswith(".vcf.gz") and not os.path.exists(vcf4ann):
        subprocess.run(["gunzip", "-c", child_only_gz], stdout=open(vcf4ann, "wb"), check=True)

    result_txt = os.path.join(base_dir, f"{sampleID}_ann.txt")
    log_path   = os.path.join(base_dir, "logFile.txt")
    ann_cmd    = f"python3 /miRTI/hw1/annovar_pipeline0_3.py -input {vcf4ann} -output {result_txt}"
    subprocess.Popen(f"nohup {ann_cmd} > {log_path} 2>&1 &", shell=True)

    print("ANNOVAR started, waiting for completion...")

    if not poll_annovar_completion(base_dir, sampleID):
        return JsonResponse({"error": "ANNOVAR timeout，請檢查 logFile.txt"}, status=500)
    
    print("ANNOVAR completed.")

    annot_table = pd.read_csv(result_txt, sep="\t")
    if "Otherinfo11" in annot_table.columns:
        annot_table["INH"] = annot_table["Otherinfo11"].str.extract(r"INH=([^;]+)", expand=False).fillna("")

    # ---------------------- 9. Genotype 前處理 -------------------------------
    avinput = re.sub(r".vcf(.gz)?$", "_tmp.avinput", child_only_gz)
    gt_df   = pd.read_csv(avinput, sep="\t", header=None,
                          usecols=[0,1,2,3,4,5,6,7,9,14,16,17])
    gt_df   = preprocessor(gt_df, float(Min_AAF), int(Min_DP_cutoff)).start_processing()

    # ---------------------- 10. Gene panel / Amelie ---------------------------
    panels       = genePanelListProcessing(frontendJson.get("GenePanelList", []))
    gene_panel   = panels["genes"]
    panelNames   = panels["panelNames"]
    genePanelDF  = panels["result"]

    hpo_ids = extractHpoIds(panelNames)
    if hpo_ids:
        amelie = requestAmelieAPI(request, hpo_ids, gene_panel)
        am_df  = pd.DataFrame({"Genes": amelie.keys()})
        am_df["Max_Score"]            = am_df["Genes"].apply(lambda g: round(max(amelie[g].values()), 2))
        am_df["Mean_Score"]           = am_df["Genes"].apply(lambda g: round(sum(amelie[g].values())/len(amelie[g]), 2))
        am_df["Number_of_References"] = am_df["Genes"].apply(lambda g: len(amelie[g]))
        am_df["References_List"]      = am_df["Genes"].apply(lambda g: list(amelie[g].keys()))
        am_df["Scores_List"]          = am_df["Genes"].apply(lambda g: list(amelie[g].values()))
        genePanelDF = (
            genePanelDF.merge(am_df, on="Genes", how="outer")
                       .fillna(-1).astype({"Number_of_References": int})
        )
    else:
        for col in ["Max_Score", "Mean_Score", "Number_of_References", "References_List", "Scores_List"]:
            genePanelDF[col] = -1

    genePanelDF.to_csv(os.path.join(base_dir, f"{sampleID}_GenePanelDataFrame.tsv"), sep="\t", index=False)

    # ---------------------- 11. WES layering ---------------------------------
    wes = WES_layering(annotation_table=annot_table,
                       genotype_table=gt_df,
                       gene_panel=gene_panel,
                       MAF_cutoff=MAF_cutoff,
                       review_status="0",
                       phenotypeDrivenRanking=genePanelDF)
    parameters = wes.layering()

    # ---------------------- 12. 後處理 (沿用第二段) ---------------------------
    aggregateDict = panels
    aggregateDict["result"] = genePanelDF

    for key in [
        "known_pheno_variant", "suspect_pheno_variant",
        "other_variant", "two_hit_pheno_variant", "homo_pheno_variant"
    ]:
        if parameters[key].shape[0]:
            parameters[key].index = parameters[key].apply(createVariantIndex, axis=1)
            parameters[key]["checked"] = "off"

    # reportIndex
    variantIndices = []
    for key in [
        "known_pheno_variant", "suspect_pheno_variant",
        "other_variant", "two_hit_pheno_variant", "homo_pheno_variant"
    ]:
        if parameters[key].shape[0]:
            variantIndices += list(parameters[key].index)
    reportIndex = pd.DataFrame(index=pd.unique(variantIndices))
    reportIndex["report"] = "off"
    parameters["reportIndex"] = reportIndex

    # 層別計數
    parameters["number_of_phenotype_associated_variant"] = parameters["known_pheno_variant"].shape[0]
    parameters["number_of_incidental_finding_variant"]   = (
        parameters.get("known_other_variant", pd.DataFrame()).shape[0] +
        parameters.get("known_ACMG_variant", pd.DataFrame()).shape[0]
    )
    parameters["number_of_drug_response_variant"]        = parameters.get("drug_response_variant", pd.DataFrame()).shape[0]
    parameters["number_of_predicted_suspect_variant"]    = parameters["suspect_pheno_variant"].shape[0]
    parameters["number_of_other_variant"]                = parameters["other_variant"].shape[0]

    # 其餘欄位
    parameters.update({
        "gene_panel"   : gene_panel,
        "aggregateDict": aggregateDict,
        "maf_cutoff"   : MAF_cutoff,
        "min_aaf"      : Min_AAF,
        "min_dp_cutoff": Min_DP_cutoff,
        "passOnly"     : "False",
        "strategy"     : "A",
        "review_status": "0",
    })

    # ---------------------- 13. 序列化 & Excel -------------------------------
    pickle_path = os.path.join(base_dir, f"{sampleID}.pickle")
    with open(pickle_path, "wb") as pf:
        pickle.dump(parameters, pf)

    get_summary_excel(parameters, newJobID, sampleID)

    # ---------------------- 14. 更新 Job 狀態 -------------------------------
    existJobs.jobs.filter(jobID=newJobID).update(status="finished")

    return JsonResponse({"message": "Trio analysis complete"})




  






def api_test(request):
   
    if request.method == 'POST':
        print("success")
        # 先從 request.POST 中獲取所有表單數據
        sampleID = request.POST.get('subject_id', '')  
        syndrome = request.POST.get('name', '')  
        dob = request.POST.get('dob', '')  
        gender = request.POST.get('gender', '')  
        history = request.POST.get('history', '') 
        myfile = request.FILES.get('myfile')
        strategy = request.POST.get('strategyRadioOptions', '')  
        review_status = request.POST.get('evidenceRadioOptions', '')  
        MAF_cutoff = request.POST.get('maf_cutoff', '')  
        Min_DP_cutoff = request.POST.get('min_dp_cutoff', '')  
        Min_AAF = request.POST.get('min_aaf', '')  
        filtering = request.POST.get('filteringOptions', '')  
        config_name = request.POST.get('configName', '')  

        # 在這裡你可以根據需要使用這些數據進行後續的操作
        print('Select job for interpretation :' )
        print('Strategy is:' + strategy)
        print('Review stauts is:' + review_status)
        print('MAF cutoff is :' + MAF_cutoff)
        print('Min dp cutoff is :' + Min_DP_cutoff)
        print('Min aaf is :' + Min_AAF)
        print('Filtering options is :' + filtering)
        print('Save config as :' + config_name)
        
        # allele_frequency = request.POST.get('allele_frequency', '') 
        # panel_name = request.POST.get('panel_name', '') 
        # genes = request.POST.get('genes', '') 
    

        cwd = os.getcwd()
        print('*************************cwd')
        print(cwd)

        newJobID = ''.join(random.sample(string.ascii_letters, 10))
        folder_path = os.path.join('media', 'patient', newJobID)
        os.makedirs(folder_path, exist_ok=True)
        
        file_path = os.path.join(folder_path, 'info.txt')
        
        log_file_path = os.path.join(folder_path, 'logFile.txt')
        with open(log_file_path, 'w') as logfile:
           pass 

        with open(file_path, 'w') as file:
            file.write(f'Subject ID: {sampleID}\n')
            file.write(f'Name: {syndrome}\n')
            file.write(f'Date of Birth: {dob}\n')
            file.write(f'Gender: {gender}\n')
            file.write(f'History/Description: {history}\n')

            # 這些變量需要從前端獲取，否則會引發錯誤
            # file.write('******************************************filter setup page\n')
            # file.write(f'allele_frequency: {allele_frequency}\n')
            # file.write(f'panel_name: {panel_name}\n')
            # file.write(f'genes: {genes}\n')

        myfile = request.FILES.get('myfile')  

        if myfile:
            file_path = os.path.join(folder_path, myfile.name)
            with open(file_path, 'wb') as file:  
                for chunk in myfile.chunks():
                    file.write(chunk)
            print(file_path)  # media/patient/ILZqTykfeg/22W00407_S2_gpu_HF.vcf
            print(folder_path)  # media/patient/ILZqTykfeg
            uploadFile_url = file_path
            resultFile_url = folder_path + "/" + sampleID + "_ann.txt"
            newJob = existJobs.jobs.create(
                jobID=newJobID,
                subject_id=sampleID,
                name=syndrome,
                dob=dob,
                gender=gender,
                history=history,
                uploadFile_url=uploadFile_url,
                resultFile_url=resultFile_url
            )
            x = existJobs.jobs.get(jobID=newJobID)
            subject_id = x.subject_id
            print(subject_id)
            print("end")
            if file_path.endswith(".vcf"):
                print(uploadFile_url)
                print(resultFile_url)
                ann_command = "python3 /miRTI/hw1/annovar_pipeline0_3.py -input " + uploadFile_url + " -output " + resultFile_url
                print(ann_command)
                command = "nohup " + ann_command + ">" + log_file_path + "&"
            else:
                print(uploadFile_url)
                print(resultFile_url)
                ann_command = "python3 /miRTI/hw1/annovar_pipeline0_3.py -input " + uploadFile_url + " -output " + resultFile_url
                print(ann_command)
                command = "nohup " + ann_command + ">" + log_file_path + "&"
            if command:
                os.system(command)
                print("command exist")

            if newJob:
                os.system('nohup sh /home/cadilac/137_share/147_backup/VIP/media/test.sh&')

                grep_PID = "pgrep -fo '" + newJob.jobID + "'"
                myPID = subprocess.check_output(grep_PID, shell=True)
                myPID = int(myPID)

                existJobs.jobs.filter(jobID=newJobID).update(processID=myPID)
                existJobs.jobs.filter(jobID=newJobID).update(status="running")

                if poll_annovar_completion(folder_path, sampleID):
                    print("annovar.py 已經執行完畢。")
                    existJobs.jobs.filter(jobID=newJobID).update(status="finished")

                    # 更新狀態為 finished 後，立即執行 select_job_for_interpretation 的邏輯
                    finished_jobs = existJobs.jobs.filter(status="finished")
                    print("this is finished job!")
                    print(finished_jobs)

                    try:
                        select_job = request.session['select_ID']
                    except NameError:
                        select_job = "none"
                    except KeyError:
                        select_job = "none"
                    first_record = finished_jobs[1]
                    select_job = first_record.jobID

                    print('current job is :' + select_job)

                    if select_job == "none":
                        parameters = {'finished_jobs': finished_jobs, 'select_ID': select_job}
                    else:
                        pickle_exist = check_pickle_exist(select_job)
                        print("work")
                        config_list = getConfig(select_job)

                        if pickle_exist:
                            parameters = load_parameters(request)
                            parameters['syndrome'] = finished_jobs.filter(jobID=select_job)[0].name
                            parameters['pickle_exist'] = pickle_exist
                            parameters['config_list'] = config_list
                        else:
                            parameters = {'finished_jobs': finished_jobs, 'select_ID': select_job,
                                          'sampleID': finished_jobs.filter(jobID=select_job)[0].subject_id,
                                          'syndrome': finished_jobs.filter(jobID=select_job)[0].name,
                                          'pickle_exist': pickle_exist,
                                          'config_list': config_list}
                    print(parameters)

                    if request.method == "POST":
                        btn_load = request.POST.get("btn_load", "False")
                        btn_layer = request.POST.get("btn_layer", "False")

                        print("btn_load :" + btn_load)
                        print("btn_layer :" + btn_layer)

                        if btn_load == "True":
                            print(parameters)
                            select_config = request.POST['tmpConfig']
                            print('select config :' + select_config)

                            if select_config == 'none':
                                for i in ['strategy', 'review_status', 'MAF_cutoff', 'Min_DP_cutoff', 'Min_AAF', 'gene_panel',
                                          'gene_panel_string', 'select_config']:
                                    if (i in parameters):
                                        parameters.pop(i)
                                return render(request, 'select_job-test_v2.html', parameters)
                            else:
                                config = loadConfig(select_job, select_config)
                                config['select_config'] = select_config

                                for x in config.keys():
                                    parameters.update({x: config[x]})
                                    print(parameters[x])

                                GenePanelListJson = json.dumps({'GenePanelList': parameters['GenePanelList']})
                                escaped_json_data = escapejs(GenePanelListJson)

                                parameters.update({"GenePanelList": escaped_json_data})

                                return render(request, 'select_job-test_v2.html', parameters)

                        elif (btn_layer == "True") & (select_job != 'none'):
                            print('Select job for interpretation :' + select_job)

                            strategy = request.POST['strategyRadioOptions']
                            print('Strategy is:' + strategy)

                            review_status = request.POST['evidenceRadioOptions']
                            print('Review stauts is:' + review_status)

                            MAF_cutoff = request.POST['maf_cutoff']
                            print('MAF cutoff is :' + MAF_cutoff)

                            Min_DP_cutoff = request.POST['min_dp_cutoff']
                            print('Min dp cutoff is :' + Min_DP_cutoff)

                            Min_AAF = request.POST['min_aaf']
                            print('Min aaf is :' + Min_AAF)

                            filtering = request.POST['filteringOptions']
                            print('filtering options is :' + filtering)

                            config_name = request.POST['configName']
                            print('Save config as :' + config_name)
def create_patient_table():
    with connection.cursor() as cursor:
        cursor.execute("""
            CREATE TABLE patient (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id VARCHAR(50),
                name VARCHAR(100),
                dob VARCHAR(20),
                gender VARCHAR(10),
                history TEXT,
                jobID VARCHAR(20),
            
            )
        """)
def check_annovar_completion(folder_path, subject_id):
    ann_file_path = os.path.join(folder_path, f"{subject_id}_ann.txt")
    return os.path.exists(ann_file_path)

def argments():
    parser = argparse.ArgumentParser(description="This is the tool to filter variant with vcffiles")
    parser.add_argument('-i', '--input', required=True, help="input your vcf result file")
    parser.add_argument('-d', '--db', required=False, help="input your database file list directory")
    parser.add_argument('-o', '--outdir', required=True, help="input your output directory name")
    args = parser.parse_args()
    return args

## function for implement the genome

def extract_base(fasta_file:dict, chr: str, start: int, end: int) -> str:
    seq_record = fasta_file[chr]
    return str(seq_record.seq[start-1:end])

def flatten_genomic_change(fasta_file:dict, string: str) -> List[Union[str, int]]:
    # SNP
    if '>' in string:
        tmp_string = string.split(':')
        chr = tmp_string[0]
        change_sign = tmp_string[1].index('>')
        ref = tmp_string[1][change_sign-1]
        alt = tmp_string[1][change_sign+1]
        position = int(tmp_string[1][2:-3])
        return [chr, position, position, ref, alt]
    
    # INDEL
    elif re.search(r'del[A-Z]+ins[A-Z]+', string):
        tmp_string = string.split(':')
        chr = tmp_string[0]
        tmp_string = re.split(r'del|ins', tmp_string[1])
        ref = tmp_string[1]
        alt = tmp_string[2]
        tmp_position = re.sub(r'g.', '', tmp_string[0])
        tmp_position = [int(pos) for pos in tmp_position.split('_')]
        return [chr, tmp_position[0], tmp_position[1], ref, alt]

    # delins
    elif 'delins' in string:
        tmp_string = re.split(r':|_|delins', string)
        chr = tmp_string[0]
        start = int(re.sub(r'g.', '', tmp_string[1]))
        end = start if len(tmp_string) != 4 else int(tmp_string[2])
        alt = tmp_string[2] if len(tmp_string) != 4 else tmp_string[3]
        #print(chr, start, end)
        ref = extract_base(fasta_file, chr, start, end)
        return [chr, start, end, ref, alt]

    # del or ins
    elif 'del' in string or 'ins' in string:
        tmp_string = string.split(':')
        chr = tmp_string[0]
        change_sign = 'del' if 'del' in tmp_string[1] else 'ins'
        tmp_string = re.split(change_sign, tmp_string[1])
        
        if change_sign == 'del':
            ref = tmp_string[1]
            alt = '-'
            # bug
            tmp_position = re.sub(r'g.', '', tmp_string[0]).split('_')
            start = int(tmp_position[0])
            if len(tmp_position) > 1:
                end = int(tmp_position[1])
            else:
                end = int(tmp_position[0])
            if re.search(r'\d+', ref):
                ref = extract_base(fasta_file, chr, start, end)
            end = start + len(ref) - 1
            return [chr, start, end, ref, alt]
        else:
            ref = '-'
            alt = tmp_string[1]
            tmp_position = int(re.sub(r'g.', '', tmp_string[0]))
            return [chr, tmp_position, tmp_position, ref, alt]
    # duplication
    elif 'dup' in string:
        tmp_string = re.split(r'dup|_|:', string)
        chr = tmp_string[0]
        tmp_position = int(re.sub(r'g.', '', tmp_string[1])) - 1
        ref = '-'
        alt = tmp_string[-1]
        return [chr, tmp_position, tmp_position, ref, alt]
    
    else:
        print(f"error in {string}")
        return [None] * 5

def left_trim(ref: str, alt: str) -> dict:
    ref_seq = list(ref)
    alt_seq = list(alt)
    stop = 0
    for j in range(min(len(ref_seq), len(alt_seq))):
        if ref_seq[j] == alt_seq[j]:
            stop = j + 1
        else:
            break
    
    trim_ref = ref[stop:]
    trim_alt = alt[stop:]
    trim_length = stop
    return {"trim_ref": trim_ref, "trim_alt": trim_alt, "trim_length": trim_length}

def extract_transvar(arg: List[str]) -> List[dict]:
    header = arg[0].split('\t')
    context = arg[1:]
    result = [dict(zip(header, line.split('\t'))) for line in context]
    return result

## run ANNOVAR

def decompose_multiallelic(row):
    results = []
    i = 0
    for allele in row['ALT']:
        alt_allele = allele.value
        new_row = row.copy()
        new_row['ALT'] = alt_allele
        new_row['AF'] = row['AF'][i]
        new_row['FAO'] = row['FAO'][i]
        results.append(new_row)
        i +=1
    return results

def normalize_variant(row):
    global reference
    # INDEL case
    if len(row['REF']) != 1 or len(row['ALT']) != 1:
        transvar_input = f"{row['CHROM']}:{row['POS']}_{row['POS']}{row['REF']}>{row['ALT']}"
        transvar_result = subprocess.run(f"transvar ganno -i \"{transvar_input}\" --refseq", shell=True, capture_output=True, text=True).stdout
        if not transvar_result.strip() or transvar_result.strip() == "input\ttranscript\tgene\tstrand\tcoordinates(gDNA/cDNA/protein)\tregion\tinfo":
            return row
        else:
            if "left_align_gDNA" in transvar_result:
                tmp_str = re.search(r"left_align_gDNA=([^;]+);", transvar_result).group(1)
                chr = re.search(r"(\w+):", transvar_result).group(1)
                flattened = flatten_genomic_change(reference, f"{chr}:{tmp_str}")
                row["CHROM"], row["POS"], row["END"], row["REF"], row["ALT"] = flattened
            else:
                tmp_str = re.search(r"(\w+):(\w+)", transvar_result).group(2)
                if pd.isna(tmp_str):
                    return row
                else:
                    flattened = flatten_genomic_change(reference, tmp_str)
                    row["CHROM"], row["POS"], row["END"], row["REF"], row["ALT"] = flattened
    return row


from multiprocessing import Pool, cpu_count
import pandas as pd
import vcfpy


def prepareAVINPUT(input_vcf, tmp_output_avinput):
    global reference
    # input_vcf = '/home/cadilac/137_share/147_backup/interpretation/00228512_OCPv1.vcf'
    reader = vcfpy.Reader.from_path(input_vcf)
    records = [record for record in reader if record.FILTER == ['PASS']]
    records = [record for record in records if len(record.ALT) > 0 and record.ALT[0] != vcfpy.SymbolicAllele('CNV')]
    records = [record for record in records if not any(isinstance(alt, vcfpy.BreakEnd) for alt in record.ALT)]
    print("Filtered records:", len(records))

    # Use multiprocessing to process records in parallel
    with Pool(min(5, cpu_count())) as pool:
        vcf_data = pool.map(process_record, records)

    # Flatten the list of lists
    vcf_data = [item for sublist in vcf_data for item in sublist]

    # extract to tidy
    vcf_df = pd.DataFrame(vcf_data)
    print("VCF DataFrame:")
    print(vcf_df)

    # genotype
    sub_vcf = vcf_df[vcf_df['GT'] != '0/0']
    print("Filtered genotype (not 0/0):")
    print(sub_vcf)

    # Use multiprocessing to decompose multiallelic rows in parallel
    with Pool(min(5, cpu_count())) as pool:
        decomposed_vcf = pool.map(decompose_row, [row for _, row in sub_vcf.iterrows()])

    # Flatten the list of lists
    decomposed_vcf = [item for sublist in decomposed_vcf for item in sublist]

    decomposed_vcf_df = pd.DataFrame(decomposed_vcf)
    print("Decomposed VCF DataFrame:")
    print(decomposed_vcf_df)

    # Filter VF if it exists
    if 'VF' in decomposed_vcf_df.columns:
        # Use vectorized operation instead of apply
        decomposed_vcf_df['VF'] = decomposed_vcf_df['VF'].apply(lambda x: x[0] if isinstance(x, list) and len(x) > 0 else x)
        decomposed_vcf_df = decomposed_vcf_df[decomposed_vcf_df['VF'] != 0]
        print("Filtered VF != 0:")
        print(decomposed_vcf_df)
    else:
        print("Column 'VF' not found in DataFrame, skipping VF filter.")

    # Filter FDP == 'NA'
    decomposed_vcf_df['DP'] = pd.to_numeric(decomposed_vcf_df['DP'], errors='coerce')
    decomposed_vcf_df = decomposed_vcf_df.dropna(subset=['DP'])
    print("Filtered DP != 'NA':")
    print(decomposed_vcf_df)

    # Process FAO and FDP
    if 'AD' in decomposed_vcf_df.columns:
        decomposed_vcf_df['AD'] = decomposed_vcf_df['AD'].apply(lambda x: x[0] if isinstance(x, list) and len(x) > 0 else x)
        if 'VF' in decomposed_vcf_df.columns:
            decomposed_vcf_df['VF'] = decomposed_vcf_df['VF'].apply(lambda x: x[0] if isinstance(x, list) and len(x) > 0 else x)
            # Replace '.' with NaN for conversion
            decomposed_vcf_df['DP'] = decomposed_vcf_df['DP'].replace('.', pd.NA)
            decomposed_vcf_df['VF'] = decomposed_vcf_df['VF'].replace('.', pd.NA)
            decomposed_vcf_df.loc[decomposed_vcf_df['AD'].isna(), 'AD'] = (pd.to_numeric(decomposed_vcf_df['DP'], errors='coerce') * pd.to_numeric(decomposed_vcf_df['VF'], errors='coerce')).round()
        print("Processed FAO and FDP:")
        print(decomposed_vcf_df)

    else:
        print("Column 'AD' not found in DataFrame.")

    # Process END
    decomposed_vcf_df['END'] = pd.to_numeric(decomposed_vcf_df['POS'], errors='coerce').fillna(0).astype(int).astype(str)
    existing_columns = [col for col in ["CHROM", "POS", "END", "REF", "ALT", "GT", "QUAL", "DP", "VF", "AD"] if col in decomposed_vcf_df.columns]
    decomposed_vcf_df = decomposed_vcf_df[existing_columns]
    column_mapping = {
        "CHROM": "CHROM",
        "POS": "POS",
        "END": "END",
        "REF": "REF",
        "ALT": "ALT",
        "GT": "GT",
        "QUAL": "QUAL",
        "DP": "FDP",
        "VF": "AF",
        "AD": "FAO"
    }
    decomposed_vcf_df = decomposed_vcf_df.rename(columns={k: v for k, v in column_mapping.items() if k in decomposed_vcf_df.columns})

    if 'POS' in decomposed_vcf_df.columns:
        decomposed_vcf_df['POS'] = pd.to_numeric(decomposed_vcf_df['POS'], errors='coerce').fillna(0).astype(int).astype(str)
    if 'END' in decomposed_vcf_df.columns:
        decomposed_vcf_df['END'] = pd.to_numeric(decomposed_vcf_df['END'], errors='coerce').fillna(0).astype(int).astype(str)

    # normalization (vectorized approach to improve performance)
    decomposed_vcf_df = decomposed_vcf_df.apply(lambda row: normalize_variant(row), axis=1)

    # update genotype to het and hom
    if 'GT' in decomposed_vcf_df.columns:
        decomposed_vcf_df['GT'] = decomposed_vcf_df['GT'].apply(lambda x: 'het' if x == '0/1' else 'hom')

    decomposed_vcf_df.dropna(subset=['CHROM', 'POS', 'REF', 'ALT'], inplace=True)

    # Fill missing columns with default values to ensure AVINPUT file creation
    for col in ['CHROM', 'POS', 'END', 'REF', 'ALT', 'GT', 'QUAL', 'FDP', 'AF', 'FAO']:
        if col not in decomposed_vcf_df.columns:
            decomposed_vcf_df[col] = '.'  # Use '.' as the default value

    # output
    decomposed_vcf_df = decomposed_vcf_df[['CHROM', 'POS', 'END', 'REF', 'ALT', 'GT', 'QUAL', 'FDP', 'AF', 'FAO']]
    decomposed_vcf_df.to_csv(tmp_output_avinput, sep='\t', index=False, header=False)
    
    # Check if AVINPUT file exists before running ANNOVAR
    if not os.path.exists(tmp_output_avinput):
        raise FileNotFoundError(f"AVINPUT file not found: {tmp_output_avinput}")

    return decomposed_vcf_df


def process_record(record):
    vcf_data = []
    info_dict = {
        'CHROM': record.CHROM,
        'POS': record.POS,
        'ID': record.ID,
        'REF': record.REF,
        'ALT': record.ALT,
        'QUAL': record.QUAL,
        'FILTER': record.FILTER,
    }
    info_dict.update(record.INFO)
    for call in record.calls:
        sample_dict = call.data
        sample_dict.update(info_dict)
        vcf_data.append(sample_dict)
    return vcf_data


def decompose_row(row):
    decomposed_vcf = []
    if len(row['ALT']) > 2:
        decomposed_vcf.extend(decompose_multiallelic(row))
    else:
        row['ALT'] = row['ALT'][0].value
        decomposed_vcf.append(row)
    return decomposed_vcf



# annotation

def annotate_CGI(target, db_path):
    if any(target.columns.str.contains("CGI_annotation")):
        target = target.loc[:, ~target.columns.str.contains("CGI_annotation")]

    CGI_with_position = pd.read_csv(os.path.join(db_path,"hg19_CGI_with_pos_20200115.txt"), sep="\t", header = 0)
    CGI_without_position = pd.read_csv(os.path.join(db_path,"hg19_CGI_without_pos_20200115.txt"), sep="\t", header = 0)

    target = pd.merge(target, CGI_with_position, how='left', left_on=target.columns[:5].tolist(), right_on=CGI_with_position.columns[:5].tolist())
    target['CGI_annotation'] = target['CGI_annotation'].fillna(".")

    # Annotate based on CGI_without_position
    for i, row in CGI_without_position.iterrows():
        tmp_gene = row['Hugo_symbol']
        tmp_mut = row['Biomarker']

        if tmp_mut == "Truncating Mutations":
            ind = target[(target['Gene.refGene'] == tmp_gene) & (target['ExonicFunc.refGene'] == "stopgain")].index
            if len(ind) != 0:
                target.loc[ind, 'CGI_annotation'] = row['CGI_annotation']
        else:
            tmp_mut_split = tmp_mut.split()
            exon = f"{row['RefSeq']}:exon{int(tmp_mut_split[2])}"
            state = tmp_mut_split[3]

            if re.search("(I|i)nsertion", state):
                ind = target[(target['AAChange.refGene'].str.contains(exon)) & (target['ExonicFunc.refGene'].str.contains("insertion"))].index
                if len(ind) != 0:
                    target.loc[ind, 'CGI_annotation'] = row['CGI_annotation']
            elif re.search("(D|d)eletion", state):
                ind = target[(target['AAChange.refGene'].str.contains(exon)) & (target['ExonicFunc.refGene'].str.contains("deletion"))].index
                if len(ind) != 0:
                    target.loc[ind, 'CGI_annotation'] = row['CGI_annotation']
            elif re.search("splice", state):
                ind = target[(target['AAChange.refGene'].str.contains(exon)) & (target['Func.refGene'].str.contains("splicing"))].index
                if len(ind) != 0:
                    target.loc[ind, 'CGI_annotation'] = row['CGI_annotation']
    return target


def annotate_oncoKB(target, db_path):
    if any(target.columns.str.contains("oncoKB_annotation")):
        target = target.loc[:, ~target.columns.str.contains("oncoKB_annotation")]
    
    oncoKB_with_position = pd.read_csv(os.path.join(db_path, "hg19_oncoKB_with_position_20200110.txt"), sep="\t", header = 0)
    oncoKB_without_position = pd.read_csv(os.path.join(db_path, "hg19_oncoKB_without_position_20200110.txt"), sep="\t", header = 0)
    
    target = target.merge(oncoKB_with_position, left_on=target.columns[:5].tolist(), right_on=oncoKB_with_position.columns[:5].tolist(), how='left')
    target['oncoKB_annotation'] = target['oncoKB_annotation'].fillna('.')
    
    # Annotate oncoKB_without_position
    for i, row in oncoKB_without_position.iterrows():
        tmp_gene = row['Hugo Symbol']
        tmp_mut = row['Alteration']
        
        if tmp_mut == "Truncating Mutations":
            ind = target[(target['Gene.refGene'] == tmp_gene) & (target['ExonicFunc.refGene'] == "stopgain")].index
            if not ind.empty:
                target.loc[ind, 'oncoKB_annotation'] = row['oncoKB_annotation']
        else:
            tmp_mut_split = tmp_mut.split()
            exon = f"{row['RefSeq']}:exon{int(tmp_mut_split[1])}"
            state = tmp_mut_split[2]
            
            if re.search(r"(I|i)nsertion", state):
                ind = target[target['AAChange.refGene'].str.contains(exon, na=False) & target['ExonicFunc.refGene'].str.contains("insertion", na=False)].index
                if not ind.empty:
                    target.loc[ind, 'oncoKB_annotation'] = row['oncoKB_annotation']
            elif re.search(r"(D|d)eletion", state):
                ind = target[target['AAChange.refGene'].str.contains(exon, na=False) & target['ExonicFunc.refGene'].str.contains("deletion", na=False)].index
                if not ind.empty:
                    target.loc[ind, 'oncoKB_annotation'] = row['oncoKB_annotation']
            elif re.search(r"splice", state, re.IGNORECASE):
                ind = target[target['AAChange.refGene'].str.contains(exon, na=False) & target['Func.refGene'].str.contains("splicing", na=False)].index
                if not ind.empty:
                    target.loc[ind, 'oncoKB_annotation'] = row['oncoKB_annotation']
    return target

def process_predictions(target):
    # scoring
    def calculate_pre_sum(row):
        values = row.values
        if (values == ".").sum() == 5:
            return "Un_predict"
        else:
            return (values == "D").sum() / (values != ".").sum()
    
    prediction_tools = ["Polyphen2_HVAR_pred", "MetaSVM_pred", "CADD_phred", "VEST3_score", "MetaLR_pred"]
    test1 = target[prediction_tools].copy()
    test1["CADD_phred"] = test1["CADD_phred"].apply(lambda x: "T" if x == "." else ("D" if float(x) > 20 else "T"))
    
    # Polyphen2_HVAR_pred
    test1["Polyphen2_HVAR_pred"] = test1["Polyphen2_HVAR_pred"].replace({"B": "T", "P": "D"})
    
    # VEST3_score
    test1["VEST3_score"] = test1["VEST3_score"].apply(lambda x: "T" if x == "." else ("D" if float(x) > 0.5 else "T"))
    test1["pre_sum"] = test1.apply(calculate_pre_sum, axis=1)
    
    # merge
    target = target.copy()
    target["summarized_prediction"] = test1["pre_sum"]
    return target

# Merge AVINPUT and ANNOVAR result
def process_annovar_results(target, tmp_av, output):

    print(tmp_av['AF'])

    target['mergeidx'] = target.apply(lambda row: f"{row['Chr']}:{row['Start']}-{row['End']}:{row['Ref']}>{row['Alt']}", axis=1)

    if 'AF' in target.columns:
        target['AF'] = target['AF'].replace('.', 0).astype(float)
    
    print(tmp_av['AF'])
    # Got the VAF, FAO and DP   
    if tmp_av.shape[1] == 5:
        tmp_av.columns = ["Chr", "Start", "End", "Ref", "Alt"]
        tmp_av['GT'] = "het"
        tmp_av['QUAL'] = 1000
        tmp_av['DP'] = 2000
        tmp_av['VAF'] = 0.5
        tmp_av['FAO'] = 1000
        if not tmp_av.iloc[0]['Chr'].startswith('chr'):
            if tmp_av.iloc[0]['Chr'] in map(str, range(1, 23)) + ['X', 'Y']:
                tmp_av['Chr'] = 'chr' + tmp_av['Chr']
            else:
                tmp_av = tmp_av.iloc[1:]
    
    tmp_av.columns = ["Chr", "Start", "End", "Ref", "Alt", "GT", "QUAL", "DP", "VAF", "FAO"]
    tmp_av['mergeidx'] = tmp_av.apply(lambda row: f"{row['Chr']}:{row['Start']}-{row['End']}:{row['Ref']}>{row['Alt']}", axis=1)

    # merge
    tmp_result = pd.merge(target, tmp_av[["VAF", "DP", "FAO","mergeidx"]], left_on=["mergeidx"], right_on=["mergeidx"], how='outer')
    tmp_result.to_csv(output, sep='\t', index=False)
    return tmp_result
    


# Filter
def filter_biobank_af(x):
    if x == '.':
        return 0
    else:
        biobank_af = x.split('|')[2]
        AF = biobank_af[3:]
        return AF
    
def filter(source_df,Min_AAF,Maf_cutoff):
    # ------- Actionable ---------
    # Rule: any drugs in clinical database, oncoKB, COSMIC, CIVIC, MyCancerGenome, CGI
    actionable_df = source_df[~source_df['oncoKB_annotation'].isin(['.']) | ~source_df['CGI_annotation'].isin(['.']) | ~source_df['CIVIC_annotation'].isin(['.'])]
    print("---------------this is actionable_df--------------")
    print(actionable_df)
    # ------- Filter ---------
    print("------------------------------------this is before population filtering df")
    print(source_df)
    source_df['AF'] = source_df['AF'].apply(lambda x: 0 if x == '.' else x)
    source_df['AF'] = pd.to_numeric(source_df['AF'], errors='coerce')
    tmp_df = source_df[source_df['AF'] <= Maf_cutoff]
    # Biobank AF <= 0.01
    tmp_df['biobank_af'] = tmp_df['TaiwanBioBank'].apply(filter_biobank_af)
    df = tmp_df[tmp_df['biobank_af'].astype(float) <= Maf_cutoff]
    df = df.drop(columns=['biobank_af'])
    df_population = df
    print("----------------------------------this is after filtering population df")
    print(df)
    # Exonic

    func_list = ['exonic', 'splicing', 'exonic;splicing']
    df = df[df['Func.refGene'].isin(func_list)]

    # Nonsynonymous
    filter_df = df[~df['ExonicFunc.refGene'].isin(['synonymous SNV'])]
    df_function=filter_df
    print("---------------------------------this is after functional filtering df -----------------------")
    print(filter_df)

    #===============potential treatment=====================
    potential_treatment_df=filter_df
    potential_treatment_df['VAF']=pd.to_numeric(potential_treatment_df['VAF'], errors='coerce')
    potential_treatment_df = potential_treatment_df[(potential_treatment_df['VAF'] >= 0.05) & (potential_treatment_df['VAF'] <= 0.5)]
    potential_treatment_df = potential_treatment_df[~potential_treatment_df['cosmic90_coding'].isin(['.'])]
    print("-------------------------this is potential_treatment_df ")
    print(potential_treatment_df)
    #===============potential treatment=====================
    # ----- Heredity -------
    tmp_heredity_df = filter_df[(filter_df['CLNREVSTAT'].isin(['reviewed_by_expert_panel']) &
                                 filter_df['CLNSIG'].isin(['Pathogenic', 'Likely_pathogenic'])) |
                                (filter_df['LOVD_all_clinical'].str.contains('pathogenic') &
                                 (~filter_df['LOVD_all_clinical'].str.contains('benign')) &
                                 (~filter_df['LOVD_all_clinical'].str.contains('VUS'))) |
                                filter_df['ClinGen_annotation'].str.contains('Pathogenic')]

    # non-actionable heredity variants
    heredity_df = tmp_heredity_df[~tmp_heredity_df.isin(actionable_df.to_dict('list')).all(1)]
    print("--------------------------------------this is heredity df----------------------")
    print(heredity_df)

    # Uncertain -> LOVD/ClinVar/Clingene not pathogenic(/likely) or not benign(/likely)
    tmp_un_df = filter_df[~filter_df.isin(actionable_df.to_dict('list')).all(1)&
                       ~filter_df.isin(heredity_df.to_dict('list')).all(1)]
    uncertain_df = tmp_un_df[~tmp_un_df['LOVD_all_clinical'].str.contains('benign')&
                             ~tmp_un_df['ClinGen_annotation'].str.contains('Benign')&
                             (~tmp_un_df['CLNSIG'].isin(['Benign', 'Likely_benign']))]

    # print(uncertain_df)
    # uncertain_df.to_csv('uncertain_df.csv', sep=',')

    uncertain_df['VAF'] = pd.to_numeric(uncertain_df['VAF'], errors='coerce')
    internal_filter = uncertain_df[(uncertain_df['VAF'] >= 0.05) & (uncertain_df['VAF'] <= 0.5)]


    # ------ COSMIC -------
    COSMIC_df = internal_filter[~internal_filter['cosmic90_coding'].isin(['.'])]
    print("-------------------------this is COSMIC df")
    print(COSMIC_df)
    # Prediction
    non_cosmic_df = internal_filter[internal_filter['cosmic90_coding'].isin(['.'])]
    if 'summarized_prediction' in non_cosmic_df.columns:
        unpredict_df = non_cosmic_df[non_cosmic_df['summarized_prediction'] == 'Un_predict']
        tmp_predict_df = non_cosmic_df[~non_cosmic_df.isin(unpredict_df.to_dict('list')).all(1)]
        suspect_df = tmp_predict_df[tmp_predict_df['summarized_prediction'].astype(float) >= 0.71]
        suspect_df = pd.concat([suspect_df, unpredict_df], ignore_index=True)
    else:
        suspect_df = non_cosmic_df[non_cosmic_df['test1$pre_sum'].astype(float) >= 0.71]
    print("this is Predictive df--------------------------------------")
    print(suspect_df)
    return actionable_df, heredity_df, COSMIC_df, suspect_df, potential_treatment_df, df_population, df_function


def poll_annovar_completion(folder_path, subject_id, timeout=None, interval=10):# 確認annovar程式是否有跑完 才可以去status標記running或更新資訊
    elapsed_time = 0
    while True:
        if check_annovar_completion(folder_path, subject_id):
            return True
        time.sleep(interval)
        elapsed_time += interval
        if timeout is not None and elapsed_time >= timeout:
            return False


def save_info(request):
    if request.method == 'POST':
        sampleID = request.POST.get('subject_id', '')  
        syndrome = request.POST.get('name', '')  
        dob = request.POST.get('dob', '')  
        gender = request.POST.get('gender', '')  
        history = request.POST.get('history', '') 
        # allele_frequency = request.POST.get('allele_frequency', '') 
        # panel_name = request.POST.get('panel_name', '') 
        # genes = request.POST.get('genes', '') 
    

        cwd = os.getcwd()
        print('*************************cwd')
        print(cwd)

        newJobID = ''.join(random.sample(string.ascii_letters, 10))
        folder_path = os.path.join('media', 'patient', newJobID)
        os.makedirs(folder_path, exist_ok=True)
        
        file_path = os.path.join(folder_path, 'info.txt')
        
        log_file_path = os.path.join(folder_path, 'logFile.txt')
        with open(log_file_path, 'w') as logfile:
           pass 

        with open(file_path, 'w') as file:
            file.write(f'Subject ID: {sampleID}\n')
            file.write(f'Name: {syndrome}\n')
            file.write(f'Date of Birth: {dob}\n')
            file.write(f'Gender: {gender}\n')
            file.write(f'History/Description: {history}\n')

            
            file.write('******************************************filter setup page\n')
            file.write(f'allele_frequency: {allele_frequency}\n')
            file.write(f'panel_name: {panel_name}\n')
            file.write(f'genes: {genes}\n')

        myfile = request.FILES.get('myfile')  

        
        
        

        if myfile:
            file_path = os.path.join(folder_path, myfile.name)
            with open(file_path, 'wb') as file:  
                for chunk in myfile.chunks():
                    file.write(chunk)
            print(file_path)#media/patient/ILZqTykfeg/22W00407_S2_gpu_HF.vcf
            print(folder_path)#media/patient/ILZqTykfeg
            uploadFile_url = file_path
            resultFile_url = folder_path + "/" + sampleID + "_ann.txt"
            newJob = existJobs.jobs.create(
            jobID=newJobID,
            subject_id=sampleID,
            name=syndrome,
            dob=dob,
            gender=gender,
            history=history,
            uploadFile_url=uploadFile_url,
            resultFile_url=resultFile_url

        )
            x=existJobs.jobs.get(jobID=newJobID)
            subject_id=x.subject_id
            print(subject_id)
            print("end")
            if file_path.endswith(".vcf"):
                print(uploadFile_url)
                print(resultFile_url)
                # command = ann_command + " -vcf=" + uploadFile_url + " -out=" + resultFile_url + ">" + logFile + "&"
                ann_command = "python3 /miRTI/hw1/annovar_pipeline0_3.py -input " + uploadFile_url + " -output " + resultFile_url
                print(ann_command)
                command = "nohup " + ann_command + ">" + log_file_path + "&"
            else:
                print(uploadFile_url)
                print(resultFile_url)
                # command = ann_command + " -avinput=" + uploadFile_url + " -out=" + resultFile_url + ">" + logFile + "&"
                ann_command = "python3 /miRTI/hw1/annovar_pipeline0_3.py -input " + uploadFile_url + " -output " + resultFile_url
                print(ann_command)
                command = "nohup " + ann_command + ">" + log_file_path + "&"
        if command:
            os.system(command)
            print("command exist")
            

        if newJob:
            # os.system(command)
            
            os.system('nohup sh /home/cadilac/137_share/147_backup/VIP/media/test.sh&')
            #myPID = subprocess.check_output(grep_PID, shell=True)

            grep_PID = "pgrep -fo '" + newJob.jobID + "'"
            myPID = subprocess.check_output(grep_PID, shell=True)
            myPID = int(myPID)

            existJobs.jobs.filter(jobID=newJobID).update(processID=myPID)
            existJobs.jobs.filter(jobID=newJobID).update(status="running")

            if poll_annovar_completion(folder_path, sampleID):
                print("annovar.py 已經執行完畢。")
                existJobs.jobs.filter(jobID=newJobID).update(status="finished")
            
            return redirect('/input/success', locals())
        else:

            return redirect('/input/failed', locals())
        





def select_job_for_interpretation(request):


    
    finished_jobs = existJobs.jobs.filter(status="finished")
    # finished_jobs1 = existJobs.jobs.filter(status="finished")
    # print(finished_jobs1)
    print("this is finished job!")
    print(finished_jobs)
    
    # select_job = finished_jobs[0]

    ## request Job ID, return none when Job ID is not fetched
    try:
        select_job = request.session['select_ID']
    except NameError:
        select_job = "none"
    except KeyError:
        select_job = "none"
    first_record = finished_jobs[1]
    select_job = first_record.jobID
    
    print('current job is :' + select_job)

    if select_job == "none":
        parameters = {'finished_jobs': finished_jobs, 'select_ID': select_job, }
    else:
        pickle_exist = check_pickle_exist(select_job)
        print("work")
        config_list = getConfig(select_job)
        # print('config_list:')
        # print(config_list)

        if pickle_exist:
            parameters = load_parameters(request)
            parameters['syndrome'] = finished_jobs.filter(jobID=select_job)[0].name
            parameters['pickle_exist'] = pickle_exist
            parameters['config_list'] = config_list
        else:
            parameters = {'finished_jobs': finished_jobs, 'select_ID': select_job,
                          'sampleID': finished_jobs.filter(jobID=select_job)[0].subject_id,
                          'syndrome': finished_jobs.filter(jobID=select_job)[0].name,
                          'pickle_exist': pickle_exist,
                          'config_list': config_list}
    print(parameters)

    if request.method == "POST":
        ## check which button is clicked
        btn_load = request.POST.get("btn_load",
                                    "False")  ## request from the name of an object, return true if success, otherwise false.
        btn_layer = request.POST.get("btn_layer", "False")

        print("btn_load :" + btn_load)
        print("btn_layer :" + btn_layer)

        ## event of btn_load
        if btn_load == "True":
            print(parameters)
            select_config = request.POST['tmpConfig']
            print('select config :' + select_config)

            if select_config == 'none':
                # config_keys = ['strategy','review_status','MAF_cutoff','Min_DP_cutoff','Min_AAF','gene_panel']
                for i in ['strategy', 'review_status', 'MAF_cutoff', 'Min_DP_cutoff', 'Min_AAF', 'gene_panel',
                          'gene_panel_string', 'select_config']:
                    if (i in parameters):
                        parameters.pop(i)
                # print('review_status:'+parameters['review_status'])
                return render(request, 'select_job-test_v2.html', parameters)
            else:
                config = loadConfig(select_job, select_config)
                config['select_config'] = select_config

                ## add configs into demonstration parameters
                for x in config.keys():
                    parameters.update({x: config[x]})
                    print(parameters[x])

                ## change GenePanelList to Json
                GenePanelListJson=json.dumps({'GenePanelList':parameters['GenePanelList']})
                ## escape invalid symbols
                escaped_json_data = escapejs(GenePanelListJson)

                ## assign json back to GenePanelList
                parameters.update({"GenePanelList": escaped_json_data})

                return render(request, 'select_job-test_v2.html', parameters)

        ## event of btn_layer    
        elif (btn_layer == "True") & (select_job != 'none'):
            print('Select job for interpretation :' + select_job)

            ### get interpretation strategy ###
            strategy = request.POST['strategyRadioOptions']
            print('Strategy is:' + strategy)

            ### get review status ###
            review_status = request.POST['evidenceRadioOptions']
            print('Review stauts is:' + review_status)

            ### get gene panel for phenotype and cutoff of MAF ###
            MAF_cutoff = request.POST['maf_cutoff']
            print('MAF cutoff is :' + MAF_cutoff)




            Min_DP_cutoff = request.POST['min_dp_cutoff']
            print('Min dp cutoff is :' + Min_DP_cutoff)

            Min_AAF = request.POST['min_aaf']
            print('Min aaf is :' + Min_AAF)

            filtering = request.POST['filteringOptions']
            print('filtering options is :' + filtering)

            config_name = request.POST['configName']
            print('Save config as :' + config_name)

            if strategy != "Cancer":

                # 從前端表單獲取json資料
                frontendJson = request.POST.get('json_data')
                print(frontendJson)
                if(frontendJson==''):
                    print("fuck")
                frontendJsonContent = json.loads(frontendJson)
                # type(frontendJsonContent) # dict
                # print(frontendJsonContent.keys())  # ['HPOterm', 'GenePanelList']
                
                # 處理gene panel list
                aggregateDict = genePanelListProcessing(frontendJsonContent['GenePanelList'])

                print(aggregateDict)
                gene_panel = aggregateDict['genes']
                panelNames = aggregateDict['panelNames']
                genePanelDataFrame = aggregateDict['result']

                hpoTermIds = extractHpoIds(panelNames)


                print("*****************test")
                print(gene_panel)
                print("****************************")
                print(panelNames)
                print("****************************")
                print(genePanelDataFrame)
                print("****************************")
                print(hpoTermIds)
                if len(hpoTermIds)!=0:
                    # request Amelie phenotype driven ranking score from API
                    amelieResultDict = requestAmelieAPI(request,hpoTermIds,gene_panel)

                    # post-processing for requested result
                    amelieResultTable = pd.DataFrame({'Genes':amelieResultDict.keys()})
                    amelieResultTable['Max_Score'] = amelieResultTable['Genes'].apply(lambda x: round(max(dict(amelieResultDict[x]).values()),2))
                    amelieResultTable['Mean_Score'] = amelieResultTable['Genes'].apply(lambda x: round(sum(dict(amelieResultDict[x]).values())/len(dict(amelieResultDict[x]).values()),2))
                    amelieResultTable['Number_of_References'] = amelieResultTable['Genes'].apply(lambda x: len(dict(amelieResultDict[x]).values()))
                    amelieResultTable['References_List'] = amelieResultTable['Genes'].apply(lambda x: list(dict(amelieResultDict[x]).keys()))
                    amelieResultTable['Scores_List'] = amelieResultTable['Genes'].apply(lambda x: list(dict(amelieResultDict[x]).values()))

                    # merge result
                    genePanelDataFrame = genePanelDataFrame.merge(amelieResultTable,on='Genes',how='outer').fillna(-1)
                    genePanelDataFrame['Number_of_References'] = genePanelDataFrame['Number_of_References'].to_numpy(int)
                    # hpoTermIds 為空時，新增同樣的欄位並塞空值
                else:
                    genePanelDataFrame['Max_Score'] = -1
                    genePanelDataFrame['Mean_Score'] = -1
                    genePanelDataFrame['Number_of_References'] = -1
                    genePanelDataFrame['References_List'] = -1
                    genePanelDataFrame['Scores_List'] = -1
                
                # 輸出整理完的表格
                genePanelDataFrame.to_csv('media/patient/'+select_job+'/GenePanelDataFrame.tsv',sep='\t',index=None)

                # 將新表格塞回去
                aggregateDict['result'] = genePanelDataFrame

                #gene_panel = adjust_genePanel(gene_panel_text)
                print('gene panel is :')
                print(gene_panel)
            config_values = [strategy, review_status, MAF_cutoff, Min_DP_cutoff, Min_AAF, filtering]
            config_keys = ['strategy', 'review_status', 'MAF_cutoff', 'Min_DP_cutoff', 'Min_AAF','filtering']
            config = dict(zip(config_keys, config_values))
             # 將json資料加入config中
            config.update(frontendJsonContent)
            print("***********config,select_job,config_name")
            print(config)
            print("**********")
            print(select_job)
            print("**********")
            print(config_name)
            # save config as json
            saveConfig(config, select_job, config_name)


            #### load annotated table and genotype table ####
            annotated_file = finished_jobs.filter(jobID=select_job)[0].resultFile_url
            # print(annotated_file)

            input_file = finished_jobs.filter(jobID=select_job)[0].uploadFile_url
            # print(input_file)

            sampleID = finished_jobs.filter(jobID=select_job)[0].subject_id
            annot_table = pd.read_csv(annotated_file, sep='\t')
            regex = re.compile('.vcf$')
            if regex.search(input_file):
                gt_input_file = regex.sub('_tmp.avinput', input_file)
                gt_input = pd.read_csv(gt_input_file, sep='\t', header=None,usecols=[0,1,2,3,4,5,6,7,9,14,16,17])
                # gt_input = gt_input.drop(columns=[8,10,11,12,13,14,15])
                # gt_input.columns = ['Chr','Start','End','Ref','Alt','GT','QUAL','DP','ori_pos','header','format']
                av_processor = preprocessor(gt_input, float(Min_AAF), int(Min_DP_cutoff), filtering) #
                start_time = time.time()
                gt_input = av_processor.start_processing()
                print('Elapse time:' + str(time.time() - start_time))
            else:
                gt_input_file = input_file

                gt_input = pd.read_csv(gt_input_file, sep='\t', header=None)
                gt_input = gt_input.rename(
                    columns={0: 'Chr', 1: 'Start', 2: 'End', 3: 'Ref', 4: 'Alt', 5: 'GT', 6: 'QUAL', 7: 'DP'})
                gt_input['VAF'] = 0.5
                gt_input['AD'] = '250,250'

            print(gt_input_file)
            if strategy != "Cancer":
                WES_layer = WES_layering(annotation_table=annot_table,
                                         genotype_table=gt_input,
                                         gene_panel=gene_panel,
                                         MAF_cutoff=MAF_cutoff,
                                         review_status=review_status,
                                         phenotypeDrivenRanking=genePanelDataFrame)
                 
                parameters = WES_layer.layering()
                print(parameters)
                print("****************parameters\n")
                print(parameters['known_pheno_variant'])
                # x=parameters['known_pheno_variant']
                # x.to_csv('/home/uuuwei0504/下載/VIP_germline-main/VIP/test/known_variants,csv',index=False)
                print("****************test\n")
                for tmp_key in ['known_pheno_variant', 'suspect_pheno_variant', 'other_variant',
                                'two_hit_pheno_variant', 'homo_pheno_variant']:
                    if parameters[tmp_key].shape[0] != 0:
                        parameters[tmp_key].index = parameters[tmp_key].apply(createVariantIndex, axis=1)
                        parameters[tmp_key]['checked'] = 'off'
            else:
                Somatic_layer = Somatic_layering(annotation_table=annot_table, genotype_table=gt_input,
                                                 MAF_cutoff=MAF_cutoff)
                tmp_gene_panel = Somatic_layer.load_cancer_associated_genes()['Gene Symbol']
                gene_panel = [tmp_gene_panel[i] for i in tmp_gene_panel.index]
                parameters = Somatic_layer.layering()
            variantIndices = list()
            for tmp_key in ['known_pheno_variant', 'suspect_pheno_variant', 'other_variant', 'two_hit_pheno_variant',
                            'homo_pheno_variant']:
                if parameters[tmp_key].shape[0] != 0:
                    variantIndices = variantIndices + list(parameters[tmp_key].index)
                # print(aggregateDict)
            reportIndex = pd.DataFrame(index=pd.unique(variantIndices))
            reportIndex['report'] = 'off'
            parameters['reportIndex'] = reportIndex

            ## count number of variants in each layer and put it into parameter
            number_of_phenotype_associated_variant = parameters['known_pheno_variant'].shape[0]
            number_of_incidental_finding_variant = parameters['known_other_variant'].shape[0] + \
                                                   parameters['known_ACMG_variant'].shape[0]
            number_of_drug_response_variant = parameters['drug_response_variant'].shape[0]
            number_of_predicted_suspect_variant = parameters['suspect_pheno_variant'].shape[0]
            number_of_other_variant = parameters['other_variant'].shape[0]

            parameters['number_of_phenotype_associated_variant'] = number_of_phenotype_associated_variant
            parameters['number_of_incidental_finding_variant'] = number_of_incidental_finding_variant
            parameters['number_of_drug_response_variant'] = number_of_drug_response_variant
            parameters['number_of_predicted_suspect_variant'] = number_of_predicted_suspect_variant
            parameters['number_of_other_variant'] = number_of_other_variant

            # other information
            parameters['gene_panel'] = gene_panel
            parameters['aggregateDict'] = aggregateDict
            parameters['maf_cutoff'] = MAF_cutoff
            parameters['min_aaf'] = Min_AAF
            parameters['passOnly'] = filtering
            parameters['min_dp_cutoff'] = Min_DP_cutoff
            parameters['strategy'] = strategy
            parameters['review_status'] = review_status

            # pack these information into pickle file
            resultFile_path = "media/patient/" + select_job + "/" + sampleID
            with open(resultFile_path + '.pickle', 'wb') as wf:
                pickle.dump(parameters, wf)

            parameters['finished_jobs'] = finished_jobs
            parameters['select_ID'] = select_job
            parameters['sampleID'] = sampleID
            parameters['syndrome'] = finished_jobs.filter(jobID=select_job)[0].name

            get_summary_excel(parameters, select_job, sampleID)

            print('select ID: ' + request.session['select_ID'])

            print(parameters)




    return render(request, 'select_job-test_v2.html', parameters)
    
# def show_job_list(request):
#     # request.session['select_job'] = 'none'

#     finished_jobs = existJobs.jobs.all().filter(status="finished")

#     jobs = existJobs.jobs.order_by('-date')
#     running_jobs = existJobs.jobs.all().filter(status="running")
#     print("running_jobs is :")
#     print(running_jobs)
#     pending_jobs = existJobs.jobs.all().filter(status="pending")
#     print("pending jobs is :")
#     print(pending_jobs)
#     running_jobs_cnt = len(running_jobs)
#     if len(running_jobs) > 0:
#         for i in range(len(running_jobs)):
#             tmp_PID = running_jobs[i].processID
#             tmp_jobID = running_jobs[i].jobID

#             check_PID_exist = "ps -p " + tmp_PID + " >/dev/null"
#             check_value = os.system(check_PID_exist)
#             print(check_value)

#             result_file = running_jobs[i].resultFile_url
#             print(os.path.isfile(result_file))

#             if (check_value != 0) and (os.path.isfile(result_file)):
#                 running_jobs.filter(processID=tmp_PID, jobID=tmp_jobID).update(status="finished")
#                 print("***************finished")

#             elif (check_value != 0) and (not os.path.isfile(result_file)):
#                 running_jobs.filter(processID=tmp_PID, jobID=tmp_jobID).update(status="expired")
#                 print("***************expired")

#     else:
#         print("no running jobs")

#     #if len(pending_jobs) > 0:
#      #   for i in range(len(pending_jobs)):
#       #      tmp_PID = pending_jobs[i].processID
#        #     tmp_jobID = pending_jobs[i].jobID
# #
#  #           check_PID_exist = "ps -p " + tmp_PID + " >/dev/null"
#   #          check_value = os.system(check_PID_exist)
#    #         print(check_value)

#     #        result_file = pending_jobs[i].resultFile_url
#      #       print(os.path.isfile(result_file))

#       #      if (check_value != 0) and (os.path.isfile(result_file)):
#        #         pending_jobs.filter(processID=tmp_PID, jobID=tmp_jobID).update(status="finished")
#         #        print("***************finished")

#          #   elif (check_value != 0) and (not os.path.isfile(result_file)):
#           #      pending_jobs.filter(processID=tmp_PID, jobID=tmp_jobID).update(status="expired")
#            #     print("***************expired")

#     #else:
#      #   print("no pending jobs")



#     if request.method == 'POST':
#         id_for_layer = request.POST.get("layer-id", "none")
#         id_for_delete = request.POST.get("delete-id", "none")
#         id_for_reAnnotate = request.POST.get("reAnnotate-id", "none")
#         if id_for_delete != "none" and existJobs.jobs.get(jobID=id_for_delete).status != "running":
#             delete_job(id_for_delete)
#             print("Delete " + id_for_delete)

#         elif id_for_reAnnotate != "none" and existJobs.jobs.get(jobID=id_for_reAnnotate).status != "running":
#             reannotate_job(id_for_reAnnotate)
#             print("ReAnnotate" + id_for_reAnnotate)

#         elif id_for_layer != "none":
#             print("Layer " + id_for_layer)
#             request.session['select_ID'] = id_for_layer
#             # parameters = {'select_ID': id_for_layer}
#             # print(parameters)
#             # return render(request, 'select_job-test.html', parameters)
#             # return redirect(select_job_for_interpretation,select_ID = id_for_layer)
#             return redirect('/selection/')



#         else:
#             print('Job ' + id_for_delete + ' is still running, please wait!')

#     print(jobs)
#     print(running_jobs)
#     print(finished_jobs)
#     print("******jobs")
#     print(jobs[0])
#     jobs_json = serialize('json', jobs)
#     running_jobs_json = serialize('json', running_jobs)
#     finished_jobs_json = serialize('json', finished_jobs)
#     print("------------test--------------")
#     finished_jobs_count = len(finished_jobs)
#     print(f"Finished jobs count: {len(finished_jobs)}")
#     print(finished_jobs.count())
#     print("------------test--end----------")

#     data = {
#         'jobs': jobs_json,
#         'running_jobs_cnt': running_jobs_cnt,
#         'finished_jobs': finished_jobs_json,
#     }

#     return JsonResponse(data)
from datetime import timedelta
from django.http import JsonResponse
from django.core.serializers import serialize
from django.shortcuts import redirect
import os
import subprocess
from django.utils.timezone import now

def show_job_list(request):
    GRACE_PERIOD = timedelta(minutes=30)

    finished_jobs = existJobs.jobs.filter(status="finished")

    jobs = existJobs.jobs.order_by('-date')
    running_jobs = existJobs.jobs.filter(status="running")
    pending_jobs = existJobs.jobs.filter(status="pending")

    running_jobs_cnt = running_jobs.count()
    jobs_to_update = []

    if running_jobs.exists():
        for job in running_jobs:
            result_file = job.resultFile_url
            file_exists = result_file and os.path.isfile(result_file)

            # **使用「剩餘時間」計算 expired**
            remaining_time = (job.date + GRACE_PERIOD) - now()
            expired = remaining_time.total_seconds() <= 0  # ✅ 確保不會因時區問題報錯

            if file_exists:
                job.status = "finished"
            elif expired:
                job.status = "expired"

            jobs_to_update.append(job)

    if jobs_to_update:
        existJobs.jobs.bulk_update(jobs_to_update, ["status"])

    data = {
        'jobs': serialize('json', jobs),
        'running_jobs_cnt': running_jobs_cnt,
        'finished_jobs': serialize('json', finished_jobs),
    }

    return JsonResponse(data)



def genePanelListProcessing(genePanelList):
    
    print(str(len(genePanelList))+" gene panels are detected!")
    # geneSet用於存放所有genePanelList中的基因
    geneSet=set()
    # panelNameSet用於存放所有genePanelList中的套組名稱
    panelNameSet=set()

    # aggregateList用於存放所有gene及其對應的套組名稱
    aggregateList=[]

    for i in range(len(genePanelList)):
        # 透過adjust_genePanel將gene panel從字串處理為list，並轉換為set
        currentGeneSet = set(adjust_genePanel(genePanelList[i]['genePanel']))
        currentPanelName = genePanelList[i]['panelName']

        # 將 currentGeneSet 中各個元素的所屬 panelName 轉換成字典
        currentGenePanelDict = {elem: currentPanelName for elem in currentGeneSet}

        # 取得 geneSet 和 currentGeneSet 的聯集
        geneSet = geneSet.union(currentGeneSet)

        # 將 currentPanelName 加入 panelNameSet
        panelNameSet.add(currentPanelName)

        # 將currentGenePhenoDict加進genePhenoList
        aggregateList.append(currentGenePanelDict)

    # 將兩個 set 合併成一個 DataFrame
    aggregateTable = pd.DataFrame({'Genes': list(geneSet)})

    # 透過apply檢查每個Gene出現在phenoList中的哪幾個phenotype
    aggregateTable['Panel_Name'] = aggregateTable['Genes'].apply(lambda x:[aggregateList[i].get(x) for i in range(len(aggregateList)) if aggregateList[i].get(x) is not None])

    # 計算每個Gene出現在幾個phenotype中
    aggregateTable['Count'] = aggregateTable['Panel_Name'].apply(len)
    
    # 比對Gene名稱是否有在目前使用的資料庫(hg19_refGeneWithVer.txt)中
    refGeneList = pd.read_csv("hw1/DB/refGeneList.txt",header=None)
    refGeneList.columns = ['Genes']
    aggregateTable['isRecognized'] = aggregateTable['Genes'].isin(refGeneList['Genes'])
    
    # 對Count進行排序
    aggregateTable = aggregateTable.sort_values('Count', ascending=False)

    # 調整欄位順序
    aggregateTable = aggregateTable[['Genes', 'isRecognized', 'Panel_Name', 'Count']]
    print(panelNameSet)
    # 將gene list, phenotpye list(phenoList) 及處理完的結果 (genePhenoAggregateTable) 以dict儲存並回傳
    aggregateDict = {
        'genes':list(geneSet),
        'panelNames':list(panelNameSet),
        'result':aggregateTable
    }
    return(aggregateDict)  
def get_summary_excel(parameters, select_job, sampleID):
    excel_path = "media/patient/" + select_job + "/" + sampleID
    #writer = pd.ExcelWriter(excel_path + '.xlsx', engine="xlsxwriter")
    writer = pd.ExcelWriter(excel_path + '.xlsx')

    if parameters['strategy'] == "Cancer":
        parameters['actionable_variant'].to_excel(writer, sheet_name='Actionable variant', index=False)

    parameters['known_pheno_variant'].to_excel(writer, sheet_name='Phenotype associated variants', index=False)
    parameters['known_ACMG_variant'].to_excel(writer, sheet_name='Incidental ACMG variants', index=False)
    parameters['known_other_variant'].to_excel(writer, sheet_name='Incidental other variants', index=False)
    parameters['drug_response_demo'].to_excel(writer, sheet_name='Drug response variants', index=False)
    parameters['suspect_pheno_variant'].to_excel(writer, sheet_name='Suspect phenotype variants', index=False)
    parameters['suspect_ACMG_variant'].to_excel(writer, sheet_name='Suspect ACMG variants', index=False)
    parameters['suspect_other_variant'].to_excel(writer, sheet_name='Suspect other disease', index=False)
    parameters['other_variant'].to_excel(writer, sheet_name='Other variants', index=False)

    print('writer:',writer)

    writer.save()
def delete_job(job_id):
    existJobs.jobs.get(jobID=job_id).delete()
    if len(existJobs.jobs.filter(jobID=job_id)) == 0:
        folder_path = "media/patient/" + job_id
        if (os.path.isdir(folder_path)):
            os.system("rm -rf media/" + job_id)
            print("Folder has been removed successfully!")
        else:
            print("No such folder exist.")
        print("Job " + job_id + " has been removed successfully!")
    else:
        print("Nothing happened.")
    return job_id
def reannotate_job(job_id):
    currentJob = existJobs.jobs.get(jobID=job_id)

    ann_command = "python3 /miRTI/hw1/annovar_pipeline0_3.py -input " + currentJob.uploadFile_url + " -output " + currentJob.resultFile_url
    logFile = 'media/patient/' + job_id + '/log.txt'
    command = "nohup " + ann_command + ">" + logFile + "&"

    os.system(command)
    grep_PID = "pgrep -fo '" + currentJob.jobID + "'"
    myPID = subprocess.check_output(grep_PID, shell=True)
    myPID = int(myPID)

    existJobs.jobs.filter(jobID=job_id).update(processID=myPID)
    existJobs.jobs.filter(jobID=job_id).update(status="running")

    return job_id
def adjust_genePanel(gene_panel_text):
    tmp_gene_panel = re.split(',|\n|\t|\r| ', gene_panel_text)
    tmp_gene_panel = pd.Series(tmp_gene_panel)
    tmp_gene_panel = tmp_gene_panel[~tmp_gene_panel.duplicated()]
    tmp_gene_panel = tmp_gene_panel[tmp_gene_panel != ""]
    gene_panel = [tmp_gene_panel[i] for i in tmp_gene_panel.index]
    return gene_panel
def check_pickle_exist(select_job):
    tmp_dir = 'media/patient/' + select_job
    if(any([True for i in os.listdir(tmp_dir) if re.search('.pickle$',i)])):
        return True
    else:
        return False  
def getConfig(jobID):
    fileList = os.listdir('media/patient/' + jobID)
    config_list = [i for i in fileList if re.search("json", i)]
    if (len(config_list) > 0):
        config_list = [re.sub('.json$', '', i) for i in config_list]

    return config_list
def load_parameters(request):
    finished_jobs = existJobs.jobs.all().filter(status="finished")
    print(finished_jobs)
    first_record = finished_jobs[1]
    select_job = first_record.jobID
    
    sampleID = finished_jobs.filter(jobID=select_job)[0].subject_id
    fs = FileSystemStorage()
    print(fs.location)
    parm_pickle = fs.location + '/' + "/patient/"+ select_job + '/' + sampleID + '.pickle'

    #
    with open(parm_pickle, 'rb') as file:
        parameters = pickle.load(file)

    parameters['select_ID'] = select_job
    parameters['sampleID'] = sampleID
    parameters['finished_jobs'] = finished_jobs

    # variants_df = parameters['summary_table']
    # variants_df.columns = variants_df.columns.str.replace('.', '_')
    # parameters['all_num'] = len(variants_df)

    # parameters['summary_table'] = variants_df
    # print(parameters)
    return parameters
def loadConfig(jobID, select_config_file):
    tmp_config_dir = 'media/patient/' + jobID + '/' + select_config_file + '.json'
    with open(tmp_config_dir) as json_file:
        config = json.load(json_file)
    return config
def extractHpoIds(panelNames):
    ## panelNames should be a list
    hpoTermIds=[panelNames[i].split('(')[0] if re.match("^HP:\d{7}\(", panelNames[i]) else None for i in range(len(panelNames)) ]
    hpoTermIds=set(hpoTermIds)
    try:
        hpoTermIds.remove(None)
        print("Value of None is removed!")
    except:
        ## 若沒有None存在，不做任何事，僅print出下列訊息
        print("No value of None is detected!")

    return list(hpoTermIds)
def requestAmelieAPI(request,phenotypes,genes):
    # sampleID should be a string
    # phenotype should be a list
    # genes should be a lits
    
    # request job information to restore data
    
    finished_jobs = existJobs.jobs.all().filter(status="finished")
    first_record = finished_jobs[1]
    select_job = first_record.jobID
    sampleID = finished_jobs.filter(jobID=select_job)[0].subject_id

    url = 'https://amelie.stanford.edu/api/gene_list_api/'

    # request Amelie API
    response = requests.post(
        url,
        verify=False,
        data={'patientName': sampleID,
              'phenotypes': ','.join(phenotypes),
              'genes': ','.join(genes)})
    
    # save result as json
    result_dir="media/patient/" + select_job + "/amelie_score.json"
    with open(result_dir, 'w') as outfile:
        json.dump(response.json(), outfile,indent=4)

    return dict(response.json())
def saveConfig(config, jobID, name):
    config_list = getConfig(jobID)
    if (name in config_list):
        print('file exist!')
        config_dir = 'media/patient/' + jobID + "/" + name + '.json'
    else:
        thisTime = time.localtime()
        stamp = str(thisTime[0]) + "Y_" + str(thisTime[1]) + "M_" + str(thisTime[2]) + "D_" + str(
            thisTime[3]) + "h_" + str(thisTime[4]) + "m_" + str(thisTime[5]) + "s.json"
        config_dir = 'media/patient/' + jobID + "/" + name + "_" + stamp

    with open(config_dir, 'w') as outfile:
        json.dump(config, outfile,indent=4)
    if os.path.isfile(config_dir):
        print("Save configuration success!")
    else:
        print("Fail to save configuration.")
def createVariantIndex(x):
    return str(x['Chr']) + ':' + str(x['Start']) + '_' + str(x['End']) + x['Ref'] + '>' + x['Alt']


# 要切json檔的部份
# def phenotype_associated_variant(request):
#     if request.session['select_ID'] == 'none':
#         return render(request, 'phenotype_associated.html', {'select_ID': 'none'})
#     else:
#         ori_parameters = load_parameters(request)  ## for backup
#         tmp_parameters = load_parameters(request)  ## for display
#         tmp_parameters['known_pheno_variant'] = tmp_parameters['known_pheno_variant'].apply(rearrange_location, axis=1)
#         parameters = modify_table(request, tmp_parameters, ['known_pheno_variant'])
#         print(parameters['reportIndex'])
#         print("------------------------------")
#         if request.method == 'POST':
#             ori_parameters = updateReportIndexTable(request, ori_parameters, ['known_pheno_variant'])
#             savePickle(ori_parameters['select_ID'], ori_parameters)
#             return redirect('/phenotype_associated/')
#         return render(request, 'phenotype_associated.html', parameters)



# def actionable_variant(request):
#     if request.session['select_ID'] == 'none':
#         return render(request, 'actionable_variant.html', {'select_ID': 'none'})
#     else:
#         tmp_parameters = load_parameters(request)
#         print(tmp_parameters['actionable_variant'])
#         tmp_parameters['actionable_variant'] = tmp_parameters['actionable_variant'].apply(rearrange_location, axis=1)
#         parameters = modify_table(request, tmp_parameters, ['actionable_variant'])

#         return render(request, 'actionable_variant.html', parameters)



# def COSMIC_variant(request):
#     if request.session['select_ID'] == 'none':
#         return render(request, 'cosmic_variant.html', {'select_ID': 'none'})
#     else:
#         tmp_parameters = load_parameters(request)
#         tmp_parameters['COSMIC_variant'] = tmp_parameters['COSMIC_variant'].apply(rearrange_location, axis=1)
#         parameters = modify_table(request, tmp_parameters, ['COSMIC_variant'])

#         return render(request, 'cosmic_variant.html', parameters)


# def other_variant(request):
#     if request.session['select_ID'] == 'none':
#         return render(request, 'others.html', {'select_ID': 'none'})
#     else:
#         ori_parameters = load_parameters(request)  ## for backup
#         tmp_parameters = load_parameters(request)  ## for display
#         tmp_parameters['other_variant'] = tmp_parameters['other_variant'].apply(rearrange_location, axis=1)
#         parameters = modify_table(request, tmp_parameters, ['other_variant'])
#         print(parameters['reportIndex'])
#         print("------------------------------")
#         if request.method == 'POST':
#             ori_parameters = updateReportIndexTable(request, ori_parameters, ['other_variant'])
#             savePickle(ori_parameters['select_ID'], ori_parameters)
#             return redirect('/others/')
#         return render(request, 'others.html', parameters)



# def incidental_finding_variant(request):
#     if request.session['select_ID'] == 'none':
#         return render(request, 'incidental_finding.html', {'select_ID': 'none'})
#     else:
#         tmp_parameters = load_parameters(request)
#         tmp_parameters['known_other_variant'] = tmp_parameters['known_other_variant'].apply(rearrange_location, axis=1)
#         tmp_parameters['known_ACMG_variant'] = tmp_parameters['known_ACMG_variant'].apply(rearrange_location, axis=1)
#         parameters = modify_table(request, tmp_parameters, ['known_other_variant', 'known_ACMG_variant'])

#         parameters['here_df_list'] = zip([parameters['known_ACMG_variant'], parameters['known_other_variant']],
#                                          ['ACMG variants', 'Other pathogenic variants'])

#         return render(request, 'incidental_finding.html', parameters)
def modify_table(request, parameters, df_names):
    for df_name in df_names:
        parameters[df_name].columns = parameters[df_name].columns.str.replace('.', '_')
        parameters[df_name] = parameters[df_name].rename(columns={'1000G_ALL': 'AF_1000G'})
        # parameters[df_name] = parameters[df_name].rename(columns={'1000G_EAS':'AF_1000G_EAS'})
        parameters[df_name] = parameters[df_name].apply(summarize_known_clinical_evidence, axis=1)

    return parameters
def updateReportIndexTable(request, original_parameters, currentKey):
    for tmp_key in currentKey:
        for tmp_index in original_parameters[tmp_key].index:
            report_status = request.POST.get(tmp_index, 'off')
            print(report_status)
            ori_status = pd.unique(original_parameters['reportIndex'].loc[tmp_index, 'report'])[0]
            if report_status != ori_status:
                original_parameters['reportIndex'].loc[tmp_index, 'report'] = report_status
                original_parameters = updateReportStatus(tmp_index, report_status, original_parameters)
                print(tmp_index + ':' + ori_status + '>' + report_status)
    return original_parameters
def updateReportStatus(variantIndex, changedStatus, original_parameters):
    if original_parameters['known_pheno_variant'].shape[0] != 0:
        if original_parameters['known_pheno_variant'].index.isin([variantIndex]).any():
            original_parameters['known_pheno_variant'].loc[variantIndex, 'checked'] = changedStatus

    if original_parameters['suspect_pheno_variant'].shape[0] != 0:
        if original_parameters['suspect_pheno_variant'].index.isin([variantIndex]).any():
            original_parameters['suspect_pheno_variant'].loc[variantIndex, 'checked'] = changedStatus
            print("\"" + original_parameters['suspect_pheno_variant'].loc[variantIndex, 'checked'] + "\"")

    if original_parameters['other_variant'].shape[0] != 0:
        if original_parameters['other_variant'].index.isin([variantIndex]).any():
            original_parameters['other_variant'].loc[variantIndex, 'checked'] = changedStatus

    if original_parameters['two_hit_pheno_variant'].shape[0] != 0:
        if original_parameters['two_hit_pheno_variant'].index.isin([variantIndex]).any():
            original_parameters['two_hit_pheno_variant'].loc[variantIndex, 'checked'] = changedStatus

    if original_parameters['homo_pheno_variant'].shape[0] != 0:
        if original_parameters['homo_pheno_variant'].index.isin([variantIndex]).any():
            original_parameters['homo_pheno_variant'].loc[variantIndex, 'checked'] = changedStatus

    return original_parameters
def savePickle(jobID, parameters):
    sampleID = existJobs.jobs.all().filter(jobID=jobID)[0].sampleID
    resultFile_path = "media/patient/" + jobID + "/" + sampleID
    with open(resultFile_path + '.pickle', 'wb') as wf:
        pickle.dump(parameters, wf)
def summarize_known_clinical_evidence(x):
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




def api_page(request):
    
    return render(request, 'api_test.html')
def search_page(request):

    return render(request, "test.html", locals())
def load_parameters1(pickle_path):
    # 檢查文件是否存在
    if not os.path.exists(pickle_path):
        raise FileNotFoundError(f"Pickle file not found: {pickle_path}")
    
    # 打開並讀取 pickle 文件
    with open(pickle_path, 'rb') as file:
        parameters = pickle.load(file)
    
    return parameters

def modify_table1(parameters, df_names):
    for df_name in df_names:
        parameters[df_name].columns = parameters[df_name].columns.str.replace('.', '_')
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
@csrf_exempt
def known_pathogenic():
    finished_jobs = existJobs.jobs.all().filter(status="finished")
    global global_newJobID
    newJobID = 'GsqxBRAFYn'
    first_record = finished_jobs.filter(jobID=newJobID).first()
    


    
    select_job = first_record.jobID
    
    sampleID = finished_jobs.filter(jobID=select_job)[0].subject_id
    fs = FileSystemStorage()
    parm_pickle = fs.location + '/' + "/patient/"+ select_job + '/' + sampleID + '.pickle'
    print("****")
    pickle_path = 'media/patient/LyvnWreaTh/NA10080.pickle' 
    
 
    parameters = load_parameters1(parm_pickle)
    # print(parameters['known_pheno_variant'])
    

    parameters['known_pheno_variant'] = parameters['known_pheno_variant'].apply(rearrange_location1, axis=1)
    

    parameters = modify_table1(parameters, ['known_pheno_variant'])
    print("**************************************")
    print(parameters['known_pheno_variant'])
    parameters['known_pheno_variant'].to_csv('known_pheno_variant.csv', index=False)

    # print(parameters)
import csv


@csrf_exempt
def known_pathogenic_to_json(request):
    if request.method == 'POST':

        finished_jobs = existJobs.jobs.all().filter(status="finished")
        global global_newJobID
        newJobID = 'TsOqwztceS'
        first_record = finished_jobs.filter(jobID=newJobID).first()

        select_job = first_record.jobID

        sampleID = finished_jobs.filter(jobID=select_job)[0].subject_id
        fs = FileSystemStorage()
        parm_pickle = fs.location + '/' + "/patient/"+ select_job + '/' + sampleID + '.pickle'
        print("****")
        pickle_path = 'media/patient/LyvnWreaTh/NA10080.pickle' 
        
        parameters = load_parameters1(parm_pickle)
        print(parameters['known_pheno_variant'])
        

        parameters['known_pheno_variant'] = parameters['known_pheno_variant'].apply(rearrange_location1, axis=1)
        

        parameters = modify_table1(parameters, ['known_pheno_variant'])
        print("**************************************")
        print(parameters['known_pheno_variant'])
        parameters['known_pheno_variant'].to_csv('known_pheno_variant.csv', index=False)

        data = []
        with open('known_pheno_variant.csv', mode='r', encoding='utf-8-sig') as original_file:
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
                new_row['OMIM'] = row['OMIM_number'] if row['OMIM_number'] != 'None' else ''

                # 11. Amelie Max score
                new_row['Amelie Max score'] = row['Max_Score']

                # 12. Amelie Mean score
                new_row['Amelie Mean score'] = row['Mean_Score']

                data.append(new_row)
                print(data)

        return JsonResponse(data, safe=False)
    else:
        return HttpResponse("Only POST requests are accepted.")

@csrf_exempt
def other_variant(request):
    if request.method == 'POST':
        finished_jobs = existJobs.jobs.all().filter(status="finished")
        global global_newJobID
        newJobID = 'TsOqwztceS'  # Replace with your actual job ID
        first_record = finished_jobs.filter(jobID=newJobID).first()

        select_job = first_record.jobID

        sampleID = finished_jobs.filter(jobID=select_job)[0].subject_id
        fs = FileSystemStorage()
        parm_pickle = os.path.join(fs.location, 'patient', select_job, f'{sampleID}.pickle')
        print("****")

        parameters = load_parameters1(parm_pickle)

        parameters['other_variant'] = parameters['other_variant'].apply(rearrange_location1, axis=1)

        parameters = modify_table1(parameters, ['other_variant'])
        print("**************************************")
        print(parameters['other_variant'])
        parameters['other_variant'].to_csv('other_variant.csv', index=False)

        data = []
        with open('other_variant.csv', mode='r', encoding='utf-8-sig') as original_file:
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
                new_row['OMIM'] = row['OMIM_number'] if row['OMIM_number'] != 'None' else ''

                # 11. Amelie Max score
                new_row['Amelie Max score'] = row['Max_Score']

                # 12. Amelie Mean score
                new_row['Amelie Mean score'] = row['Mean_Score']

                data.append(new_row)

        # Writing data to CSV file
        with open('result_tableother_variant_result.csv', mode='w', encoding='utf-8-sig', newline='') as csv_file:
            fieldnames = ['Location', 'Gene', 'RS ID', 'MAF', 'Genotype / VAF', 'Evidence', 
                        'Domain', 'Pathogenicity', 'Splicing effect', 'OMIM', 
                        'Amelie Max score', 'Amelie Mean score']
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)

            writer.writeheader()
            for row in data:
                writer.writerow(row)

        return JsonResponse(data, safe=False)
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)


def filter_vcf_by_maf(vcf_file, output_file, maf_cutoff):
    """
    根據 MAF_cutoff 篩選 VCF 文件的 AF 欄位資料。
    :param vcf_file: 輸入的 VCF 文件路徑。
    :param output_file: 篩選後輸出的 VCF 文件路徑。
    :param maf_cutoff: MAF 篩選條件（保留小於等於該值的資料）。
    """
    with pysam.VariantFile(vcf_file, "r") as vcf_in:
        with pysam.VariantFile(output_file, "w", header=vcf_in.header) as vcf_out:
            for record in vcf_in:
                # 提取 AF 值
                af = record.info.get("AF", [None])[0]
                
                # 確保 AF 是 float 型別
                try:
                    af = float(af) if af is not None else None
                except ValueError:
                    af = None
                
                # 進行篩選
                if af is not None and af <= maf_cutoff:
                    vcf_out.write(record)
    print(f"篩選完成！輸出檔案: {output_file}")

def update_job_status():
    running_jobs = existJobs.jobs.filter(status="running")

    for job in running_jobs:
        tmp_PID = job.processID
        tmp_jobID = job.jobID

        # 用 ps -p 檢查 PID 是否存在 (這裡你也可考慮改用 subprocess.run)
        check_PID_exist = f"ps -p {tmp_PID} >/dev/null"
        check_value = os.system(check_PID_exist)
        print(f"Job {tmp_jobID}, check_value = {check_value}")

        result_file = job.resultFile_url
        file_exists = os.path.isfile(result_file)
        print(f"file_exists = {file_exists}")

        if (check_value != 0) and file_exists:
            # PID 掛掉，但檔案已經生成 -> finished
            existJobs.jobs.filter(processID=tmp_PID, jobID=tmp_jobID).update(status="finished")
            print("***************finished")

        elif (check_value != 0) and (not file_exists):
            # PID 掛掉，而且檔案不存在 -> expired
            existJobs.jobs.filter(processID=tmp_PID, jobID=tmp_jobID).update(status="expired")
            print("***************expired")


def germline_function(newJobID,uploadFile_url,resultFile_url,sampleID,request):     #resultFile_url 是要自己設字的/miRTI/media/patient/{newjobID}/germline/資料夾內 才是生成的資料
        print("germline_function start !!!")
        if uploadFile_url.endswith(".vcf"):
            ann_command = f"python3 /miRTI/hw1/annovar_pipeline0_3.py -input {uploadFile_url} -output {resultFile_url}"
        log_file_path = os.path.join('media', 'patient', newJobID, 'germline', 'logFile.txt')
        command = f"nohup {ann_command} > {log_file_path} &"
        print("ready to annotate")
        os.system(command)
        if command:
            os.system(command)
            print("command executed")
        if poll_annovar_completion(f'media/patient/{newJobID}/germline/', sampleID):
            print("annovar.py 執行完畢")
            existJobs.jobs.filter(jobID=newJobID).update(status="finished")

            # 更新状态为 finished 后，立即执行 select_job_for_interpretation 的逻辑
            finished_jobs = existJobs.jobs.filter(status="finished")
            print("已完成的工作")
            print(finished_jobs)
            if finished_jobs.exists():
                    first_record = finished_jobs.filter(jobID=newJobID).first()
                    if first_record:
                        select_job = first_record.jobID
                        print(f'current job is : {select_job}')
                    else:
                        print('No job found with the specified jobID.')
                    if select_job == "none":
                        parameters = {'finished_jobs': finished_jobs, 'select_ID': select_job}

                    else:
                        pickle_exist = check_pickle_exist(select_job)
                        config_list = getConfig(select_job)

                        if pickle_exist:
                            parameters = load_parameters(request)
                            parameters['syndrome'] = first_record.name
                            parameters['pickle_exist'] = pickle_exist
                            parameters['config_list'] = config_list
                        else:
                            parameters = {
                                'finished_jobs': finished_jobs,
                                'select_ID': select_job,
                                'sampleID': first_record.subject_id,
                                'syndrome': first_record.name,
                                'pickle_exist': pickle_exist,
                                'config_list': config_list
                            }


                    print(parameters)
                    if select_job != 'none':
                            strategy = 'A'
                            review_status = '0'
                            front_info_path = f"/miRTI/media/patient/{newJobID}/germline/front_info.txt"
                            # sampleID = data.get('subject_id', '')  
                            with open(front_info_path, 'r', encoding='utf-8') as file:
                                data = json.load(file)
                            MAF_cutoff = data['MAF_cutoff_germline']
                            Min_DP_cutoff = data['min_dp_cutoff']
                            Min_AAF = data['min_aaf']
                            filtering = 'False'
                            frontendJson = data['gene_panel_list']

                            print(f'Strategy is: {strategy}')
                            # print(f'Review status is: {review_status}')
                            print(f'MAF cutoff is : {MAF_cutoff}')
                            print(f'Min dp cutoff is : {Min_DP_cutoff}')
                            print(f'Min aaf is : {Min_AAF}')
                            # print(f'Filtering options is : {filtering}')
                            if strategy != "Cancer":

                                print(frontendJson)
                                frontendJsonContent = frontendJson
                                # type(frontendJsonContent) # dict
                                # print(frontendJsonContent.keys())  # ['HPOterm', 'GenePanelList']
                                
                                # 處理gene panel list
                                aggregateDict = genePanelListProcessing(frontendJsonContent['GenePanelList'])

                                print(aggregateDict)
                                gene_panel = aggregateDict['genes']
                                panelNames = aggregateDict['panelNames']
                                genePanelDataFrame = aggregateDict['result']

                                hpoTermIds = extractHpoIds(panelNames)


                                print("*****************test")
                                print(gene_panel)
                                print("****************************")
                                print(panelNames)
                                print("****************************")
                                print(genePanelDataFrame)
                                print("****************************")
                                print(hpoTermIds)
                                if isinstance(frontendJson, str):
                                    try:
                                        frontendJsonContent = frontendJson
                                    except json.JSONDecodeError:
                                        # 如果解析失敗，frontendJson 可能已經是一個字典
                                        print("frontendJson 解析失敗，請檢查輸入數據。")
                                        frontendJsonContent = {}
                                elif isinstance(frontendJson, dict):
                                    # 如果 frontendJson 已經是一個字典，直接使用它
                                    frontendJsonContent = frontendJson
                                else:
                                    raise TypeError("Invalid type for JSON content")

                                # 確認 frontendJsonContent 是字典，避免後續操作報錯
                                if not isinstance(frontendJsonContent, dict):
                                    raise ValueError("Parsed JSON content is not a dictionary")

                                # 處理 gene panel list
                                aggregateDict = genePanelListProcessing(frontendJsonContent.get('GenePanelList', []))

                                print(aggregateDict)
                                gene_panel = aggregateDict['genes']
                                panelNames = aggregateDict['panelNames']
                                genePanelDataFrame = aggregateDict['result']

                                hpoTermIds = extractHpoIds(panelNames)

                                print("*****************test")
                                print(gene_panel)
                                print("****************************")
                                print(panelNames)
                                print("****************************")
                                print(genePanelDataFrame)
                                print("****************************")
                                print(hpoTermIds)
                                if len(hpoTermIds)!=0:
                                    # request Amelie phenotype driven ranking score from API
                                    amelieResultDict = requestAmelieAPI(request,hpoTermIds,gene_panel)

                                    # post-processing for requested result
                                    amelieResultTable = pd.DataFrame({'Genes':amelieResultDict.keys()})
                                    amelieResultTable['Max_Score'] = amelieResultTable['Genes'].apply(lambda x: round(max(dict(amelieResultDict[x]).values()),2))
                                    amelieResultTable['Mean_Score'] = amelieResultTable['Genes'].apply(lambda x: round(sum(dict(amelieResultDict[x]).values())/len(dict(amelieResultDict[x]).values()),2))
                                    amelieResultTable['Number_of_References'] = amelieResultTable['Genes'].apply(lambda x: len(dict(amelieResultDict[x]).values()))
                                    amelieResultTable['References_List'] = amelieResultTable['Genes'].apply(lambda x: list(dict(amelieResultDict[x]).keys()))
                                    amelieResultTable['Scores_List'] = amelieResultTable['Genes'].apply(lambda x: list(dict(amelieResultDict[x]).values()))

                                    # merge result
                                    genePanelDataFrame = genePanelDataFrame.merge(amelieResultTable,on='Genes',how='outer').fillna(-1)
                                    genePanelDataFrame['Number_of_References'] = genePanelDataFrame['Number_of_References'].to_numpy(int)
                                    # hpoTermIds 為空時，新增同樣的欄位並塞空值
                                else:
                                    genePanelDataFrame['Max_Score'] = -1
                                    genePanelDataFrame['Mean_Score'] = -1
                                    genePanelDataFrame['Number_of_References'] = -1
                                    genePanelDataFrame['References_List'] = -1
                                    genePanelDataFrame['Scores_List'] = -1
                                
                                # 輸出整理完的表格
                                genePanelDataFrame.to_csv('media/patient/'+newJobID+'/germline/GenePanelDataFrame.tsv',sep='\t',index=None)

                                # 將新表格塞回去
                                aggregateDict['result'] = genePanelDataFrame

                                #gene_panel = adjust_genePanel(gene_panel_text)
                                print('gene panel is :')
                                print(gene_panel)
                            config_values = [strategy, review_status, MAF_cutoff, Min_DP_cutoff, Min_AAF, filtering]
                            config_keys = ['strategy',  'review_status','MAF_cutoff', 'Min_DP_cutoff', 'Min_AAF','filtering']
                            config = dict(zip(config_keys, config_values))
                            # 將json資料加入config中
                            config.update(frontendJsonContent)
                            print("***********config,select_job,config_name")
                            print(config)
                            print("**********")
                            print(select_job)

                            # save config as json
                            try:
                                print("success")
                                min_aaf_value = float(Min_AAF)
                            except ValueError:
                                print("false Min_aaf")
                            

                            # 檢查並轉換 Min_DP_cutoff
                            try:
                                print("success")
                                min_dp_cutoff_value = int(Min_DP_cutoff)
                            except ValueError:
                                print("false Min_DP")
                            
                            
                            #### load annotated table and genotype table ####
                            finished_job = finished_jobs.filter(jobID=select_job)[0]
                            annotated_file = resultFile_url
                            input_file = uploadFile_url
                            sampleID = sampleID

                            annot_table = pd.read_csv(annotated_file, sep='\t')
                            
                            regex = re.compile('.vcf$')
                            if regex.search(input_file):
                                gt_input_file = regex.sub('_tmp.avinput', input_file)
                                gt_input = pd.read_csv(gt_input_file, sep='\t', header=None, usecols=[0, 1, 2, 3, 4, 5, 6, 7, 9, 14, 16, 17])
                                
                                av_processor = preprocessor(gt_input, min_aaf_value, min_dp_cutoff_value)
                                start_time = time.time()
                                gt_input = av_processor.start_processing()
                                print('Elapse time:' + str(time.time() - start_time))
                            else:
                                gt_input_file = input_file
                                gt_input = pd.read_csv(gt_input_file, sep='\t', header=None)
                                gt_input = gt_input.rename(
                                    columns={0: 'Chr', 1: 'Start', 2: 'End', 3: 'Ref', 4: 'Alt', 5: 'GT', 6: 'QUAL', 7: 'DP'})
                                gt_input['VAF'] = 0.5
                                gt_input['AD'] = '250,250'
                            print("*********gt_input_file")
                            print(gt_input_file)
                            
                            if strategy != "Cancer":
                                WES_layer = WES_layering(annotation_table=annot_table,
                                                        genotype_table=gt_input,
                                                        gene_panel=gene_panel,
                                                        MAF_cutoff=MAF_cutoff,
                                                        review_status=review_status,
                                                        phenotypeDrivenRanking=genePanelDataFrame)
                                
                                parameters = WES_layer.layering()
                                print(parameters)
                                print("****************parameters\n")
                                print(parameters['known_pheno_variant'])
                                # x=parameters['known_pheno_variant']
                                # x.to_csv('/home/uuuwei0504/下載/VIP_germline-main/VIP/test/known_variants,csv',index=False)
                                print("****************test\n")
                                for tmp_key in ['known_pheno_variant', 'suspect_pheno_variant', 'other_variant',
                                                'two_hit_pheno_variant', 'homo_pheno_variant']:
                                    if parameters[tmp_key].shape[0] != 0:
                                        parameters[tmp_key].index = parameters[tmp_key].apply(createVariantIndex, axis=1)
                                        parameters[tmp_key]['checked'] = 'off'
                            
                            variantIndices = list()
                            for tmp_key in ['known_pheno_variant', 'suspect_pheno_variant', 'other_variant', 'two_hit_pheno_variant',
                                            'homo_pheno_variant']:
                                if parameters[tmp_key].shape[0] != 0:
                                    variantIndices = variantIndices + list(parameters[tmp_key].index)
                                # print(aggregateDict)
                            reportIndex = pd.DataFrame(index=pd.unique(variantIndices))
                            reportIndex['report'] = 'off'
                            parameters['reportIndex'] = reportIndex

                            ## count number of variants in each layer and put it into parameter
                            number_of_phenotype_associated_variant = parameters['known_pheno_variant'].shape[0]
                            number_of_incidental_finding_variant = parameters['known_other_variant'].shape[0] + \
                                                                parameters['known_ACMG_variant'].shape[0]
                            number_of_drug_response_variant = parameters['drug_response_variant'].shape[0]
                            number_of_predicted_suspect_variant = parameters['suspect_pheno_variant'].shape[0]
                            number_of_other_variant = parameters['other_variant'].shape[0]

                            parameters['number_of_phenotype_associated_variant'] = number_of_phenotype_associated_variant
                            parameters['number_of_incidental_finding_variant'] = number_of_incidental_finding_variant
                            parameters['number_of_drug_response_variant'] = number_of_drug_response_variant
                            parameters['number_of_predicted_suspect_variant'] = number_of_predicted_suspect_variant
                            parameters['number_of_other_variant'] = number_of_other_variant

                            # other information
                            parameters['gene_panel'] = gene_panel
                            parameters['aggregateDict'] = aggregateDict
                            parameters['maf_cutoff'] = MAF_cutoff
                            parameters['min_aaf'] = Min_AAF
                            parameters['passOnly'] = filtering
                            parameters['min_dp_cutoff'] = Min_DP_cutoff
                            parameters['strategy'] = strategy
                            parameters['review_status'] = review_status

                            # pack these information into pickle file
                            resultFile_path = f"/miRTI/media/patient/{newJobID}/germline/germline_result"
                            with open(resultFile_path + '.pickle', 'wb') as wf:
                                pickle.dump(parameters, wf)

                            parameters['finished_jobs'] = finished_jobs
                            parameters['select_ID'] = select_job
                            parameters['sampleID'] = sampleID
                            parameters['syndrome'] = finished_jobs.filter(jobID=select_job)[0].name

                            get_summary_excel(parameters, select_job, sampleID)

                            print(parameters)

                            print("page3 finished !")


def somatic_pipeline(newjobID):
    factory = RequestFactory()
    body = json.dumps({"newjobid": newjobID}).encode("utf-8")

    req1 = factory.post("/somatic_result", body, content_type="application/json")
    res1 = somatic_result(req1)

    req2 = factory.post("/process_cosmic", body, content_type="application/json")
    res2 = process_cosmic(req2)

    # Step 1: mutisnp_civic
    req3 = factory.post("/mutisnp_civic", body, content_type="application/json")
    res3 = mutisnp_civic(req3)


    factory = RequestFactory()
    body = json.dumps({"newjobid": newjobID}).encode("utf-8")

    # 測試 mutisnp_



    # 整理結果 → decode 變成 dict
    return {
        "mutisnp_civic": json.loads(res3.content),
        "process_cosmic": json.loads(res2.content),
        "somatic_result": json.loads(res1.content)
    }

def run_germline_prediction(
    newJobID: str,
    output_csv_file_path: str,
    tmp_germline_prediction: str,
    request,
    filename_with_ext: str,
    basename: str,
    germline_model: str = '/miRTI/hw1/prediction_germline/models'
):
    """
    將既有的 germline_prediction 區塊封裝為函式，功能與原碼一致。
    依序：
      1) 準備 germline 目錄與資料
      2) 與醫院提供的 predict_blacklist 合併
      3) 產出 tmp_germline_prediction
      4) 重新接收前端參數並寫入 front_info.txt
      5) 呼叫 run(germline_model, germline_input, germline_output)
    備註：此函式假設外部已定義 `run()` 推論函式。
    """

    # ----------------------------------------------germline_prediction_start-----------------------------------
    print("----------------------------------------------germline_prediction_start-----------------------------------")
    germline_path = f'/miRTI/media/patient/{newJobID}/germline'
    os.makedirs(germline_path, exist_ok=True)

    df_germline = pd.read_csv(output_csv_file_path)
    df_gerlmine_list_from_hospital = pd.read_csv('/miRTI/hw1/20250125germline_prediction/predict_blacklist.csv')
    df_gerlmine_list_from_hospital['#Uploaded_variation'] = df_gerlmine_list_from_hospital.apply(
        lambda row: f"{row['Chr']}_{row['Start']}_{row['Ref']}/{row['Alt']}", axis=1
    )

    csv1_keys = set(df_germline['#Uploaded_variation'])
    csv2_keys = set(df_gerlmine_list_from_hospital['#Uploaded_variation'])

    csv2_selected = df_gerlmine_list_from_hospital[
        ['#Uploaded_variation', 'Occurence', 'CntSampleWithVariant', 'FreqConfirmedGermline',
         'FreqConfirmedSomatic', 'is_benign', 'is_pathogenic']
    ]
    duplicates = csv2_selected[csv2_selected.duplicated(subset=['#Uploaded_variation'], keep=False)]
    if not duplicates.empty:
        csv2_selected = csv2_selected.drop_duplicates(subset=['#Uploaded_variation'])

    merged_df = pd.merge(df_germline, csv2_selected, on='#Uploaded_variation', how='left')
    merged_df.to_csv(tmp_germline_prediction, index=False)
    print(f"----------------------germline file path : {tmp_germline_prediction}")

    # ------------------------------------------germline重新接收一次資料 (為求方便)---------------------------------------
    front_info_path = f"/miRTI/media/patient/{newJobID}/germline/front_info.txt"
    data = json.loads(request.body.decode('utf-8'))
    MAF_cutoff_germline = data.get('maf_cutoff_germline', '')
    Min_DP_cutoff = data.get('min_dp_cutoff', '')
    Min_AAF = data.get('min_aaf', '')
    frontendJson = data.get('genePanelList', '')

    response_data = {
        "MAF_cutoff_germline": MAF_cutoff_germline,
        "min_dp_cutoff": Min_DP_cutoff,
        "min_aaf": Min_AAF,
        "gene_panel_list": frontendJson
    }

    # ------------------------------------------germline存資料 存前端的-----------------------
    os.makedirs(os.path.dirname(front_info_path), exist_ok=True)
    with open(front_info_path, 'w', encoding='utf-8') as json_file:
        json.dump(response_data, json_file, indent=4, ensure_ascii=False)

    uploadFile_url = f"/miRTI/media/patient/{newJobID}/{filename_with_ext}"
    resultFile_url = f"/miRTI/media/patient/{newJobID}/germline/{basename}_ann.txt"
    sampleID = basename
    # germline_function(newJobID, uploadFile_url, resultFile_url, sampleID, request)

    # -----------------------------------------load germline_prediction_models and output file--------------------------
    germline_input = tmp_germline_prediction
    germline_output = f'/miRTI/media/patient/{newJobID}/germline/{basename}_germline_prediction_output.csv'

    # 注意：此處依舊呼叫外部已存在的 run() 函式，與原本行為一致
    run(germline_model, germline_input, germline_output)
    germline_df = pd.read_csv(germline_output)
    germline_df = germline_df.dropna(subset=['VAF'])
    MAF_cutoff_germline = float(MAF_cutoff_germline)
    germline_df['VAF']=pd.to_numeric(germline_df['VAF'], errors='coerce')
    filtered_germline = germline_df[(germline_df['is_Germline'] == 1) & (germline_df['VAF'] > MAF_cutoff_germline)]

    filtered_germline.to_csv(f'/miRTI/media/patient/{newJobID}/heridty1.csv', index=False)    

    # 方便上層如果要用到路徑或結果
    return {
        "germline_path": germline_path,
        "tmp_germline_prediction": tmp_germline_prediction,
        "front_info_path": front_info_path,
        "germline_model": germline_model,
        "germline_input": germline_input,
        "germline_output": germline_output,
        "response_data": response_data
    }

def run_vep_and_annovar(newJobID, file_name, MAF_cutoff, uploadFile_url,Min_AAF,Min_DP_cutoff):
    """
    執行 VEP (三個 docker)、mane select、ANNOVAR、黑名單過濾、臨床資料庫 annotate，
    並輸出分類結果 CSV。
    """

    #--------------------------------------------------------VEP----------------------------------------------------
    os.environ['vep_db_path'] = '/media/disk2/uuuwei0504/VEP/database/'
    os.environ['ref_fasta_path'] = '/media/disk2/uuuwei0504/VEP/hg19/'
    vep_db_path = os.getenv('vep_db_path')
    ref_fasta_path = os.getenv('ref_fasta_path')

    print("VEP Database Path:", vep_db_path)
    print("Reference FASTA Path:", ref_fasta_path)

    docker_command1 = [
        'docker', 'run', '--rm',
        '-v', f'/media/disk2/uuuwei0504/VEP:/workdir',
        '-v', f'{vep_db_path}:/opt/vep/.vep/',
        '-v', f'{ref_fasta_path}:/opt/vep/.vep/Ref/',
        'ensemblorg/ensembl-vep:release_112.0',
        'vep', '--offline',  '--assembly', 'GRCh37',
        '-i', f'/workdir/result/{file_name}',
        '--fasta', 'Ref/ucsc.hg19.fasta',
        '--no_stats', '--hgvs', '--numbers',
        '--biotype', '--canonical', '--symbol',
        '--total_length', '--variant_class',
        '--tab', '--output_file', f'/workdir/newjobid/{newJobID}/unfiltered.vep.txt',
        '--force_overwrite', '--fork', '12',
        '--refseq',
        '--warning_file', '/workdir/result/warnings.log'
    ]
    docker_command2 = [
        'docker', 'run', '--rm',
        '-v', f'/media/disk2/uuuwei0504/VEP:/workdir',
        '-v', f'{vep_db_path}:/opt/vep/.vep/',
        '-v', f'{ref_fasta_path}:/opt/vep/.vep/Ref/',
        'ensemblorg/ensembl-vep:release_112.0',
        'vep', '--offline', '--assembly', 'GRCh37',
        '-i', f'/workdir/result/{file_name}',
        '--fasta', 'Ref/ucsc.hg19.fasta',
        '--no_stats', '--hgvs', '--numbers',
        '--biotype', '--canonical', '--symbol',
        '--total_length', '--variant_class',
        '--tab', '--output_file', f'/workdir/newjobid/{newJobID}/pick_orfer.vep.txt',
        '--force_overwrite', '--fork', '12',
        '--refseq',
        '--warning_file', '/workdir/result/warnings.log',
        '--pick', '--pick_order', 'canonical,length'
    ]
    docker_command3 = [
        'docker', 'run', '--rm',
        '-v', f'/media/disk2/uuuwei0504/VEP:/workdir',
        '-v', f'{vep_db_path}:/opt/vep/.vep/',
        '-v', f'{ref_fasta_path}:/opt/vep/.vep/Ref/',
        'ensemblorg/ensembl-vep:release_112.0',
        'vep', '--offline',  '--assembly', 'GRCh37',
        '-i', f'/workdir/result/{file_name}',
        '--fasta', 'Ref/ucsc.hg19.fasta',
        '--no_stats', '--hgvs', '--numbers',
        '--biotype', '--canonical', '--symbol',
        '--total_length', '--variant_class',
        '--tab', '--output_file', f'/workdir/newjobid/{newJobID}/vep_add_ensambal.vep.txt',
        '--force_overwrite', '--fork', '12',
        '--warning_file', '/workdir/result/warnings.log'
    ]

    subprocess.run(docker_command1, check=True)
    subprocess.run(docker_command2, check=True)
    subprocess.run(docker_command3, check=True)

    print('--------------------VEP END --------------')

    #--------------------------------------------------------VEP mane select----------------------------------------
    docker_txt1 = f'/VEP/newjobid/{newJobID}/unfiltered.vep.txt'
    docker_txt2 = f'/VEP/newjobid/{newJobID}/pick_orfer.vep.txt'
    docker_txt3 = f'/VEP/newjobid/{newJobID}/vep_add_ensambal.vep.txt'

    docker_csv1 = f'/VEP/newjobid/{newJobID}/unfiltered.vep.csv'
    docker_csv2 = f'/VEP/newjobid/{newJobID}/pick_orfer.vep.csv'
    vep_add_ensambl = os.path.join(os.path.dirname(uploadFile_url), 'vep_add_ensambl.csv')
    final_merge = os.path.join(os.path.dirname(uploadFile_url), 'final_merge.csv')
    final_merge_ensambl_variant = os.path.join(os.path.dirname(uploadFile_url), 'final_merge_add_ensambl_variant.csv')
    merge_menaselect_vep = f'/VEP/newjobid/{newJobID}/merge_menaselect_vep.csv'
    maneselect_file = f'/VEP/HGNC_main_table.csv'

    veptxt_to_csv(docker_txt1, docker_csv1)
    veptxt_to_csv(docker_txt2, docker_csv2)
    veptxt_to_csv(docker_txt3, vep_add_ensambl)
    maneselect_and_vep(maneselect_file, docker_csv1, merge_menaselect_vep)
    compare(merge_menaselect_vep, docker_csv2, final_merge)
    add_ensambl_variant(vep_add_ensambl, final_merge, final_merge_ensambl_variant)

    #--------------------------------------------------------ANNOVAR-----------------------------------------------
    print('--------------------annovar start--------- ')
    start = time.time()

    job = existJobs.jobs.get(jobID=newJobID)
    sampleID = job.subject_id
    uploadFile_url = job.uploadFile_url
    resultFile_url = job.resultFile_url

    filename_with_ext = os.path.basename(uploadFile_url)
    basename, _ = os.path.splitext(filename_with_ext)
    path = os.path.dirname(uploadFile_url)
    germline = os.path.dirname(uploadFile_url)
    new_uploadFile_url = os.path.join(path, basename)

    annovar_path = "/annovar"
    humandb = "/annovar/humandb"
    clinicaldb_path = "/annovar/somatic/clinicaldb/"

    fasta_file = '/annovar/humandb/ucsc_hg19.fa'
    reference = SeqIO.to_dict(SeqIO.parse(fasta_file, 'fasta'))
    with open(os.path.join(humandb, "annovar_to_approved_symbol.json"), 'r') as file:
        genedict = json.load(file)

    tmp_output_avinput = new_uploadFile_url + '.output.avinput'
    tmp_output_annovar = new_uploadFile_url + '_annovar_final.txt'
    tmp_annovar = new_uploadFile_url + '_annotate'
    tmp_annovar_merge_vep = new_uploadFile_url + '_vep_annovar_merge.csv'

    tmp_germline_prediction = f'{germline}/germline/{filename_with_ext}_germline_prediction.csv'
    existJobs.jobs.filter(jobID=newJobID).update(resultFile_url=tmp_annovar_merge_vep)

    avinputdf = prepareAVINPUT(uploadFile_url, tmp_output_avinput)
    existJobs.jobs.filter(jobID=newJobID).update(status="running")

    annovar_cmd = (
        f"perl {annovar_path}/table_annovar.pl "
        f"{tmp_output_avinput} "
        f"{humandb} "
        f"-buildver hg19 -out {tmp_annovar} -remove "
        f"-protocol refGene,avsnp150,ClinGen_annotation,gnomad211_genome,Taiwan_Biobank,LOVD_all,clinvar_20240407,cosmic90_coding,dbnsfp35a,CIVIC_annotation,OCP_ver2,1000g2015aug_all "
        f"-operation g,f,f,f,f,f,f,f,f,f,f,f "
        f"-nastring . --thread 16 --otherinfo "
    )

    print(annovar_cmd)
    subprocess.run(annovar_cmd, shell=True)
#--------------------------------------------------BLacklist Filter-----------------------------------------------
    # Blacklist
    blacklist_path = "/miRTI/media/reference/Blacklist/blacklist_V8.1.xlsx"
    blacklist_df = pd.read_excel(blacklist_path, sheet_name="工作表1")

    multianno = pd.read_csv(f"""{tmp_annovar}.hg19_multianno.txt""", sep='\t', header=0)
    annovardf = process_annovar_results(multianno, avinputdf, os.path.join(path, f"{basename}_annovar_final.txt"))

    blacklist_rsids = blacklist_df['dbsnp'].dropna().unique()
    annovardf = annovardf[~annovardf['avsnp150'].isin(blacklist_rsids)]

    annovardf['Gene'] = annovardf['Gene.refGene'].apply(lambda x: genedict.get(x, x))
# ------------------------------------------------Variant QC------------------------------------------------------
    if 'AF' in annovardf.columns:
        annovardf['AF'] = pd.to_numeric(annovardf['AF'], errors='coerce')
        annovardf = annovardf[annovardf['AF'] <= MAF_cutoff]
    if 'DP' in annovardf.columns:
        print("DPDPDPDP")
        annovardf['DP'] = pd.to_numeric(annovardf['DP'], errors='coerce')

        try:
            cutoff_val = float(Min_DP_cutoff)
        except (ValueError, TypeError):
            cutoff_val = 20.0  # 給預設值 錯誤就給20 DP
        print(cutoff_val)
        annovardf = annovardf[annovardf['DP'] >= cutoff_val]



# ----------------------------------------------Population and Functional and Cancer Classification---------------------------
    # Annotate DB
    CGIdf = annotate_CGI(annovardf, clinicaldb_path)
    Oncodf = annotate_oncoKB(CGIdf, clinicaldb_path)
    predictdf = process_predictions(Oncodf)
    predictdf = predictdf.dropna()
    predictdf.to_csv('/miRTI/media/reference/views/tmp.test.txt', sep='\t', index=False)

    actionable_df, heredity_df, COSMIC_df, suspect_df, potential_treatment_df, df_population, df_functional = filter(predictdf,Min_AAF,MAF_cutoff)

    end = time.time()
    print(f"ANNOVAR speed : {end - start} /second")

    #--------------------------------------------------------SAVE CSV----------------------------------------------
    output_dir = os.path.dirname(uploadFile_url)

    os.makedirs(output_dir, exist_ok=True)  # 保險，確保目錄存在
    actionable_df.to_csv(os.path.join(output_dir, 'actionable.csv'), index=False)
    heredity_df.to_csv(os.path.join(output_dir, 'heredity.csv'), index=False)
    COSMIC_df.to_csv(os.path.join(output_dir, 'COSMIC.csv'), index=False)
    suspect_df.to_csv(os.path.join(output_dir, 'suspect.csv'), index=False)
    potential_treatment_df.to_csv(os.path.join(output_dir, 'potential_treatment_df.csv'), index=False)
    df_population.to_csv(os.path.join(output_dir, 'df_population.csv'), index=False)

    print(f"DataFrames 已成功儲存到 {uploadFile_url} 目錄下的 CSV 檔案！")
 #-------------------------------------annovar_addition_vep_csv-------------------------------------
    annovar_file = f'{tmp_output_annovar}'
    output_csv_file_path = f'{tmp_annovar_merge_vep}'

    df_annovarfile = pd.read_csv(annovar_file, delimiter='\t')
    df_annovarfile.columns = df_annovarfile.columns.str.strip()
    print("df_annovarfile columns:", df_annovarfile.columns)

    try:
        df_annovarfile['#Uploaded_variation'] = df_annovarfile.apply(
            lambda row: f"{row['Chr']}_{row['Start']}_{row['Ref']}/{row['Alt']}", axis=1
        )
    except KeyError as e:
        print(f"KeyError: {e}")
        print("Available columns:", df_annovarfile.columns)

    df_annovarfile.to_csv(output_csv_file_path, index=False)
    df_vepfile = pd.read_csv(final_merge_ensambl_variant, delimiter=',', skip_blank_lines=True)
    print(f'The file has been successfully saved to {output_csv_file_path}')

    #--------------------------------------annovar_vep_merge-------------------------------------------
    df1 = df_annovarfile
    df2 = df_vepfile
    print(df1['#Uploaded_variation'])
    print(df2['#Uploaded_variation'])

    print("df1 columns:", df1.columns)
    print("df2 columns:", df2.columns)

    merged_df = pd.merge(df1, df2, on='#Uploaded_variation', how='outer')
    merged_df.fillna("-", inplace=True)

    print("tmp_annovar_merge_vep:")
    print(tmp_annovar_merge_vep)
    merged_df.to_csv(tmp_annovar_merge_vep, index=False)

    #--------------------------------------RETURN------------------------------------------------------
    return {
        "actionable": actionable_df,
        "heredity": heredity_df,
        "cosmic": COSMIC_df,
        "suspect": suspect_df,
        "potential_treatment": potential_treatment_df,
        "population": df_population,
        "functional": df_functional,
        "annovar_vep_merged": merged_df
    }