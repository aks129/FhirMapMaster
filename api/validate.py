"""
FHIR validation API endpoint for Vercel
"""

from http.server import BaseHTTPRequestHandler
import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

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

            response = {
                "status": "success",
                "validation_results": validation_results,
                "resource_type": resource.get('resourceType', 'Unknown'),
                "profile": profile
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

    def validate_resource_structure(self, resource):
        """Basic structural validation"""
        results = []

        # Check for resourceType
        if 'resourceType' not in resource:
            results.append({
                "severity": "error",
                "message": "Missing required field: resourceType",
                "location": "root"
            })

        # Check for id
        if 'id' in resource and not resource['id']:
            results.append({
                "severity": "error",
                "message": "Resource ID must not be empty",
                "location": "id"
            })

        # Patient-specific validation
        if resource.get('resourceType') == 'Patient':
            if 'name' not in resource:
                results.append({
                    "severity": "warning",
                    "message": "Patient should have a name",
                    "location": "name"
                })

        if not results:
            results.append({
                "severity": "information",
                "message": "Basic structural validation passed",
                "location": "root"
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
            "message": error_message
        }

        self.wfile.write(json.dumps(error_response).encode())