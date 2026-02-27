from dataclasses import dataclass
from pathlib import Path
import json
from datavalidator.extract.pbip_loader import PbipContext

@dataclass
class ReportPage:
    page_id: str
    display_name: str
    visual_count: int

@dataclass
class ReportExtraction:
    pages: list[ReportPage]
    theme_present: bool

def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8", errors="ignore"))

def extract_report(ctx: PbipContext) -> ReportExtraction:
    if not ctx.report_dir:
        return ReportExtraction(pages=[], theme_present=False)

    definition_dir = ctx.report_dir / "definition"
    pages_index = definition_dir / "pages" / "pages.json"
    report_json = definition_dir / "report.json"

    # Theme detection (best-effort)
    theme_present = False
    if report_json.exists():
        try:
            obj = _read_json(report_json)
            theme_present = "theme" in json.dumps(obj).lower()
        except Exception:
            pass

    if not pages_index.exists():
        return ReportExtraction(pages=[], theme_present=theme_present)

    idx = _read_json(pages_index)

    # Your structure: { "$schema":..., "pageOrder":[...], "activePageName":"..." }
    page_order = idx.get("pageOrder", [])
    if not isinstance(page_order, list) or not page_order:
        # fallback: just enumerate page folders
        page_order = [p.name for p in (definition_dir / "pages").iterdir() if p.is_dir()]

    pages: list[ReportPage] = []

    for pid in page_order:
        page_dir = definition_dir / "pages" / pid
        page_json = page_dir / "page.json"
        display_name = pid

        if page_json.exists():
            pobj = _read_json(page_json)
            if isinstance(pobj, dict):
                display_name = pobj.get("displayName") or pobj.get("name") or pobj.get("title") or pid

        visuals_dir = page_dir / "visuals"
        visual_count = len(list(visuals_dir.rglob("visual.json"))) if visuals_dir.exists() else 0

        pages.append(ReportPage(page_id=pid, display_name=display_name, visual_count=visual_count))

    return ReportExtraction(pages=pages, theme_present=theme_present)