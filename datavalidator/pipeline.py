from __future__ import annotations

import json
import os
from pathlib import Path

from datavalidator.analyze.inventory_builder import build_inventory
from datavalidator.analyze.findings_builder import build_findings
from datavalidator.report.render import render_audit_report

def run_pipeline(project_path: Path, out_dir: Path, run_ai: bool = False) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    inventory = build_inventory(project_path)
    bundle = build_findings(inventory)

    signals = bundle["signals"]
    findings = bundle["findings"]

    # Save core artifacts always
    (out_dir / "inventory.json").write_text(json.dumps(inventory, indent=2), encoding="utf-8")
    (out_dir / "signals.json").write_text(json.dumps(signals, indent=2), encoding="utf-8")
    (out_dir / "findings.json").write_text(json.dumps(findings, indent=2), encoding="utf-8")

    # AI layer (Power Query first)
    if run_ai:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY not set. .env is not loaded or env var missing.\n"
                "Fix: ensure .env at repo root and cli.py calls load_dotenv()."
            )

        from datavalidator.ai.pq_ai import generate_pq_ai
        ai_pq = generate_pq_ai(signals=signals, findings=findings)
        # merge into signals so template can render AI section without extra file reads
        signals = dict(signals)
        signals["ai"] = {"powerQuery": ai_pq}

        (out_dir / "ai_pq.json").write_text(json.dumps(ai_pq, indent=2), encoding="utf-8")
        (out_dir / "signals.json").write_text(json.dumps(signals, indent=2), encoding="utf-8")  # overwrite with ai included

    render_audit_report(out_dir=out_dir, inventory=inventory, findings=findings, signals=signals)
