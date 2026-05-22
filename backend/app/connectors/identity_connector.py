"""
IdentityConnector — reads identity_directory.csv.

Production upgrade: replace _fetch_raw() with Okta /api/v1/users,
Azure AD /users, or Google Workspace Admin SDK Directory API.
"""

from datetime import date

from app.connectors.base import BaseConnector


class IdentityConnector(BaseConnector):
    source_name = "SSO Identity Directory"
    source_type = "csv"
    production_equivalent = "Okta / Azure AD / Google Workspace SCIM"

    REQUIRED_COLS = {"employee_id", "employee_name", "email", "department", "status"}

    def _fetch_raw(self):
        return self._read_csv("identity_directory.csv")

    def _normalize(self, rows):
        out = []
        for r in rows:
            try:
                sd = r.get("start_date", "")
                out.append({
                    "employee_id":    r["employee_id"].strip(),
                    "employee_name":  r["employee_name"].strip(),
                    "email":          r["email"].strip().lower(),
                    "department":     r["department"].strip(),
                    "team":           r.get("team", "").strip(),
                    "role":           r.get("role", "").strip(),
                    "manager_id":     r.get("manager_id", "").strip(),
                    "cost_center":    r.get("cost_center", "").strip(),
                    "location":       r.get("location", "").strip(),
                    "employment_type": r.get("employment_type", "Full-time").strip(),
                    "start_date":     date.fromisoformat(sd) if sd else None,
                    "sso_provider":   r.get("sso_provider", "").strip(),
                    "status":         r.get("status", "active").strip(),
                })
            except Exception:
                continue
        return out
