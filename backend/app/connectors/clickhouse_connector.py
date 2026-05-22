"""
ClickHouseConnector — reads clickhouse_ai_traces.csv (pre-aggregated by day).

Production upgrade: replace _fetch_raw() with a ClickHouse HTTP query:
  SELECT * FROM ai_request_traces WHERE date >= today() - 7
using clickhouse-driver or clickhouse-connect.
"""

from datetime import datetime
from app.connectors.base import BaseConnector


class ClickHouseConnector(BaseConnector):
    source_name = "ClickHouse Analytics Store"
    source_type = "csv"
    production_equivalent = "ClickHouse ai_request_traces table (clickhouse-connect)"

    REQUIRED_COLS = {"agg_id", "date", "employee_id", "model_name", "cost_usd"}

    def _fetch_raw(self):
        return self._read_csv("clickhouse_ai_traces.csv")

    def _normalize(self, rows):
        out = []
        for r in rows:
            try:
                day = r.get("date", "")
                ts  = datetime.fromisoformat(day + "T12:00:00") if day else datetime.utcnow()
                input_t  = self._safe_int(r.get("input_tokens", 0))
                output_t = self._safe_int(r.get("output_tokens", 0))
                out.append({
                    "trace_id":    r["agg_id"],
                    "timestamp":   ts,
                    "source_type": "clickhouse",
                    "employee_id": r.get("employee_id", ""),
                    "department":  r.get("department", ""),
                    "team":        "",
                    "provider":    r.get("provider", ""),
                    "model_name":  r.get("model_name", ""),
                    "task_type":   "",
                    "input_tokens":  input_t,
                    "output_tokens": output_t,
                    "total_tokens":  self._safe_int(r.get("total_tokens", input_t + output_t)),
                    "cost_usd":      self._safe_float(r.get("cost_usd", 0.0)),
                    "latency_ms":    self._safe_int(r.get("avg_latency_ms", 0)),
                    "status_code":   200,
                    "cache_hit":     self._safe_bool(r.get("cache_hit_count", 0)),
                    "request_allowed": True,
                    "expensive_model_simple_task": False,
                    "internal_app": "",
                })
            except Exception:
                continue
        return out
