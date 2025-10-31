import os, sys, subprocess
from urllib.parse import urlparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ALLOWED = {"players", "coaches", "physios", "youth", "members", "finance"}

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path.strip("/")

        # página inicial / healthcheck
        if path in ("", "healthz"):
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            if path == "":
                msg = (
                    "Vila Caiz online ✅\n"
                    "Usa /players /coaches /physios /youth /members /finance\n"
                )
            else:
                msg = "ok"
            self.wfile.write(msg.encode("utf-8"))
            return

        # endpoints que chamam o teu CLI
        if path in ALLOWED:
            try:
                cp = subprocess.run(
                    [sys.executable, "app.py", path],
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=60
                )
                code = 200 if cp.returncode == 0 else 500
                body = (cp.stdout or "") + (cp.stderr or "")
            except Exception as e:
                code = 500
                body = f"erro ao executar {path}: {e}"

            self.send_response(code)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(body.encode("utf-8") or b"(sem output)")
            return

        # se não existir rota
        self.send_response(404)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"404 not found")

    def log_message(self, *_):
        # menos lixo nos logs
        return

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    srv = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"HTTP a correr na porta {port}")
    srv.serve_forever()
