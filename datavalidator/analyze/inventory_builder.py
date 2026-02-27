from __future__ import annotations

from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Dict

from datavalidator.extract.pbip_loader import load_pbip
from datavalidator.extract.pq_extractor import extract_powerquery
from datavalidator.extract.report_extractor import extract_report
from datavalidator.extract.tmdl_extractor import extract_semantic_model


def _to_jsonable(x: Any) -> Any:
    if x is None:
        return None
    if isinstance(x, (str, int, float, bool, list, dict)):
        return x
    if is_dataclass(x):
        return asdict(x)
    if hasattr(x, "dict") and callable(getattr(x, "dict")):
        return x.dict()
    if hasattr(x, "__dict__"):
        return dict(x.__dict__)
    return str(x)


def build_inventory(project_path: Path) -> Dict[str, Any]:
    project_path = Path(project_path)
    ctx = load_pbip(project_path)

    pq = _to_jsonable(extract_powerquery(ctx)) or {}
    rp = _to_jsonable(extract_report(ctx)) or {}
    model = _to_jsonable(extract_semantic_model(ctx)) or {}

    pq.setdefault("queries", [])
    pq.setdefault("count", len(pq.get("queries") or []))
    pq.setdefault("partitionsWithM", pq.get("partitionsWithM") or pq.get("queries") or [])

    return {
        "rootDir": str(project_path),
        "project": {"rootDir": str(project_path), "name": project_path.name},
        "paths": {
            "reportDir": str(getattr(ctx, "report_dir", "") or ""),
            "semanticModelDir": str(getattr(ctx, "model_dir", "") or ""),
        },
        "powerQuery": pq,
        "report": rp,
        "model": model,
    }