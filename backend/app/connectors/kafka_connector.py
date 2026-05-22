"""
KafkaTelemetryConnector — reads kafka_ai_telemetry.jsonl.

Production upgrade: replace _fetch_raw() with a Kafka consumer on
topic ai.telemetry.events using confluent-kafka-python.
"""

from datetime import datetime, timezone
from app.connectors.base import BaseConnector


class KafkaTelemetryConnector(BaseConnector):
    source_name = "Kafka AI Telemetry Stream"
    source_type = "jsonl"
    production_equivalent = "Kafka topic ai.telemetry.events (confluent-kafka-python)"

    REQUIRED_COLS = {"event_type", "trace_id", "timestamp", "employee_id", "model"}

    def _fetch_raw(self):
        return self._read_jsonl("kafka_ai_telemetry.jsonl")

    def _normalize(self, rows):
        out = []
        for r in rows:
            try:
                ts_raw = r.get("timestamp", "")
                ts = datetime.fromisoformat(ts_raw) if ts_raw else datetime.now(timezone.utc)
                out.append({
                    "trace_id":    r["trace_id"],
                    "timestamp":   ts,
                    "source_type": "kafka",
                    "employee_id": r.get("employee_id", ""),
                    "department":  r.get("department", ""),
                    "team":        r.get("team_id", ""),
                    "provider":    r.get("provider", ""),
                    "model_name":  r.get("model", ""),
                    "input_tokens":  self._safe_int(r.get("input_tokens", 0)),
                    "output_tokens": self._safe_int(r.get("output_tokens", 0)),
                    "total_tokens":  self._safe_int(r.get("input_tokens", 0)) + self._safe_int(r.get("output_tokens", 0)),
                    "cost_usd":      self._safe_float(r.get("cost_usd", 0.0)),
                    "latency_ms":    self._safe_int(r.get("latency_ms", 0)),
                    "cache_hit":     self._safe_bool(r.get("cache_hit", False)),
                    "status_code":   200,
                    "request_allowed": r.get("policy_result", "allowed") == "allowed",
                    "expensive_model_simple_task": False,
                    "internal_app": "",
                    "task_type": "",
                })
            except Exception:
                continue
        return out
