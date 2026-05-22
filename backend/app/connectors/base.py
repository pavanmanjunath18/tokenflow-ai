"""
BaseConnector — every MVP connector reads CSV/JSONL.

Production upgrade path per connector:
  identity_directory      → Okta / Azure AD / Google Workspace SCIM API
  model_pricing           → Provider pricing APIs or internal pricing DB
  license_inventory       → ChatGPT Enterprise / GitHub Copilot admin REST APIs
  api_gateway_traces      → Real API gateway (Envoy/Kong) → ClickHouse/PostgreSQL

Each subclass only needs to implement:
  _fetch_raw()   — returns list[dict] from source (file today, API tomorrow)
  _normalize()   — cleans, casts, and shapes rows into canonical form
  REQUIRED_COLS  — set of columns used for schema validation

Watermark filtering:
  sync(since=<datetime>) filters normalized rows by their 'timestamp' field.
  Reference-data connectors (no 'timestamp' in output) are always full-refresh.
  Row-level validation warnings are collected via _validate_rows() and returned
  in ConnectorResult.row_warnings for the ingestion service to persist.
"""

import csv
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


class ConnectorError(Exception):
    pass


@dataclass
class ConnectorResult:
    rows: list[dict]
    schema_errors: list[str]
    row_warnings: list[dict]   # {row_number, field_name, error_type, raw_value, message}
    rows_skipped: int          # rows filtered out by watermark


class BaseConnector(ABC):
    source_name: str = "base"
    source_type: str = "csv"
    production_equivalent: str = "Unknown"

    def __init__(self):
        self.data_dir = Path(settings.synthetic_data_dir)

    # ── public interface ──────────────────────────────────────────────────────

    def sync(self, since: datetime | None = None) -> ConnectorResult:
        """
        Run full ETL: fetch → validate schema → normalize → watermark filter
        → validate rows. Returns a ConnectorResult.

        If *since* is provided and normalized rows contain a 'timestamp' field,
        only rows with timestamp >= since are included; the rest are counted in
        rows_skipped (simulating a real incremental/delta pull).
        """
        raw = self._fetch_raw()
        schema_errors = self._validate_schema(raw)
        all_rows = self._normalize(raw)

        # Watermark: filter time-series connectors; skip for reference data
        if since is not None and all_rows and "timestamp" in all_rows[0]:
            rows = [r for r in all_rows if r["timestamp"] >= since]
            rows_skipped = len(all_rows) - len(rows)
        else:
            rows = all_rows
            rows_skipped = 0

        row_warnings = self._validate_rows(rows)
        return ConnectorResult(
            rows=rows,
            schema_errors=schema_errors,
            row_warnings=row_warnings,
            rows_skipped=rows_skipped,
        )

    # ── abstract methods ──────────────────────────────────────────────────────

    @abstractmethod
    def _fetch_raw(self) -> list[dict[str, Any]]:
        """Read from source. Override to swap CSV → real integration."""

    @abstractmethod
    def _normalize(self, rows: list[dict]) -> list[dict]:
        """Clean, cast, and shape rows into a canonical form."""

    REQUIRED_COLS: set[str] = set()

    # ── shared helpers ────────────────────────────────────────────────────────

    def _validate_schema(self, rows: list[dict]) -> list[str]:
        """Check that the first row contains all REQUIRED_COLS."""
        if not rows or not self.REQUIRED_COLS:
            return []
        actual = set(rows[0].keys())
        missing = self.REQUIRED_COLS - actual
        return [f"Missing column: {c}" for c in sorted(missing)]

    def _validate_rows(self, rows: list[dict]) -> list[dict]:
        """
        Row-level validation on normalized output.
        Returns a list of warning dicts — one entry per missing required field
        value found across all rows. Caps at 100 warnings to avoid log spam.
        """
        if not rows or not self.REQUIRED_COLS:
            return []
        warnings: list[dict] = []
        for i, row in enumerate(rows):
            if len(warnings) >= 100:
                break
            for col in self.REQUIRED_COLS:
                val = row.get(col)
                if val is None or (isinstance(val, str) and not val.strip()):
                    warnings.append({
                        "row_number": i,
                        "field_name": col,
                        "error_type": "missing_value",
                        "raw_value": str(val),
                        "message": f"Required field '{col}' is empty or null after normalization",
                    })
        return warnings

    def _read_csv(self, filename: str) -> list[dict]:
        path = self.data_dir / filename
        if not path.exists():
            raise ConnectorError(f"CSV not found: {path}")
        with open(path, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def _read_jsonl(self, filename: str) -> list[dict]:
        path = self.data_dir / filename
        if not path.exists():
            raise ConnectorError(f"JSONL not found: {path}")
        rows = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
        return rows

    @staticmethod
    def _safe_float(val: Any, default: float = 0.0) -> float:
        try:
            return float(val)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _safe_int(val: Any, default: int = 0) -> int:
        try:
            return int(float(val))
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _safe_bool(val: Any, default: bool = False) -> bool:
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            return val.strip().lower() in ("true", "1", "yes")
        return default
