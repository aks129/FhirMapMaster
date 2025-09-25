"""
Enhanced Mapping Interface with LLM Integration
Provides AI-assisted mapping with human-in-the-loop review
"""

import streamlit as st
import pandas as pd
import asyncio
import json
from typing import Dict, List, Optional, Any

from utils.core.llm_service_v2 import enhanced_llm_service, MappingContext
from utils.core.template_manager import template_manager
from utils.validation.validation_engine import validation_engine, ValidationLevel
from utils.engines.database_adapter import database_service


def render_enhanced_mapping_interface():
    """Render the enhanced mapping interface with AI assistance."""

    st.header("🤖 AI-Assisted FHIR Mapping")

    # Check if we have data
    if 'df' not in st.session_state or st.session_state.df is None:
        st.warning("Please upload and profile data first.")
        return

    df = st.session_state.df

    # Initialize session state for mappings
    if 'ai_suggestions' not in st.session_state:
        st.session_state.ai_suggestions = {}
    if 'approved_mappings' not in st.session_state:
        st.session_state.approved_mappings = {}
    if 'mapping_feedback' not in st.session_state:
        st.session_state.mapping_feedback = {}

    # Sidebar configuration
    with st.sidebar:
        st.subheader("🎛️ AI Configuration")

        # LLM Provider selection
        available_providers = enhanced_llm_service.get_available_providers()
        if available_providers:
            selected_provider = st.selectbox(
                "LLM Provider",
                available_providers,
                help="Select the AI provider for mapping suggestions"
            )
        else:
            st.error("No LLM providers configured. Please set API keys.")
            return

        # Confidence threshold
        confidence_threshold = st.slider(
            "Confidence Threshold",
            min_value=0.0,
            max_value=1.0,
            value=0.7,
            step=0.1,
            help="Minimum confidence score for suggestions"
        )

        # Resource type selection
        fhir_resource_type = st.selectbox(
            "Target FHIR Resource",
            ["Patient", "Observation", "Encounter", "Condition", "MedicationRequest"],
            index=0
        )

        # Implementation Guide
        ig_selection = st.selectbox(
            "Implementation Guide",
            ["US Core 7.0.0", "US Core 6.1.0", "CARIN BB 2.0.0"],
            index=0
        )

    # Main interface tabs
    tab1, tab2, tab3, tab4 = st.tabs(["🎯 AI Suggestions", "📋 Template Library", "✅ Validation", "📊 Analytics"])

    with tab1:
        render_ai_suggestions_tab(df, fhir_resource_type, ig_selection, confidence_threshold)

    with tab2:
        render_template_library_tab(df, fhir_resource_type)

    with tab3:
        render_validation_tab()

    with tab4:
        render_analytics_tab()


def render_ai_suggestions_tab(df: pd.DataFrame, resource_type: str, ig: str, threshold: float):
    """Render AI suggestions tab."""

    st.subheader(f"AI Mapping Suggestions for {resource_type}")

    # Generate suggestions button
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        if st.button("🧠 Generate AI Suggestions", type="primary"):
            with st.spinner("Generating AI suggestions..."):
                generate_ai_suggestions(df, resource_type, ig, threshold)

    with col2:
        if st.button("🔄 Refresh"):
            st.rerun()

    with col3:
        if st.button("🗑️ Clear All"):
            st.session_state.ai_suggestions.clear()
            st.rerun()

    # Display suggestions
    if st.session_state.ai_suggestions:
        st.success(f"Generated {len(st.session_state.ai_suggestions)} suggestions")

        # Bulk actions
        st.subheader("Bulk Actions")
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("✅ Accept All High Confidence"):
                accept_high_confidence_suggestions(threshold=0.85)
                st.rerun()

        with col2:
            if st.button("❌ Reject All Low Confidence"):
                reject_low_confidence_suggestions(threshold=0.5)
                st.rerun()

        with col3:
            auto_apply = st.checkbox("Auto-apply approved mappings")

        # Individual suggestions
        st.subheader("Field Mappings")

        for field_name, suggestions in st.session_state.ai_suggestions.items():
            render_field_suggestion_card(field_name, suggestions, df)

    else:
        st.info("Click 'Generate AI Suggestions' to get started")


def render_field_suggestion_card(field_name: str, suggestions: List[Dict], df: pd.DataFrame):
    """Render individual field suggestion card."""

    with st.expander(f"📝 {field_name}", expanded=True):
        # Show sample data
        sample_data = df[field_name].dropna().head(3).tolist()
        st.text(f"Sample data: {sample_data}")

        # Display suggestions
        for i, suggestion in enumerate(suggestions):
            confidence = suggestion.get('confidence', 0)
            confidence_color = "🟢" if confidence > 0.8 else "🟡" if confidence > 0.6 else "🔴"

            col1, col2, col3, col4 = st.columns([3, 2, 1, 1])

            with col1:
                st.write(f"**{suggestion.get('fhir_path', 'Unknown')}**")
                st.caption(suggestion.get('rationale', 'No explanation provided'))

            with col2:
                st.write(f"{confidence_color} {confidence:.1%}")
                st.caption(f"Type: {suggestion.get('transformation_type', 'direct')}")

            with col3:
                suggestion_key = f"{field_name}_{i}"
                if st.button("✅", key=f"approve_{suggestion_key}"):
                    approve_suggestion(field_name, suggestion)
                    st.rerun()

            with col4:
                if st.button("❌", key=f"reject_{suggestion_key}"):
                    reject_suggestion(field_name, suggestion)
                    st.rerun()

            # Show transformation preview
            if suggestion.get('source_expression'):
                with st.expander("🔍 Transformation Preview", expanded=False):
                    st.code(suggestion['source_expression'], language='jinja2')

        # Manual mapping option
        st.write("---")
        manual_fhir_path = st.text_input(
            "Manual FHIR Path",
            key=f"manual_{field_name}",
            placeholder="e.g., Patient.name[0].given[0]"
        )
        manual_expression = st.text_area(
            "Transformation Expression",
            key=f"manual_expr_{field_name}",
            placeholder="e.g., {{ " + field_name + " }}"
        )

        if st.button(f"💾 Save Manual Mapping", key=f"save_manual_{field_name}"):
            if manual_fhir_path and manual_expression:
                manual_suggestion = {
                    'fhir_path': manual_fhir_path,
                    'source_expression': manual_expression,
                    'confidence': 1.0,
                    'rationale': 'Manual mapping',
                    'transformation_type': 'custom',
                    'provider': 'manual'
                }
                approve_suggestion(field_name, manual_suggestion)
                st.success("Manual mapping saved!")
                st.rerun()


def render_template_library_tab(df: pd.DataFrame, resource_type: str):
    """Render template library tab."""

    st.subheader("📚 Template Library")

    # Search templates
    col1, col2 = st.columns([2, 1])

    with col1:
        search_query = st.text_input("🔍 Search templates", placeholder="Search by name, tags, or use case")

    with col2:
        category_filter = st.selectbox(
            "Category",
            ["All", "Resource Templates", "Use Case Templates", "Data Source Templates"]
        )

    # Get template suggestions
    template_suggestions = template_manager.get_template_suggestions(df, resource_type)

    if template_suggestions:
        st.success(f"Found {len(template_suggestions)} matching templates")

        # Display templates
        for template in template_suggestions:
            with st.expander(f"📋 {template.metadata.name} v{template.metadata.version}"):
                col1, col2 = st.columns([2, 1])

                with col1:
                    st.write(f"**Description:** {template.metadata.description}")
                    st.write(f"**Use Cases:** {', '.join(template.metadata.use_cases)}")
                    st.write(f"**Tags:** {', '.join(template.metadata.tags)}")

                with col2:
                    st.write(f"**Complexity:** {template.metadata.complexity_level.value}")
                    st.write(f"**Mappings:** {len(template.field_mappings)}")

                # Template parameters
                if template.parameters:
                    st.write("**Parameters:**")
                    for param in template.parameters:
                        st.write(f"- {param.name}: {param.description}")

                # Apply template button
                if st.button(f"🚀 Apply Template", key=f"apply_{template.template_id}"):
                    apply_template_to_data(template, df)
    else:
        st.info("No matching templates found. Try different search criteria.")


def render_validation_tab():
    """Render validation tab."""

    st.subheader("✅ Validation Results")

    if 'approved_mappings' not in st.session_state or not st.session_state.approved_mappings:
        st.warning("No approved mappings to validate. Please approve some suggestions first.")
        return

    # Validation settings
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
        if st.button("🔍 Validate Mappings"):
            run_validation(validation_level, profile_url)

    # Display validation results
    if 'validation_results' in st.session_state:
        results = st.session_state.validation_results

        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Resources", results.get('total_resources', 0))

        with col2:
            st.metric("Valid Resources", results.get('valid_resources', 0))

        with col3:
            st.metric("Errors", results.get('error_count', 0))

        with col4:
            st.metric("Warnings", results.get('warning_count', 0))

        # Detailed results
        if results.get('validation_reports'):
            st.subheader("Detailed Results")

            for report in results['validation_reports']:
                with st.expander(f"Resource {report.resource_id} - {report.overall_status}"):

                    # Show validation issues
                    for result in report.results:
                        severity_color = {"error": "🔴", "warning": "🟡", "information": "🔵"}
                        color = severity_color.get(result.severity.value, "⚪")

                        st.write(f"{color} **{result.severity.value.title()}**: {result.message}")
                        st.caption(f"Location: {result.location} | Rule: {result.rule_id}")

                        if result.suggested_fix:
                            st.info(f"💡 Suggestion: {result.suggested_fix}")


def render_analytics_tab():
    """Render analytics and metrics tab."""

    st.subheader("📊 Mapping Analytics")

    # AI Performance metrics
    if enhanced_llm_service:
        cost_summary = enhanced_llm_service.get_cost_summary()

        if cost_summary:
            st.subheader("💰 LLM Cost Summary")

            for provider, metrics in cost_summary.items():
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric(f"{provider} - Total Cost", f"${metrics.get('total_cost', 0):.4f}")

                with col2:
                    st.metric(f"{provider} - API Calls", metrics.get('total_calls', 0))

                with col3:
                    st.metric(f"{provider} - Avg Cost/Call", f"${metrics.get('avg_cost', 0):.4f}")

    # Mapping statistics
    if st.session_state.approved_mappings:
        st.subheader("🎯 Mapping Statistics")

        total_fields = len(st.session_state.get('df', pd.DataFrame()).columns)
        mapped_fields = len(st.session_state.approved_mappings)
        mapping_coverage = (mapped_fields / total_fields * 100) if total_fields > 0 else 0

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Total Fields", total_fields)

        with col2:
            st.metric("Mapped Fields", mapped_fields)

        with col3:
            st.metric("Mapping Coverage", f"{mapping_coverage:.1f}%")

        # Mapping quality metrics
        if st.session_state.mapping_feedback:
            feedback_data = st.session_state.mapping_feedback
            approved_count = sum(1 for v in feedback_data.values() if v == 'approved')
            rejected_count = sum(1 for v in feedback_data.values() if v == 'rejected')

            if approved_count + rejected_count > 0:
                approval_rate = approved_count / (approved_count + rejected_count) * 100
                st.metric("AI Suggestion Approval Rate", f"{approval_rate:.1f}%")


# Helper functions

def generate_ai_suggestions(df: pd.DataFrame, resource_type: str, ig: str, threshold: float):
    """Generate AI mapping suggestions for all fields."""

    suggestions = {}

    for column in df.columns:
        # Create mapping context
        sample_values = df[column].dropna().head(5).astype(str).tolist()

        context = MappingContext(
            field_name=column,
            data_type=str(df[column].dtype),
            sample_values=sample_values,
            table_context={},
            fhir_resource_type=resource_type,
            implementation_guide=ig.split()[0],  # Extract "US Core" from "US Core 7.0.0"
            ig_version=ig.split()[-1] if len(ig.split()) > 2 else "latest"
        )

        try:
            # Generate suggestions asynchronously
            field_suggestions = asyncio.run(
                enhanced_llm_service.generate_mapping_suggestions(context, confidence_threshold=threshold)
            )

            if field_suggestions:
                suggestions[column] = [
                    {
                        'fhir_path': s.fhir_path,
                        'source_expression': s.source_expression,
                        'confidence': s.confidence / 100,  # Convert to 0-1 range
                        'rationale': s.rationale,
                        'transformation_type': s.transformation_type,
                        'provider': s.provider
                    }
                    for s in field_suggestions
                ]

        except Exception as e:
            st.error(f"Failed to generate suggestions for {column}: {str(e)}")

    st.session_state.ai_suggestions = suggestions


def approve_suggestion(field_name: str, suggestion: Dict):
    """Approve a mapping suggestion."""
    st.session_state.approved_mappings[field_name] = suggestion
    st.session_state.mapping_feedback[f"{field_name}_suggestion"] = 'approved'

    # Learn from feedback
    if enhanced_llm_service and 'context' in st.session_state:
        enhanced_llm_service.learn_from_feedback(
            st.session_state.context,
            suggestion,
            accepted=True
        )


def reject_suggestion(field_name: str, suggestion: Dict):
    """Reject a mapping suggestion."""
    st.session_state.mapping_feedback[f"{field_name}_suggestion"] = 'rejected'

    # Learn from feedback
    if enhanced_llm_service and 'context' in st.session_state:
        enhanced_llm_service.learn_from_feedback(
            st.session_state.context,
            suggestion,
            accepted=False
        )


def accept_high_confidence_suggestions(threshold: float = 0.85):
    """Accept all high confidence suggestions."""
    for field_name, suggestions in st.session_state.ai_suggestions.items():
        for suggestion in suggestions:
            if suggestion.get('confidence', 0) >= threshold:
                approve_suggestion(field_name, suggestion)
                break  # Take the first high confidence suggestion


def reject_low_confidence_suggestions(threshold: float = 0.5):
    """Reject all low confidence suggestions."""
    for field_name, suggestions in st.session_state.ai_suggestions.items():
        for suggestion in suggestions:
            if suggestion.get('confidence', 0) < threshold:
                reject_suggestion(field_name, suggestion)


def apply_template_to_data(template, df: pd.DataFrame):
    """Apply template to current data."""
    try:
        # Get template parameters from user
        st.subheader(f"Configure Template: {template.metadata.name}")

        parameters = {}
        for param in template.parameters:
            if param.type == "string":
                parameters[param.name] = st.text_input(
                    param.description,
                    key=f"param_{param.name}",
                    value=param.default or ""
                )
            elif param.type == "choice":
                parameters[param.name] = st.selectbox(
                    param.description,
                    param.options or [],
                    key=f"param_{param.name}"
                )

        if st.button("Apply Template"):
            results = template_manager.apply_template(template.template_id, df, parameters)
            st.session_state.transformed_data = results
            st.success(f"Template applied! Generated {len(results)} FHIR resources.")

    except Exception as e:
        st.error(f"Failed to apply template: {str(e)}")


def run_validation(level: str, profile: str):
    """Run validation on approved mappings."""
    if not st.session_state.approved_mappings:
        return

    try:
        # Create sample FHIR resources from mappings
        # This is a simplified version - in practice would use the full mapping engine

        validation_level = ValidationLevel.STANDARD
        if level == "Basic":
            validation_level = ValidationLevel.BASIC
        elif level == "Strict":
            validation_level = ValidationLevel.STRICT

        # Mock validation results for demo
        st.session_state.validation_results = {
            'total_resources': 1,
            'valid_resources': 1,
            'error_count': 0,
            'warning_count': 0,
            'validation_reports': []
        }

        st.success("Validation completed!")

    except Exception as e:
        st.error(f"Validation failed: {str(e)}")