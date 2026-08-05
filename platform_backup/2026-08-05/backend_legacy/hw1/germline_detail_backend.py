import os
import json
import csv
import ast
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import FileSystemStorage
from .models import existJobs
import pickle
import pandas as pd

# ---------------------------
# Safe parse / column fallback
# ---------------------------

def _safe_literal(x, default=None):
    """CSV 內存 dict/list 的欄位，用 literal_eval 安全解析。"""
    if x is None:
        return default
    if isinstance(x, (dict, list)):
        return x
    s = str(x).strip()
    if s in ("", ".", "None", "nan", "NaN"):
        return default
    try:
        return ast.literal_eval(s)
    except Exception:
        return default

def _get_first(row, keys, default=""):
    """從 dict row 依序取第一個存在且非空的欄位。"""
    for k in keys:
        if k in row and row[k] not in (None, "", ".", "None", "nan", "NaN"):
            return row[k]
    return default

def _to_float(x, default=None):
    try:
        if x in (None, "", ".", "None", "nan", "NaN"):
            return default
        return float(x)
    except Exception:
        return default

def _normalize_gender(g):
    g = (g or "").strip().lower()
    if g in ("male", "m"):
        return "male"
    if g in ("female", "f"):
        return "female"
    return ""

def _phenotype_is_missing(v):
    # 你的舊碼用 -1 表示沒有 phenotype，CSV/DF 可能是 -1、"-1"、"."、""、None
    if v is None:
        return True
    s = str(v).strip()
    return s in ("", ".", "None", "-1", "nan", "NaN")

def _build_location(row):
    chr_ = _get_first(row, ["Chr", "chr", "CHROM", "Chrom", "chromosome", "#CHROM"], "")
    start = _get_first(row, ["Start", "start", "POS", "Pos", "pos"], "")
    end = _get_first(row, ["End", "end", "STOP", "Stop", "stop"], start)
    ref = _get_first(row, ["Ref", "ref", "REF"], "")
    alt = _get_first(row, ["Alt", "alt", "ALT"], "")
    if chr_ == "" or start == "":
        return ""
    return f"{chr_}:{start}_{end}{ref}>{alt}"

def _build_omim_match(gender_norm, genotype, phenotype_str):
    """
    依 Phenotype 內最後的 (AD)/(AR)/(XLR)/(XLD) 判斷是否符合條件
    回傳 'O' / 'X'
    """
    if _phenotype_is_missing(phenotype_str):
        return "X"

    s = str(phenotype_str)
    if "(" in s and ")" in s:
        mode = s.split("(")[-1].split(")")[0].strip().upper()
    else:
        mode = ""

    gt = (genotype or "").strip().lower()  # hom/het
    if mode in ("AD", "AR"):
        if mode == "AD" and gt in ("hom", "het"):
            return "O"
        if mode == "AR" and gt == "hom":
            return "O"
        return "X"

    if mode == "XLR":
        if gender_norm == "male" and gt in ("het", "hom"):
            return "O"
        if gender_norm == "female" and gt == "het":
            return "O"
        return "X"

    if mode == "XLD":
        if gender_norm == "male" and gt in ("het", "hom"):
            return "O"
        if gender_norm == "female" and gt == "hom":
            return "O"
        return "X"

    return "X"


# ===========================
# hg38: ClinVar + AlphaMissense
# ===========================

def summarize_known_clinical_evidence_hg38(x: pd.Series) -> pd.Series:
    """
    - 不再依賴 LOVD_all_clinical / LOVD_SIG
    - 產生：
        - clinvar_summary
        - AlphaMissense_out (統一給前端顯示)
    """
    # ---- ClinVar summary (compatible) ----
    # 1) 優先使用已存在的 clinvar_summary（若 pipeline 已算好）
    clinvar_summary = x.get("clinvar_summary", ".")

    if clinvar_summary in (None, "", ".", "None", "nan", "NaN"):
        # 2) 若有 ClinVar 原始欄位（類似你舊碼的 CLN*），就用舊邏輯算 summary
        clinvar_alleleID = x.get("CLNALLELEID", ".")
        clinvar_review_stat = x.get("CLNREVSTAT", ".")
        clinvar_SIG = x.get("CLNSIG", ".")

        review_star_dict = {
            "no_assertion_provided": "0★",
            "no_assertion_criteria_provided": "0★",
            "no_assertion_for_the_individual_variant": "0★",
            "criteria_provided,_conflicting_interpretations": "1★",
            "criteria_provided,_single_submitter": "1★",
            "criteria_provided,_multiple_submitters,_no_conflicts": "2★",
            "reviewed_by_expert_panel": "3★",
            "practice_guideline": "4★",
        }

        if (str(clinvar_alleleID) != ".") and (str(clinvar_SIG) != "."):
            star = review_star_dict.get(str(clinvar_review_stat), "")
            clinvar_summary = str(clinvar_SIG).replace("_", " ")
            clinvar_summary = f"{clinvar_summary}({star})" if star else clinvar_summary
        else:
            clinvar_summary = "."

    x["clinvar_summary"] = clinvar_summary

    # ---- AlphaMissense (flexible column names) ----
    am_class = x.get("AlphaMissense_class", None)
    if am_class in (None, "", ".", "None", "nan", "NaN"):
        am_class = x.get("AlphaMissense_pred", None)
    if am_class in (None, "", ".", "None", "nan", "NaN"):
        am_class = x.get("AlphaMissense_prediction", None)
    if am_class in (None, "", ".", "None", "nan", "NaN"):
        am_class = x.get("alphamissense_class", None)

    am_score = x.get("AlphaMissense_score", None)
    if am_score in (None, "", ".", "None", "nan", "NaN"):
        am_score = x.get("AlphaMissense", None)
    if am_score in (None, "", ".", "None", "nan", "NaN"):
        am_score = x.get("alphamissense_score", None)
    if am_score in (None, "", ".", "None", "nan", "NaN"):
        am_score = x.get("am_score", None)

    if am_class not in (None, "", ".", "None", "nan", "NaN") and am_score not in (None, "", ".", "None", "nan", "NaN"):
        x["AlphaMissense_out"] = f"{am_class} ({am_score})"
    elif am_class not in (None, "", ".", "None", "nan", "NaN"):
        x["AlphaMissense_out"] = str(am_class)
    elif am_score not in (None, "", ".", "None", "nan", "NaN"):
        x["AlphaMissense_out"] = str(am_score)
    else:
        x["AlphaMissense_out"] = "."

    return x


def _row_to_variant_payload(row, gender_norm=""):
    """
    將 pipeline dataframe 的一列（dict）轉成前端需要的 dict（含巢狀 dict）
    hg38：Evidence = ClinVar + AlphaMissense
    """
    location = _build_location(row)

    gene = _get_first(row, ["Gene_refGene", "Gene", "SYMBOL", "Symbol", "gene", "HGNC", "hgnc_symbol"], "-")
    rsid = _get_first(row, ["avsnp150", "rsid", "RSID", "RS_ID", "dbSNP", "ID"], ".")

    maf_gnomad = _get_first(row, ["AF", "gnomAD_AF", "gnomADg_AF", "gnomAD_AF_popmax", "GnomAD_AF"], ".")
    maf_1000g = _get_first(row, ["AF_1000G", "1000G_AF", "ThousandG_AF", "KG_AF"], ".")
    maf_tw = _get_first(row, ["TaiwanBioBank", "TWBB", "TW_Biobank_AF"], ".")

    gt = _get_first(row, ["GT", "Genotype", "genotype"], "")
    vaf = _to_float(_get_first(row, ["VAF", "vaf"], "."), default=None)
    ad = _get_first(row, ["AD", "ad"], "")
    otherinfo10 = _get_first(row, ["Otherinfo10", "otherinfo10"], "")

    clinvar = _get_first(row, ["clinvar_summary", "ClinVar", "clinvar", "clinvar_sig"], ".")
    alpha = _get_first(
        row,
        ["AlphaMissense_out", "AlphaMissense_score", "AlphaMissense_class", "AlphaMissense", "alphamissense_score", "alphamissense_class"],
        ".",
    )

    domain = _get_first(row, ["Interpro_domain", "INTERPRO", "Domain", "domain"], "")

    dele_agree = _get_first(row, ["deleterious_agreed", "deleterious_agree", "patho_agreed"], "0")
    dele_tools = _get_first(row, ["deleterious_tools", "deleterious_tool_count", "patho_tools"], "0")

    splice_agree = _get_first(row, ["splicing_effect_agreed", "splice_agreed"], "0")
    splice_tools = _get_first(row, ["splicing_effect_tools", "splice_tools"], "0")

    phenotype = _get_first(row, ["Phenotype", "phenotype"], None)
    omim_num = _get_first(row, ["OMIM_number", "omim_number", "OMIM", "omim"], "")
    if omim_num in ("None", ".", None, "-1"):
        omim_num = ""

    omim_match = _build_omim_match(gender_norm, gt, phenotype)

    max_score = _get_first(row, ["Max_Score", "Amelie_Max", "amelie_max", "Amelie Max score"], "")
    mean_score = _get_first(row, ["Mean_Score", "Amelie_Mean", "amelie_mean", "Amelie Mean score"], "")

    payload = {
        "Location": location,
        "Gene": gene,
        "RS ID": rsid,
        "MAF": {
            "gnomAD": maf_gnomad,
            "1000G": maf_1000g,
            "TW Biobank": maf_tw,
        },
        "Genotype / VAF": {
            "GT": gt,
            "VAF": vaf if vaf is not None else 0.0,
            "AD": ad,
            "Otherinfo10": otherinfo10,
        },
        "Evidence": {
            "Clinvar": "." if clinvar in ("", None) else clinvar,
            "AlphaMissense": alpha,
        },
        "Domain": domain,
        "Pathogenicity": {
            "Summary": f"({dele_agree}/{dele_tools})",
            "Polyphen2_HVAR": _get_first(row, ["Polyphen2_HVAR_pred", "polyphen2_hvar_pred"], ""),
            "SIFT": _get_first(row, ["SIFT_pred", "sift_pred"], ""),
            "VEST3": _get_first(row, ["VEST3_score", "vest3_score"], ""),
            "MutationTaster": _get_first(row, ["MutationTaster_pred", "mutationtaster_pred"], ""),
            "MetaSVM": _get_first(row, ["MetaSVM_pred", "metasvm_pred"], ""),
            "MetaLR": _get_first(row, ["MetaLR_pred", "metalr_pred"], ""),
            "CADD": _get_first(row, ["CADD_phred", "cadd_phred"], ""),
            "DANN": _get_first(row, ["DANN_score", "dann_score"], ""),
        },
        "Splicing effect": {
            "Summary": f"({splice_agree}/{splice_tools})",
            "dbscsnv ADA score": _get_first(row, ["dbscSNV_ADA_SCORE", "dbscsnv_ada_score"], ""),
            "dbscsnv RF score": _get_first(row, ["dbscSNV_RF_SCORE", "dbscsnv_rf_score"], ""),
            "SPIDEX zscore": _get_first(row, ["dpsi_zscore", "spidex_zscore"], ""),
        },
        "OMIM_number": {
            "Phenotype": phenotype if phenotype is not None else -1,
            "OMIM_number": omim_num,
            "符合條件": omim_match,
        },
        "Amelie Max score": max_score,
        "Amelie Mean score": mean_score,
    }
    return payload


def _load_cached_csv_as_json(csv_path, schema="variant"):
    """
    讀你先前寫入的 result_table/*.csv，回傳 JSON（巢狀 dict 會用 literal_eval 還原）
    schema:
      - 'variant': 用在 known/predicted/other
      - 'drug': 用在 drug_response
    """
    if not os.path.exists(csv_path):
        return None

    data = []
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if schema == "drug":
                data.append({
                    "Location": row.get("Location", ""),
                    "Gene": row.get("Gene", ""),
                    "RS ID": row.get("RS ID", ""),
                    "Drug evidence": row.get("Drug evidence", ""),
                    "Chemical": row.get("Chemical", ""),
                    "ClinVar": row.get("ClinVar", "."),
                })
            else:
                data.append({
                    "Location": row.get("Location", ""),
                    "Gene": row.get("Gene", ""),
                    "RS ID": row.get("RS ID", ""),
                    "MAF": _safe_literal(row.get("MAF"), default={}),
                    "Genotype / VAF": _safe_literal(row.get("Genotype / VAF"), default={}),
                    "Evidence": _safe_literal(row.get("Evidence"), default={}),
                    "Domain": row.get("Domain", ""),
                    "Pathogenicity": _safe_literal(row.get("Pathogenicity"), default={}),
                    "Splicing effect": _safe_literal(row.get("Splicing effect"), default={}),
                    "OMIM_number": _safe_literal(row.get("OMIM_number"), default={}),
                    "Amelie Max score": row.get("Amelie Max score", ""),
                    "Amelie Mean score": row.get("Amelie Mean score", ""),
                })
    return data


def rearrange_location1(variant_table):
    canonical_table = pd.read_csv("hw1/DB/Canonical_gene_table.csv")
    Chr = str(variant_table["Chr"])
    Start = str(variant_table["Start"])
    Ref = variant_table["Ref"]
    Alt = variant_table["Alt"]

    # hg38 可能沒有這些欄位 -> 用 get
    AAchange = variant_table.get("AAChange.refGene", variant_table.get("AAChange_refGene", "."))
    GeneDetail = variant_table.get("GeneDetail.refGene", variant_table.get("GeneDetail_refGene", "."))
    gene_name = variant_table.get("Gene.refGene", variant_table.get("Gene_refGene", variant_table.get("Gene", "")))

    canonical = canonical_table[canonical_table["Gene"] == gene_name]["Transcript"].values

    if AAchange != ".":
        if "NM" in str(AAchange):
            if len(canonical) != 0:
                canonical = canonical[0]
                matching = [s for s in str(AAchange).split(",") if canonical in s]
                if len(matching) != 0:
                    presentString = ":".join(matching[0].split(":")[1:])
                else:
                    canonical = str(AAchange).split(",")[0].split(":")[1]
                    presentString = ":".join(str(AAchange).split(",")[0].split(":")[1:])
                    presentString += "\n(*Noncanonical transcript)"
            else:
                canonical = str(AAchange).split(",")[0].split(":")[1]
                presentString = ":".join(str(AAchange).split(",")[0].split(":")[1:])
                presentString += "\n(*Noncanonical transcript)"
        else:
            presentString = str(AAchange)

    elif GeneDetail != ".":
        if "NM" in str(GeneDetail):
            if len(canonical) != 0:
                canonical = canonical[0]
                matching = [s for s in str(GeneDetail).split(";") if canonical in s]
                if len(matching) != 0:
                    presentString = matching[0]
                else:
                    canonical = str(GeneDetail).split(";")[0].split(":")[1]
                    presentString = str(GeneDetail).split(";")[0]
                    presentString += "\n(*Noncanonical transcript)"
            else:
                canonical = str(GeneDetail).split(";")[0].split(":")[1]
                presentString = str(GeneDetail).split(";")[0]
                presentString += "\n(*Noncanonical transcript)"
        else:
            presentString = str(GeneDetail)
    else:
        canonical = "None"
        func = variant_table.get("Func.refGene", variant_table.get("Func_refGene", "."))
        presentString = str(func)

    location = Chr + ":" + Start + Ref + ">" + Alt + "\n" + presentString
    variant_table["Location"] = location
    variant_table["Canonical"] = canonical
    return variant_table


def _write_variant_csv(csv_path, rows):
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    fieldnames = [
        "Location", "Gene", "RS ID", "MAF", "Genotype / VAF", "Evidence",
        "Domain", "Pathogenicity", "Splicing effect", "OMIM_number",
        "Amelie Max score", "Amelie Mean score",
    ]
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def load_parameters1(pickle_path):
    if not os.path.exists(pickle_path):
        raise FileNotFoundError(f"Pickle file not found: {pickle_path}")

    with open(pickle_path, "rb") as file:
        parameters = pickle.load(file)

    return parameters


def _get_job_and_parameters(newJobID):
    """
    你原本依 existJobs/jobs + pickle 的流程集中在這裡
    """
    finished_jobs = existJobs.jobs.all().filter(status="finished")
    first_record = finished_jobs.filter(jobID=newJobID).first()
    if first_record is None:
        return None, None, None, None

    select_job = first_record.jobID
    gender_norm = _normalize_gender(first_record.gender)

    sampleID = finished_jobs.filter(jobID=select_job)[0].subject_id
    fs = FileSystemStorage()
    parm_pickle = os.path.join(fs.location, "patient", select_job, f"{sampleID}.pickle")
    parameters = load_parameters1(parm_pickle)
    return first_record, gender_norm, parameters, select_job


def modify_table1(parameters, df_names):
    """
    hg38: apply summarize_known_clinical_evidence_hg38 (no LOVD)
    """
    for df_name in df_names:
        df = parameters[df_name]
        df.columns = df.columns.str.replace(".", "_", regex=False)

        # 舊邏輯：1000G_ALL -> AF_1000G（若存在）
        if "1000G_ALL" in df.columns and "AF_1000G" not in df.columns:
            df = df.rename(columns={"1000G_ALL": "AF_1000G"})

        df = df.apply(summarize_known_clinical_evidence_hg38, axis=1)
        parameters[df_name] = df

    return parameters


# ===========================
# Views
# ===========================

@csrf_exempt
def known_pathogenic_to_json(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=405)

    payload = json.loads(request.body.decode("utf-8") or "{}")
    newJobID = payload.get("newjobID")
    if not newJobID:
        return JsonResponse({"error": "missing newjobID"}, status=400)

    folder_path = f"/miRTI/media/patient/{newJobID}/result_table"
    csv_path = os.path.join(folder_path, "known_pheno_variant.csv")

    cached = _load_cached_csv_as_json(csv_path, schema="variant")
    if cached is not None:
        return JsonResponse(cached, safe=False)

    first_record, gender_norm, parameters, _ = _get_job_and_parameters(newJobID)
    if first_record is None:
        return JsonResponse({"error": "No finished job found with the given job ID"}, status=404)

    df = parameters.get("known_pheno_variant")
    if df is None:
        return JsonResponse({"error": "parameters missing known_pheno_variant"}, status=500)

    df = df.apply(rearrange_location1, axis=1)
    parameters["known_pheno_variant"] = df
    parameters = modify_table1(parameters, ["known_pheno_variant"])
    df = parameters["known_pheno_variant"]

    rows = [_row_to_variant_payload(r, gender_norm=gender_norm) for r in df.to_dict(orient="records")]

    _write_variant_csv(csv_path, rows)
    return JsonResponse(rows, safe=False)


@csrf_exempt
def incidental_finding_variant(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=405)

    payload = json.loads(request.body.decode("utf-8") or "{}")
    newJobID = payload.get("newjobID")
    if not newJobID:
        return JsonResponse({"error": "missing newjobID"}, status=400)

    folder_path = f"/miRTI/media/patient/{newJobID}/result_table"
    csv1 = os.path.join(folder_path, "known_acmg_variant_result.csv")
    csv2 = os.path.join(folder_path, "known_other_variant_result.csv")

    c1 = _load_cached_csv_as_json(csv1, schema="variant")
    c2 = _load_cached_csv_as_json(csv2, schema="variant")
    if c1 is not None and c2 is not None:
        return JsonResponse({"data1": c1, "data2": c2}, safe=False)

    first_record, gender_norm, parameters, _ = _get_job_and_parameters(newJobID)
    if first_record is None:
        return JsonResponse({"error": "No finished job found with the given job ID"}, status=404)

    df_acmg = parameters.get("known_ACMG_variant")
    df_other = parameters.get("known_other_variant")
    if df_acmg is None or df_other is None:
        return JsonResponse({"error": "parameters missing known_ACMG_variant or known_other_variant"}, status=500)

    df_acmg = df_acmg.apply(rearrange_location1, axis=1)
    df_other = df_other.apply(rearrange_location1, axis=1)
    parameters["known_ACMG_variant"] = df_acmg
    parameters["known_other_variant"] = df_other
    parameters = modify_table1(parameters, ["known_ACMG_variant", "known_other_variant"])

    df_acmg = parameters["known_ACMG_variant"]
    df_other = parameters["known_other_variant"]

    acmg_rows = [_row_to_variant_payload(r, gender_norm) for r in df_acmg.to_dict(orient="records")]
    other_rows = [_row_to_variant_payload(r, gender_norm) for r in df_other.to_dict(orient="records")]

    _write_variant_csv(csv1, acmg_rows)
    _write_variant_csv(csv2, other_rows)

    return JsonResponse({"data1": acmg_rows, "data2": other_rows}, safe=False)


@csrf_exempt
def predicted_suspect_variant(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=405)

    payload = json.loads(request.body.decode("utf-8") or "{}")
    newJobID = payload.get("newjobID")
    if not newJobID:
        return JsonResponse({"error": "missing newjobID"}, status=400)

    folder_path = f"/miRTI/media/patient/{newJobID}/result_table"
    csv_path = os.path.join(folder_path, "predicted_suspect_variant_result.csv")

    cached = _load_cached_csv_as_json(csv_path, schema="variant")
    if cached is not None:
        return JsonResponse(cached, safe=False)

    first_record, gender_norm, parameters, _ = _get_job_and_parameters(newJobID)
    if first_record is None:
        return JsonResponse({"error": "No finished job found with the given job ID"}, status=404)

    df = parameters.get("suspect_pheno_variant")
    if df is None:
        return JsonResponse({"error": "parameters missing suspect_pheno_variant"}, status=500)

    df = df.apply(rearrange_location1, axis=1)
    parameters["suspect_pheno_variant"] = df
    parameters = modify_table1(parameters, ["suspect_pheno_variant"])
    df = parameters["suspect_pheno_variant"]

    rows = [_row_to_variant_payload(r, gender_norm) for r in df.to_dict(orient="records")]
    _write_variant_csv(csv_path, rows)
    return JsonResponse(rows, safe=False)


@csrf_exempt
def predicted_ACMG_variant(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=405)

    payload = json.loads(request.body.decode("utf-8") or "{}")
    newJobID = payload.get("newjobID")
    if not newJobID:
        return JsonResponse({"error": "missing newjobID"}, status=400)

    folder_path = f"/miRTI/media/patient/{newJobID}/result_table"
    csv_path = os.path.join(folder_path, "predicted_ACMG_variant_result.csv")

    cached = _load_cached_csv_as_json(csv_path, schema="variant")
    if cached is not None:
        return JsonResponse(cached, safe=False)

    first_record, gender_norm, parameters, _ = _get_job_and_parameters(newJobID)
    if first_record is None:
        return JsonResponse({"error": "No finished job found with the given job ID"}, status=404)

    df = parameters.get("suspect_ACMG_variant")
    if df is None:
        return JsonResponse({"error": "parameters missing suspect_ACMG_variant"}, status=500)

    df = df.apply(rearrange_location1, axis=1)
    parameters["suspect_ACMG_variant"] = df
    parameters = modify_table1(parameters, ["suspect_ACMG_variant"])
    df = parameters["suspect_ACMG_variant"]

    rows = [_row_to_variant_payload(r, gender_norm) for r in df.to_dict(orient="records")]
    _write_variant_csv(csv_path, rows)
    return JsonResponse(rows, safe=False)


@csrf_exempt
def predicted_other_variant(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=405)

    payload = json.loads(request.body.decode("utf-8") or "{}")
    newJobID = payload.get("newjobID")
    if not newJobID:
        return JsonResponse({"error": "missing newjobID"}, status=400)

    folder_path = f"/miRTI/media/patient/{newJobID}/result_table"
    csv_path = os.path.join(folder_path, "predicted_other_variant_result.csv")

    cached = _load_cached_csv_as_json(csv_path, schema="variant")
    if cached is not None:
        return JsonResponse(cached, safe=False)

    first_record, gender_norm, parameters, _ = _get_job_and_parameters(newJobID)
    if first_record is None:
        return JsonResponse({"error": "No finished job found with the given job ID"}, status=404)

    df = parameters.get("suspect_other_variant")
    if df is None:
        return JsonResponse({"error": "parameters missing suspect_other_variant"}, status=500)

    df = df.apply(rearrange_location1, axis=1)
    parameters["suspect_other_variant"] = df
    parameters = modify_table1(parameters, ["suspect_other_variant"])
    df = parameters["suspect_other_variant"]

    rows = [_row_to_variant_payload(r, gender_norm) for r in df.to_dict(orient="records")]
    _write_variant_csv(csv_path, rows)
    return JsonResponse(rows, safe=False)


@csrf_exempt
def other_variant(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=405)

    payload = json.loads(request.body.decode("utf-8") or "{}")
    newJobID = payload.get("newjobID")
    if not newJobID:
        return JsonResponse({"error": "missing newjobID"}, status=400)

    folder_path = f"/miRTI/media/patient/{newJobID}/result_table"
    csv_path = os.path.join(folder_path, "other_variant_result.csv")

    cached = _load_cached_csv_as_json(csv_path, schema="variant")
    if cached is not None:
        return JsonResponse(cached, safe=False)

    first_record, gender_norm, parameters, _ = _get_job_and_parameters(newJobID)
    if first_record is None:
        return JsonResponse({"error": "No finished job found with the given job ID"}, status=404)

    df = parameters.get("other_variant")
    if df is None:
        return JsonResponse({"error": "parameters missing other_variant"}, status=500)

    df = df.apply(rearrange_location1, axis=1)
    parameters["other_variant"] = df
    parameters = modify_table1(parameters, ["other_variant"])
    df = parameters["other_variant"]

    rows = [_row_to_variant_payload(r, gender_norm) for r in df.to_dict(orient="records")]
    _write_variant_csv(csv_path, rows)
    return JsonResponse(rows, safe=False)


@csrf_exempt
def drug_response_variant(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=405)

    payload = json.loads(request.body.decode("utf-8") or "{}")
    newJobID = payload.get("newjobID")
    if not newJobID:
        return JsonResponse({"error": "missing newjobID"}, status=400)

    folder_path = f"/miRTI/media/patient/{newJobID}/result_table"
    csv_path = os.path.join(folder_path, "drug_response_demo.csv")

    cached = _load_cached_csv_as_json(csv_path, schema="drug")
    if cached is not None:
        return JsonResponse({"data": cached}, safe=False)

    first_record, gender_norm, parameters, _ = _get_job_and_parameters(newJobID)
    if first_record is None:
        return JsonResponse({"error": "No finished job found with the given job ID"}, status=404)

    df = parameters.get("drug_response_demo")
    if df is None:
        return JsonResponse({"error": "parameters missing drug_response_demo"}, status=500)

    df = df.apply(rearrange_location1, axis=1)
    parameters["drug_response_demo"] = df
    parameters = modify_table1(parameters, ["drug_response_demo"])
    df = parameters["drug_response_demo"]

    rows = []
    for r in df.to_dict(orient="records"):
        rows.append({
            "Location": _build_location(r),
            "Gene": _get_first(r, ["Gene_refGene", "Gene", "SYMBOL", "Symbol"], ""),
            "RS ID": _get_first(r, ["avsnp150", "rsid", "RSID", "ID"], ""),
            "Drug evidence": _get_first(r, ["response_summary", "Drug evidence", "drug_evidence"], ""),
            "Chemical": _get_first(r, ["Chemicals", "Chemical", "chemicals"], ""),
            "ClinVar": _get_first(r, ["clinvar_summary", "ClinVar"], "."),
        })

    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        fieldnames = ["Location", "Gene", "RS ID", "Drug evidence", "Chemical", "ClinVar"]
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    return JsonResponse({"data": rows}, safe=False)
