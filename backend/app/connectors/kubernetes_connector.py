"""
KubernetesLogsConnector — reads kubernetes_gateway_logs.csv.

Production upgrade: replace _fetch_raw() with a Prometheus HTTP query
or kubectl logs pipe. Example Prometheus query:
  sum(rate(http_requests_total{namespace="ai-platform"}[5m])) by (pod)
"""

from datetime import datetime, timezone
from app.connectors.base import BaseConnector


class KubernetesLogsConnector(BaseConnector):
    source_name = "Kubernetes Gateway Logs"
    source_type = "csv"
    production_equivalent = "Prometheus metrics scrape / kubectl logs (ai-platform namespace)"

    REQUIRED_COLS = {"log_id", "timestamp", "pod_name", "request_count", "error_count", "status"}

    def _fetch_raw(self):
        return self._read_csv("kubernetes_gateway_logs.csv")

    def _normalize(self, rows):
        out = []
        for r in rows:
            try:
                ts_raw = r.get("timestamp", "")
                ts = datetime.fromisoformat(ts_raw) if ts_raw else datetime.now(timezone.utc)
                out.append({
                    "log_id":            r["log_id"].strip(),
                    "timestamp":         ts,
                    "cluster":           r.get("cluster", "").strip(),
                    "namespace":         r.get("namespace", "").strip(),
                    "pod_name":          r.get("pod_name", "").strip(),
                    "gateway_version":   r.get("gateway_version", "").strip(),
                    "request_count":     self._safe_int(r.get("request_count", 0)),
                    "error_count":       self._safe_int(r.get("error_count", 0)),
                    "error_rate":        self._safe_float(r.get("error_rate", 0.0)),
                    "avg_latency_ms":    self._safe_int(r.get("avg_latency_ms", 0)),
                    "p95_latency_ms":    self._safe_int(r.get("p95_latency_ms", 0)),
                    "cpu_usage_percent": self._safe_float(r.get("cpu_usage_percent", 0.0)),
                    "memory_usage_mb":   self._safe_int(r.get("memory_usage_mb", 0)),
                    "restart_count":     self._safe_int(r.get("restart_count", 0)),
                    "status":            r.get("status", "healthy").strip(),
                })
            except Exception:
                continue
        return out
