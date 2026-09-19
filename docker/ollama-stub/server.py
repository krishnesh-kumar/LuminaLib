"""Minimal Ollama-API-compatible stub for CI E2E runs.

Real Ollama + mistral needs a multi-GB model pull and real inference time,
which is too slow/expensive to run on every CI push. This stub implements
just enough of the Ollama HTTP API (POST /api/generate) for the app's
OllamaProvider to work against, returning a canned response instantly.
"""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        if self.path in ("/", "/api/tags"):
            self._json(200, {"status": "ok", "models": [{"name": "mistral"}]})
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw or b"{}")
        except json.JSONDecodeError:
            body = {}

        if self.path == "/api/generate":
            prompt = body.get("prompt", "")
            self._json(200, {
                "model": body.get("model", "mistral"),
                "response": f"[CI stub summary] {len(prompt)} chars analyzed. This is a placeholder LLM response for automated testing.",
                "done": True,
            })
        else:
            self._json(404, {"error": "not found"})

    def _json(self, status, payload):
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("0.0.0.0", 11434), Handler)
    server.serve_forever()
