# from Bio import Entrez

# Entrez.email = "a5619216@gmail.com"  # 請替換為你的 email

# def get_clinvar_url(hgvs_query: str) -> str:
#     """
#     輸入 ClinVar 變異名稱（cache），回傳對應的 ClinVar variation URL 或 'not_found'
#     """
#     # 精準搜尋
#     handle = Entrez.esearch(db="clinvar", term=f"{hgvs_query}[Name]")
#     record = Entrez.read(handle)
#     handle.close()

#     if not record.get("IdList"):
#         return "not_found"

#     cid = record["IdList"][0]
#     # 組出 ClinVar URL
#     escaped = hgvs_query.replace(":", "%3A").replace(">", "%3E")
#     url = f"https://www.ncbi.nlm.nih.gov/clinvar/variation/{cid}/?oq={escaped}&m={escaped}"
#     return url

# if __name__ == "__main__":
#     sample = "NM_002529.4(NTRK1):c.824A>C"
#     link = get_clinvar_url(sample)
#     print(link)




#=================================以上為一筆一筆查==============================

import pandas as pd
from Bio import Entrez


Entrez.email = "a5619216@gmail.com"

def get_clinvar_url(hgvs_query: str) -> str:
    """
    輸入 HGVS 格式的 query_clinvar（如 NM_006180.6(NTRK2):c.1444+927C>A），
    回傳對應的 ClinVar variation 網址
    """
    try:
        handle = Entrez.esearch(db="clinvar", term=f"{hgvs_query}[Name]")
        record = Entrez.read(handle)
        handle.close()

        if not record.get("IdList"):
            return "not_found"

        cid = record["IdList"][0]
        escaped = hgvs_query.replace(":", "%3A").replace(">", "%3E")
        return f"https://www.ncbi.nlm.nih.gov/clinvar/variation/{cid}/?oq={escaped}&m={escaped}"
    except Exception as e:
        return f"error: {str(e)}"

if __name__ == "__main__":

    input_csv_path = "/miRTI/media/reference/Blacklist/somatic_result_blacklist.csv"
    output_csv_path = "/miRTI/media/reference/Blacklist/somatic_result_blacklist_with_ClinvarWebsite.csv"
    df = pd.read_csv(input_csv_path)
    if "query_clinvar" not in df.columns:
        raise ValueError("輸入的 CSV 必須包含 'query_clinvar' 欄位")
    df["clinvar_website"] = df["query_clinvar"].apply(get_clinvar_url)
    df.to_csv(output_csv_path, index=False)



