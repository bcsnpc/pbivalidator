from __future__ import annotations

from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

def render_audit_report(out_dir: Path, inventory, findings, signals) -> None:
    templates_dir = Path(__file__).parent / "templates"
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(["html"]),
    )
    template = env.get_template("audit_report.html.j2")
    html = template.render(inventory=inventory, findings=findings, signals=signals)

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "report.html").write_text(html, encoding="utf-8")