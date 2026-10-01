"""Persistent local PubMed store and FTS5 retrieval for literature RAG."""
import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def database_path():
    return Path(os.environ.get("LITERATURE_RAG_DB", "/wgs_reference/literature_rag/literature.sqlite3"))


def connect():
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.executescript("""
        CREATE TABLE IF NOT EXISTS articles (
            pmid TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            abstract TEXT NOT NULL,
            journal TEXT NOT NULL DEFAULT '',
            publication_year TEXT NOT NULL DEFAULT '',
            url TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'PubMed',
            fetched_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS gene_articles (
            gene TEXT NOT NULL,
            pmid TEXT NOT NULL REFERENCES articles(pmid) ON DELETE CASCADE,
            retrieval_query TEXT NOT NULL DEFAULT '',
            phenotype_labels TEXT NOT NULL DEFAULT '[]',
            PRIMARY KEY (gene, pmid)
        );
        CREATE INDEX IF NOT EXISTS gene_articles_gene_idx ON gene_articles(gene);
        CREATE VIRTUAL TABLE IF NOT EXISTS article_fts USING fts5(
            pmid UNINDEXED, title, abstract, journal, tokenize='unicode61'
        );
        CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
    """)
    connection.execute("INSERT OR REPLACE INTO metadata(key,value) VALUES('schema_version','1')")
    connection.commit()
    return connection


def store_articles(gene, query, phenotypes, articles):
    now = datetime.now(timezone.utc).isoformat()
    with connect() as db:
        for article in articles:
            pmid = str(article["pmid"])
            db.execute("""INSERT INTO articles(pmid,title,abstract,journal,publication_year,url,source,fetched_at)
                VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(pmid) DO UPDATE SET
                title=excluded.title, abstract=excluded.abstract, journal=excluded.journal,
                publication_year=excluded.publication_year, url=excluded.url, fetched_at=excluded.fetched_at""",
                (pmid, article.get("title", ""), article.get("abstract", ""), article.get("journal", ""),
                 article.get("year", ""), article.get("url", ""), "PubMed", now))
            db.execute("DELETE FROM article_fts WHERE pmid=?", (pmid,))
            db.execute("INSERT INTO article_fts(pmid,title,abstract,journal) VALUES(?,?,?,?)",
                       (pmid, article.get("title", ""), article.get("abstract", ""), article.get("journal", "")))
            db.execute("""INSERT INTO gene_articles(gene,pmid,retrieval_query,phenotype_labels)
                VALUES(?,?,?,?) ON CONFLICT(gene,pmid) DO UPDATE SET
                retrieval_query=excluded.retrieval_query, phenotype_labels=excluded.phenotype_labels""",
                (gene.upper(), pmid, query, json.dumps(phenotypes, ensure_ascii=False)))
        db.execute("INSERT OR REPLACE INTO metadata(key,value) VALUES('last_updated',?)", (now,))


def search_articles(gene, phenotypes=None, limit=8):
    gene = gene.upper()
    tokens = []
    for label in phenotypes or []:
        tokens.extend(re.findall(r"[A-Za-z0-9]{3,}", label)[:5])
    with connect() as db:
        if tokens:
            match = " OR ".join(f'"{token}"' for token in dict.fromkeys(tokens[:12]))
            rows = db.execute("""SELECT a.*, bm25(article_fts) AS rank
                FROM gene_articles ga JOIN articles a ON a.pmid=ga.pmid
                JOIN article_fts ON article_fts.pmid=a.pmid
                WHERE ga.gene=? AND article_fts MATCH ?
                ORDER BY rank, a.publication_year DESC LIMIT ?""", (gene, match, limit)).fetchall()
        else:
            rows = db.execute("""SELECT a.* FROM gene_articles ga JOIN articles a ON a.pmid=ga.pmid
                WHERE ga.gene=? ORDER BY a.publication_year DESC LIMIT ?""", (gene, limit)).fetchall()
    return [{"pmid": row["pmid"], "title": row["title"], "abstract": row["abstract"],
             "journal": row["journal"], "year": row["publication_year"], "url": row["url"]} for row in rows]


def statistics():
    with connect() as db:
        articles = db.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
        genes = db.execute("SELECT COUNT(DISTINCT gene) FROM gene_articles").fetchone()[0]
        updated = db.execute("SELECT value FROM metadata WHERE key='last_updated'").fetchone()
    return {"articles": articles, "genes": genes, "last_updated": updated[0] if updated else None, "schema_version": 1}
