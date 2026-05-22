"""
APIGatewayConnector — reads api_gateway_traces.csv.

Production upgrade: replace _fetch_raw() with a ClickHouse query against
ai_request_traces, a Kafka consumer on ai.telemetry.events, or a direct
PostgreSQL read from a real gateway database.
"""

from datetime import datetime, timezone

from app.connectors.base import BaseConnector


class APIGatewayConnector(BaseConnector):
    source_name = "AI Gateway Traces"
    source_type = "csv"
    production_equivalent = "Envoy/Kong gateway → ClickHouse ai_request_traces"

    REQUIRED_COLS = {
        "trace_id", "timestamp", "employee_id", "department",
        "model_name", "input_tokens", "output_tokens", "cost_usd",
    }

    def _fetch_raw(self):
        return self._read_csv("api_gateway_traces.csv")

    def _normalize(self, rows):
        out = []
        for r in rows:
            try:
                ts_raw = r.get("timestamp", "")
                ts = datetime.fromisoformat(ts_raw) if ts_raw else datetime.now(timezone.utc)
                out.append({
                    "trace_id":                    r["trace_id"].strip(),
                    "timestamp":                   ts,
                    "source_type":                 "api_gateway",
                    "employee_id":                 r["employee_id"].strip(),
                    "department":                  r["department"].strip(),
                    "team":                        r.get("team", "").strip(),
                    "internal_app":                r.get("internal_app", "").strip(),
                    "provider":                    r.get("provider", "").strip(),
                    "model_name":                  r.get("model_name", "").strip(),
                    "task_type":                   r.get("task_type", "").strip(),
                    "input_tokens":                self._safe_int(r.get("input_tokens", 0)),
                    "output_tokens":               self._safe_int(r.get("output_tokens", 0)),
                    "total_tokens":                self._safe_int(r.get("total_tokens", 0)),
                    "cost_usd":                    self._safe_float(r.get("cost_usd", 0)),
                    "latency_ms":                  self._safe_int(r.get("latency_ms", 0)),
                    "status_code":                 self._safe_int(r.get("status_code", 200)),
                    "cache_hit":                   self._safe_bool(r.get("cache_hit", False)),
                    "request_allowed":             self._safe_bool(r.get("request_allowed", True)),
                    "expensive_model_simple_task": self._safe_bool(r.get("expensive_model_simple_task", False)),
                })
            except Exception:
                continue
        return out
