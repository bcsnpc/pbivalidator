# DataValidator

DataValidator audits a Power BI PBIP project and produces a clear QA report with deterministic findings and optional AI summary.

## What It Checks
- Query folding risk indicators in Power Query (heuristics)
- Source parameterization vs hardcoded/literal source values
- Source inventory (which source systems/connectors are used)
- Multiple-source usage in the same model
- Naming convention consistency (dominant style + outliers)
- Incremental refresh status (informational, optional)

## Output Files
Each run creates:
- `inventory.json`
- `signals.json`
- `findings.json`
- `report.html`
- `ai_pq.json` (only with `--ai`)

## Important Run Behavior
Every run creates a **new timestamped output folder** under `-o`.

Example:
- Command uses `-o .\output`
- Actual run folder becomes: `.\output\<project>_YYYYMMDD_HHMMSS\`

This prevents old runs from being overwritten.

## End-User Instructions (EXE)
Users only need `datavalidator.exe`.

### Step 1: Place exe in a folder
Example:
- `D:\Tools\DataValidator\datavalidator.exe`

### Step 2: Open PowerShell and go to exe folder
```powershell
cd D:\Tools\DataValidator
```

### Step 3: Run scan
```powershell
.\datavalidator.exe -p "D:\path\to\YourPBIP" -o ".\output"
```

### Step 4: Open report
Go to generated run folder and open `report.html`.

## AI Mode (Optional)
AI mode requires `OPENAI_API_KEY`.

### Step 1: create `.env` next to exe
```env
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-5
```

### Step 2: run with `--ai`
```powershell
.\datavalidator.exe -p "D:\path\to\YourPBIP" -o ".\output" --ai
```

## Build EXE (Maintainers)
From repo root:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install pyinstaller typer python-dotenv jinja2 openai
.\build_exe.ps1
```

Build output:
- `dist\datavalidator.exe`

## Developer Run (Source)
```powershell
.\.venv\Scripts\python.exe -m datavalidator.cli -p "D:\path\to\YourPBIP" -o ".\output"
```

With AI:

```powershell
.\.venv\Scripts\python.exe -m datavalidator.cli -p "D:\path\to\YourPBIP" -o ".\output" --ai
```

## Troubleshooting
- Error `Missing option '--project'`: you must pass `-p` with PBIP path.
- Error `Path ... does not exist`: check project path spelling.
- Error `OPENAI_API_KEY not set`: add `.env` or environment variable.
- If run by double-clicking exe: it launches without args and fails. Run from terminal.

## Current Scope Notes
- Folding checks are heuristic, not full engine-level fold validation.
- Hardcoding/parameterization checks are best-effort pattern checks.
- Calculated and measures-only/helper tables are excluded from table-based naming/folding findings.
