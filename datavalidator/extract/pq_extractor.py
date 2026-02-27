from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class PQItem:
    table: str
    path: str
    kind: str  # e.g. "SourceBlock"
    sourceType: str  # "m" | "nativeQuery" | "daxOrOther" | "unknown"
    isNativeQuery: bool
    containsSQL: bool
    mSnippet: Optional[str]
    confidence: float


@dataclass
class PowerQueryExtraction:
    count: int
    source_type: str  # "table_source_scan"
    queries: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return {"count": self.count, "source_type": self.source_type, "queries": self.queries}


# Heuristics: what "looks like" M vs not
_RE_M_HINTS = re.compile(
    r"\b(let|in)\b|"
    r"\b(Sql\.Database|Odbc\.DataSource|OleDb\.DataSource|Snowflake\.Databases|Databricks\.Catalogs|SapHana\.Database|GoogleBigQuery\.Database)\b|"
    r"\b(Table\.(SelectRows|RemoveColumns|RenameColumns|TransformColumns|Group|Join|NestedJoin|AddColumn|ExpandTableColumn|Buffer)\b)",
    re.IGNORECASE | re.MULTILINE,
)

_RE_NATIVE_QUERY = re.compile(r"\bValue\.NativeQuery\s*\(", re.IGNORECASE)
_RE_DAXISH = re.compile(r"\bNAMEOF\s*\(|\{\s*\(\"", re.IGNORECASE)  # tuples / NAMEOF often show up in calc tables
_RE_SQL_TEXT = re.compile(r"\b(SELECT|WITH|FROM|JOIN|GROUP\s+BY|WHERE)\b", re.IGNORECASE)


def extract_powerquery(ctx_or_root: Any) -> PowerQueryExtraction:
    """
    Extract PQ-ish snippets from PBIP by scanning SemanticModel table .tmdl files
    for 'Source =' blocks. This is heuristic but works well for PBIP exports.
    """
    root = _resolve_root(ctx_or_root)
    tmdl_tables_dir = _find_tables_dir(root)
    items: List[PQItem] = []

    if not tmdl_tables_dir or not tmdl_tables_dir.exists():
        return PowerQueryExtraction(count=0, source_type="table_source_scan", queries=[])

    for tmdl in sorted(tmdl_tables_dir.glob("*.tmdl")):
        table_name = tmdl.stem
        text = tmdl.read_text(encoding="utf-8", errors="ignore")

        # Collect candidate "Source =" blocks (Power BI often stores source expressions inside table definitions)
        for block in _extract_source_blocks(text):
            snippet = block.strip()
            is_native = bool(_RE_NATIVE_QUERY.search(snippet))
            contains_sql = bool(_RE_SQL_TEXT.search(snippet)) or ("#(lf)" in snippet and "SELECT" in snippet.upper())

            # Classify
            if _RE_DAXISH.search(snippet) and not _RE_M_HINTS.search(snippet):
                source_type = "daxOrOther"
                confidence = 0.85
                m_snip = None
            elif _RE_M_HINTS.search(snippet) or is_native:
                source_type = "nativeQuery" if is_native else "m"
                confidence = 0.90 if is_native else 0.80
                m_snip = snippet
            else:
                source_type = "unknown"
                confidence = 0.30
                m_snip = None

            items.append(
                PQItem(
                    table=table_name,
                    path=str(tmdl),
                    kind="SourceBlock",
                    sourceType=source_type,
                    isNativeQuery=is_native,
                    containsSQL=contains_sql,
                    mSnippet=m_snip,
                    confidence=confidence,
                )
            )

    # Keep only the PQ-relevant ones for downstream PQ rules, but still expose all in inventory if you want later.
    pq_relevant = [it for it in items if it.sourceType in ("m", "nativeQuery") and it.mSnippet]

    return PowerQueryExtraction(
        count=len(pq_relevant),
        source_type="table_source_scan",
        queries=[asdict(it) for it in pq_relevant],
    )


def _resolve_root(ctx_or_root: Any) -> Path:
    if isinstance(ctx_or_root, (str, Path)):
        return Path(ctx_or_root)
    # Try common ctx shapes
    for attr in ("root", "project_root", "projectPath", "path"):
        if hasattr(ctx_or_root, attr):
            return Path(getattr(ctx_or_root, attr))
    raise ValueError("extract_powerquery: cannot determine PBIP root from ctx")


def _find_tables_dir(root: Path) -> Optional[Path]:
    # Root contains *.SemanticModel folder
    sm = None
    for p in root.iterdir():
        if p.is_dir() and p.name.endswith(".SemanticModel"):
            sm = p
            break
    if not sm:
        # user may pass the semantic model folder directly
        if root.is_dir() and root.name.endswith(".SemanticModel"):
            sm = root
    if not sm:
        return None

    tables_dir = sm / "definition" / "tables"
    return tables_dir if tables_dir.exists() else None


def _extract_source_blocks(tmdl_text: str) -> List[str]:
    """
    Extract blocks that start with 'Source =' until a likely end.
    PBIP/TMDL formatting varies, so we keep this heuristic and safe.
    """
    blocks: List[str] = []
    # A loose pattern: capture from "Source =" to the next "\n      " that looks like a new property OR end of file
    # This will also catch Table.FromRows(...) blocks etc.
    pattern = re.compile(r"(?ms)^\s*Source\s*=\s*(.+?)(?=\n\s*[A-Za-z_][A-Za-z0-9_\s\[\]\-]*\s*=|\n\s*partition\s|'measure\s|\Z)")
    for m in pattern.finditer(tmdl_text):
        blocks.append(m.group(1))
    return blocks