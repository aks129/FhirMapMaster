import subprocess
import sys
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Parker - FHIR Mapping Tool</title>
            <meta http-equiv="refresh" content="0; URL='https://fhirmapmaster.streamlit.app'" />
        </head>
        <body>
            <h1>Parker - Healthcare Data to FHIR Mapper</h1>
            <p>This is a Streamlit application. Please deploy it using Streamlit Cloud for best results.</p>
            <p>Redirecting to Streamlit deployment...</p>
            <p>If not redirected, please visit: <a href="https://fhirmapmaster.streamlit.app">https://fhirmapmaster.streamlit.app</a></p>
        </body>
        </html>
        """

        self.wfile.write(html.encode())
        return