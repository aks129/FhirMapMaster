"""
Data transformation API endpoint for Vercel
"""

from http.server import BaseHTTPRequestHandler
import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        """Transform data to FHIR format"""
        try:
            # Get request body
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)

            # Extract input data
            source_data = data.get('data', {})
            resource_type = data.get('resource_type', 'Patient')

            # Perform basic transformation (simplified for Vercel)
            fhir_resource = self.transform_to_fhir(source_data, resource_type)

            response = {
                "status": "success",
                "fhir_resource": fhir_resource,
                "resource_type": resource_type,
                "message": "Transformation completed successfully"
            }

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            self.wfile.write(json.dumps(response, indent=2).encode())

        except Exception as e:
            self.send_error_response(str(e))

    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def transform_to_fhir(self, source_data, resource_type):
        """Basic transformation to FHIR format"""

        if resource_type == "Patient":
            return {
                "resourceType": "Patient",
                "id": source_data.get("patient_id", "unknown"),
                "name": [{
                    "use": "official",
                    "given": [source_data.get("first_name", "")],
                    "family": source_data.get("last_name", "")
                }],
                "birthDate": source_data.get("birth_date", ""),
                "gender": self.map_gender(source_data.get("gender", ""))
            }

        elif resource_type == "Observation":
            return {
                "resourceType": "Observation",
                "id": source_data.get("observation_id", "unknown"),
                "status": "final",
                "code": {
                    "text": source_data.get("test_name", "Unknown Test")
                },
                "valueQuantity": {
                    "value": source_data.get("test_value", 0),
                    "unit": source_data.get("unit", "")
                }
            }

        else:
            return {
                "resourceType": resource_type,
                "id": "generated",
                "meta": {
                    "note": "Basic transformation applied"
                }
            }

    def map_gender(self, gender):
        """Map gender values to FHIR standard"""
        gender_lower = str(gender).lower()
        if gender_lower in ['m', 'male']:
            return 'male'
        elif gender_lower in ['f', 'female']:
            return 'female'
        elif gender_lower in ['o', 'other']:
            return 'other'
        else:
            return 'unknown'

    def send_error_response(self, error_message):
        """Send error response"""
        self.send_response(400)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

        error_response = {
            "status": "error",
            "message": error_message
        }

        self.wfile.write(json.dumps(error_response).encode())