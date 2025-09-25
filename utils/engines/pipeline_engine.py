"""
YAML Pipeline Engine for FHIR Transformations
Implements the specification from specs/002-pipeline-templates/spec.md
"""

import os
import sys
import yaml
import json
import time
import asyncio
from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import subprocess
import tempfile

import pandas as pd
from jinja2 import Environment, BaseLoader, select_autoescape
try:
    import structlog
except ImportError:
    import logging as structlog

# Import our other components
from .database_adapter import database_service
from ..validation.validation_engine import validation_engine, ValidationLevel
from ..core.template_manager import template_manager

try:
    logger = structlog.get_logger(__name__)
except:
    logger = structlog.getLogger(__name__)


class PipelineStageType(Enum):
    """Types of pipeline stages."""
    EXTRACT = "extract"
    TRANSFORM = "transform"
    VALIDATE = "validate"
    LOAD = "load"
    CUSTOM = "custom"


class PipelineStatus(Enum):
    """Pipeline execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class PipelineStage:
    """Single pipeline stage definition."""
    name: str
    type: PipelineStageType
    config: Dict[str, Any]
    depends_on: List[str] = field(default_factory=list)
    timeout_seconds: int = 3600
    retry_count: int = 0
    on_failure: str = "stop"  # stop, continue, rollback


@dataclass
class PipelineDefinition:
    """Complete pipeline definition."""
    name: str
    description: str
    version: str
    schedule: Optional[str] = None
    stages: List[PipelineStage] = field(default_factory=list)
    global_config: Dict[str, Any] = field(default_factory=dict)
    error_handling: Dict[str, Any] = field(default_factory=dict)
    notifications: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class PipelineExecution:
    """Pipeline execution instance."""
    execution_id: str
    pipeline_name: str
    status: PipelineStatus
    start_time: float
    end_time: Optional[float] = None
    stage_results: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)


class PipelineStageExecutor:
    """Base class for pipeline stage executors."""

    def __init__(self, pipeline_engine):
        self.pipeline_engine = pipeline_engine
        self.jinja_env = Environment(
            loader=BaseLoader(),
            autoescape=select_autoescape(['html', 'xml'])
        )
        self._register_template_functions()

    def _register_template_functions(self):
        """Register custom template functions."""

        def yesterday():
            """Get yesterday's date."""
            from datetime import datetime, timedelta
            return (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

        def today():
            """Get today's date."""
            from datetime import datetime
            return datetime.now().strftime('%Y-%m-%d')

        def now():
            """Get current timestamp."""
            from datetime import datetime
            return datetime.now().isoformat()

        # Register global functions
        self.jinja_env.globals.update({
            'yesterday': yesterday,
            'today': today,
            'now': now
        })

    async def execute(self, stage: PipelineStage, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a pipeline stage."""
        raise NotImplementedError


class ExtractStageExecutor(PipelineStageExecutor):
    """Executor for data extraction stages."""

    async def execute(self, stage: PipelineStage, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute data extraction stage."""
        config = stage.config
        source_type = config.get("source", "file")

        if source_type == "file":
            return await self._extract_from_file(config, context)
        elif source_type == "database":
            return await self._extract_from_database(config, context)
        elif source_type == "api":
            return await self._extract_from_api(config, context)
        else:
            raise ValueError(f"Unsupported extract source: {source_type}")

    async def _extract_from_file(self, config: Dict, context: Dict) -> Dict[str, Any]:
        """Extract data from file."""
        file_path = config["path"]
        file_format = config.get("format", "csv")

        # Render path template
        template = self.jinja_env.from_string(file_path)
        rendered_path = template.render(**context)

        if file_format == "csv":
            data = pd.read_csv(rendered_path)
        elif file_format == "excel":
            data = pd.read_excel(rendered_path)
        elif file_format == "parquet":
            data = pd.read_parquet(rendered_path)
        elif file_format == "json":
            data = pd.read_json(rendered_path)
        else:
            raise ValueError(f"Unsupported file format: {file_format}")

        logger.info(f"Extracted {len(data)} records from {rendered_path}")

        return {
            "data": data,
            "source_path": rendered_path,
            "record_count": len(data),
            "columns": list(data.columns)
        }

    async def _extract_from_database(self, config: Dict, context: Dict) -> Dict[str, Any]:
        """Extract data from database."""
        query = config["query"]

        # Render query template
        template = self.jinja_env.from_string(query)
        rendered_query = template.render(**context)

        # Execute query using database service
        if not database_service.connected:
            await database_service.initialize()

        result = database_service.adapter.execute_query(rendered_query)

        logger.info(f"Extracted {result.row_count} records from database")

        return {
            "data": result.data,
            "query": rendered_query,
            "record_count": result.row_count,
            "execution_time_ms": result.execution_time_ms
        }

    async def _extract_from_api(self, config: Dict, context: Dict) -> Dict[str, Any]:
        """Extract data from API endpoint."""
        import aiohttp

        url = config["url"]
        method = config.get("method", "GET")
        headers = config.get("headers", {})

        # Render URL template
        template = self.jinja_env.from_string(url)
        rendered_url = template.render(**context)

        async with aiohttp.ClientSession() as session:
            async with session.request(method, rendered_url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()

                    # Convert to DataFrame if possible
                    if isinstance(data, list):
                        df = pd.DataFrame(data)
                    else:
                        df = pd.json_normalize(data)

                    logger.info(f"Extracted {len(df)} records from API")

                    return {
                        "data": df,
                        "source_url": rendered_url,
                        "record_count": len(df),
                        "status_code": response.status
                    }
                else:
                    raise RuntimeError(f"API request failed with status {response.status}")


class TransformStageExecutor(PipelineStageExecutor):
    """Executor for data transformation stages."""

    async def execute(self, stage: PipelineStage, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute transformation stage."""
        config = stage.config
        transform_type = config.get("type", "mapping")

        if transform_type == "mapping":
            return await self._execute_mapping_transform(config, context)
        elif transform_type == "sql":
            return await self._execute_sql_transform(config, context)
        elif transform_type == "template":
            return await self._execute_template_transform(config, context)
        else:
            raise ValueError(f"Unsupported transform type: {transform_type}")

    async def _execute_mapping_transform(self, config: Dict, context: Dict) -> Dict[str, Any]:
        """Execute mapping-based transformation."""
        mapping_file = config.get("mapping_file")
        template_id = config.get("template_id")

        # Get source data from context
        input_data = context.get("data")
        if input_data is None:
            raise ValueError("No input data found in context")

        if mapping_file:
            # Load mapping configuration
            with open(mapping_file, 'r') as f:
                mapping_config = yaml.safe_load(f)

            # Apply mapping (simplified - would use enhanced_mapper.py in practice)
            transformed_data = self._apply_yaml_mapping(input_data, mapping_config)

        elif template_id:
            # Use template manager
            template_params = config.get("parameters", {})
            fhir_resources = template_manager.apply_template(template_id, input_data, template_params)
            transformed_data = pd.DataFrame(fhir_resources)

        else:
            raise ValueError("Either mapping_file or template_id must be specified")

        logger.info(f"Transformed {len(transformed_data)} records")

        return {
            "data": transformed_data,
            "record_count": len(transformed_data),
            "transformation_type": "mapping"
        }

    async def _execute_sql_transform(self, config: Dict, context: Dict) -> Dict[str, Any]:
        """Execute SQL-based transformation."""
        sql_query = config["query"]
        input_table = config.get("input_table", "temp_input")

        # Load input data to database
        input_data = context.get("data")
        if input_data is not None:
            database_service.adapter.load_data(input_data, input_table, mode="replace")

        # Render SQL template
        template = self.jinja_env.from_string(sql_query)
        rendered_query = template.render(**context, input_table=input_table)

        # Execute query
        result = database_service.adapter.execute_query(rendered_query)

        logger.info(f"SQL transform produced {result.row_count} records")

        return {
            "data": result.data,
            "record_count": result.row_count,
            "sql_query": rendered_query,
            "execution_time_ms": result.execution_time_ms
        }

    async def _execute_template_transform(self, config: Dict, context: Dict) -> Dict[str, Any]:
        """Execute template-based transformation."""
        template_engine = config.get("template_engine", "jinja2")
        template_content = config.get("template")
        template_file = config.get("template_file")

        if template_file:
            with open(template_file, 'r') as f:
                template_content = f.read()

        if not template_content:
            raise ValueError("Template content or file must be specified")

        input_data = context.get("data")
        if input_data is None:
            raise ValueError("No input data found in context")

        # Apply template to each row
        results = []
        template_obj = self.jinja_env.from_string(template_content)

        for _, row in input_data.iterrows():
            row_context = {**context, **row.to_dict()}
            result = template_obj.render(**row_context)

            # Try to parse as JSON
            try:
                parsed_result = json.loads(result)
                results.append(parsed_result)
            except json.JSONDecodeError:
                results.append({"output": result})

        transformed_data = pd.DataFrame(results)

        logger.info(f"Template transform produced {len(results)} records")

        return {
            "data": transformed_data,
            "record_count": len(results),
            "template_engine": template_engine
        }

    def _apply_yaml_mapping(self, data: pd.DataFrame, mapping_config: Dict) -> pd.DataFrame:
        """Apply YAML mapping configuration to data."""
        # Simplified implementation - in practice would use enhanced_mapper.py
        results = []

        for _, row in data.iterrows():
            result = {}

            # Apply field mappings
            for mapping in mapping_config.get("mappings", []):
                for rule in mapping.get("rules", []):
                    field = rule["field"]
                    expression = rule["expression"]

                    # Simple template rendering
                    template = self.jinja_env.from_string(expression)
                    value = template.render(**row.to_dict())

                    # Set nested value
                    self._set_nested_field(result, field, value)

            results.append(result)

        return pd.DataFrame(results)

    def _set_nested_field(self, obj: Dict, field_path: str, value: Any):
        """Set nested field value."""
        parts = field_path.split('.')
        current = obj

        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]

        current[parts[-1]] = value


class ValidateStageExecutor(PipelineStageExecutor):
    """Executor for validation stages."""

    async def execute(self, stage: PipelineStage, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute validation stage."""
        config = stage.config
        validation_type = config.get("type", "fhir")

        if validation_type == "fhir":
            return await self._execute_fhir_validation(config, context)
        elif validation_type == "schema":
            return await self._execute_schema_validation(config, context)
        elif validation_type == "business_rules":
            return await self._execute_business_rules_validation(config, context)
        else:
            raise ValueError(f"Unsupported validation type: {validation_type}")

    async def _execute_fhir_validation(self, config: Dict, context: Dict) -> Dict[str, Any]:
        """Execute FHIR validation."""
        input_data = context.get("data")
        if input_data is None:
            raise ValueError("No input data found in context")

        profile = config.get("profile", "")
        validation_level = ValidationLevel(config.get("level", "standard"))
        strict_mode = config.get("strict_mode", False)

        validation_results = []
        valid_resources = []
        invalid_resources = []

        for _, row in input_data.iterrows():
            if "fhir_resource" in row:
                resource = row["fhir_resource"]

                # Parse if string
                if isinstance(resource, str):
                    try:
                        resource = json.loads(resource)
                    except json.JSONDecodeError:
                        continue

                # Validate resource
                report = await validation_engine.validate_resource(
                    resource, profile, validation_level
                )

                validation_results.append(report)

                if report.is_valid:
                    valid_resources.append(resource)
                elif not strict_mode:
                    # Include warnings in non-strict mode
                    valid_resources.append(resource)
                else:
                    invalid_resources.append({
                        "resource": resource,
                        "errors": [r.message for r in report.results if r.severity.value == "error"]
                    })

        validation_summary = {
            "total_resources": len(validation_results),
            "valid_resources": len(valid_resources),
            "invalid_resources": len(invalid_resources),
            "validation_rate": len(valid_resources) / max(1, len(validation_results)) * 100
        }

        logger.info(f"FHIR validation: {validation_summary['valid_resources']}/{validation_summary['total_resources']} resources valid")

        return {
            "data": pd.DataFrame(valid_resources) if valid_resources else pd.DataFrame(),
            "validation_results": validation_results,
            "validation_summary": validation_summary,
            "invalid_resources": invalid_resources
        }

    async def _execute_schema_validation(self, config: Dict, context: Dict) -> Dict[str, Any]:
        """Execute schema validation."""
        # Simplified schema validation implementation
        input_data = context.get("data")
        schema = config.get("schema", {})
        required_fields = schema.get("required_fields", [])

        validation_errors = []
        valid_records = []

        for idx, row in input_data.iterrows():
            row_errors = []

            # Check required fields
            for field in required_fields:
                if field not in row or pd.isna(row[field]):
                    row_errors.append(f"Missing required field: {field}")

            if not row_errors:
                valid_records.append(row.to_dict())
            else:
                validation_errors.append({
                    "row_index": idx,
                    "errors": row_errors
                })

        logger.info(f"Schema validation: {len(valid_records)}/{len(input_data)} records valid")

        return {
            "data": pd.DataFrame(valid_records),
            "validation_errors": validation_errors,
            "validation_summary": {
                "total_records": len(input_data),
                "valid_records": len(valid_records),
                "error_records": len(validation_errors)
            }
        }

    async def _execute_business_rules_validation(self, config: Dict, context: Dict) -> Dict[str, Any]:
        """Execute business rules validation."""
        # Placeholder for business rules validation
        input_data = context.get("data")
        rules = config.get("rules", [])

        # Simple rule engine implementation
        valid_records = []
        rule_violations = []

        for idx, row in input_data.iterrows():
            violations = []

            for rule in rules:
                rule_name = rule["name"]
                condition = rule["condition"]

                # Simple condition evaluation (in practice, use a proper rule engine)
                try:
                    # This is a simplified example - real implementation would be more robust
                    if not eval(condition, {}, row.to_dict()):
                        violations.append(f"Rule violation: {rule_name}")
                except Exception as e:
                    violations.append(f"Rule evaluation error: {rule_name} - {str(e)}")

            if not violations:
                valid_records.append(row.to_dict())
            else:
                rule_violations.append({
                    "row_index": idx,
                    "violations": violations
                })

        logger.info(f"Business rules validation: {len(valid_records)}/{len(input_data)} records valid")

        return {
            "data": pd.DataFrame(valid_records),
            "rule_violations": rule_violations,
            "validation_summary": {
                "total_records": len(input_data),
                "valid_records": len(valid_records),
                "violation_records": len(rule_violations)
            }
        }


class LoadStageExecutor(PipelineStageExecutor):
    """Executor for data loading stages."""

    async def execute(self, stage: PipelineStage, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute load stage."""
        config = stage.config
        destination_type = config.get("destination", "file")

        if destination_type == "file":
            return await self._load_to_file(config, context)
        elif destination_type == "database":
            return await self._load_to_database(config, context)
        elif destination_type == "fhir_server":
            return await self._load_to_fhir_server(config, context)
        else:
            raise ValueError(f"Unsupported load destination: {destination_type}")

    async def _load_to_file(self, config: Dict, context: Dict) -> Dict[str, Any]:
        """Load data to file."""
        input_data = context.get("data")
        if input_data is None:
            raise ValueError("No input data found in context")

        output_path = config["path"]
        output_format = config.get("format", "json")

        # Render path template
        template = self.jinja_env.from_string(output_path)
        rendered_path = template.render(**context)

        # Ensure output directory exists
        os.makedirs(os.path.dirname(rendered_path), exist_ok=True)

        if output_format == "json":
            input_data.to_json(rendered_path, orient="records", indent=2)
        elif output_format == "ndjson":
            input_data.to_json(rendered_path, orient="records", lines=True)
        elif output_format == "csv":
            input_data.to_csv(rendered_path, index=False)
        elif output_format == "parquet":
            input_data.to_parquet(rendered_path, index=False)
        else:
            raise ValueError(f"Unsupported output format: {output_format}")

        logger.info(f"Loaded {len(input_data)} records to {rendered_path}")

        return {
            "output_path": rendered_path,
            "record_count": len(input_data),
            "format": output_format
        }

    async def _load_to_database(self, config: Dict, context: Dict) -> Dict[str, Any]:
        """Load data to database."""
        input_data = context.get("data")
        table_name = config["table"]
        mode = config.get("mode", "replace")

        success = database_service.adapter.load_data(input_data, table_name, mode)

        if not success:
            raise RuntimeError(f"Failed to load data to table {table_name}")

        logger.info(f"Loaded {len(input_data)} records to database table {table_name}")

        return {
            "table_name": table_name,
            "record_count": len(input_data),
            "mode": mode
        }

    async def _load_to_fhir_server(self, config: Dict, context: Dict) -> Dict[str, Any]:
        """Load FHIR resources to FHIR server."""
        import aiohttp

        input_data = context.get("data")
        endpoint = config["endpoint"]
        auth_type = config.get("auth", "none")

        # Prepare headers
        headers = {"Content-Type": "application/fhir+json"}

        if auth_type == "bearer":
            token = config.get("token")
            headers["Authorization"] = f"Bearer {token}"

        uploaded_count = 0
        failed_count = 0

        async with aiohttp.ClientSession() as session:
            for _, row in input_data.iterrows():
                resource = row.get("fhir_resource") if "fhir_resource" in row else row.to_dict()

                if isinstance(resource, str):
                    resource = json.loads(resource)

                try:
                    resource_type = resource.get("resourceType")
                    resource_id = resource.get("id")

                    url = f"{endpoint}/{resource_type}"
                    if resource_id:
                        url += f"/{resource_id}"

                    async with session.put(url, json=resource, headers=headers) as response:
                        if response.status in [200, 201]:
                            uploaded_count += 1
                        else:
                            failed_count += 1
                            logger.warning(f"Failed to upload resource: {response.status}")

                except Exception as e:
                    failed_count += 1
                    logger.error(f"Error uploading resource: {str(e)}")

        logger.info(f"Uploaded {uploaded_count} resources to FHIR server, {failed_count} failed")

        return {
            "endpoint": endpoint,
            "uploaded_count": uploaded_count,
            "failed_count": failed_count,
            "success_rate": uploaded_count / max(1, uploaded_count + failed_count) * 100
        }


class PipelineEngine:
    """Main pipeline execution engine."""

    def __init__(self):
        self.stage_executors = {
            PipelineStageType.EXTRACT: ExtractStageExecutor(self),
            PipelineStageType.TRANSFORM: TransformStageExecutor(self),
            PipelineStageType.VALIDATE: ValidateStageExecutor(self),
            PipelineStageType.LOAD: LoadStageExecutor(self),
        }

        self.executions = {}  # Store execution history

    def load_pipeline(self, pipeline_file: str) -> PipelineDefinition:
        """Load pipeline definition from YAML file."""
        with open(pipeline_file, 'r') as f:
            pipeline_data = yaml.safe_load(f)

        # Convert stages
        stages = []
        for stage_data in pipeline_data.get("stages", []):
            stage = PipelineStage(
                name=stage_data["name"],
                type=PipelineStageType(stage_data["type"]),
                config=stage_data.get("config", {}),
                depends_on=stage_data.get("depends_on", []),
                timeout_seconds=stage_data.get("timeout_seconds", 3600),
                retry_count=stage_data.get("retry_count", 0),
                on_failure=stage_data.get("on_failure", "stop")
            )
            stages.append(stage)

        pipeline = PipelineDefinition(
            name=pipeline_data["name"],
            description=pipeline_data.get("description", ""),
            version=pipeline_data.get("version", "1.0.0"),
            schedule=pipeline_data.get("schedule"),
            stages=stages,
            global_config=pipeline_data.get("global_config", {}),
            error_handling=pipeline_data.get("error_handling", {}),
            notifications=pipeline_data.get("notifications", [])
        )

        return pipeline

    async def execute_pipeline(self, pipeline: PipelineDefinition, context: Dict[str, Any] = None) -> PipelineExecution:
        """Execute a pipeline."""
        import uuid

        execution_id = str(uuid.uuid4())
        context = context or {}

        # Add global config to context
        context.update(pipeline.global_config)

        execution = PipelineExecution(
            execution_id=execution_id,
            pipeline_name=pipeline.name,
            status=PipelineStatus.RUNNING,
            start_time=time.time()
        )

        self.executions[execution_id] = execution

        try:
            logger.info(f"Starting pipeline execution: {pipeline.name}")

            # Build dependency graph
            stage_deps = {stage.name: stage.depends_on for stage in pipeline.stages}
            execution_order = self._topological_sort(stage_deps)

            # Execute stages in order
            for stage_name in execution_order:
                stage = next(s for s in pipeline.stages if s.name == stage_name)

                logger.info(f"Executing stage: {stage_name}")
                stage_start = time.time()

                try:
                    # Execute stage with timeout
                    stage_result = await asyncio.wait_for(
                        self._execute_stage(stage, context),
                        timeout=stage.timeout_seconds
                    )

                    stage_duration = time.time() - stage_start
                    execution.stage_results[stage_name] = {
                        **stage_result,
                        "duration_seconds": stage_duration,
                        "status": "completed"
                    }

                    # Update context with stage results
                    context.update(stage_result)

                    logger.info(f"Stage {stage_name} completed in {stage_duration:.2f}s")

                except Exception as e:
                    stage_duration = time.time() - stage_start
                    error_msg = str(e)

                    execution.stage_results[stage_name] = {
                        "status": "failed",
                        "error": error_msg,
                        "duration_seconds": stage_duration
                    }

                    logger.error(f"Stage {stage_name} failed: {error_msg}")

                    # Handle failure
                    if stage.on_failure == "stop":
                        raise
                    elif stage.on_failure == "continue":
                        continue
                    elif stage.on_failure == "rollback":
                        await self._rollback_pipeline(execution)
                        raise

            execution.status = PipelineStatus.COMPLETED
            execution.end_time = time.time()

            # Calculate metrics
            total_duration = execution.end_time - execution.start_time
            execution.metrics = {
                "total_duration_seconds": total_duration,
                "stages_completed": len([s for s in execution.stage_results.values() if s.get("status") == "completed"]),
                "stages_failed": len([s for s in execution.stage_results.values() if s.get("status") == "failed"]),
                "total_records_processed": sum(s.get("record_count", 0) for s in execution.stage_results.values())
            }

            logger.info(f"Pipeline {pipeline.name} completed in {total_duration:.2f}s")

        except Exception as e:
            execution.status = PipelineStatus.FAILED
            execution.end_time = time.time()
            execution.error_message = str(e)

            logger.error(f"Pipeline {pipeline.name} failed: {str(e)}")

            # Send failure notifications
            await self._send_notifications(pipeline, execution)

        return execution

    async def _execute_stage(self, stage: PipelineStage, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single pipeline stage."""
        executor = self.stage_executors.get(stage.type)
        if not executor:
            raise ValueError(f"No executor found for stage type: {stage.type}")

        # Retry logic
        for attempt in range(stage.retry_count + 1):
            try:
                return await executor.execute(stage, context)
            except Exception as e:
                if attempt < stage.retry_count:
                    logger.warning(f"Stage {stage.name} attempt {attempt + 1} failed, retrying: {str(e)}")
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise

    def _topological_sort(self, dependencies: Dict[str, List[str]]) -> List[str]:
        """Perform topological sort for stage dependencies."""
        from collections import defaultdict, deque

        # Build graph
        graph = defaultdict(list)
        in_degree = defaultdict(int)

        for node in dependencies:
            in_degree[node] = 0

        for node, deps in dependencies.items():
            for dep in deps:
                graph[dep].append(node)
                in_degree[node] += 1

        # Kahn's algorithm
        queue = deque([node for node in in_degree if in_degree[node] == 0])
        result = []

        while queue:
            node = queue.popleft()
            result.append(node)

            for neighbor in graph[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(result) != len(dependencies):
            raise ValueError("Circular dependency detected in pipeline stages")

        return result

    async def _rollback_pipeline(self, execution: PipelineExecution):
        """Rollback pipeline changes."""
        logger.info(f"Rolling back pipeline execution: {execution.execution_id}")
        # Implementation would depend on stage types and what needs to be rolled back

    async def _send_notifications(self, pipeline: PipelineDefinition, execution: PipelineExecution):
        """Send pipeline notifications."""
        for notification in pipeline.notifications:
            try:
                if notification["type"] == "email":
                    # Email notification implementation
                    pass
                elif notification["type"] == "slack":
                    # Slack notification implementation
                    pass
            except Exception as e:
                logger.error(f"Failed to send notification: {str(e)}")

    def get_execution(self, execution_id: str) -> Optional[PipelineExecution]:
        """Get pipeline execution by ID."""
        return self.executions.get(execution_id)

    def list_executions(self, pipeline_name: Optional[str] = None) -> List[PipelineExecution]:
        """List pipeline executions."""
        executions = list(self.executions.values())

        if pipeline_name:
            executions = [e for e in executions if e.pipeline_name == pipeline_name]

        return sorted(executions, key=lambda e: e.start_time, reverse=True)


# Global pipeline engine instance
pipeline_engine = PipelineEngine()