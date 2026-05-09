#!/usr/bin/env python3
"""
Coven Mail Bridge — Salem's mailbox, exposed for the dashboard.

Pure-stdlib HTTP server (matches the original mailbox-server.py ethos: no deps).

Endpoints (all JSON unless noted):
  Health & metrics
    GET  /health
    GET  /metrics                       Prometheus exposition

  Mailbox (reads inbox.jsonl + cursor.txt directly from the mounted volume)
    GET  /api/unread-count
    GET  /api/messages?limit=N
    POST /api/mark-read

  Send (proxies to each familiar's /hooks/agent)
    POST /api/send/{familiar}           body: {"message":"...","from":"..."}
    POST /api/broadcast                 body: {"message":"...","from":"..."}

  Debug primitives (research-backed; see docs/09-debugging.md)
    GET  /api/peer-ping                 quick /health roundtrip per familiar
    GET  /api/circuits                  circuit-breaker state per familiar
    POST /api/selftest                  broadcast a "respond with alive" probe

Auth model: Tailscale is the boundary. No app-level auth. Don't expose to
the public internet.
"""

import http.server
import json
import os
import socketserver
import time
import urllib.request
import urllib.error
from pathlib import Path

# ── Configuration ────────────────────────────────────────────────────────
MAILBOX_DIR = Path(os.environ.get("MAILBOX_DIR", "/mailbox"))
INBOX_FILE  = MAILBOX_DIR / "inbox.jsonl"
CURSOR_FILE = MAILBOX_DIR / "cursor.txt"
PORT        = int(os.environ.get("PORT", 18793))

FAMILIARS = {
    "salem":  {"host": os.environ.get("SALEM_HOST",  ""), "port": os.environ.get("SALEM_GATEWAY_PORT",  "18789"), "token": os.environ.get("SALEM_HOOK_TOKEN",  "")},
    "hilda":  {"host": os.environ.get("HILDA_HOST",  ""), "port": os.environ.get("HILDA_GATEWAY_PORT",  "18790"), "token": os.environ.get("HILDA_HOOK_TOKEN",  "")},
    "zelda":  {"host": os.environ.get("ZELDA_HOST",  ""), "port": os.environ.get("ZELDA_GATEWAY_PORT",  "18789"), "token": os.environ.get("ZELDA_HOOK_TOKEN",  "")},
    "harvey": {"host": os.environ.get("HARVEY_HOST", ""), "port": os.environ.get("HARVEY_GATEWAY_PORT", "18789"), "token": os.environ.get("HARVEY_HOOK_TOKEN", "")},
}

# ── Circuit breaker state ────────────────────────────────────────────────
# closed = healthy, open = stop trying for 60s, half-open = next call probes.
CIRCUITS = {n: {"state": "closed", "failures": 0, "last_failure": 0.0, "last_success": 0.0} for n in FAMILIARS}
CIRCUIT_FAILURE_THRESHOLD = 3
CIRCUIT_OPEN_DURATION_S   = 60

# ── In-memory metrics (Prometheus exposition) ────────────────────────────
METRICS = {
    "coven_mail_sent_total":          0,
    "coven_mail_send_errors_total":   0,
    "coven_peer_pings_total":         0,
    "coven_peer_ping_errors_total":   0,
    "coven_circuit_trips_total":      0,
    "coven_selftests_total":          0,
}


# ── Mailbox file helpers ─────────────────────────────────────────────────
def read_inbox():
    if not INBOX_FILE.exists():
        return []
    out = []
    with open(INBOX_FILE) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def read_cursor():
    if not CURSOR_FILE.exists():
        return 0
    try:
        return int(CURSOR_FILE.read_text().strip())
    except (ValueError, OSError):
        return 0


def write_cursor(n):
    CURSOR_FILE.write_text(str(n))


# ── Familiar hook caller (with circuit breaker) ──────────────────────────
def call_familiar_hook(name, message, sender="sabrina"):
    if name not in FAMILIARS:
        raise ValueError(f"unknown familiar: {name}")
    f = FAMILIARS[name]
    if not f["host"] or not f["token"]:
        raise RuntimeError(f"{name} not configured (missing host or token)")

    c = CIRCUITS[name]
    now = time.time()
    if c["state"] == "open":
        if now - c["last_failure"] > CIRCUIT_OPEN_DURATION_S:
            c["state"] = "half-open"
        else:
            raise ConnectionError(f"circuit open for {name}")

    url = f"http://{f['host']}:{f['port']}/hooks/agent"
    payload = json.dumps({
        "message": f"[Message from {sender}] {message}",
        "name": f"coven-{sender}",
    }).encode()
    req = urllib.request.Request(
        url, data=payload, method="POST",
        headers={
            "Authorization": f"Bearer {f['token']}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            c["state"] = "closed"
            c["failures"] = 0
            c["last_success"] = now
            METRICS["coven_mail_sent_total"] += 1
            return resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, OSError) as e:
        c["failures"] += 1
        c["last_failure"] = now
        METRICS["coven_mail_send_errors_total"] += 1
        if c["failures"] >= CIRCUIT_FAILURE_THRESHOLD and c["state"] != "open":
            c["state"] = "open"
            METRICS["coven_circuit_trips_total"] += 1
        raise


def ping_familiar_health(name):
    f = FAMILIARS[name]
    if not f["host"]:
        return {"ok": False, "error": "not configured"}
    METRICS["coven_peer_pings_total"] += 1
    try:
        url = f"http://{f['host']}:{f['port']}/health"
        t0 = time.time()
        with urllib.request.urlopen(url, timeout=5) as resp:
            return {"ok": True, "status": resp.status, "latency_ms": int((time.time() - t0) * 1000)}
    except Exception as e:
        METRICS["coven_peer_ping_errors_total"] += 1
        return {"ok": False, "error": str(e)}


# ── HTTP handler ─────────────────────────────────────────────────────────
class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # quieter than default
        return

    # ─ helpers
    def _send(self, status, body, content_type="application/json"):
        if content_type == "application/json" and not isinstance(body, (bytes, bytearray)):
            body = json.dumps(body).encode()
        elif isinstance(body, str):
            body = body.encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _query(self):
        if "?" not in self.path:
            return {}
        out = {}
        for kv in self.path.split("?", 1)[1].split("&"):
            if "=" in kv:
                k, v = kv.split("=", 1)
                out[k] = v
        return out

    def _read_body(self):
        try:
            n = int(self.headers.get("Content-Length", 0))
            return json.loads(self.rfile.read(n)) if n else {}
        except Exception:
            return {}

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    # ─ GET routes
    def do_GET(self):
        path = self.path.split("?", 1)[0]

        if path == "/health":
            return self._send(200, {"ok": True, "service": "coven-mail-bridge"})

        if path == "/api/unread-count":
            messages = read_inbox()
            cursor = read_cursor()
            return self._send(200, {
                "total": len(messages),
                "cursor": cursor,
                "unread": max(0, len(messages) - cursor),
            })

        if path == "/api/messages":
            limit = int(self._query().get("limit", 20))
            messages = read_inbox()
            cursor = read_cursor()
            recent = list(reversed(messages[-limit:]))
            for i, m in enumerate(recent):
                line_num = len(messages) - i  # 1-indexed
                m["read"] = line_num <= cursor
            return self._send(200, {
                "messages": recent,
                "total": len(messages),
                "cursor": cursor,
            })

        if path == "/api/peer-ping":
            return self._send(200, {n: ping_familiar_health(n) for n in FAMILIARS})

        if path == "/api/circuits":
            return self._send(200, CIRCUITS)

        if path == "/metrics":
            lines = []
            for k, v in METRICS.items():
                lines.append(f"# TYPE {k} counter")
                lines.append(f"{k} {v}")
            messages = read_inbox()
            cursor = read_cursor()
            lines.append("# TYPE coven_mailbox_messages_total counter")
            lines.append(f"coven_mailbox_messages_total {len(messages)}")
            lines.append("# TYPE coven_mailbox_unread gauge")
            lines.append(f"coven_mailbox_unread {max(0, len(messages) - cursor)}")
            lines.append("# TYPE coven_circuit_open gauge")
            for n, c in CIRCUITS.items():
                lines.append(f'coven_circuit_open{{familiar="{n}"}} {1 if c["state"] == "open" else 0}')
            return self._send(200, "\n".join(lines) + "\n", "text/plain; version=0.0.4")

        if path == "/" or path == "/spellbook":
            # Tiny self-served HTML for the spell-history view (linked from Homepage).
            return self._send(200, _SPELLBOOK_HTML, "text/html; charset=utf-8")

        return self._send(404, {"error": "not found"})

    # ─ POST routes
    def do_POST(self):
        path = self.path.split("?", 1)[0]
        data = self._read_body()

        if path == "/api/mark-read":
            messages = read_inbox()
            write_cursor(len(messages))
            return self._send(200, {"ok": True, "cursor": len(messages)})

        if path == "/api/broadcast":
            msg = data.get("message", "").strip()
            sender = data.get("from", "sabrina")
            if not msg:
                return self._send(400, {"error": "message required"})
            results = {}
            for n in FAMILIARS:
                try:
                    call_familiar_hook(n, msg, sender)
                    results[n] = "sent"
                except Exception as e:
                    results[n] = f"error: {e}"
            return self._send(200, results)

        if path.startswith("/api/send/"):
            n = path.split("/", 3)[3]
            msg = data.get("message", "").strip()
            sender = data.get("from", "sabrina")
            if n not in FAMILIARS:
                return self._send(404, {"error": f"unknown familiar: {n}"})
            if not msg:
                return self._send(400, {"error": "message required"})
            try:
                call_familiar_hook(n, msg, sender)
                return self._send(200, {"ok": True})
            except Exception as e:
                return self._send(502, {"error": str(e)})

        if path == "/api/selftest":
            METRICS["coven_selftests_total"] += 1
            results = {}
            for n in FAMILIARS:
                try:
                    call_familiar_hook(n, "Self-test from Sabrina — please respond with 'alive'.", "self-test")
                    results[n] = "dispatched"
                except Exception as e:
                    results[n] = f"error: {e}"
            return self._send(200, results)

        return self._send(404, {"error": "not found"})


# ── Self-served HTML: Spellbook (history) + Sabrina's Console (send/debug) ──
_SPELLBOOK_HTML = r"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>✨ The Spellbook</title>
<link href="https://fonts.googleapis.com/css2?family=Cinzel+Decorative:wght@700;900&family=Sacramento&family=Quicksand:wght@400;500;700&display=swap" rel="stylesheet">
<style>
  :root {
    --midnight:#0F0524; --velvet:#1A0B2E; --wine:#2D1B4E;
    --pink:#FF1493; --hot:#FF6EC7; --lav:#B19CD9; --gold:#FFD700; --cream:#F5E6FF;
  }
  *{box-sizing:border-box} html,body{margin:0;padding:0}
  body{
    font-family:'Quicksand',sans-serif;color:var(--cream);
    background:
      radial-gradient(ellipse at 20% 10%, rgba(255,20,147,.18), transparent 55%),
      radial-gradient(ellipse at 85% 30%, rgba(177,156,217,.20), transparent 55%),
      linear-gradient(180deg,var(--midnight),var(--velvet) 60%,var(--wine));
    min-height:100vh;padding:32px 24px;
  }
  h1{
    font-family:'Sacramento',cursive;font-size:64px;color:var(--hot);
    text-align:center;margin:0 0 6px;text-shadow:0 0 16px rgba(255,20,147,.6);
  }
  .sub{text-align:center;font-family:'Cinzel Decorative',serif;letter-spacing:3px;color:var(--lav);margin-bottom:24px}
  .container{max-width:900px;margin:0 auto}
  .tabs{display:flex;justify-content:center;gap:8px;margin-bottom:24px}
  .tab{
    background:rgba(26,11,46,.7);border:1px solid rgba(177,156,217,.3);color:var(--cream);
    padding:8px 18px;border-radius:10px;cursor:pointer;font-family:'Cinzel Decorative',serif;
    letter-spacing:1.5px;font-size:.9em;transition:all .2s;
  }
  .tab.active{background:linear-gradient(135deg,var(--pink),var(--hot));border-color:var(--gold);box-shadow:0 0 12px rgba(255,20,147,.5)}
  .tab:hover:not(.active){border-color:var(--hot)}
  .panel{display:none}
  .panel.active{display:block}

  /* History */
  .msg{
    background:linear-gradient(135deg,rgba(45,27,78,.85),rgba(74,44,122,.65));
    border:1px solid rgba(255,110,199,.35);border-radius:14px;padding:18px 22px;margin:14px 0;
    box-shadow:0 4px 20px rgba(15,5,36,.6),inset 0 1px 0 rgba(245,230,255,.08);
  }
  .msg.unread{border-color:var(--gold);box-shadow:0 0 16px rgba(255,215,0,.3),0 4px 20px rgba(15,5,36,.6)}
  .from{color:var(--hot);font-weight:700;font-family:'Cinzel Decorative',serif;letter-spacing:1.5px}
  .ts{color:var(--lav);font-size:.85em;float:right}
  .subj{color:var(--cream);font-style:italic;margin:6px 0}
  .body{color:var(--cream);white-space:pre-wrap;margin-top:8px}
  .empty{text-align:center;padding:60px;color:var(--lav)}
  .badge{display:inline-block;background:var(--gold);color:#000;border-radius:12px;padding:2px 10px;font-size:.8em;margin-left:8px}

  /* Console */
  .card{
    background:linear-gradient(135deg,rgba(45,27,78,.85),rgba(74,44,122,.65));
    border:1px solid rgba(255,110,199,.35);border-radius:14px;padding:22px;margin:16px 0;
    box-shadow:0 4px 20px rgba(15,5,36,.6);
  }
  .card h2{
    font-family:'Cinzel Decorative',serif;color:var(--lav);letter-spacing:2px;
    text-transform:uppercase;margin:0 0 16px;font-size:1.1em;
  }
  label{display:block;color:var(--gold);font-size:.8em;letter-spacing:1.2px;text-transform:uppercase;margin-bottom:6px}
  textarea, input, select{
    width:100%;background:rgba(26,11,46,.7);border:1px solid rgba(177,156,217,.4);border-radius:10px;
    color:var(--cream);padding:10px 14px;font-family:'Quicksand',sans-serif;font-size:1em;margin-bottom:14px;
  }
  textarea{min-height:80px;resize:vertical}
  textarea:focus, input:focus, select:focus{outline:none;border-color:var(--hot);box-shadow:0 0 8px rgba(255,110,199,.5)}
  .btn{
    background:linear-gradient(135deg,var(--pink),var(--hot));border:none;border-radius:10px;
    color:#fff;padding:10px 20px;font-family:'Quicksand',sans-serif;font-weight:700;cursor:pointer;
    box-shadow:0 0 12px rgba(255,20,147,.5);margin-right:8px;
  }
  .btn:hover{filter:brightness(1.15)}
  .btn.ghost{background:transparent;border:1px solid var(--lav);color:var(--lav);box-shadow:none}
  .toolbar{text-align:center;margin-bottom:24px}
  .grid{display:grid;grid-template-columns:repeat(2,1fr);gap:12px;margin-top:8px}
  .ping{
    padding:10px 14px;border-radius:10px;background:rgba(26,11,46,.5);
    border:1px solid rgba(177,156,217,.2);
  }
  .ping.ok{border-color:rgba(126,196,255,.5)}
  .ping.fail{border-color:var(--pink)}
  .ping .name{font-family:'Cinzel Decorative',serif;color:var(--cream);letter-spacing:1.2px}
  .ping .detail{font-size:.85em;color:var(--lav);margin-top:4px}
  pre{background:rgba(15,5,36,.6);padding:12px;border-radius:8px;overflow:auto;color:var(--cream);font-size:.85em}
  .ok-text{color:#7EC4FF}
  .err-text{color:var(--pink)}
</style>
</head><body>
<div class="container">
  <h1>✨ The Spellbook ✨</h1>
  <div class="sub">CAST HISTORY · COVEN COMMAND CONSOLE</div>

  <div class="tabs">
    <button class="tab active" data-panel="history">📜 History</button>
    <button class="tab" data-panel="send">💌 Send Mail</button>
    <button class="tab" data-panel="debug">🔍 Debug</button>
  </div>

  <!-- History -->
  <div class="panel active" id="panel-history">
    <div class="toolbar">
      <button class="btn" onclick="markRead()">Mark all read</button>
      <span id="count" style="margin-left:16px"></span>
    </div>
    <div id="messages" class="empty">Consulting the book…</div>
  </div>

  <!-- Send / Broadcast -->
  <div class="panel" id="panel-send">
    <div class="card">
      <h2>💌 Send to one familiar</h2>
      <label>To</label>
      <select id="send-to">
        <option value="salem">🐈‍⬛ Salem</option>
        <option value="hilda">☕ Hilda</option>
        <option value="zelda">📖 Zelda</option>
        <option value="harvey">🛠 Harvey</option>
      </select>
      <label>From (your sender name)</label>
      <input id="send-from" value="sabrina">
      <label>Message</label>
      <textarea id="send-msg" placeholder="Cast a spell, ask a question, request a status check…"></textarea>
      <button class="btn" onclick="sendOne()">Cast spell</button>
      <span id="send-result" style="margin-left:12px"></span>
    </div>
    <div class="card">
      <h2>🔮 Broadcast to the whole coven</h2>
      <label>From</label>
      <input id="bcast-from" value="sabrina">
      <label>Message</label>
      <textarea id="bcast-msg" placeholder="A message every familiar receives at once."></textarea>
      <button class="btn" onclick="broadcast()">Broadcast</button>
      <pre id="bcast-result" style="display:none"></pre>
    </div>
  </div>

  <!-- Debug -->
  <div class="panel" id="panel-debug">
    <div class="card">
      <h2>🩺 Peer ping — is everyone alive?</h2>
      <button class="btn" onclick="peerPing()">Run peer-ping</button>
      <button class="btn ghost" onclick="selftest()">Broadcast selftest</button>
      <div class="grid" id="ping-grid"></div>
    </div>
    <div class="card">
      <h2>⚡ Circuit breakers</h2>
      <button class="btn ghost" onclick="circuits()">Refresh state</button>
      <pre id="circuit-result" style="display:none"></pre>
    </div>
  </div>
</div>

<script>
const tabs = document.querySelectorAll('.tab');
tabs.forEach(t => t.addEventListener('click', () => {
  tabs.forEach(x => x.classList.remove('active'));
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  t.classList.add('active');
  document.getElementById('panel-' + t.dataset.panel).classList.add('active');
}));

const esc = s => (s||'').replace(/[<>&]/g, c => ({'<':'&lt;','>':'&gt;','&':'&amp;'})[c]);

async function loadHistory() {
  const r = await fetch('/api/messages?limit=100');
  const d = await r.json();
  document.getElementById('count').innerHTML =
    `${d.messages.length} of ${d.total} entries${d.total - d.cursor ? ` <span class="badge">${d.total - d.cursor} unread</span>` : ''}`;
  const el = document.getElementById('messages');
  if (!d.messages.length) { el.innerHTML = '<div class="empty">No spells cast yet.</div>'; return; }
  el.innerHTML = d.messages.map(m => `
    <div class="msg${m.read ? '' : ' unread'}">
      <span class="ts">${esc(m.ts)}</span>
      <div class="from">${esc(m.from || 'unknown')}</div>
      ${m.subject ? `<div class="subj">${esc(m.subject)}</div>` : ''}
      <div class="body">${esc(m.body)}</div>
    </div>`).join('');
}
async function markRead() { await fetch('/api/mark-read', {method:'POST'}); loadHistory(); }

async function sendOne() {
  const to = document.getElementById('send-to').value;
  const msg = document.getElementById('send-msg').value.trim();
  const from = document.getElementById('send-from').value.trim() || 'sabrina';
  if (!msg) return;
  const r = await fetch('/api/send/' + to, {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({message: msg, from: from})
  });
  const d = await r.json();
  document.getElementById('send-result').innerHTML = r.ok
    ? '<span class="ok-text">✨ cast successfully</span>'
    : '<span class="err-text">✗ ' + esc(d.error || 'failed') + '</span>';
}
async function broadcast() {
  const msg = document.getElementById('bcast-msg').value.trim();
  const from = document.getElementById('bcast-from').value.trim() || 'sabrina';
  if (!msg) return;
  const r = await fetch('/api/broadcast', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({message: msg, from: from})
  });
  const d = await r.json();
  const el = document.getElementById('bcast-result');
  el.style.display = 'block';
  el.textContent = JSON.stringify(d, null, 2);
}

async function peerPing() {
  const r = await fetch('/api/peer-ping');
  const d = await r.json();
  document.getElementById('ping-grid').innerHTML = Object.entries(d).map(([n, p]) => `
    <div class="ping ${p.ok ? 'ok' : 'fail'}">
      <div class="name">${n.toUpperCase()}</div>
      <div class="detail">${p.ok ? `✨ alive · ${p.latency_ms}ms` : '✗ ' + esc(p.error)}</div>
    </div>`).join('');
}
async function selftest() {
  const r = await fetch('/api/selftest', {method:'POST'});
  const d = await r.json();
  alert('Self-test dispatched:\n' + JSON.stringify(d, null, 2));
}
async function circuits() {
  const r = await fetch('/api/circuits');
  const d = await r.json();
  const el = document.getElementById('circuit-result');
  el.style.display = 'block';
  el.textContent = JSON.stringify(d, null, 2);
}

loadHistory();
setInterval(loadHistory, 5000);
</script>
</body></html>
"""


class ThreadingServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


if __name__ == "__main__":
    server = ThreadingServer(("0.0.0.0", PORT), Handler)
    print(f"🐈‍⬛ Coven Mail Bridge listening on :{PORT}", flush=True)
    server.serve_forever()
