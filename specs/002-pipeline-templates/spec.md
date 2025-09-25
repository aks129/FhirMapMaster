# Specification: Pipeline and Template Development System

## Overview
A comprehensive pipeline architecture supporting YAML-based configurations and Liquid templating for automated, repeatable FHIR data transformations with CI/CD integration capabilities.

## Problem Statement
Organizations need:
- Automated, repeatable data transformation workflows
- Version-controlled mapping configurations
- Template-based transformations for common patterns
- Integration with modern data platforms and CI/CD pipelines

## User Stories

### As a Data Engineer
- I want to define mappings as code in YAML files
- I want to use Liquid templates for complex transformations
- I want to run transformations in automated pipelines
- I want to test mappings before deployment

### As a DevOps Engineer
- I want CI/CD integration for mapping deployments
- I want automated testing of mapping changes
- I want rollback capabilities for failed mappings
- I want monitoring and alerting for pipeline failures

### As a Solution Architect
- I want reusable templates for common scenarios
- I want to compose complex mappings from simple components
- I want database-agnostic transformation pipelines
- I want scalable processing for large datasets

## Functional Requirements

### 1. YAML-Based Configuration

#### 1.1 Mapping Definition Language
```yaml
mapping_specification:
  version: "1.0"
  metadata:
    name: "Patient Demographics Mapping"
    author: "system"
    created: "2024-01-01"
    ig_profile: "us-core-7.0.0"

  sources:
    - name: "patient_data"
      type: "csv"
      schema:
        fields:
          - name: "patient_id"
            type: "string"
            required: true
          - name: "first_name"
            type: "string"
          - name: "last_name"
            type: "string"
          - name: "dob"
            type: "date"
            format: "yyyy-MM-dd"

  targets:
    - resource: "Patient"
      profile: "http://hl7.org/fhir/us/core/StructureDefinition/us-core-patient"

  mappings:
    - source: "patient_data"
      target: "Patient"
      rules:
        - field: "id"
          expression: "{{ patient_id | prepend: 'pat-' }}"

        - field: "name[0].given[0]"
          expression: "{{ first_name }}"

        - field: "name[0].family"
          expression: "{{ last_name }}"

        - field: "birthDate"
          expression: "{{ dob | date: '%Y-%m-%d' }}"

  transformations:
    - name: "clean_names"
      type: "pre_process"
      expression: |
        {% assign first_name = first_name | strip | capitalize %}
        {% assign last_name = last_name | strip | capitalize %}

  validations:
    - name: "required_fields"
      rules:
        - field: "patient_id"
          condition: "not_empty"
        - field: "dob"
          condition: "valid_date"
```

#### 1.2 Pipeline Configuration
```yaml
pipeline:
  name: "daily_patient_sync"
  schedule: "0 2 * * *"  # 2 AM daily

  stages:
    - name: "extract"
      type: "database"
      config:
        source: "databricks"
        query: "SELECT * FROM patients WHERE updated_date >= '{{ yesterday }}'"

    - name: "transform"
      type: "mapping"
      config:
        mapping_file: "mappings/patient_demographics.yaml"
        template_engine: "liquid"

    - name: "validate"
      type: "fhir_validation"
      config:
        profile: "us-core-7.0.0"
        strict_mode: true

    - name: "load"
      type: "fhir_server"
      config:
        endpoint: "https://fhir.example.com"
        auth: "oauth2"

  error_handling:
    on_failure: "rollback"
    notifications:
      - type: "email"
        recipients: ["admin@example.com"]
      - type: "slack"
        channel: "#data-alerts"
```

### 2. Liquid Template Engine

#### 2.1 Template Components
```liquid
{%- comment -%} Patient Name Template {%- endcomment -%}
{%- capture patient_name -%}
{
  "use": "official",
  "family": "{{ last_name | escape }}",
  "given": [
    "{{ first_name | escape }}"
    {%- if middle_name -%}
    , "{{ middle_name | escape }}"
    {%- endif -%}
  ],
  {%- if prefix -%}
  "prefix": ["{{ prefix | escape }}"],
  {%- endif -%}
  {%- if suffix -%}
  "suffix": ["{{ suffix | escape }}"],
  {%- endif -%}
  "period": {
    "start": "{{ name_effective_date | default: 'now' | date: '%Y-%m-%d' }}"
  }
}
{%- endcapture -%}
```

#### 2.2 Custom Filters
```yaml
custom_filters:
  - name: "to_fhir_date"
    description: "Convert various date formats to FHIR date"
    implementation: |
      def to_fhir_date(value):
        # Parse multiple date formats
        # Return YYYY-MM-DD format

  - name: "to_coding"
    description: "Convert code to FHIR Coding"
    implementation: |
      def to_coding(value, system):
        return {
          "system": system,
          "code": value,
          "display": lookup_display(value, system)
        }

  - name: "sanitize_id"
    description: "Create valid FHIR resource ID"
    implementation: |
      def sanitize_id(value):
        # Remove invalid characters
        # Ensure uniqueness
```

### 3. Database Integration

#### 3.1 DuckDB Integration
```yaml
duckdb_connector:
  config:
    database: "fhir_mappings.db"
    read_only: false

  capabilities:
    - name: "local_processing"
      description: "Process data locally without external dependencies"

    - name: "parquet_support"
      description: "Native Parquet file support for efficient storage"

    - name: "sql_transformations"
      description: "SQL-based data transformations"

  usage:
    extract:
      query: |
        SELECT * FROM read_parquet('data/*.parquet')
        WHERE date >= '{{ start_date }}'

    transform:
      query: |
        CREATE TABLE mapped_patients AS
        SELECT
          patient_id,
          to_fhir_name(first_name, last_name) as name,
          to_fhir_date(birth_date) as birthDate
        FROM raw_patients

    load:
      format: "ndjson"
      output: "output/patients.ndjson"
```

#### 3.2 Databricks Integration
```yaml
databricks_connector:
  config:
    workspace_url: "https://workspace.databricks.com"
    cluster_id: "${DATABRICKS_CLUSTER_ID}"
    auth:
      type: "service_principal"
      client_id: "${DATABRICKS_CLIENT_ID}"
      client_secret: "${DATABRICKS_CLIENT_SECRET}"

  capabilities:
    - name: "distributed_processing"
      description: "Scale to billions of records"

    - name: "delta_lake"
      description: "ACID transactions and time travel"

    - name: "streaming"
      description: "Real-time data processing"

  usage:
    notebooks:
      - path: "/fhir/transformations/patient_mapping"
        parameters:
          source_table: "raw.patients"
          target_table: "fhir.patient_resources"

    sql_warehouse:
      endpoint: "${SQL_WAREHOUSE_ID}"
      queries:
        - name: "extract_patients"
          sql: "SELECT * FROM catalog.schema.patients"
```

### 4. Testing Framework

#### 4.1 Unit Tests for Mappings
```yaml
mapping_tests:
  - name: "test_patient_name_mapping"
    input:
      first_name: "John"
      last_name: "Doe"
      middle_name: "Michael"

    expected:
      name:
        - given: ["John", "Michael"]
          family: "Doe"
          use: "official"

  - name: "test_date_transformation"
    input:
      dob: "01/15/1980"

    expected:
      birthDate: "1980-01-15"

  - name: "test_missing_optional_field"
    input:
      first_name: "Jane"
      last_name: "Smith"
      # middle_name is missing

    expected:
      name:
        - given: ["Jane"]
          family: "Smith"
```

#### 4.2 Integration Tests
```yaml
integration_tests:
  - name: "end_to_end_patient_mapping"
    stages:
      - setup:
          action: "load_test_data"
          file: "test_data/patients.csv"

      - execute:
          action: "run_pipeline"
          config: "pipelines/patient_mapping.yaml"

      - validate:
          assertions:
            - type: "record_count"
              expected: 100
            - type: "fhir_valid"
              profile: "us-core-patient"
            - type: "field_coverage"
              minimum: 95

      - cleanup:
          action: "delete_test_resources"
```

### 5. CI/CD Integration

#### 5.1 GitHub Actions Workflow
```yaml
name: FHIR Mapping Pipeline

on:
  push:
    branches: [main]
    paths:
      - 'mappings/**'
      - 'templates/**'

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov

      - name: Run mapping tests
        run: |
          pytest tests/mappings --cov=mappings

      - name: Validate YAML configurations
        run: |
          python scripts/validate_configs.py

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
      - name: Deploy to Databricks
        run: |
          databricks workspace import_dir \
            --path /production/mappings \
            --source mappings/

      - name: Update pipeline configurations
        run: |
          python scripts/deploy_pipelines.py \
            --environment production
```

## Success Metrics

### Performance
- **Processing Speed**: >10,000 records/second for simple mappings
- **Pipeline Success Rate**: >99.5% uptime
- **Transformation Accuracy**: 100% validation pass rate
- **Scale**: Support for billions of records via Databricks

### Developer Experience
- **Configuration Time**: <30 minutes for new mapping
- **Test Coverage**: >90% for all mappings
- **Deployment Time**: <5 minutes from commit to production
- **Rollback Time**: <2 minutes for failed deployments

## Implementation Roadmap

### Phase 1: YAML Configuration (Weeks 1-3)
- Design YAML schema
- Build configuration parser
- Create validation framework
- Document configuration syntax

### Phase 2: Liquid Templates (Weeks 4-6)
- Integrate Liquid engine
- Create custom healthcare filters
- Build template library
- Develop template testing tools

### Phase 3: Database Integration (Weeks 7-9)
- DuckDB connector
- Databricks connector
- Query optimization
- Performance testing

### Phase 4: CI/CD Pipeline (Weeks 10-12)
- GitHub Actions setup
- Automated testing
- Deployment automation
- Monitoring integration