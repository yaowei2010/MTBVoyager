import pandas as pd
import base64
import os
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import csv
import re
import glob

@csrf_exempt
def fusion_gene(request):
    if request.method == 'POST':
        data = json.loads(request.body.decode('utf-8'))
        newjobid = data.get('newjobid', '')
        #newjobid='WGUIvPqaMA'
        folder_path = f"/miRTI/media/patient/{newjobid}"
        
        tsv_files_path = glob.glob(os.path.join(f'{folder_path}/fusion_gene', "*.tsv"))
        if not tsv_files_path:
            return JsonResponse({'error': 'No TSV file found'}, status=404)
        tsv_file_path = tsv_files_path[0]
        tsv_data = pd.read_csv(tsv_file_path, sep='\t')
        tsv_data = tsv_data.rename(columns={'#gene1':'gene1'})
        tsv_data = tsv_data.iloc[:, :-2]  # 移除最後兩欄
        tsv_data = tsv_data.to_dict(orient='records')  
        pdf_path = f'{folder_path}/fusion_gene/fusions.pdf'
        
        if os.path.exists(pdf_path):
            with open(pdf_path, 'rb') as pdf_file:
                pdf_base64 = base64.b64encode(pdf_file.read()).decode('utf-8')
        else:
            return JsonResponse({'error': 'PDF file not found'}, status=404)
        
        try:
            response_data = {
                'pdf_base64': pdf_base64, 
                'tsv_data': tsv_data, 
                }
            return JsonResponse(response_data, safe=False)
        
        except Exception as e:
            error_response = {'error': str(e)}
            return JsonResponse(error_response, status=500)