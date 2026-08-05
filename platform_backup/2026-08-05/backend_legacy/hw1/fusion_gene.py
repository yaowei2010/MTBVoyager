import pandas as pd
import base64
import os
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json


@csrf_exempt
def fusion_gene(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
            newjobid = data.get('newjobid', '')

            folder_path = f"/miRTI/media/patient/{newjobid}"
            fusion_gene_folder = os.path.join(folder_path, "fusion_gene")

            # 前端表格固定讀 annotation 後的結果
            tsv_file_path = os.path.join(fusion_gene_folder, "annotated_fusions.tsv")

            if not os.path.exists(tsv_file_path):
                return JsonResponse(
                    {'error': f'annotated_fusions.tsv not found: {tsv_file_path}'},
                    status=404
                )

            # 讀取 annotated_fusions.tsv
            tsv_data = pd.read_csv(tsv_file_path, sep='\t', dtype=str)

            # 把 NaN 補成 "-"
            tsv_data = tsv_data.fillna("-")

            # 如果前端用 gene1，就把 #gene1 改名成 gene1
            # 其他欄位全部保留，不要刪最後兩欄
            tsv_data = tsv_data.rename(columns={'#gene1': 'gene1'})

            # 這裡不要再做：
            # tsv_data = tsv_data.iloc[:, :-2]
            # 因為最後兩欄通常是 orf_breakpoint5p / orf_breakpoint3p

            tsv_records = tsv_data.to_dict(orient='records')

            # PDF 使用 draw_fusions.R 產生的結果
            pdf_path = os.path.join(fusion_gene_folder, "fusions.pdf")

            if os.path.exists(pdf_path):
                with open(pdf_path, 'rb') as pdf_file:
                    pdf_base64 = base64.b64encode(pdf_file.read()).decode('utf-8')
            else:
                return JsonResponse(
                    {'error': f'PDF file not found: {pdf_path}'},
                    status=404
                )

            response_data = {
                'pdf_base64': pdf_base64,
                'tsv_data': tsv_records,
            }

            return JsonResponse(response_data, safe=False)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Only POST method is allowed'}, status=405)