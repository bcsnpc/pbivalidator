from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List
import re


@dataclass
class TableInfo:
    name: str
    columns: int
    measures: int
    is_hidden: bool
    file: str


_TABLE_NAME_RE = re.compile(r'^\s*table\s+"([^"]+)"', re.IGNORECASE | re.MULTILINE)
_MEASURE_RE = re.compile(r'^\s*measure\s+"[^"]+"', re.IGNORECASE | re.MULTILINE)
_COLUMN_RE = re.compile(r'^\s*column\s+"[^"]+"', re.IGNORECASE | re.MULTILINE)
_HIDDEN_RE = re.compile(r'^\s*isHidden\s*:\s*(true|false)', re.IGNORECASE | re.MULTILINE)


def _parse_table_tmdl(text: str, fallback_name: str) -> TableInfo:
    m = _TABLE_NAME_RE.search(text)
    name = m.group(1) if m else fallback_name

    measures = len(_MEASURE_RE.findall(text))
    cols = len(_COLUMN_RE.findall(text))

    hm = _HIDDEN_RE.search(text)
    hidden = (hm.group(1).lower() == "true") if hm else False

    return TableInfo(
        name=name,
        columns=cols,
        measures=measures,
        is_hidden=hidden,
        file=fallback_name,
    )


def extract_tables_from_pbip_semantic_model(pbip_root: Path) -> List[TableInfo]:
    """
    Source of truth for table inventory in PBIP:
      <root>/*.SemanticModel/definition/tables/*.tmdl
    """
    model_dir = None
    for p in pbip_root.iterdir():
        if p.is_dir() and p.name.endswith(".SemanticModel"):
            model_dir = p
            break
    if model_dir is None:
        return []

    tables_dir = model_dir / "definition" / "tables"
    if not tables_dir.exists():
        return []

    out: List[TableInfo] = []
    for fp in sorted(tables_dir.glob("*.tmdl")):
        txt = fp.read_text(encoding="utf-8", errors="ignore")
        out.append(_parse_table_tmdl(txt, fallback_name=fp.stem))
    return out


def build_model_snapshot(pbip_root: Path) -> Dict[str, Any]:
    tables = extract_tables_from_pbip_semantic_model(pbip_root)
    return {
        "tablesCount": len(tables),
        "tables": [
            {
                "name": t.name,
                "columns": t.columns,
                "measures": t.measures,
                "isHidden": t.is_hidden,
                "file": t.file,
            }
            for t in tables
        ],
        "hiddenCount": sum(1 for t in tables if t.is_hidden),
    }