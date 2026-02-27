# AI Context

## Purpose
DataValidator is a PBIP quality scanner focused on Power Query and semantic-model governance. It reads PBIP artifacts, computes deterministic signals/findings, optionally enriches findings with AI, and generates JSON + HTML outputs for QA and engineering teams.

## Core Capabilities
- PBIP inventory extraction
- Power Query heuristic analysis
  - Folding risk indicators
  - Hardcoded source hints
  - Parameterization coverage
  - Transformation complexity hints
- Naming consistency analysis
  - Dominant table naming convention inference
  - Outlier detection
- Incremental refresh readiness status
  - Informational only (optional feature)
  - Guidance if folding blockers exist
- AI summary layer
  - Consolidated summary
  - AI findings + quick wins
  - Questions for developers

## Runtime Flow
1. CLI receives PBIP path and output directory.
2. Inventory is built from PBIP files.
3. Signals are derived from inventory.
4. Findings are generated from signals.
5. Optional AI review uses signals + findings.
6. HTML report and JSON artifacts are written to output.

## Technical Stack
- Language: Python
- CLI: Typer
- Templating: Jinja2
- Env config: python-dotenv
- AI: OpenAI Responses API

## Key Folders
- `datavalidator/cli.py`
  - user entrypoint
- `datavalidator/pipeline.py`
  - orchestration
- `datavalidator/extract/`
  - PBIP/report/model/PQ extraction
- `datavalidator/analyze/`
  - signals + findings logic
- `datavalidator/ai/`
  - AI summarization
- `datavalidator/report/`
  - report rendering and templates
- `output/`
  - generated artifacts

## Output Contract
- `inventory.json`
  - extracted project details
- `signals.json`
  - normalized analytic signals
- `findings.json`
  - deterministic findings
- `ai_pq.json`
  - AI layer output (when enabled)
- `report.html`
  - human-readable consolidated report

## Detection Model Notes
- Folding detection is heuristic, not a true engine-level fold verifier.
- Hardcoding detection is pattern-based and best-effort.
- Table naming convention is inferred statistically from current model names.
- Calculated and measures-only tables are excluded from table-based naming/folding findings.

## How Users Operate the Tool
For EXE users:

```powershell
.\datavalidator.exe -p "D:\path\to\PBIP" -o ".\output"
```

With AI:

```powershell
.\datavalidator.exe -p "D:\path\to\PBIP" -o ".\output" --ai
```

Then open:
- `output\report.html`

## Future Enhancement Opportunities
- True folding validation using source-aware diagnostics.
- Configurable rule packs and thresholds via YAML.
- Dedicated naming policy profiles (snake_case, PascalCase, dim_/fact_ standards).
- DAX measure quality checks and anti-pattern detection.
- Relationship-level model design checks (cardinality/filter direction quality rules).
- Test harness with sample PBIP fixtures and golden outputs.
- CI/CD package pipeline for signed EXE releases.
- Optional GUI wrapper for non-technical users.

## Productization Notes
- Recommended distribution for business users: Windows `datavalidator.exe`.
- Keep release artifacts versioned and publish a changelog.
- Preserve backward compatibility of JSON keys where possible.
