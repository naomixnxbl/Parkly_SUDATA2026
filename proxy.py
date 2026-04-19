#!/usr/bin/env python3
"""
Parkly proxy — relays TfNSW API calls from the browser.

Why this exists:
    The TfNSW Open Data API doesn't send CORS headers that browsers need for
    direct JavaScript calls. This tiny server sits on localhost, adds your
    API key server-side, and adds the CORS headers so the HTML can talk to it.

Run:
    python proxy.py
    (starts on http://localhost:8787)

Then open parkly.html in your browser — it will automatically detect the proxy.
"""

import http.server
import socketserver
import urllib.request
import urllib.parse
import urllib.error
import json
import os
import sys

# ─────────────────────────────────────────────────────────────────
# CONFIG — paste your TfNSW API key here OR set TFNSW_API_KEY env var
# ─────────────────────────────────────────────────────────────────

API_KEY = os.environ.get('TFNSW_API_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiJWM053Y014Y3FzbWtKNTcyZ09SZi1rS3YtVXNNZnlhQXhGdkRyUEdIQTFRIiwiaWF0IjoxNzc2NTU1NzA0fQ.A_SIU3NKLXpHbrtfilRpa952yHQqg-rmDN8_SyvJH-8')
PORT = 8787
TFNSW_BASE = 'https://api.transport.nsw.gov.au/v1'


class ProxyHandler(http.server.BaseHTTPRequestHandler):

    def _send_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')

    def do_OPTIONS(self):
        self.send_response(204)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        if API_KEY == 'YOUR_KEY_HERE':
            self.send_response(500)
            self._send_cors_headers()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"error": "API key not set. Edit proxy.py and paste your TfNSW key, or set TFNSW_API_KEY env var."}')
            return

        # Map /endpoint?query to https://api.transport.nsw.gov.au/v1/endpoint?query
        target_url = TFNSW_BASE + self.path

        try:
            req = urllib.request.Request(target_url)
            req.add_header('Authorization', f'apikey {API_KEY}')
            req.add_header('Accept', 'application/json')

            with urllib.request.urlopen(req, timeout=10) as resp:
                data = resp.read()
                status = resp.status

            self.send_response(status)
            self._send_cors_headers()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(data)

            print(f'[OK] {self.path} → {status} ({len(data)} bytes)')

        except urllib.error.HTTPError as e:
            body = e.read() if hasattr(e, 'read') else b''
            self.send_response(e.code)
            self._send_cors_headers()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(body or f'{{"error": "HTTP {e.code}"}}'.encode())
            print(f'[ERR] {self.path} → HTTP {e.code}')

        except Exception as e:
            self.send_response(500)
            self._send_cors_headers()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            err = json.dumps({'error': str(e)}).encode()
            self.wfile.write(err)
            print(f'[ERR] {self.path} → {e}')

    def log_message(self, fmt, *args):
        # Suppress default noisy logging (we do our own above)
        pass


def main():
    if API_KEY == 'YOUR_KEY_HERE':
        print('=' * 60)
        print(' ⚠  TfNSW API key not set!')
        print('=' * 60)
        print()
        print(' Option 1 — set environment variable:')
        print('   export TFNSW_API_KEY="your_key_here"')
        print('   python proxy.py')
        print()
        print(' Option 2 — edit proxy.py line 25 and paste your key there')
        print()
        print(' Get a free key at: opendata.transport.nsw.gov.au')
        print('=' * 60)
        print()
        print(' Starting server anyway (requests will return an error)...')
        print()

    print(f'▶ Parkly proxy running on http://localhost:{PORT}')
    print(f'  Relaying to: {TFNSW_BASE}')
    print(f'  Using key: {API_KEY[:12]}...' if len(API_KEY) > 12 else '  Using key: [not set]')
    print(f'  Ctrl-C to stop')
    print()

    with socketserver.TCPServer(('', PORT), ProxyHandler) as httpd:
        httpd.allow_reuse_address = True
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print('\n  Stopped.')


if __name__ == '__main__':
    main()
