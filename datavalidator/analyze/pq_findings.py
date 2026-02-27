from __future__ import annotations

import re
from typing import Any, Dict, List


# Folding breaker-ish patterns (heuristic)
FOLDING_BREAKERS = [
    (re.compile(r"\bTable\.Buffer\b", re.IGNORECASE), "Table.Buffer often blocks folding and forces local evaluation."),
    (re.compile(r"\bBinary\.Decompress\b", re.IGNORECASE), "Embedded binary/data steps typically mean no folding."),
    (re.compile(r"\bWeb\.Contents\b", re.IGNORECASE), "Web.Contents / API sources typically won’t fold like SQL sources."),
    (re.compile(r"\bOdbc\.Query\b", re.IGNORECASE), "Odbc.Query can be folding-hostile depending on connector."),
    (re.compile(r"\bText\.From\b|\bNumber\.ToText\b", re.IGNORECASE), "Text/number conversions mid-pipeline often reduce folding."),
    (re.compile(r"\bTable\.ToRecords\b|\bRecord\.ToTable\b", re.IGNORECASE), "Record/List materialization typically breaks folding."),
]

RE_FILTER = re.compile(r"\bTable\.SelectRows\b|\bTable\.RowCount\b|\bWHERE\b", re.IGNORECASE)
RE_HEAVY = re.compile(r"\bTable\.(Group|NestedJoin|Join|ExpandTableColumn|AddColumn|TransformColumns)\b", re.IGNORECASE)
RE_NATIVE_QUERY = re.compile(r"\bValue\.NativeQuery\s*\(", re.IGNORECASE)
RE_RANGE = re.compile(r"\bRangeStart\b|\bRangeEnd\b", re.IGNORECASE)


def build_pq_findings(inventory: Dict[str, Any], signals: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    pq = (signals.get("powerQuery") or {})
    items: List[Dict[str, Any]] = pq.get("items") or []

    if not items:
        out.append(
            {
                "id": "PQ000",
                "category": "PowerQuery",
                "severity": "HIGH",
                "title": "No Power Query M sources extracted",
                "message": "No Power Query snippets were detected in the PBIP semantic model table files.",
                "recommendation": "Confirm the model has Import/Hybrid tables and that M is present in table .tmdl Source blocks. If M is elsewhere in your PBIP version, extend extractor to scan additional files.",
                "evidence": {"powerQueryCount": 0},
            }
        )
        return out

    # Incremental readiness
    if not (signals.get("incremental") or {}).get("hasRangeParamsOrRefs"):
        out.append(
            {
                "id": "PQ010",
                "category": "PowerQuery",
                "severity": "MED",
                "title": "Incremental refresh readiness not detected",
                "message": "RangeStart/RangeEnd not detected in parameters or in M snippets.",
                "recommendation": "If incremental refresh is required: add RangeStart/RangeEnd parameters, apply an early date filter using them, and then configure incremental refresh in the semantic model.",
                "evidence": {"paramNames": (signals.get("parameters") or {}).get("names", [])},
            }
        )

    # Hard-coded sources
    hardcoding = (signals.get("hardcoding") or {})
    if hardcoding.get("count", 0) > 0:
        out.append(
            {
                "id": "PQ100",
                "category": "PowerQuery",
                "severity": "HIGH",
                "title": "Hard-coded source hints detected in M",
                "message": f"Detected {hardcoding.get('count')} potential hard-coded host/db references in M snippets.",
                "recommendation": "Parameterize server/workspace/catalog/database where possible (especially for dev/qa/prod portability).",
                "evidence": {"examples": hardcoding.get("hits", [])[:10]},
            }
        )

    # Folding breaker scan + heavy ops + filter placement heuristic
    for it in items:
        snip = it.get("mSnippet") or ""
        table = it.get("table")
        path = it.get("path")
        is_native = bool(RE_NATIVE_QUERY.search(snip))

        breakers = []
        for rx, why in FOLDING_BREAKERS:
            if rx.search(snip):
                breakers.append({"pattern": rx.pattern, "why": why})

        heavy_ops = len(RE_HEAVY.findall(snip))
        has_filter = bool(RE_FILTER.search(snip))

        # Late filter heuristic: heavy ops but no filter reference
        late_filter = (heavy_ops >= 3) and (not has_filter)

        if breakers:
            out.append(
                {
                    "id": "PQ210",
                    "category": "PowerQuery",
                    "severity": "MED" if not is_native else "HIGH",
                    "title": "Potential query folding breakers detected",
                    "message": f"'{table}' contains patterns that commonly prevent folding.",
                    "recommendation": "Reorder steps so filters happen early, avoid Table.Buffer unless proven necessary, and validate folding using View Native Query / diagnostics.",
                    "evidence": {"table": table, "path": path, "breakers": breakers[:6]},
                }
            )

        if late_filter:
            out.append(
                {
                    "id": "PQ220",
                    "category": "PowerQuery",
                    "severity": "MED",
                    "title": "Filters may be applied late (heuristic)",
                    "message": f"'{table}' has multiple heavy transformation ops but no obvious early filter.",
                    "recommendation": "Try moving row filters (Table.SelectRows) as early as possible to improve folding and refresh time.",
                    "evidence": {"table": table, "path": path, "heavyOps": heavy_ops},
                }
            )

        # Native query warning for incremental refresh (per MS guidance)
        if is_native and RE_RANGE.search(snip):
            out.append(
                {
                    "id": "PQ230",
                    "category": "PowerQuery",
                    "severity": "HIGH",
                    "title": "Native query + incremental parameters detected",
                    "message": f"'{table}' uses Value.NativeQuery and references RangeStart/RangeEnd. This often undermines incremental refresh folding and can force full data retrieval depending on pattern.",
                    "recommendation": "Validate incremental refresh folding carefully. Consider pushing filters into the native query in a folding-friendly way and test refresh behavior.",
                    "evidence": {"table": table, "path": path},
                }
            )

    return out