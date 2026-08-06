import os
import json
import glob
import base64
import subprocess
import pandas as pd
from datetime import datetime, date

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone

from .models import existJobs


def _parse_dob_to_date(dob: str) -> date:
    if dob is None:
        raise ValueError("dob is None")
    s = str(dob).strip()
    if not s:
        raise ValueError("dob is empty")

    s10 = s[:10]
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
        try:
            return datetime.strptime(s10, fmt).date()
        except ValueError:
            pass

    s_digits = "".join(ch for ch in s if ch.isdigit())
    if len(s_digits) == 8:
        return datetime.strptime(s_digits, "%Y%m%d").date()

    raise ValueError(f"Unsupported dob format: {dob}")


def _calc_age(birth_d: date, today: date | None = None) -> int:
    if today is None:
        today = timezone.localdate()
    y = today.year - birth_d.year
    if (today.month, today.day) < (birth_d.month, birth_d.day):
        y -= 1
    return max(y, 0)


def _map_gender_to_sex(gender: str) -> int:
    if gender is None:
        return 0
    g = str(gender).strip().lower()
    if g in ["m", "male", "man", "男", "1"]:
        return 1
    if g in ["f", "female", "woman", "女", "0"]:
        return 0
    return 0


def generate_onconpc_input(data_dir, output_path, age, sex, randid):
    main_df = pd.read_csv(
        "/miRTI/media/reference/onconpc/data/onconpc_processed_cups_data.csv",
        index_col="RANDID"
    )
    all_columns = main_df.columns

    # SBS
    sbs_path = os.path.join(
        data_dir,
        "mutSig/Assignment/Assignment_Solution/Activities/Assignment_Solution_Activities.txt"
    )
    sbs_df = pd.read_csv(sbs_path, sep="\t", index_col=0)
    total = sbs_df.iloc[0].sum()
    sbs_ratio = sbs_df.iloc[0] / total if total != 0 else sbs_df.iloc[0] * 0
    sbs_columns = [col for col in all_columns if col.startswith("SBS")]
    filtered_row = sbs_ratio.reindex(sbs_columns, fill_value=0)

    # Variants -> Gene count
    variant_df = pd.read_csv(os.path.join(data_dir, "potential_treatment_df.csv"))
    gene_counts = variant_df["Gene"].value_counts()
    gene_count_row = pd.Series(0, index=all_columns, dtype=float)
    for gene, count in gene_counts.items():
        if gene in gene_count_row.index:
            gene_count_row[gene] = float(count)

    # VCF -> CNA
    vcf_files = [f for f in os.listdir(data_dir) if f.endswith(".vcf")]
    if not vcf_files:
        raise FileNotFoundError(f"No .vcf found in: {data_dir}")
    uploadFile_url = os.path.join(data_dir, vcf_files[-1])

    vcf_df = pd.read_csv(uploadFile_url, sep="\t", comment="#", header=None)
    if vcf_df.shape[1] < 8:
        raise ValueError("VCF 檔案格式錯誤，無法找到 INFO 欄。")

    info_col = vcf_df[7]
    cnv_gene_values = {}

    for info in info_col:
        parts = dict(item.split("=", 1) for item in str(info).split(";") if "=" in item)
        gene = parts.get("ANT")
        cn = parts.get("CN")
        if gene and cn:
            try:
                gene_key = f"{gene} CNA"
                delta = float(cn) - 2.0
                if delta < -2 or delta > 2:
                    delta = 0.0
                if gene_key in all_columns:
                    cnv_gene_values[gene_key] = cnv_gene_values.get(gene_key, 0.0) + delta
            except ValueError:
                continue

    cnv_row = pd.Series(0.0, index=all_columns, dtype=float)
    for gene, value in cnv_gene_values.items():
        cnv_row[gene] = float(value)

    # Combine
    combined_row = pd.Series(0.0, index=all_columns, dtype=float)
    combined_row.update(filtered_row)
    combined_row = combined_row + gene_count_row + cnv_row

    mean_age = 60.362025
    std_age = 13.034576
    combined_row["Age"] = (float(age) - mean_age) / std_age
    combined_row["Sex"] = int(sex)

    final_df = pd.DataFrame([combined_row], index=[randid])
    final_df.index.name = "RANDID"

    outdir = os.path.dirname(output_path)
    if outdir:
        os.makedirs(outdir, exist_ok=True)
    final_df.to_csv(output_path)

    # debug
    print("write:", output_path)
    print(final_df.loc[randid][final_df.loc[randid] != 0])


@csrf_exempt
def cancertype_prediction(request):
    if request.method != "POST":
        return JsonResponse({"error": "只接受POST請求"}, status=400)

    data = json.loads(request.body.decode("utf-8"))
    newjobid = data.get("newjobid", "")
    print("收到 newjobid:", newjobid)

    # job
    try:
        job = existJobs.jobs.get(jobID=newjobid)
    except existJobs.DoesNotExist:
        return JsonResponse({"error": f"找不到 jobID={newjobid} 的 existJobs"}, status=404)

    # age/sex
    try:
        birth_date = _parse_dob_to_date(job.dob)
        age = _calc_age(birth_date)
    except Exception as e:
        return JsonResponse({
            "error": "DOB 解析失敗",
            "dob": job.dob,
            "details": str(e)
        }, status=400)

    sex = _map_gender_to_sex(job.gender)

    folder_path = f"/miRTI/media/patient/{newjobid}"
    cancer_type_folder = os.path.join(folder_path, "cancer type")
    cancer_type_csv = os.path.join(cancer_type_folder, "cancer_type.csv")
    prediction_summary_csv = os.path.join(cancer_type_folder, "prediction_summary.csv")

    pdf_path = os.path.join(cancer_type_folder, f"{newjobid}.pdf")
    legacy_pdf_path = os.path.join(cancer_type_folder, "filtered.pdf")

    # ---------- helpers ----------
    def _ensure_jobid_pdf():
        if os.path.exists(legacy_pdf_path) and not os.path.exists(pdf_path):
            try:
                os.replace(legacy_pdf_path, pdf_path)
            except OSError:
                pass

    def _is_result_ready() -> bool:
        if not os.path.isdir(cancer_type_folder):
            return False
        if not os.path.exists(cancer_type_csv):
            return False
        if not os.path.exists(prediction_summary_csv):
            return False
        if not (os.path.exists(pdf_path) or os.path.exists(legacy_pdf_path)):
            return False
        return True

    def load_results():
        cancer_type_preview = []
        prediction_summary_preview = []
        pdf_base64 = ""

        if os.path.exists(cancer_type_csv):
            df = pd.read_csv(cancer_type_csv)
            cancer_type_preview = df.to_dict(orient="records")

        if os.path.exists(prediction_summary_csv):
            df = pd.read_csv(prediction_summary_csv)
            prediction_summary_preview = df.to_dict(orient="records")

        _ensure_jobid_pdf()
        target_pdf = pdf_path if os.path.exists(pdf_path) else legacy_pdf_path
        if os.path.exists(target_pdf):
            with open(target_pdf, "rb") as f:
                pdf_base64 = base64.b64encode(f.read()).decode("utf-8")

        return cancer_type_preview, prediction_summary_preview, pdf_base64

    # ---------- ready -> read ----------
    if _is_result_ready():
        cancer_type_preview, prediction_summary_preview, pdf_base64 = load_results()
        return JsonResponse({
            "status": "ready",
            "exists": True,
            "age_used": age,
            "sex_used": sex,
            "cancer_type_preview": cancer_type_preview,
            "prediction_summary_preview": prediction_summary_preview,
            "pdf_base64": pdf_base64
        })

    # ---------- prereq checks ----------
    sbs_path = os.path.join(
        folder_path,
        "mutSig/Assignment/Assignment_Solution/Activities/Assignment_Solution_Activities.txt"
    )
    pt_path = os.path.join(folder_path, "potential_treatment_df.csv")
    vcf_glob = os.path.join(folder_path, "*.vcf")
    vcf_files = glob.glob(vcf_glob)

    if not os.path.exists(sbs_path):
        return JsonResponse({
            "status": "missing_prereq",
            "missing": "mutation_signature",
            "message": "請先執行 mutation signature 的流程，產生 Assignment_Solution_Activities.txt",
            "expected_path": sbs_path
        }, status=409)

    if not os.path.exists(pt_path):
        return JsonResponse({
            "status": "missing_input",
            "missing": "potential_treatment_df.csv",
            "message": "找不到 potential_treatment_df.csv，無法進行 cancer type prediction",
            "expected_path": pt_path
        }, status=400)

    if not vcf_files:
        return JsonResponse({
            "status": "missing_input",
            "missing": "vcf",
            "message": "找不到 .vcf 檔，無法進行 cancer type prediction",
            "expected_glob": vcf_glob
        }, status=400)

    # ---------- run (even if folder exists) ----------
    os.makedirs(cancer_type_folder, exist_ok=True)

    try:
        generate_onconpc_input(
            data_dir=folder_path,
            output_path=cancer_type_csv,
            age=age,
            sex=sex,
            randid=newjobid
        )
    except Exception as e:
        return JsonResponse({
            "error": "generate_onconpc_input 失敗，cancer_type.csv 未產生",
            "details": str(e),
            "cancer_type_csv": cancer_type_csv
        }, status=500)

    if not os.path.exists(cancer_type_csv):
        return JsonResponse({
            "error": "cancer_type.csv 未產生（檔案不存在），中止執行 test.py",
            "cancer_type_csv": cancer_type_csv
        }, status=500)

    try:
        subprocess.run([
            "mamba", "run",
            "-n", "onconpc_conda_env",
            "python3",
            "/miRTI/media/reference/onconpc/python_code/test.py",
            "--csv", cancer_type_csv,
            "--outdir", cancer_type_folder
        ], check=True)
    except subprocess.CalledProcessError as e:
        return JsonResponse({
            "error": "執行 predict_and_explain_onconpc 時出錯",
            "details": str(e)
        }, status=500)

    _ensure_jobid_pdf()

    cancer_type_preview, prediction_summary_preview, pdf_base64 = load_results()
    return JsonResponse({
        "status": "ready",
        "exists": False,
        "age_used": age,
        "sex_used": sex,
        "cancer_type_preview": cancer_type_preview,
        "prediction_summary_preview": prediction_summary_preview,
        "pdf_base64": pdf_base64
    })
