import re
from datavalidator.rules.base import Rule
from datavalidator.core.findings import Finding

HARD_SOURCE_PATTERNS = [
    r"Sql\.Database\(\s*\".+?\"\s*,\s*\".+?\"\s*\)",
    r"File\.Contents\(\s*\"[A-Za-z]:\\.+?\"\s*\)",
    r"Web\.Contents\(\s*\"https?://.+?\"\s*\)",
    r"Odbc\.DataSource\(\s*\".+?\"\s*\)",
]

class PQ001(Rule):
    rule_id = "PQ001"
    title = "Hardcoded data source detected"

    def run(self, ctx, pq=None, **kwargs):
        findings = []
        if not pq:
            return findings

        for q in pq.queries:
            for pat in HARD_SOURCE_PATTERNS:
                m = re.search(pat, q.m, flags=re.IGNORECASE | re.DOTALL)
                if m:
                    findings.append(Finding(
                        rule_id=self.rule_id,
                        category="PowerQuery",
                        severity="HIGH",
                        title=self.title,
                        message=f"Query '{q.name}' appears to use a hardcoded source.",
                        evidence={"query": q.name, "match": m.group(0)[:200]},
                        recommendation="Parameterize server/database/file/url and reference parameters in the Source step."
                    ))
                    break
        return findings