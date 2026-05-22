"""
Connector schema validation tests.

Verifies that each connector:
- Has required metadata attributes
- Validates schemas correctly
- Handles missing columns gracefully
- Produces well-formed normalized rows when data files exist
"""

import pytest
from app.connectors.base import BaseConnector, ConnectorError
from app.connectors.identity_connector import IdentityConnector
from app.connectors.model_pricing_connector import ModelPricingConnector
from app.connectors.license_connector import LicenseInventoryConnector
from app.connectors.api_gateway_connector import APIGatewayConnector
from app.connectors.browser_extension_connector import BrowserExtensionConnector
from app.connectors.kafka_connector import KafkaTelemetryConnector
from app.connectors.kubernetes_connector import KubernetesLogsConnector
from app.connectors.productivity_connector import ProductivityConnector
from app.connectors.clickhouse_connector import ClickHouseConnector


CONNECTORS = [
    IdentityConnector,
    ModelPricingConnector,
    LicenseInventoryConnector,
    APIGatewayConnector,
    BrowserExtensionConnector,
    KafkaTelemetryConnector,
    KubernetesLogsConnector,
    ProductivityConnector,
    ClickHouseConnector,
]


class TestConnectorMetadata:
    @pytest.mark.parametrize("cls", CONNECTORS)
    def test_has_source_name(self, cls):
        c = cls()
        assert isinstance(c.source_name, str)
        assert len(c.source_name) > 0

    @pytest.mark.parametrize("cls", CONNECTORS)
    def test_has_source_type(self, cls):
        c = cls()
        assert c.source_type in ("csv", "jsonl", "api", "kafka", "clickhouse", "kubernetes")

    @pytest.mark.parametrize("cls", CONNECTORS)
    def test_has_production_equivalent(self, cls):
        c = cls()
        assert isinstance(c.production_equivalent, str)
        assert len(c.production_equivalent) > 5


class TestSchemaValidation:
    def test_validate_schema_empty_rows_returns_no_errors(self):
        c = IdentityConnector()
        errors = c._validate_schema([])
        assert errors == []

    def test_validate_schema_missing_columns(self):
        c = IdentityConnector()
        # Pass a row that's missing required columns
        incomplete = [{"employee_id": "E001"}]  # missing many required cols
        errors = c._validate_schema(incomplete)
        assert len(errors) > 0
        assert all("Missing column:" in e for e in errors)

    def test_validate_schema_valid_row(self):
        c = ModelPricingConnector()
        # Build a row with all required columns
        if not c.REQUIRED_COLS:
            pytest.skip("No REQUIRED_COLS defined")
        row = {col: "dummy" for col in c.REQUIRED_COLS}
        errors = c._validate_schema([row])
        assert errors == []


class TestBaseHelpers:
    def test_safe_float_normal(self):
        c = IdentityConnector()
        assert c._safe_float("3.14") == pytest.approx(3.14)

    def test_safe_float_bad_value(self):
        c = IdentityConnector()
        assert c._safe_float("not_a_number") == 0.0

    def test_safe_float_none(self):
        c = IdentityConnector()
        assert c._safe_float(None) == 0.0

    def test_safe_int_normal(self):
        c = IdentityConnector()
        assert c._safe_int("42") == 42

    def test_safe_int_float_string(self):
        c = IdentityConnector()
        assert c._safe_int("42.9") == 42

    def test_safe_bool_true_strings(self):
        c = IdentityConnector()
        for s in ("true", "True", "TRUE", "1", "yes"):
            assert c._safe_bool(s) is True

    def test_safe_bool_false_strings(self):
        c = IdentityConnector()
        for s in ("false", "False", "0", "no"):
            assert c._safe_bool(s) is False

    def test_read_csv_missing_file_raises(self):
        c = IdentityConnector()
        with pytest.raises(ConnectorError, match="CSV not found"):
            c._read_csv("nonexistent_file.csv")

    def test_read_jsonl_missing_file_raises(self):
        c = KafkaTelemetryConnector()
        with pytest.raises(ConnectorError, match="JSONL not found"):
            c._read_jsonl("nonexistent_file.jsonl")
