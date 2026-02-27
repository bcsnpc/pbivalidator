# DataValidator

DataValidator scans a Power BI PBIP project and generates a QA report for:
- Power Query patterns (folding risk, parameterization, hardcoded sources)
- Naming consistency (dominant naming style + outliers)
- Incremental refresh readiness (informational)
- HTML + JSON artifacts for QA and developers

## Who This Is For
- BI developers
- QA engineers reviewing PBIP models
- Teams wanting a repeatable pre-release quality check

## What Users Get
Given a PBIP project folder, DataValidator generates:
- `inventory.json`
- `signals.json`
- `findings.json`
- `report.html`
- `ai_pq.json` (only when `--ai` is used)

## End-User Setup (EXE Distribution)
If you distribute `datavalidator.exe`, users do not need to install Python or dependencies.

### 1. Files to give users
- `datavalidator.exe`
- (optional) `.env` template for AI mode

### 2. Minimal usage
Run in Command Prompt or PowerShell:

```powershell
.\datavalidator.exe -p "D:\path\to\YourProject" -o ".\output"
```

AI-enhanced report:

```powershell
.\datavalidator.exe -p "D:\path\to\YourProject" -o ".\output" --ai
```

### 3. Output location
- HTML report: `output\report.html`
- JSON artifacts: `output\*.json`

## AI Mode
AI mode requires `OPENAI_API_KEY` in environment or `.env`.

Example `.env`:

```env
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-5
```

## Build EXE (for maintainers)
From repo root:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install pyinstaller typer python-dotenv jinja2 openai
.\build_exe.ps1
```

Output executable:
- `dist\datavalidator.exe`

## Developer Run (source mode)

```powershell
.\.venv\Scripts\python.exe -m datavalidator.cli -p "D:\path\to\YourProject" -o ".\output"
```

With AI:

```powershell
.\.venv\Scripts\python.exe -m datavalidator.cli -p "D:\path\to\YourProject" -o ".\output" --ai
```

## Troubleshooting
- `OPENAI_API_KEY not set`: add key in `.env` or environment.
- No Power Query items found: verify PBIP has import/hybrid tables with M in `.SemanticModel\definition\tables\*.tmdl`.
- Slow AI runs: run without `--ai` for deterministic checks only.

## Current Scope
- Deterministic checks for folding risk and query hygiene are heuristic.
- Incremental refresh is treated as optional; tool reports status and fold-readiness guidance.
- Calculated tables and measure-holder tables are excluded from table-based naming/folding findings.
