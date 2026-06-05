#!/usr/bin/env python3
"""
Web Dashboard Server
Serves the unified dashboard on a web port
"""

import asyncio
import json
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dashboard_server")


class DashboardHandler(BaseHTTPRequestHandler):
    """HTTP handler for dashboard"""
    
    def do_GET(self):
        """Handle GET requests"""
        if self.path == '/' or self.path == '/index.html':
            self._serve_html()
        elif self.path == '/api/dashboard':
            self._serve_api()
        else:
            self._send_error(404, "Not Found")
    
    def _serve_html(self):
        """Serve the HTML dashboard"""
        html_path = Path('/root/.openclaw/workspace/dashboard_data/index.html')
        if html_path.exists():
            with open(html_path, 'r') as f:
                content = f.read()
            self._send_response(200, 'text/html', content)
        else:
            self._send_error(404, "Dashboard not found")
    
    def _serve_api(self):
        """Serve JSON API data"""
        data = self._collect_data()
        self._send_response(200, 'application/json', json.dumps(data))
    
    def _collect_data(self) -> dict:
        """Collect all dashboard data"""
        import sys
        sys.path.insert(0, '/root/.openclaw/workspace')
        from unified_dashboard import UnifiedDashboard
        
        dashboard = UnifiedDashboard()
        
        # Run async collection
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(dashboard.generate_full_dashboard())
        except:
            pass
        
        # Build response from sections
        result = {
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "crypto": None,
            "cashout": None,
            "swarm": None,
            "agents": None,
            "system": None,
            "telegram": None
        }
        
        for key, section in dashboard.sections.items():
            result[key] = {
                "name": section.name,
                "icon": section.icon,
                "status": section.status,
                "data": section.data,
                "last_updated": section.last_updated
            }
        
        return result
    
    def _send_response(self, status, content_type, content):
        """Send HTTP response"""
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(content.encode() if isinstance(content, str) else content)
    
    def _send_error(self, status, message):
        """Send error response"""
        self._send_response(status, 'text/plain', message)
    
    def log_message(self, format, *args):
        """Suppress default logging"""
        logger.info(f"{self.address_string()} - {format % args}")


def start_server(port=8080):
    """Start the dashboard server"""
    server = HTTPServer(('0.0.0.0', port), DashboardHandler)
    logger.info(f"🚀 Dashboard server started on http://0.0.0.0:{port}")
    logger.info(f"📊 Access: http://43.98.199.136:{port}")
    
    # Save port info
    port_file = Path('/root/.openclaw/workspace/dashboard_data/port.txt')
    with open(port_file, 'w') as f:
        f.write(str(port))
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server stopped")
        server.shutdown()


if __name__ == '__main__':
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    start_server(port)
