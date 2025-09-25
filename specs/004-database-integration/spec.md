# Specification: Database Integration (DuckDB & Databricks)

## Overview
Comprehensive database integration supporting both local development with DuckDB and enterprise-scale processing with Databricks, enabling seamless data transformation workflows across different deployment contexts.

## Problem Statement
Healthcare organizations need:
- Local development and testing capabilities without cloud dependencies
- Enterprise-scale processing for production workloads
- Seamless transition between development and production environments
- Support for various data formats and processing patterns

## User Stories

### As a Healthcare Data Engineer
- I want to develop mappings locally using DuckDB for fast iteration
- I want to deploy the same mappings to Databricks for production scale
- I want to process data from various sources (files, databases, APIs)
- I want efficient handling of large healthcare datasets

### As a Data Platform Architect
- I want unified data processing patterns across environments
- I want cost-effective local development workflows
- I want enterprise-grade security and compliance in production
- I want monitoring and observability across all data pipelines

### As a Healthcare Developer
- I want SQL-based transformations for complex data logic
- I want Python/Spark integration for advanced analytics
- I want streaming capabilities for real-time data processing
- I want easy debugging and profiling of transformation logic

## Functional Requirements

### 1. DuckDB Integration

#### 1.1 Local Development Environment
```yaml
duckdb_configuration:
  database:
    path: "data/fhir_mappings.db"
    mode: "read_write"
    memory_limit: "8GB"
    threads: "auto"

  extensions:
    required:
      - httpfs        # Remote file access
      - json          # JSON processing
      - parquet       # Parquet format
      - spatial       # Geographic data
      - inet          # Network functions

  capabilities:
    file_formats:
      - csv: "Built-in CSV reader with auto-detection"
      - parquet: "Columnar format for efficient analytics"
      - json: "Nested JSON processing"
      - xlsx: "Excel file support via Python"

    data_sources:
      - local_files: "Direct file system access"
      - s3_compatible: "MinIO, AWS S3 via httpfs"
      - http_endpoints: "REST API data ingestion"
      - pandas_dataframes: "Python integration"

  performance_features:
    - columnar_storage: "Efficient column-oriented processing"
    - vectorized_execution: "SIMD-optimized operations"
    - parallel_processing: "Multi-threaded query execution"
    - result_caching: "Query result caching"
```

#### 1.2 DuckDB-Specific Features
```sql
-- Healthcare data processing patterns in DuckDB

-- 1. Multi-format data ingestion
CREATE VIEW patient_data AS
SELECT * FROM read_parquet('data/patients/*.parquet')
UNION ALL
SELECT * FROM read_csv('data/patients/*.csv', auto_detect=true)
UNION ALL
SELECT * FROM read_json('data/patients/*.json', format='auto');

-- 2. FHIR resource construction
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

-- 3. Validation and quality checks
CREATE VIEW data_quality_report AS
SELECT
  'Patient' as resource_type,
  count(*) as total_records,
  count(*) FILTER (WHERE first_name IS NOT NULL) as first_name_populated,
  count(*) FILTER (WHERE last_name IS NOT NULL) as last_name_populated,
  count(*) FILTER (WHERE birth_date IS NOT NULL) as birth_date_populated,
  count(*) FILTER (WHERE gender IN ('male', 'female', 'other', 'unknown')) as valid_gender
FROM patient_data;
```

### 2. Databricks Integration

#### 2.1 Enterprise Configuration
```yaml
databricks_configuration:
  workspace:
    url: "${DATABRICKS_WORKSPACE_URL}"
    region: "us-east-1"

  compute:
    clusters:
      development:
        node_type: "i3.xlarge"
        min_workers: 1
        max_workers: 4
        spark_version: "13.3.x-scala2.12"
        auto_termination: 120

      production:
        node_type: "i3.2xlarge"
        min_workers: 2
        max_workers: 20
        spark_version: "13.3.x-scala2.12"
        auto_scaling: true
        spot_instances: true

  storage:
    catalog: "fhir_catalog"
    schemas:
      - raw_data
      - transformed_data
      - fhir_resources

    data_formats:
      - delta_lake: "ACID transactions and time travel"
      - parquet: "Efficient columnar storage"
      - unity_catalog: "Centralized metadata management"

  security:
    authentication: "service_principal"
    encryption:
      - at_rest: "customer_managed_keys"
      - in_transit: "tls_1_2"
    access_control: "attribute_based"
```

#### 2.2 Spark-Based Processing
```python
# Healthcare data processing in Databricks/Spark

from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *
import json

# FHIR resource schema definitions
patient_fhir_schema = StructType([
    StructField("resourceType", StringType(), False),
    StructField("id", StringType(), False),
    StructField("name", ArrayType(StructType([
        StructField("use", StringType(), True),
        StructField("given", ArrayType(StringType()), True),
        StructField("family", StringType(), True)
    ])), True),
    StructField("birthDate", StringType(), True),
    StructField("gender", StringType(), True)
])

def transform_to_fhir_patient(df):
    """Transform raw patient data to FHIR Patient resources"""

    return df.select(
        lit("Patient").alias("resourceType"),
        col("patient_id").alias("id"),
        array(
            struct(
                lit("official").alias("use"),
                array(col("first_name")).alias("given"),
                col("last_name").alias("family")
            )
        ).alias("name"),
        date_format(col("birth_date"), "yyyy-MM-dd").alias("birthDate"),
        when(lower(col("gender")).isin("m", "male"), "male")
        .when(lower(col("gender")).isin("f", "female"), "female")
        .otherwise("unknown").alias("gender")
    )

# Streaming processing for real-time FHIR transformation
def create_streaming_fhir_pipeline():
    """Create streaming pipeline for real-time FHIR transformation"""

    # Read streaming data from Delta table
    streaming_df = spark.readStream \
        .format("delta") \
        .table("raw_data.patient_updates")

    # Transform to FHIR format
    fhir_df = transform_to_fhir_patient(streaming_df)

    # Write to Delta table with ACID guarantees
    query = fhir_df.writeStream \
        .format("delta") \
        .outputMode("append") \
        .option("checkpointLocation", "/mnt/checkpoints/fhir_patients") \
        .table("fhir_resources.patients")

    return query
```

### 3. Unified Processing Framework

#### 3.1 Cross-Platform Compatibility
```yaml
unified_framework:
  sql_compatibility:
    common_functions:
      - date_functions: "DATE, DATEADD, DATEDIFF"
      - string_functions: "CONCAT, SUBSTR, REGEXP_REPLACE"
      - json_functions: "JSON_EXTRACT, JSON_OBJECT"
      - aggregate_functions: "COUNT, SUM, AVG, MIN, MAX"

    platform_differences:
      duckdb_specific:
        - read_parquet: "Built-in Parquet reader"
        - struct_pack: "Create structured data"
        - array_agg: "Array aggregation"

      databricks_specific:
        - delta_format: "Delta Lake operations"
        - unity_catalog: "Catalog operations"
        - spark_functions: "Spark SQL functions"

  abstraction_layer:
    query_templates:
      patient_extraction: |
        SELECT
          patient_id,
          first_name,
          last_name,
          birth_date,
          gender
        FROM {source_table}
        WHERE {filter_conditions}

    transformation_patterns:
      fhir_patient: |
        SELECT
          'Patient' as resourceType,
          patient_id as id,
          {platform_specific_name_construction} as name,
          {platform_specific_date_format} as birthDate,
          {platform_specific_gender_mapping} as gender
        FROM patient_data
```

#### 3.2 Environment Detection and Adaptation
```python
import os
import importlib

class DatabaseAdapter:
    """Unified database adapter supporting DuckDB and Databricks"""

    def __init__(self):
        self.platform = self._detect_platform()
        self.connection = self._create_connection()

    def _detect_platform(self):
        """Detect current execution environment"""
        if 'DATABRICKS_RUNTIME_VERSION' in os.environ:
            return 'databricks'
        elif importlib.util.find_spec('duckdb'):
            return 'duckdb'
        else:
            raise Exception("No supported database platform detected")

    def _create_connection(self):
        """Create platform-specific connection"""
        if self.platform == 'databricks':
            from pyspark.sql import SparkSession
            return SparkSession.builder.getOrCreate()
        elif self.platform == 'duckdb':
            import duckdb
            return duckdb.connect('data/fhir_mappings.db')

    def execute_query(self, query, parameters=None):
        """Execute query with platform-specific optimizations"""
        if self.platform == 'databricks':
            return self._execute_spark_query(query, parameters)
        elif self.platform == 'duckdb':
            return self._execute_duckdb_query(query, parameters)

    def optimize_for_fhir(self, df):
        """Apply platform-specific FHIR optimizations"""
        if self.platform == 'databricks':
            # Databricks optimizations
            df = df.repartition(200)  # Optimize parallelism
            df.cache()  # Cache frequently accessed data
        elif self.platform == 'duckdb':
            # DuckDB optimizations
            # Enable parallel processing
            self.connection.execute("SET threads TO 8")
            # Optimize memory usage
            self.connection.execute("SET memory_limit = '8GB'")

        return df
```

### 4. Performance Optimization

#### 4.1 DuckDB Performance Tuning
```yaml
duckdb_optimization:
  memory_management:
    - buffer_size: "4GB"
    - temp_directory: "/tmp/duckdb"
    - max_memory: "8GB"

  query_optimization:
    - enable_optimizer: true
    - enable_profiler: true
    - enable_progress_bar: true

  storage_optimization:
    - compression: "zstd"
    - row_group_size: 122880
    - checkpoint_threshold: "1GB"

  parallel_processing:
    - threads: "auto"
    - external_threads: 4
    - preserve_insertion_order: false
```

#### 4.2 Databricks Performance Tuning
```yaml
databricks_optimization:
  cluster_configuration:
    - spark.sql.adaptive.enabled: true
    - spark.sql.adaptive.coalescePartitions.enabled: true
    - spark.sql.adaptive.skewJoin.enabled: true
    - spark.sql.cbo.enabled: true

  delta_optimization:
    - auto_optimize: true
    - auto_compact: true
    - optimize_write: true
    - z_order_columns: ["patient_id", "date"]

  caching_strategy:
    - cache_frequently_accessed_tables: true
    - use_disk_cache: true
    - cache_size: "50% of memory"

  performance_monitoring:
    - spark_ui_enabled: true
    - metrics_collection: true
    - query_profiling: true
```

### 5. Data Pipeline Patterns

#### 5.1 Batch Processing Pipeline
```yaml
batch_pipeline:
  duckdb_implementation:
    steps:
      - extract:
          query: "CREATE VIEW raw_data AS SELECT * FROM read_parquet('data/input/*.parquet')"

      - transform:
          query: |
            CREATE TABLE fhir_patients AS
            SELECT to_fhir_patient(patient_id, first_name, last_name, birth_date, gender) as fhir_resource
            FROM raw_data

      - validate:
          query: |
            SELECT
              count(*) as total_resources,
              count(*) FILTER (WHERE json_extract(fhir_resource, '$.resourceType') = 'Patient') as valid_patients
            FROM fhir_patients

      - load:
          format: "parquet"
          destination: "output/fhir_patients.parquet"

  databricks_implementation:
    steps:
      - extract:
          source: "delta_table"
          table: "raw_data.patients"

      - transform:
          notebook: "/fhir/transformations/patient_mapping"
          cluster: "production"

      - validate:
          function: "validate_fhir_resources"
          profile: "us-core-patient"

      - load:
          format: "delta"
          destination: "fhir_resources.patients"
          mode: "overwrite"
```

## Success Metrics

### Performance Benchmarks
- **DuckDB Processing**: >50,000 records/second for simple transformations
- **Databricks Processing**: >500,000 records/second with auto-scaling
- **Memory Efficiency**: <2GB for 1M patient records in DuckDB
- **Query Response**: <10ms for cached analytical queries

### Scalability Targets
- **DuckDB**: Support up to 10M records per transformation
- **Databricks**: Support unlimited scale with auto-scaling
- **Cost Efficiency**: <50% increase in processing cost vs current solutions
- **Development Speed**: 3x faster iteration with local DuckDB development

## Implementation Plan

### Phase 1: DuckDB Foundation (Weeks 1-3)
- DuckDB integration setup
- Basic SQL transformations
- File format support
- Performance optimization

### Phase 2: Databricks Integration (Weeks 4-6)
- Databricks connector
- Spark-based transformations
- Unity Catalog integration
- Security implementation

### Phase 3: Unified Framework (Weeks 7-9)
- Cross-platform abstraction
- Environment detection
- Query compatibility layer
- Testing framework

### Phase 4: Production Readiness (Weeks 10-12)
- Performance benchmarking
- Monitoring integration
- Documentation
- Training materials