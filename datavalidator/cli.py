from __future__ import annotations

from datetime import datetime
from pathlib import Path
import typer
from dotenv import load_dotenv

from datavalidator.pipeline import run_pipeline

app = typer.Typer(add_completion=False)

@app.command()
def run(
    project: Path = typer.Option(..., "--project", "-p", exists=True, help="PBIP project root folder"),
    out: Path = typer.Option(Path("output"), "--out", "-o", help="Output directory"),
    ai: bool = typer.Option(False, "--ai", help="Run AI review (Power Query first)"),
):
    """
    Run QA scan on a PBIP project and generate:
      - output/inventory.json
      - output/signals.json
      - output/findings.json
      - (optional) output/ai_pq.json
      - output/report.html
    """
    # IMPORTANT: load .env into environment for THIS process
    load_dotenv(override=False)

    out.mkdir(parents=True, exist_ok=True)

    project_name = project.stem if project.is_file() else project.name
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = out / f"{project_name}_{ts}"
    run_dir.mkdir(parents=True, exist_ok=True)

    run_pipeline(project_path=project, out_dir=run_dir, run_ai=ai)
    typer.echo(f"Report generated: {run_dir / 'report.html'}")

def main():
    app()

if __name__ == "__main__":
    main()
