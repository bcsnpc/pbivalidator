from __future__ import annotations
from typing import Any, Dict, List
import re

HEAVY_PATTERNS = [
    ("Table.Buffer", "HIGH", "PQ101", "Table.Buffer can break query folding"),
    ("Value.NativeQuery", "MED", "PQ102", "NativeQuery requires careful parameterization and security review"),
    ("Table.Group", "MED", "PQ103", "Grouping in Power Query can be expensive; prefer backend when possible"),
    ("Table.Sort", "LOW", "PQ104", "Sorting in Power Query can be expensive; validate folding"),
]

def pq_insights(inv: Dict[str, Any]) -> List[Dict[str, Any]]:
    findings = []
    pq = inv.get("powerQuery", {})
    parts = pq.get("partitionsWithM", [])

    # parameters list (from expressions)
    params = (inv.get("model", {}).get("expressions", {}) or {}).get("parameters", [])
    param_names = {p["name"] for p in params}

    for p in parts:
        mtxt = p.get("partitionSnippet", "")

        # heavy patterns
        for pat, sev, fid, title in HEAVY_PATTERNS:
            if pat in mtxt:
                findings.append({
                    "id": fid,
                    "category": "PowerQuery",
                    "severity": sev,
                    "title": title,
                    "message": f"Found '{pat}' in table '{p['table']}'.",
                    "recommendation": "Validate folding and consider pushing transformations to the source (SQL/view) where feasible.",
                    "evidence": [{"path": p["path"], "snippet": mtxt}],
                })

        # step bloat (count #"<step>")
        steps = re.findall(r'#"\s*[^"]+\s*"', mtxt)
        if len(steps) >= 25:
            findings.append({
                "id": "PQ201",
                "category": "PowerQuery",
                "severity": "MED",
                "title": "Power Query step bloat",
                "message": f"Table '{p['table']}' has ~{len(steps)} transformation steps.",
                "recommendation": "Reduce steps (merge renames/types) and push heavy logic upstream when possible.",
                "evidence": [{"path": p["path"], "snippet": mtxt}],
            })

        # “hardcoding readiness” heuristic:
        # if lots of quoted literals AND few parameter usages
        literal_count = len(re.findall(r'"[^"]{3,}"', mtxt))
        param_used = sum(1 for n in param_names if n in mtxt)
        if literal_count >= 12 and param_used == 0:
            findings.append({
                "id": "PQ301",
                "category": "PowerQuery",
                "severity": "HIGH",
                "title": "Likely hardcoded data access",
                "message": f"Table '{p['table']}' contains many string literals but does not reference known parameters.",
                "recommendation": "Parameterize host/database/catalog/schema names for safe DEV→QA→PROD promotion.",
                "evidence": [{"path": p["path"], "snippet": mtxt}],
            })

    # global: parameters summary
    if params:
        findings.append({
            "id": "PQ000",
            "category": "PowerQuery",
            "severity": "INFO",
            "title": "Detected Power Query parameters",
            "message": f"Found {len(params)} parameters (example: {', '.join(sorted(list(param_names))[:6])}).",
            "recommendation": "Ensure all environment-specific values are parameterized and used consistently across queries.",
            "evidence": [inv["model"]["expressions"]["evidence"]],
        })

    return findings