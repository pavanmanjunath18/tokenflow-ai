"""License waste detection."""

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.license import AILicense


INACTIVE_THRESHOLD_DAYS = 3


def get_license_waste(db: Session) -> dict:
    all_licenses = db.query(AILicense).all()

    inactive = []
    duplicate_keys: dict[tuple, list] = {}
    seen = set()

    for lic in all_licenses:
        # Inactive: paid seat, barely used
        if lic.monthly_seat_cost > 0 and lic.active_days_last_30 <= INACTIVE_THRESHOLD_DAYS:
            inactive.append(lic)

        # Duplicate: same employee + same tool more than once
        key = (lic.employee_id, lic.tool_name)
        duplicate_keys.setdefault(key, []).append(lic)

    duplicates = [
        lic
        for group in duplicate_keys.values()
        if len(group) > 1
        for lic in group[1:]  # keep first, flag extras
    ]

    all_waste = {l.license_id: l for l in inactive + duplicates}
    waste_list = []
    for lic in all_waste.values():
        reason = []
        if lic.active_days_last_30 <= INACTIVE_THRESHOLD_DAYS and lic.monthly_seat_cost > 0:
            reason.append(f"Only {lic.active_days_last_30} active days in last 30")
        key = (lic.employee_id, lic.tool_name)
        if len(duplicate_keys.get(key, [])) > 1:
            reason.append("Duplicate seat for same tool")

        waste_list.append({
            "license_id":          lic.license_id,
            "employee_id":         lic.employee_id,
            "department":          lic.department,
            "tool_name":           lic.tool_name,
            "plan_type":           lic.plan_type,
            "monthly_seat_cost":   lic.monthly_seat_cost,
            "active_days_last_30": lic.active_days_last_30,
            "license_status":      lic.license_status,
            "waste_reason":        "; ".join(reason),
            "last_active_date":    lic.last_active_date,
        })

    total_monthly_waste = sum(w["monthly_seat_cost"] for w in waste_list)

    return {
        "inactive_licenses": len(inactive),
        "duplicate_licenses": len(duplicates),
        "total_monthly_waste": round(total_monthly_waste, 2),
        "licenses": waste_list,
    }
