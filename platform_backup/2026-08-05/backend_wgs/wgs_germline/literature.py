"""Retrieval-augmented gene literature summaries using PubMed and a local LLM."""
import hashlib
import json
import os
import re
import threading
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

from .literature_store import search_articles, store_articles


NCBI_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
GENE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,39}$")
_NCBI_LOCK = threading.Lock()
_LAST_NCBI_REQUEST = 0.0
_CACHE_LOCKS = {}
_CACHE_LOCKS_GUARD = threading.Lock()


def _cache_lock(cache):
    """Return one process-local lock per cache key to deduplicate inference."""
    key = str(cache)
    with _CACHE_LOCKS_GUARD:
        return _CACHE_LOCKS.setdefault(key, threading.Lock())


def _read_usable_cache(cache):
    try:
        result = json.loads(cache.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return None
    # Transient model failures are diagnostic records, not reusable cache.
    return result if result.get("status") in {"complete", "no_evidence"} else None


def _write_cache(cache, result):
    cache.parent.mkdir(parents=True, exist_ok=True)
    temporary = cache.with_suffix(cache.suffix + f".{threading.get_ident()}.tmp")
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(cache)


def _with_cache_metadata(result, cache, hit, inference_performed):
    response = dict(result)
    response["cache"] = {
        "hit": hit,
        "stored": result.get("status") in {"complete", "no_evidence"},
        "key": cache.stem,
    }
    response["inference_performed"] = inference_performed
    return response


def _request(url, data=None, headers=None, timeout=45):
    global _LAST_NCBI_REQUEST
    if url.startswith(NCBI_BASE):
        with _NCBI_LOCK:
            delay = 0.36 - (time.monotonic() - _LAST_NCBI_REQUEST)
            if delay > 0:
                time.sleep(delay)
            _LAST_NCBI_REQUEST = time.monotonic()
    request = urllib.request.Request(url, data=data, headers={
        "User-Agent": os.environ.get("LITERATURE_USER_AGENT", "NCKU-MTB/1.0 literature-rag"),
        **(headers or {}),
    })
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def _pubmed_articles(gene, phenotypes, variant="", limit=8):
    phenotype_query = " OR ".join(f'"{label}"[Title/Abstract]' for label in phenotypes[:4] if label)
    subject = f"({phenotype_query})" if phenotype_query else "(disease[Title/Abstract] OR phenotype[Title/Abstract])"
    variant_query = f' OR "{variant}"[Title/Abstract]' if variant else ""
    query = f'("{gene}"[Title/Abstract] OR "{gene}"[Gene Name]) AND {subject}{variant_query}'
    common = {
        "tool": "ncku_mtb_literature_rag",
        "email": os.environ.get("NCBI_EMAIL", ""),
    }
    search_url = f"{NCBI_BASE}/esearch.fcgi?" + urllib.parse.urlencode({
        **common, "db": "pubmed", "term": query, "retmode": "json",
        "retmax": limit, "sort": "relevance",
    })
    search = json.loads(_request(search_url))
    pmids = search.get("esearchresult", {}).get("idlist", [])
    if not pmids:
        return query, []
    fetch_url = f"{NCBI_BASE}/efetch.fcgi?" + urllib.parse.urlencode({
        **common, "db": "pubmed", "id": ",".join(pmids), "retmode": "xml",
    })
    root = ET.fromstring(_request(fetch_url))
    articles = []
    for record in root.findall(".//PubmedArticle"):
        citation = record.find("MedlineCitation")
        article = citation.find("Article") if citation is not None else None
        if article is None:
            continue
        pmid = "".join(citation.findtext("PMID", default="")).strip()
        title = "".join(article.find("ArticleTitle").itertext()) if article.find("ArticleTitle") is not None else ""
        abstract = "\n".join("".join(node.itertext()) for node in article.findall("Abstract/AbstractText"))
        journal = article.findtext("Journal/Title", default="")
        year = article.findtext("Journal/JournalIssue/PubDate/Year", default="") or article.findtext("Journal/JournalIssue/PubDate/MedlineDate", default="")[:4]
        if pmid and (title or abstract):
            articles.append({"pmid": pmid, "title": title, "abstract": abstract, "journal": journal, "year": year,
                             "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"})
    order = {pmid: index for index, pmid in enumerate(pmids)}
    articles.sort(key=lambda item: order.get(item["pmid"], 999))
    return query, articles


def _extract_json(text):
    text = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start:end + 1])
        raise


def _generate(gene, variant, phenotypes, articles):
    endpoint = os.environ.get("LITERATURE_LLM_URL", "http://literature_llm:8080/v1/chat/completions")
    model = os.environ.get("LITERATURE_LLM_MODEL", "local-medical-instruct")
    contexts = []
    for item in articles:
        contexts.append(f"PMID {item['pmid']} | {item['year']} | {item['title']}\n{item['abstract'][:3500]}")
    schema = {
        "type": "object", "additionalProperties": False,
        "properties": {
            "summary": {"type": "string"},
            "phenotype_relevance": {"type": "string"},
            "inheritance": {"type": "string"},
            "variant_evidence": {"type": "string"},
            "limitations": {"type": "array", "items": {"type": "string"}, "maxItems": 8},
            "citations": {"type": "array", "items": {
                "type": "object", "additionalProperties": False,
                "properties": {"pmid": {"type": "string", "enum": [item["pmid"] for item in articles]},
                               "claims": {"type": "array", "items": {"type": "string", "maxLength": 180}, "minItems": 1, "maxItems": 3}},
                "required": ["pmid", "claims"],
            }, "minItems": 1, "maxItems": len(articles)},
        },
        "required": ["summary", "phenotype_relevance", "inheritance", "variant_evidence", "limitations", "citations"],
    }
    context_text = "\n\n".join(contexts)
    prompt = f"""Gene: {gene}
Variant: {variant or 'not supplied'}
Phenotypes: {', '.join(phenotypes) or 'not supplied'}

Evidence records:
{context_text}

Return one JSON object with fields summary, phenotype_relevance, inheritance,
variant_evidence, limitations, and citations (PMID plus supported claims).
Use only the evidence records. Do not infer pathogenicity, diagnose, recommend treatment, or cite any PMID not supplied.
Every substantive narrative claim must be represented in citations. Citation claims must be paraphrases of at most 20 words;
never copy sentences verbatim from an abstract. Clearly say when evidence is absent or conflicting.
If no variant was supplied, variant_evidence must state that no variant-specific assessment was possible.
Keep each narrative field under 60 words and include at most three short claims per cited PMID."""
    body = json.dumps({
        "model": model,
        "temperature": 0.1,
        # Leave enough room for the constrained JSON object to close. The
        # tighter per-field limits above prevent unnecessarily long output.
        "max_tokens": 1400,
        "response_format": {"type": "json_schema", "json_schema": {"name": "literature_summary", "strict": True, "schema": schema}},
        "messages": [
            {"role": "system", "content": "You summarize biomedical literature conservatively. Every factual claim must be traceable to the supplied PubMed records."},
            {"role": "user", "content": prompt},
        ],
    }).encode()
    raw = _request(endpoint, data=body, headers={"Content-Type": "application/json"}, timeout=int(os.environ.get("LITERATURE_LLM_TIMEOUT", "300")))
    response = json.loads(raw)
    result = _extract_json(response["choices"][0]["message"]["content"])
    allowed = {item["pmid"] for item in articles}
    citations, seen_pmids = [], set()
    for item in result.get("citations", []):
        pmid = str(item.get("pmid", ""))
        if pmid not in allowed or pmid in seen_pmids:
            continue
        # Do not display model-reproduced abstract fragments. The model selects
        # only from an enum of retrieved PMIDs; the UI links to the source.
        citations.append({"pmid": pmid, "claims": ["Evidence source used for the gene and phenotype synthesis."]})
        seen_pmids.add(pmid)
    result["citations"] = citations
    for key in ("summary", "phenotype_relevance", "inheritance", "variant_evidence"):
        result[key] = str(result.get(key) or "Not established from the retrieved literature.")
    if not variant:
        result["variant_evidence"] = "No variant was supplied; variant-specific evidence was not assessed."
    result["limitations"] = [str(item) for item in result.get("limitations", [])][:8]
    if not citations:
        result["limitations"].append("No concise citation claim passed output validation; review the retrieved publications directly.")
    return result


def summarize(directory: Path, metadata: dict, gene: str, variant="", refresh=False):
    gene = gene.strip().upper()
    variant = variant.strip()[:160]
    if not GENE_RE.fullmatch(gene):
        raise ValueError("Invalid gene symbol")
    phenotypes = [str(item.get("label") or item.get("name") or "").strip()
                  for item in metadata.get("settings", {}).get("phenotypes", [])]
    phenotypes = [item for item in phenotypes if item]
    key_data = json.dumps({"gene": gene, "variant": variant, "phenotypes": phenotypes}, sort_keys=True)
    key = hashlib.sha256(key_data.encode()).hexdigest()[:20]
    cache = directory / "literature" / f"{gene}.{key}.json"
    if not refresh:
        cached = _read_usable_cache(cache)
        if cached:
            return _with_cache_metadata(cached, cache, hit=True, inference_performed=False)

    # A double-checked per-key lock prevents two simultaneous requests from
    # running the local model for the same gene/variant/phenotype input.
    with _cache_lock(cache):
        if not refresh:
            cached = _read_usable_cache(cache)
            if cached:
                return _with_cache_metadata(cached, cache, hit=True, inference_performed=False)

        articles = search_articles(gene, phenotypes, limit=8)
        query = "local-rag-index"
        retrieval_source = "local"
        if refresh or not articles:
            query, fetched = _pubmed_articles(gene, phenotypes, variant)
            if fetched:
                store_articles(gene, query, phenotypes, fetched)
                articles = search_articles(gene, phenotypes, limit=8) or fetched
            retrieval_source = "pubmed-refresh"
        result = {
            "gene": gene, "variant": variant, "phenotypes": phenotypes,
            "query": query, "retrieval_source": retrieval_source, "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "articles": articles, "generator": "local-open-weight-llm", "status": "complete",
        }
        if not articles:
            result.update({"status": "no_evidence", "summary": "No matching PubMed records were retrieved.", "citations": []})
        else:
            try:
                result.update(_generate(gene, variant, phenotypes, articles))
            except Exception as exc:
                result.update({"status": "model_unavailable", "summary": "Literature was retrieved, but the local inference service is unavailable.",
                               "limitations": [str(exc)[:300]], "citations": []})
        _write_cache(cache, result)
        return _with_cache_metadata(result, cache, hit=False, inference_performed=bool(articles))
