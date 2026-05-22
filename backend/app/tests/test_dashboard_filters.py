"""
Dashboard analytics filter tests.

Verifies:
- Unfiltered queries return all data
- Department filter scopes results to that department
- Provider filter scopes results to that provider
- Date range filter narrows to the specified window
- Combined filters are AND-ed together
- get_available_departments / get_available_providers return distinct values
"""

import pytest
from datetime import datetime, date, timezone

from app.services.analytics_service import (
    get_overview, get_department_stats, get_model_stats, get_spend_over_time,
    get_available_departments, get_available_providers, AnalyticsFilters,
)
from app.services.ingestion_service import _upsert_batch
from app.models.usage_event import AIUsageEvent


def _event(trace_id, dept, provider, model, cost, ts):
    return {
        "trace_id": trace_id,
        "timestamp": ts,
        "source_type": "api_gateway",
        "employee_id": "E001",
        "department": dept,
        "team": "Platform",
        "internal_app": "test",
        "provider": provider,
        "model_name": model,
        "task_type": "test",
        "input_tokens": 100,
        "output_tokens": 100,
        "total_tokens": 200,
        "cost_usd": cost,
        "latency_ms": 200,
        "status_code": 200,
        "cache_hit": False,
        "request_allowed": True,
        "expensive_model_simple_task": False,
    }


@pytest.fixture
def seeded_db(db):
    """Seed 6 events: 2 depts × 2 providers, spread across 2 months."""
    t_jan = datetime(2025, 1, 10, 12, 0, tzinfo=timezone.utc)
    t_feb = datetime(2025, 2, 10, 12, 0, tzinfo=timezone.utc)
    rows = [
        _event("FILTER_T001", "Engineering", "anthropic", "claude-3-5-sonnet", 2.0, t_jan),
        _event("FILTER_T002", "Engineering", "openai",    "gpt-4o",            3.0, t_jan),
        _event("FILTER_T003", "Marketing",   "anthropic", "claude-3-5-sonnet", 1.5, t_jan),
        _event("FILTER_T004", "Marketing",   "openai",    "gpt-4o",            2.5, t_feb),
        _event("FILTER_T005", "Engineering", "anthropic", "claude-3-5-sonnet", 4.0, t_feb),
        _event("FILTER_T006", "Marketing",   "anthropic", "claude-haiku-3",    0.5, t_feb),
    ]
    _upsert_batch(db, AIUsageEvent, rows, "trace_id")
    return db


class TestDepartmentFilter:
    def test_no_filter_returns_all_events(self, seeded_db):
        stats = get_department_stats(seeded_db, AnalyticsFilters())
        depts = {s["department"] for s in stats}
        assert "Engineering" in depts
        assert "Marketing" in depts

    def test_dept_filter_scopes_to_one_dept(self, seeded_db):
        stats = get_department_stats(seeded_db, AnalyticsFilters(department="Engineering"))
        assert all(s["department"] == "Engineering" for s in stats)

    def test_dept_filter_on_overview(self, seeded_db):
        all_data = get_overview(seeded_db, AnalyticsFilters())
        eng_data  = get_overview(seeded_db, AnalyticsFilters(department="Engineering"))
        assert eng_data["total_requests"] < all_data["total_requests"]
        assert eng_data["total_spend"] < all_data["total_spend"]


class TestProviderFilter:
    def test_provider_filter_scopes_model_stats(self, seeded_db):
        stats = get_model_stats(seeded_db, AnalyticsFilters(provider="openai"))
        assert all(s["provider"] == "openai" for s in stats)

    def test_anthropic_filter_excludes_openai(self, seeded_db):
        stats = get_model_stats(seeded_db, AnalyticsFilters(provider="anthropic"))
        providers = {s["provider"] for s in stats}
        assert "openai" not in providers


class TestDateRangeFilter:
    def test_start_date_filters_out_older_events(self, seeded_db):
        # Only Feb events
        all_data = get_overview(seeded_db, AnalyticsFilters())
        feb_data  = get_overview(seeded_db, AnalyticsFilters(start_date=date(2025, 2, 1)))
        assert feb_data["total_requests"] < all_data["total_requests"]

    def test_end_date_filters_out_newer_events(self, seeded_db):
        # Only Jan events
        all_data = get_overview(seeded_db, AnalyticsFilters())
        jan_data  = get_overview(seeded_db, AnalyticsFilters(end_date=date(2025, 1, 31)))
        assert jan_data["total_requests"] < all_data["total_requests"]

    def test_narrow_date_range_returns_subset(self, seeded_db):
        jan_only = get_overview(seeded_db, AnalyticsFilters(
            start_date=date(2025, 1, 1), end_date=date(2025, 1, 31)
        ))
        feb_only = get_overview(seeded_db, AnalyticsFilters(
            start_date=date(2025, 2, 1), end_date=date(2025, 2, 28)
        ))
        all_data = get_overview(seeded_db, AnalyticsFilters())
        assert jan_only["total_requests"] + feb_only["total_requests"] == all_data["total_requests"]

    def test_spend_over_time_respects_date_filter(self, seeded_db):
        jan_spend = get_spend_over_time(seeded_db, AnalyticsFilters(
            start_date=date(2025, 1, 1), end_date=date(2025, 1, 31)
        ))
        all_spend = get_spend_over_time(seeded_db, AnalyticsFilters())
        assert len(jan_spend) <= len(all_spend)


class TestCombinedFilters:
    def test_dept_and_provider_combined(self, seeded_db):
        stats = get_model_stats(seeded_db, AnalyticsFilters(
            department="Engineering", provider="anthropic"
        ))
        # Only Engineering + anthropic events
        for s in stats:
            assert s["provider"] == "anthropic"

    def test_dept_and_date_combined(self, seeded_db):
        eng_feb = get_overview(seeded_db, AnalyticsFilters(
            department="Engineering", start_date=date(2025, 2, 1)
        ))
        # Only FILTER_T005 matches
        assert eng_feb["total_requests"] == 1


class TestFilterOptions:
    def test_get_available_departments(self, seeded_db):
        depts = get_available_departments(seeded_db)
        assert "Engineering" in depts
        assert "Marketing" in depts
        # Sorted, unique
        assert depts == sorted(set(depts))

    def test_get_available_providers(self, seeded_db):
        providers = get_available_providers(seeded_db)
        assert "anthropic" in providers
        assert "openai" in providers
