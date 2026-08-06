from __future__ import annotations
import time, re, json, os, logging
from logging.handlers import RotatingFileHandler
from dataclasses import dataclass
from typing import Iterable, Optional

import pandas as pd
import requests
from bs4 import BeautifulSoup
from Bio import Entrez
from psycopg2.extras import RealDictCursor,Json
from psycopg2 import sql
from ..postgressql_setting.dbpool import PgConn

# ---------------- Logging ----------------
def _get_logger():
    logger = logging.getLogger("blacklist.clinvar_web")
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        os.makedirs("/miRTI/logs", exist_ok=True)
        fh = RotatingFileHandler(
            "/miRTI/logs/blacklist.log",
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        fmt = logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s:%(lineno)d | %(message)s"
        )
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    return logger


logger = _get_logger()
# ----------------------------------------

Entrez.email = "a5619216@gmail.com"

TARGET_COLS = [
    "Chr",
    "Start",
    "End",
    "Ref",
    "Alt",
    "Func.refGene",
    "Gene.refGene",
    "avsnp150",
    "Feature",
    "HGVSc",
    "HGVSp",
    "AAChange.refGene",
    "#Uploaded_variation",
    "AF",
    "TaiwanBioBank",
]


def _first_gene(g: str) -> str:
    return (g or "").split(";")[0].split("|")[0].strip()


def _first_nm(s: str) -> str | None:
    m = re.search(r"(NM_\d+(?:\.\d+)?)", s or "")
    return m.group(1) if m else None


def _first_cdot(s: str) -> str | None:
    m = re.search(r"(c\.[A-Za-z0-9_>+\-*=]+)", s or "")
    return m.group(1) if m else None


def _first_pdot(s: str) -> str | None:
    m = re.search(r"(p\.[A-Za-z][A-Za-z0-9_*=]+)", s or "")
    return m.group(1) if m else None


def build_query_from_rowlike(row: dict) -> str:
    payload = row.get("detail") or row.get("payload") or {}

    def G(key, default=""):
        return row.get(key, payload.get(key, default))

    feature = str(G("Feature", "")).strip()
    gene = _first_gene(str(G("Gene.refGene", "")).strip())
    hgvsc = str(G("HGVSc", "")).strip()
    hgvsp = str(G("HGVSp", "")).strip()
    aachg = str(G("AAChange.refGene", "")).strip()
    rsid = str(G("avsnp150", "")).strip()

    if ":" in hgvsc and "c." in hgvsc:
        return hgvsc
    if "c." in hgvsc:
        nm = _first_nm(feature) or _first_nm(aachg)
        if nm:
            return f"{nm}:{hgvsc}"
    if aachg:
        nm = _first_nm(aachg)
        cdot = _first_cdot(aachg)
        if nm and cdot:
            return f"{nm}:{cdot}"
    pdot = _first_pdot(hgvsp) or _first_pdot(aachg)
    if gene and pdot:
        return f"{gene} {pdot}"
    if rsid and re.match(r"^rs\d+$", rsid):
        return rsid

    logger.debug(
        "build_query empty | row_head={Chr:%s,Start:%s,Ref:%s,Alt:%s}",
        row.get("Chr"),
        row.get("Start"),
        row.get("Ref"),
        row.get("Alt"),
    )
    return ""


def get_clinvar_url_by_entrez(hgvs_query: str) -> str:
    try:
        if pd.isna(hgvs_query) or str(hgvs_query).strip() == "":
            return "not_found"
        handle = Entrez.esearch(db="clinvar", term=f"{hgvs_query}[Name]")
        record = Entrez.read(handle)
        handle.close()
        if not record.get("IdList"):
            return "not_found"
        cid = record["IdList"][0]
        escaped = hgvs_query.replace(":", "%3A").replace(">", "%3E")
        url = (
            f"https://www.ncbi.nlm.nih.gov/clinvar/variation/{cid}"
            f"/?oq={escaped}&m={escaped}"
        )
        logger.debug("entrez ok | query=%s url=%s", hgvs_query, url)
        return url
    except Exception as e:
        logger.exception("entrez fail | query=%s", hgvs_query)
        return f"error: {str(e)}"


def build_term_url(q: str) -> str:
    from urllib.parse import quote

    url = f"https://www.ncbi.nlm.nih.gov/clinvar/?term={quote(q, safe='')}"
    logger.debug("term url | query=%s url=%s", q, url)
    return url


def extract_table_rows(soup, table_selector, source_type):
    rows = soup.select(f"{table_selector} tr[class*='sub-col']")
    recs = []
    for r in rows:
        cols = r.find_all("td")
        if len(cols) < 5:
            continue
        classification = cols[0].get_text(strip=True)
        stars = len(cols[1].select("span.fa-star"))
        condition = cols[2].get_text(strip=True)
        submitter_tag = cols[3].find("a")
        submitter = submitter_tag.text.strip() if submitter_tag else ""
        accession_info = cols[3].get_text(strip=True)
        more_info = cols[4].get_text(strip=True)
        recs.append(
            {
                "Classification": classification,
                "ReviewStars": stars,
                "Condition": condition,
                "Submitter": submitter,
                "AccessionInfo": accession_info,
                "MoreInfo": more_info,
                "SourceType": source_type,
            }
        )
    return recs


def _clean_text(x: str | None) -> str | None:
    if x is None:
        return None
    s = re.sub(r"\s+", " ", str(x)).strip()
    return s or None


def _count_review_stars(section) -> int:
    """計算 summary 區塊中的實心星數。"""
    if section is None:
        return 0
    return len(section.select("span.fa-star"))



def _extract_single_item_value(section) -> str | None:
    """抓 Germline / Somatic summary 的主要評價文字。"""
    if section is None:
        return None

    no_data = section.select_one("p.without-classification")
    if no_data:
        return _clean_text(no_data.get_text(" ", strip=True))

    value = section.select_one(".single-item-value")
    if value:
        return _clean_text(value.get_text(" ", strip=True))

    return _clean_text(section.get_text(" ", strip=True))


def _extract_submission_count(section) -> int | None:
    if section is None:
        return None
    tag = section.select_one("#submission-counts")
    if not tag:
        return None
    try:
        return int(_clean_text(tag.get_text()) or 0)
    except Exception:
        return None


def _extract_summary_item(section) -> dict:
    """統一抽取 ClinVar summary 的 value / stars / submission_count。"""
    return {
        "value": _extract_single_item_value(section),
        "review_stars": _count_review_stars(section),
        "submission_count": _extract_submission_count(section),
        "summary_text": _clean_text(section.get_text(" ", strip=True)) if section else None,
    }


def extract_germline_somatic_summary(soup) -> dict:
    """
    抓 ClinVar 頁面上方 div#germline-somatic-info 中的 Germline / Somatic summary。
    不再抓 Legacy submission table 的 Classification / Condition / Submitter。
    """
    root = soup.select_one("div#germline-somatic-info")
    if root is None:
        return {}

    germline_section = root.select_one(".germline-info .germline-section")

    somatic_sections = root.select(".somatic-info .somatic-section")
    somatic_clinical_section = None
    somatic_oncogenicity_section = None
    for sec in somatic_sections:
        classes = sec.get("class") or []
        if "oncogenicity" in classes:
            somatic_oncogenicity_section = sec
        else:
            somatic_clinical_section = sec

    germline = _extract_summary_item(germline_section)
    somatic_clinical = _extract_summary_item(somatic_clinical_section)
    somatic_oncogenicity = _extract_summary_item(somatic_oncogenicity_section)

    summary = {
        "germline": {
            "classification": germline["value"],
            "review_stars": germline["review_stars"],
            "submission_count": germline["submission_count"],
            "summary_text": germline["summary_text"],
        },
        "somatic": {
            "clinical_impact": somatic_clinical["value"],
            "clinical_impact_review_stars": somatic_clinical["review_stars"],
            "clinical_impact_submission_count": somatic_clinical["submission_count"],
            "oncogenicity": somatic_oncogenicity["value"],
            "oncogenicity_review_stars": somatic_oncogenicity["review_stars"],
            "oncogenicity_submission_count": somatic_oncogenicity["submission_count"],
        },
    }

    return {
        "SourceType": "germline_somatic_summary",
        "GermlineClassification": germline["value"],
        "GermlineReviewStars": germline["review_stars"],
        "GermlineSubmissionCount": germline["submission_count"],
        "SomaticClinicalImpact": somatic_clinical["value"],
        "SomaticClinicalImpactReviewStars": somatic_clinical["review_stars"],
        "SomaticClinicalImpactSubmissionCount": somatic_clinical["submission_count"],
        "SomaticOncogenicity": somatic_oncogenicity["value"],
        "SomaticOncogenicityReviewStars": somatic_oncogenicity["review_stars"],
        "SomaticOncogenicitySubmissionCount": somatic_oncogenicity["submission_count"],
        "ClinVarSummary": summary,
    }


def fetch_clinvar_latest_one(url: str) -> dict | None:
    """
    抓 ClinVar 頁面上方 germline/somatic summary。
    不再抓 Legacy submission table 的 Classification / Condition / Submitter。
    """
    if not url or url == "not_found" or (
        isinstance(url, str) and url.startswith("error:")
    ):
        return None
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=8)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        summary = extract_germline_somatic_summary(soup)
        if not summary:
            logger.info("no germline/somatic summary | url=%s", url)
            return None
        summary["ClinVarURL"] = url
        return summary
    except Exception:
        logger.exception("scrape fail | url=%s", url)
        return None


def _schema_for_user(user_id: int) -> str:
    return f"user_{int(user_id)}"


def _ensure_output_tables(schema: str):
    try:
        with PgConn(autocommit=True) as conn, conn.cursor() as cur:
            # clinvar_lookup
            cur.execute(
                sql.SQL(
                    """
                CREATE TABLE IF NOT EXISTS {}.clinvar_lookup (
                  "Chr"   TEXT,
                  "Start" BIGINT,
                  "End"   BIGINT,
                  "Ref"   TEXT,
                  "Alt"   TEXT,
                  occurrence_count BIGINT,
                  case_count BIGINT,
                  analysis_case_total BIGINT,
                  case_ratio NUMERIC,
                  query TEXT,
                  resolve_mode TEXT,
                  clinvar_url TEXT,
                  status TEXT,
                  created_at_db TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                  updated_at_db TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                  PRIMARY KEY ("Chr","Start","End","Ref","Alt", query)
                )
                """
                ).format(sql.Identifier(schema))
            )

            # clinvar_latest：包含來源 payload/time + ClinVar germline/somatic summary
            cur.execute(
                sql.SQL(
                    """
                CREATE TABLE IF NOT EXISTS {}.clinvar_latest (
                  "Chr"   TEXT,
                  "Start" BIGINT,
                  "End"   BIGINT,
                  "Ref"   TEXT,
                  "Alt"   TEXT,
                  occurrence_count BIGINT,
                  case_count BIGINT,
                  analysis_case_total BIGINT,
                  case_ratio NUMERIC,
                  query TEXT,
                  clinvar_url TEXT,

                  -- 舊欄位：保留相容
                  classification TEXT,
                  review_stars INT,
                  condition TEXT,
                  submitter TEXT,
                  accession_info TEXT,
                  more_info TEXT,
                  date_extracted TEXT,
                  date_parsed TIMESTAMPTZ,

                  -- 新欄位：ClinVar 頁面上方 Germline / Somatic summary
                  germline_classification TEXT,
                  germline_review_stars INT,
                  germline_submission_count INT,
                  somatic_clinical_impact TEXT,
                  somatic_clinical_impact_review_stars INT,
                  somatic_clinical_impact_submission_count INT,
                  somatic_oncogenicity TEXT,
                  somatic_oncogenicity_review_stars INT,
                  somatic_oncogenicity_submission_count INT,
                  clinvar_summary JSONB,

                  src_payload    JSONB,
                  src_created_at TIMESTAMPTZ,
                  src_updated_at TIMESTAMPTZ,
                  created_at_db TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                  updated_at_db TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                  PRIMARY KEY ("Chr","Start","End","Ref","Alt", clinvar_url)
                )
                """
                ).format(sql.Identifier(schema))
            )

            # 舊表補欄位（保險）
            for addcol in (
                sql.SQL("ALTER TABLE {}.{} ADD COLUMN IF NOT EXISTS src_payload JSONB").format(
                    sql.Identifier(schema), sql.Identifier("clinvar_latest")
                ),
                sql.SQL("ALTER TABLE {}.{} ADD COLUMN IF NOT EXISTS src_created_at TIMESTAMPTZ").format(
                    sql.Identifier(schema), sql.Identifier("clinvar_latest")
                ),
                sql.SQL("ALTER TABLE {}.{} ADD COLUMN IF NOT EXISTS src_updated_at TIMESTAMPTZ").format(
                    sql.Identifier(schema), sql.Identifier("clinvar_latest")
                ),
                sql.SQL("ALTER TABLE {}.{} ADD COLUMN IF NOT EXISTS occurrence_count BIGINT").format(
                    sql.Identifier(schema), sql.Identifier("clinvar_latest")
                ),
                sql.SQL("ALTER TABLE {}.{} ADD COLUMN IF NOT EXISTS case_count BIGINT").format(
                    sql.Identifier(schema), sql.Identifier("clinvar_latest")
                ),
                sql.SQL("ALTER TABLE {}.{} ADD COLUMN IF NOT EXISTS analysis_case_total BIGINT").format(
                    sql.Identifier(schema), sql.Identifier("clinvar_latest")
                ),
                sql.SQL("ALTER TABLE {}.{} ADD COLUMN IF NOT EXISTS case_ratio NUMERIC").format(
                    sql.Identifier(schema), sql.Identifier("clinvar_latest")
                ),
                sql.SQL("ALTER TABLE {}.{} ADD COLUMN IF NOT EXISTS germline_classification TEXT").format(
                    sql.Identifier(schema), sql.Identifier("clinvar_latest")
                ),
                sql.SQL("ALTER TABLE {}.{} ADD COLUMN IF NOT EXISTS germline_review_stars INT").format(
                    sql.Identifier(schema), sql.Identifier("clinvar_latest")
                ),
                sql.SQL("ALTER TABLE {}.{} ADD COLUMN IF NOT EXISTS germline_submission_count INT").format(
                    sql.Identifier(schema), sql.Identifier("clinvar_latest")
                ),
                sql.SQL("ALTER TABLE {}.{} ADD COLUMN IF NOT EXISTS somatic_clinical_impact TEXT").format(
                    sql.Identifier(schema), sql.Identifier("clinvar_latest")
                ),
                sql.SQL("ALTER TABLE {}.{} ADD COLUMN IF NOT EXISTS somatic_clinical_impact_review_stars INT").format(
                    sql.Identifier(schema), sql.Identifier("clinvar_latest")
                ),
                sql.SQL("ALTER TABLE {}.{} ADD COLUMN IF NOT EXISTS somatic_clinical_impact_submission_count INT").format(
                    sql.Identifier(schema), sql.Identifier("clinvar_latest")
                ),
                sql.SQL("ALTER TABLE {}.{} ADD COLUMN IF NOT EXISTS somatic_oncogenicity TEXT").format(
                    sql.Identifier(schema), sql.Identifier("clinvar_latest")
                ),
                sql.SQL("ALTER TABLE {}.{} ADD COLUMN IF NOT EXISTS somatic_oncogenicity_review_stars INT").format(
                    sql.Identifier(schema), sql.Identifier("clinvar_latest")
                ),
                sql.SQL("ALTER TABLE {}.{} ADD COLUMN IF NOT EXISTS somatic_oncogenicity_submission_count INT").format(
                    sql.Identifier(schema), sql.Identifier("clinvar_latest")
                ),
                sql.SQL("ALTER TABLE {}.{} ADD COLUMN IF NOT EXISTS clinvar_summary JSONB").format(
                    sql.Identifier(schema), sql.Identifier("clinvar_latest")
                ),
            ):
                cur.execute(addcol)

        logger.info("ensure tables ok | schema=%s", schema)
    except Exception:
        logger.exception("ensure tables fail | schema=%s", schema)
        raise

def _iter_source_rows(
    schema: str, mode: str, limit: Optional[int] = None
) -> Iterable[dict]:
    src_table = f"blacklist_compare_{'intersect' if mode == 'intersect' else 'diff'}"
    try:
        with PgConn(autocommit=True) as conn, conn.cursor(
            cursor_factory=RealDictCursor
        ) as cur:
            q = sql.SQL(
                """
              SELECT "Chr","Start","End","Ref","Alt",
                     occurrence_count, case_count, analysis_case_total, case_ratio,
                     payload AS detail, created_at, updated_at
              FROM {}.{}
              WHERE "Chr" IS NOT NULL AND "Ref" IS NOT NULL AND "Alt" IS NOT NULL
                AND "Start" IS NOT NULL AND "End" IS NOT NULL
              ORDER BY "Chr","Start","Ref","Alt"
            """
            ).format(sql.Identifier(schema), sql.Identifier(src_table))
            if limit is not None and limit > 0:
                q = sql.Composed([q, sql.SQL(" LIMIT "), sql.Literal(int(limit))])
            cur.execute(q)
            for row in cur:
                yield dict(row)
    except Exception:
        logger.exception(
            "iter source fail | schema=%s table=%s limit=%s", schema, src_table, limit
        )
        raise


def _upsert_lookup(conn, schema: str, row: dict):
    try:
        with conn.cursor() as cur:
            cur.execute(
                sql.SQL(
                    """
                  INSERT INTO {}.clinvar_lookup
                    ("Chr","Start","End","Ref","Alt", query, resolve_mode, clinvar_url, status)
                  VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                  ON CONFLICT ("Chr","Start","End","Ref","Alt", query)
                  DO UPDATE SET
                    resolve_mode = EXCLUDED.resolve_mode,
                    clinvar_url  = EXCLUDED.clinvar_url,
                    status       = EXCLUDED.status,
                    updated_at_db = NOW()
                """
                ).format(sql.Identifier(schema)),
                [
                    row["Chr"],
                    row["Start"],
                    row["End"],
                    row["Ref"],
                    row["Alt"],
                    row["query"],
                    row["resolve_mode"],
                    row["clinvar_url"],
                    row["status"],
                ],
            )
    except Exception:
        logger.exception(
            "upsert lookup fail | schema=%s row_head={Chr:%s,Start:%s,Ref:%s,Alt:%s,query:%s}",
            schema,
            row.get("Chr"),
            row.get("Start"),
            row.get("Ref"),
            row.get("Alt"),
            row.get("query"),
        )
        raise


def _to_datetime_or_none(v):
    try:
        if isinstance(v, pd.Timestamp):
            return v.to_pydatetime()
        return v if (v is None or hasattr(v, "isoformat")) else None
    except Exception:
        return None


def _upsert_latest(conn, schema: str, keyrow: dict, latest: dict, query: str):
    """
    寫入 ClinVar 頁面上方 germline/somatic summary。
    Legacy Classification / Condition / Submitter 不再抓取，相關欄位只保留 NULL 以相容舊表。
    """
    sql_stmt = sql.SQL(
        """
        INSERT INTO {}.clinvar_latest
          ("Chr","Start","End","Ref","Alt",
           occurrence_count, case_count, analysis_case_total, case_ratio,
           query, clinvar_url,
           classification, review_stars, condition, submitter,
           accession_info, more_info, date_extracted, date_parsed,
           germline_classification,
           germline_review_stars,
           germline_submission_count,
           somatic_clinical_impact,
           somatic_clinical_impact_review_stars,
           somatic_clinical_impact_submission_count,
           somatic_oncogenicity,
           somatic_oncogenicity_review_stars,
           somatic_oncogenicity_submission_count,
           clinvar_summary,
           src_payload, src_created_at, src_updated_at)
        VALUES
          (%s,%s,%s,%s,%s,
           %s,%s,%s,%s,
           %s,%s,
           NULL,NULL,NULL,NULL,
           NULL,NULL,NULL,NULL,
           %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
           %s,%s,%s)
        ON CONFLICT ("Chr","Start","End","Ref","Alt", clinvar_url)
        DO UPDATE SET
          occurrence_count = EXCLUDED.occurrence_count,
          case_count = EXCLUDED.case_count,
          analysis_case_total = EXCLUDED.analysis_case_total,
          case_ratio = EXCLUDED.case_ratio,
          query = EXCLUDED.query,
          classification = NULL,
          review_stars = NULL,
          condition = NULL,
          submitter = NULL,
          accession_info = NULL,
          more_info = NULL,
          date_extracted = NULL,
          date_parsed = NULL,
          germline_classification = EXCLUDED.germline_classification,
          germline_review_stars = EXCLUDED.germline_review_stars,
          germline_submission_count = EXCLUDED.germline_submission_count,
          somatic_clinical_impact = EXCLUDED.somatic_clinical_impact,
          somatic_clinical_impact_review_stars = EXCLUDED.somatic_clinical_impact_review_stars,
          somatic_clinical_impact_submission_count = EXCLUDED.somatic_clinical_impact_submission_count,
          somatic_oncogenicity = EXCLUDED.somatic_oncogenicity,
          somatic_oncogenicity_review_stars = EXCLUDED.somatic_oncogenicity_review_stars,
          somatic_oncogenicity_submission_count = EXCLUDED.somatic_oncogenicity_submission_count,
          clinvar_summary = EXCLUDED.clinvar_summary,
          src_payload = EXCLUDED.src_payload,
          src_created_at = EXCLUDED.src_created_at,
          src_updated_at = EXCLUDED.src_updated_at,
          updated_at_db = NOW()
    """
    ).format(sql.Identifier(schema))

    src_payload = keyrow.get("detail") or keyrow.get("payload")
    src_created_at = keyrow.get("created_at")
    src_updated_at = keyrow.get("updated_at")

    payload_param = Json(src_payload) if src_payload is not None else None
    summary_param = Json(latest.get("ClinVarSummary")) if latest.get("ClinVarSummary") is not None else None

    params = [
        keyrow.get("Chr"),
        keyrow.get("Start"),
        keyrow.get("End"),
        keyrow.get("Ref"),
        keyrow.get("Alt"),
        keyrow.get("occurrence_count"),
        keyrow.get("case_count"),
        keyrow.get("analysis_case_total"),
        keyrow.get("case_ratio"),
        query,
        latest.get("ClinVarURL"),
        latest.get("GermlineClassification"),
        int(latest.get("GermlineReviewStars") or 0),
        latest.get("GermlineSubmissionCount"),
        latest.get("SomaticClinicalImpact"),
        int(latest.get("SomaticClinicalImpactReviewStars") or 0),
        latest.get("SomaticClinicalImpactSubmissionCount"),
        latest.get("SomaticOncogenicity"),
        int(latest.get("SomaticOncogenicityReviewStars") or 0),
        latest.get("SomaticOncogenicitySubmissionCount"),
        summary_param,
        payload_param,
        src_created_at,
        src_updated_at,
    ]

    try:
        with conn.cursor() as cur:
            cur.execute(sql_stmt, params)
    except Exception:
        logger.exception(
            "upsert latest fail | schema=%s url=%s key={Chr:%s,Start:%s,Ref:%s,Alt:%s}",
            schema,
            latest.get("ClinVarURL"),
            keyrow.get("Chr"),
            keyrow.get("Start"),
            keyrow.get("Ref"),
            keyrow.get("Alt"),
        )
        raise


def run_batch(cfg: JobConfig) -> dict:
    schema = _schema_for_user(cfg.user_id)
    _ensure_output_tables(schema)

    modes = (
        ["intersect", "diff"]
        if cfg.mode == "both"
        else [("intersect" if cfg.mode == "intersect" else "diff")]
    )
    stats = {"scanned": 0, "lookup_upserts": 0, "latest_upserts": 0}
    logger.info(
        "run_batch | user_id=%s schema=%s modes=%s resolve_mode=%s scrape=%s limit=%s",
        cfg.user_id,
        schema,
        modes,
        cfg.resolve_mode,
        cfg.scrape,
        cfg.limit,
    )

    with PgConn(autocommit=True) as conn:
        for m in modes:
            for row in _iter_source_rows(schema, m, cfg.limit):
                stats["scanned"] += 1
                try:
                    query = build_query_from_rowlike(row)
                    if not query:
                        continue

                    if cfg.resolve_mode == "term":
                        url = build_term_url(query)
                    else:
                        url = get_clinvar_url_by_entrez(query)
                        if url == "not_found" or (
                            isinstance(url, str) and url.startswith("error:")
                        ):
                            url = build_term_url(query)

                    rec = {
                        "Chr": row["Chr"],
                        "Start": row["Start"],
                        "End": row["End"],
                        "Ref": row["Ref"],
                        "Alt": row["Alt"],
                        "query": query,
                        "resolve_mode": cfg.resolve_mode,
                        "clinvar_url": url,
                        "status": "ok"
                        if url and not str(url).startswith("error:")
                        else (url or "not_found"),
                    }
                    _upsert_lookup(conn, schema, rec)
                    stats["lookup_upserts"] += 1

                    if cfg.scrape:
                        latest = fetch_clinvar_latest_one(url)
                        if latest:
                            # row 裡有 detail / created_at / updated_at
                            _upsert_latest(conn, schema, row, latest, query)
                            stats["latest_upserts"] += 1
                        time.sleep(cfg.sleep_sec)
                except Exception:
                    logger.exception(
                        "run_batch row fail | schema=%s row_head={Chr:%s,Start:%s,Ref:%s,Alt:%s}",
                        schema,
                        row.get("Chr"),
                        row.get("Start"),
                        row.get("Ref"),
                        row.get("Alt"),
                    )
                    continue

    logger.info("run_batch done | stats=%s", stats)
    return stats
