"""
Health check endpoint for Vercel deployment
"""

from http.server import BaseHTTPRequestHandler
import json

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Health check endpoint"""
        try:
            # Basic health check
            health_status = {
                "status": "healthy",
                "service": "FhirMapMaster API",
                "version": "2.0.0",
                "message": "Parker v2.0 API is running successfully",
                "endpoints": {
                    "health": "/api/health",
                    "validate": "/api/validate",
                    "transform": "/api/transform"
                },
                "links": {
                    "streamlit_app": "https://fhirmapmaster.streamlit.app",
                    "github": "https://github.com/aks129/FhirMapMaster",
                    "documentation": "https://github.com/aks129/FhirMapMaster/blob/main/README_V2.md"
                },
                "features": [
                    "Multi-LLM AI Integration",
                    "Multi-Layer FHIR Validation",
                    "Database Flexibility (DuckDB/Databricks)",
                    "Template Management",
                    "Pipeline Automation"
                ]
            }

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()

            self.wfile.write(json.dumps(health_status, indent=2).encode())

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            error_response = {
                "status": "error",
                "message": str(e),
                "service": "FhirMapMaster API"
            }

            self.wfile.write(json.dumps(error_response).encode())

    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()