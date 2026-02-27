$ErrorActionPreference = "Stop"

Write-Host "Building DataValidator EXE..."

if (-not (Test-Path ".\\.venv\\Scripts\\python.exe")) {
  throw "Virtual environment not found at .\\.venv. Create it first."
}

.\.venv\Scripts\python.exe -m PyInstaller `
  --noconfirm `
  --clean `
  --onefile `
  --name datavalidator `
  --collect-all jinja2 `
  --collect-all typer `
  --collect-all dotenv `
  --add-data "datavalidator\\report\\templates;datavalidator\\report\\templates" `
  datavalidator\cli.py

Write-Host "Build complete: dist\\datavalidator.exe"
