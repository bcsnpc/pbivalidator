from dataclasses import dataclass
from typing import Literal, Dict, Any

Severity = Literal["BLOCKER", "HIGH", "MED", "LOW", "INFO"]
Category = Literal["PowerQuery", "Model", "Report", "Naming", "DataValidation"]

@dataclass
class Finding:
    rule_id: str
    category: Category
    severity: Severity
    title: str
    message: str
    evidence: Dict[str, Any]
    recommendation: str