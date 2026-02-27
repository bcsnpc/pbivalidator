import re
from datavalidator.rules.base import Rule
from datavalidator.core.findings import Finding

BAD_EXACT = {"Query1", "Query2", "New Query", "NewQuery"}
BAD_CONTAINS = ["Copy of", "Final", "Temp", "Test"]

class NC003(Rule):
    rule_id = "NC003"
    title = "Power Query query naming has bad defaults"

    def run(self, ctx, pq=None, **kwargs):
        findings = []
        if not pq:
            return findings

        for q in pq.queries:
            if q.name in BAD_EXACT or re.match(r"Query\d+$", q.name, flags=re.IGNORECASE):
                bad = True
            else:
                bad = any(s.lower() in q.name.lower() for s in BAD_CONTAINS)

            if bad:
                findings.append(Finding(
                    rule_id=self.rule_id,
                    category="Naming",
                    severity="LOW",
                    title=self.title,
                    message=f"Query name '{q.name}' is non-descriptive or default-like.",
                    evidence={"query": q.name},
                    recommendation="Rename queries to meaningful names aligned with purpose (e.g., dim_Date, fact_Claim)."
                ))
        return findings