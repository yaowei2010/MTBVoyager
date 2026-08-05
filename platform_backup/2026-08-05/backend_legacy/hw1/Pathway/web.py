# views.py
import os, json, traceback
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt

from .pipeline_ssMutPA import pipeline
from .Read_table import read_table_csv, normalize_mrwr, normalize_pathes
import re
from decimal import Decimal
from typing import Any
from ..postgressql_setting.dbpool import pg_fetchall, pg_fetchone


@csrf_exempt
def run_pipeline_view(request):
    if request.method != "POST":
        return HttpResponseBadRequest("POST only")

    try:
        data = json.loads(request.body.decode("utf-8") or "{}")

        patient_id = str(data.get("patient_id", "")).strip()
        user_id_raw = data.get("userId", None)
        source = str(data.get("source", "csv")).strip().lower()  # db / csv

        try:
            user_id_int = int(str(user_id_raw).strip())
        except Exception:
            user_id_int = None

        try:
            top_n = int(data.get("top_n", 100))
        except Exception:
            top_n = 100
        top_n = max(1, min(top_n, 1000))

        if not patient_id:
            return JsonResponse({"ok": False, "detail": "patient_id is required"}, status=400)

        if source not in ("db", "csv"):
            return JsonResponse({"ok": False, "detail": "source must be 'db' or 'csv'"}, status=400)

        gmt_rdata = "/miRTI/hw1/Pathway/Data/all_pathways_gmt.Rdata"
        if not os.path.isfile(gmt_rdata):
            return JsonResponse(
                {"ok": False, "detail": f"Pathway Rdata not found: {gmt_rdata}"},
                status=400
            )

        pop_csv_path = None
        schema = None

        if source == "csv":
            pop_csv_path = f"/miRTI/media/patient/{patient_id}/df_population.csv"
            if not os.path.isfile(pop_csv_path):
                return JsonResponse(
                    {"ok": False, "detail": f"df_population.csv not found: {pop_csv_path}"},
                    status=400
                )
            output_dir = f"/miRTI/media/patient/{patient_id}/pathway_output_population_compare"
        else:  # source == "db"
            if user_id_int is None:
                return JsonResponse(
                    {"ok": False, "detail": "userId is required when source='db'"},
                    status=400
                )
            schema = f"user_{user_id_int}"
            output_dir = f"/miRTI/media/patient/{patient_id}/pathway_output_db_compare"

        os.makedirs(output_dir, exist_ok=True)

        seed_csv = os.path.join(output_dir, "seed_genes.csv")
        mrwr_csv = os.path.join(output_dir, "MRWR_result.csv")
        pathes_csv = os.path.join(output_dir, "PathES_results.csv")

        def _file_good(p):
            try:
                return os.path.isfile(p) and os.path.getsize(p) > 0
            except Exception:
                return False

        if not (_file_good(mrwr_csv) and _file_good(pathes_csv)):
            result = pipeline(
                patient_id=patient_id,
                output_dir=output_dir,
                gmt_rdata=gmt_rdata,
                source=source,
                schema=schema,
                pop_csv_path=pop_csv_path,
                gamma=1.2,
            )

            mrwr_csv = result.get("mrwr", mrwr_csv)
            pathes_csv = result.get("pathes", pathes_csv)

        missing = [p for p in [mrwr_csv, pathes_csv] if not _file_good(p)]
        if missing:
            return JsonResponse(
                {"ok": False, "detail": f"Missing or empty output files: {missing}"},
                status=500
            )

        mrwr_table = read_table_csv(
            mrwr_csv, top_n=12436, normalize=normalize_mrwr
        )
        pathes_table = read_table_csv(
            pathes_csv, top_n=top_n, normalize=normalize_pathes
        )

        outputs = {
            "label": "Wprime",
            "out_dir": output_dir,
            "input_source": source,
            "input_csv": pop_csv_path,
            "schema": schema,
            "seed_genes": seed_csv if os.path.isfile(seed_csv) else None,
            "mrwr_csv": mrwr_csv,
            "pathes_csv": pathes_csv,
        }

        return JsonResponse({
            "ok": True,
            "patient_id": patient_id,
            "input_source": source,
            "outputs": outputs,
            "tables": {
                "mrwr": mrwr_table,
                "pathes": pathes_table,
            }
        }, json_dumps_params={"ensure_ascii": False})

    except Exception as e:
        return JsonResponse(
            {"ok": False, "detail": str(e), "traceback": traceback.format_exc()},
            status=500
        )


_SAFE_SCHEMA_TABLE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

def safe_schema_or_table(name: str) -> str:
    if not name or not _SAFE_SCHEMA_TABLE.match(name):
        raise ValueError(f"Unsafe schema/table identifier: {name!r}")
    return name

def quote_ident(name: str) -> str:
    s = str(name)
    return '"' + s.replace('"', '""') + '"'

def json_safe(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, Decimal):
        return float(v)
    return v


def resolve_patient_table_name(schema: str, patient_id: str) -> str:
    pid = str(patient_id).strip()
    if not pid:
        raise ValueError("empty patient_id")
    prefix = f"vep_annovar_merge_{pid}"

    row = pg_fetchone(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = %s
          AND lower(table_name) = lower(%s)
        LIMIT 1
        """,
        (schema, prefix),
        dict_rows=True,
    )
    if row and row.get("table_name"):
        return str(row["table_name"])

    row2 = pg_fetchone(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = %s
          AND table_name ILIKE %s
        ORDER BY table_name
        LIMIT 1
        """,
        (schema, prefix + "%"),
        dict_rows=True,
    )
    if row2 and row2.get("table_name"):
        return str(row2["table_name"])

    raise ValueError(f"patient table not found in schema={schema}, prefix={prefix}")


@csrf_exempt
def variants_by_gene(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "POST only"}, status=405)

    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except Exception:
        return JsonResponse({"ok": False, "error": "Invalid JSON body"}, status=400)

    patient_id = str(payload.get("patient_id") or "").strip()
    user_id = str(payload.get("userId") or "").strip()
    gene = str(payload.get("gene") or "").strip().upper()
    source = str(payload.get("source") or "db").strip().lower()

    if not patient_id:
        return JsonResponse({"ok": False, "error": "patient_id is required"}, status=400)
    if not user_id:
        return JsonResponse({"ok": False, "error": "userId is required"}, status=400)
    if not gene:
        return JsonResponse({"ok": False, "error": "gene is required"}, status=400)
    if source == "pop":
        source = "csv"

    if source not in ("db", "csv"):
        return JsonResponse({"ok": False, "error": "source must be 'db' or 'csv'"}, status=400)

    user_norm = re.sub(r"[^A-Za-z0-9_]+", "_", user_id)
    try:
        schema = safe_schema_or_table(f"user_{user_norm}")
    except Exception as e:
        return JsonResponse({"ok": False, "error": f"bad userId -> schema: {e}"}, status=400)

    try:
        table = resolve_patient_table_name(schema, patient_id)
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=404)

    try:
        col_rows = pg_fetchall(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position
            """,
            (schema, table),
            dict_rows=True,
        )
        columns = [r["column_name"] for r in col_rows]
        if not columns:
            return JsonResponse({"ok": False, "error": f"no columns: {schema}.{table}"}, status=500)
    except Exception as e:
        return JsonResponse({"ok": False, "error": f"read columns failed: {e}"}, status=500)

    gene_col = "Gene.refGene"

    schema_q = quote_ident(schema)
    table_q = quote_ident(table)
    gene_col_q = quote_ident(gene_col)

    try:
        sql = f"""
          SELECT *
          FROM {schema_q}.{table_q}
          WHERE UPPER({gene_col_q}) = %s
          LIMIT 5000
        """
        rows = pg_fetchall(sql, (gene,), dict_rows=True)
    except Exception as e:
        return JsonResponse({"ok": False, "error": f"DB query failed: {e}"}, status=500)

    safe_rows = [{k: json_safe(v) for k, v in r.items()} for r in rows]
    return JsonResponse({"ok": True, "table": {"columns": columns, "rows": safe_rows}})