import os
import sys
import json
import socket
import hmac
import secrets
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from typing import Tuple, List, Optional

# Ensure UTF-8 output on Windows terminal
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# =====================================================================
# SECURE CONFIGURATION & CONSTANTS
# =====================================================================
DEFAULT_UPSTREAM_URL = os.environ.get("OLLAMA_UPSTREAM_URL", "http://127.0.0.1:11434")
PROXY_PORT = int(os.environ.get("PROXY_PORT", 11435))
PROXY_HOST = "0.0.0.0"

# Generate or load a strong, persistent master token
SECURE_TOKEN_FILE = os.path.expanduser("~/.ollama_proxy_token")
if not os.path.exists(SECURE_TOKEN_FILE):
    try:
        master_token = secrets.token_hex(32)
        with open(SECURE_TOKEN_FILE, "w", encoding="utf-8") as f:
            f.write(master_token)
        try:
            os.chmod(SECURE_TOKEN_FILE, 0o600)
        except Exception:
            pass
    except Exception:
        master_token = secrets.token_hex(32)
else:
    try:
        with open(SECURE_TOKEN_FILE, "r", encoding="utf-8") as f:
            master_token = f.read().strip()
    except Exception:
        master_token = secrets.token_hex(32)

# SECURITY ALLOWLISTS (DNS Rebinding & CORS Hijacking Countermeasures)
ALLOWED_HOSTS = {
    "localhost:11435", "127.0.0.1:11435", "localhost", "127.0.0.1",
    f"localhost:{PROXY_PORT}", f"127.0.0.1:{PROXY_PORT}", f"0.0.0.0:{PROXY_PORT}"
}
try:
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    ALLOWED_HOSTS.add(f"{local_ip}:{PROXY_PORT}")
    ALLOWED_HOSTS.add(local_ip)
except Exception:
    pass

# =====================================================================
# SECURE REVERSE PROXY MIDDLEWARE
# =====================================================================
class SecureOllamaProxyHandler(BaseHTTPRequestHandler):
    """
    HTTP proxy handler implementing host header validation, origin sanitization,
    token-gated authentication, and payload inspection to block template poisoning.
    """
    protocol_version = 'HTTP/1.1'

    def log_message(self, format_str, *args):
        sys.stdout.write(f"[Proxy HTTP] {format_str % args}\n")
        sys.stdout.flush()

    def _send_error_response(self, status_code: int, message: str):
        response_body = json.dumps({"error": message, "status": status_code}).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response_body)))
        self.send_header("Access-Control-Allow-Origin", "null")
        self.end_headers()
        self.wfile.write(response_body)

    def _validate_security_envelope(self) -> bool:
        # 1. Neutralize DNS Rebinding (CVE-2024-28224)
        host_header = self.headers.get("Host", "").lower().strip()
        if not host_header:
            self._send_error_response(400, "Bad Request: Missing Host Header")
            return False
            
        if host_header not in ALLOWED_HOSTS:
            print(f"[🛡️ Security Alert] Blocked suspected DNS Rebinding attack! Unrecognized Host: '{host_header}'")
            self._send_error_response(403, "Access Denied: Invalid Host Header (Suspected DNS Rebinding)")
            return False

        # 2. Neutralize Cross-Origin Browser Hijacking (CORS Leaks)
        origin_header = self.headers.get("Origin")
        if origin_header:
            origin_lower = origin_header.lower()
            if not (origin_lower.startswith("http://localhost:") or origin_lower.startswith("http://127.0.0.1:")):
                print(f"[🛡️ Security Alert] Blocked suspected Cross-Origin browser hijack from: '{origin_header}'")
                self._send_error_response(403, "Access Denied: Cross-Origin requests are strictly restricted")
                return False

        # 3. Authenticate Request via Shared Secrets
        auth_header = self.headers.get("Authorization", "")
        token_header = self.headers.get("X-Ollama-Bypass-Token", "")
        
        provided_token = ""
        if auth_header.lower().startswith("bearer "):
            provided_token = auth_header[7:].strip()
        elif token_header:
            provided_token = token_header.strip()

        if not provided_token or not hmac.compare_digest(provided_token, master_token):
            print(f"[🛡️ Security Alert] Blocked unauthenticated connection attempt from {self.client_address[0]}")
            self._send_error_response(401, "Unauthorized: Invalid or missing secure bypass token.")
            return False

        return True

    def _inspect_and_sanitize_payload(self, body_bytes: bytes) -> bool:
        if self.path in ("/api/create", "/api/create/"):
            try:
                payload = json.loads(body_bytes.decode("utf-8"))
                if "template" in payload:
                    template_str = str(payload["template"]).lower()
                    poison_signatures = ["attacker", "evil.site", "exfil", "system: override", "ignore previous"]
                    for sig in poison_signatures:
                        if sig in template_str:
                            print(f"[🛡️ Security Alert] Intercepted poisoned chat template creation payload containing signature: '{sig}'!")
                            return False
                            
                if "system" in payload:
                    system_str = str(payload["system"]).lower()
                    if "ignore previous instructions" in system_str or "developer-mode" in system_str:
                        print("[🛡️ Security Alert] Blocked jailbreak payload attempt in Model Definition system instructions.")
                        return False
            except json.JSONDecodeError:
                pass
        return True

    def handle_request(self):
        if not self._validate_security_envelope():
            return

        content_length = int(self.headers.get('Content-Length', 0))
        body_bytes = self.rfile.read(content_length) if content_length > 0 else b""

        if body_bytes and not self._inspect_and_sanitize_payload(body_bytes):
            self._send_error_response(422, "Security Violation: Poisoned chat templates or jailbreak sequences detected.")
            return

        target_url = f"{DEFAULT_UPSTREAM_URL}{self.path}"
        
        clean_headers = {}
        for key, value in self.headers.items():
            if key.lower() not in ("authorization", "x-ollama-bypass-token", "host"):
                clean_headers[key] = value

        req = Request(
            target_url,
            data=body_bytes if body_bytes else None,
            headers=clean_headers,
            method=self.command
        )

        try:
            with urlopen(req, timeout=30.0) as upstream_response:
                self.send_response(upstream_response.status)
                for key, value in upstream_response.headers.items():
                    if key.lower() not in ("access-control-allow-origin", "transfer-encoding"):
                        self.send_header(key, value)
                
                self.send_header("Access-Control-Allow-Origin", "http://localhost:5173")
                self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Ollama-Bypass-Token")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, DELETE")
                self.end_headers()

                while True:
                    chunk = upstream_response.read(4096)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    self.wfile.flush()

        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
            pass
        except HTTPError as e:
            try:
                self.send_response(e.code)
                for key, value in e.headers.items():
                    self.send_header(key, value)
                self.end_headers()
                self.wfile.write(e.read())
            except Exception:
                pass
        except URLError as e:
            print(f"[❌ Connection Error] Failed to contact upstream Ollama on {DEFAULT_UPSTREAM_URL}: {e}")
            self._send_error_response(502, f"Bad Gateway: Upstream Ollama is offline or refusing connections on {DEFAULT_UPSTREAM_URL}.")
        except Exception as e:
            print(f"[❌ Server Error] Proxy exception encountered: {e}")
            try:
                self._send_error_response(500, f"Internal Server Error: {str(e)}")
            except Exception:
                pass

    def do_GET(self):
        self.handle_request()

    def do_POST(self):
        self.handle_request()

    def do_DELETE(self):
        self.handle_request()

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "http://localhost:5173")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, DELETE")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Ollama-Bypass-Token")
        self.send_header("Access-Control-Max-Age", "86400")
        self.end_headers()


def run_secure_proxy():
    print("=====================================================================")
    print("OLLAMA SECURE EMBEDDED REVERSE PROXY & FIREWALL SHIELD")
    print("=====================================================================")
    print(f"[*] Secure Token Generated & Saved to: {SECURE_TOKEN_FILE}")
    print(f"[*] Access Token key: {master_token}")
    print(f"[*] Upstream Target (Strict Loopback): {DEFAULT_UPSTREAM_URL}")
    print(f"[*] Proxy Firewall binding to: http://{PROXY_HOST}:{PROXY_PORT}")
    print(f"[*] Protected Host Headers: {list(ALLOWED_HOSTS)}")
    print("=====================================================================")
    
    server_address = (PROXY_HOST, PROXY_PORT)
    try:
        httpd = HTTPServer(server_address, SecureOllamaProxyHandler)
        print("[+] Firewall shield fully operational and listening. Protect mode: ACTIVE.\n")
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[!] Shutting down secure reverse proxy. Exit clean.")
    except Exception as e:
        print(f"\n[⚠️] Failed to spin up proxy server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_secure_proxy()
