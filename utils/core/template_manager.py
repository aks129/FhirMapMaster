"""
Reusable Template Management System
Implements the specification from specs/005-reusable-templates/spec.md
"""

import os
import json
import yaml
import hashlib
import time
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, asdict, field
from enum import Enum
from pathlib import Path
import re
import git

import pandas as pd
import jinja2
from jinja2 import Environment, FileSystemLoader, select_autoescape
import structlog

logger = structlog.get_logger(__name__)


class TemplateCategory(Enum):
    """Template categories."""
    RESOURCE_TEMPLATE = "resource_templates"
    USE_CASE_TEMPLATE = "use_case_templates"
    DATA_SOURCE_TEMPLATE = "data_source_templates"
    COMPOSITE_TEMPLATE = "composite_templates"


class ComplexityLevel(Enum):
    """Template complexity levels."""
    BASIC = "basic"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


@dataclass
class TemplateParameter:
    """Template parameter definition."""
    name: str
    type: str  # string, choice, boolean, conditional
    description: str
    required: bool = False
    default: Optional[Any] = None
    options: Optional[List[str]] = None
    validation_pattern: Optional[str] = None
    condition: Optional[str] = None


@dataclass
class FieldMapping:
    """FHIR field mapping definition."""
    fhir_path: str
    source_expression: str
    required: bool = False
    transformation_type: str = "direct"
    validation_rules: List[str] = field(default_factory=list)


@dataclass
class TestCase:
    """Template test case."""
    name: str
    input_data: Dict[str, Any]
    expected_output: Dict[str, Any]
    validation_profile: Optional[str] = None


@dataclass
class TemplateMetadata:
    """Template metadata."""
    name: str
    version: str
    author: str
    created_date: str
    updated_date: str
    description: str
    tags: List[str]
    category: TemplateCategory
    use_cases: List[str]
    complexity_level: ComplexityLevel
    fhir_version: str = "R4B"
    implementation_guides: List[str] = field(default_factory=list)


@dataclass
class MappingTemplate:
    """Complete mapping template definition."""
    metadata: TemplateMetadata
    parameters: List[TemplateParameter]
    schema_requirements: Dict[str, Any]
    fhir_mapping: Dict[str, Any]
    field_mappings: List[FieldMapping]
    validation_rules: List[Dict[str, Any]]
    test_cases: List[TestCase]

    # Runtime fields
    template_id: str = ""
    file_path: str = ""

    def __post_init__(self):
        if not self.template_id:
            self.template_id = self._generate_template_id()

    def _generate_template_id(self) -> str:
        """Generate unique template ID."""
        content = f"{self.metadata.name}_{self.metadata.version}_{self.metadata.category.value}"
        return hashlib.md5(content.encode()).hexdigest()[:12]


class TemplateRepository:
    """Template repository for storage and versioning."""

    def __init__(self, repo_path: str = "templates"):
        self.repo_path = Path(repo_path)
        self.repo_path.mkdir(exist_ok=True)

        # Initialize git repo if not exists
        try:
            self.git_repo = git.Repo(self.repo_path)
        except git.InvalidGitRepositoryError:
            self.git_repo = git.Repo.init(self.repo_path)

        self.templates_cache = {}
        self.metadata_index = {}

    def save_template(self, template: MappingTemplate) -> bool:
        """Save template to repository."""
        try:
            # Determine file path based on category
            category_dir = self.repo_path / template.metadata.category.value
            category_dir.mkdir(exist_ok=True)

            template_file = category_dir / f"{template.metadata.name.lower().replace(' ', '_')}_v{template.metadata.version}.yaml"

            # Convert to YAML
            template_dict = self._template_to_dict(template)

            with open(template_file, 'w') as f:
                yaml.dump(template_dict, f, default_flow_style=False, sort_keys=False)

            # Update template object
            template.file_path = str(template_file)

            # Update cache and index
            self.templates_cache[template.template_id] = template
            self._update_metadata_index(template)

            # Git commit
            self._commit_template(template, "Added template")

            logger.info(f"Saved template: {template.metadata.name} v{template.metadata.version}")
            return True

        except Exception as e:
            logger.error(f"Failed to save template: {str(e)}")
            return False

    def load_template(self, template_id: str) -> Optional[MappingTemplate]:
        """Load template by ID."""
        if template_id in self.templates_cache:
            return self.templates_cache[template_id]

        # Search for template file
        for template_file in self.repo_path.rglob("*.yaml"):
            try:
                with open(template_file, 'r') as f:
                    template_dict = yaml.safe_load(f)

                template = self._dict_to_template(template_dict)
                template.file_path = str(template_file)

                if template.template_id == template_id:
                    self.templates_cache[template_id] = template
                    return template

            except Exception as e:
                logger.warning(f"Failed to load template from {template_file}: {str(e)}")

        return None

    def search_templates(self,
                        query: str = "",
                        category: Optional[TemplateCategory] = None,
                        resource_type: Optional[str] = None,
                        use_case: Optional[str] = None,
                        tags: Optional[List[str]] = None,
                        limit: int = 20) -> List[MappingTemplate]:
        """Search templates with filters."""

        results = []

        # Load all templates if not cached
        if not self.templates_cache:
            self._load_all_templates()

        for template in self.templates_cache.values():
            # Apply filters
            if category and template.metadata.category != category:
                continue

            if resource_type and not any(resource_type.lower() in rm.get("resource", "").lower()
                                       for rm in template.fhir_mapping.values()):
                continue

            if use_case and use_case not in template.metadata.use_cases:
                continue

            if tags and not any(tag in template.metadata.tags for tag in tags):
                continue

            # Text search in name, description, tags
            if query:
                searchable_text = " ".join([
                    template.metadata.name,
                    template.metadata.description,
                    " ".join(template.metadata.tags)
                ]).lower()

                if query.lower() not in searchable_text:
                    continue

            results.append(template)

        # Sort by relevance (can be enhanced with scoring)
        results.sort(key=lambda t: t.metadata.updated_date, reverse=True)

        return results[:limit]

    def get_popular_templates(self, limit: int = 10) -> List[MappingTemplate]:
        """Get most popular templates (by usage statistics)."""
        # Placeholder implementation - could track usage statistics
        templates = self.search_templates(limit=limit)
        return templates[:limit]

    def _template_to_dict(self, template: MappingTemplate) -> Dict[str, Any]:
        """Convert template to dictionary for YAML serialization."""
        return {
            "metadata": asdict(template.metadata),
            "parameters": [asdict(p) for p in template.parameters],
            "schema_requirements": template.schema_requirements,
            "fhir_mapping": template.fhir_mapping,
            "field_mappings": [asdict(fm) for fm in template.field_mappings],
            "validation_rules": template.validation_rules,
            "test_cases": [asdict(tc) for tc in template.test_cases]
        }

    def _dict_to_template(self, data: Dict[str, Any]) -> MappingTemplate:
        """Convert dictionary to template object."""

        # Convert metadata
        metadata_dict = data["metadata"]
        metadata_dict["category"] = TemplateCategory(metadata_dict["category"])
        metadata_dict["complexity_level"] = ComplexityLevel(metadata_dict["complexity_level"])
        metadata = TemplateMetadata(**metadata_dict)

        # Convert parameters
        parameters = [TemplateParameter(**p) for p in data.get("parameters", [])]

        # Convert field mappings
        field_mappings = [FieldMapping(**fm) for fm in data.get("field_mappings", [])]

        # Convert test cases
        test_cases = [TestCase(**tc) for tc in data.get("test_cases", [])]

        return MappingTemplate(
            metadata=metadata,
            parameters=parameters,
            schema_requirements=data.get("schema_requirements", {}),
            fhir_mapping=data.get("fhir_mapping", {}),
            field_mappings=field_mappings,
            validation_rules=data.get("validation_rules", []),
            test_cases=test_cases
        )

    def _load_all_templates(self):
        """Load all templates into cache."""
        for template_file in self.repo_path.rglob("*.yaml"):
            try:
                with open(template_file, 'r') as f:
                    template_dict = yaml.safe_load(f)

                template = self._dict_to_template(template_dict)
                template.file_path = str(template_file)

                self.templates_cache[template.template_id] = template
                self._update_metadata_index(template)

            except Exception as e:
                logger.warning(f"Failed to load template from {template_file}: {str(e)}")

    def _update_metadata_index(self, template: MappingTemplate):
        """Update searchable metadata index."""
        self.metadata_index[template.template_id] = {
            "name": template.metadata.name,
            "tags": template.metadata.tags,
            "category": template.metadata.category.value,
            "use_cases": template.metadata.use_cases,
            "resource_types": [fm.fhir_path.split(".")[0] for fm in template.field_mappings]
        }

    def _commit_template(self, template: MappingTemplate, message: str):
        """Commit template changes to git."""
        try:
            self.git_repo.index.add([template.file_path])
            self.git_repo.index.commit(f"{message}: {template.metadata.name} v{template.metadata.version}")
        except Exception as e:
            logger.warning(f"Git commit failed: {str(e)}")


class TemplateEngine:
    """Template processing engine using Jinja2."""

    def __init__(self, templates_path: str = "templates"):
        self.templates_path = Path(templates_path)
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_path)),
            autoescape=select_autoescape(['html', 'xml'])
        )

        # Add custom filters for FHIR processing
        self._register_fhir_filters()

    def _register_fhir_filters(self):
        """Register FHIR-specific Jinja2 filters."""

        def sanitize_id(value):
            """Sanitize string for FHIR ID use."""
            if not value:
                return ""
            # Remove invalid characters, keep alphanumeric, hyphens, periods
            sanitized = re.sub(r'[^A-Za-z0-9\-\.]', '', str(value))
            return sanitized[:64]  # FHIR ID max length

        def to_fhir_date(value):
            """Convert various date formats to FHIR date."""
            if not value:
                return None

            # Handle pandas Timestamp
            if hasattr(value, 'strftime'):
                return value.strftime('%Y-%m-%d')

            # Handle string dates (basic patterns)
            date_str = str(value).strip()

            # MM/dd/yyyy -> yyyy-MM-dd
            if re.match(r'\d{2}/\d{2}/\d{4}', date_str):
                parts = date_str.split('/')
                return f"{parts[2]}-{parts[0].zfill(2)}-{parts[1].zfill(2)}"

            # dd-MM-yyyy -> yyyy-MM-dd
            if re.match(r'\d{2}-\d{2}-\d{4}', date_str):
                parts = date_str.split('-')
                return f"{parts[2]}-{parts[1]}-{parts[0]}"

            # Return as-is if already in FHIR format
            if re.match(r'\d{4}-\d{2}-\d{2}', date_str):
                return date_str

            return None

        def to_coding(code, system, display=None):
            """Create FHIR Coding object."""
            coding = {
                "system": system,
                "code": str(code) if code else None
            }
            if display:
                coding["display"] = str(display)
            return coding

        def format_name(first_name, last_name, middle_name=None):
            """Format FHIR HumanName."""
            name = {
                "use": "official",
                "family": str(last_name).strip() if last_name else None,
                "given": []
            }

            if first_name:
                name["given"].append(str(first_name).strip())
            if middle_name:
                name["given"].append(str(middle_name).strip())

            return name

        # Register filters
        self.env.filters['sanitize_id'] = sanitize_id
        self.env.filters['to_fhir_date'] = to_fhir_date
        self.env.filters['to_coding'] = to_coding
        self.env.filters['format_name'] = format_name

    def apply_template(self,
                      template: MappingTemplate,
                      source_data: pd.DataFrame,
                      parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Apply template to source data."""

        # Validate parameters
        validation_errors = self._validate_parameters(template, parameters)
        if validation_errors:
            raise ValueError(f"Parameter validation failed: {validation_errors}")

        # Process each row
        results = []
        for _, row in source_data.iterrows():
            try:
                # Create context for template
                context = {
                    **parameters,
                    **row.to_dict(),
                    'row_index': row.name
                }

                # Apply field mappings
                fhir_resource = self._apply_field_mappings(template, context)

                # Validate result
                if self._validate_result(template, fhir_resource):
                    results.append(fhir_resource)

            except Exception as e:
                logger.error(f"Template application failed for row {row.name}: {str(e)}")
                continue

        return results

    def _validate_parameters(self,
                           template: MappingTemplate,
                           parameters: Dict[str, Any]) -> List[str]:
        """Validate template parameters."""
        errors = []

        for param in template.parameters:
            value = parameters.get(param.name)

            # Check required parameters
            if param.required and (value is None or value == ""):
                errors.append(f"Required parameter '{param.name}' is missing")
                continue

            if value is None:
                continue

            # Validate parameter type
            if param.type == "choice" and param.options:
                if str(value) not in param.options:
                    errors.append(f"Parameter '{param.name}' must be one of: {param.options}")

            # Validate pattern
            if param.validation_pattern and not re.match(param.validation_pattern, str(value)):
                errors.append(f"Parameter '{param.name}' does not match required pattern")

        return errors

    def _apply_field_mappings(self,
                            template: MappingTemplate,
                            context: Dict[str, Any]) -> Dict[str, Any]:
        """Apply field mappings to create FHIR resource."""

        # Start with resource type
        resource = {
            "resourceType": template.fhir_mapping.get("resource_type", "Unknown")
        }

        # Apply each field mapping
        for mapping in template.field_mappings:
            try:
                # Render the expression template
                template_obj = self.env.from_string(mapping.source_expression)
                rendered_value = template_obj.render(**context)

                # Parse JSON if the result looks like JSON
                try:
                    if rendered_value.strip().startswith(('{', '[')):
                        rendered_value = json.loads(rendered_value)
                except json.JSONDecodeError:
                    pass  # Keep as string

                # Set value in FHIR resource
                self._set_nested_value(resource, mapping.fhir_path, rendered_value)

            except Exception as e:
                logger.error(f"Field mapping failed for {mapping.fhir_path}: {str(e)}")
                if mapping.required:
                    raise

        return resource

    def _set_nested_value(self, obj: Dict[str, Any], path: str, value: Any):
        """Set nested value in dictionary using dot notation."""
        parts = path.split('.')
        current = obj

        # Navigate to parent
        for part in parts[:-1]:
            # Handle array indices like "name[0]"
            if '[' in part:
                key, index_str = part.split('[')
                index = int(index_str.rstrip(']'))

                if key not in current:
                    current[key] = []

                # Extend array if needed
                while len(current[key]) <= index:
                    current[key].append({})

                current = current[key][index]
            else:
                if part not in current:
                    current[part] = {}
                current = current[part]

        # Set final value
        final_key = parts[-1]
        if '[' in final_key:
            key, index_str = final_key.split('[')
            index = int(index_str.rstrip(']'))

            if key not in current:
                current[key] = []

            while len(current[key]) <= index:
                current[key].append(None)

            current[key][index] = value
        else:
            current[final_key] = value

    def _validate_result(self, template: MappingTemplate, resource: Dict[str, Any]) -> bool:
        """Validate generated FHIR resource."""
        # Basic validation - check required fields
        for rule in template.validation_rules:
            rule_type = rule.get("type")

            if rule_type == "required_field":
                field_path = rule.get("field")
                if not self._get_nested_value(resource, field_path):
                    logger.warning(f"Required field {field_path} is missing")
                    return False

        return True

    def _get_nested_value(self, obj: Dict[str, Any], path: str) -> Any:
        """Get nested value from dictionary using dot notation."""
        parts = path.split('.')
        current = obj

        for part in parts:
            if '[' in part:
                key, index_str = part.split('[')
                index = int(index_str.rstrip(']'))

                if key not in current or not isinstance(current[key], list) or len(current[key]) <= index:
                    return None

                current = current[key][index]
            else:
                if part not in current:
                    return None
                current = current[part]

        return current


class TemplateManager:
    """Main template management service."""

    def __init__(self, templates_path: str = "templates"):
        self.repository = TemplateRepository(templates_path)
        self.engine = TemplateEngine(templates_path)

        # Initialize with built-in templates
        self._initialize_builtin_templates()

    def create_template(self,
                       name: str,
                       resource_type: str,
                       field_mappings: List[Dict[str, Any]],
                       **kwargs) -> MappingTemplate:
        """Create a new template."""

        # Generate metadata
        metadata = TemplateMetadata(
            name=name,
            version="1.0.0",
            author=kwargs.get("author", "system"),
            created_date=time.strftime("%Y-%m-%d"),
            updated_date=time.strftime("%Y-%m-%d"),
            description=kwargs.get("description", f"Template for {resource_type}"),
            tags=kwargs.get("tags", [resource_type.lower()]),
            category=TemplateCategory(kwargs.get("category", "resource_templates")),
            use_cases=kwargs.get("use_cases", ["general"]),
            complexity_level=ComplexityLevel(kwargs.get("complexity", "basic"))
        )

        # Convert field mappings
        mappings = [
            FieldMapping(
                fhir_path=fm["fhir_path"],
                source_expression=fm["source_expression"],
                required=fm.get("required", False),
                transformation_type=fm.get("transformation_type", "direct")
            )
            for fm in field_mappings
        ]

        template = MappingTemplate(
            metadata=metadata,
            parameters=kwargs.get("parameters", []),
            schema_requirements=kwargs.get("schema_requirements", {}),
            fhir_mapping={"resource_type": resource_type},
            field_mappings=mappings,
            validation_rules=kwargs.get("validation_rules", []),
            test_cases=kwargs.get("test_cases", [])
        )

        return template

    def save_template(self, template: MappingTemplate) -> bool:
        """Save template to repository."""
        return self.repository.save_template(template)

    def find_templates(self, **search_params) -> List[MappingTemplate]:
        """Find templates matching search criteria."""
        return self.repository.search_templates(**search_params)

    def get_template(self, template_id: str) -> Optional[MappingTemplate]:
        """Get template by ID."""
        return self.repository.load_template(template_id)

    def apply_template(self,
                      template_id: str,
                      source_data: pd.DataFrame,
                      parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Apply template to source data."""

        template = self.repository.load_template(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")

        return self.engine.apply_template(template, source_data, parameters)

    def get_template_suggestions(self,
                               source_data: pd.DataFrame,
                               target_resource_type: Optional[str] = None) -> List[MappingTemplate]:
        """Get template suggestions based on source data characteristics."""

        # Analyze source data
        column_names = source_data.columns.tolist()
        data_patterns = self._analyze_data_patterns(source_data)

        # Search for matching templates
        suggestions = []

        # Search by resource type if specified
        if target_resource_type:
            templates = self.find_templates(resource_type=target_resource_type)
        else:
            templates = self.repository.search_templates(limit=50)

        # Score templates based on field matching
        for template in templates:
            score = self._calculate_template_match_score(template, column_names, data_patterns)
            if score > 0.3:  # Threshold for relevance
                suggestions.append((template, score))

        # Sort by score
        suggestions.sort(key=lambda x: x[1], reverse=True)

        return [template for template, score in suggestions[:10]]

    def _analyze_data_patterns(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Analyze data patterns in source DataFrame."""
        patterns = {
            "has_id_fields": any("id" in col.lower() for col in data.columns),
            "has_name_fields": any("name" in col.lower() for col in data.columns),
            "has_date_fields": any("date" in col.lower() or "birth" in col.lower() for col in data.columns),
            "has_phone_fields": any("phone" in col.lower() for col in data.columns),
            "has_address_fields": any(addr in col.lower() for col in data.columns for addr in ["address", "street", "city", "state", "zip"]),
            "numeric_columns": data.select_dtypes(include=[np.number]).columns.tolist(),
            "date_columns": data.select_dtypes(include=['datetime64']).columns.tolist(),
            "row_count": len(data)
        }

        return patterns

    def _calculate_template_match_score(self,
                                      template: MappingTemplate,
                                      column_names: List[str],
                                      data_patterns: Dict[str, Any]) -> float:
        """Calculate how well a template matches source data."""

        score = 0.0
        total_mappings = len(template.field_mappings)

        if total_mappings == 0:
            return 0.0

        # Check field name matches
        matched_fields = 0
        for mapping in template.field_mappings:
            # Simple field name matching - can be enhanced with NLP
            for col in column_names:
                if any(word in col.lower() for word in mapping.source_expression.lower().split()):
                    matched_fields += 1
                    break

        field_score = matched_fields / total_mappings
        score += field_score * 0.6

        # Pattern matching bonus
        if data_patterns["has_id_fields"] and any("id" in fm.fhir_path.lower() for fm in template.field_mappings):
            score += 0.1

        if data_patterns["has_name_fields"] and any("name" in fm.fhir_path.lower() for fm in template.field_mappings):
            score += 0.1

        if data_patterns["has_date_fields"] and any("date" in fm.fhir_path.lower() for fm in template.field_mappings):
            score += 0.1

        # Use case relevance
        if "general" in template.metadata.use_cases:
            score += 0.1

        return min(score, 1.0)  # Cap at 1.0

    def _initialize_builtin_templates(self):
        """Initialize built-in templates."""

        # Patient Demographics Template
        patient_template = self.create_template(
            name="Patient Demographics Basic",
            resource_type="Patient",
            description="Basic patient demographics mapping for US Core",
            tags=["patient", "demographics", "us-core"],
            field_mappings=[
                {
                    "fhir_path": "id",
                    "source_expression": "{{ patient_id | sanitize_id }}",
                    "required": True
                },
                {
                    "fhir_path": "identifier[0]",
                    "source_expression": '{"use": "usual", "system": "local", "value": "{{ patient_id }}"}',
                    "transformation_type": "template"
                },
                {
                    "fhir_path": "name[0]",
                    "source_expression": "{{ format_name(first_name, last_name, middle_name) }}",
                    "transformation_type": "template"
                },
                {
                    "fhir_path": "birthDate",
                    "source_expression": "{{ birth_date | to_fhir_date }}"
                },
                {
                    "fhir_path": "gender",
                    "source_expression": "{% if gender|lower in ['m', 'male'] %}male{% elif gender|lower in ['f', 'female'] %}female{% else %}unknown{% endif %}"
                }
            ],
            validation_rules=[
                {"type": "required_field", "field": "id"},
                {"type": "required_field", "field": "name"}
            ]
        )

        self.save_template(patient_template)

        logger.info("Initialized built-in templates")


# Global template manager instance
template_manager = TemplateManager()