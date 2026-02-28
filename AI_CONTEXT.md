# AI Context

## Purpose
DataValidator is a PBIP quality scanner for model governance and Power Query review. It extracts PBIP metadata, builds deterministic signals/findings, optionally adds AI explanation, and renders an HTML report.

## Primary Outcomes
- Practical QA findings from PBIP artifacts
- Visibility into source systems and multi-source models
- Actionable recommendations for folding, parameterization, naming, and refresh readiness
- Developer-facing AI summary and questions

## Runtime Flow
1. CLI receives PBIP path and output root path.
2. CLI creates a unique timestamped run folder.
3. Inventory extraction reads PBIP report/model/PQ artifacts.
4. Signals computation normalizes metrics and diagnostics.
5. Findings builder produces deterministic findings.
6. Optional AI layer summarizes and prioritizes findings.
7. Report renderer writes `report.html` + JSON outputs.

## Technical Stack
- Python
- Typer (CLI)
- Jinja2 (report templating)
- python-dotenv (`.env` support)
- OpenAI Responses API (optional AI mode)

## Folder Structure
- `datavalidator/cli.py`
  - entrypoint, env load, unique run folder creation
- `datavalidator/pipeline.py`
  - orchestration of extraction/analyze/report
- `datavalidator/extract/`
  - PBIP parsing and semantic-model/PQ extraction
- `datavalidator/analyze/`
  - signal generation and deterministic findings
- `datavalidator/ai/`
  - AI summary generation
- `datavalidator/report/`
  - HTML rendering and template
- `output/`
  - run artifacts (timestamped subfolders)

## Signal Domains
- `powerQuery`
  - extracted M items, fold-breaker hints, heavy step counts
- `hardcoding`
  - hardcoded/literal source hints + parameterization coverage
- `sources`
  - connector/source inventory by query/table
  - distinct source count and multiple-source flag
- `naming`
  - dominant table naming style + outlier list
- `incremental`
  - presence of RangeStart/RangeEnd references (informational)

## Output Contract
Per run folder:
- `inventory.json`
- `signals.json`
- `findings.json`
- `report.html`
- `ai_pq.json` (if `--ai`)

## User Operation (EXE)
1. Open PowerShell.
2. `cd` into folder where `datavalidator.exe` is present.
3. Run:
   - `.\datavalidator.exe -p "D:\path\to\PBIP" -o ".\output"`
4. Open generated `report.html` from the run folder.

AI mode:
- add `.env` next to exe with `OPENAI_API_KEY`
- run with `--ai`

## Current Design Choices
- Incremental refresh is optional and reported as informational.
- Calculated/measures-only helper tables are excluded from table-based naming and folding findings.
- Source detection is pattern-based and best-effort.

## Future Enhancements
- Add configurable policy profiles (severity thresholds, naming standards).
- Add stronger source-specific folding diagnostics.
- Add DAX quality checks (measure anti-patterns, complexity risk).
- Add machine-readable schema versioning for JSON outputs.
- Add CI release pipeline to build and publish signed exe artifacts.
- Add optional UI shell for non-technical users.
