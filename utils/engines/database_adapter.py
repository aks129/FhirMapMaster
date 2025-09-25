"""
Unified Database Adapter for DuckDB and Databricks
Implements the specification from specs/004-database-integration/spec.md
"""

import os
import sys
import json
import time
import asyncio
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass
from enum import Enum
from abc import ABC, abstractmethod
import importlib.util

import pandas as pd
import numpy as np
try:
    import structlog
except ImportError:
    import logging as structlog

try:
    logger = structlog.get_logger(__name__)
except:
    logger = structlog.getLogger(__name__)


class DatabasePlatform(Enum):
    """Supported database platforms."""
    DUCKDB = "duckdb"
    DATABRICKS = "databricks"
    UNKNOWN = "unknown"


@dataclass
class QueryResult:
    """Result of a database query."""
    data: pd.DataFrame
    execution_time_ms: float
    row_count: int
    metadata: Dict[str, Any]
    platform: DatabasePlatform


@dataclass
class PerformanceMetrics:
    """Performance metrics for database operations."""
    query_time_ms: float
    memory_usage_mb: float
    rows_processed: int
    cache_hit: bool = False


class DatabaseInterface(ABC):
    """Abstract interface for database adapters."""

    @abstractmethod
    def connect(self) -> bool:
        """Establish database connection."""
        pass

    @abstractmethod
    def execute_query(self, query: str, parameters: Optional[Dict] = None) -> QueryResult:
        """Execute a SQL query."""
        pass

    @abstractmethod
    def load_data(self, data: pd.DataFrame, table_name: str, mode: str = "replace") -> bool:
        """Load DataFrame into database table."""
        pass

    @abstractmethod
    def optimize_for_fhir(self) -> None:
        """Apply FHIR-specific optimizations."""
        pass

    @abstractmethod
    def get_platform_info(self) -> Dict[str, Any]:
        """Get platform information."""
        pass


class DuckDBAdapter(DatabaseInterface):
    """DuckDB adapter for local development and processing."""

    def __init__(self, database_path: str = "data/fhir_mappings.db"):
        self.database_path = database_path
        self.connection = None
        self.fhir_functions_loaded = False

    def connect(self) -> bool:
        """Establish DuckDB connection."""
        try:
            import duckdb

            # Create database directory if needed
            os.makedirs(os.path.dirname(self.database_path), exist_ok=True)

            self.connection = duckdb.connect(self.database_path)

            # Install and load extensions
            self._install_extensions()

            # Apply FHIR optimizations
            self.optimize_for_fhir()

            logger.info(f"Connected to DuckDB: {self.database_path}")
            return True

        except ImportError:
            logger.error("DuckDB not installed. Run: pip install duckdb")
            return False
        except Exception as e:
            logger.error(f"DuckDB connection failed: {str(e)}")
            return False

    def _install_extensions(self):
        """Install required DuckDB extensions."""
        extensions = ['httpfs', 'json', 'parquet', 'spatial']

        for ext in extensions:
            try:
                self.connection.execute(f"INSTALL {ext};")
                self.connection.execute(f"LOAD {ext};")
                logger.debug(f"Loaded DuckDB extension: {ext}")
            except Exception as e:
                logger.warning(f"Failed to load extension {ext}: {str(e)}")

    def execute_query(self, query: str, parameters: Optional[Dict] = None) -> QueryResult:
        """Execute SQL query in DuckDB."""
        if not self.connection:
            raise RuntimeError("Not connected to DuckDB")

        start_time = time.time()

        try:
            if parameters:
                result = self.connection.execute(query, parameters).fetchdf()
            else:
                result = self.connection.execute(query).fetchdf()

            execution_time = (time.time() - start_time) * 1000

            return QueryResult(
                data=result,
                execution_time_ms=execution_time,
                row_count=len(result),
                metadata={
                    "query_type": self._detect_query_type(query),
                    "table_scanned": self._extract_tables(query)
                },
                platform=DatabasePlatform.DUCKDB
            )

        except Exception as e:
            logger.error(f"DuckDB query failed: {str(e)}")
            raise

    def load_data(self, data: pd.DataFrame, table_name: str, mode: str = "replace") -> bool:
        """Load DataFrame into DuckDB table."""
        try:
            if mode == "replace":
                self.connection.execute(f"DROP TABLE IF EXISTS {table_name}")

            # Register DataFrame as view first
            self.connection.register(f"temp_{table_name}", data)

            # Create table from view
            self.connection.execute(f"""
                CREATE TABLE {table_name} AS
                SELECT * FROM temp_{table_name}
            """)

            # Unregister temporary view
            self.connection.unregister(f"temp_{table_name}")

            logger.info(f"Loaded {len(data)} rows into {table_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to load data into {table_name}: {str(e)}")
            return False

    def optimize_for_fhir(self) -> None:
        """Apply DuckDB optimizations for FHIR processing."""
        try:
            # Set memory limit
            self.connection.execute("SET memory_limit = '8GB';")

            # Set thread count
            self.connection.execute("SET threads TO 8;")

            # Enable parallelism
            self.connection.execute("SET enable_progress_bar = true;")

            # Load FHIR helper functions
            self._load_fhir_functions()

            logger.info("Applied DuckDB FHIR optimizations")

        except Exception as e:
            logger.error(f"Failed to apply optimizations: {str(e)}")

    def _load_fhir_functions(self):
        """Load FHIR-specific functions."""
        if self.fhir_functions_loaded:
            return

        try:
            # Function to create FHIR Patient resource
            patient_function = """
            CREATE OR REPLACE FUNCTION to_fhir_patient(
                patient_id VARCHAR,
                first_name VARCHAR,
                last_name VARCHAR,
                birth_date DATE,
                gender VARCHAR
            ) RETURNS JSON AS
            $$
            {
                "resourceType": "Patient",
                "id": patient_id,
                "name": [
                    {
                        "use": "official",
                        "given": [first_name],
                        "family": last_name
                    }
                ],
                "birthDate": birth_date::VARCHAR,
                "gender": CASE
                    WHEN lower(gender) IN ('m', 'male') THEN 'male'
                    WHEN lower(gender) IN ('f', 'female') THEN 'female'
                    ELSE 'unknown'
                END
            }
            $$;
            """
            self.connection.execute(patient_function)

            # Function to validate FHIR date
            date_function = """
            CREATE OR REPLACE FUNCTION validate_fhir_date(date_str VARCHAR)
            RETURNS BOOLEAN AS
            $$
                SELECT regexp_matches(date_str, '^\\d{4}(-\\d{2}(-\\d{2})?)?$')
            $$;
            """
            self.connection.execute(date_function)

            # Function to create FHIR identifier
            identifier_function = """
            CREATE OR REPLACE FUNCTION to_fhir_identifier(
                system VARCHAR,
                value VARCHAR,
                use_type VARCHAR DEFAULT 'usual'
            ) RETURNS JSON AS
            $$
            {
                "use": use_type,
                "system": system,
                "value": value
            }
            $$;
            """
            self.connection.execute(identifier_function)

            self.fhir_functions_loaded = True
            logger.info("Loaded FHIR helper functions")

        except Exception as e:
            logger.error(f"Failed to load FHIR functions: {str(e)}")

    def create_fhir_transformation_views(self, table_name: str, resource_type: str) -> bool:
        """Create transformation views for FHIR resources."""
        try:
            if resource_type == "Patient":
                view_sql = f"""
                CREATE OR REPLACE VIEW {table_name}_fhir AS
                SELECT
                    to_fhir_patient(
                        patient_id,
                        first_name,
                        last_name,
                        birth_date::DATE,
                        gender
                    ) as fhir_resource,
                    patient_id as source_id
                FROM {table_name}
                WHERE patient_id IS NOT NULL
                """

            elif resource_type == "Observation":
                view_sql = f"""
                CREATE OR REPLACE VIEW {table_name}_fhir AS
                SELECT
                    {{
                        "resourceType": "Observation",
                        "id": observation_id,
                        "status": "final",
                        "code": {{
                            "coding": [{{
                                "system": "http://loinc.org",
                                "code": loinc_code,
                                "display": test_name
                            }}]
                        }},
                        "valueQuantity": {{
                            "value": test_value,
                            "unit": unit
                        }},
                        "subject": {{
                            "reference": "Patient/" || patient_id
                        }}
                    }}::JSON as fhir_resource,
                    observation_id as source_id
                FROM {table_name}
                WHERE observation_id IS NOT NULL
                """

            self.connection.execute(view_sql)
            logger.info(f"Created FHIR transformation view for {resource_type}")
            return True

        except Exception as e:
            logger.error(f"Failed to create transformation view: {str(e)}")
            return False

    def _detect_query_type(self, query: str) -> str:
        """Detect the type of SQL query."""
        query_lower = query.lower().strip()
        if query_lower.startswith("select"):
            return "SELECT"
        elif query_lower.startswith("insert"):
            return "INSERT"
        elif query_lower.startswith("update"):
            return "UPDATE"
        elif query_lower.startswith("create"):
            return "CREATE"
        else:
            return "OTHER"

    def _extract_tables(self, query: str) -> List[str]:
        """Extract table names from query (simple implementation)."""
        import re
        # Simple regex to find table names - can be enhanced
        tables = re.findall(r'FROM\s+(\w+)', query, re.IGNORECASE)
        tables.extend(re.findall(r'JOIN\s+(\w+)', query, re.IGNORECASE))
        return list(set(tables))

    def get_platform_info(self) -> Dict[str, Any]:
        """Get DuckDB platform information."""
        try:
            version_result = self.connection.execute("SELECT version();").fetchone()
            return {
                "platform": "DuckDB",
                "version": version_result[0] if version_result else "unknown",
                "database_path": self.database_path,
                "extensions": ["httpfs", "json", "parquet", "spatial"]
            }
        except:
            return {
                "platform": "DuckDB",
                "version": "unknown",
                "database_path": self.database_path
            }


class DataBricksAdapter(DatabaseInterface):
    """Databricks adapter for enterprise-scale processing."""

    def __init__(self,
                 server_hostname: Optional[str] = None,
                 http_path: Optional[str] = None,
                 access_token: Optional[str] = None):

        self.server_hostname = server_hostname or os.environ.get('DATABRICKS_SERVER_HOSTNAME')
        self.http_path = http_path or os.environ.get('DATABRICKS_HTTP_PATH')
        self.access_token = access_token or os.environ.get('DATABRICKS_ACCESS_TOKEN')

        self.connection = None
        self.spark_session = None

    def connect(self) -> bool:
        """Establish Databricks connection."""
        try:
            # Check for Databricks runtime environment
            if 'DATABRICKS_RUNTIME_VERSION' in os.environ:
                # Running in Databricks - use Spark session
                from pyspark.sql import SparkSession
                self.spark_session = SparkSession.builder.getOrCreate()
                logger.info("Connected to Databricks via Spark session")
                return True

            # External connection via SQL connector
            from databricks.sql import connect

            if not all([self.server_hostname, self.http_path, self.access_token]):
                logger.error("Databricks connection parameters missing")
                return False

            self.connection = connect(
                server_hostname=self.server_hostname,
                http_path=self.http_path,
                access_token=self.access_token
            )

            logger.info("Connected to Databricks via SQL connector")
            return True

        except ImportError:
            logger.error("Databricks SQL connector not installed")
            return False
        except Exception as e:
            logger.error(f"Databricks connection failed: {str(e)}")
            return False

    def execute_query(self, query: str, parameters: Optional[Dict] = None) -> QueryResult:
        """Execute query in Databricks."""
        start_time = time.time()

        try:
            if self.spark_session:
                # Use Spark SQL
                result_df = self.spark_session.sql(query).toPandas()
            else:
                # Use SQL connector
                cursor = self.connection.cursor()
                cursor.execute(query, parameters or {})

                # Fetch results and convert to DataFrame
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                result_df = pd.DataFrame(rows, columns=columns)
                cursor.close()

            execution_time = (time.time() - start_time) * 1000

            return QueryResult(
                data=result_df,
                execution_time_ms=execution_time,
                row_count=len(result_df),
                metadata={
                    "execution_engine": "spark" if self.spark_session else "sql_connector",
                    "cluster_info": self._get_cluster_info()
                },
                platform=DatabasePlatform.DATABRICKS
            )

        except Exception as e:
            logger.error(f"Databricks query failed: {str(e)}")
            raise

    def load_data(self, data: pd.DataFrame, table_name: str, mode: str = "replace") -> bool:
        """Load DataFrame into Databricks table."""
        try:
            if self.spark_session:
                # Convert to Spark DataFrame
                spark_df = self.spark_session.createDataFrame(data)

                # Write to Delta table
                writer = spark_df.write.mode(mode)
                if mode == "replace":
                    writer.option("overwriteSchema", "true")

                writer.saveAsTable(table_name)

                logger.info(f"Loaded {len(data)} rows into Databricks table {table_name}")
                return True
            else:
                # Use SQL connector - more limited
                logger.warning("Data loading via SQL connector not fully supported")
                return False

        except Exception as e:
            logger.error(f"Failed to load data into Databricks: {str(e)}")
            return False

    def optimize_for_fhir(self) -> None:
        """Apply Databricks optimizations for FHIR processing."""
        try:
            if self.spark_session:
                spark_conf = self.spark_session.conf

                # Enable adaptive query execution
                spark_conf.set("spark.sql.adaptive.enabled", "true")
                spark_conf.set("spark.sql.adaptive.coalescePartitions.enabled", "true")
                spark_conf.set("spark.sql.adaptive.skewJoin.enabled", "true")

                # Enable cost-based optimizer
                spark_conf.set("spark.sql.cbo.enabled", "true")

                # Set memory fractions for FHIR processing
                spark_conf.set("spark.sql.adaptive.advisoryPartitionSizeInBytes", "134217728")  # 128MB

                logger.info("Applied Databricks FHIR optimizations")

        except Exception as e:
            logger.error(f"Failed to apply Databricks optimizations: {str(e)}")

    def create_fhir_transformation_functions(self) -> bool:
        """Create UDFs for FHIR transformations."""
        try:
            if not self.spark_session:
                return False

            from pyspark.sql.functions import udf
            from pyspark.sql.types import StringType
            import json

            def to_fhir_patient(patient_id, first_name, last_name, birth_date, gender):
                """Create FHIR Patient resource."""
                return json.dumps({
                    "resourceType": "Patient",
                    "id": patient_id,
                    "name": [{
                        "use": "official",
                        "given": [first_name],
                        "family": last_name
                    }],
                    "birthDate": str(birth_date) if birth_date else None,
                    "gender": "male" if gender and gender.lower() in ['m', 'male']
                             else "female" if gender and gender.lower() in ['f', 'female']
                             else "unknown"
                })

            # Register UDF
            self.spark_session.udf.register("to_fhir_patient", to_fhir_patient, StringType())

            logger.info("Created FHIR transformation functions")
            return True

        except Exception as e:
            logger.error(f"Failed to create FHIR functions: {str(e)}")
            return False

    def _get_cluster_info(self) -> Dict[str, Any]:
        """Get Databricks cluster information."""
        try:
            if self.spark_session:
                return {
                    "spark_version": self.spark_session.version,
                    "app_name": self.spark_session.sparkContext.appName,
                    "master": self.spark_session.sparkContext.master
                }
        except:
            pass

        return {"cluster_info": "unavailable"}

    def get_platform_info(self) -> Dict[str, Any]:
        """Get Databricks platform information."""
        return {
            "platform": "Databricks",
            "runtime_version": os.environ.get('DATABRICKS_RUNTIME_VERSION', 'unknown'),
            "cluster_info": self._get_cluster_info(),
            "connection_type": "spark" if self.spark_session else "sql_connector"
        }


class DatabaseAdapterFactory:
    """Factory for creating database adapters."""

    @staticmethod
    def detect_platform() -> DatabasePlatform:
        """Auto-detect the current database platform."""

        # Check for Databricks runtime
        if 'DATABRICKS_RUNTIME_VERSION' in os.environ:
            return DatabasePlatform.DATABRICKS

        # Check for Databricks connection parameters
        databricks_params = [
            os.environ.get('DATABRICKS_SERVER_HOSTNAME'),
            os.environ.get('DATABRICKS_HTTP_PATH'),
            os.environ.get('DATABRICKS_ACCESS_TOKEN')
        ]
        if all(databricks_params):
            return DatabasePlatform.DATABRICKS

        # Check if DuckDB is available
        if importlib.util.find_spec('duckdb'):
            return DatabasePlatform.DUCKDB

        return DatabasePlatform.UNKNOWN

    @staticmethod
    def create_adapter(platform: Optional[DatabasePlatform] = None) -> DatabaseInterface:
        """Create appropriate database adapter."""

        if platform is None:
            platform = DatabaseAdapterFactory.detect_platform()

        if platform == DatabasePlatform.DUCKDB:
            return DuckDBAdapter()
        elif platform == DatabasePlatform.DATABRICKS:
            return DataBricksAdapter()
        else:
            raise RuntimeError(f"Unsupported database platform: {platform}")


class UnifiedDatabaseService:
    """Unified service for database operations across platforms."""

    def __init__(self):
        self.platform = DatabaseAdapterFactory.detect_platform()
        self.adapter = DatabaseAdapterFactory.create_adapter(self.platform)
        self.connected = False

    def initialize(self) -> bool:
        """Initialize the database service."""
        self.connected = self.adapter.connect()
        if self.connected:
            logger.info(f"Initialized database service on {self.platform.value}")
        return self.connected

    def execute_fhir_transformation(self,
                                   source_table: str,
                                   resource_type: str,
                                   mapping_config: Dict[str, Any]) -> QueryResult:
        """Execute FHIR transformation query."""

        if not self.connected:
            raise RuntimeError("Database not connected")

        # Generate platform-specific query
        query = self._generate_transformation_query(source_table, resource_type, mapping_config)

        # Execute query
        return self.adapter.execute_query(query)

    def _generate_transformation_query(self,
                                     source_table: str,
                                     resource_type: str,
                                     mapping_config: Dict[str, Any]) -> str:
        """Generate platform-specific transformation query."""

        if resource_type == "Patient":
            if self.platform == DatabasePlatform.DUCKDB:
                return f"""
                SELECT
                    to_fhir_patient(
                        patient_id,
                        first_name,
                        last_name,
                        birth_date::DATE,
                        gender
                    ) as fhir_resource,
                    patient_id as source_id
                FROM {source_table}
                WHERE patient_id IS NOT NULL
                """

            elif self.platform == DatabasePlatform.DATABRICKS:
                return f"""
                SELECT
                    to_fhir_patient(patient_id, first_name, last_name, birth_date, gender) as fhir_resource,
                    patient_id as source_id
                FROM {source_table}
                WHERE patient_id IS NOT NULL
                """

        # Fallback for other resource types
        return f"SELECT * FROM {source_table}"

    def load_source_data(self, data: pd.DataFrame, table_name: str = "source_data") -> bool:
        """Load source data for transformation."""
        if not self.connected:
            raise RuntimeError("Database not connected")

        return self.adapter.load_data(data, table_name)

    def get_platform_capabilities(self) -> Dict[str, Any]:
        """Get platform capabilities and information."""
        return {
            "platform": self.platform.value,
            "connected": self.connected,
            "info": self.adapter.get_platform_info(),
            "features": {
                "local_processing": self.platform == DatabasePlatform.DUCKDB,
                "distributed_processing": self.platform == DatabasePlatform.DATABRICKS,
                "streaming": self.platform == DatabasePlatform.DATABRICKS,
                "file_formats": ["csv", "parquet", "json"],
                "fhir_functions": True
            }
        }


# Global database service instance
database_service = UnifiedDatabaseService()