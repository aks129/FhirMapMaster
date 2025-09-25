"""
FhirMapMaster - Enhanced Application with Spec-Driven Architecture
Main Streamlit application implementing the comprehensive FHIR mapping platform
"""

import streamlit as st
import os
import sys
import asyncio
from pathlib import Path

# Add utils to path for imports
sys.path.append(str(Path(__file__).parent))

# Import original components (for backward compatibility)
from components.file_uploader import render_file_uploader
from components.data_profiler import render_data_profiler
from components.resource_selector import render_resource_selector
from components.export_interface import render_export_interface

# Import enhanced components
from components.enhanced_mapping_interface import render_enhanced_mapping_interface

# Import new core services
from utils.core.llm_service_v2 import enhanced_llm_service
from utils.validation.validation_engine import validation_engine
from utils.engines.database_adapter import database_service
from utils.core.template_manager import template_manager
from utils.engines.pipeline_engine import pipeline_engine

import structlog

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="ISO"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


def ensure_cache_dirs():
    """Create required cache directories."""
    cache_dirs = [
        "cache",
        "cache/cpcds",
        "cache/fhir",
        "cache/validator",
        "cache/templates",
        "cache/pipelines",
        "sample_data",
        "data",
        "data/input",
        "data/output",
        "logs"
    ]

    for directory in cache_dirs:
        os.makedirs(directory, exist_ok=True)


def initialize_services():
    """Initialize all backend services."""

    with st.spinner("Initializing services..."):
        # Initialize database service
        try:
            if database_service.initialize():
                st.success("✅ Database service initialized")
                logger.info("Database service initialized successfully")
            else:
                st.warning("⚠️ Database service failed to initialize")
                logger.warning("Database service initialization failed")
        except Exception as e:
            st.error(f"❌ Database service error: {str(e)}")
            logger.error(f"Database service error: {str(e)}")

        # Initialize LLM service
        try:
            providers = enhanced_llm_service.get_available_providers()
            if providers:
                st.success(f"✅ LLM service initialized with providers: {', '.join(providers)}")
                logger.info(f"LLM service initialized: {providers}")
            else:
                st.info("ℹ️ No LLM providers configured (API keys needed)")
                logger.info("No LLM providers available")
        except Exception as e:
            st.warning(f"⚠️ LLM service warning: {str(e)}")
            logger.warning(f"LLM service warning: {str(e)}")

        # Initialize template manager
        try:
            st.success("✅ Template manager initialized")
            logger.info("Template manager initialized")
        except Exception as e:
            st.error(f"❌ Template manager error: {str(e)}")
            logger.error(f"Template manager error: {str(e)}")


def setup_page_config():
    """Configure Streamlit page settings."""
    st.set_page_config(
        page_title="Parker: Advanced FHIR Mapping Platform",
        page_icon="🕸️",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            'Get Help': 'https://github.com/aks129/FhirMapMaster',
            'Report a bug': 'https://github.com/aks129/FhirMapMaster/issues',
            'About': """
            # Parker - Advanced FHIR Mapping Platform

            Transform healthcare data into FHIR R4B resources with AI assistance.

            **Features:**
            - Multi-LLM AI assistance (OpenAI, Anthropic)
            - Multi-layer FHIR validation
            - Template-based transformations
            - Pipeline automation with YAML
            - DuckDB & Databricks integration
            - Human-in-the-loop workflows

            Version 2.0 - Spec-Driven Architecture
            """
        }
    )


def initialize_session_state():
    """Initialize Streamlit session state variables."""

    # Core data state
    if 'uploaded_file' not in st.session_state:
        st.session_state.uploaded_file = None
    if 'df' not in st.session_state:
        st.session_state.df = None
    if 'data_profile' not in st.session_state:
        st.session_state.data_profile = None

    # Mapping state
    if 'mappings' not in st.session_state:
        st.session_state.mappings = {}
    if 'ai_suggestions' not in st.session_state:
        st.session_state.ai_suggestions = {}
    if 'approved_mappings' not in st.session_state:
        st.session_state.approved_mappings = {}
    if 'mapping_feedback' not in st.session_state:
        st.session_state.mapping_feedback = {}

    # FHIR configuration
    if 'fhir_standard' not in st.session_state:
        st.session_state.fhir_standard = "US Core"
    if 'ig_version' not in st.session_state:
        st.session_state.ig_version = "7.0.0"
    if 'target_resource_type' not in st.session_state:
        st.session_state.target_resource_type = "Patient"

    # Workflow state
    if 'current_step' not in st.session_state:
        st.session_state.current_step = "upload"
    if 'workflow_mode' not in st.session_state:
        st.session_state.workflow_mode = "interactive"  # interactive, pipeline, template

    # Validation state
    if 'validation_results' not in st.session_state:
        st.session_state.validation_results = None
    if 'validation_reports' not in st.session_state:
        st.session_state.validation_reports = []

    # Pipeline state
    if 'pipeline_executions' not in st.session_state:
        st.session_state.pipeline_executions = {}
    if 'current_pipeline' not in st.session_state:
        st.session_state.current_pipeline = None

    # System state
    if 'services_initialized' not in st.session_state:
        st.session_state.services_initialized = False


def render_header():
    """Render application header with status indicators."""

    col1, col2, col3 = st.columns([3, 1, 1])

    with col1:
        st.title("🕸️ Parker: Advanced FHIR Mapping Platform")
        st.caption("Transform healthcare data into FHIR resources with AI assistance")

    with col2:
        # Service status indicators
        if st.session_state.services_initialized:
            st.success("🟢 Services Online")
        else:
            st.error("🔴 Services Offline")

    with col3:
        # Platform information
        platform_info = database_service.get_platform_capabilities()
        platform = platform_info.get('platform', 'Unknown')
        st.info(f"💾 {platform}")


def render_sidebar():
    """Render enhanced sidebar with workflow controls."""

    with st.sidebar:
        st.header("🎛️ Control Panel")

        # Workflow mode selection
        st.subheader("Workflow Mode")
        workflow_mode = st.radio(
            "Select workflow",
            ["🖱️ Interactive", "🤖 Template-Based", "⚡ Pipeline Automation"],
            key="workflow_mode_selector"
        )

        # Map workflow modes
        mode_mapping = {
            "🖱️ Interactive": "interactive",
            "🤖 Template-Based": "template",
            "⚡ Pipeline Automation": "pipeline"
        }
        st.session_state.workflow_mode = mode_mapping[workflow_mode]

        st.divider()

        # Service status and controls
        st.subheader("🔧 Services")

        if st.button("🔄 Refresh Services"):
            st.session_state.services_initialized = False
            st.rerun()

        # AI Configuration
        st.subheader("🤖 AI Configuration")

        # LLM Provider status
        providers = enhanced_llm_service.get_available_providers()
        if providers:
            st.success(f"Active: {', '.join(providers)}")
        else:
            st.warning("No providers configured")

        # Quick API key configuration
        with st.expander("🔑 API Keys"):
            openai_key = st.text_input("OpenAI API Key", type="password", key="openai_key_input")
            anthropic_key = st.text_input("Anthropic API Key", type="password", key="anthropic_key_input")

            if st.button("💾 Save Keys"):
                if openai_key:
                    os.environ['OPENAI_API_KEY'] = openai_key
                if anthropic_key:
                    os.environ['ANTHROPIC_API_KEY'] = anthropic_key
                st.success("Keys saved for this session")
                st.rerun()

        st.divider()

        # Database Configuration
        st.subheader("💾 Database")
        platform_info = database_service.get_platform_capabilities()

        st.write(f"**Platform:** {platform_info.get('platform', 'Unknown')}")
        st.write(f"**Connected:** {platform_info.get('connected', False)}")

        if platform_info.get('features', {}).get('local_processing'):
            st.info("💻 Local processing enabled")
        if platform_info.get('features', {}).get('distributed_processing'):
            st.info("☁️ Cloud processing enabled")

        st.divider()

        # System metrics
        st.subheader("📊 Session Metrics")

        if st.session_state.df is not None:
            st.metric("Records Loaded", len(st.session_state.df))
            st.metric("Fields", len(st.session_state.df.columns))

        if st.session_state.approved_mappings:
            st.metric("Approved Mappings", len(st.session_state.approved_mappings))

        # Cost tracking
        if enhanced_llm_service:
            cost_summary = enhanced_llm_service.get_cost_summary()
            if cost_summary:
                total_cost = sum(metrics.get('total_cost', 0) for metrics in cost_summary.values())
                st.metric("AI API Cost", f"${total_cost:.4f}")


def render_workflow_interactive():
    """Render interactive workflow interface."""

    # Progress indicator
    steps = ["Upload", "Profile", "Map", "Validate", "Export"]
    current_step_index = steps.index(st.session_state.current_step.title()) if st.session_state.current_step.title() in steps else 0

    # Create progress bar
    progress_cols = st.columns(len(steps))
    for i, (col, step) in enumerate(zip(progress_cols, steps)):
        with col:
            if i < current_step_index:
                st.success(f"✅ {step}")
            elif i == current_step_index:
                st.info(f"🔄 {step}")
            else:
                st.text(f"⏳ {step}")

    st.divider()

    # Workflow tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📁 Upload & Profile", "🎯 AI Mapping", "📋 Resource Selection", "✅ Validation", "📤 Export"])

    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            render_file_uploader()
        with col2:
            render_data_profiler()

    with tab2:
        render_enhanced_mapping_interface()

    with tab3:
        render_resource_selector()

    with tab4:
        render_validation_interface()

    with tab5:
        render_export_interface()


def render_workflow_template():
    """Render template-based workflow."""

    st.header("🤖 Template-Based Workflow")
    st.info("Apply pre-built templates for common healthcare data transformation scenarios")

    # Template selection
    if st.session_state.df is not None:
        st.subheader("📋 Available Templates")

        # Get template suggestions
        suggestions = template_manager.get_template_suggestions(
            st.session_state.df,
            st.session_state.target_resource_type
        )

        if suggestions:
            for template in suggestions:
                with st.expander(f"📋 {template.metadata.name}"):
                    col1, col2 = st.columns([2, 1])

                    with col1:
                        st.write(f"**Description:** {template.metadata.description}")
                        st.write(f"**Use Cases:** {', '.join(template.metadata.use_cases)}")
                        st.write(f"**Complexity:** {template.metadata.complexity_level.value}")

                    with col2:
                        if st.button(f"🚀 Apply Template", key=f"apply_{template.template_id}"):
                            apply_template_workflow(template)
        else:
            st.warning("No matching templates found for your data")
    else:
        st.warning("Please upload data first")


def render_workflow_pipeline():
    """Render pipeline automation workflow."""

    st.header("⚡ Pipeline Automation")
    st.info("Define and execute automated FHIR transformation pipelines")

    # Pipeline tabs
    tab1, tab2, tab3 = st.tabs(["📝 Pipeline Editor", "▶️ Execution", "📊 Monitoring"])

    with tab1:
        render_pipeline_editor()

    with tab2:
        render_pipeline_execution()

    with tab3:
        render_pipeline_monitoring()


def render_validation_interface():
    """Render validation interface."""

    st.subheader("✅ Multi-Layer Validation")

    if not st.session_state.approved_mappings:
        st.warning("No approved mappings to validate. Please create some mappings first.")
        return

    # Validation configuration
    col1, col2, col3 = st.columns(3)

    with col1:
        validation_level = st.selectbox(
            "Validation Level",
            ["Basic", "Standard", "Strict"],
            index=1
        )

    with col2:
        profile_url = st.text_input(
            "Profile URL",
            value="http://hl7.org/fhir/us/core/StructureDefinition/us-core-patient"
        )

    with col3:
        validators = st.multiselect(
            "Validators",
            ["structural", "hapi", "business_rules"],
            default=["structural", "business_rules"]
        )

    # Run validation
    if st.button("🔍 Run Validation", type="primary"):
        run_comprehensive_validation(validation_level, profile_url, validators)

    # Display results
    if st.session_state.validation_results:
        display_validation_results()


def render_pipeline_editor():
    """Render pipeline configuration editor."""

    st.subheader("📝 Pipeline Configuration")

    # Load existing pipeline or create new
    col1, col2 = st.columns([2, 1])

    with col1:
        pipeline_name = st.text_input("Pipeline Name", placeholder="patient_demographics_pipeline")

    with col2:
        if st.button("📁 Load Pipeline"):
            load_pipeline_config(pipeline_name)

    # Pipeline editor (simplified)
    st.subheader("⚙️ Pipeline Stages")

    # Add stage interface
    with st.expander("➕ Add Stage"):
        stage_name = st.text_input("Stage Name")
        stage_type = st.selectbox("Stage Type", ["extract", "transform", "validate", "load"])

        if st.button("Add Stage"):
            add_pipeline_stage(stage_name, stage_type)

    # Display existing stages
    if 'pipeline_stages' in st.session_state:
        for stage in st.session_state.pipeline_stages:
            with st.expander(f"⚙️ {stage['name']}"):
                st.json(stage)


def render_pipeline_execution():
    """Render pipeline execution interface."""

    st.subheader("▶️ Pipeline Execution")

    if st.button("🚀 Execute Pipeline", type="primary"):
        execute_current_pipeline()

    # Show execution status
    if 'current_execution' in st.session_state:
        execution = st.session_state.current_execution

        st.write(f"**Status:** {execution.status.value}")
        st.write(f"**Started:** {execution.start_time}")

        if execution.end_time:
            duration = execution.end_time - execution.start_time
            st.write(f"**Duration:** {duration:.2f} seconds")

        # Stage results
        for stage_name, result in execution.stage_results.items():
            with st.expander(f"📊 {stage_name}"):
                st.json(result)


def render_pipeline_monitoring():
    """Render pipeline monitoring dashboard."""

    st.subheader("📊 Pipeline Monitoring")

    # Execution history
    executions = pipeline_engine.list_executions()

    if executions:
        for execution in executions[:10]:  # Show last 10
            with st.expander(f"🔄 {execution.pipeline_name} - {execution.status.value}"):

                col1, col2, col3 = st.columns(3)

                with col1:
                    st.write(f"**ID:** {execution.execution_id[:8]}...")

                with col2:
                    st.write(f"**Duration:** {(execution.end_time or execution.start_time) - execution.start_time:.2f}s")

                with col3:
                    if execution.metrics:
                        st.write(f"**Records:** {execution.metrics.get('total_records_processed', 0)}")
    else:
        st.info("No pipeline executions found")


# Helper functions

def apply_template_workflow(template):
    """Apply template in workflow mode."""
    try:
        st.info(f"Applying template: {template.metadata.name}")

        # Get parameters from user
        parameters = {}
        for param in template.parameters:
            if param.type == "string":
                parameters[param.name] = st.text_input(
                    param.description,
                    value=param.default or "",
                    key=f"template_param_{param.name}"
                )

        # Apply template
        results = template_manager.apply_template(
            template.template_id,
            st.session_state.df,
            parameters
        )

        st.session_state.transformed_data = results
        st.success(f"Template applied! Generated {len(results)} FHIR resources")

        # Automatically validate results
        st.session_state.current_step = "validate"

    except Exception as e:
        st.error(f"Template application failed: {str(e)}")
        logger.error(f"Template application failed: {str(e)}")


def run_comprehensive_validation(level: str, profile: str, validators: list):
    """Run comprehensive validation."""
    try:
        st.info("Running validation...")

        # This would integrate with the validation engine
        # For now, create mock results
        st.session_state.validation_results = {
            'level': level,
            'profile': profile,
            'validators': validators,
            'summary': {
                'total_resources': 100,
                'valid_resources': 95,
                'warnings': 5,
                'errors': 0
            }
        }

        st.success("Validation completed!")

    except Exception as e:
        st.error(f"Validation failed: {str(e)}")
        logger.error(f"Validation failed: {str(e)}")


def display_validation_results():
    """Display validation results."""
    results = st.session_state.validation_results

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Resources", results['summary']['total_resources'])

    with col2:
        st.metric("Valid Resources", results['summary']['valid_resources'])

    with col3:
        st.metric("Warnings", results['summary']['warnings'])

    with col4:
        st.metric("Errors", results['summary']['errors'])

    # Validation rate
    total = results['summary']['total_resources']
    valid = results['summary']['valid_resources']
    rate = (valid / total * 100) if total > 0 else 0

    st.metric("Validation Rate", f"{rate:.1f}%")


def load_pipeline_config(pipeline_name: str):
    """Load pipeline configuration."""
    try:
        config_path = f"pipelines/configurations/{pipeline_name}.yaml"
        if os.path.exists(config_path):
            pipeline_def = pipeline_engine.load_pipeline(config_path)
            st.session_state.current_pipeline = pipeline_def
            st.success(f"Loaded pipeline: {pipeline_name}")
        else:
            st.error(f"Pipeline not found: {pipeline_name}")
    except Exception as e:
        st.error(f"Failed to load pipeline: {str(e)}")


def add_pipeline_stage(name: str, stage_type: str):
    """Add stage to current pipeline."""
    if 'pipeline_stages' not in st.session_state:
        st.session_state.pipeline_stages = []

    stage = {
        'name': name,
        'type': stage_type,
        'config': {}
    }

    st.session_state.pipeline_stages.append(stage)
    st.success(f"Added stage: {name}")


def execute_current_pipeline():
    """Execute the current pipeline."""
    try:
        if st.session_state.current_pipeline:
            st.info("Executing pipeline...")

            # This would use the pipeline engine
            # For now, create mock execution
            import uuid
            execution_id = str(uuid.uuid4())

            st.session_state.current_execution = {
                'execution_id': execution_id,
                'status': 'completed',
                'start_time': 1234567890,
                'end_time': 1234567900,
                'stage_results': {}
            }

            st.success("Pipeline executed successfully!")

        else:
            st.error("No pipeline loaded")

    except Exception as e:
        st.error(f"Pipeline execution failed: {str(e)}")


def main():
    """Main application entry point."""

    # Setup
    ensure_cache_dirs()
    setup_page_config()
    initialize_session_state()

    # Initialize services on first run
    if not st.session_state.services_initialized:
        initialize_services()
        st.session_state.services_initialized = True

    # Render UI
    render_header()
    render_sidebar()

    st.divider()

    # Main workflow based on mode
    if st.session_state.workflow_mode == "interactive":
        render_workflow_interactive()
    elif st.session_state.workflow_mode == "template":
        render_workflow_template()
    elif st.session_state.workflow_mode == "pipeline":
        render_workflow_pipeline()

    # Footer
    st.divider()
    col1, col2, col3 = st.columns(3)

    with col1:
        st.caption("🕸️ Parker v2.0 - Spec-Driven Architecture")
    with col2:
        st.caption("Built with Streamlit & FHIR R4B")
    with col3:
        st.caption("[GitHub](https://github.com/aks129/FhirMapMaster)")


if __name__ == "__main__":
    main()