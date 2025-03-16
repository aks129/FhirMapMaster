"""
Profile selector component for pre-mapping configuration.
This component allows users to select which FHIR profiles they want to map their data to.
"""
import streamlit as st
import pandas as pd
from utils.fhir_mapper import get_fhir_resources

def render_resource_selector():
    """
    Render the FHIR profile selection interface.
    This step comes before mapping to let users select which profiles they want to map to.
    """
    st.header("🕸️ Profile Selection Configuration")
    
    st.markdown("""
    ### *"Choose your web anchors before spinning the web!"*
    
    Parker will help you map your data to FHIR profiles, but first, select which FHIR profiles 
    you want to include in your mapping. This helps focus the mapping process on just what you need.
    """)
    
    # Get available resources based on the selected implementation guide
    fhir_standard = st.session_state.fhir_standard
    ig_version = st.session_state.ig_version
    
    st.info(f"Configuring resources for **{fhir_standard} {ig_version}** Implementation Guide")
    
    # Get resources with the specific version
    fhir_resources = get_fhir_resources(fhir_standard, ig_version)
    
    # Initialize selected_resources in session state if not present
    if 'selected_resources' not in st.session_state:
        st.session_state.selected_resources = {}
    
    # Group resources by category for better organization
    resource_categories = {
        "Clinical": ["Patient", "Practitioner", "PractitionerRole", "RelatedPerson", "Person", "Organization", "Location"],
        "Clinical Summary": ["AllergyIntolerance", "Condition", "Procedure", "FamilyMemberHistory", "CarePlan", "Goal", "DiagnosticReport", "DocumentReference"],
        "Diagnostics": ["Observation", "ImagingStudy", "MolecularSequence"],
        "Medications": ["Medication", "MedicationRequest", "MedicationAdministration", "MedicationDispense", "MedicationStatement"],
        "Workflow": ["Encounter", "Appointment", "Schedule", "Slot", "AppointmentResponse"],
        "Financial": ["Coverage", "ExplanationOfBenefit", "Claim", "ClaimResponse", "PaymentNotice"],
        "Specialized": ["Device", "DeviceRequest", "SupplyDelivery", "SupplyRequest", "Immunization", "ImmunizationRecommendation", "ServiceRequest"],
        "Other": []
    }
    
    # Put any unmatched resources in the Other category
    all_categorized = [item for sublist in resource_categories.values() for item in sublist]
    for resource in fhir_resources:
        if resource not in all_categorized:
            resource_categories["Other"].append(resource)
    
    # Filter out empty categories
    filtered_categories = {k: v for k, v in resource_categories.items() 
                           if any(r in fhir_resources for r in v)}
    
    st.markdown("## Select FHIR Profiles")
    
    st.markdown("""
    Choose which FHIR profiles you want to include in your mapping. Parker will help you map your data 
    to these profiles based on the implementation guide you selected.
    """)
    
    # Quick select options
    quick_select = st.radio(
        "Quick Profile Selection:",
        [
            "🕸️ Select Individual Profiles",
            "🌟 Clinical Basics (Patient, Condition, Observation, etc.)",
            "💊 Medication-focused (Patient, Medication, MedicationRequest, etc.)",
            "💰 Financial (Patient, Coverage, ExplanationOfBenefit, etc.)"
        ],
        index=0
    )
    
    # Apply quick selections if chosen
    if "Clinical Basics" in quick_select and quick_select != st.session_state.get('last_quick_select'):
        basic_resources = ["Patient", "Condition", "Observation", "AllergyIntolerance", "Procedure", "Encounter"]
        st.session_state.selected_resources = {r: True for r in basic_resources if r in fhir_resources}
        st.session_state.last_quick_select = quick_select
        
    elif "Medication-focused" in quick_select and quick_select != st.session_state.get('last_quick_select'):
        med_resources = ["Patient", "Medication", "MedicationRequest", "MedicationStatement", "MedicationAdministration", "Practitioner"]
        st.session_state.selected_resources = {r: True for r in med_resources if r in fhir_resources}
        st.session_state.last_quick_select = quick_select
        
    elif "Financial" in quick_select and quick_select != st.session_state.get('last_quick_select'):
        financial_resources = ["Patient", "Coverage", "ExplanationOfBenefit", "Claim", "Organization"]
        st.session_state.selected_resources = {r: True for r in financial_resources if r in fhir_resources}
        st.session_state.last_quick_select = quick_select
    
    elif "Individual Resources" in quick_select and quick_select != st.session_state.get('last_quick_select'):
        # Reset to individual selection mode
        st.session_state.selected_resources = {}
        st.session_state.last_quick_select = quick_select
    
    # Display profiles by category with checkboxes
    st.markdown("### Profile Categories")
    
    for category, resources in filtered_categories.items():
        # Only show categories that have profiles in the selected IG
        resources = [r for r in resources if r in fhir_resources]
        if not resources:
            continue
            
        with st.expander(f"{category} Profiles"):
            for resource in resources:
                resource_key = f"resource_{resource}"
                # Initialize with current selection state or default to False
                current_selection = st.session_state.selected_resources.get(resource, False)
                
                if st.checkbox(
                    f"{resource}",
                    value=current_selection,
                    key=resource_key,
                    help=f"Include {resource} in your FHIR mapping"
                ):
                    st.session_state.selected_resources[resource] = True
                else:
                    # Remove if it was previously selected but now unchecked
                    if resource in st.session_state.selected_resources:
                        st.session_state.selected_resources.pop(resource)
    
    # Show summary of selected profiles
    st.markdown("## Selected Profiles")
    
    if st.session_state.selected_resources:
        st.success(f"You've selected {len(st.session_state.selected_resources)} profiles for mapping.")
        
        # Display the selected profiles
        for resource in st.session_state.selected_resources:
            st.write(f"✅ {resource}")
    else:
        st.warning("No profiles selected. Please select at least one profile for mapping.")
    
    # Navigation buttons
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔙 Back to Data Profiling"):
            return False
            
    with col2:
        proceed_button = st.button("Continue to Mapping 🔜", disabled=not st.session_state.selected_resources)
        if proceed_button:
            # Ensure we have at least one profile selected
            if st.session_state.selected_resources:
                return True
            else:
                st.error("Please select at least one profile before continuing.")
                return False
    
    return False

def get_resource_profiles(ig_name, version):
    """
    Get profiles available for a specific implementation guide and version.
    
    Args:
        ig_name: The implementation guide name (US Core or CARIN BB)
        version: The version of the implementation guide
        
    Returns:
        dict: Dictionary of resource type to available profiles
    """
    # Default profiles based on implementation guide
    profiles = {}
    
    if "US Core" in ig_name:
        # US Core has specific profiles for many resource types
        # Complete profile list from https://hl7.org/fhir/us/core/profiles-and-extensions.html#profiles
        profiles = {
            "Patient": [f"http://hl7.org/fhir/us/core/StructureDefinition/us-core-patient"],
            "Practitioner": [f"http://hl7.org/fhir/us/core/StructureDefinition/us-core-practitioner"],
            "PractitionerRole": [f"http://hl7.org/fhir/us/core/StructureDefinition/us-core-practitionerrole"],
            "Organization": [f"http://hl7.org/fhir/us/core/StructureDefinition/us-core-organization"],
            "Location": [f"http://hl7.org/fhir/us/core/StructureDefinition/us-core-location"],
            "Encounter": [f"http://hl7.org/fhir/us/core/StructureDefinition/us-core-encounter"],
            "Condition": [
                f"http://hl7.org/fhir/us/core/StructureDefinition/us-core-condition-problems-health-concerns",
                f"http://hl7.org/fhir/us/core/StructureDefinition/us-core-condition-encounter-diagnosis"
            ],
            "Procedure": [f"http://hl7.org/fhir/us/core/StructureDefinition/us-core-procedure"],
            "AllergyIntolerance": [f"http://hl7.org/fhir/us/core/StructureDefinition/us-core-allergyintolerance"],
            "Medication": [f"http://hl7.org/fhir/us/core/StructureDefinition/us-core-medication"],
            "MedicationRequest": [f"http://hl7.org/fhir/us/core/StructureDefinition/us-core-medicationrequest"],
            "Immunization": [f"http://hl7.org/fhir/us/core/StructureDefinition/us-core-immunization"],
            "CarePlan": [f"http://hl7.org/fhir/us/core/StructureDefinition/us-core-careplan"],
            "CareTeam": [f"http://hl7.org/fhir/us/core/StructureDefinition/us-core-careteam"],
            "Goal": [f"http://hl7.org/fhir/us/core/StructureDefinition/us-core-goal"],
            "ServiceRequest": [f"http://hl7.org/fhir/us/core/StructureDefinition/us-core-servicerequest"],
            "Provenance": [f"http://hl7.org/fhir/us/core/StructureDefinition/us-core-provenance"],
            "Device": [f"http://hl7.org/fhir/us/core/StructureDefinition/us-core-implantable-device"],
            "RelatedPerson": [f"http://hl7.org/fhir/us/core/StructureDefinition/us-core-relatedperson"],
            "Specimen": [f"http://hl7.org/fhir/us/core/StructureDefinition/us-core-specimen"],
            "QuestionnaireResponse": [f"http://hl7.org/fhir/us/core/StructureDefinition/us-core-questionnaireresponse"],
            "Observation": [
                f"http://hl7.org/fhir/us/core/StructureDefinition/us-core-observation-lab",
                f"http://hl7.org/fhir/us/core/StructureDefinition/us-core-vital-signs",
                f"http://hl7.org/fhir/us/core/StructureDefinition/us-core-bloodpressure",
                f"http://hl7.org/fhir/us/core/StructureDefinition/us-core-bodytemp",
                f"http://hl7.org/fhir/us/core/StructureDefinition/us-core-bodyheight",
                f"http://hl7.org/fhir/us/core/StructureDefinition/us-core-bodyweight",
                f"http://hl7.org/fhir/us/core/StructureDefinition/us-core-bmi",
                f"http://hl7.org/fhir/us/core/StructureDefinition/us-core-head-circumference",
                f"http://hl7.org/fhir/us/core/StructureDefinition/us-core-heartrate",
                f"http://hl7.org/fhir/us/core/StructureDefinition/us-core-respiratory-rate",
                f"http://hl7.org/fhir/us/core/StructureDefinition/us-core-pulse-oximetry",
                f"http://hl7.org/fhir/us/core/StructureDefinition/us-core-smokingstatus",
                f"http://hl7.org/fhir/us/core/StructureDefinition/us-core-observation-clinical-result",
                f"http://hl7.org/fhir/us/core/StructureDefinition/us-core-observation-clinical-test",
                f"http://hl7.org/fhir/us/core/StructureDefinition/us-core-observation-imaging",
                f"http://hl7.org/fhir/us/core/StructureDefinition/us-core-observation-sdoh-assessment",
                f"http://hl7.org/fhir/us/core/StructureDefinition/us-core-observation-sexual-orientation",
                f"http://hl7.org/fhir/us/core/StructureDefinition/us-core-observation-social-history",
                f"http://hl7.org/fhir/us/core/StructureDefinition/us-core-observation-survey",
                f"http://hl7.org/fhir/us/core/StructureDefinition/us-core-pediatric-bmi-for-age",
                f"http://hl7.org/fhir/us/core/StructureDefinition/us-core-pediatric-head-occipital-frontal-circumference-percentile",
                f"http://hl7.org/fhir/us/core/StructureDefinition/us-core-pediatric-weight-for-height",
                f"http://hl7.org/fhir/us/core/StructureDefinition/us-core-waist-circumference",
                f"http://hl7.org/fhir/us/core/StructureDefinition/us-core-simple-observation"
            ],
            "DiagnosticReport": [
                f"http://hl7.org/fhir/us/core/StructureDefinition/us-core-diagnosticreport-lab",
                f"http://hl7.org/fhir/us/core/StructureDefinition/us-core-diagnosticreport-note"
            ],
            "DocumentReference": [f"http://hl7.org/fhir/us/core/StructureDefinition/us-core-documentreference"]
        }
    elif "CARIN BB" in ig_name:
        # CARIN BB focuses on financial and insurance resources
        profiles = {
            "Patient": [f"http://hl7.org/fhir/us/carin-bb/{version}/StructureDefinition/C4BB-Patient"],
            "Coverage": [f"http://hl7.org/fhir/us/carin-bb/{version}/StructureDefinition/C4BB-Coverage"],
            "ExplanationOfBenefit": [
                f"http://hl7.org/fhir/us/carin-bb/{version}/StructureDefinition/C4BB-ExplanationOfBenefit",
                f"http://hl7.org/fhir/us/carin-bb/{version}/StructureDefinition/C4BB-ExplanationOfBenefit-Inpatient-Institutional",
                f"http://hl7.org/fhir/us/carin-bb/{version}/StructureDefinition/C4BB-ExplanationOfBenefit-Outpatient-Institutional",
                f"http://hl7.org/fhir/us/carin-bb/{version}/StructureDefinition/C4BB-ExplanationOfBenefit-Pharmacy",
                f"http://hl7.org/fhir/us/carin-bb/{version}/StructureDefinition/C4BB-ExplanationOfBenefit-Professional-NonClinician"
            ],
            "Organization": [f"http://hl7.org/fhir/us/carin-bb/{version}/StructureDefinition/C4BB-Organization"],
            "Practitioner": [f"http://hl7.org/fhir/us/carin-bb/{version}/StructureDefinition/C4BB-Practitioner"]
        }
    
    return profiles