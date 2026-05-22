"""
BaseConnector — every MVP connector reads CSV/JSONL.

Production upgrade path per connector:
  identity_directory      → Okta / Azure AD / Google Workspace SCIM API
  model_pricing           → Provider pricing APIs or internal pricing DB
  license_inventory       → ChatGPT Enterprise / GitHub Copilot admin REST APIs
  api_gateway_traces      → Real API gateway (Envoy/Kong) → ClickHouse/PostgreSQL

Each subclass only needs to implement:
  _fetch_raw()   — returns list[dict] from source (file today, API tomorrow)
  REQUIRED_COLS  — set of columns used for schema validation
"""

import csv
import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


class ConnectorError(Exception):
    pass


class BaseConnector(ABC):
    source_name: str = "base"
    source_type: str = "csv"
    production_equivalent: str = "Unknown"

    def __init__(self):
        self.data_dir = Path(settings.synthetic_data_dir)

    # ── public interface ──────────────────────────────────────────────────────

    def sync(self) -> tuple[list[dict], list[str]]:
        """Run full ETL: fetch → validate → normalize. Returns (rows, errors)."""
        raw = self._fetch_raw()
        errors = self._validate_schema(raw)
        normalized = self._normalize(raw)
        return normalized, errors

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
        if not rows or not self.REQUIRED_COLS:
            return []
        actual = set(rows[0].keys())
        missing = self.REQUIRED_COLS - actual
        return [f"Missing column: {c}" for c in sorted(missing)]

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
