from __future__ import annotations

from typing import Any, Dict, List

from datavalidator.analyze.signals_builder import build_signals


def build_findings(inventory: Dict[str, Any]) -> Dict[str, Any]:
    signals = build_signals(inventory)
    findings: List[Dict[str, Any]] = []

    pq = (signals.get("powerQuery") or {})
    pq_count = pq.get("count", 0)
    inc = signals.get("incremental") or {}
    inc_ready = bool(inc.get("hasRangeParamsOrRefs"))
    param_names = (signals.get("parameters") or {}).get("names", [])
    hardcoding = signals.get("hardcoding") or {}
    naming = signals.get("naming") or {}
    folding = pq.get("foldingByTable") or []

    # Findings QA can action
    if pq_count == 0:
        findings.append({
            "id": "PQ000",
            "severity": "HIGH",
            "category": "PowerQuery",
            "title": "No Power Query partitions extracted",
            "message": "Could not find partition blocks in SemanticModel TMDL tables. PQ validation cannot run.",
            "recommendation": "Confirm PBIP uses Import partitions with M in table .tmdl files. If model is DirectQuery or stores M elsewhere, extend extractor to scan expressions.tmdl.",
            "evidence": {"powerQueryKeys": list((inventory.get("powerQuery") or {}).keys())}
        })

    if not inc_ready:
        folding_problem_tables = [t for t in folding if t.get("breakers")]
        findings.append({
            "id": "PQ010",
            "severity": "INFO",
            "category": "PowerQuery",
            "title": "No incremental refresh configuration detected",
            "message": "Incremental refresh is optional and not currently configured (RangeStart/RangeEnd not detected).",
            "recommendation": (
                "If you choose to configure incremental refresh, first make sure key source queries are foldable. "
                f"Current folding-risk tables flagged: {len(folding_problem_tables)}."
            ),
            "evidence": {
                "paramNames": param_names,
                "foldingRiskTables": [{"table": t.get("table"), "breakers": t.get("breakers")} for t in folding_problem_tables[:10]],
            }
        })

    hardcoded_count = hardcoding.get("count", 0)
    if hardcoded_count > 0:
        findings.append({
            "id": "PQ020",
            "severity": "HIGH",
            "category": "PowerQuery",
            "title": "Hard-coded source references detected",
            "message": f"Detected {hardcoded_count} M source snippets with hard-coded host/path/url literals.",
            "recommendation": "Move source values to parameters (e.g., Host, Server, Database, ApiBaseUrl) and reference those parameters in source steps.",
            "evidence": {"examples": (hardcoding.get("hits") or [])[:10]}
        })

    coverage = hardcoding.get("sourceCoverage") or []
    non_param = [r for r in coverage if r.get("status") != "parameterized"]
    if coverage and non_param:
        findings.append({
            "id": "PQ021",
            "severity": "MED",
            "category": "PowerQuery",
            "title": "Not all extracted queries appear parameterized",
            "message": f"{len(non_param)} of {len(coverage)} extracted sources are not confidently parameterized.",
            "recommendation": "Standardize source access so each query uses shared parameters or parameterized functions.",
            "evidence": {"nonParameterized": non_param[:15]}
        })

    tables_with_breakers = [t for t in folding if t.get("breakers")]
    if tables_with_breakers:
        findings.append({
            "id": "PQ030",
            "severity": "MED",
            "category": "PowerQuery",
            "title": "Potential query folding breakers found",
            "message": f"{len(tables_with_breakers)} tables contain patterns that often prevent folding.",
            "recommendation": "Review those queries in Power Query and validate folding with View Native Query/diagnostics.",
            "evidence": {
                "topBreakers": pq.get("topFoldingBreakers", []),
                "tables": [{"table": t.get("table"), "breakers": t.get("breakers")} for t in tables_with_breakers[:15]],
            }
        })

    step_bloat = [t for t in folding if (t.get("stepCount") or 0) >= 25]
    if step_bloat:
        findings.append({
            "id": "PQ031",
            "severity": "LOW",
            "category": "PowerQuery",
            "title": "Large transformation chains detected",
            "message": f"{len(step_bloat)} tables have 25+ transformation steps.",
            "recommendation": "Simplify transformations and move heavy logic upstream where practical.",
            "evidence": {"tables": [{"table": t.get("table"), "stepCount": t.get("stepCount")} for t in step_bloat[:15]]}
        })

    possible_late_filter = [t for t in folding if (t.get("heavyOps") or 0) >= 3 and not t.get("hasFilterHint")]
    if possible_late_filter:
        findings.append({
            "id": "PQ032",
            "severity": "MED",
            "category": "PowerQuery",
            "title": "Potential late filtering in some M queries",
            "message": f"{len(possible_late_filter)} tables show several heavy operations with no filter hint.",
            "recommendation": "Apply row filters early in M to improve folding and refresh performance.",
            "evidence": {"tables": [{"table": t.get("table"), "heavyOps": t.get("heavyOps")} for t in possible_late_filter[:15]]}
        })

    dominant_style = naming.get("dominantTableStyle")
    outliers = naming.get("outlierTables") or []
    coverage_ratio = naming.get("dominantCoverage")
    if dominant_style and outliers:
        findings.append({
            "id": "NC010",
            "severity": "LOW" if (coverage_ratio or 0) >= 0.5 else "MED",
            "category": "Naming",
            "title": "Inconsistent table naming convention",
            "message": f"Dominant table naming style is '{dominant_style}', but {len(outliers)} table names are outliers.",
            "recommendation": "Adopt the dominant naming style and rename outliers for consistency.",
            "evidence": {
                "dominantStyle": dominant_style,
                "styleDistribution": naming.get("tableStyles", {}),
                "outliers": outliers[:25],
            }
        })

    if dominant_style:
        findings.append({
            "id": "NC011",
            "severity": "INFO",
            "category": "Naming",
            "title": "Detected dominant table naming convention",
            "message": f"Dominant style inferred as '{dominant_style}' across model tables.",
            "recommendation": "Use this style as the project naming standard for new objects.",
            "evidence": {
                "styleDistribution": naming.get("tableStyles", {}),
                "dominantCoverage": coverage_ratio,
            }
        })

    return {"signals": signals, "findings": findings}
