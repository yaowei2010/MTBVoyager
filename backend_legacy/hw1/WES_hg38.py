import os
import re
import io
import logging
import pandas as pd


class WES_layering_hg38:
    def __init__(
        self,
        annotation_table,
        genotype_table,
        gene_panel,
        MAF_cutoff,
        review_status,
        phenotypeDrivenRanking=None,
        log_file="layering.log",
        debug_dir="layering_debug",
        write_step_tsv=True,  # 保留這個參數，但現在代表「是否把表格內容印到 log」
        key_cols=("Chr", "Start", "End", "Ref", "Alt"),
        promoterai_abs_thr=0.5,
        promoterai_abs_strong=0.8,
        spliceai_thr=0.2,
        # --- 新增：控制「印到 log 的表格大小」 ---
        log_table_max_rows=30,
        log_table_max_cols=40,
        log_table_show_tail=False,
        log_table_max_colwidth=80,
        gnomad_population="eas",
    ):
        # 註解後的表格
        self.annotation_table = annotation_table

        # 基因型及品質的表格
        self.genotype_table = genotype_table

        # 欲探勘之基因套組
        self.gene_panel = gene_panel

        # Populational Allele frequency的門檻
        self.maf_cutoff = float(MAF_cutoff)
        self.gnomad_population = self._normalize_gnomad_population(gnomad_population)
        self.gnomad_af_column = self._gnomad_population_columns()[self.gnomad_population]

        # Clinvar的證據強度（review stars）
        self.review_status = int(review_status)

        # phenotype driven ranking 分數表
        self.phenotypeDrivenRanking = phenotypeDrivenRanking

        self.promoterai_abs_thr = float(promoterai_abs_thr)
        self.promoterai_abs_strong = float(promoterai_abs_strong)
        self.spliceai_thr = float(spliceai_thr)

        # logging / debug
        self.key_cols = list(key_cols)
        self.debug_dir = debug_dir
        self.write_step_tsv = bool(write_step_tsv)
        os.makedirs(self.debug_dir, exist_ok=True)

        # --- 新增：log 表格顯示控制 ---
        self.log_table_max_rows = int(log_table_max_rows)
        self.log_table_max_cols = int(log_table_max_cols)
        self.log_table_show_tail = bool(log_table_show_tail)
        self.log_table_max_colwidth = int(log_table_max_colwidth)

        self.logger = self._setup_logger(log_file)
        self.logger.info("===== WES layering logger started =====")
        self.logger.info(
            f"maf_cutoff={self.maf_cutoff}, gnomad_population={self.gnomad_population}, gnomad_af_column={self.gnomad_af_column}, review_status={self.review_status}, debug_dir={self.debug_dir}, "
            f"write_step_tsv={self.write_step_tsv} (now=log tables), "
            f"log_table_max_rows={self.log_table_max_rows}, log_table_max_cols={self.log_table_max_cols}, "
            f"log_table_show_tail={self.log_table_show_tail}"
        )

    @staticmethod
    def _gnomad_population_columns():
        return {
            "all": "AF",
            "popmax": "AF_popmax",
            "afr": "AF_afr",
            "amr": "AF_amr",
            "asj": "AF_asj",
            "eas": "AF_eas",
            "fin": "AF_fin",
            "nfe": "AF_nfe",
            "oth": "AF_oth",
            "sas": "AF_sas",
        }

    @classmethod
    def _normalize_gnomad_population(cls, value):
        population = str(value or "eas").strip().lower()
        return population if population in cls._gnomad_population_columns() else "eas"

    def _apply_selected_gnomad_af(self, df: pd.DataFrame) -> pd.DataFrame:
        selected_column = self.gnomad_af_column
        if selected_column in df.columns:
            df["AF"] = df[selected_column]
            self.logger.info(f"gnomAD population={self.gnomad_population}, using {selected_column} as AF")
        elif "AF" in df.columns:
            self.logger.info(f"gnomAD population={self.gnomad_population}, column {selected_column} missing; fallback to AF")
        else:
            df["AF"] = -1
            self.logger.info(f"gnomAD population={self.gnomad_population}, no AF column found; filled AF=-1")
        return df

    # -----------------------------
    # Logger & debug helpers
    # -----------------------------
    def _setup_logger(self, log_file: str):
        logger = logging.getLogger(f"WES_layering_{id(self)}")
        logger.setLevel(logging.INFO)

        if logger.handlers:
            return logger

        fmt = logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s")

        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setFormatter(fmt)
        logger.addHandler(fh)

        sh = logging.StreamHandler()
        sh.setFormatter(fmt)
        logger.addHandler(sh)

        return logger

    def _log_df(self, step_name: str, df: pd.DataFrame, extra: str = ""):
        if df is None:
            self.logger.info(f"[{step_name}] df=None {extra}".strip())
            return

        n = df.shape[0]
        gene_n = df["Gene.refGene"].nunique() if "Gene.refGene" in df.columns else None
        self.logger.info(
            f"[{step_name}] rows={n}, genes={gene_n}, cols={df.shape[1]} {extra}".strip()
        )

        if n == 0:
            self.logger.warning(f"[{step_name}] dataframe is EMPTY!")

        if n > 0 and all(c in df.columns for c in self.key_cols):
            ex = (
                df[self.key_cols]
                .head(5)
                .astype(str)
                .agg(":".join, axis=1)
                .tolist()
            )
            self.logger.info(f"[{step_name}] example_keys={ex}")

    # --- 新增：把 DataFrame 內容印到 log ---
    def _log_table(
        self,
        step_name: str,
        df: pd.DataFrame,
        label: str = "",
        max_rows: int = None,
        max_cols: int = None,
        show_tail: bool = None,
    ):
        if df is None:
            self.logger.info(f"[{step_name}] {label} df=None".strip())
            return

        nrows, ncols = df.shape
        self.logger.info(f"[{step_name}] {label} table rows={nrows} cols={ncols}".strip())
        if nrows == 0:
            return

        if max_rows is None:
            max_rows = self.log_table_max_rows
        if max_cols is None:
            max_cols = self.log_table_max_cols
        if show_tail is None:
            show_tail = self.log_table_show_tail

        # 欄位太多就截斷
        view = df
        truncated_cols = False
        if ncols > max_cols:
            view = df.iloc[:, :max_cols]
            truncated_cols = True

        # head
        head_n = min(max_rows, len(view))
        head_df = view.head(head_n)

        buf = io.StringIO()
        with pd.option_context(
            "display.max_rows", max_rows,
            "display.max_columns", max_cols,
            "display.width", 200,
            "display.max_colwidth", self.log_table_max_colwidth,
        ):
            head_df.to_string(buf, index=False)
        msg = buf.getvalue()

        extra = []
        if truncated_cols:
            extra.append(f"cols_truncated_to={max_cols}")
        if nrows > max_rows:
            extra.append(f"rows_shown=head({head_n})/{nrows}")
        if extra:
            self.logger.info(f"[{step_name}] {label} ({', '.join(extra)})".strip())

        self.logger.info(f"[{step_name}] {label}\n{msg}".rstrip())

        # tail（可選）
        if show_tail and nrows > max_rows:
            tail_n = min(max_rows, nrows)
            tail_df = view.tail(tail_n)
            buf2 = io.StringIO()
            with pd.option_context(
                "display.max_rows", max_rows,
                "display.max_columns", max_cols,
                "display.width", 200,
                "display.max_colwidth", self.log_table_max_colwidth,
            ):
                tail_df.to_string(buf2, index=False)
            self.logger.info(f"[{step_name}] {label} tail({tail_n})\n{buf2.getvalue()}".rstrip())

    # --- 修改：原本寫 tsv，改成印到 log ---
    def _write_tsv(self, step_name: str, df: pd.DataFrame, suffix: str):
        # write_step_tsv 原本是控制寫檔，現在改成控制「是否把表格印到 log」
        if not self.write_step_tsv:
            return
        if df is None:
            return
        self._log_table(step_name=step_name, df=df, label=f"[{suffix}]")

    def _make_key_series(self, df: pd.DataFrame) -> pd.Series:
        return df[self.key_cols].astype(str).agg("::".join, axis=1)

    def _exclude_by_key(self, base_df: pd.DataFrame, remove_df: pd.DataFrame) -> pd.DataFrame:
        if base_df is None or base_df.shape[0] == 0:
            return base_df
        if remove_df is None or remove_df.shape[0] == 0:
            return base_df
        if not all(c in base_df.columns for c in self.key_cols):
            return base_df
        if not all(c in remove_df.columns for c in self.key_cols):
            return base_df

        base_key = self._make_key_series(base_df)
        rm_key = set(self._make_key_series(remove_df))
        return base_df.loc[~base_key.isin(rm_key)].copy()

    def _log_filter(
        self,
        step_name: str,
        before_df: pd.DataFrame,
        after_df: pd.DataFrame,
        reason: str = "",
        write_dropped=True,
        write_kept=True,
    ) -> pd.DataFrame:
        self._log_df(step_name + ".before", before_df, extra=f"reason={reason}")
        self._log_df(step_name + ".after", after_df, extra=f"reason={reason}")

        dropped = pd.DataFrame()
        if (
            before_df is not None
            and after_df is not None
            and before_df.shape[0] > 0
            and all(c in before_df.columns for c in self.key_cols)
            and all(c in after_df.columns for c in self.key_cols)
        ):
            b_key = self._make_key_series(before_df)
            a_key = set(self._make_key_series(after_df))
            dropped = before_df.loc[~b_key.isin(a_key)].copy()
        else:
            if before_df is not None and after_df is not None:
                dropped = before_df.loc[~before_df.index.isin(after_df.index)].copy()

        kept_n = 0 if after_df is None else after_df.shape[0]
        drop_n = 0 if dropped is None else dropped.shape[0]
        self.logger.info(f"[{step_name}] kept={kept_n} dropped={drop_n} {reason}".strip())

        if write_dropped:
            self._write_tsv(step_name, dropped, suffix="dropped")
        if write_kept:
            self._write_tsv(step_name, after_df, suffix="kept")

        return dropped

    def _normalize_key_cols(self, df: pd.DataFrame, name: str) -> pd.DataFrame:
        """把 KEY 欄位做一致化：str/strip、Start/End 去 .0、Chr 補 chr 前綴"""
        if df is None:
            return df

        df = df.copy()
        for c in self.key_cols:
            if c not in df.columns:
                raise KeyError(f"[{name}] missing key column: {c}")
            df[c] = df[c].astype(str).str.strip()

        for c in ["Start", "End"]:
            df[c] = df[c].str.replace(r"\.0$", "", regex=True)

        def add_chr(s):
            s = str(s).strip()
            return s if s.lower().startswith("chr") else "chr" + s

        df["Chr"] = df["Chr"].map(add_chr)
        return df

    # -----------------------------
    # Noncoding filter by PromoterAI / SpliceAI
    # -----------------------------
    def _first_existing_col(self, df: pd.DataFrame, candidates):
        for c in candidates:
            if c in df.columns:
                return c
        return None

    def _to_num(self, s: pd.Series) -> pd.Series:
        s = s.fillna(".").astype(str)
        s = s.replace({".": None, "": None, "nan": None, "NaN": None})
        return pd.to_numeric(s, errors="coerce")


    def _get_promoterai_score(self, df: pd.DataFrame) -> pd.Series:
        col = "promoterAI_tss500"
        if col not in df.columns:
            raise KeyError(f"[noncoding_filter] missing PromoterAI column: {col}")
        return self._to_num(df[col])

    def _get_spliceai_max_ds(self, df: pd.DataFrame) -> pd.Series:
        cols = ["SpliceAI_pred_DS_AG", "SpliceAI_pred_DS_AL", "SpliceAI_pred_DS_DG", "SpliceAI_pred_DS_DL"]
        missing = [c for c in cols if c not in df.columns]
        if missing:
            raise KeyError(f"[noncoding_filter] missing SpliceAI columns: {missing}")

        mat = pd.DataFrame({c: self._to_num(df[c]) for c in cols}, index=df.index)
        return mat.max(axis=1, skipna=True)


    def _noncoding_mask(self, df: pd.DataFrame) -> pd.Series:
        func = df.get("Func.refGene", pd.Series([""] * len(df), index=df.index)).fillna("").astype(str).str.lower()
        return func.ne("exonic")

    def filter_noncoding_by_promoter_splice(self, df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.shape[0] == 0:
            return df

        df = df.copy()
        noncoding = self._noncoding_mask(df)
        coding_df = df.loc[~noncoding].copy()
        noncoding_df = df.loc[noncoding].copy()

        if noncoding_df.shape[0] == 0:
            return df

        prom = self._get_promoterai_score(noncoding_df)
        dsmax = self._get_spliceai_max_ds(noncoding_df)

        noncoding_df["PromoterAI_score_norm"] = prom
        noncoding_df["PromoterAI_pass"] = prom.abs() >= self.promoterai_abs_thr
        noncoding_df["PromoterAI_strong"] = prom.abs() >= self.promoterai_abs_strong

        noncoding_df["SpliceAI_maxDS"] = dsmax
        noncoding_df["SpliceAI_pass"] = dsmax >= self.spliceai_thr

        # 注意：這裡依你原本程式寫的是 AND（兩者都要過）
        keep_noncoding = noncoding_df[
            noncoding_df["PromoterAI_pass"] & noncoding_df["SpliceAI_pass"]
        ].copy()

        out = pd.concat([coding_df, keep_noncoding], axis=0, ignore_index=False, sort=False).copy()
        return out

    # -----------------------------
    # DB loaders
    # -----------------------------
    def load_ACMG(self):
        ACMG_gene = [
            "ATP7B","KCNH2","MSH6","RET","TSC1","VHL","WT1","MYH7","KCNQ1",
            "OTC","FBN1","SDHD","APOB","MLH1","GLA","RYR2","APC","CACNA1S",
            "PTEN","PMS2","RYR1","TMEM43","SDHAF2","SMAD4","MSH2","ACTC1",
            "BRCA1","SDHC","MYL2","NF2","SDHB","MUTYH","DSP","ACTA2","DSG2",
            "DSC2","PRKAG2","BMPR1A","MYBPC3","TP53","TGFBR1","STK11","BRCA2",
            "TSC2","MYH11","SMAD3","COL3A1","LDLR","TNNI3","RB1","SCN5A",
            "TGFBR2","LMNA","TPM1","PKP2","TNNT2","MEN1","PCSK9","MYL3",
        ]
        return ACMG_gene

    def load_OMIM(self):
        OMIM_table = pd.read_csv("hw1/DB/HPO_merge_omim_summary_V6.csv", engine="python")
        OMIM_table = OMIM_table.rename(
            columns={
                "Gene.Symbols1": "Gene.refGene",
                "Mim.Number": "OMIM_number",
                "phenotype_summary": "Phenotype",
            }
        )
        OMIM_table = OMIM_table[["Gene.refGene", "OMIM_number", "Phenotype"]].drop_duplicates()
        return OMIM_table

    # -----------------------------
    # Field adjusters
    # -----------------------------
    def adjust_AF(self, x):
        if pd.isna(x) or x == ".":
            return -1
        return x

    def adjust_TBB_AF(self, x):
        if pd.isna(x) or x == ".":
            return -1
        elif re.search(r"[|]", str(x)):
            AF = str(x).split("|")[2].split(":")[1]
        else:
            AF = x
        return AF

    # -----------------------------
    # prediction summary
    # -----------------------------
    def summarize_drug_response_evidence(self, x):
        evidence = str(x.get("Level of Evidence", ""))
        typ = str(x.get("Clinical Annotation Types", ""))
        summary_string = evidence + "(" + typ + ")"
        x["response_summary"] = summary_string
        return x

    def _safe_float(self, v, default=None):
        try:
            if v is None or pd.isna(v) or v == ".":
                return default
            return float(v)
        except Exception:
            return default

    def summarize_prediction(self, x):
        Polyphen2_HVAR = x.get("Polyphen2_HVAR_pred", ".")
        VEST3 = x.get("VEST3_score", ".")
        MetaSVM = x.get("MetaSVM_pred", ".")
        MetaLR = x.get("MetaLR_pred", ".")
        CADD = x.get("CADD_phred", ".")
        MuTaster = x.get("MutationTaster_pred", ".")
        SIFT = x.get("SIFT_pred", ".")
        DANN = x.get("DANN_score", ".")

        deleterious_agreed = 0
        deleterious_tools = 0

        ADA_score = x.get("dbscSNV_ADA_SCORE", ".")
        RF_score = x.get("dbscSNV_RF_SCORE", ".")
        splicing_effect_agreed = 0
        splicing_effect_tools = 0

        if Polyphen2_HVAR != ".":
            deleterious_tools += 1
            if str(Polyphen2_HVAR) in ["D", "P"]:
                deleterious_agreed += 1

        if VEST3 != ".":
            deleterious_tools += 1
            if self._safe_float(VEST3, default=-1) is not None and self._safe_float(VEST3, default=-1) > 0.5:
                deleterious_agreed += 1

        if MetaSVM != ".":
            deleterious_tools += 1
            if str(MetaSVM) in ["D"]:
                deleterious_agreed += 1

        if MetaLR != ".":
            deleterious_tools += 1
            if str(MetaLR) in ["D"]:
                deleterious_agreed += 1

        if CADD != ".":
            deleterious_tools += 1
            if self._safe_float(CADD, default=-1) is not None and self._safe_float(CADD, default=-1) > 20:
                deleterious_agreed += 1

        if MuTaster != ".":
            deleterious_tools += 1
            if str(MuTaster) in ["D", "A"]:
                deleterious_agreed += 1

        if SIFT != ".":
            deleterious_tools += 1
            if str(SIFT) in ["D"]:
                deleterious_agreed += 1

        if DANN != ".":
            deleterious_tools += 1
            if self._safe_float(DANN, default=-1) is not None and self._safe_float(DANN, default=-1) > 0.95:
                deleterious_agreed += 1

        if ADA_score != ".":
            splicing_effect_tools += 1
            if self._safe_float(ADA_score, default=-1) is not None and self._safe_float(ADA_score, default=-1) >= 0.6:
                splicing_effect_agreed += 1

        if RF_score != ".":
            splicing_effect_tools += 1
            if self._safe_float(RF_score, default=-1) is not None and self._safe_float(RF_score, default=-1) >= 0.6:
                splicing_effect_agreed += 1

        x["deleterious_agreed"] = deleterious_agreed
        x["deleterious_tools"] = deleterious_tools
        x["splicing_effect_agreed"] = splicing_effect_agreed
        x["splicing_effect_tools"] = splicing_effect_tools
        return x

    # -----------------------------
    # Drug response
    # -----------------------------
    def drug_response(self, input_variant):
        pharmGKB_table = pd.read_csv(
            "hw1/DB/clinical_ann_metadata.tsv",
            sep="\t",
            on_bad_lines="skip",
            engine="python",
        )

        drug_response_db = pharmGKB_table[pharmGKB_table["Level of Evidence"].isin(["1A", "1B"])]

        if "avsnp150" not in input_variant.columns or "Location" not in drug_response_db.columns:
            self.logger.warning("[drug_response] missing columns (avsnp150 or Location). return empty.")
            empty = input_variant.iloc[0:0].copy()
            return empty, empty

        drug_response_variant = input_variant[input_variant["avsnp150"].isin(list(drug_response_db["Location"]))].copy()

        drug_response_db = drug_response_db.rename(columns={"Location": "avsnp150"})
        drug_response_demo = pd.merge(drug_response_variant, drug_response_db, how="inner", on="avsnp150")
        drug_response_demo = drug_response_demo.apply(self.summarize_drug_response_evidence, axis=1)
        drug_response_demo = drug_response_demo.rename(columns={"Related Chemicals": "Chemicals"})

        self._log_df("drug_response.variant", drug_response_variant)
        self._log_df("drug_response.demo", drug_response_demo)

        # 這些原本寫檔，現在會印到 log
        self._write_tsv("drug_response_variant", drug_response_variant, "kept")
        self._write_tsv("drug_response_demo", drug_response_demo, "kept")

        return drug_response_variant, drug_response_demo

    # -----------------------------
    # Known pathogenic
    # -----------------------------
    # def known_pathogenic(self, input_variant, criteria):
    #     review_star_dict = {
    #         "no_assertion_provided": 0,
    #         "no_assertion_criteria_provided": 0,
    #         "no_assertion_for_the_individual_variant": 0,
    #         "criteria_provided,_conflicting_interpretations": 1,
    #         "criteria_provided,_single_submitter": 1,
    #         "criteria_provided,_multiple_submitters,_no_conflicts": 2,
    #         "reviewed_by_expert_panel": 3,
    #         "practice_guideline": 4,
    #     }
    #     review_status_table = pd.DataFrame.from_dict(
    #         review_star_dict, orient="index", columns=["review_status"]
    #     )

    #     df = input_variant.copy()

    #     for col in ["CLNSIG", "CLNREVSTAT"]:
    #         if col not in df.columns:
    #             df[col] = ""
    #         df[col] = df[col].fillna("").astype(str)

    #     clinvar_pathogenic_index = df.index[
    #         df["CLNSIG"].str.contains(r"[P|p]athogenic", regex=True)
    #         & ~df["CLNSIG"].str.contains(r"[C|c]onflicting", regex=True)
    #         & df["CLNREVSTAT"].isin(
    #             review_status_table.index[review_status_table["review_status"] >= criteria]
    #         )
    #     ]

    #     clinvar_benign_index = df.index[
    #         df["CLNSIG"].str.contains(r"[B|b]enign", regex=True)
    #         & ~df["CLNSIG"].str.contains(r"[C|c]onflicting", regex=True)
    #         & df["CLNREVSTAT"].isin(
    #             review_status_table.index[review_status_table["review_status"] >= 2]
    #         )
    #     ]

    #     known_pathogenic_index = clinvar_pathogenic_index
    #     known_pathogenic_index = known_pathogenic_index[~known_pathogenic_index.isin(clinvar_benign_index)]

    #     known_pathogenic_variant = df.loc[known_pathogenic_index].copy()
    #     known_pathogenic_variant = known_pathogenic_variant.apply(self.summarize_prediction, axis=1)

    #     self._log_df("known_pathogenic.output", known_pathogenic_variant, extra=f"criteria={criteria}")
    #     self._write_tsv("known_pathogenic_output", known_pathogenic_variant, "kept")
    #     return known_pathogenic_variant
    def known_pathogenic(self, input_variant, criteria):
        #### select pathogenic variants recorded in Clinvar (no conflicting) and AlphaMissense (LP/P) ####
        review_star_dict = {
            'no_assertion_provided': 0,
            'no_assertion_criteria_provided': 0,
            'no_assertion_for_the_individual_variant': 0,
            'criteria_provided,_conflicting_interpretations': 1,
            'criteria_provided,_single_submitter': 1,
            'criteria_provided,_multiple_submitters,_no_conflicts': 2,
            'reviewed_by_expert_panel': 3,
            'practice_guideline': 4
        }
        review_status_table = pd.DataFrame.from_dict(review_star_dict, orient='index', columns=['review_status'])
        print("Review status table:")
        print(review_status_table)

        df = input_variant.copy()

        # 欄位保護：避免 NaN / 缺欄位讓 .str.contains 爆掉
        for col in ["CLNSIG", "CLNREVSTAT"]:
            if col not in df.columns:
                df[col] = ""
            df[col] = df[col].fillna("").astype(str)

        # ---- ClinVar pathogenic index ----
        clinvar_pathogenic_index = df.index[
            df['CLNSIG'].str.contains(r'[P|p]athogenic', regex=True)
            & ~df['CLNSIG'].str.contains(r'[C|c]onflicting', regex=True)
            & df['CLNREVSTAT'].isin(
                review_status_table.index[review_status_table['review_status'] >= criteria]
            )
        ]
        print("ClinVar pathogenic index(ClinVar已知的致病基因):")
        print(clinvar_pathogenic_index)

        # ---- ClinVar benign index (strong benign) ----
        clinvar_benign_index = df.index[
            df['CLNSIG'].str.contains(r'[B|b]enign', regex=True)
            & ~df['CLNSIG'].str.contains(r'[C|c]onflicting', regex=True)
            & df['CLNREVSTAT'].isin(
                review_status_table.index[review_status_table['review_status'] >= 2]
            )
        ]
        print("ClinVar benign index(ClinVar已知的良性基因):")
        print(clinvar_benign_index)

        # =========================
        # AlphaMissense 取代 LOVD
        # =========================
        am_col = "am_class"  # <- 改成你實際欄位名（例如 alphamissense_class）
        if am_col not in df.columns:
            print(f"[WARN] missing column: {am_col}. AlphaMissense part skipped.")
            alphamissense_pathogenic_index = df.index[[]]  # 空 index
        else:
            am = df[am_col].fillna("").astype(str).str.strip().str.lower()
            am = am.replace({".": "", "nan": "", "none": ""})

            # 只找 likely_pathogenic / pathogenic
            alphamissense_pathogenic_index = df.index[am.isin(["likely_pathogenic", "pathogenic"])]

        print("AlphaMissense pathogenic index(AlphaMissense=likely_pathogenic/pathogenic):")
        print(alphamissense_pathogenic_index)

        # ---- union + exclude benign ----
        known_pathogenic_index = clinvar_pathogenic_index.union(alphamissense_pathogenic_index)
        known_pathogenic_index = known_pathogenic_index[~known_pathogenic_index.isin(clinvar_benign_index)]
        print("Known pathogenic index:")
        print(known_pathogenic_index)

        known_pathogenic_variant = df.loc[known_pathogenic_index, :].copy()
        print("Known pathogenic variants:")
        print(known_pathogenic_variant)

        known_pathogenic_variant = known_pathogenic_variant.apply(self.summarize_prediction, axis=1)
        return known_pathogenic_variant

    # -----------------------------
    # Predict suspect
    # -----------------------------
    def predict_suspect(self, input_variant):
        tool_set = [
            "Polyphen2_HVAR_pred","VEST3_score","MetaSVM_pred","MetaLR_pred",
            "CADD_phred","MutationTaster_pred","SIFT_pred","DANN_score",
            "dbscSNV_ADA_SCORE","dbscSNV_RF_SCORE",
        ]

        df = input_variant.copy()

        for c in tool_set:
            if c not in df.columns:
                df[c] = "."

        before = df.copy()
        df = df[
            (~df[tool_set].isin(["."]).all(1))
            | df.get("ExonicFunc.refGene", pd.Series([""] * len(df))).isin(
                ["stopgain", "stoploss", "startgain", "startloss"]
            )
        ].copy()
        self._log_filter("suspect.01.filter_has_tool_or_trunc", before, df, reason="has prediction or truncating")

        if df.shape[0] == 0:
            for c in ["deleterious_agreed","deleterious_tools","splicing_effect_agreed","splicing_effect_tools"]:
                df[c] = pd.Series(dtype=int)
            return df

        df = df.apply(self.summarize_prediction, axis=1)

        before2 = df.copy()
        exonic_func = df.get("ExonicFunc.refGene", pd.Series([""] * len(df))).astype(str)
        candidate_index = df.index[
            (df["deleterious_agreed"] >= 2)
            | (df["splicing_effect_agreed"] >= 2)
            | (exonic_func.isin(["stopgain","stoploss","startgain","startloss"]))
        ]
        suspect_variant = df.loc[candidate_index].copy()
        self._log_filter("suspect.02.pick_candidates", before2, suspect_variant, reason="deleterious/splicing>=2 or trunc")

        if suspect_variant.shape[0] > 0:
            for col in ["CLNSIG", "CLNREVSTAT"]:
                if col not in suspect_variant.columns:
                    suspect_variant[col] = ""
                suspect_variant[col] = suspect_variant[col].fillna("").astype(str)

            before3 = suspect_variant.copy()
            clinvar_non_benign_index = suspect_variant.index[
                ~(
                    suspect_variant["CLNSIG"].str.contains(r"[B|b]enign", regex=True)
                    & suspect_variant["CLNREVSTAT"].isin(
                        [
                            "criteria_provided,_multiple_submitters,_no_conflicts",
                            "reviewed_by_expert_panel",
                            "practice_guideline",
                        ]
                    )
                )
            ]
            suspect_variant = suspect_variant.loc[clinvar_non_benign_index].copy()
            self._log_filter("suspect.03.remove_strong_benign", before3, suspect_variant, reason="exclude strong benign")

        return suspect_variant

    # -----------------------------
    # Inheritance matching
    # -----------------------------
    def inheritance_matching(self, input_variant):
        homo_variant = input_variant[input_variant["GT"] == "hom"].copy()

        het_df = input_variant[input_variant["GT"] == "het"].copy()
        result = {}
        for g in het_df["Gene.refGene"].dropna().unique():
            n_class1 = het_df[(het_df["Gene.refGene"] == g) & (het_df["class"] == 1)].shape[0]
            n_class2 = het_df[(het_df["Gene.refGene"] == g) & (het_df["class"] == 2)].shape[0]
            n_class3 = het_df[(het_df["Gene.refGene"] == g) & (het_df["class"] == 3)].shape[0]
            result[g] = [n_class1, n_class2, n_class3]

        if len(result) == 0:
            tmp = pd.DataFrame(columns=["class1","class2","class3"])
        else:
            tmp = pd.DataFrame.from_dict(result, orient="index", columns=["class1","class2","class3"])

        two_hit_candidate = tmp[(tmp.sum(1) >= 2) & (tmp.sum(1) != tmp["class3"])]
        two_hit_variant = het_df[het_df["Gene.refGene"].isin(two_hit_candidate.index.to_list())].copy()
        return homo_variant, two_hit_variant

    # -----------------------------
    # Main layering with FULL logs
    # -----------------------------
    def layering(self):
        self.logger.info("===== WES_layering START =====")

        annot_table = self.annotation_table.copy()
        gt_input = self.genotype_table.copy()

        self._log_df("00.input.annot_table", annot_table)
        self._log_df("00.input.genotype_table", gt_input)

        ACMG_genes = self.load_ACMG()
        OMIM_table = self.load_OMIM()
        self._log_df("00.DB.OMIM_table", OMIM_table)

        phenotypeDrivenRanking = self.phenotypeDrivenRanking
        if phenotypeDrivenRanking is None:
            self.logger.info("[00.input] phenotypeDrivenRanking=None")
        else:
            self._log_df("00.input.phenotypeDrivenRanking", phenotypeDrivenRanking)

        # Step 01: normalize KEY + merge annot x genotype
        KEY = self.key_cols
        annot_table_norm = self._normalize_key_cols(annot_table, "annot_table")
        gt_input_norm = self._normalize_key_cols(gt_input, "gt_input")

        step = "01.merge_annot_gt"
        tmp = pd.merge(annot_table_norm, gt_input_norm, how="outer", on=KEY, indicator=True)
        self.logger.info(f"[{step}] outer merge indicator counts:\n{tmp['_merge'].value_counts()}")
        before_merge = annot_table_norm.copy()
        annot_table = tmp[tmp["_merge"] == "both"].drop(columns=["_merge"]).copy()
        self._log_filter(step, before_merge, annot_table, reason="inner kept only (both)")

        # Step 02: adjust column names & AF
        step = "02.adjust_cols_and_AF"
        before = annot_table.copy()

        annot_table.columns = [re.sub("refGeneWithVer$", "refGene", i) for i in annot_table.columns]

        annot_table = self._apply_selected_gnomad_af(annot_table)
        if "AF" not in annot_table.columns:
            annot_table["AF"] = -1
        annot_table["AF"] = annot_table["AF"].apply(self.adjust_AF)
        annot_table["AF"] = pd.to_numeric(annot_table["AF"], errors="coerce").fillna(-1).astype(float)

        self._log_filter(step, before, annot_table, reason=f"rename refGeneWithVer->refGene, selected gnomAD {self.gnomad_population} ({self.gnomad_af_column}) as AF, AF '.'->-1 and to float")

        # Step 03: merge OMIM
        step = "03.merge_OMIM"
        before = annot_table.copy()

        if "Gene.refGene" not in annot_table.columns:
            raise KeyError("annot_table missing Gene.refGene (after renaming).")

        annot_table = pd.merge(annot_table, OMIM_table, on="Gene.refGene", how="left")
        self._log_filter(step, before, annot_table, reason="left join OMIM by Gene.refGene")

        # Step 04: merge phenotypeDrivenRanking
        step = "04.merge_phenoRanking"
        before = annot_table.copy()

        if phenotypeDrivenRanking is not None:
            need_cols = ["Genes", "Max_Score", "Mean_Score"]
            for c in need_cols:
                if c not in phenotypeDrivenRanking.columns:
                    raise KeyError(f"phenotypeDrivenRanking missing column: {c}")

            annot_table = (
                annot_table.merge(
                    phenotypeDrivenRanking[need_cols],
                    left_on="Gene.refGene",
                    right_on="Genes",
                    how="left",
                )
                .fillna(-1)
                .copy()
            )
            annot_table["Max_Score"] = pd.to_numeric(annot_table["Max_Score"], errors="coerce").fillna(-1)
            annot_table["Mean_Score"] = pd.to_numeric(annot_table["Mean_Score"], errors="coerce").fillna(-1)
        else:
            annot_table["Max_Score"] = -1
            annot_table["Mean_Score"] = -1

        self._log_filter(step, before, annot_table, reason="left join phenotypeDrivenRanking (or set -1)")

        # Step 05: drug response
        step = "05.drug_response"
        self._log_df(step + ".input", annot_table)
        self._write_tsv(step, annot_table, "input")

        drug_response_variant, drug_response_demo = self.drug_response(annot_table)

        # Step 06: MAF cutoff
        step = "06.maf_cutoff"
        before = annot_table.copy()
        filtered_table = before[before["AF"] < self.maf_cutoff].copy()
        self._log_filter(step, before, filtered_table, reason=f"{self.gnomad_af_column} ({self.gnomad_population}) < {self.maf_cutoff}")

        # Step 06b: noncoding promoter/splice split（原樣保留）
        step = "06b.noncoding_promoterai_spliceai_split3"
        noncoding_base = filtered_table.copy()
        noncoding_only = noncoding_base[self._noncoding_mask(noncoding_base)].copy()

        prom = self._get_promoterai_score(noncoding_only)
        dsmax = self._get_spliceai_max_ds(noncoding_only)

        noncoding_only["PromoterAI_score_norm"] = prom
        noncoding_only["PromoterAI_pass"] = prom.abs() >= self.promoterai_abs_thr
        noncoding_only["PromoterAI_strong"] = prom.abs() >= self.promoterai_abs_strong

        noncoding_only["SpliceAI_maxDS"] = dsmax
        noncoding_only["SpliceAI_pass"] = dsmax >= self.spliceai_thr

        promoter_only = noncoding_only[noncoding_only["PromoterAI_pass"]].copy()
        splice_only = noncoding_only[noncoding_only["SpliceAI_pass"]].copy()
        both_pass = noncoding_only[noncoding_only["PromoterAI_pass"] | noncoding_only["SpliceAI_pass"]].copy()

        self._log_df(step + ".noncoding_only", noncoding_only)
        self._log_df(step + ".promoter_only", promoter_only,
                     extra=f"|PromoterAI|>={self.promoterai_abs_thr} & SpliceAI_maxDS<{self.spliceai_thr}")
        self._log_df(step + ".splice_only", splice_only,
                     extra=f"|PromoterAI|<{self.promoterai_abs_thr} & SpliceAI_maxDS>={self.spliceai_thr}")
        self._log_df(step + ".both", both_pass,
                     extra=f"|PromoterAI|>={self.promoterai_abs_thr} & SpliceAI_maxDS>={self.spliceai_thr}")

        # Step 07: remove drug_response
        step = "07.remove_drug_response"
        before = filtered_table.copy()
        filtered_table = self._exclude_by_key(filtered_table, drug_response_variant)
        self._log_filter(step, before, filtered_table, reason="exclude drug_response variants by KEY")

        # Step 08: known_pathogenic
        step = "08.known_pathogenic"
        self._log_df(step + ".input", filtered_table)
        self._write_tsv(step, filtered_table, "input")

        known_pathogenic_variant = self.known_pathogenic(filtered_table, self.review_status).copy()
        known_pathogenic_variant["class"] = 1

        self._log_df(step + ".output", known_pathogenic_variant)
        self._write_tsv(step, known_pathogenic_variant, "kept")

        pheno_genes_raw = self.gene_panel[0] if isinstance(self.gene_panel, (list, tuple)) and len(self.gene_panel) > 0 else str(self.gene_panel)
        pheno_genes = [g.strip() for g in str(pheno_genes_raw).split("、") if g.strip()]
        self.logger.info(f"[gene_panel] genes_count={len(pheno_genes)} genes_preview={pheno_genes[:20]}")

        known_pheno_variant = known_pathogenic_variant[known_pathogenic_variant["Gene.refGene"].isin(pheno_genes)].copy()
        known_ACMG_variant = known_pathogenic_variant[known_pathogenic_variant["Gene.refGene"].isin(ACMG_genes)].copy()
        known_other_variant = known_pathogenic_variant[
            ~known_pathogenic_variant.index.isin(known_pheno_variant.index)
            & ~known_pathogenic_variant.index.isin(known_ACMG_variant.index)
        ].copy()

        self._log_df("08a.known_pheno_variant", known_pheno_variant)
        self._log_df("08b.known_ACMG_variant", known_ACMG_variant)
        self._log_df("08c.known_other_variant", known_other_variant)

        # Step 09: remove known_pathogenic
        step = "09.remove_known_pathogenic"
        before = filtered_table.copy()
        filtered_table = self._exclude_by_key(filtered_table, known_pathogenic_variant)
        self._log_filter(step, before, filtered_table, reason="exclude known_pathogenic by KEY")

        # Step 10: suspect
        step = "10.suspect"
        self._log_df(step + ".input", filtered_table)
        self._write_tsv(step, filtered_table, "input")

        suspect_variant = self.predict_suspect(filtered_table).copy()
        suspect_variant["class"] = 2

        self._log_df(step + ".output", suspect_variant)
        self._write_tsv(step, suspect_variant, "kept")

        suspect_pheno_variant = suspect_variant[suspect_variant["Gene.refGene"].isin(pheno_genes)].copy()
        suspect_ACMG_variant = suspect_variant[suspect_variant["Gene.refGene"].isin(ACMG_genes)].copy()
        suspect_other_variant = suspect_variant[
            ~suspect_variant.index.isin(suspect_pheno_variant.index)
            & ~suspect_variant.index.isin(suspect_ACMG_variant.index)
        ].copy()

        self._log_df("10a.suspect_pheno_variant", suspect_pheno_variant)
        self._log_df("10b.suspect_ACMG_variant", suspect_ACMG_variant)
        self._log_df("10c.suspect_other_variant", suspect_other_variant)

        # Step 11: remove suspect
        step = "11.remove_suspect"
        before = filtered_table.copy()
        filtered_table = self._exclude_by_key(filtered_table, suspect_variant)
        self._log_filter(step, before, filtered_table, reason="exclude suspect by KEY")

        # Step 12: other pheno variant (class3)
        step = "12.other_pheno_variant"
        before = filtered_table.copy()
        filtered_table = filtered_table.copy()
        filtered_table["class"] = 3
        self._log_filter(step + ".base_set_class3", before, filtered_table, reason="set class=3 for remaining")

        other_pheno_variant = filtered_table[
            filtered_table["Gene.refGene"].isin(pheno_genes)
            & ~(filtered_table.get("Func.refGene", pd.Series([""] * len(filtered_table))).isin(["intronic", "intergenic"]))
        ].copy()
        if other_pheno_variant.shape[0] > 0:
            other_pheno_variant = other_pheno_variant.apply(self.summarize_prediction, axis=1)

        self._log_df(step + ".output", other_pheno_variant)
        self._write_tsv(step, other_pheno_variant, "kept")

        # Step 13: other variants for inheritance
        step = "13.other_variant_for_inheritance"
        other_variant = filtered_table[
            (filtered_table.get("Func.refGene", pd.Series([""] * len(filtered_table))).isin(["exonic"]))
            & ~(
                filtered_table.get("ExonicFunc.refGene", pd.Series([""] * len(filtered_table))).isin(
                    ["synonymous SNV", "unknown", "."]
                )
            )
        ].copy()
        if other_variant.shape[0] > 0:
            other_variant = other_variant.apply(self.summarize_prediction, axis=1)

        self._log_df(step + ".output", other_variant)
        self._write_tsv(step, other_variant, "kept")

        # Step 14: combine + inheritance
        step = "14.combine_and_inheritance_matching"
        variant_set = pd.concat([known_pathogenic_variant, suspect_variant, other_variant], axis=0, ignore_index=False, sort=False)
        self._log_df(step + ".variant_set", variant_set)
        self._write_tsv(step, variant_set, "kept")

        homo_variant, two_hit_variant = self.inheritance_matching(variant_set)
        homo_pheno_variant = homo_variant[homo_variant["Gene.refGene"].isin(pheno_genes)].copy()
        two_hit_pheno_variant = two_hit_variant[two_hit_variant["Gene.refGene"].isin(pheno_genes)].copy()

        self._log_df("14a.homo_variant", homo_variant)
        self._log_df("14b.two_hit_variant", two_hit_variant)
        self._log_df("14c.homo_pheno_variant", homo_pheno_variant)
        self._log_df("14d.two_hit_pheno_variant", two_hit_pheno_variant)

        parameters = {
            "known_pheno_variant": known_pheno_variant,
            "known_ACMG_variant": known_ACMG_variant,
            "known_other_variant": known_other_variant,
            "suspect_pheno_variant": suspect_pheno_variant,
            "suspect_ACMG_variant": suspect_ACMG_variant,
            "suspect_other_variant": suspect_other_variant,
            "drug_response_variant": drug_response_variant,
            "drug_response_demo": drug_response_demo,
            "other_variant": other_pheno_variant,
            "homo_pheno_variant": homo_pheno_variant,
            "two_hit_pheno_variant": two_hit_pheno_variant,
            "noncoding_promoter_splice_variant": both_pass,
        }

        self.logger.info("===== WES_layering DONE =====")
        for k, v in parameters.items():
            if isinstance(v, pd.DataFrame):
                self.logger.info(f"[RESULT] {k}: rows={v.shape[0]}")
        return parameters
