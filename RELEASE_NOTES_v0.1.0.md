# DataValidator v0.1.0

Initial public release of DataValidator as a Windows CLI tool (`datavalidator.exe`) for PBIP quality auditing, including UX and reporting enhancements.

## Highlights

- Scans PBIP projects and generates:
  - `inventory.json`
  - `signals.json`
  - `findings.json`
  - `report.html`
  - `ai_pq.json` (when `--ai` is used)
- Ships as a single executable for easy user adoption.
- Optional AI mode with OpenAI for summary, prioritized findings, quick wins, and developer questions.
- Improved HTML report UI for easier triage and readability.
- Every run now creates a timestamped subfolder under output (no overwrite of prior runs).

## Deterministic Checks Included

- Power Query folding-risk heuristics:
  - common folding breaker patterns
  - heavy transformation chain detection
  - late-filtering hints
- Source quality checks:
  - hardcoded source/literal hints
  - parameterization coverage by query
- Source inventory:
  - connector/source types detected in model queries
  - per-table source mapping
  - multiple-source model detection
- Naming consistency:
  - dominant table naming convention detection
  - outlier table identification
- Incremental refresh status:
  - reported as informational (optional capability)
  - guidance provided for fold-readiness before enabling

## Modeling Nuance Handling

- Calculated tables and measures-only/helper tables are excluded from table-based naming/folding findings.

## Usage

From PowerShell:
1. `cd` to the folder containing `datavalidator.exe`
2. run the command below

```powershell
.\datavalidator.exe -p "D:\path\to\PBIP" -o ".\output"
```

With AI:

```powershell
.\datavalidator.exe -p "D:\path\to\PBIP" -o ".\output" --ai
```

AI mode requires:

```env
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-5
```

Output path behavior:
- `-o .\output` now creates run folders like:
  - `.\output\<project>_YYYYMMDD_HHMMSS\`

## Documentation Included

- `README.md` for user and maintainer instructions
- `AI_CONTEXT.md` for architecture, technical context, folder structure, and future enhancements
- `build_exe.ps1` to build `dist\datavalidator.exe`

## Notes / Known Constraints

- Folding detection is heuristic (not full engine-level fold verification).
- Hardcoding/parameterization checks are pattern-based best effort.
- AI mode currently supports OpenAI only.
