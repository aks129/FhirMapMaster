"""
Multi-Layer FHIR Validation Framework
Implements the specification from specs/003-validation-framework/spec.md
"""

import json
import time
import hashlib
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from abc import ABC, abstractmethod
import asyncio
from concurrent.futures import ThreadPoolExecutor

import requests
import pandas as pd
import structlog

logger = structlog.get_logger(__name__)


class ValidationSeverity(Enum):
    """Validation severity levels."""
    ERROR = "error"
    WARNING = "warning"
    INFORMATION = "information"


class ValidationLevel(Enum):
    """Validation thoroughness levels."""
    BASIC = "basic"
    STANDARD = "standard"
    STRICT = "strict"


@dataclass
class ValidationResult:
    """Single validation result."""
    severity: ValidationSeverity
    message: str
    location: str  # FHIR path
    rule_id: str
    validator: str
    suggested_fix: Optional[str] = None
    timestamp: float = 0

    def __post_init__(self):
        if self.timestamp == 0:
            self.timestamp = time.time()


@dataclass
class ValidationReport:
    """Complete validation report for a resource."""
    resource_id: str
    resource_type: str
    profile: str
    validation_level: ValidationLevel
    overall_status: str  # "valid", "valid_with_warnings", "invalid"
    results: List[ValidationResult]
    performance_metrics: Dict[str, float]
    timestamp: float = 0

    def __post_init__(self):
        if self.timestamp == 0:
            self.timestamp = time.time()

    @property
    def error_count(self) -> int:
        return len([r for r in self.results if r.severity == ValidationSeverity.ERROR])

    @property
    def warning_count(self) -> int:
        return len([r for r in self.results if r.severity == ValidationSeverity.WARNING])

    @property
    def is_valid(self) -> bool:
        return self.error_count == 0


class FHIRValidatorInterface(ABC):
    """Abstract interface for FHIR validators."""

    @abstractmethod
    async def validate_resource(self, resource: Dict, profile: str) -> List[ValidationResult]:
        """Validate a FHIR resource against a profile."""
        pass

    @abstractmethod
    def get_validator_info(self) -> Dict[str, str]:
        """Get validator information."""
        pass


class HAPIValidator(FHIRValidatorInterface):
    """HAPI FHIR Validator implementation."""

    def __init__(self, base_url: str = "http://hapi.fhir.org/baseR4"):
        self.base_url = base_url
        self.session = requests.Session()

    async def validate_resource(self, resource: Dict, profile: str) -> List[ValidationResult]:
        """Validate resource using HAPI FHIR validator."""
        try:
            # Prepare validation request
            validation_request = {
                "resourceType": "Parameters",
                "parameter": [
                    {
                        "name": "resource",
                        "resource": resource
                    },
                    {
                        "name": "profile",
                        "valueString": profile
                    }
                ]
            }

            # Call HAPI validation endpoint
            response = self.session.post(
                f"{self.base_url}/$validate",
                json=validation_request,
                headers={"Content-Type": "application/fhir+json"},
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                return self._parse_hapi_response(result)
            else:
                logger.error(f"HAPI validation failed: {response.status_code}")
                return [ValidationResult(
                    severity=ValidationSeverity.ERROR,
                    message=f"Validation service error: {response.status_code}",
                    location="root",
                    rule_id="SERVICE_ERROR",
                    validator="hapi"
                )]

        except Exception as e:
            logger.error(f"HAPI validation exception: {str(e)}")
            return [ValidationResult(
                severity=ValidationSeverity.ERROR,
                message=f"Validation error: {str(e)}",
                location="root",
                rule_id="VALIDATION_EXCEPTION",
                validator="hapi"
            )]

    def _parse_hapi_response(self, response: Dict) -> List[ValidationResult]:
        """Parse HAPI validation response."""
        results = []

        # Extract issues from OperationOutcome
        if response.get("resourceType") == "OperationOutcome":
            for issue in response.get("issue", []):
                severity_map = {
                    "fatal": ValidationSeverity.ERROR,
                    "error": ValidationSeverity.ERROR,
                    "warning": ValidationSeverity.WARNING,
                    "information": ValidationSeverity.INFORMATION
                }

                results.append(ValidationResult(
                    severity=severity_map.get(issue.get("severity"), ValidationSeverity.ERROR),
                    message=issue.get("diagnostics", ""),
                    location=".".join(issue.get("location", [""])),
                    rule_id=issue.get("code", "UNKNOWN"),
                    validator="hapi"
                ))

        return results

    def get_validator_info(self) -> Dict[str, str]:
        """Get HAPI validator information."""
        return {
            "name": "HAPI FHIR",
            "version": "6.10.0",
            "base_url": self.base_url
        }


class LocalStructuralValidator(FHIRValidatorInterface):
    """Local structural validator for basic FHIR validation."""

    def __init__(self):
        self.required_fields = {
            "Patient": ["resourceType"],
            "Observation": ["resourceType", "status", "code"],
            "Encounter": ["resourceType", "status", "class"],
            "Condition": ["resourceType", "code"],
            "MedicationRequest": ["resourceType", "status", "intent", "medicationReference"]
        }

    async def validate_resource(self, resource: Dict, profile: str) -> List[ValidationResult]:
        """Perform basic structural validation."""
        results = []
        resource_type = resource.get("resourceType")

        if not resource_type:
            results.append(ValidationResult(
                severity=ValidationSeverity.ERROR,
                message="Missing required field: resourceType",
                location="root",
                rule_id="MISSING_RESOURCE_TYPE",
                validator="structural",
                suggested_fix="Add resourceType field"
            ))
            return results

        # Check required fields
        required = self.required_fields.get(resource_type, [])
        for field in required:
            if field not in resource:
                results.append(ValidationResult(
                    severity=ValidationSeverity.ERROR,
                    message=f"Missing required field: {field}",
                    location=field,
                    rule_id="MISSING_REQUIRED_FIELD",
                    validator="structural",
                    suggested_fix=f"Add {field} field"
                ))

        # Validate ID format
        if "id" in resource:
            resource_id = resource["id"]
            if not isinstance(resource_id, str) or not resource_id.strip():
                results.append(ValidationResult(
                    severity=ValidationSeverity.ERROR,
                    message="Resource ID must be a non-empty string",
                    location="id",
                    rule_id="INVALID_ID",
                    validator="structural",
                    suggested_fix="Provide valid string ID"
                ))

        return results

    def get_validator_info(self) -> Dict[str, str]:
        """Get structural validator information."""
        return {
            "name": "Local Structural Validator",
            "version": "1.0.0"
        }


class BusinessRuleValidator:
    """Validator for business rules and cross-resource validation."""

    def __init__(self):
        self.rules = self._load_business_rules()

    def _load_business_rules(self) -> Dict[str, List[Dict]]:
        """Load business validation rules."""
        return {
            "Patient": [
                {
                    "rule_id": "PATIENT_NAME_REQUIRED",
                    "description": "Patient must have a name",
                    "severity": "error",
                    "check": lambda p: "name" in p and len(p["name"]) > 0
                },
                {
                    "rule_id": "BIRTH_DATE_FORMAT",
                    "description": "Birth date must be valid FHIR date",
                    "severity": "error",
                    "check": lambda p: self._validate_fhir_date(p.get("birthDate"))
                }
            ],
            "Observation": [
                {
                    "rule_id": "OBSERVATION_VALUE_REQUIRED",
                    "description": "Observation must have a value or dataAbsentReason",
                    "severity": "error",
                    "check": lambda o: any(k.startswith("value") for k in o.keys()) or "dataAbsentReason" in o
                }
            ]
        }

    def validate_business_rules(self, resource: Dict) -> List[ValidationResult]:
        """Validate business rules for a resource."""
        results = []
        resource_type = resource.get("resourceType")

        if resource_type not in self.rules:
            return results

        for rule in self.rules[resource_type]:
            try:
                if not rule["check"](resource):
                    severity_map = {
                        "error": ValidationSeverity.ERROR,
                        "warning": ValidationSeverity.WARNING,
                        "info": ValidationSeverity.INFORMATION
                    }

                    results.append(ValidationResult(
                        severity=severity_map.get(rule["severity"], ValidationSeverity.ERROR),
                        message=rule["description"],
                        location="root",
                        rule_id=rule["rule_id"],
                        validator="business_rules"
                    ))
            except Exception as e:
                logger.error(f"Business rule check failed: {str(e)}")

        return results

    def _validate_fhir_date(self, date_value: Optional[str]) -> bool:
        """Validate FHIR date format."""
        if not date_value:
            return True  # Optional field

        # Basic FHIR date patterns: YYYY, YYYY-MM, YYYY-MM-DD
        import re
        date_pattern = r'^\d{4}(-\d{2}(-\d{2})?)?$'
        return bool(re.match(date_pattern, date_value))


class ValidationCache:
    """Cache validation results to improve performance."""

    def __init__(self, max_size: int = 10000):
        self.cache = {}
        self.max_size = max_size
        self.access_times = {}

    def _generate_key(self, resource: Dict, profile: str, validator: str) -> str:
        """Generate cache key."""
        resource_hash = hashlib.md5(json.dumps(resource, sort_keys=True).encode()).hexdigest()
        return f"{validator}:{profile}:{resource_hash}"

    def get(self, resource: Dict, profile: str, validator: str) -> Optional[List[ValidationResult]]:
        """Get cached validation results."""
        key = self._generate_key(resource, profile, validator)
        if key in self.cache:
            self.access_times[key] = time.time()
            return self.cache[key]
        return None

    def set(self, resource: Dict, profile: str, validator: str, results: List[ValidationResult]):
        """Cache validation results."""
        key = self._generate_key(resource, profile, validator)

        # Evict oldest entries if cache is full
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])
            del self.cache[oldest_key]
            del self.access_times[oldest_key]

        self.cache[key] = results
        self.access_times[key] = time.time()


class QualityMetrics:
    """Calculate data quality metrics."""

    @staticmethod
    def calculate_completeness(resource: Dict, required_fields: List[str]) -> float:
        """Calculate field completeness percentage."""
        if not required_fields:
            return 100.0

        present_fields = sum(1 for field in required_fields if field in resource and resource[field])
        return (present_fields / len(required_fields)) * 100.0

    @staticmethod
    def calculate_profile_coverage(resource: Dict, profile_elements: List[str]) -> float:
        """Calculate profile element coverage."""
        if not profile_elements:
            return 100.0

        covered_elements = 0
        for element in profile_elements:
            # Simple path checking - can be enhanced
            if "." in element:
                # Handle nested paths
                parts = element.split(".")
                current = resource
                for part in parts:
                    if isinstance(current, dict) and part in current:
                        current = current[part]
                    else:
                        break
                else:
                    covered_elements += 1
            else:
                if element in resource:
                    covered_elements += 1

        return (covered_elements / len(profile_elements)) * 100.0


class MultiLayerValidationEngine:
    """Main validation engine implementing multi-layer validation."""

    def __init__(self):
        self.validators = {
            "structural": LocalStructuralValidator(),
            "hapi": HAPIValidator()
        }
        self.business_rule_validator = BusinessRuleValidator()
        self.cache = ValidationCache()
        self.quality_metrics = QualityMetrics()

    def add_validator(self, name: str, validator: FHIRValidatorInterface):
        """Add a new validator to the engine."""
        self.validators[name] = validator

    async def validate_resource(
        self,
        resource: Dict,
        profile: str,
        validation_level: ValidationLevel = ValidationLevel.STANDARD,
        validators: Optional[List[str]] = None
    ) -> ValidationReport:
        """Perform multi-layer validation of a FHIR resource."""

        start_time = time.time()
        all_results = []

        # Determine which validators to use
        validators_to_use = validators or list(self.validators.keys())
        if validation_level == ValidationLevel.BASIC:
            validators_to_use = ["structural"]
        elif validation_level == ValidationLevel.STRICT:
            validators_to_use = list(self.validators.keys())

        # Run structural validation first (always)
        if "structural" in validators_to_use:
            cached_results = self.cache.get(resource, profile, "structural")
            if cached_results:
                all_results.extend(cached_results)
            else:
                structural_results = await self.validators["structural"].validate_resource(resource, profile)
                self.cache.set(resource, profile, "structural", structural_results)
                all_results.extend(structural_results)

        # If structural validation passes, run other validators
        structural_errors = [r for r in all_results if r.severity == ValidationSeverity.ERROR]

        if not structural_errors or validation_level == ValidationLevel.STRICT:
            # Run other validators in parallel
            tasks = []
            for validator_name in validators_to_use:
                if validator_name != "structural" and validator_name in self.validators:
                    cached_results = self.cache.get(resource, profile, validator_name)
                    if cached_results:
                        all_results.extend(cached_results)
                    else:
                        task = self._validate_with_validator(
                            validator_name, resource, profile
                        )
                        tasks.append(task)

            if tasks:
                validator_results = await asyncio.gather(*tasks, return_exceptions=True)
                for results in validator_results:
                    if isinstance(results, list):
                        all_results.extend(results)

        # Run business rule validation
        if validation_level in [ValidationLevel.STANDARD, ValidationLevel.STRICT]:
            business_results = self.business_rule_validator.validate_business_rules(resource)
            all_results.extend(business_results)

        # Calculate metrics
        validation_time = time.time() - start_time
        performance_metrics = {
            "validation_time_ms": validation_time * 1000,
            "validators_used": len(validators_to_use),
            "cache_hits": 0  # Could implement cache hit tracking
        }

        # Determine overall status
        error_count = len([r for r in all_results if r.severity == ValidationSeverity.ERROR])
        warning_count = len([r for r in all_results if r.severity == ValidationSeverity.WARNING])

        if error_count > 0:
            overall_status = "invalid"
        elif warning_count > 0:
            overall_status = "valid_with_warnings"
        else:
            overall_status = "valid"

        return ValidationReport(
            resource_id=resource.get("id", "unknown"),
            resource_type=resource.get("resourceType", "unknown"),
            profile=profile,
            validation_level=validation_level,
            overall_status=overall_status,
            results=all_results,
            performance_metrics=performance_metrics
        )

    async def _validate_with_validator(self, validator_name: str, resource: Dict, profile: str) -> List[ValidationResult]:
        """Validate with a specific validator and cache results."""
        try:
            results = await self.validators[validator_name].validate_resource(resource, profile)
            self.cache.set(resource, profile, validator_name, results)
            return results
        except Exception as e:
            logger.error(f"Validator {validator_name} failed: {str(e)}")
            return [ValidationResult(
                severity=ValidationSeverity.ERROR,
                message=f"Validator {validator_name} failed: {str(e)}",
                location="root",
                rule_id="VALIDATOR_ERROR",
                validator=validator_name
            )]

    def validate_bundle(self, bundle: Dict, validation_level: ValidationLevel = ValidationLevel.STANDARD) -> List[ValidationReport]:
        """Validate all resources in a FHIR Bundle."""
        reports = []

        if bundle.get("resourceType") != "Bundle":
            # Treat single resource as bundle entry
            entries = [{"resource": bundle}]
        else:
            entries = bundle.get("entry", [])

        async def validate_all():
            tasks = []
            for entry in entries:
                resource = entry.get("resource", {})
                if resource:
                    # Determine profile based on resource type
                    profile = self._get_default_profile(resource.get("resourceType"))
                    task = self.validate_resource(resource, profile, validation_level)
                    tasks.append(task)

            return await asyncio.gather(*tasks, return_exceptions=True)

        # Run validation
        try:
            results = asyncio.run(validate_all())
            for result in results:
                if isinstance(result, ValidationReport):
                    reports.append(result)
        except Exception as e:
            logger.error(f"Bundle validation failed: {str(e)}")

        return reports

    def _get_default_profile(self, resource_type: str) -> str:
        """Get default profile URL for resource type."""
        base_profiles = {
            "Patient": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-patient",
            "Observation": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-observation-lab",
            "Encounter": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-encounter",
            "Condition": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-condition",
            "MedicationRequest": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-medicationrequest"
        }
        return base_profiles.get(resource_type, f"http://hl7.org/fhir/StructureDefinition/{resource_type}")

    def get_validator_info(self) -> Dict[str, Dict[str, str]]:
        """Get information about all configured validators."""
        info = {}
        for name, validator in self.validators.items():
            info[name] = validator.get_validator_info()
        return info


# Global validation engine instance
validation_engine = MultiLayerValidationEngine()