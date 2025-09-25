"""
Health check endpoint for Vercel deployment
"""

from http.server import BaseHTTPRequestHandler
import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Health check endpoint"""
        try:
            # Basic health check
            health_status = {
                "status": "healthy",
                "service": "FhirMapMaster API",
                "version": "2.0.0",
                "endpoints": {
                    "health": "/api/health",
                    "validate": "/api/validate",
                    "suggest": "/api/suggest",
                    "transform": "/api/transform"
                },
                "streamlit_app": "https://fhirmapmaster.streamlit.app",
                "github": "https://github.com/aks129/FhirMapMaster"
            }

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            self.wfile.write(json.dumps(health_status, indent=2).encode())

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()

            error_response = {
                "status": "error",
                "message": str(e)
            }

            self.wfile.write(json.dumps(error_response).encode())

    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()