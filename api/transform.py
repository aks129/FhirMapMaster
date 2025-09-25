"""
FHIR transformation API endpoint for Vercel
"""

from http.server import BaseHTTPRequestHandler
import json
from datetime import datetime

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        """Transform data to FHIR resource endpoint"""
        try:
            # Get request body
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)

            # Extract input data and transformation parameters
            source_data = data.get('data', {})
            resource_type = data.get('resource_type', 'Patient')
            profile = data.get('profile', '')
            mapping_hints = data.get('mapping_hints', {})

            # Validate input
            validation_issues = self.validate_input(source_data, resource_type)

            # Perform transformation
            transformation_result = self.transform_to_fhir(source_data, resource_type, profile, mapping_hints)

            # Calculate transformation metrics
            field_count = len(source_data) if isinstance(source_data, dict) else 0
            mapped_fields = len([k for k, v in source_data.items() if v]) if isinstance(source_data, dict) else 0
            mapping_completeness = (mapped_fields / field_count * 100) if field_count > 0 else 0

            response = {
                "status": "success",
                "service": "Parker v2.0 FHIR Transform API",
                "transformation_summary": {
                    "input_fields": field_count,
                    "mapped_fields": mapped_fields,
                    "mapping_completeness": f"{mapping_completeness:.1f}%",
                    "resource_type": resource_type,
                    "profile": profile or "Basic FHIR R4B"
                },
                "fhir_resource": transformation_result["resource"],
                "mapping_details": transformation_result["mapping_details"],
                "validation_issues": validation_issues,
                "transformation_metadata": {
                    "transformation_engine": "Parker v2.0 Basic Transformer",
                    "timestamp": datetime.now().isoformat(),
                    "confidence_score": transformation_result["confidence_score"]
                },
                "note": "This is a basic transformation. Full AI-powered mapping available in the Streamlit application."
            }

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()

            self.wfile.write(json.dumps(response, indent=2).encode())

        except Exception as e:
            self.send_error_response(str(e))

    def do_GET(self):
        """Get transformation endpoint information"""
        info = {
            "service": "Parker v2.0 FHIR Transform API",
            "description": "Transform raw data into FHIR R4B resources",
            "features": [
                "Basic field mapping and transformation",
                "Multiple resource type support",
                "Profile-aware transformation hints",
                "Mapping completeness metrics",
                "Confidence scoring"
            ],
            "usage": {
                "method": "POST",
                "content_type": "application/json",
                "body_format": {
                    "data": "Source data object to transform",
                    "resource_type": "Target FHIR resource type (Patient, Observation, etc.)",
                    "profile": "Optional FHIR profile URL",
                    "mapping_hints": "Optional mapping guidance object"
                }
            },
            "supported_resources": ["Patient", "Observation", "Practitioner", "Organization"],
            "example_request": {
                "data": {
                    "patient_id": "PAT001",
                    "first_name": "John",
                    "last_name": "Smith",
                    "birth_date": "1985-06-15",
                    "gender": "M",
                    "phone": "555-0123"
                },
                "resource_type": "Patient",
                "profile": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-patient"
            }
        }

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(info, indent=2).encode())

    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def validate_input(self, source_data, resource_type):
        """Validate input data for transformation"""
        issues = []

        if not source_data:
            issues.append({
                "severity": "error",
                "message": "No source data provided",
                "suggested_fix": "Provide a data object with fields to transform"
            })
            return issues

        if not isinstance(source_data, dict):
            issues.append({
                "severity": "error",
                "message": "Source data must be a JSON object",
                "suggested_fix": "Ensure data is provided as key-value pairs"
            })
            return issues

        if resource_type not in ["Patient", "Observation", "Practitioner", "Organization"]:
            issues.append({
                "severity": "warning",
                "message": f"Resource type '{resource_type}' has limited transformation support",
                "suggested_fix": "Use Patient, Observation, Practitioner, or Organization for best results"
            })

        return issues

    def transform_to_fhir(self, source_data, resource_type, profile="", mapping_hints={}):
        """Enhanced transformation to FHIR format with detailed mapping tracking"""

        mapping_details = {
            "applied_mappings": [],
            "skipped_fields": [],
            "transformation_notes": []
        }

        confidence_score = 85  # Base confidence for basic transformations

        if resource_type == "Patient":
            resource, patient_mappings = self.transform_patient(source_data, profile)
            mapping_details["applied_mappings"].extend(patient_mappings)

        elif resource_type == "Observation":
            resource, obs_mappings = self.transform_observation(source_data, profile)
            mapping_details["applied_mappings"].extend(obs_mappings)

        elif resource_type == "Practitioner":
            resource, prac_mappings = self.transform_practitioner(source_data, profile)
            mapping_details["applied_mappings"].extend(prac_mappings)

        elif resource_type == "Organization":
            resource, org_mappings = self.transform_organization(source_data, profile)
            mapping_details["applied_mappings"].extend(org_mappings)

        else:
            resource = {
                "resourceType": resource_type,
                "id": source_data.get("id", "generated-id"),
                "meta": {
                    "profile": [profile] if profile else None
                }
            }
            confidence_score = 50  # Lower confidence for unsupported types
            mapping_details["transformation_notes"].append(f"Limited support for {resource_type}")

        # Track unmapped fields
        mapped_keys = set(field["source_field"] for field in mapping_details["applied_mappings"])
        for key in source_data.keys():
            if key not in mapped_keys:
                mapping_details["skipped_fields"].append({
                    "field": key,
                    "value": source_data[key],
                    "reason": "No mapping rule defined"
                })

        return {
            "resource": resource,
            "mapping_details": mapping_details,
            "confidence_score": confidence_score
        }

    def transform_patient(self, source_data, profile):
        """Transform Patient resource with detailed mapping tracking"""
        mappings = []

        resource = {
            "resourceType": "Patient",
            "id": source_data.get("patient_id") or source_data.get("id", "unknown")
        }

        if source_data.get("patient_id") or source_data.get("id"):
            mappings.append({
                "source_field": "patient_id" if "patient_id" in source_data else "id",
                "target_field": "Patient.id",
                "transformation": "direct_copy",
                "value": resource["id"]
            })

        # Name transformation
        name_parts = []
        if source_data.get("first_name") or source_data.get("last_name"):
            name_obj = {"use": "official"}

            if source_data.get("first_name"):
                name_obj["given"] = [source_data["first_name"]]
                mappings.append({
                    "source_field": "first_name",
                    "target_field": "Patient.name[0].given[0]",
                    "transformation": "array_wrap",
                    "value": source_data["first_name"]
                })

            if source_data.get("last_name"):
                name_obj["family"] = source_data["last_name"]
                mappings.append({
                    "source_field": "last_name",
                    "target_field": "Patient.name[0].family",
                    "transformation": "direct_copy",
                    "value": source_data["last_name"]
                })

            resource["name"] = [name_obj]

        # Birth date
        if source_data.get("birth_date") or source_data.get("birthDate") or source_data.get("dob"):
            birth_field = next((field for field in ["birth_date", "birthDate", "dob"] if source_data.get(field)), None)
            resource["birthDate"] = source_data[birth_field]
            mappings.append({
                "source_field": birth_field,
                "target_field": "Patient.birthDate",
                "transformation": "date_format",
                "value": source_data[birth_field]
            })

        # Gender mapping
        if source_data.get("gender") or source_data.get("sex"):
            gender_field = "gender" if source_data.get("gender") else "sex"
            mapped_gender = self.map_gender(source_data[gender_field])
            resource["gender"] = mapped_gender
            mappings.append({
                "source_field": gender_field,
                "target_field": "Patient.gender",
                "transformation": "code_mapping",
                "value": mapped_gender,
                "original_value": source_data[gender_field]
            })

        # Contact information
        telecom = []
        if source_data.get("phone"):
            telecom.append({
                "system": "phone",
                "value": source_data["phone"],
                "use": "home"
            })
            mappings.append({
                "source_field": "phone",
                "target_field": "Patient.telecom[0]",
                "transformation": "telecom_structure",
                "value": source_data["phone"]
            })

        if source_data.get("email"):
            telecom.append({
                "system": "email",
                "value": source_data["email"],
                "use": "home"
            })
            mappings.append({
                "source_field": "email",
                "target_field": "Patient.telecom[1]",
                "transformation": "telecom_structure",
                "value": source_data["email"]
            })

        if telecom:
            resource["telecom"] = telecom

        # Add profile if provided
        if profile:
            resource["meta"] = {"profile": [profile]}

        return resource, mappings

    def transform_observation(self, source_data, profile):
        """Transform Observation resource"""
        mappings = []

        resource = {
            "resourceType": "Observation",
            "id": source_data.get("observation_id") or source_data.get("id", "unknown"),
            "status": source_data.get("status", "final")
        }

        # Code/Test name
        if source_data.get("test_name") or source_data.get("code"):
            code_field = "test_name" if source_data.get("test_name") else "code"
            resource["code"] = {"text": source_data[code_field]}
            mappings.append({
                "source_field": code_field,
                "target_field": "Observation.code.text",
                "transformation": "code_text",
                "value": source_data[code_field]
            })

        # Value
        if source_data.get("value") or source_data.get("test_value"):
            value_field = "value" if source_data.get("value") else "test_value"
            value_obj = {"value": float(source_data[value_field])}

            if source_data.get("unit"):
                value_obj["unit"] = source_data["unit"]
                mappings.append({
                    "source_field": "unit",
                    "target_field": "Observation.valueQuantity.unit",
                    "transformation": "direct_copy",
                    "value": source_data["unit"]
                })

            resource["valueQuantity"] = value_obj
            mappings.append({
                "source_field": value_field,
                "target_field": "Observation.valueQuantity.value",
                "transformation": "numeric_conversion",
                "value": value_obj["value"]
            })

        if profile:
            resource["meta"] = {"profile": [profile]}

        return resource, mappings

    def transform_practitioner(self, source_data, profile):
        """Transform Practitioner resource"""
        mappings = []

        resource = {
            "resourceType": "Practitioner",
            "id": source_data.get("practitioner_id") or source_data.get("id", "unknown")
        }

        # Similar name logic as Patient
        if source_data.get("first_name") or source_data.get("last_name"):
            name_obj = {"use": "official"}
            if source_data.get("first_name"):
                name_obj["given"] = [source_data["first_name"]]
            if source_data.get("last_name"):
                name_obj["family"] = source_data["last_name"]
            resource["name"] = [name_obj]
            mappings.append({
                "source_field": "name_fields",
                "target_field": "Practitioner.name[0]",
                "transformation": "name_structure",
                "value": name_obj
            })

        if profile:
            resource["meta"] = {"profile": [profile]}

        return resource, mappings

    def transform_organization(self, source_data, profile):
        """Transform Organization resource"""
        mappings = []

        resource = {
            "resourceType": "Organization",
            "id": source_data.get("organization_id") or source_data.get("id", "unknown")
        }

        if source_data.get("name") or source_data.get("organization_name"):
            name_field = "name" if source_data.get("name") else "organization_name"
            resource["name"] = source_data[name_field]
            mappings.append({
                "source_field": name_field,
                "target_field": "Organization.name",
                "transformation": "direct_copy",
                "value": source_data[name_field]
            })

        if profile:
            resource["meta"] = {"profile": [profile]}

        return resource, mappings

    def map_gender(self, gender):
        """Map gender values to FHIR standard"""
        if not gender:
            return 'unknown'

        gender_lower = str(gender).lower()
        if gender_lower in ['m', 'male', '1']:
            return 'male'
        elif gender_lower in ['f', 'female', '2']:
            return 'female'
        elif gender_lower in ['o', 'other', '3']:
            return 'other'
        else:
            return 'unknown'

    def send_error_response(self, error_message):
        """Send comprehensive error response"""
        self.send_response(400)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

        error_response = {
            "status": "error",
            "service": "Parker v2.0 FHIR Transform API",
            "message": error_message,
            "timestamp": datetime.now().isoformat(),
            "help": {
                "required_fields": ["data"],
                "optional_fields": ["resource_type", "profile", "mapping_hints"],
                "example_payload": {
                    "data": {"patient_id": "123", "first_name": "John"},
                    "resource_type": "Patient"
                }
            },
            "documentation": "https://github.com/aks129/FhirMapMaster/blob/main/README_V2.md"
        }

        self.wfile.write(json.dumps(error_response, indent=2).encode())