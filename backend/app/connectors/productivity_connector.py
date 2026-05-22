"""
ProductivityMetricsConnector — reads productivity_metrics.csv.

Production upgrade: replace _fetch_raw() with parallel API calls to
GitHub (PRs/commits), Jira (tickets), Zendesk (support), Salesforce (opps).
"""

from datetime import date
from app.connectors.base import BaseConnector


class ProductivityConnector(BaseConnector):
    source_name = "Productivity Metrics"
    source_type = "csv"
    production_equivalent = "GitHub / Jira / Zendesk / Salesforce APIs"

    REQUIRED_COLS = {"metric_id", "employee_id", "department", "period_start"}

    def _fetch_raw(self):
        return self._read_csv("productivity_metrics.csv")

    def _normalize(self, rows):
        out = []
        for r in rows:
            try:
                ps = r.get("period_start", "")
                pe = r.get("period_end", "")
                out.append({
                    "metric_id":                   r["metric_id"].strip(),
                    "employee_id":                 r["employee_id"].strip(),
                    "department":                  r.get("department", "").strip(),
                    "source_system":               r.get("source_system", "").strip(),
                    "period_start":                date.fromisoformat(ps) if ps else None,
                    "period_end":                  date.fromisoformat(pe) if pe else None,
                    "tickets_closed":              self._safe_int(r.get("tickets_closed", 0)),
                    "prs_merged":                  self._safe_int(r.get("prs_merged", 0)),
                    "commits_count":               self._safe_int(r.get("commits_count", 0)),
                    "support_resolution_hours":    self._safe_float(r.get("support_resolution_hours", 0)),
                    "sales_opportunities_created": self._safe_int(r.get("sales_opportunities_created", 0)),
                    "ai_assisted_work_items":      self._safe_int(r.get("ai_assisted_work_items", 0)),
                    "quality_score":               self._safe_float(r.get("quality_score", 0.0)),
                })
            except Exception:
                continue
        return out
