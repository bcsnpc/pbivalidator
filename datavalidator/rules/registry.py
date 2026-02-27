from datavalidator.rules.powerquery.pq001_hardcoded_source import PQ001
from datavalidator.rules.report.rp002_visual_overload import RP002
from datavalidator.rules.naming.nc003_bad_query_names import NC003
from datavalidator.rules.model.md001_bidirectional import MD001


class RuleRegistry:

    def __init__(self, rules):
        self.rules = rules

    @staticmethod
    def default():

        rules = [
            PQ001(),
            RP002(),
            NC003(),
            MD001(),   # ✅ new semantic model rule
        ]

        return RuleRegistry(rules)

    def run_all(self, ctx, **kwargs):

        findings = []

        for r in self.rules:
            findings.extend(r.run(ctx, **kwargs))

        return findings