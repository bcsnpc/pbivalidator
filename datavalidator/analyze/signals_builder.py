from __future__ import annotations

import re
from typing import Any, Dict, List


_RE_HARDCODED_HOST = re.compile(r"(https?://[^\s\"']+)|(\b[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z]{2,}\b)")
_RE_RANGE = re.compile(r"\bRangeStart\b|\bRangeEnd\b", re.IGNORECASE)
_RE_STEP = re.compile(r'#"\s*[^"]+\s*"')
_RE_FILTER = re.compile(r"\bTable\.SelectRows\b|\bWHERE\b", re.IGNORECASE)
_RE_HEAVY = re.compile(
    r"\bTable\.(Group|Join|NestedJoin|ExpandTableColumn|TransformColumns|AddColumn|Sort)\b",
    re.IGNORECASE,
)

_FOLDING_BREAKERS = [
    (re.compile(r"\bTable\.Buffer\b", re.IGNORECASE), "Table.Buffer"),
    (re.compile(r"\bBinary\.Decompress\b", re.IGNORECASE), "Binary.Decompress"),
    (re.compile(r"\bTable\.ToRecords\b|\bRecord\.ToTable\b", re.IGNORECASE), "Record/List materialization"),
    (re.compile(r"\bOdbc\.Query\b", re.IGNORECASE), "Odbc.Query"),
]

_SOURCE_LITERAL_PATTERNS = [
    re.compile(r"\bSql\.Database\s*\(\s*\"[^\"]+\"\s*,\s*\"[^\"]+\"", re.IGNORECASE),
    re.compile(r"\bWeb\.Contents\s*\(\s*\"https?://", re.IGNORECASE),
    re.compile(r"\bFile\.Contents\s*\(\s*\"[A-Za-z]:\\", re.IGNORECASE),
    re.compile(r"\bOdbc\.DataSource\s*\(\s*\"[^\"]+\"", re.IGNORECASE),
    re.compile(r"\bDatabricks\.Catalogs\s*\(\s*\"[^\"]+\"", re.IGNORECASE),
]
_SOURCE_PARAM_HINT = re.compile(
    r"\b(Sql\.Database|Databricks\.Catalogs|Web\.Contents|File\.Contents|Odbc\.DataSource)\s*\(\s*[A-Za-z_][A-Za-z0-9_]*",
    re.IGNORECASE,
)
_SOURCE_PATTERNS = [
    (re.compile(r"\bSql\.Database\b", re.IGNORECASE), "SQL Server"),
    (re.compile(r"\bDatabricks\.Catalogs\b", re.IGNORECASE), "Databricks"),
    (re.compile(r"\bPowerBI\.Dataflows\b", re.IGNORECASE), "Power BI Dataflows"),
    (re.compile(r"\bWeb\.Contents\b", re.IGNORECASE), "Web/API"),
    (re.compile(r"\bFile\.Contents\b", re.IGNORECASE), "File"),
    (re.compile(r"\bOdbc\.(DataSource|Query)\b", re.IGNORECASE), "ODBC"),
    (re.compile(r"\bOleDb\.DataSource\b", re.IGNORECASE), "OLE DB"),
    (re.compile(r"\bSnowflake\.Databases\b", re.IGNORECASE), "Snowflake"),
    (re.compile(r"\bGoogleBigQuery\.Database\b", re.IGNORECASE), "BigQuery"),
    (re.compile(r"\bSapHana\.Database\b", re.IGNORECASE), "SAP HANA"),
]


def _name_style(name: str) -> str:
    if re.fullmatch(r"[a-z][a-z0-9_]*", name):
        return "snake_case"
    if re.fullmatch(r"[A-Z][A-Za-z0-9]*", name):
        return "PascalCase"
    if re.fullmatch(r"[a-z][A-Za-z0-9]*", name) and any(c.isupper() for c in name):
        return "camelCase"
    if " " in name:
        return "space_separated"
    if "-" in name:
        return "kebab-case"
    return "other"


def build_signals(inventory: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert raw inventory into small, reliable signals for findings + AI prompts.
    """
    signals: Dict[str, Any] = {}

    pq = inventory.get("powerQuery") or {}
    raw_pq_items: List[Dict[str, Any]] = pq.get("queries") or []

    # Param extraction (best-effort): from model expressions/parameters if present
    model = inventory.get("model") or {}
    params_a = model.get("parameters") or []
    params_b = ((model.get("expressions") or {}).get("parameters") or [])
    param_names = sorted(
        {
            p.get("name")
            for p in (list(params_a) + list(params_b))
            if isinstance(p, dict) and p.get("name")
        }
    )
    signals["parameters"] = {"names": param_names}

    # Incremental readiness: RangeStart/RangeEnd in params OR in M snippet
    model_tables = model.get("tables") or []
    table_meta_by_name = {
        t.get("name"): t
        for t in model_tables
        if isinstance(t, dict) and t.get("name")
    }

    # Exclude calculated / measure-holder tables from PQ and naming analysis
    excluded_table_names = {
        name
        for name, meta in table_meta_by_name.items()
        if meta.get("isCalculated") or meta.get("isMeasuresOnly")
    }
    pq_items = [it for it in raw_pq_items if it.get("table") not in excluded_table_names]
    pq_count = len(pq_items)

    has_range = ("RangeStart" in param_names or "RangeEnd" in param_names) or any(
        _RE_RANGE.search((it.get("mSnippet") or "")) for it in pq_items
    )
    signals["incremental"] = {"hasRangeParamsOrRefs": bool(has_range)}

    # Hard-coded vs parameterized source hints
    hardcoded_hits = []
    source_coverage = []
    source_counts: Dict[str, int] = {}
    sources_by_table = []
    folding_by_table = []
    breaker_counts: Dict[str, int] = {}

    for it in pq_items:
        table = it.get("table")
        path = it.get("path")
        snip = it.get("mSnippet") or ""
        matched_literal = None
        for rx in _SOURCE_LITERAL_PATTERNS:
            lm = rx.search(snip)
            if lm:
                matched_literal = lm.group(0)[:220]
                break

        generic_host_hit = None
        m = _RE_HARDCODED_HOST.search(snip)
        if m:
            generic_host_hit = m.group(0)

        is_param_source = bool(_SOURCE_PARAM_HINT.search(snip)) or any(
            re.search(rf"\b{re.escape(pn)}\b", snip) for pn in param_names
        )

        if matched_literal or generic_host_hit:
            hardcoded_hits.append(
                {
                    "table": table,
                    "path": path,
                    "hit": matched_literal or generic_host_hit,
                }
            )

        status = "parameterized" if is_param_source and not (matched_literal or generic_host_hit) else "hardcodedOrLiteral"
        if not matched_literal and not generic_host_hit and not is_param_source:
            status = "unknown"
        source_coverage.append({"table": table, "path": path, "status": status})

        matched_sources = []
        for rx, source_name in _SOURCE_PATTERNS:
            if rx.search(snip):
                matched_sources.append(source_name)
                source_counts[source_name] = source_counts.get(source_name, 0) + 1
        if bool(it.get("isNativeQuery")):
            matched_sources.append("Native Query")
            source_counts["Native Query"] = source_counts.get("Native Query", 0) + 1

        normalized_sources = sorted(set(matched_sources)) or ["Unknown"]
        for src in normalized_sources:
            if src == "Unknown":
                source_counts[src] = source_counts.get(src, 0) + 1
        sources_by_table.append({"table": table, "path": path, "sources": normalized_sources})

        # Folding heuristics
        breakers = []
        for rx, label in _FOLDING_BREAKERS:
            if rx.search(snip):
                breakers.append(label)
                breaker_counts[label] = breaker_counts.get(label, 0) + 1
        heavy_ops = len(_RE_HEAVY.findall(snip))
        has_filter = bool(_RE_FILTER.search(snip))
        steps = len(_RE_STEP.findall(snip))
        folding_by_table.append(
            {
                "table": table,
                "path": path,
                "breakers": breakers,
                "stepCount": steps,
                "heavyOps": heavy_ops,
                "hasFilterHint": has_filter,
                "isNativeQuery": bool(it.get("isNativeQuery")),
            }
        )

    top_breakers = [
        {"pattern": k, "count": v}
        for k, v in sorted(breaker_counts.items(), key=lambda kv: kv[1], reverse=True)
    ][:8]

    # Naming convention dominance from semantic model tables
    table_names = [
        t.get("name", "")
        for t in model_tables
        if isinstance(t, dict) and t.get("name") and t.get("name") not in excluded_table_names
    ]
    style_counts: Dict[str, int] = {}
    for nm in table_names:
        style = _name_style(nm)
        style_counts[style] = style_counts.get(style, 0) + 1
    dominant_style = None
    dominant_count = 0
    if style_counts:
        dominant_style, dominant_count = sorted(style_counts.items(), key=lambda kv: kv[1], reverse=True)[0]
    outliers = []
    if dominant_style:
        outliers = [nm for nm in table_names if _name_style(nm) != dominant_style][:50]

    signals["powerQuery"] = {
        "count": pq_count,
        "items": pq_items,
        "excludedTables": sorted(excluded_table_names),
        "topFoldingBreakers": top_breakers,
        "foldingByTable": folding_by_table,
    }
    signals["hardcoding"] = {
        "hits": hardcoded_hits[:25],
        "count": len(hardcoded_hits),
        "sourceCoverage": source_coverage,
    }
    connector_rows = [
        {"name": k, "count": v}
        for k, v in sorted(source_counts.items(), key=lambda kv: kv[1], reverse=True)
    ]
    signals["sources"] = {
        "connectors": connector_rows,
        "tableSources": sources_by_table,
        "countDistinct": len([r for r in connector_rows if r.get("name") != "Unknown"]),
        "multipleSources": len([r for r in connector_rows if r.get("name") != "Unknown"]) > 1,
    }
    signals["naming"] = {
        "tableStyles": style_counts,
        "dominantTableStyle": dominant_style,
        "dominantCoverage": (dominant_count / len(table_names)) if table_names else None,
        "outlierTables": outliers,
        "tableCount": len(table_names),
    }
    signals["model"] = {
        "tablesCount": model.get("tablesCount"),
        "relationships": model.get("relationships") or {},
    }
    report = inventory.get("report") or {}
    signals["report"] = {
        "pageCount": len(report.get("pages") or []),
        "themePresent": bool(report.get("theme_present")),
    }

    return signals
