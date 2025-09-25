"""
FHIR validation API endpoint for Vercel
"""

from http.server import BaseHTTPRequestHandler
import json

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        """Validate FHIR resource endpoint"""
        try:
            # Get request body
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)

            # Extract resource and profile
            resource = data.get('resource', {})
            profile = data.get('profile', '')

            # Basic structural validation (simplified for Vercel)
            validation_results = self.validate_resource_structure(resource)

            # Calculate summary
            errors = [r for r in validation_results if r['severity'] == 'error']
            warnings = [r for r in validation_results if r['severity'] == 'warning']

            overall_status = 'valid'
            if errors:
                overall_status = 'invalid'
            elif warnings:
                overall_status = 'valid_with_warnings'

            response = {
                "status": "success",
                "service": "Parker v2.0 FHIR Validation API",
                "validation_summary": {
                    "overall_status": overall_status,
                    "error_count": len(errors),
                    "warning_count": len(warnings),
                    "total_issues": len(validation_results)
                },
                "validation_results": validation_results,
                "resource_info": {
                    "resource_type": resource.get('resourceType', 'Unknown'),
                    "resource_id": resource.get('id', 'No ID provided'),
                    "profile": profile
                },
                "note": "This is a basic structural validation. Full validation requires the Streamlit application."
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
        """Get validation endpoint information"""
        info = {
            "service": "Parker v2.0 FHIR Validation API",
            "description": "Basic FHIR resource structural validation",
            "usage": {
                "method": "POST",
                "content_type": "application/json",
                "body_format": {
                    "resource": "FHIR resource object to validate",
                    "profile": "Optional FHIR profile URL"
                }
            },
            "example_request": {
                "resource": {
                    "resourceType": "Patient",
                    "id": "example-123",
                    "name": [{"given": ["John"], "family": "Doe"}]
                },
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

    def validate_resource_structure(self, resource):
        """Basic structural validation"""
        results = []

        # Check for resourceType
        if 'resourceType' not in resource:
            results.append({
                "severity": "error",
                "message": "Missing required field: resourceType",
                "location": "root",
                "rule_id": "MISSING_RESOURCE_TYPE",
                "suggested_fix": "Add resourceType field to the resource"
            })
            return results  # Can't continue without resourceType

        resource_type = resource['resourceType']

        # Check for id
        if 'id' in resource and not resource['id']:
            results.append({
                "severity": "error",
                "message": "Resource ID must not be empty if provided",
                "location": "id",
                "rule_id": "INVALID_ID",
                "suggested_fix": "Provide a valid non-empty ID or remove the id field"
            })

        # Resource-specific validation
        if resource_type == 'Patient':
            if 'name' not in resource or not resource['name']:
                results.append({
                    "severity": "warning",
                    "message": "Patient should have at least one name",
                    "location": "name",
                    "rule_id": "MISSING_PATIENT_NAME",
                    "suggested_fix": "Add a name array with at least one HumanName object"
                })

            if 'gender' in resource:
                valid_genders = ['male', 'female', 'other', 'unknown']
                if resource['gender'] not in valid_genders:
                    results.append({
                        "severity": "error",
                        "message": f"Invalid gender value. Must be one of: {', '.join(valid_genders)}",
                        "location": "gender",
                        "rule_id": "INVALID_GENDER",
                        "suggested_fix": f"Use one of the valid gender codes: {', '.join(valid_genders)}"
                    })

        elif resource_type == 'Observation':
            required_fields = ['status', 'code']
            for field in required_fields:
                if field not in resource:
                    results.append({
                        "severity": "error",
                        "message": f"Missing required field: {field}",
                        "location": field,
                        "rule_id": f"MISSING_{field.upper()}",
                        "suggested_fix": f"Add required {field} field"
                    })

        # If no issues found, add success message
        if not results:
            results.append({
                "severity": "information",
                "message": "Basic structural validation passed successfully",
                "location": "root",
                "rule_id": "VALIDATION_SUCCESS",
                "suggested_fix": "No fixes needed for basic structure"
            })

        return results

    def send_error_response(self, error_message):
        """Send error response"""
        self.send_response(400)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

        error_response = {
            "status": "error",
            "service": "Parker v2.0 FHIR Validation API",
            "message": error_message,
            "help": "Ensure you're sending valid JSON with 'resource' and optional 'profile' fields"
        }

        self.wfile.write(json.dumps(error_response, indent=2).encode())