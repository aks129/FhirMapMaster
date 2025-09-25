"""
Test suite for Database Adapter (DuckDB & Databricks)
Tests unified database interface and platform-specific functionality
"""

import pytest
import pandas as pd
import os
from unittest.mock import Mock, patch, MagicMock

from utils.engines.database_adapter import (
    DatabaseAdapterFactory,
    DuckDBAdapter,
    DataBricksAdapter,
    UnifiedDatabaseService,
    DatabasePlatform,
    QueryResult,
    database_service
)


class TestDatabaseAdapterFactory:
    """Test database adapter factory functionality."""

    def test_platform_detection_duckdb(self):
        with patch('importlib.util.find_spec') as mock_find_spec:
            mock_find_spec.return_value = True  # DuckDB available

            platform = DatabaseAdapterFactory.detect_platform()
            assert platform == DatabasePlatform.DUCKDB

    @patch.dict(os.environ, {'DATABRICKS_RUNTIME_VERSION': '13.3.x'})
    def test_platform_detection_databricks_runtime(self):
        platform = DatabaseAdapterFactory.detect_platform()
        assert platform == DatabasePlatform.DATABRICKS

    @patch.dict(os.environ, {
        'DATABRICKS_SERVER_HOSTNAME': 'test.databricks.com',
        'DATABRICKS_HTTP_PATH': '/sql/1.0/warehouses/test',
        'DATABRICKS_ACCESS_TOKEN': 'test-token'
    })
    def test_platform_detection_databricks_external(self):
        platform = DatabaseAdapterFactory.detect_platform()
        assert platform == DatabasePlatform.DATABRICKS

    @patch('importlib.util.find_spec')
    def test_platform_detection_unknown(self, mock_find_spec):
        mock_find_spec.return_value = None  # No DuckDB

        platform = DatabaseAdapterFactory.detect_platform()
        assert platform == DatabasePlatform.UNKNOWN

    def test_adapter_creation_duckdb(self):
        adapter = DatabaseAdapterFactory.create_adapter(DatabasePlatform.DUCKDB)
        assert isinstance(adapter, DuckDBAdapter)

    def test_adapter_creation_databricks(self):
        adapter = DatabaseAdapterFactory.create_adapter(DatabasePlatform.DATABRICKS)
        assert isinstance(adapter, DataBricksAdapter)

    def test_adapter_creation_unsupported(self):
        with pytest.raises(RuntimeError, match="Unsupported database platform"):
            DatabaseAdapterFactory.create_adapter(DatabasePlatform.UNKNOWN)


class TestDuckDBAdapter:
    """Test DuckDB adapter functionality."""

    @pytest.fixture
    def adapter(self):
        return DuckDBAdapter(":memory:")  # Use in-memory database for testing

    @patch('duckdb.connect')
    def test_connection_success(self, mock_connect, adapter):
        mock_connection = Mock()
        mock_connect.return_value = mock_connection

        result = adapter.connect()
        assert result is True
        assert adapter.connection == mock_connection

    @patch('duckdb.connect')
    def test_connection_failure(self, mock_connect, adapter):
        mock_connect.side_effect = Exception("Connection failed")

        result = adapter.connect()
        assert result is False

    def test_connection_duckdb_not_installed(self, adapter):
        with patch('importlib.util.find_spec', return_value=None):
            # Simulate DuckDB not installed by making import fail
            result = adapter.connect()
            assert result is False

    @patch('duckdb.connect')
    def test_execute_query_simple(self, mock_connect, adapter):
        # Mock connection and results
        mock_connection = Mock()
        mock_connect.return_value = mock_connection

        mock_result_df = pd.DataFrame({'col1': [1, 2], 'col2': ['a', 'b']})
        mock_connection.execute.return_value.fetchdf.return_value = mock_result_df

        adapter.connect()
        result = adapter.execute_query("SELECT * FROM test_table")

        assert isinstance(result, QueryResult)
        assert len(result.data) == 2
        assert result.platform == DatabasePlatform.DUCKDB
        assert result.execution_time_ms > 0

    @patch('duckdb.connect')
    def test_execute_query_with_parameters(self, mock_connect, adapter):
        mock_connection = Mock()
        mock_connect.return_value = mock_connection

        mock_result_df = pd.DataFrame({'count': [5]})
        mock_connection.execute.return_value.fetchdf.return_value = mock_result_df

        adapter.connect()
        result = adapter.execute_query(
            "SELECT COUNT(*) as count FROM test WHERE id = ?",
            {"id": 123}
        )

        assert result.row_count == 1

    @patch('duckdb.connect')
    def test_load_data(self, mock_connect, adapter):
        mock_connection = Mock()
        mock_connect.return_value = mock_connection

        adapter.connect()

        test_data = pd.DataFrame({
            'id': [1, 2, 3],
            'name': ['Alice', 'Bob', 'Charlie']
        })

        result = adapter.load_data(test_data, "test_table")
        assert result is True

        # Verify the correct sequence of calls
        mock_connection.execute.assert_any_call("DROP TABLE IF EXISTS test_table")
        mock_connection.register.assert_called_once()
        mock_connection.unregister.assert_called_once()

    @patch('duckdb.connect')
    def test_fhir_function_loading(self, mock_connect, adapter):
        mock_connection = Mock()
        mock_connect.return_value = mock_connection

        adapter.connect()
        adapter.optimize_for_fhir()

        # Verify FHIR functions were created
        assert adapter.fhir_functions_loaded is True

        # Check that SQL functions were executed
        calls = mock_connection.execute.call_args_list
        function_calls = [call for call in calls if 'CREATE OR REPLACE FUNCTION' in str(call)]
        assert len(function_calls) >= 3  # Should have at least 3 FHIR functions

    def test_query_type_detection(self, adapter):
        assert adapter._detect_query_type("SELECT * FROM table") == "SELECT"
        assert adapter._detect_query_type("INSERT INTO table VALUES (1)") == "INSERT"
        assert adapter._detect_query_type("UPDATE table SET col = 1") == "UPDATE"
        assert adapter._detect_query_type("CREATE TABLE test (id INT)") == "CREATE"
        assert adapter._detect_query_type("DROP TABLE test") == "OTHER"

    def test_table_extraction(self, adapter):
        query = "SELECT * FROM patients JOIN encounters ON patients.id = encounters.patient_id"
        tables = adapter._extract_tables(query)

        assert "patients" in tables
        assert "encounters" in tables

    def test_platform_info(self, adapter):
        with patch('duckdb.connect') as mock_connect:
            mock_connection = Mock()
            mock_connect.return_value = mock_connection
            mock_connection.execute.return_value.fetchone.return_value = ["DuckDB v0.9.0"]

            adapter.connect()
            info = adapter.get_platform_info()

            assert info["platform"] == "DuckDB"
            assert info["version"] == "DuckDB v0.9.0"
            assert "extensions" in info


class TestDataBricksAdapter:
    """Test Databricks adapter functionality."""

    @pytest.fixture
    def adapter(self):
        return DataBricksAdapter(
            server_hostname="test.databricks.com",
            http_path="/sql/1.0/warehouses/test",
            access_token="test-token"
        )

    @patch.dict(os.environ, {'DATABRICKS_RUNTIME_VERSION': '13.3.x'})
    @patch('pyspark.sql.SparkSession')
    def test_databricks_runtime_connection(self, mock_spark, adapter):
        mock_session = Mock()
        mock_spark.builder.getOrCreate.return_value = mock_session

        result = adapter.connect()
        assert result is True
        assert adapter.spark_session == mock_session

    @patch('databricks.sql.connect')
    def test_external_connection(self, mock_connect, adapter):
        mock_connection = Mock()
        mock_connect.return_value = mock_connection

        result = adapter.connect()
        assert result is True
        assert adapter.connection == mock_connection

    @patch('databricks.sql.connect')
    def test_connection_failure(self, mock_connect, adapter):
        mock_connect.side_effect = Exception("Connection failed")

        result = adapter.connect()
        assert result is False

    def test_connection_missing_parameters(self):
        adapter = DataBricksAdapter()  # No connection parameters

        result = adapter.connect()
        assert result is False

    @patch('databricks.sql.connect')
    def test_execute_query_sql_connector(self, mock_connect, adapter):
        # Mock SQL connector
        mock_connection = Mock()
        mock_cursor = Mock()

        mock_connect.return_value = mock_connection
        mock_connection.cursor.return_value = mock_cursor

        mock_cursor.description = [("col1",), ("col2",)]
        mock_cursor.fetchall.return_value = [(1, "a"), (2, "b")]

        adapter.connect()
        result = adapter.execute_query("SELECT * FROM test")

        assert isinstance(result, QueryResult)
        assert len(result.data) == 2
        assert result.platform == DatabasePlatform.DATABRICKS

    @patch.dict(os.environ, {'DATABRICKS_RUNTIME_VERSION': '13.3.x'})
    @patch('pyspark.sql.SparkSession')
    def test_execute_query_spark(self, mock_spark, adapter):
        # Mock Spark session
        mock_session = Mock()
        mock_spark.builder.getOrCreate.return_value = mock_session

        mock_result_df = pd.DataFrame({'col1': [1, 2], 'col2': ['a', 'b']})
        mock_session.sql.return_value.toPandas.return_value = mock_result_df

        adapter.connect()
        result = adapter.execute_query("SELECT * FROM test")

        assert len(result.data) == 2
        assert "spark" in result.metadata["execution_engine"]

    @patch.dict(os.environ, {'DATABRICKS_RUNTIME_VERSION': '13.3.x'})
    @patch('pyspark.sql.SparkSession')
    def test_load_data_spark(self, mock_spark, adapter):
        mock_session = Mock()
        mock_df = Mock()
        mock_writer = Mock()

        mock_spark.builder.getOrCreate.return_value = mock_session
        mock_session.createDataFrame.return_value = mock_df
        mock_df.write = mock_writer
        mock_writer.mode.return_value = mock_writer
        mock_writer.option.return_value = mock_writer

        adapter.connect()

        test_data = pd.DataFrame({'id': [1, 2], 'name': ['A', 'B']})
        result = adapter.load_data(test_data, "test_table")

        assert result is True
        mock_writer.saveAsTable.assert_called_once_with("test_table")

    @patch.dict(os.environ, {'DATABRICKS_RUNTIME_VERSION': '13.3.x'})
    @patch('pyspark.sql.SparkSession')
    def test_spark_optimizations(self, mock_spark, adapter):
        mock_session = Mock()
        mock_conf = Mock()

        mock_spark.builder.getOrCreate.return_value = mock_session
        mock_session.conf = mock_conf

        adapter.connect()
        adapter.optimize_for_fhir()

        # Verify optimization settings were applied
        assert mock_conf.set.call_count > 0

        # Check specific optimizations
        calls = [str(call) for call in mock_conf.set.call_args_list]
        assert any("adaptive.enabled" in call for call in calls)

    def test_platform_info(self, adapter):
        with patch.dict(os.environ, {'DATABRICKS_RUNTIME_VERSION': '13.3.x'}):
            with patch('pyspark.sql.SparkSession') as mock_spark:
                mock_session = Mock()
                mock_spark.builder.getOrCreate.return_value = mock_session

                adapter.connect()
                info = adapter.get_platform_info()

                assert info["platform"] == "Databricks"
                assert info["runtime_version"] == "13.3.x"
                assert info["connection_type"] == "spark"


class TestUnifiedDatabaseService:
    """Test unified database service."""

    @pytest.fixture
    def service(self):
        return UnifiedDatabaseService()

    @patch('utils.engines.database_adapter.DatabaseAdapterFactory.detect_platform')
    @patch('utils.engines.database_adapter.DatabaseAdapterFactory.create_adapter')
    def test_service_initialization(self, mock_create, mock_detect, service):
        mock_adapter = Mock()
        mock_detect.return_value = DatabasePlatform.DUCKDB
        mock_create.return_value = mock_adapter
        mock_adapter.connect.return_value = True

        result = service.initialize()
        assert result is True
        assert service.connected is True

    def test_fhir_transformation_query_generation_patient(self, service):
        service.platform = DatabasePlatform.DUCKDB

        query = service._generate_transformation_query(
            "source_patients",
            "Patient",
            {}
        )

        assert "to_fhir_patient" in query
        assert "source_patients" in query
        assert "patient_id IS NOT NULL" in query

    def test_fhir_transformation_query_generation_databricks(self, service):
        service.platform = DatabasePlatform.DATABRICKS

        query = service._generate_transformation_query(
            "source_patients",
            "Patient",
            {}
        )

        assert "to_fhir_patient" in query
        assert "source_patients" in query

    def test_platform_capabilities(self, service):
        service.platform = DatabasePlatform.DUCKDB
        service.connected = True

        capabilities = service.get_platform_capabilities()

        assert capabilities["platform"] == "duckdb"
        assert capabilities["connected"] is True
        assert capabilities["features"]["local_processing"] is True
        assert capabilities["features"]["distributed_processing"] is False

    @patch('utils.engines.database_adapter.DatabaseAdapterFactory.detect_platform')
    @patch('utils.engines.database_adapter.DatabaseAdapterFactory.create_adapter')
    def test_execute_fhir_transformation(self, mock_create, mock_detect, service):
        mock_adapter = Mock()
        mock_detect.return_value = DatabasePlatform.DUCKDB
        mock_create.return_value = mock_adapter
        mock_adapter.connect.return_value = True

        mock_result = QueryResult(
            data=pd.DataFrame({"fhir_resource": ["resource1", "resource2"]}),
            execution_time_ms=100,
            row_count=2,
            metadata={},
            platform=DatabasePlatform.DUCKDB
        )
        mock_adapter.execute_query.return_value = mock_result

        service.initialize()
        result = service.execute_fhir_transformation("patients", "Patient", {})

        assert result.row_count == 2
        assert result.platform == DatabasePlatform.DUCKDB

    def test_service_not_connected_error(self, service):
        service.connected = False

        with pytest.raises(RuntimeError, match="Database not connected"):
            service.execute_fhir_transformation("test", "Patient", {})

        with pytest.raises(RuntimeError, match="Database not connected"):
            service.load_source_data(pd.DataFrame())


class TestIntegration:
    """Integration tests for database adapter functionality."""

    def test_global_database_service(self):
        """Test the global database service instance."""
        assert database_service is not None
        assert isinstance(database_service, UnifiedDatabaseService)

    @patch('duckdb.connect')
    def test_end_to_end_duckdb_workflow(self, mock_connect):
        """Test complete DuckDB workflow."""
        # Mock DuckDB connection
        mock_connection = Mock()
        mock_connect.return_value = mock_connection

        adapter = DuckDBAdapter(":memory:")
        connected = adapter.connect()
        assert connected

        # Test data loading
        test_data = pd.DataFrame({
            'patient_id': ['PAT001', 'PAT002'],
            'first_name': ['John', 'Jane'],
            'last_name': ['Doe', 'Smith']
        })

        result = adapter.load_data(test_data, "patients")
        assert result is True

        # Test query execution
        mock_result_df = pd.DataFrame({'fhir_resource': ['{}', '{}']})
        mock_connection.execute.return_value.fetchdf.return_value = mock_result_df

        query_result = adapter.execute_query("SELECT * FROM patients")
        assert query_result.row_count == 2

    def test_platform_detection_workflow(self):
        """Test platform detection and adapter creation workflow."""
        # Test detection
        platform = DatabaseAdapterFactory.detect_platform()
        assert platform in [DatabasePlatform.DUCKDB, DatabasePlatform.DATABRICKS, DatabasePlatform.UNKNOWN]

        # Test adapter creation (except for UNKNOWN)
        if platform != DatabasePlatform.UNKNOWN:
            adapter = DatabaseAdapterFactory.create_adapter(platform)
            assert adapter is not None

            # Test platform info
            info = adapter.get_platform_info()
            assert "platform" in info


if __name__ == "__main__":
    pytest.main([__file__])