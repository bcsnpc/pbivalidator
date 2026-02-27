from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
import re


def _safe_read_text(fp: Path) -> str:
    return fp.read_text(encoding="utf-8", errors="ignore")


def _find_pbip_root_from_ctx(ctx: Any) -> Path:
    if hasattr(ctx, "report_dir") and getattr(ctx, "report_dir"):
        return Path(getattr(ctx, "report_dir")).parent
    if hasattr(ctx, "model_dir") and getattr(ctx, "model_dir"):
        return Path(getattr(ctx, "model_dir")).parent
    for attr in ("root", "root_dir", "project_path", "projectPath"):
        if hasattr(ctx, attr) and getattr(ctx, attr):
            return Path(getattr(ctx, attr))
    if isinstance(ctx, (str, Path)):
        return Path(ctx)
    raise ValueError("extract_semantic_model: cannot determine PBIP root from ctx")


def _find_semantic_model_dir(project_root: Path) -> Optional[Path]:
    for p in project_root.iterdir():
        if p.is_dir() and p.name.endswith(".SemanticModel"):
            return p
    return None


# relationship blocks are usually like: relationship { ... } or relationship "name" { ... }
_REL_RE = re.compile(r'^\s*relationship\b', re.IGNORECASE | re.MULTILINE)
_PARAM_RE = re.compile(
    r"expression\s+([A-Za-z_][A-Za-z0-9_]*)\s*=.*?meta\s*\[(.*?)\]",
    re.IGNORECASE | re.DOTALL,
)
_IS_PARAM_RE = re.compile(r"\bIsParameterQuery\s*=\s*true\b", re.IGNORECASE)
_PARTITION_MODE_RE = re.compile(r"^\s*partition\s+.+?=\s*([A-Za-z_][A-Za-z0-9_]*)", re.IGNORECASE | re.MULTILINE)
_MEASURE_RE = re.compile(r"^\s*measure\b", re.IGNORECASE | re.MULTILINE)
_COLUMN_RE = re.compile(r"^\s*column\b", re.IGNORECASE | re.MULTILINE)


def _extract_parameters(expressions_text: str) -> List[Dict[str, str]]:
    params: List[Dict[str, str]] = []
    for m in _PARAM_RE.finditer(expressions_text):
        name = m.group(1).strip()
        meta = m.group(2) or ""
        if _IS_PARAM_RE.search(meta):
            params.append({"name": name})
    return params


def _extract_table_meta(table_text: str) -> Dict[str, Any]:
    pm = _PARTITION_MODE_RE.search(table_text)
    partition_mode = (pm.group(1).lower() if pm else "unknown")
    measure_count = len(_MEASURE_RE.findall(table_text))
    column_count = len(_COLUMN_RE.findall(table_text))
    is_calculated = partition_mode == "calculated"
    # Heuristic: measure holder/helper table (many measures, no real columns)
    is_measures_only = (measure_count > 0 and column_count <= 1)
    return {
        "partitionMode": partition_mode,
        "measureCount": measure_count,
        "columnCount": column_count,
        "isCalculated": is_calculated,
        "isMeasuresOnly": is_measures_only,
    }


def extract_semantic_model(ctx: Any) -> Dict[str, Any]:
    """
    Robust semantic model inventory for PBIP.
    - tablesCount: number of .tmdl files under definition/tables
    - relationships.count: number of relationship entries in relationships.tmdl
    - tables: list of table names inferred from file names (reliable)
    """
    project_root = _find_pbip_root_from_ctx(ctx)
    model_dir = _find_semantic_model_dir(project_root)
    if not model_dir:
        return {"tablesCount": 0, "relationships": {"count": 0}, "tables": []}

    def_dir = model_dir / "definition"
    tables_dir = def_dir / "tables"
    rels_file = def_dir / "relationships.tmdl"
    expr_file = def_dir / "expressions.tmdl"

    table_files: List[Path] = []
    if tables_dir.exists():
        table_files = sorted(tables_dir.glob("*.tmdl"))

    tables: List[Dict[str, Any]] = []
    for f in table_files:
        txt = _safe_read_text(f)
        meta = _extract_table_meta(txt)
        tables.append({"name": f.stem, "path": str(f), **meta})
    tables_count = len(table_files)

    rel_count = 0
    if rels_file.exists():
        rel_text = _safe_read_text(rels_file)
        rel_count = len(_REL_RE.findall(rel_text))

    parameters: List[Dict[str, str]] = []
    if expr_file.exists():
        expr_text = _safe_read_text(expr_file)
        parameters = _extract_parameters(expr_text)

    return {
        "tablesCount": tables_count,
        "relationships": {"count": rel_count},
        "tables": tables,
        "parameters": parameters,
        "expressions": {"parameters": parameters},
    }
