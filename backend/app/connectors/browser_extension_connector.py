"""
BrowserExtensionConnector — reads browser_extension_events.csv.

Production upgrade: replace _fetch_raw() with a webhook receiver or
Chrome extension background-script telemetry stream (e.g. HTTPS POST
to /api/telemetry/browser with a JWT per install).
"""

from datetime import datetime, timezone
from app.connectors.base import BaseConnector


class BrowserExtensionConnector(BaseConnector):
    source_name = "Browser Extension Telemetry"
    source_type = "csv"
    production_equivalent = "Chrome extension → real-time HTTPS telemetry stream"

    REQUIRED_COLS = {"event_id", "timestamp", "employee_id", "domain", "shadow_ai_flag", "risk_score"}

    def _fetch_raw(self):
        return self._read_csv("browser_extension_events.csv")

    def _normalize(self, rows):
        out = []
        for r in rows:
            try:
                ts_raw = r.get("timestamp", "")
                ts = datetime.fromisoformat(ts_raw) if ts_raw else datetime.now(timezone.utc)
                out.append({
                    "event_id":              r["event_id"].strip(),
                    "timestamp":             ts,
                    "employee_id":           r["employee_id"].strip(),
                    "department":            r.get("department", "").strip(),
                    "session_id":            r.get("session_id", "").strip(),
                    "browser":               r.get("browser", "").strip(),
                    "domain":                r.get("domain", "").strip(),
                    "task_type":             r.get("task_type", "").strip(),
                    "prompt_length_chars":   self._safe_int(r.get("prompt_length_chars", 0)),
                    "estimated_input_tokens": self._safe_int(r.get("estimated_input_tokens", 0)),
                    "estimated_output_tokens": self._safe_int(r.get("estimated_output_tokens", 0)),
                    "contains_pii":          self._safe_bool(r.get("contains_pii", False)),
                    "pii_types_detected":    r.get("pii_types_detected", "").strip(),
                    "policy_action":         r.get("policy_action", "allow").strip(),
                    "shadow_ai_flag":        self._safe_bool(r.get("shadow_ai_flag", False)),
                    "approved_tool":         self._safe_bool(r.get("approved_tool", True)),
                    "copy_paste_detected":   self._safe_bool(r.get("copy_paste_detected", False)),
                    "file_upload_detected":  self._safe_bool(r.get("file_upload_detected", False)),
                    "risk_score":            self._safe_float(r.get("risk_score", 0.0)),
                })
            except Exception:
                continue
        return out
