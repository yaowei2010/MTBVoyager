import pandas as pd
from django.http import JsonResponse

# 載入資料（只載一次）
df = pd.read_csv("/miRTI/media/reference/Germline_analysis/phenotype_to_genes_20250721.txt", sep="\t")

def search_hpo_genes(request):
    # 從 GET 取得 hpo_id，若沒給就預設用 HP:0025700
    hpo_id = request.GET.get("hpo_id", "HP:0025700")

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
