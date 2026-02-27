from __future__ import annotations
from pathlib import Path
import json, re
from typing import Any, Dict, List, Tuple

# ------------------------
# small helpers
# ------------------------
def read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="ignore")

def read_json(p: Path) -> Any:
    return json.loads(read_text(p))

def clip(text: str, max_chars: int = 900) -> str:
    text = text.strip()
    return text if len(text) <= max_chars else text[:max_chars] + "\n...<clipped>..."

def evidence(path: Path, snippet: str) -> Dict[str, str]:
    return {"path": str(path), "snippet": clip(snippet)}

# ------------------------
# report inventory
# ------------------------
def build_report_inventory(report_dir: Path) -> Dict[str, Any]:
    definition = report_dir / "definition"
    pages_index = definition / "pages" / "pages.json"

    pages_meta = read_json(pages_index)
    page_order = pages_meta.get("pageOrder", [])
    active = pages_meta.get("activePageName")

    pages: List[Dict[str, Any]] = []
    visual_type_counts_global: Dict[str, int] = {}

    for pid in page_order:
        page_dir = definition / "pages" / pid
        page_json = page_dir / "page.json"
        page_obj = read_json(page_json) if page_json.exists() else {}
        display_name = page_obj.get("displayName") or page_obj.get("name") or pid

        visuals_dir = page_dir / "visuals"
        visual_files = list(visuals_dir.rglob("visual.json")) if visuals_dir.exists() else []

        vtypes: Dict[str, int] = {}
        samples: List[Dict[str, Any]] = []

        for vf in visual_files:
            obj = read_json(vf)
            vtype = (obj.get("visual") or {}).get("visualType") or "unknown"
            vtypes[vtype] = vtypes.get(vtype, 0) + 1
            visual_type_counts_global[vtype] = visual_type_counts_global.get(vtype, 0) + 1

            # keep only a few samples for trust, not everything
            if len(samples) < 3:
                samples.append({
                    "path": str(vf),
                    "visualType": vtype,
                    "position": obj.get("position", {}),
                })

        pages.append({
            "pageId": pid,
            "displayName": display_name,
            "size": {"width": page_obj.get("width"), "height": page_obj.get("height")},
            "visualCount": len(visual_files),
            "visualTypeCounts": vtypes,
            "samples": samples,
            "evidence": evidence(pages_index, json.dumps(pages_meta, indent=2)[:800]) if pid == page_order[0] else None
        })

    return {
        "activePageName": active,
        "pageCount": len(page_order),
        "pages": pages,
        "visualTypeCountsGlobal": visual_type_counts_global,
        "evidence_pages_json": evidence(pages_index, json.dumps(pages_meta, indent=2))
    }

# ------------------------
# semantic model inventory (tables/measures/columns)
# ------------------------
def extract_columns_tmdl(txt: str) -> List[str]:
    # common patterns in TMDL: "column <name>" or "column '<name>'"
    cols = re.findall(r"\bcolumn\s+'([^']+)'", txt)
    if cols:
        return cols
    cols = re.findall(r"\bcolumn\s+([A-Za-z0-9 _\-\.\[\]]+)\b", txt)
    # reduce noise: keep reasonable tokens
    return [c.strip() for c in cols if len(c.strip()) > 0][:500]

def extract_measures_tmdl(txt: str) -> List[str]:
    ms = re.findall(r"\bmeasure\s+'([^']+)'", txt)
    if ms:
        return ms
    ms = re.findall(r"\bmeasure\s+([A-Za-z0-9 _\-\.\[\]]+)\b", txt)
    return [m.strip() for m in ms if len(m.strip()) > 0][:500]

def extract_m_partition(txt: str) -> str | None:
    # capture partition blocks: "partition X = m ... source = <M>"
    m = re.search(r"partition\s+[^\r\n]+\s*=\s*m(.*)$", txt, re.S | re.I)
    return m.group(0) if m else None

def build_tables_inventory(tables_dir: Path) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    tables: List[Dict[str, Any]] = []
    pq_partitions: List[Dict[str, Any]] = []

    for tmdl in sorted(tables_dir.glob("*.tmdl")):
        txt = read_text(tmdl)
        cols = extract_columns_tmdl(txt)
        measures = extract_measures_tmdl(txt)

        tables.append({
            "name": tmdl.stem,
            "columnsCount": len(cols),
            "measuresCount": len(measures),
            "columnsSample": cols[:15],
            "measuresSample": measures[:15],
            "evidence": evidence(tmdl, txt[:1000])
        })

        part = extract_m_partition(txt)
        if part:
            pq_partitions.append({
                "table": tmdl.stem,
                "partitionSnippet": clip(part, 1200),
                "path": str(tmdl)
            })

    return tables, pq_partitions

# ------------------------
# relationships inventory (your real format: Table.Column)
# ------------------------
def build_relationships_inventory(rel_path: Path) -> Dict[str, Any]:
    if not rel_path.exists():
        return {"count": 0, "relationships": [], "evidence": None}

    txt = read_text(rel_path)

    blocks = re.findall(
        r"relationship\s+([^\r\n]+)\r?\n(.*?)(?=\r?\n\r?\nrelationship\s+|\Z)",
        txt,
        re.S | re.I
    )

    rels = []
    for rid, body in blocks:
        cf = re.search(r"crossFilteringBehavior:\s*([A-Za-z]+)", body)
        cross = (cf.group(1) if cf else "singleDirection").strip()

        fm = re.search(r"fromColumn:\s*([^\r\n]+)", body)
        tm = re.search(r"toColumn:\s*([^\r\n]+)", body)
        if not (fm and tm):
            continue

        fexpr = fm.group(1).strip()
        texpr = tm.group(1).strip()

        # table extraction: handles:
        #  - Table.Column
        #  - 'Dim Date'.Date
        def get_table(expr: str) -> str:
            if "." not in expr:
                return expr
            t = expr.split(".", 1)[0].strip()
            if t.startswith("'") and t.endswith("'"):
                t = t[1:-1]
            return t

        rels.append({
            "id": rid.strip(),
            "crossFilteringBehavior": cross,
            "fromColumn": fexpr,
            "toColumn": texpr,
            "fromTable": get_table(fexpr),
            "toTable": get_table(texpr),
        })

    return {
        "count": len(rels),
        "relationships": rels,
        "evidence": evidence(rel_path, txt[:1200])
    }

# ------------------------
# expressions/parameters inventory
# ------------------------
def build_expressions_inventory(expr_path: Path) -> Dict[str, Any]:
    if not expr_path.exists():
        return {"parameters": [], "evidence": None}

    txt = read_text(expr_path)

    # parameters in your file look like:
    # expression Host = "..." meta [IsParameterQuery = true, ...]
    params = []
    for m in re.finditer(r"expression\s+([A-Za-z0-9_ ]+)\s*=\s*(.+?)\s*meta\s*\[(.*?)\]", txt, re.S | re.I):
        name = m.group(1).strip()
        val = m.group(2).strip()
        meta = m.group(3)
        if "IsParameterQuery" in meta:
            params.append({
                "name": name,
                "valuePreview": clip(val, 200),
                "metaPreview": clip(meta, 200)
            })

    return {
        "parameters": params,
        "count": len(params),
        "evidence": evidence(expr_path, txt[:1200])
    }

# ------------------------
# main builder
# ------------------------
def build_inventory(pbip_root: Path) -> Dict[str, Any]:
    # pbip root contains folders like *.Report and *.SemanticModel
    report_dir = next(pbip_root.glob("*.Report"), None)
    model_dir = next(pbip_root.glob("*.SemanticModel"), None)

    out: Dict[str, Any] = {
        "root": str(pbip_root),
        "hasReport": bool(report_dir),
        "hasSemanticModel": bool(model_dir),
        "report": {},
        "model": {},
        "powerQuery": {},
    }

    if report_dir:
        out["report"] = build_report_inventory(report_dir)

    if model_dir:
        definition = model_dir / "definition"
        tables_dir = definition / "tables"
        rel_path = definition / "relationships.tmdl"
        expr_path = definition / "expressions.tmdl"

        tables, pq_parts = build_tables_inventory(tables_dir)
        rels = build_relationships_inventory(rel_path)
        exprs = build_expressions_inventory(expr_path)

        out["model"] = {
            "tables": tables,
            "tablesCount": len(tables),
            "relationships": rels,
            "expressions": exprs,
        }

        out["powerQuery"] = {
            "partitionsWithM": pq_parts,
            "count": len(pq_parts),
        }

    return out