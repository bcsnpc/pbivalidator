from abc import ABC, abstractmethod
from datavalidator.core.findings import Finding
from datavalidator.extract.pbip_loader import PbipContext

class Rule(ABC):
    rule_id: str
    title: str

    @abstractmethod
    def run(self, ctx: PbipContext, **kwargs) -> list[Finding]:
        ...