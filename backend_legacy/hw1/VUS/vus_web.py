# views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

import json
import re
import tempfile
import subprocess
from pathlib import Path
from typing import Optional
from urllib.parse import unquote
import pandas as pd

from .inhouse_database_search import search_inhouse, get_all_target_tables
from ..models import existJobs

import logging
import traceback

logger = logging.getLogger(__name__)

# ===(A) 工具函式)==============================================================
_AA3_TO_1 = {
    "Ala": "A", "Arg": "R", "Asn": "N", "Asp": "D", "Cys": "C",
    "Gln": "Q", "Glu": "E", "Gly": "G", "His": "H", "Ile": "I",
    "Leu": "L", "Lys": "K", "Met": "M", "Phe": "F", "Pro": "P",
    "Ser": "S", "Thr": "T", "Trp": "W", "Tyr": "Y", "Val": "V",
    "Ter": "*", "Stop": "*", "*": "*"
}


def aa3_to_1(aa: str) -> str:
    if aa is None:
        return ""
    return _AA3_TO_1.get(str(aa).capitalize(), str(aa))


def _normalize_hgvsp_input(s: Optional[str]) -> Optional[str]:
    if s is None:
        return None

    s = str(s).strip()
    if not s or s in {"-", "NA", "N/A", "None", "nan"}:
        return None

    s = unquote(s)
    s = re.split(r"[,;]\s*", s, maxsplit=1)[0].strip()
    return s


def _extract_hgvsp_tail(s: Optional[str]) -> Optional[str]:
    s = _normalize_hgvsp_input(s)
    if not s:
        return None

    if ":p." in s:
        tail = s.split(":p.", 1)[1]
    elif s.startswith("p."):
        tail = s[2:]
    else:
        m = re.search(r"p\.(.+)$", s)
        tail = m.group(1) if m else s

    return tail.strip()


def _hgvsp_get_protein_id(s: Optional[str]) -> Optional[str]:
    s = _normalize_hgvsp_input(s)
    if not s:
        return None

    if ":p." in s:
        pid = s.split(":p.", 1)[0].strip()
        return pid if pid else None

    m = re.search(r"\b((?:NP|XP|YP)_[0-9]+(?:\.[0-9]+)?|ENSP[0-9]+(?:\.[0-9]+)?)\b", s)
    return m.group(1) if m else None


def _convert_aa_seq_3_to_1(seq: str) -> str:
    """
    將像 SerGlyTer 這種連續三碼胺基酸序列轉成 SG*
    """
    if not seq:
        return ""

    tokens = re.findall(r"[A-Z][a-z]{2}|Ter|Stop|\*", seq)
    if not tokens:
        return seq
    return "".join(aa3_to_1(x) for x in tokens)


def _hgvsp_to_short(s: Optional[str]) -> Optional[str]:
    """
    支援：
    - p.Ala123Val              -> A123V
    - p.Trp24Ter               -> W24*
    - p.Thr903=                -> T903T
    - p.Lys382AsnfsTer40       -> K382Nfs*40
    - p.Lys382fs               -> K382fs
    - p.Gly12del               -> G12del
    - p.Lys23dup               -> K23dup
    - p.Gly12delinsSer         -> G12delinsS
    - p.Glu746_Ala750del       -> E746_A750del
    - p.Val721_Cys722insSer    -> V721_C722insS
    - p.Leu747_Thr751delinsPro -> L747_T751delinsP
    """
    tail = _extract_hgvsp_tail(s)
    if not tail:
        return None

    # 1) 一般 substitution / stop / synonymous
    m = re.match(r"^([A-Za-z]{3})(\d+)([A-Za-z]{3}|Ter|Stop|\*|=)$", tail)
    if m:
        ref3, pos, alt3 = m.groups()
        ref1 = aa3_to_1(ref3)

        if alt3 == "=":
            return f"{ref1}{pos}{ref1}"

        if alt3 in {"Ter", "Stop", "*"}:
            return f"{ref1}{pos}*"

        alt1 = aa3_to_1(alt3)
        return f"{ref1}{pos}{alt1}"

    # 2) frameshift: Lys382AsnfsTer40 -> K382Nfs*40
    m = re.match(r"^([A-Za-z]{3})(\d+)([A-Za-z]{3})fs(?:Ter|Stop|\*)(\d+)$", tail)
    if m:
        ref3, pos, alt3, stop_num = m.groups()
        return f"{aa3_to_1(ref3)}{pos}{aa3_to_1(alt3)}fs*{stop_num}"

    # 3) frameshift: Lys382fs -> K382fs
    m = re.match(r"^([A-Za-z]{3})(\d+)fs$", tail, flags=re.IGNORECASE)
    if m:
        ref3, pos = m.groups()
        return f"{aa3_to_1(ref3)}{pos}fs"

    # 4) 單點 del / ins / dup
    m = re.match(r"^([A-Za-z]{3})(\d+)(del|ins|dup)$", tail, flags=re.IGNORECASE)
    if m:
        ref3, pos, op = m.groups()
        return f"{aa3_to_1(ref3)}{pos}{op.lower()}"

    # 5) 單點 delins
    m = re.match(r"^([A-Za-z]{3})(\d+)delins([A-Za-z\*]+)$", tail, flags=re.IGNORECASE)
    if m:
        ref3, pos, ins_seq = m.groups()
        return f"{aa3_to_1(ref3)}{pos}delins{_convert_aa_seq_3_to_1(ins_seq)}"

    # 6) 區間 del / ins / dup
    m = re.match(
        r"^([A-Za-z]{3})(\d+)_([A-Za-z]{3})(\d+)(del|ins|dup)$",
        tail,
        flags=re.IGNORECASE
    )
    if m:
        aa1, pos1, aa2, pos2, op = m.groups()
        return f"{aa3_to_1(aa1)}{pos1}_{aa3_to_1(aa2)}{pos2}{op.lower()}"

    # 7) 區間 delins / ins + inserted aa
    m = re.match(
        r"^([A-Za-z]{3})(\d+)_([A-Za-z]{3})(\d+)(delins|ins)([A-Za-z\*]+)$",
        tail,
        flags=re.IGNORECASE
    )
    if m:
        aa1, pos1, aa2, pos2, op, ins_seq = m.groups()
        ins_short = _convert_aa_seq_3_to_1(ins_seq)
        return f"{aa3_to_1(aa1)}{pos1}_{aa3_to_1(aa2)}{pos2}{op.lower()}{ins_short}"

    # 8) 保底：不要回 None，直接保留原 tail
    return tail


def _hgvsp_to_standard(s: Optional[str]) -> Optional[str]:
    s = _normalize_hgvsp_input(s)
    if not s:
        return None

    protein_id = _hgvsp_get_protein_id(s)
    short_change = _hgvsp_to_short(s)

    if not short_change:
        return None

    if protein_id:
        return f"{protein_id}:p.{short_change}"

    return f"p.{short_change}"


def _vep_consequence_to_variant_class(consequence: Optional[str]) -> str:
    if consequence is None:
        return "Other"

    s = str(consequence).strip()
    if not s or s in {".", "NA", "N/A", "None", "nan"}:
        return "Other"

    terms = re.split(r"[,&]", s)
    terms = [t.strip().lower() for t in terms if t.strip()]

    if any(t == "missense_variant" for t in terms):
        return "Missense_Mutation"
    if any(t == "stop_gained" for t in terms):
        return "Nonsense_Mutation"
    if any(t == "stop_lost" for t in terms):
        return "Nonstop_Mutation"
    if any(t == "frameshift_variant" for t in terms):
        return "Frame_Shift"
    if any(t == "inframe_deletion" for t in terms):
        return "In_Frame_Del"
    if any(t == "inframe_insertion" for t in terms):
        return "In_Frame_Ins"
    if any(t in {
        "splice_acceptor_variant",
        "splice_donor_variant",
        "splice_region_variant",
        "splice_polypyrimidine_tract_variant",
    } for t in terms):
        return "Splice_Site"
    if any(t == "synonymous_variant" for t in terms):
        return "Silent"
    if any(t == "start_lost" for t in terms):
        return "Translation_Start_Site"
    if any(t == "stop_retained_variant" for t in terms):
        return "Silent"
    if any(t == "intron_variant" for t in terms):
        return "Intron"
    if any(t == "5_prime_utr_variant" for t in terms):
        return "5'UTR"
    if any(t == "3_prime_utr_variant" for t in terms):
        return "3'UTR"
    if any(t == "upstream_gene_variant" for t in terms):
        return "5'Flank"
    if any(t == "downstream_gene_variant" for t in terms):
        return "3'Flank"

    return "Other"


def _annovar_to_fallback_consequence(func_refgene: Optional[str], exonic_func_refgene: Optional[str]) -> Optional[str]:
    f = str(func_refgene or "").strip().lower()
    e = str(exonic_func_refgene or "").strip().lower()

    if not f or f in {".", "na", "n/a", "none", "nan"}:
        return None

    if f == "exonic":
        exonic_map = {
            "nonsynonymous snv": "missense_variant",
            "synonymous snv": "synonymous_variant",
            "stopgain": "stop_gained",
            "stoploss": "stop_lost",
            "frameshift substitution": "frameshift_variant",
            "frameshift deletion": "frameshift_variant",
            "frameshift insertion": "frameshift_variant",
            "nonframeshift deletion": "inframe_deletion",
            "nonframeshift insertion": "inframe_insertion",
        }
        if e in exonic_map:
            return exonic_map[e]
        return "coding_sequence_variant"

    if f == "splicing":
        return "splice_region_variant"

    general_map = {
        "intronic": "intron_variant",
        "utr3": "3_prime_utr_variant",
        "utr5": "5_prime_utr_variant",
        "upstream": "upstream_gene_variant",
        "downstream": "downstream_gene_variant",
        "intergenic": "intergenic_variant",
        "ncrna_exonic": "non_coding_transcript_exon_variant",
        "ncrna_intronic": "non_coding_transcript_variant",
    }

    return general_map.get(f)


def _resolve_consequence(row: pd.Series) -> Optional[str]:
    raw_consequence = row.get("Consequence", None)

    if raw_consequence is not None:
        s = str(raw_consequence).strip()
        if s and s not in {".", "-", "NA", "N/A", "None", "nan"}:
            return s

    return _annovar_to_fallback_consequence(
        row.get("Func.refGene", None),
        row.get("ExonicFunc.refGene", None),
    )


def _parse_gene_from_query(q: str) -> str:
    q = q.strip()
    m = re.match(r"^([A-Za-z0-9_-]+)", q)
    return m.group(1).upper() if m else q.upper()


def _extract_job_id(source_table: Optional[str]) -> Optional[str]:
    if not source_table:
        return None
    tok = str(source_table).strip().split()[-1]
    m = re.search(r"(?:vep_annovar_merge_)?([A-Za-z0-9_-]+)$", tok)
    return m.group(1) if m else tok


def _sample_id_from_source_table(source_table: Optional[str]) -> str:
    if not source_table:
        return "Unknown"
    s = str(source_table).strip()
    tok = s.split()[-1] if s else ""
    tok = re.sub(r"^vep_annovar_merge_", "", tok)
    return tok or "Unknown"


def _variant_class_to_oncoprint_class(vc: Optional[str]) -> str:
    s = str(vc or "").strip()

    mapping = {
        "Missense_Mutation": "missense",
        "Silent": "synonymous",
        "Nonsense_Mutation": "stopgain",
        "Nonstop_Mutation": "stoploss",
        "Frame_Shift_Del": "frameshift",
        "Frame_Shift_Ins": "frameshift",
        "Frame_Shift": "frameshift",
        "Splice_Site": "splicing",
        "In_Frame_Del": "inframe_deletion",
        "In_Frame_Ins": "inframe_insertion",
        "Translation_Start_Site": "startloss",
        "Start_Codon_Del": "startloss",
        "Start_Codon_Ins": "startloss",
        "Start_Codon_SNP": "startloss",
    }
    return mapping.get(s, "other")


def _annovar_to_maf(df: pd.DataFrame) -> pd.DataFrame:
    """
    將 ANNOVAR / VEP 風格欄位轉為 MAF 精簡必要欄位。
    """
    df = df.copy()

    maf = pd.DataFrame({
        "Hugo_Symbol": (
            df["Gene.refGene"]
            .astype(str)
            .str.split(r"[,;]", n=1).str[0]
            .str.replace(r"[:\(].*", "", regex=True)
            .str.upper()
        ),
        "Chromosome": df["Chr"].astype(str).str.replace(r"^chr", "", regex=True),
        "Start_Position": pd.to_numeric(df["Start"], errors="coerce").astype("Int64"),
        "End_Position": pd.to_numeric(df["End"], errors="coerce").astype("Int64"),
        "Reference_Allele": df["Ref"].astype(str),
        "Tumor_Seq_Allele2": df["Alt"].astype(str),
    })

    if "source_table" in df.columns:
        maf["Tumor_Sample_Barcode"] = df["source_table"].map(_sample_id_from_source_table)
        maf["Source_Table"] = df["source_table"].astype(str)
    else:
        maf["Tumor_Sample_Barcode"] = "Unknown"
        maf["Source_Table"] = None

    maf["diagnosis"] = df["diagnosis"] if "diagnosis" in df.columns else None

    len_ref = df["Ref"].astype(str).str.len()
    len_alt = df["Alt"].astype(str).str.len()

    maf["Variant_Type"] = "SNP"
    maf.loc[len_ref < len_alt, "Variant_Type"] = "INS"
    maf.loc[len_ref > len_alt, "Variant_Type"] = "DEL"

    eq = (len_ref == len_alt)
    maf.loc[eq & (len_ref == 2), "Variant_Type"] = "DNP"
    maf.loc[eq & (len_ref == 3), "Variant_Type"] = "TNP"
    maf.loc[eq & (len_ref > 3), "Variant_Type"] = "ONP"

    resolved_consequence = df.apply(_resolve_consequence, axis=1)
    maf["Consequence"] = resolved_consequence
    maf["Variant_Classification"] = resolved_consequence.map(_vep_consequence_to_variant_class)

    if "HGVSp" in df.columns:
        hgvsp_series = pd.Series(df["HGVSp"])
        hgvsp_series = hgvsp_series.where(hgvsp_series.notna(), None)
        hgvsp_series = hgvsp_series.map(lambda x: unquote(str(x)) if x is not None else None)

        maf["HGVSp_Original"] = hgvsp_series.replace({"nan": None, "None": None})
        maf["standard_HGVSp"] = hgvsp_series.map(_hgvsp_to_standard)
        maf["Protein_Change"] = hgvsp_series.map(_hgvsp_to_short)
        maf["Protein_ID"] = hgvsp_series.map(_hgvsp_get_protein_id)
    else:
        maf["HGVSp_Original"] = None
        maf["standard_HGVSp"] = pd.Series(df.get("standard_HGVSp", None))
        maf["Protein_Change"] = pd.Series(df.get("Protein_Change", None))
        maf["Protein_ID"] = None

    maf["Func_refGene"] = df.get("Func.refGene", None)
    maf["ExonicFunc_refGene"] = df.get("ExonicFunc.refGene", None)
    maf["Gene_refGene_raw"] = df.get("Gene.refGene", None)

    maf["OncoPrint_Class"] = maf["Variant_Classification"].map(_variant_class_to_oncoprint_class)
    maf["OncoPrint_Visible"] = maf["OncoPrint_Class"].isin({
        "missense",
        "synonymous",
        "stopgain",
        "stoploss",
        "frameshift",
        "splicing",
        "inframe_insertion",
        "inframe_deletion",
        "startloss",
    })

    return maf


def _run_r_lollipop(in_maf_path: Path, gene: str, out_prefix: Path, r_script_path: Path):
    cmd = [
        "mamba", "run", "-n", "arriba",
        "Rscript", str(r_script_path),
        str(in_maf_path), gene, str(out_prefix)
    ]
    subprocess.run(cmd, check=True)

    bundle_path = Path(f"{out_prefix}_bundle.json")
    with open(bundle_path, "r", encoding="utf-8") as f:
        bundle = json.load(f)

    iso_plot_list = []
    for it in bundle.get("isoforms", []):
        pref = it["prefix"]
        mut_df = pd.read_csv(f"{pref}_mutSummary.tsv", sep="\t")
        domain_df = pd.read_csv(f"{pref}_domainDF.tsv", sep="\t")
        with open(f"{pref}_meta.json", "r", encoding="utf-8") as mf:
            meta = json.load(mf)

        plot_data = _build_plot_data(mut_df, domain_df, meta)
        plot_data["isoformID"] = meta.get("isoformID")
        plot_data["nMutations"] = meta.get("nMutations")
        plot_data["refseqID"] = meta.get("titleInfo", {}).get("refseqID")
        plot_data["proteinID"] = meta.get("titleInfo", {}).get("proteinID")
        iso_plot_list.append(plot_data)

    return {
        "gene": bundle.get("gene", gene),
        "defaultIsoform": bundle.get("defaultIsoform"),
        "isoforms": iso_plot_list
    }


def _build_plot_data(mut_df: pd.DataFrame, domain_df: pd.DataFrame, meta: dict) -> dict:
    if not isinstance(meta, dict) or "isoforms" not in meta:
        plot_data = {
            "proteinLength": int(meta["protLen"]),
            "axis": {
                "xTicks": meta["axisInfo"]["x"],
                "yTicks": meta["axisInfo"]["yPos"],
                "yLabels": meta["axisInfo"]["yLab"],
            },
            "title": {
                "text": meta["titleInfo"]["subTitle"],
                "refseqID": meta["titleInfo"].get("refseqID"),
                "proteinID": meta["titleInfo"].get("proteinID"),
                "mutationRate": meta["titleInfo"]["mutationRate"],
            },
            "domains": domain_df[["Start", "End", "Label", "domainCol"]]
                .rename(columns={
                    "Start": "startAA",
                    "End": "endAA",
                    "Label": "name",
                    "domainCol": "color",
                })
                .to_dict(orient="records"),
            "mutations": mut_df[["pos", "count2", "Variant_Classification", "point_col", "conv"]]
                .rename(columns={
                    "pos": "aaPos",
                    "count2": "yValue",
                    "Variant_Classification": "class",
                    "point_col": "color",
                    "conv": "label",
                })
                .to_dict(orient="records"),
            "palettes": {
                "variantColors": meta["colors"]["variantColors"],
                "domainColors": meta["colors"]["domainColors"],
            },
        }
        return plot_data

    iso_list = meta.get("isoforms") or []
    if not iso_list:
        return {"isoforms": [], "defaultIsoform": None}

    if "isoformID" not in mut_df.columns:
        mut_df = mut_df.copy()
        mut_df["isoformID"] = "UNKNOWN"
    if "isoformID" not in domain_df.columns:
        domain_df = domain_df.copy()
        domain_df["isoformID"] = "UNKNOWN"

    def _nm(x):
        try:
            return int(x.get("nMutations", 0))
        except Exception:
            return 0

    default_iso = max(iso_list, key=_nm).get("isoformID")
    out_isoforms = []

    for x in iso_list:
        iso_id = str(x.get("isoformID"))
        if iso_id is None:
            continue

        mut_sub = mut_df[mut_df["isoformID"].astype(str) == iso_id]
        dom_sub = domain_df[domain_df["isoformID"].astype(str) == iso_id]

        axis_info = x.get("axisInfo", {})
        title_info = x.get("titleInfo", {})
        colors = x.get("colors", {})
        prot_len = x.get("protLen", None)

        iso_plot = {
            "isoformID": iso_id,
            "nMutations": int(x.get("nMutations", 0)),
            "proteinLength": int(prot_len) if prot_len is not None else None,
            "axis": {
                "xTicks": axis_info.get("x"),
                "yTicks": axis_info.get("yPos"),
                "yLabels": axis_info.get("yLab"),
            },
            "title": {
                "text": title_info.get("subTitle"),
                "refseqID": title_info.get("refseqID"),
                "proteinID": title_info.get("proteinID"),
                "mutationRate": title_info.get("mutationRate"),
            },
            "domains": (
                dom_sub[["Start", "End", "Label", "domainCol"]]
                .rename(columns={
                    "Start": "startAA",
                    "End": "endAA",
                    "Label": "name",
                    "domainCol": "color",
                })
                .to_dict(orient="records")
                if not dom_sub.empty else []
            ),
            "mutations": (
                mut_sub[["pos", "count2", "Variant_Classification", "point_col", "conv"]]
                .rename(columns={
                    "pos": "aaPos",
                    "count2": "yValue",
                    "Variant_Classification": "class",
                    "point_col": "color",
                    "conv": "label",
                })
                .to_dict(orient="records")
                if not mut_sub.empty else []
            ),
            "palettes": {
                "variantColors": colors.get("variantColors"),
                "domainColors": colors.get("domainColors"),
            },
        }
        out_isoforms.append(iso_plot)

    return {
        "defaultIsoform": default_iso,
        "isoforms": out_isoforms
    }


def _json_500(msg: str, exc: Exception) -> JsonResponse:
    tb = traceback.format_exc(limit=6)
    logger.error("%s\n%s", msg, tb)
    return JsonResponse({"error": msg, "detail": str(exc), "trace": tb}, status=500)


# ===(B) API：variant_lookup)====================================================
@csrf_exempt
def variant_lookup(request):
    """
    POST JSON: { "query": "<gene 或 gene.p.Variant>", "user_id": "<必填>", "skip_plot": <可選 true|false> }
    """
    if request.method != "POST":
        return JsonResponse({"error": "Only POST method allowed"}, status=405)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception as e:
        return JsonResponse({"error": "Invalid JSON payload", "detail": str(e)}, status=400)

    user_input = str(payload.get("query", "")).strip()
    request_user_id = str(payload.get("user_id", "")).strip()
    skip_plot = bool(payload.get("skip_plot", False))

    if not user_input:
        return JsonResponse({"error": "Missing query parameter"}, status=400)
    if not request_user_id:
        return JsonResponse({"error": "Missing user_id"}, status=400)

    schema_name = f"user_{request_user_id}"
    logger.info("🔎 /vus  query=%r  user_id=%s  schema=%s  skip_plot=%s",
                user_input, request_user_id, schema_name, skip_plot)

    try:
        tables = get_all_target_tables(schema_name)
        logger.info("可用 VEP 表（%s）: %s", schema_name, tables)
        if not tables:
            return JsonResponse({"message": f"No VEP tables found in schema {schema_name}."}, status=200)

        full_df: pd.DataFrame = search_inhouse(user_input, schema_name)
        if full_df is None or full_df.empty:
            return JsonResponse({"message": "No matching records found"}, status=200)

        if "source_table" in full_df.columns:
            job_ids = (
                pd.Series(full_df["source_table"])
                .dropna()
                .map(_extract_job_id)
                .dropna()
                .unique()
                .tolist()
            )
        else:
            job_ids = []

        diag_map = {}
        if job_ids:
            qs = existJobs.objects.filter(jobID__in=job_ids, user_id=request_user_id)
            diag_map = {obj.jobID: (obj.diagnosis or "N/A") for obj in qs}

        def _resolve_diag(source_table_val):
            jid = _extract_job_id(source_table_val)
            return diag_map.get(jid, None) if jid else None

        full_df = full_df.copy()
        full_df["diagnosis"] = (
            full_df["source_table"].map(_resolve_diag)
            if "source_table" in full_df.columns else None
        )

        full_df = full_df.where(pd.notnull(full_df), None)
        maf_df_all = _annovar_to_maf(pd.DataFrame(full_df))

        oncoprint_df = maf_df_all.loc[
            maf_df_all["OncoPrint_Visible"] == True,
            [
                "Hugo_Symbol",
                "Tumor_Sample_Barcode",
                "diagnosis",
                "OncoPrint_Class",
                "Protein_Change",
                "Protein_ID",
                "Variant_Classification",
            ]
        ].copy()

        print(
            maf_df_all[
                [
                    "Hugo_Symbol",
                    "Chromosome",
                    "Start_Position",
                    "End_Position",
                    "Func_refGene",
                    "ExonicFunc_refGene",
                    "Consequence",
                    "Variant_Classification",
                    "Protein_Change",
                ]
            ].head(100).to_string()
        )

        oncoprint_df = oncoprint_df.drop_duplicates().reset_index(drop=True)

        plot_data = None
        if not skip_plot:
            try:
                gene = _parse_gene_from_query(user_input)
                R_SCRIPT_PATH = Path(__file__).resolve().parent / "lollipop_cli.R"

                maf_df_plot = maf_df_all.copy()
                maf_df_plot = maf_df_plot[maf_df_plot["Protein_Change"].notna()].reset_index(drop=True)

                with tempfile.TemporaryDirectory() as tmpdir_str:
                    tmpdir = Path(tmpdir_str)
                    in_maf = tmpdir / "input_maf.tsv"
                    out_pref = tmpdir / f"{gene}_out"
                    maf_df_plot.to_csv(in_maf, sep="\t", index=False)

                    plot_data = _run_r_lollipop(in_maf, gene, out_pref, R_SCRIPT_PATH)

            except subprocess.CalledProcessError as e:
                logger.warning("Rscript failed: %s", e)
                plot_data = None
                r_warn = f"Rscript failed: {e}"
            except FileNotFoundError as e:
                logger.warning("Rscript file missing: %s", e)
                plot_data = None
                r_warn = f"Rscript file missing: {e}"
            else:
                r_warn = None
        else:
            r_warn = "plot skipped by request"

        full_results_json = pd.DataFrame(full_df).to_dict(orient="records")
        maf_json = maf_df_all.where(pd.notnull(maf_df_all), None).to_dict(orient="records")
        oncoprint_json = oncoprint_df.where(pd.notnull(oncoprint_df), None).to_dict(orient="records")

        resp = {
            "full_results": full_results_json,
            "maf": maf_json,
            "oncoprint_maf": oncoprint_json,
            "plot_data": plot_data,
            "all_tables": tables,
        }
        if r_warn:
            resp["warning"] = r_warn

        return JsonResponse(resp, json_dumps_params={"ensure_ascii": False}, status=200)

    except subprocess.CalledProcessError as e:
        return _json_500("Rscript failed", e)
    except FileNotFoundError as e:
        return _json_500("File not found", e)
    except Exception as e:
        return _json_500("Unhandled server error", e)