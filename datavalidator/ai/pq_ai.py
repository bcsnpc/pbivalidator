from __future__ import annotations

import os
from typing import Any, Dict, List

from openai import OpenAI

def _model_name() -> str:
    return os.environ.get("OPENAI_MODEL", "gpt-5")

def generate_pq_ai(signals: Dict[str, Any], findings: List[Dict[str, Any]] | None = None) -> Dict[str, Any]:
    """
    Takes signals.json content (already computed heuristics) and asks AI for:
      - 3-8 prioritized recommendations
      - risk highlights (folding, native query, incremental readiness, hardcoded sources)
      - action steps for developer + QA wording
    Returns a JSON dict (safe to dump).
    """
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    pq = signals.get("powerQuery") or {}
    model = signals.get("model") or {}
    report = signals.get("report") or {}
    hardcoding = signals.get("hardcoding") or {}
    naming = signals.get("naming") or {}
    incremental = signals.get("incremental") or {}
    params = signals.get("parameters") or {}
    findings = findings or []

    # Keep the prompt compact to avoid token waste. We are NOT sending raw TMDL here yet.
    prompt_text = f"""
You are a senior Power BI / Fabric BI engineer and QA lead.
Given the following extracted signals from a PBIP project, produce actionable Power Query recommendations.

OUTPUT STRICT JSON with keys:
- "summary" (1 paragraph)
- "findings" (array of objects: {{severity, title, why_it_matters, evidence, fix_steps[]}})
- "quick_wins" (array of short action bullets)
- "questions_for_dev" (array of concrete questions)

SIGNALS:
project_model_tables={model.get("tablesCount")}
relationships_count={((model.get("relationships") or {}).get("count"))}
report_pages={report.get("pageCount")}
pq_query_count={pq.get("count")}
pq_top_breakers={pq.get("topFoldingBreakers", [])}
incremental={incremental}
parameters={params}
hardcoding={hardcoding}
naming={naming}

RULE_BASED_FINDINGS={findings}

Be practical. Focus on query folding, parameterization, naming consistency, refresh readiness, and developer actionability.
"""

    # ✅ Correct Responses API input format
    resp = client.responses.create(
        model=_model_name(),
        input=[
            {
                "role": "user",
                "content": [{"type": "input_text", "text": prompt_text}],
            }
        ],
    )

    # The SDK returns output text in resp.output_text
    text = getattr(resp, "output_text", None)
    if not text:
        # fallback if SDK shape differs
        text = str(resp)

    # Return as “best effort” JSON object.
    # If model returns non-JSON, keep raw text so report still renders.
    import json
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            parsed.setdefault("summary", "")
            parsed.setdefault("findings", [])
            parsed.setdefault("quick_wins", [])
            parsed.setdefault("questions_for_dev", [])
            return parsed
        return {"raw": text}
    except Exception:
        return {"raw": text}
