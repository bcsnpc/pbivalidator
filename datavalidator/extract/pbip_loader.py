from dataclasses import dataclass
from pathlib import Path

@dataclass
class PbipContext:
    project_root: Path          # folder that contains .Report and .SemanticModel
    pbip_file: Path | None      # the .pbip file (manifest)
    report_dir: Path | None
    model_dir: Path | None
    project_name: str

def load_pbip(project_path: Path) -> PbipContext:
    """
    Accepts either:
      - the PBIP project folder (recommended), e.g. D:\vc_test
      - the .pbip file path, e.g. D:\vc_test\vc_test.pbip
    Returns a context whose project_root is ALWAYS a directory.
    """
    p = project_path

    # If user passed the .pbip file, project_root is its parent folder
    if p.is_file() and p.suffix.lower() == ".pbip":
        project_root = p.parent
        pbip_file = p
        project_name = p.stem

    # If user passed a folder, find the .pbip file inside it (optional)
    elif p.is_dir():
        project_root = p
        pbip_candidates = list(project_root.glob("*.pbip"))
        pbip_file = pbip_candidates[0] if pbip_candidates else None
        project_name = pbip_file.stem if pbip_file else project_root.name

    else:
        raise FileNotFoundError(f"PBIP path not found: {p}")

    report_dir = None
    model_dir = None

    # Look for artifact folders in the project root
    for child in project_root.iterdir():
        if child.is_dir() and child.name.endswith(".Report"):
            report_dir = child
        if child.is_dir() and child.name.endswith(".SemanticModel"):
            model_dir = child

    return PbipContext(
        project_root=project_root,
        pbip_file=pbip_file,
        report_dir=report_dir,
        model_dir=model_dir,
        project_name=project_name,
    )