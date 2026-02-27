from datavalidator.rules.base import Rule
from datavalidator.core.findings import Finding

class RP002(Rule):
    rule_id = "RP002"
    title = "Visual overload per page"

    def run(self, ctx, report=None, **kwargs):
        findings = []
        if not report or not getattr(report, "pages", None):
            return findings

        for p in report.pages:
            # use display_name (fallback to page_id)
            page_name = getattr(p, "display_name", None) or getattr(p, "page_id", "Unknown Page")

            if p.visual_count >= 20:
                sev = "HIGH"
            elif p.visual_count >= 14:
                sev = "MED"
            else:
                continue

            findings.append(Finding(
                rule_id=self.rule_id,
                category="Report",
                severity=sev,
                title=self.title,
                message=f"Page '{page_name}' contains {p.visual_count} visuals.",
                evidence={"page": page_name, "visual_count": p.visual_count},
                recommendation="Split into drill-through/tooltip pages or reduce visuals for performance/readability."
            ))

        return findings