import pandas as pd
import base64
import os
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import csv
import re
import glob
from neo4j import GraphDatabase
import math

def node_internal_id(node):
    return getattr(node, "element_id", node.id)

def node_to_external_id(node):
    if "NCCN_Node" in node.labels:
        return node.get("id")
    return node.get("name")

def clean_text(label) -> str:
    if label is None:
        return ""
    if isinstance(label, float) and math.isnan(label):
        return ""
    if not isinstance(label, str):
        return str(label)

    label = re.sub(r"_x[0-9A-Fa-f]{4}_", "", label)
    original = label
    label = re.sub(r"\nor \n", r"\n• ", label)
    label = re.sub(r"\nor\n", r"\n• ", label)
    label = re.sub(r"or\n", r"\n• ", label)
    label = re.sub(r"\nor", r"\n• ", label)

    if label != original and not label.lstrip().startswith("•"):
        label = "• " + label.lstrip()

    return label

def node_payload(node):
    if "NCCN_Node" in node.labels:
        return {
            "id": clean_text(node.get("id")),
            "label": clean_text(node.get("label")),
            "disease": clean_text(node.get("disease")),
            "page": clean_text(node.get("page")),
            "category": clean_text(node.get("category")),
        }
    return {
        "id": clean_text(node.get("name")),
        "label": clean_text(node.get("name")),
        "category": "VARIANT",
    }

def fetch_treatment_graph(query_str: str, driver, mmr_status):
    cypher = """
    MATCH p = (v:Variant {name: $q})-[:HAS_VARIANT]->(n:NCCN_Node)
              -[:LEADS_TO*1..3]->(m:NCCN_Node)
    WHERE   n.disease = $mmr_status
    RETURN p
    UNION
    MATCH p = (b:Biomarker)-[:HAS_BIOMARKER]->(n:NCCN_Node)
              -[:LEADS_TO*1..3]->(m:NCCN_Node)
    WHERE   toLower(b.name) CONTAINS toLower($q)
      AND   n.disease = $mmr_status
    RETURN p
    """

    nodes_by_internal, id_map, links = {}, {}, []

    with driver.session() as session:
        for record in session.run(cypher, q=query_str, mmr_status=mmr_status):
            path = record["p"]
            for node in path.nodes:
                iid = node_internal_id(node)
                if iid not in nodes_by_internal:
                    nodes_by_internal[iid] = node_payload(node)
                    id_map[iid] = node_to_external_id(node)
            for rel in path.relationships:
                sid = node_internal_id(rel.start_node)
                tid = node_internal_id(rel.end_node)
                links.append({"source": id_map[sid], "target": id_map[tid]})

    unique_links = {(l["source"], l["target"]): l for l in links}.values()

    filtered_ids = {
        n["id"]
        for n in nodes_by_internal.values()
        if n.get("category") in ("VARIANT", "BIOMARKER")
    }

    nodes_out = [n for n in nodes_by_internal.values() if n["id"] not in filtered_ids]
    links_out = [l for l in unique_links if l["source"] not in filtered_ids and l["target"] not in filtered_ids]

    return {"nodes": nodes_out, "links": links_out}

def search_treatment_point(variant_name, mmr_status, driver):
    query = """
    MATCH (v:Variant {name: $variant_name})-[:HAS_VARIANT]->(n:NCCN_Node)
    WHERE n.disease = $mmr_status
    RETURN n
    UNION
    MATCH (v:Biomarker {name: $variant_name})-[:HAS_BIOMARKER]->(n:NCCN_Node)
    WHERE n.disease = $mmr_status
    RETURN n
    """
    with driver.session() as session:
        results = session.run(query, variant_name=variant_name, mmr_status=mmr_status)
        return [record for record in results]

def search_treatment_form(variant_name, mmr_status, driver):
    query = """
    MATCH (v:Variant)-[:HAS_VARIANT]->(n:NCCN_Node)
    WHERE v.name IN [$variant_name] AND n.disease = $mmr_status
    RETURN DISTINCT v.name AS variant, n.label AS label, n.category AS category
    UNION
    MATCH (b:Biomarker)-[:HAS_BIOMARKER]->(n:NCCN_Node)
    WHERE toLower(b.name) CONTAINS toLower($variant_name) AND n.disease = $mmr_status
    RETURN DISTINCT b.name AS variant, n.label AS label, n.category AS category
    """
    with driver.session() as session:
        results = session.run(query, variant_name=variant_name, mmr_status=mmr_status)
        return [record.data() for record in results]

def serialize_node(node):
    return {
        "id": clean_text(node.get("id")),
        "label": clean_text(node.get("label")),
        "disease": clean_text(node.get("disease")),
        "page": clean_text(node.get("page")),
        "category": clean_text(node.get("category")),
    }

def convert_to_graph2(records):
    nodes_dict = {}
    for record in records:
        n = record["n"]
        n_id = clean_text(n["id"])
        if n_id not in nodes_dict:
            nodes_dict[n_id] = serialize_node(n)
    return {"nodes": list(nodes_dict.values()), "links": []}

def records_to_json(records, variant_name, output_path=None):
    json_data = []
    keyword = variant_name.lower().strip()
    for record in records:
        label_text = clean_text(record["label"])
        segments = [seg.strip() for seg in label_text.split("•") if seg.strip()]
        matched_segments = [f"• {seg}" for seg in segments if keyword in seg.lower()]
        if matched_segments:
            item = {
                "variant": record["variant"],
                "label": "\n".join(matched_segments),
                "category": record.get("category", "")
            }
            json_data.append(item)
    return json_data

def fetch_workup_graph(driver, mmr_status):
    cypher = """
    MATCH p = (n:NCCN_Node)-[:LEADS_TO*1..2]->(m:NCCN_Node)
    WHERE toString(n.disease) = $mmr_status
    AND ALL(x IN nodes(p) WHERE toUpper(toString(x.category)) = "WORKUP")
    RETURN p
    """

    nodes_by_internal, id_map, links = {}, {}, []

    with driver.session() as session:
        for record in session.run(cypher, mmr_status=mmr_status):
            path = record["p"]
            for node in path.nodes:
                iid = node_internal_id(node)
                if iid not in nodes_by_internal:
                    nodes_by_internal[iid] = node_payload(node)
                    id_map[iid] = node_to_external_id(node)
            for rel in path.relationships:
                sid = node_internal_id(rel.start_node)
                tid = node_internal_id(rel.end_node)
                links.append({
                    "source": id_map[sid],
                    "target": id_map[tid]
                })

    # 去除重複連線
    unique_links = {(l["source"], l["target"]): l for l in links}.values()

    # 最後組裝成跟 fetch_treatment_graph 相同格式
    return {
        "nodes": list(nodes_by_internal.values()),
        "links": list(unique_links)
    }


@csrf_exempt
def potential_treatment(request):
    if request.method == 'POST':
        data = json.loads(request.body.decode('utf-8'))
        variant_name = data.get('variant', '')
        mmr_status = data.get('mmr_status', '')
        cancer_status = data.get('cancer_status', '')

        if mmr_status.lower().strip() == 'unclassified / unknown':
            mmr_status = cancer_status
        else:
            mmr_status = mmr_status + ' ' +cancer_status
        print(mmr_status)

        if not variant_name:
            return JsonResponse({'error': 'No variant specified'}, status=400)

        NEO4J_URI = "bolt://140.116.214.138:7699"
        NEO4J_USER = "neo4j"
        NEO4J_PASSWORD = "your_password"

        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        try:
            treatment1 = fetch_treatment_graph(variant_name, driver, mmr_status)
            print(treatment1)
            treatment2_raw = search_treatment_point(variant_name, mmr_status, driver)
            treatment2 = convert_to_graph2(treatment2_raw)
            treatment3_raw = search_treatment_form(variant_name, mmr_status, driver)
            treatment3 = records_to_json(treatment3_raw, variant_name)
            workup = fetch_workup_graph(driver,mmr_status)
            print(workup)

            response_data = {
                "treatment_graph": treatment1,
                "treatment_point": treatment2,
                "treatment_form": treatment3,
                'workup':workup
            }

            return JsonResponse(response_data, json_dumps_params={'ensure_ascii': False, 'allow_nan': False})

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
        finally:
            driver.close()
    else:
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)
