# NCKU Genomics Platform — 2026-07-21 deployment

這個目錄固定目前平台的 frontend、backend 與 PostgreSQL 版本，並包含建立於
2026-07-21 的 public schema 資料庫快照。帳號密碼不寫入 Compose，部署時由 `.env`
提供。

## 內容

- Frontend: `takeshi945/nckumtb:frontend-clinical-ui-20260721`
- Frontend offline image: `images/frontend-clinical-ui-20260721.tar.gz`
- Backend overlay: `takeshi945/nckumtb:backend-wgs-germline-20260721`
- WGS task tools: `ncku-wgs-python:20260721`
- Database: `postgres:15`
- Restore helper: `postgres:16`
- Database snapshot: `database/platform_public_20260721.dump`

## 主機資料目錄

先準備以下結構；大型註解資料不包含在此備份包中：

```text
DATA_ROOT/
├── VEP/
├── annovar/annovar/
├── annotsv/
├── backend/db.sqlite3
├── media/
├── mondo/
│   ├── mondo_terms.tsv
│   ├── mondo_gene_associations.tsv
│   └── release.json
├── literature_rag/literature.sqlite3
├── wgs_germline/
└── tmp/
```

另外準備 `WGS_REFERENCE_ROOT/hg38.fa` 與 `hg38.fa.fai`。首次部署可將本包內
`state/backend/db.sqlite3` 與 `state/mondo/*` 複製到上述位置；如果目標位置已有
正式資料，請勿覆寫。

## 首次部署

```bash
cp .env.example .env
# 編輯 .env，設定絕對路徑、DB 帳號與安全密碼
docker compose --env-file .env config --quiet
sha256sum -c SHA256SUMS
docker load -i images/frontend-clinical-ui-20260721.tar.gz
docker compose --env-file .env pull postgres db_restore_public
docker compose --env-file .env --profile build-only build backend wgs_tools
docker compose --env-file .env up -d postgres
docker compose --env-file .env --profile restore run --rm db_restore_public
docker compose --env-file .env up -d
```

開啟 `http://<server-ip>:3002/variant/`。若修改 `FRONTEND_PORT`，請改用對應 port。

## 檢查狀態

```bash
docker compose --env-file .env ps
docker compose --env-file .env logs --tail=100 backend
docker compose --env-file .env logs --tail=100 frontend
```

`db_restore_public` 會在偵測到既有平台資料時跳過 restore，避免覆寫既有資料。
若要重新還原，請建立全新的 Compose project/volume，不要刪除仍在使用的正式資料庫 volume。

## 備份與搬移

搬移時至少保留本目錄、資料庫 dump，以及 `DATA_ROOT` 下的大型資料與媒體檔。
Docker named volume `pgdata` 是執行中的資料庫；dump 則是可攜式初始化快照。
Frontend 因映像倉庫沒有推送權限，已直接封裝為離線 archive；Backend 與 PostgreSQL
基底映像由 registry 下載，WGS backend overlay 與 task tools 則由本包內 source build。

## WGS Germline

WGS API、Nextflow DSL2 pipeline 和 MONDO/Monarch index builder 位於
`backend_wgs/`。執行中的上傳、Nextflow work、log 與結果會持久化在
`${DATA_ROOT}/wgs_germline`。VEP 預設使用 24 forks，可由 `.env` 的
VEP 預設依染色體切分，以 `WGS_VEP_MAX_PARALLEL=8` 與
`WGS_VEP_FORK_PER_SHARD=3` 調整（預設合計約 24 CPU）。PharmCAT 仍使用完整 VCF 單次執行。

Gene literature RAG 使用本機 SQLite FTS5 corpus；備份包預載 ACMG SF genes。
若要啟動本機 open-weight LLM，依 `models/README.md` 將 Apache-2.0 的 Qwen2.5
GGUF 模型放入 `LITERATURE_MODEL_ROOT`，再執行
`docker compose --env-file .env --profile literature-llm up -d literature_llm`。

預先提供的 MONDO runtime index 版本為 MONDO 2026-07-06、Monarch
2026-04-07，並整合官方 MONDO Rare Disease subset；autocomplete 會以
`Rare disease` badge 標示。若要更新，請依 `backend_wgs/README.md` 重新產生。
