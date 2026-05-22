"""
ModelPricingConnector — reads model_pricing.csv.

Production upgrade: call provider pricing APIs directly, or maintain
an internal pricing DB synced nightly via a scheduled job.
"""

from datetime import date

from app.connectors.base import BaseConnector


class ModelPricingConnector(BaseConnector):
    source_name = "Model Pricing Catalog"
    source_type = "csv"
    production_equivalent = "Provider pricing APIs + internal pricing DB"

    REQUIRED_COLS = {"provider", "model_name", "input_cost_per_1m_tokens", "output_cost_per_1m_tokens"}

    def _fetch_raw(self):
        return self._read_csv("model_pricing.csv")

    def _normalize(self, rows):
        out = []
        for r in rows:
            try:
                ed = r.get("effective_date", "")
                out.append({
                    "provider":                       r["provider"].strip(),
                    "model_name":                     r["model_name"].strip(),
                    "tier":                           r.get("tier", "standard").strip(),
                    "input_cost_per_1m_tokens":       self._safe_float(r["input_cost_per_1m_tokens"]),
                    "output_cost_per_1m_tokens":      self._safe_float(r["output_cost_per_1m_tokens"]),
                    "cached_input_cost_per_1m_tokens": self._safe_float(r.get("cached_input_cost_per_1m_tokens", 0)),
                    "effective_date":                 date.fromisoformat(ed) if ed else None,
                })
            except Exception:
                continue
        return out
