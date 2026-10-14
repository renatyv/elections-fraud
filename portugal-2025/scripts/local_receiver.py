#!/usr/bin/env python3
"""Local receiver for files uploaded by the browser-based downloader (CORS: *).

POST /put  body: {"files": [{"name": "territory-results/KEY-AR.json",
                             "b64": "..."}]}
All files are written into the given directory. Run: python3 receiver.py DIR PORT
"""
import base64
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

OUT = sys.argv[1]
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 8765
os.makedirs(OUT, exist_ok=True)


class H(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_POST(self):
        if self.path != "/put":
            self.send_response(404)
            self._cors()
            self.end_headers()
            return
        n = int(self.headers.get("Content-Length", 0))
        data = json.loads(self.rfile.read(n))
        written = skipped = 0
        for f in data.get("files", []):
            name = os.path.normpath(f["name"]).lstrip("/")
            if ".." in name.split(os.sep):
                continue
            p = os.path.join(OUT, name)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            if os.path.exists(p):
                skipped += 1
                continue
            with open(p, "wb") as fh:
                fh.write(base64.b64decode(f["b64"]))
            written += 1
        body = json.dumps({"written": written, "skipped": skipped}).encode()
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/ping":
            body = b"pong"
            self.send_response(200)
            self._cors()
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self._cors()
            self.end_headers()

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", PORT), H).serve_forever()
