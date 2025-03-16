import requests
import json
import os
from pathlib import Path
import pandas as pd
import streamlit as st
import time

# Cache directory for downloaded resources
CACHE_DIR = Path("./cache")

def ensure_cache_dir():
    """Ensure the cache directory exists"""
    if not CACHE_DIR.exists():
        CACHE_DIR.mkdir(parents=True)

def fetch_us_core_profiles():
    """
    Get US Core Implementation Guide profiles.
    
    Instead of fetching from external sources which can be unreliable,
    we'll use a predefined set of US Core profiles with their required fields
    and must-support elements as defined in the US Core Implementation Guide.
    
    Returns:
        dict: A dictionary containing US Core profile definitions.
    """
    # Create cache file path
    cache_file = CACHE_DIR / "us_core_profiles.json"
    
    # Check if we have a cached version
    if cache_file.exists():
        try:
            with open(cache_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            st.warning(f"Error reading cached US Core profiles: {str(e)}. Building from scratch.")
    
    # Define our US Core profiles with their core fields
    # This follows US Core 6.1.0 requirements from https://hl7.org/fhir/us/core/
    us_core_profiles = {
        "Patient": {
            "description": "US Core Patient Profile - represents demographics and other administrative information about an individual receiving health care.",
            "fields": {
                "identifier": {
                    "description": "An identifier for this patient.",
                    "cardinality": "1..*",
                    "min": 1,
                    "max": "*",
                    "mustSupport": True
                },
                "name": {
                    "description": "A name associated with the patient.",
                    "cardinality": "1..*",
                    "min": 1,
                    "max": "*", 
                    "mustSupport": True
                },
                "gender": {
                    "description": "Administrative Gender - the gender that the patient is considered to have for administration and record keeping purposes.",
                    "cardinality": "1..1",
                    "min": 1,
                    "max": "1",
                    "mustSupport": True
                },
                "birthDate": {
                    "description": "The date of birth for the individual.",
                    "cardinality": "0..1",
                    "min": 0,
                    "max": "1",
                    "mustSupport": True
                },
                "address": {
                    "description": "An address for the individual.",
                    "cardinality": "0..*",
                    "min": 0,
                    "max": "*",
                    "mustSupport": True
                },
                "telecom": {
                    "description": "A contact detail for the individual.",
                    "cardinality": "0..*",
                    "min": 0,
                    "max": "*",
                    "mustSupport": True
                },
                "race": {
                    "description": "Patient's race (US Core Extension).",
                    "cardinality": "0..1",
                    "min": 0,
                    "max": "1", 
                    "mustSupport": True
                },
                "ethnicity": {
                    "description": "Patient's ethnicity (US Core Extension).",
                    "cardinality": "0..1",
                    "min": 0,
                    "max": "1",
                    "mustSupport": True
                },
                "communication": {
                    "description": "Languages which may be used to communicate with the patient.",
                    "cardinality": "0..*",
                    "min": 0,
                    "max": "*",
                    "mustSupport": True
                }
            }
        },
        "Condition": {
            "description": "US Core Condition Profile - represents a clinical condition, problem, diagnosis, or other event, situation, issue, or clinical concept.",
            "fields": {
                "clinicalStatus": {
                    "description": "Active, inactive, etc.",
                    "cardinality": "0..1",
                    "min": 0,
                    "max": "1",
                    "mustSupport": True
                },
                "verificationStatus": {
                    "description": "Whether the condition has been confirmed.",
                    "cardinality": "0..1",
                    "min": 0,
                    "max": "1",
                    "mustSupport": True
                },
                "category": {
                    "description": "Type of condition (problem-list-item, encounter-diagnosis, etc).",
                    "cardinality": "1..*",
                    "min": 1,
                    "max": "*",
                    "mustSupport": True
                },
                "code": {
                    "description": "Identification of the condition, problem or diagnosis.",
                    "cardinality": "1..1",
                    "min": 1,
                    "max": "1",
                    "mustSupport": True
                },
                "subject": {
                    "description": "Who has the condition.",
                    "cardinality": "1..1",
                    "min": 1,
                    "max": "1",
                    "mustSupport": True
                },
                "encounter": {
                    "description": "Encounter when condition first asserted.",
                    "cardinality": "0..1",
                    "min": 0,
                    "max": "1",
                    "mustSupport": True
                },
                "onset": {
                    "description": "When condition first started (date or age).",
                    "cardinality": "0..1",
                    "min": 0,
                    "max": "1",
                    "mustSupport": True
                },
                "abatement": {
                    "description": "When condition resolved (date or age).",
                    "cardinality": "0..1",
                    "min": 0,
                    "max": "1",
                    "mustSupport": True
                },
                "recordedDate": {
                    "description": "Date record was first recorded.",
                    "cardinality": "0..1",
                    "min": 0,
                    "max": "1",
                    "mustSupport": True
                }
            }
        },
        "Observation": {
            "description": "US Core Observation Profile - represents measurements and assertions about a patient.",
            "fields": {
                "status": {
                    "description": "Observation status (final, amended, entered-in-error, etc).",
                    "cardinality": "1..1",
                    "min": 1,
                    "max": "1",
                    "mustSupport": True
                },
                "category": {
                    "description": "Classification of observation.",
                    "cardinality": "1..*",
                    "min": 1,
                    "max": "*",
                    "mustSupport": True
                },
                "code": {
                    "description": "Type of observation.",
                    "cardinality": "1..1",
                    "min": 1,
                    "max": "1",
                    "mustSupport": True
                },
                "subject": {
                    "description": "Who or what the observation is about.",
                    "cardinality": "1..1",
                    "min": 1,
                    "max": "1",
                    "mustSupport": True
                },
                "effectiveDateTime": {
                    "description": "Clinically relevant time for observation.",
                    "cardinality": "0..1",
                    "min": 0,
                    "max": "1",
                    "mustSupport": True
                },
                "valueQuantity": {
                    "description": "Actual result as a quantity.",
                    "cardinality": "0..1",
                    "min": 0,
                    "max": "1",
                    "mustSupport": True
                },
                "valueString": {
                    "description": "Actual result as text.",
                    "cardinality": "0..1",
                    "min": 0,
                    "max": "1",
                    "mustSupport": True
                },
                "valueCodeableConcept": {
                    "description": "Actual result as codeable concept.",
                    "cardinality": "0..1",
                    "min": 0,
                    "max": "1",
                    "mustSupport": True
                }
            }
        },
        "Encounter": {
            "description": "US Core Encounter Profile - represents an interaction between a patient and healthcare provider(s).",
            "fields": {
                "status": {
                    "description": "planned | arrived | triaged | in-progress | onleave | finished | cancelled",
                    "cardinality": "1..1",
                    "min": 1,
                    "max": "1",
                    "mustSupport": True
                },
                "class": {
                    "description": "Classification of encounter (inpatient, outpatient, etc).",
                    "cardinality": "1..1", 
                    "min": 1,
                    "max": "1",
                    "mustSupport": True
                },
                "type": {
                    "description": "Type of encounter.",
                    "cardinality": "0..*",
                    "min": 0,
                    "max": "*",
                    "mustSupport": True
                },
                "subject": {
                    "description": "The patient present at the encounter.",
                    "cardinality": "1..1",
                    "min": 1,
                    "max": "1",
                    "mustSupport": True
                },
                "participant": {
                    "description": "List of participants involved in the encounter.",
                    "cardinality": "0..*",
                    "min": 0,
                    "max": "*",
                    "mustSupport": True
                },
                "period": {
                    "description": "The start and end time of the encounter.",
                    "cardinality": "1..1",
                    "min": 1,
                    "max": "1", 
                    "mustSupport": True
                },
                "diagnosis": {
                    "description": "The list of diagnosis relevant to this encounter.",
                    "cardinality": "0..*",
                    "min": 0,
                    "max": "*",
                    "mustSupport": True
                }
            }
        },
        "AllergyIntolerance": {
            "description": "US Core AllergyIntolerance Profile - represents risk of harmful or undesirable reactions to substances.",
            "fields": {
                "clinicalStatus": {
                    "description": "active | inactive | resolved",
                    "cardinality": "0..1",
                    "min": 0,
                    "max": "1",
                    "mustSupport": True
                },
                "verificationStatus": {
                    "description": "unconfirmed | confirmed | refuted | entered-in-error",
                    "cardinality": "0..1",
                    "min": 0,
                    "max": "1",
                    "mustSupport": True
                },
                "code": {
                    "description": "Code that identifies the allergy or intolerance.",
                    "cardinality": "1..1",
                    "min": 1,
                    "max": "1",
                    "mustSupport": True
                },
                "patient": {
                    "description": "Who the sensitivity is for.",
                    "cardinality": "1..1",
                    "min": 1,
                    "max": "1",
                    "mustSupport": True
                },
                "reaction": {
                    "description": "Adverse reaction events linked to exposure to substance.",
                    "cardinality": "0..*",
                    "min": 0,
                    "max": "*",
                    "mustSupport": True
                }
            }
        },
        "Immunization": {
            "description": "US Core Immunization Profile - represents an immunization event.",
            "fields": {
                "status": {
                    "description": "completed | not-done | entered-in-error",
                    "cardinality": "1..1",
                    "min": 1,
                    "max": "1",
                    "mustSupport": True
                },
                "statusReason": {
                    "description": "Reason for current status.",
                    "cardinality": "0..1",
                    "min": 0,
                    "max": "1",
                    "mustSupport": True
                },
                "vaccineCode": {
                    "description": "Vaccine product administered.",
                    "cardinality": "1..1",
                    "min": 1,
                    "max": "1",
                    "mustSupport": True
                },
                "patient": {
                    "description": "Who was immunized.",
                    "cardinality": "1..1",
                    "min": 1,
                    "max": "1",
                    "mustSupport": True
                },
                "occurrenceDateTime": {
                    "description": "Date vaccine administered.",
                    "cardinality": "1..1",
                    "min": 1,
                    "max": "1",
                    "mustSupport": True
                },
                "primarySource": {
                    "description": "Indicates if this record is from the source who administered the vaccine.",
                    "cardinality": "1..1",
                    "min": 1, 
                    "max": "1",
                    "mustSupport": True
                }
            }
        },
        "MedicationRequest": {
            "description": "US Core MedicationRequest Profile - represents an order for both supply of medication and administration to a patient.",
            "fields": {
                "status": {
                    "description": "active | on-hold | cancelled | completed | entered-in-error | stopped | draft | unknown",
                    "cardinality": "1..1",
                    "min": 1,
                    "max": "1",
                    "mustSupport": True
                },
                "intent": {
                    "description": "proposal | plan | order | original-order | reflex-order | filler-order | instance-order | option",
                    "cardinality": "1..1",
                    "min": 1,
                    "max": "1",
                    "mustSupport": True
                },
                "medicationCodeableConcept": {
                    "description": "What medication was ordered.",
                    "cardinality": "1..1",
                    "min": 1,
                    "max": "1",
                    "mustSupport": True
                },
                "subject": {
                    "description": "Who the medication is for.",
                    "cardinality": "1..1",
                    "min": 1,
                    "max": "1",
                    "mustSupport": True
                },
                "authoredOn": {
                    "description": "When request was initially authored.",
                    "cardinality": "0..1",
                    "min": 0,
                    "max": "1",
                    "mustSupport": True
                },
                "requester": {
                    "description": "Who ordered the medication.",
                    "cardinality": "0..1",
                    "min": 0,
                    "max": "1",
                    "mustSupport": True
                },
                "dosageInstruction": {
                    "description": "How medication should be taken.",
                    "cardinality": "0..*",
                    "min": 0,
                    "max": "*",
                    "mustSupport": True
                }
            }
        },
        "Procedure": {
            "description": "US Core Procedure Profile - represents an action performed on or for a patient.",
            "fields": {
                "status": {
                    "description": "preparation | in-progress | not-done | on-hold | stopped | completed | entered-in-error | unknown",
                    "cardinality": "1..1",
                    "min": 1,
                    "max": "1",
                    "mustSupport": True
                },
                "code": {
                    "description": "Identification of the procedure.",
                    "cardinality": "1..1",
                    "min": 1,
                    "max": "1",
                    "mustSupport": True
                },
                "subject": {
                    "description": "Who the procedure was performed on.",
                    "cardinality": "1..1",
                    "min": 1,
                    "max": "1",
                    "mustSupport": True
                },
                "performedDateTime": {
                    "description": "When the procedure was performed.",
                    "cardinality": "0..1",
                    "min": 0,
                    "max": "1",
                    "mustSupport": True
                },
                "performedPeriod": {
                    "description": "When the procedure was performed (start and end times).",
                    "cardinality": "0..1",
                    "min": 0,
                    "max": "1",
                    "mustSupport": True
                }
            }
        },
        "DiagnosticReport": {
            "description": "US Core DiagnosticReport Profile - represents the findings and interpretation of diagnostic tests performed on a patient.",
            "fields": {
                "status": {
                    "description": "registered | partial | preliminary | final +",
                    "cardinality": "1..1",
                    "min": 1,
                    "max": "1",
                    "mustSupport": True
                },
                "category": {
                    "description": "Classification of report (lab, radiology, etc).",
                    "cardinality": "1..*",
                    "min": 1,
                    "max": "*",
                    "mustSupport": True
                },
                "code": {
                    "description": "The specific test that was performed.",
                    "cardinality": "1..1",
                    "min": 1,
                    "max": "1",
                    "mustSupport": True
                },
                "subject": {
                    "description": "The patient that the report is about.",
                    "cardinality": "1..1",
                    "min": 1,
                    "max": "1",
                    "mustSupport": True
                },
                "effectiveDateTime": {
                    "description": "Clinically relevant time for the report.",
                    "cardinality": "0..1",
                    "min": 0,
                    "max": "1",
                    "mustSupport": True
                },
                "issued": {
                    "description": "DateTime this version was made available.",
                    "cardinality": "0..1",
                    "min": 0,
                    "max": "1",
                    "mustSupport": True
                },
                "result": {
                    "description": "Observations that are part of this diagnostic report.",
                    "cardinality": "0..*",
                    "min": 0,
                    "max": "*",
                    "mustSupport": True
                }
            }
        },
        "DocumentReference": {
            "description": "US Core DocumentReference Profile - represents a reference to a document of any kind.",
            "fields": {
                "status": {
                    "description": "current | superseded | entered-in-error",
                    "cardinality": "1..1",
                    "min": 1,
                    "max": "1",
                    "mustSupport": True
                },
                "type": {
                    "description": "Type of document.",
                    "cardinality": "1..1",
                    "min": 1,
                    "max": "1",
                    "mustSupport": True
                },
                "category": {
                    "description": "The categorization of document.",
                    "cardinality": "1..*",
                    "min": 1,
                    "max": "*",
                    "mustSupport": True
                },
                "subject": {
                    "description": "Who/what is the subject of the document.",
                    "cardinality": "1..1",
                    "min": 1,
                    "max": "1",
                    "mustSupport": True
                },
                "content": {
                    "description": "Document content.",
                    "cardinality": "1..*",
                    "min": 1,
                    "max": "*",
                    "mustSupport": True
                }
            }
        },
        "CarePlan": {
            "description": "US Core CarePlan Profile - describes the intentions of how one or more practitioners intend to deliver care for a particular patient.",
            "fields": {
                "status": {
                    "description": "draft | active | suspended | completed | entered-in-error | cancelled | unknown",
                    "cardinality": "1..1",
                    "min": 1,
                    "max": "1",
                    "mustSupport": True
                },
                "intent": {
                    "description": "proposal | plan | order | option",
                    "cardinality": "1..1",
                    "min": 1,
                    "max": "1",
                    "mustSupport": True
                },
                "subject": {
                    "description": "Who the care plan is for.",
                    "cardinality": "1..1",
                    "min": 1,
                    "max": "1",
                    "mustSupport": True
                },
                "category": {
                    "description": "Category of care plan.",
                    "cardinality": "1..*",
                    "min": 1,
                    "max": "*",
                    "mustSupport": True
                }
            }
        },
        "Goal": {
            "description": "US Core Goal Profile - describes intended objectives for a patient.",
            "fields": {
                "lifecycleStatus": {
                    "description": "proposed | planned | accepted | active | on-hold | completed | cancelled | entered-in-error | rejected",
                    "cardinality": "1..1",
                    "min": 1,
                    "max": "1",
                    "mustSupport": True
                },
                "description": {
                    "description": "Description of the goal.",
                    "cardinality": "1..1",
                    "min": 1,
                    "max": "1",
                    "mustSupport": True
                },
                "subject": {
                    "description": "Who the goal is for.",
                    "cardinality": "1..1",
                    "min": 1,
                    "max": "1",
                    "mustSupport": True
                },
                "target": {
                    "description": "Target outcome for the goal.",
                    "cardinality": "0..1",
                    "min": 0,
                    "max": "1",
                    "mustSupport": True
                }
            }
        },
        "Organization": {
            "description": "US Core Organization Profile - represents a formally or informally recognized grouping of people or organizations.",
            "fields": {
                "identifier": {
                    "description": "Identifies this organization across multiple systems.",
                    "cardinality": "1..*",
                    "min": 1,
                    "max": "*",
                    "mustSupport": True
                },
                "active": {
                    "description": "Whether the organization's record is still in active use.",
                    "cardinality": "0..1",
                    "min": 0,
                    "max": "1",
                    "mustSupport": True
                },
                "name": {
                    "description": "Name used for the organization.",
                    "cardinality": "1..1",
                    "min": 1,
                    "max": "1",
                    "mustSupport": True
                },
                "telecom": {
                    "description": "Contact details for the organization.",
                    "cardinality": "0..*",
                    "min": 0,
                    "max": "*",
                    "mustSupport": True
                },
                "address": {
                    "description": "An address for the organization.",
                    "cardinality": "0..*",
                    "min": 0,
                    "max": "*",
                    "mustSupport": True
                }
            }
        },
        "Practitioner": {
            "description": "US Core Practitioner Profile - represents a person who is directly or indirectly involved in the provisioning of healthcare.",
            "fields": {
                "identifier": {
                    "description": "An identifier for the person as this practitioner.",
                    "cardinality": "1..*",
                    "min": 1,
                    "max": "*",
                    "mustSupport": True
                },
                "name": {
                    "description": "The name(s) associated with the practitioner.",
                    "cardinality": "1..*",
                    "min": 1,
                    "max": "*",
                    "mustSupport": True
                }
            }
        }
    }
    
    # Add additional profiles for vital signs
    vital_signs_profiles = {
        "BloodPressure": {
            "description": "US Core Blood Pressure Profile - represents a systolic and diastolic blood pressure measurement.",
            "fields": {
                "code": {
                    "description": "BloodPressure code.",
                    "cardinality": "1..1",
                    "min": 1,
                    "max": "1",
                    "mustSupport": True
                },
                "component": {
                    "description": "Components for systolic and diastolic pressure.",
                    "cardinality": "2..2",
                    "min": 2,
                    "max": "2",
                    "mustSupport": True
                }
            }
        },
        "HeartRate": {
            "description": "US Core Heart Rate Profile - represents heart rate measurement.",
            "fields": {
                "code": {
                    "description": "Heart rate code.",
                    "cardinality": "1..1",
                    "min": 1,
                    "max": "1", 
                    "mustSupport": True
                },
                "valueQuantity": {
                    "description": "Heart rate value.",
                    "cardinality": "1..1",
                    "min": 1,
                    "max": "1",
                    "mustSupport": True
                }
            }
        },
        "RespiratoryRate": {
            "description": "US Core Respiratory Rate Profile - represents respiratory rate measurement.",
            "fields": {
                "code": {
                    "description": "Respiratory rate code.",
                    "cardinality": "1..1",
                    "min": 1, 
                    "max": "1",
                    "mustSupport": True
                },
                "valueQuantity": {
                    "description": "Respiratory rate value.",
                    "cardinality": "1..1",
                    "min": 1,
                    "max": "1", 
                    "mustSupport": True
                }
            }
        },
        "BodyTemperature": {
            "description": "US Core Body Temperature Profile - represents body temperature measurement.",
            "fields": {
                "code": {
                    "description": "Body temperature code.",
                    "cardinality": "1..1",
                    "min": 1,
                    "max": "1",
                    "mustSupport": True
                },
                "valueQuantity": {
                    "description": "Body temperature value.",
                    "cardinality": "1..1", 
                    "min": 1,
                    "max": "1",
                    "mustSupport": True
                }
            }
        },
        "BodyHeight": {
            "description": "US Core Body Height Profile - represents body height measurement.",
            "fields": {
                "code": {
                    "description": "Body height code.",
                    "cardinality": "1..1",
                    "min": 1,
                    "max": "1",
                    "mustSupport": True
                },
                "valueQuantity": {
                    "description": "Body height value.",
                    "cardinality": "1..1",
                    "min": 1,
                    "max": "1",
                    "mustSupport": True
                }
            }
        },
        "BodyWeight": {
            "description": "US Core Body Weight Profile - represents body weight measurement.",
            "fields": {
                "code": {
                    "description": "Body weight code.",
                    "cardinality": "1..1",
                    "min": 1,
                    "max": "1",
                    "mustSupport": True
                },
                "valueQuantity": {
                    "description": "Body weight value.",
                    "cardinality": "1..1",
                    "min": 1, 
                    "max": "1",
                    "mustSupport": True
                }
            }
        },
        "BMI": {
            "description": "US Core BMI Profile - represents Body Mass Index calculation.",
            "fields": {
                "code": {
                    "description": "BMI code.",
                    "cardinality": "1..1",
                    "min": 1,
                    "max": "1",
                    "mustSupport": True
                },
                "valueQuantity": {
                    "description": "BMI value.",
                    "cardinality": "1..1",
                    "min": 1,
                    "max": "1",
                    "mustSupport": True
                }
            }
        }
    }
    
    # Merge vital signs profiles into main profiles dictionary
    us_core_profiles.update(vital_signs_profiles)
    
    # Cache the profiles
    ensure_cache_dir()
    with open(cache_file, 'w') as f:
        json.dump(us_core_profiles, f, indent=2)
        
    return us_core_profiles

def fetch_carin_bb_profiles():
    """
    Fetch CARIN BB Implementation Guide profiles from GitHub.
    
    Returns:
        dict: A dictionary containing CARIN BB profile definitions.
    """
    # Create cache file path
    cache_file = CACHE_DIR / "carin_bb_profiles.json"
    
    # Check if we have a cached version
    if cache_file.exists():
        try:
            with open(cache_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            st.warning(f"Error reading cached CARIN BB profiles: {str(e)}. Fetching from source.")
    
    carin_bb_profiles = {}
    
    # Base URL for raw GitHub content
    base_url = "https://raw.githubusercontent.com/HL7/carin-bb/master/input/resources/StructureDefinition"
    
    # List of core resources to fetch
    resources = [
        "CARIN-BB-Coverage", 
        "CARIN-BB-ExplanationOfBenefit",
        "CARIN-BB-ExplanationOfBenefit-Inpatient-Institutional",
        "CARIN-BB-ExplanationOfBenefit-Outpatient-Institutional", 
        "CARIN-BB-ExplanationOfBenefit-Pharmacy", 
        "CARIN-BB-ExplanationOfBenefit-Professional",
        "CARIN-BB-Organization", 
        "CARIN-BB-Patient",
        "CARIN-BB-Practitioner"
    ]
    
    try:
        for resource in resources:
            url = f"{base_url}/{resource}.json"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                profile = response.json()
                
                # Extract base resource type from the profile name
                full_type = profile.get("type", "")
                resource_type = full_type.split('-')[-1] if '-' in full_type else full_type
                
                # Create a clean structure with field definitions
                fields = {}
                
                # Process the differential elements to get field definitions
                for element in profile.get("differential", {}).get("element", []):
                    path = element.get("path", "")
                    
                    # Skip the base resource definition and complex nested structures
                    if "." in path and path.count(".") == 1 and resource_type.lower() in path.lower():
                        # Extract the field name after the resource type
                        field = path.split(".")[-1]
                        
                        # Get description or definition
                        description = element.get("definition", element.get("short", "No description"))
                        
                        # Extract cardinality
                        min_occurs = element.get("min", 0)
                        max_occurs = element.get("max", "*")
                        cardinality = f"{min_occurs}..{max_occurs}"
                        
                        # Extract must-support flag
                        must_support = element.get("mustSupport", False)
                        
                        # Store as a dictionary with all metadata
                        fields[field] = {
                            "description": description,
                            "cardinality": cardinality,
                            "min": min_occurs,
                            "max": max_occurs,
                            "mustSupport": must_support
                        }
                
                # Add to our profiles dictionary
                if resource_type not in carin_bb_profiles:
                    carin_bb_profiles[resource_type] = {
                        "fields": fields,
                        "description": profile.get("description", f"CARIN BB {resource_type} profile")
                    }
                else:
                    # Merge fields if resource already exists
                    carin_bb_profiles[resource_type]["fields"].update(fields)
                
            else:
                print(f"Failed to fetch {resource}: {response.status_code}")
                
        # Cache the profiles
        ensure_cache_dir()
        with open(cache_file, 'w') as f:
            json.dump(carin_bb_profiles, f, indent=2)
            
        return carin_bb_profiles
    
    except Exception as e:
        st.error(f"Error fetching CARIN BB profiles: {str(e)}")
        return {}

def enrich_fhir_resources_with_ig_profiles(resources, standard):
    """
    Enrich the existing FHIR resources with detailed Implementation Guide profiles.
    
    Args:
        resources: Dict containing the current FHIR resource definitions
        standard: The FHIR standard (US Core or CARIN BB)
        
    Returns:
        dict: Enriched FHIR resource definitions
    """
    # Make a deep copy to avoid modifying the original
    import copy
    enriched = copy.deepcopy(resources)
    
    try:
        if standard == "US Core":
            ig_profiles = fetch_us_core_profiles()
        elif standard == "CARIN BB":
            ig_profiles = fetch_carin_bb_profiles()
        else:
            return resources  # No enrichment for unknown standards
            
        # Enrich each resource with IG profile data
        for resource_name, resource_data in ig_profiles.items():
            if resource_name in enriched:
                # Merge descriptions
                if "description" in resource_data:
                    enriched[resource_name]["description"] = resource_data["description"]
                
                # Merge fields, prioritizing IG-specific definitions
                if "fields" in resource_data:
                    for field, field_data in resource_data["fields"].items():
                        # If the field exists and it's a string description, convert to dict first
                        if field in enriched[resource_name]["fields"]:
                            if isinstance(enriched[resource_name]["fields"][field], str):
                                current_description = enriched[resource_name]["fields"][field]
                                enriched[resource_name]["fields"][field] = {
                                    "description": current_description
                                }
                            
                            # Extract and add cardinality information if available
                            if isinstance(field_data, dict):
                                # Extract cardinality from the differential element
                                if "min" in field_data and "max" in field_data:
                                    min_occurs = field_data.get("min", 0)
                                    max_occurs = field_data.get("max", "*")
                                    cardinality = f"{min_occurs}..{max_occurs}"
                                    
                                    # Update with cardinality and must-support info
                                    enriched[resource_name]["fields"][field]["cardinality"] = cardinality
                                    enriched[resource_name]["fields"][field]["min"] = min_occurs
                                    enriched[resource_name]["fields"][field]["max"] = max_occurs
                                    
                                    # Add must-support flag if available
                                    must_support = field_data.get("mustSupport", False)
                                    enriched[resource_name]["fields"][field]["mustSupport"] = must_support
                                
                                # Update or add description
                                if "description" in field_data:
                                    enriched[resource_name]["fields"][field]["description"] = field_data["description"]
                                elif isinstance(field_data, str):
                                    # If field_data is just a string, it's a description
                                    enriched[resource_name]["fields"][field]["description"] = field_data
                            else:
                                # If field_data is just a string, it's a description
                                enriched[resource_name]["fields"][field]["description"] = field_data
                        else:
                            # Field doesn't exist yet, add it
                            if isinstance(field_data, dict):
                                enriched[resource_name]["fields"][field] = field_data
                            else:
                                # Just a string description
                                enriched[resource_name]["fields"][field] = {
                                    "description": field_data,
                                    "cardinality": "0..1",  # Default cardinality
                                    "min": 0,
                                    "max": "1",
                                    "mustSupport": False
                                }
            else:
                # If the resource doesn't exist in our base definitions, add it
                enriched[resource_name] = resource_data
                
        # Ensure every field has cardinality info by providing defaults where missing
        for resource_name, resource_data in enriched.items():
            for field, field_data in resource_data.get("fields", {}).items():
                if isinstance(field_data, str):
                    # Convert string descriptions to dict
                    enriched[resource_name]["fields"][field] = {
                        "description": field_data,
                        "cardinality": "0..1",  # Default cardinality
                        "min": 0,
                        "max": "1",
                        "mustSupport": False
                    }
                elif isinstance(field_data, dict) and "cardinality" not in field_data:
                    # Add default cardinality where missing
                    field_data["cardinality"] = "0..1"
                    field_data["min"] = 0
                    field_data["max"] = "1"
                    field_data["mustSupport"] = False
                
        return enriched
        
    except Exception as e:
        st.warning(f"Error enriching FHIR resources with IG profiles: {str(e)}")
        return resources  # Return original if enrichment fails