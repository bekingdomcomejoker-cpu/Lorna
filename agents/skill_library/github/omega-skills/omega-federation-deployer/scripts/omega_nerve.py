import os, json, time, hmac, subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

NODE_ID = "OMEGA_NODE_1"
TOKEN = "OMEGA_RESONANCE_1.67"

def log_bus(task_id, action, status, result):
    entry = {"timestamp": time.time(), "task_id": task_id, "action": action, "status": status, "result": result}
    with open(os.path.expanduser("~/omega_root/logs/comm_bus.jsonl"), "a") as f:
        f.write(json.dumps(entry) + "\n")

class SovereignGovernor(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            cl = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(cl).decode("utf-8"))
            provided_token = self.headers.get("X-Node-Token")
            if not provided_token or not hmac.compare_digest(provided_token, TOKEN):
                self.send_response(401); self.end_headers(); return
            action = data.get("action")
            task_id = data.get("task_id", "task-init")
            log_bus(task_id, action, "Success", "Nerve Acknowledged")
            self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers()
            self.wfile.write(json.dumps({"ok": True, "task_id": task_id}).encode("utf-8"))
        except Exception as e:
            self.send_response(500); self.end_headers(); self.wfile.write(str(e).encode())

if __name__ == "__main__":
    print(f"[*] OMEGA NERVE {NODE_ID} online.")
