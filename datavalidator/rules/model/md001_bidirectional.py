from datavalidator.rules.base import Rule
from datavalidator.core.findings import Finding


class MD001(Rule):

    rule_id = "MD001"
    title = "Bidirectional relationship detected"

    def run(self, ctx, model=None, **kwargs):

        findings = []

        if not model:
            return findings

        for r in model.relationships:

            if r.cross_filter.lower() == "both":

                findings.append(Finding(
                    rule_id=self.rule_id,
                    category="Model",
                    severity="HIGH",
                    title=self.title,
                    message=f"{r.from_table} ↔ {r.to_table} uses bidirectional filtering.",
                    recommendation="Prefer single-direction relationships unless explicitly required."
                ))

        return findings