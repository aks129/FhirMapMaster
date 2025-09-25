"""
Test suite for Multi-Layer Validation Framework
Tests FHIR validation, quality metrics, and reporting
"""

import pytest
import asyncio
import json
import time
from unittest.mock import Mock, patch, AsyncMock

from utils.validation.validation_engine import (
    ValidationEngine,
    MultiLayerValidationEngine,
    ValidationResult,
    ValidationReport,
    ValidationSeverity,
    ValidationLevel,
    HAPIValidator,
    LocalStructuralValidator,
    BusinessRuleValidator,
    ValidationCache,
    QualityMetrics,
    validation_engine
)


class TestValidationResult:
    """Test ValidationResult data structure."""

    def test_validation_result_creation(self):
        result = ValidationResult(
            severity=ValidationSeverity.ERROR,
            message="Missing required field",
            location="Patient.name",
            rule_id="MISSING_REQUIRED",
            validator="structural",
            suggested_fix="Add name field"
        )

        assert result.severity == ValidationSeverity.ERROR
        assert result.message == "Missing required field"
        assert result.location == "Patient.name"
        assert result.suggested_fix == "Add name field"
        assert result.timestamp > 0

    def test_validation_result_auto_timestamp(self):
        result1 = ValidationResult(
            severity=ValidationSeverity.WARNING,
            message="Test message",
            location="root",
            rule_id="TEST",
            validator="test"
        )

        time.sleep(0.01)

        result2 = ValidationResult(
            severity=ValidationSeverity.WARNING,
            message="Test message 2",
            location="root",
            rule_id="TEST",
            validator="test"
        )

        assert result2.timestamp > result1.timestamp


class TestValidationReport:
    """Test ValidationReport data structure."""

    def test_validation_report_creation(self):
        results = [
            ValidationResult(
                severity=ValidationSeverity.ERROR,
                message="Error 1",
                location="field1",
                rule_id="ERR1",
                validator="test"
            ),
            ValidationResult(
                severity=ValidationSeverity.WARNING,
                message="Warning 1",
                location="field2",
                rule_id="WARN1",
                validator="test"
            )
        ]

        report = ValidationReport(
            resource_id="test-123",
            resource_type="Patient",
            profile="test-profile",
            validation_level=ValidationLevel.STANDARD,
            overall_status="invalid",
            results=results,
            performance_metrics={"validation_time_ms": 100.5}
        )

        assert report.resource_id == "test-123"
        assert report.error_count == 1
        assert report.warning_count == 1
        assert not report.is_valid
        assert report.performance_metrics["validation_time_ms"] == 100.5

    def test_validation_report_properties(self):
        results = [
            ValidationResult(ValidationSeverity.WARNING, "W1", "loc1", "WARN1", "test"),
            ValidationResult(ValidationSeverity.WARNING, "W2", "loc2", "WARN2", "test")
        ]

        report = ValidationReport(
            resource_id="test-456",
            resource_type="Observation",
            profile="test-profile",
            validation_level=ValidationLevel.BASIC,
            overall_status="valid_with_warnings",
            results=results,
            performance_metrics={}
        )

        assert report.error_count == 0
        assert report.warning_count == 2
        assert report.is_valid  # No errors = valid


class TestLocalStructuralValidator:
    """Test local structural validation."""

    @pytest.fixture
    def validator(self):
        return LocalStructuralValidator()

    async def test_valid_patient_resource(self, validator):
        patient = {
            "resourceType": "Patient",
            "id": "test-123",
            "name": [{"given": ["John"], "family": "Doe"}]
        }

        results = await validator.validate_resource(patient, "")
        assert len(results) == 0

    async def test_missing_resource_type(self, validator):
        invalid_resource = {
            "id": "test-123"
        }

        results = await validator.validate_resource(invalid_resource, "")
        assert len(results) == 1
        assert results[0].severity == ValidationSeverity.ERROR
        assert "resourceType" in results[0].message

    async def test_missing_required_fields(self, validator):
        observation = {
            "resourceType": "Observation",
            "id": "test-obs"
            # Missing status and code
        }

        results = await validator.validate_resource(observation, "")

        # Should have errors for missing status and code
        error_messages = [r.message for r in results]
        assert any("status" in msg for msg in error_messages)
        assert any("code" in msg for msg in error_messages)

    async def test_invalid_id_format(self, validator):
        patient = {
            "resourceType": "Patient",
            "id": "",  # Empty ID
            "name": [{"given": ["John"], "family": "Doe"}]
        }

        results = await validator.validate_resource(patient, "")

        # Should have error for invalid ID
        assert any("ID" in r.message for r in results)

    def test_validator_info(self, validator):
        info = validator.get_validator_info()
        assert info["name"] == "Local Structural Validator"
        assert "version" in info


class TestBusinessRuleValidator:
    """Test business rules validation."""

    @pytest.fixture
    def validator(self):
        return BusinessRuleValidator()

    def test_patient_name_required_rule(self, validator):
        # Patient without name
        patient_no_name = {
            "resourceType": "Patient",
            "id": "test-123"
        }

        results = validator.validate_business_rules(patient_no_name)
        assert len(results) > 0
        assert any("name" in r.message.lower() for r in results)

        # Patient with name
        patient_with_name = {
            "resourceType": "Patient",
            "id": "test-123",
            "name": [{"given": ["John"], "family": "Doe"}]
        }

        results = validator.validate_business_rules(patient_with_name)
        name_errors = [r for r in results if "name" in r.message.lower()]
        assert len(name_errors) == 0

    def test_birth_date_format_rule(self, validator):
        # Invalid date format
        patient_invalid_date = {
            "resourceType": "Patient",
            "id": "test-123",
            "name": [{"given": ["John"], "family": "Doe"}],
            "birthDate": "01/15/1980"  # Invalid format
        }

        results = validator.validate_business_rules(patient_invalid_date)
        assert any("date" in r.message.lower() for r in results)

        # Valid date format
        patient_valid_date = {
            "resourceType": "Patient",
            "id": "test-123",
            "name": [{"given": ["John"], "family": "Doe"}],
            "birthDate": "1980-01-15"
        }

        results = validator.validate_business_rules(patient_valid_date)
        date_errors = [r for r in results if "date" in r.message.lower()]
        assert len(date_errors) == 0

    def test_observation_value_required_rule(self, validator):
        # Observation without value or dataAbsentReason
        obs_no_value = {
            "resourceType": "Observation",
            "status": "final",
            "code": {"text": "Test"}
        }

        results = validator.validate_business_rules(obs_no_value)
        assert any("value" in r.message.lower() for r in results)

        # Observation with value
        obs_with_value = {
            "resourceType": "Observation",
            "status": "final",
            "code": {"text": "Test"},
            "valueString": "Normal"
        }

        results = validator.validate_business_rules(obs_with_value)
        value_errors = [r for r in results if "value" in r.message.lower()]
        assert len(value_errors) == 0

    def test_fhir_date_validation(self, validator):
        # Test the helper method
        assert validator._validate_fhir_date("2024-01-15")
        assert validator._validate_fhir_date("2024-01")
        assert validator._validate_fhir_date("2024")
        assert validator._validate_fhir_date("")  # Empty is valid (optional)
        assert validator._validate_fhir_date(None)  # None is valid (optional)

        assert not validator._validate_fhir_date("01/15/2024")
        assert not validator._validate_fhir_date("invalid-date")


class TestValidationCache:
    """Test validation result caching."""

    def test_cache_operations(self):
        cache = ValidationCache(max_size=10)

        resource = {"resourceType": "Patient", "id": "test"}
        profile = "test-profile"
        validator = "test-validator"

        results = [
            ValidationResult(ValidationSeverity.ERROR, "Test error", "root", "TEST", "test")
        ]

        # Test cache miss
        assert cache.get(resource, profile, validator) is None

        # Test cache set and hit
        cache.set(resource, profile, validator, results)
        cached_results = cache.get(resource, profile, validator)

        assert cached_results is not None
        assert len(cached_results) == 1
        assert cached_results[0].message == "Test error"

    def test_cache_eviction(self):
        cache = ValidationCache(max_size=2)

        # Add more items than cache size
        for i in range(3):
            resource = {"resourceType": "Patient", "id": f"test-{i}"}
            results = [ValidationResult(ValidationSeverity.INFO, f"Info {i}", "root", "INFO", "test")]
            cache.set(resource, "profile", "validator", results)

        # Check eviction occurred
        assert len(cache.cache) <= 2

    def test_cache_key_generation(self):
        cache = ValidationCache()

        resource1 = {"resourceType": "Patient", "id": "test"}
        resource2 = {"resourceType": "Patient", "id": "test"}
        resource3 = {"resourceType": "Patient", "id": "different"}

        key1 = cache._generate_key(resource1, "profile", "validator")
        key2 = cache._generate_key(resource2, "profile", "validator")
        key3 = cache._generate_key(resource3, "profile", "validator")

        # Same resources should generate same key
        assert key1 == key2

        # Different resources should generate different keys
        assert key1 != key3


class TestQualityMetrics:
    """Test data quality metrics calculation."""

    def test_completeness_calculation(self):
        # All fields present
        resource_complete = {
            "field1": "value1",
            "field2": "value2",
            "field3": "value3"
        }
        required_fields = ["field1", "field2", "field3"]

        completeness = QualityMetrics.calculate_completeness(resource_complete, required_fields)
        assert completeness == 100.0

        # Some fields missing
        resource_partial = {
            "field1": "value1",
            "field2": None,
            "field3": "value3"
        }

        completeness = QualityMetrics.calculate_completeness(resource_partial, required_fields)
        assert completeness == (2/3) * 100

        # No required fields
        completeness = QualityMetrics.calculate_completeness(resource_complete, [])
        assert completeness == 100.0

    def test_profile_coverage_calculation(self):
        resource = {
            "name": "test",
            "nested": {"field": "value"},
            "array": [{"item": "value1"}]
        }

        # All elements present
        profile_elements = ["name", "nested", "array"]
        coverage = QualityMetrics.calculate_profile_coverage(resource, profile_elements)
        assert coverage == 100.0

        # Some elements missing
        profile_elements = ["name", "missing", "nested"]
        coverage = QualityMetrics.calculate_profile_coverage(resource, profile_elements)
        assert coverage == (2/3) * 100

        # No profile elements
        coverage = QualityMetrics.calculate_profile_coverage(resource, [])
        assert coverage == 100.0


class TestHAPIValidator:
    """Test HAPI FHIR validator (mocked)."""

    @pytest.fixture
    def validator(self):
        return HAPIValidator("http://test-hapi.com")

    @patch('requests.Session.post')
    async def test_successful_validation(self, mock_post, validator):
        # Mock successful HAPI response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "resourceType": "OperationOutcome",
            "issue": [
                {
                    "severity": "information",
                    "code": "informational",
                    "diagnostics": "Validation successful",
                    "location": ["Patient"]
                }
            ]
        }
        mock_post.return_value = mock_response

        resource = {"resourceType": "Patient", "id": "test"}
        results = await validator.validate_resource(resource, "test-profile")

        assert len(results) == 1
        assert results[0].severity == ValidationSeverity.INFORMATION
        assert results[0].validator == "hapi"

    @patch('requests.Session.post')
    async def test_validation_with_errors(self, mock_post, validator):
        # Mock HAPI response with errors
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "resourceType": "OperationOutcome",
            "issue": [
                {
                    "severity": "error",
                    "code": "required",
                    "diagnostics": "Missing required field 'name'",
                    "location": ["Patient.name"]
                }
            ]
        }
        mock_post.return_value = mock_response

        resource = {"resourceType": "Patient", "id": "test"}
        results = await validator.validate_resource(resource, "test-profile")

        assert len(results) == 1
        assert results[0].severity == ValidationSeverity.ERROR
        assert "name" in results[0].message

    @patch('requests.Session.post')
    async def test_validation_service_error(self, mock_post, validator):
        # Mock HTTP error
        mock_response = Mock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response

        resource = {"resourceType": "Patient", "id": "test"}
        results = await validator.validate_resource(resource, "test-profile")

        assert len(results) == 1
        assert results[0].severity == ValidationSeverity.ERROR
        assert "service error" in results[0].message.lower()

    def test_validator_info(self, validator):
        info = validator.get_validator_info()
        assert info["name"] == "HAPI FHIR"
        assert info["base_url"] == "http://test-hapi.com"


class TestMultiLayerValidationEngine:
    """Test the main validation engine."""

    @pytest.fixture
    def engine(self):
        return MultiLayerValidationEngine()

    async def test_basic_validation_level(self, engine):
        resource = {
            "resourceType": "Patient",
            "id": "test-123",
            "name": [{"given": ["John"], "family": "Doe"}]
        }

        report = await engine.validate_resource(
            resource,
            "test-profile",
            ValidationLevel.BASIC
        )

        assert report.resource_id == "test-123"
        assert report.validation_level == ValidationLevel.BASIC
        assert report.is_valid  # Should pass basic validation
        assert "validation_time_ms" in report.performance_metrics

    async def test_validation_with_errors(self, engine):
        invalid_resource = {
            "resourceType": "Patient",
            "id": ""  # Invalid empty ID
        }

        report = await engine.validate_resource(
            invalid_resource,
            "test-profile",
            ValidationLevel.STANDARD
        )

        assert not report.is_valid
        assert report.error_count > 0
        assert report.overall_status == "invalid"

    async def test_validation_with_warnings_only(self, engine):
        # This would need a resource that passes structural validation
        # but fails business rules with warnings only
        resource = {
            "resourceType": "Patient",
            "id": "test-123",
            "name": [{"given": ["John"], "family": "Doe"}]
        }

        # Mock business rules to return warnings
        with patch.object(engine.business_rule_validator, 'validate_business_rules') as mock_business:
            mock_business.return_value = [
                ValidationResult(ValidationSeverity.WARNING, "Test warning", "root", "WARN", "business")
            ]

            report = await engine.validate_resource(
                resource,
                "test-profile",
                ValidationLevel.STANDARD
            )

            assert report.is_valid  # No errors
            assert report.warning_count > 0
            assert report.overall_status == "valid_with_warnings"

    async def test_bundle_validation(self, engine):
        bundle = {
            "resourceType": "Bundle",
            "entry": [
                {
                    "resource": {
                        "resourceType": "Patient",
                        "id": "patient-1",
                        "name": [{"given": ["John"], "family": "Doe"}]
                    }
                },
                {
                    "resource": {
                        "resourceType": "Patient",
                        "id": "patient-2",
                        "name": [{"given": ["Jane"], "family": "Smith"}]
                    }
                }
            ]
        }

        reports = engine.validate_bundle(bundle, ValidationLevel.STANDARD)
        assert len(reports) == 2
        assert all(r.resource_type == "Patient" for r in reports)

    def test_default_profile_selection(self, engine):
        # Test default profile URL generation
        patient_profile = engine._get_default_profile("Patient")
        assert "us-core-patient" in patient_profile.lower()

        observation_profile = engine._get_default_profile("Observation")
        assert "observation" in observation_profile.lower()

        # Unknown resource type
        unknown_profile = engine._get_default_profile("UnknownResource")
        assert "UnknownResource" in unknown_profile

    def test_validator_info_aggregation(self, engine):
        info = engine.get_validator_info()
        assert "structural" in info
        assert "hapi" in info
        assert all("name" in validator_info for validator_info in info.values())


class TestIntegration:
    """Integration tests for the validation framework."""

    async def test_end_to_end_validation_workflow(self):
        """Test complete validation workflow."""
        engine = MultiLayerValidationEngine()

        # Test data: mix of valid and invalid resources
        test_resources = [
            {
                "resourceType": "Patient",
                "id": "valid-patient",
                "name": [{"given": ["John"], "family": "Doe"}],
                "birthDate": "1980-01-15"
            },
            {
                "resourceType": "Patient",
                "id": "",  # Invalid: empty ID
                "name": [{"given": ["Jane"], "family": "Smith"}]
            },
            {
                "resourceType": "Patient",
                "id": "no-name-patient"
                # Invalid: missing required name
            }
        ]

        validation_results = []

        for resource in test_resources:
            report = await engine.validate_resource(
                resource,
                "http://hl7.org/fhir/us/core/StructureDefinition/us-core-patient",
                ValidationLevel.STANDARD
            )
            validation_results.append(report)

        # Verify results
        assert len(validation_results) == 3

        # First resource should be valid
        assert validation_results[0].is_valid

        # Second and third should have errors
        assert not validation_results[1].is_valid
        assert not validation_results[2].is_valid

        # Check performance metrics are populated
        for report in validation_results:
            assert "validation_time_ms" in report.performance_metrics
            assert report.performance_metrics["validation_time_ms"] > 0

    def test_global_validation_engine_instance(self):
        """Test the global validation engine instance."""
        assert validation_engine is not None
        assert isinstance(validation_engine, MultiLayerValidationEngine)

        # Test that it has the expected validators
        validator_info = validation_engine.get_validator_info()
        assert "structural" in validator_info
        assert "hapi" in validator_info


# Pytest configuration
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


if __name__ == "__main__":
    pytest.main([__file__])