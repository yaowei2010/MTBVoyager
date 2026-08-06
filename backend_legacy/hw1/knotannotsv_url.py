import subprocess
import os
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from openpyxl import load_workbook
import requests
import pandas as pd
import traceback
# def run_shell_script(script_path,newjobID):

#     os.chdir(os.path.dirname(script_path))
    

#     result = subprocess.run(['python3', script_path,newjobID], capture_output=True, text=True)
    

#     if result.returncode == 0:
#         print("Shell 腳本執行成功")
#         print(result.stdout)
#     else:
#         print("Shell 腳本執行失敗")
#         print(result.stderr)
#         exit(1)
def run_shell_script(script_path, newjobID):
    command = ['python3', script_path, newjobID]
    result = subprocess.run(
        command,
        cwd=os.path.dirname(script_path),
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        print("Shell 腳本執行成功")
        print(result.stdout)
    else:
        print("Shell 腳本執行失敗")
        print(result.stderr)
        raise RuntimeError(f"Shell 腳本錯誤：\n{result.stderr}")
    

# def run_perl_script(perl_script_path, annotSV_file, config_file, out_dir, out_prefix):

#     os.chdir(os.path.dirname(perl_script_path))
    
#     command = [
#         'perl', perl_script_path,
#         '--annotSVfile', annotSV_file,
#         '--configFile', config_file,
#         '--outDir', out_dir,
#         '--outPrefix', out_prefix
#     ]
    
#     # 使用 subprocess 執行 perl 腳本
#     result = subprocess.run(command, capture_output=True, text=True)
    
#     # 檢查執行結果
#     if result.returncode == 0:
#         print("Perl 腳本執行成功")
#         print(result.stdout)
#     else:
#         print("Perl 腳本執行失敗")
#         print(result.stderr)
#         exit(1)
def run_perl_script(perl_script_path, annotSV_file, config_file, out_dir, out_prefix):
    command = [
        'perl', perl_script_path,
        '--annotSVfile', annotSV_file,
        '--configFile', config_file,
        '--outDir', out_dir,
        '--outPrefix', out_prefix
    ]
    result = subprocess.run(
        command,
        cwd=os.path.dirname(perl_script_path),
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        print("Perl 腳本執行成功")
        print(result.stdout)
    else:
        print("Perl 腳本執行失敗")
        print(result.stderr)
        raise RuntimeError(f"Perl 腳本錯誤：\n{result.stderr}")


# shell_script_path = "/media/disk2/uuuwei0504/test_annotsv.sh"

# perl_script_path = "/media/disk2/uuuwei0504/annotsv_git_hub/knotAnnotSV/knotAnnotSV2XL.pl"
# annotSV_file = "/media/disk2/uuuwei0504/annotsv/output/23WE0127_S4_genotyped-segments_ann_through_slurm.tsv"
# config_file = "/media/disk2/uuuwei0504/annotsv_git_hub/knotAnnotSV/config_AnnotSV.yaml"
# out_dir = "/media/disk2/uuuwei0504/annotsv_git_hub/knotAnnotSV/example"
# out_prefix = "spreadsheet"
# @csrf_exempt
# def knotannotsv1(request):
#     if request.method == 'GET':
#         print("===================================Knotannotsv=====================================")
#         print("===================================Knotannotsv=====================================")
#         print("===================================Knotannotsv=====================================")
#         print("===================================Knotannotsv=====================================")
#         print("===================================Knotannotsv=====================================")
#         # newjobID='NYjGypKFge'
#         payload = json.loads(request.body.decode("utf-8") or "{}")
#         newjobID = payload.get("newjobID") 
#         shell_script_path = "/miRTI/hw1/knotannotsv/ssh_annotsv.py"
#         perl_script_path = "/miRTI/hw1/knotannotsv/knotannotsv/knotAnnotSV/knotAnnotSV.pl"
#         annotSV_file = f"/annotsv/output1/{newjobID}.tsv"
#         config_file = "/miRTI/hw1/knotannotsv/knotannotsv/knotAnnotSV/config_AnnotSV.yaml"
#         out_dir = f"/miRTI/media/patient/{newjobID}"
#         out_prefix = "knotannotsv"




#         run_shell_script(shell_script_path,newjobID)
#         run_perl_script(perl_script_path, annotSV_file, config_file, out_dir, out_prefix)

#         print("Current working directory:", os.getcwd())
# #        wb = load_workbook(f"/miRTI/media/patient/{newjobID}/spreadsheet_{newjobID}.xlsm", read_only=True)

# #        sheet = wb.active


# #        df = pd.DataFrame(sheet.values)
# #        print(df)
# #        data = df.to_json(orient='records')
#         print("END")
#         return JsonResponse("success", safe=False)

@csrf_exempt
def knotannotsv1(request):
    print("===================================Knotannotsv=====================================")

    # 1) 允許 GET/POST
    if request.method not in ("GET", "POST"):
        return JsonResponse({"error": "Invalid request method"}, status=405)

    # 2) 取 newjobID（POST: body JSON；GET: query string）
    newjobID = None
    if request.method == "POST":
        try:
            payload = json.loads(request.body.decode("utf-8") or "{}")
        except Exception:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        newjobID = payload.get("newjobID") or payload.get("newJobID") or payload.get("newjobid")
    else:  # GET
        newjobID = request.GET.get("newjobID") or request.GET.get("newJobID") or request.GET.get("newjobid")

    if not newjobID:
        return JsonResponse({"error": "missing newjobID"}, status=400)

    # 3) 路徑/參數
    shell_script_path = "/miRTI/hw1/knotannotsv/ssh_annotsv.py"
    perl_script_path = "/miRTI/hw1/knotannotsv/knotannotsv/knotAnnotSV/knotAnnotSV.pl"
    annotSV_file = f"/annotsv/output1/{newjobID}.tsv"
    config_file = "/miRTI/hw1/knotannotsv/knotannotsv/knotAnnotSV/config_AnnotSV.yaml"
    out_dir = f"/miRTI/media/patient/{newjobID}"
    out_prefix = "knotannotsv"

    # 4) 執行（加 try/except 確保不會回 None）
    try:
        # 你原本的 function（需確保它們自己不吞 exception）
        run_shell_script(shell_script_path, newjobID)
        run_perl_script(perl_script_path, annotSV_file, config_file, out_dir, out_prefix)

        print("Current working directory:", os.getcwd())
        print("END")

        # 若你要回 HTML（前端 parseFromString），應該回 text/html
        # 目前先回 JSON 成功（你前端那段是把 response.data 當 HTML，若要維持前端不改，就改成回 HTML）
        return JsonResponse({"status": "success", "newjobID": newjobID}, status=200)

    except Exception as e:
        tb = traceback.format_exc()
        print("[knotannotsv1] ERROR:", tb)
        return JsonResponse(
            {
                "status": "error",
                "message": str(e),
                "traceback": tb,  # 若不想回傳 traceback 可拿掉
                "newjobID": newjobID,
            },
            status=500,
        )

from django.http import FileResponse
from django.http import HttpResponseNotFound

import os

@csrf_exempt
def send_html(request):
    if request.method == 'GET':
        newjobID='NYjGypKFge'

        file_path = f"/miRTI/media/patient/{newjobID}/knotannotsv_{newjobID}.html"
        if os.path.exists(file_path):
            file_name = os.path.basename(file_path)
            response = FileResponse(open(file_path, 'rb'))
            response['Content-Disposition'] = f'attachment; filename="{file_name}"'
            return response
        else:
            return HttpResponseNotFound('File not found')
