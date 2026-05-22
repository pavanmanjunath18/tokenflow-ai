"""
LicenseInventoryConnector — reads ai_license_inventory.csv.

Production upgrade: replace _fetch_raw() with ChatGPT Enterprise admin API,
GitHub Copilot billing API, or Claude Team admin export.
"""

from datetime import date

from app.connectors.base import BaseConnector


class LicenseInventoryConnector(BaseConnector):
    source_name = "AI License Inventory"
    source_type = "csv"
    production_equivalent = "ChatGPT Enterprise / GitHub Copilot / Claude Team admin APIs"

    REQUIRED_COLS = {"license_id", "employee_id", "tool_name", "monthly_seat_cost", "license_status"}

    def _fetch_raw(self):
        return self._read_csv("ai_license_inventory.csv")

    def _normalize(self, rows):
        out = []
        for r in rows:
            try:
                ad = r.get("assigned_date", "")
                la = r.get("last_active_date", "")
                out.append({
                    "license_id":          r["license_id"].strip(),
                    "employee_id":         r["employee_id"].strip(),
                    "tool_name":           r["tool_name"].strip(),
                    "plan_type":           r.get("plan_type", "").strip(),
                    "monthly_seat_cost":   self._safe_float(r["monthly_seat_cost"]),
                    "assigned_date":       date.fromisoformat(ad) if ad else None,
                    "last_active_date":    date.fromisoformat(la) if la else None,
                    "active_days_last_30": self._safe_int(r.get("active_days_last_30", 0)),
                    "license_status":      r.get("license_status", "active").strip(),
                    "department":          r.get("department", "").strip(),
                })
            except Exception:
                continue
        return out
