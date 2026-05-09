#!/usr/bin/env python3
"""
Coven Mail Bridge — Salem's mailbox + coven observability layer.

Pure-stdlib HTTP server. Exposes a normalized API that the dashboard,
Magic Mirror, and any familiar can consume.

Endpoints:
  Health & metrics
    GET  /health
    GET  /metrics                      Prometheus exposition

  Mailbox
    GET  /api/unread-count
    GET  /api/messages?limit=N
    POST /api/mark-read

  Send (proxies to each familiar's /hooks/agent)
    POST /api/send/{familiar}
    POST /api/broadcast

  Familiar status (used by Homepage tiles — fixes the API-error tiles)
    GET  /api/familiar/{name}          normalized summary per familiar
    GET  /api/coven-summary            all 4 in one call
    GET  /api/peer-ping                /health roundtrip per peer
    GET  /api/circuits                 circuit-breaker state

  Coven observability
    GET  /api/activity?limit=N         live feed (mail + circuit + heartbeats)
    GET  /api/cron                     cron heartbeats + state
    POST /api/cron/heartbeat           cron jobs call this when they run
    GET  /api/watchdog                 watchdog heartbeats
    POST /api/watchdog/heartbeat       watchdogs call this each cycle
    GET  /api/upgrades                 docker image update availability
                                       + GitHub release notes "review"

  Debug
    POST /api/selftest                 broadcast probe to all familiars

  Familiar self-service (so familiars can use the bridge without humans)
    POST /api/event                    log any structured event to the feed
                                       (used for subagent lifecycle, decisions,
                                        spell-cast markers, anything you want
                                        surfaced in Surveillance)
    GET  /api/handbook                 returns the Familiar's Handbook markdown
                                       so each familiar can self-serve the manual

Auth model: Tailscale is the boundary. No app-level auth.
"""

import http.server
import json
import os
import socketserver
import time
import urllib.request
import urllib.error
from collections import deque
from pathlib import Path

# ── Configuration ────────────────────────────────────────────────────────
MAILBOX_DIR  = Path(os.environ.get("MAILBOX_DIR", "/mailbox"))
INBOX_FILE   = MAILBOX_DIR / "inbox.jsonl"
CURSOR_FILE  = MAILBOX_DIR / "cursor.txt"
HANDBOOK_FILE = Path(os.environ.get("HANDBOOK_FILE", "/app/handbook.md"))
PORT         = int(os.environ.get("PORT", 18793))

FAMILIARS = {
    "salem":  {
        "host": os.environ.get("SALEM_HOST",  ""),
        "port": os.environ.get("SALEM_GATEWAY_PORT",  "18789"),
        "hook_token":    os.environ.get("SALEM_HOOK_TOKEN",    ""),
        "gateway_token": os.environ.get("SALEM_GATEWAY_TOKEN", ""),
    },
    "hilda":  {
        "host": os.environ.get("HILDA_HOST",  ""),
        "port": os.environ.get("HILDA_GATEWAY_PORT",  "18790"),
        "hook_token":    os.environ.get("HILDA_HOOK_TOKEN",    ""),
        "gateway_token": os.environ.get("HILDA_GATEWAY_TOKEN", ""),
    },
    "zelda":  {
        "host": os.environ.get("ZELDA_HOST",  ""),
        "port": os.environ.get("ZELDA_GATEWAY_PORT",  "18789"),
        "hook_token":    os.environ.get("ZELDA_HOOK_TOKEN",    ""),
        "gateway_token": os.environ.get("ZELDA_GATEWAY_TOKEN", ""),
    },
    "harvey": {
        "host": os.environ.get("HARVEY_HOST", ""),
        "port": os.environ.get("HARVEY_GATEWAY_PORT", "18789"),
        "hook_token":    os.environ.get("HARVEY_HOOK_TOKEN",    ""),
        "gateway_token": os.environ.get("HARVEY_GATEWAY_TOKEN", ""),
    },
}

# Services we know how to check for upgrades. (image, github_repo)
UPGRADE_SERVICES = [
    ("homepage",     "ghcr.io/gethomepage/homepage", "gethomepage/homepage"),
    ("beszel",       "henrygd/beszel",               "henrygd/beszel"),
    ("prometheus",   "prom/prometheus",              "prometheus/prometheus"),
    ("alertmanager", "prom/alertmanager",            "prometheus/alertmanager"),
    ("grafana",      "grafana/grafana",              "grafana/grafana"),
    ("nginx",        "nginx",                        "nginx/nginx"),
]

# ── Circuit breakers ─────────────────────────────────────────────────────
CIRCUITS = {n: {"state": "closed", "failures": 0, "last_failure": 0.0, "last_success": 0.0} for n in FAMILIARS}
CIRCUIT_FAILURE_THRESHOLD = 3
CIRCUIT_OPEN_DURATION_S   = 60

# ── Activity ring buffer (for live feed) ─────────────────────────────────
ACTIVITY = deque(maxlen=500)
def log_activity(kind, **fields):
    ACTIVITY.appendleft({"ts": time.time(), "kind": kind, **fields})

# ── Heartbeats: cron + watchdog ──────────────────────────────────────────
# In-memory only (resets on bridge restart, which is fine for heartbeats).
CRON_HEARTBEATS = {}      # name → {last_seen, status, last_output, host, schedule}
WATCHDOG_HEARTBEATS = {}  # name → {last_seen, status, last_output, host}

# ── Upgrade-check cache (1h TTL) ─────────────────────────────────────────
UPGRADE_CACHE = {"data": None, "fetched_at": 0.0}
UPGRADE_TTL_S = 3600

# ── Metrics ──────────────────────────────────────────────────────────────
METRICS = {
    "coven_mail_sent_total":          0,
    "coven_mail_send_errors_total":   0,
    "coven_peer_pings_total":         0,
    "coven_peer_ping_errors_total":   0,
    "coven_circuit_trips_total":      0,
    "coven_selftests_total":          0,
    "coven_familiar_summary_errors_total": 0,
    "coven_upgrade_checks_total":     0,
    "coven_events_total":             0,
    "coven_handbook_fetches_total":   0,
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


# ── Familiar HTTP helpers ────────────────────────────────────────────────
def call_familiar_hook(name, message, sender="sabrina"):
    if name not in FAMILIARS:
        raise ValueError(f"unknown familiar: {name}")
    f = FAMILIARS[name]
    if not f["host"] or not f["hook_token"]:
        raise RuntimeError(f"{name} not configured (host or hook_token missing)")

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
            "Authorization": f"Bearer {f['hook_token']}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            c["state"] = "closed"
            c["failures"] = 0
            c["last_success"] = now
            METRICS["coven_mail_sent_total"] += 1
            log_activity("mail-sent", to=name, sender=sender, summary=message[:120])
            return resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, OSError) as e:
        c["failures"] += 1
        c["last_failure"] = now
        METRICS["coven_mail_send_errors_total"] += 1
        log_activity("mail-send-error", to=name, error=str(e))
        if c["failures"] >= CIRCUIT_FAILURE_THRESHOLD and c["state"] != "open":
            c["state"] = "open"
            METRICS["coven_circuit_trips_total"] += 1
            log_activity("circuit-open", familiar=name, after_failures=c["failures"])
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


def fetch_familiar_summary(name):
    """Normalized summary per familiar.

    Tries /api/diagnostics/summary with the gateway bearer; falls back to
    /health if that's unavailable. Always returns a stable shape so the
    dashboard tiles never break.
    """
    f = FAMILIARS[name]
    if not f["host"]:
        return {"name": name, "ok": False, "error": "not configured"}

    base = {"name": name, "host": f["host"], "port": f["port"], "ok": False,
            "model": "—", "tokens_per_sec": 0.0, "active_sessions": 0,
            "latency_ms": None, "error": None}

    # 1. Try the rich diagnostics endpoint
    if f["gateway_token"]:
        try:
            url = f"http://{f['host']}:{f['port']}/api/diagnostics/summary"
            req = urllib.request.Request(url, headers={"Authorization": f"Bearer {f['gateway_token']}"})
            t0 = time.time()
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.load(resp)
            return {**base,
                    "ok": True,
                    "model": data.get("model", base["model"]),
                    "tokens_per_sec": float(data.get("tokens_per_sec", 0) or 0),
                    "active_sessions": int(data.get("active_sessions", 0) or 0),
                    "latency_ms": int((time.time() - t0) * 1000)}
        except Exception:
            METRICS["coven_familiar_summary_errors_total"] += 1

    # 2. Fall back to /health (no auth, no detail)
    try:
        url = f"http://{f['host']}:{f['port']}/health"
        t0 = time.time()
        with urllib.request.urlopen(url, timeout=5) as resp:
            return {**base, "ok": True, "latency_ms": int((time.time() - t0) * 1000)}
    except Exception as e:
        return {**base, "error": str(e)}


# ── Activity feed (mail + circuits + heartbeats merged) ──────────────────
def get_activity_feed(limit=50):
    events = list(ACTIVITY)[:limit * 2]

    # Pull recent mail entries into the same shape so they appear in the feed
    cursor = read_cursor()
    msgs = read_inbox()
    for i, m in enumerate(msgs[-limit:]):
        line_num = len(msgs) - len(msgs[-limit:]) + i + 1
        ts_str = m.get("ts", "")
        try:
            ts = time.mktime(time.strptime(ts_str.split(".")[0], "%Y-%m-%dT%H:%M:%S"))
        except (ValueError, AttributeError):
            ts = 0
        events.append({
            "ts": ts,
            "kind": "mail-received",
            "from": m.get("from", "?"),
            "to":   m.get("to", "salem"),
            "summary": m.get("subject") or (m.get("body", "")[:120]),
            "read": line_num <= cursor,
        })

    events.sort(key=lambda e: e.get("ts", 0), reverse=True)
    return events[:limit]


# ── Upgrade availability + release-note review ───────────────────────────
def fetch_upgrade_check():
    """Check Docker Hub + GitHub releases for each tracked service.

    Cached for an hour. Returns one entry per service with the latest
    available tag, current pinned tag (if any in compose), and a tiny
    "review" of the release notes (sentiment + top excerpt).
    """
    if UPGRADE_CACHE["data"] and time.time() - UPGRADE_CACHE["fetched_at"] < UPGRADE_TTL_S:
        return UPGRADE_CACHE["data"]

    METRICS["coven_upgrade_checks_total"] += 1
    out = []
    for service, image, gh in UPGRADE_SERVICES:
        entry = {"service": service, "image": image, "github": gh,
                 "latest_tag": None, "release": None, "review": None, "error": None}
        try:
            tag = _fetch_latest_tag(image)
            entry["latest_tag"] = tag
        except Exception as e:
            entry["error"] = f"docker-hub: {e}"
        try:
            release = _fetch_latest_release(gh)
            entry["release"] = release
            entry["review"] = _review_release(release.get("body", ""))
        except Exception as e:
            entry["error"] = (entry["error"] or "") + f" github: {e}"
        out.append(entry)

    UPGRADE_CACHE["data"] = out
    UPGRADE_CACHE["fetched_at"] = time.time()
    return out


def _fetch_latest_tag(image):
    # Strip ghcr.io/ prefix; treat short names as docker.io/library
    if image.startswith("ghcr.io/"):
        # GitHub Container Registry — use GitHub API on the source repo via the GH releases path
        return None  # we get this via _fetch_latest_release instead
    repo = image if "/" in image else f"library/{image}"
    url = f"https://hub.docker.com/v2/repositories/{repo}/tags?page_size=20&ordering=last_updated"
    with urllib.request.urlopen(url, timeout=10) as resp:
        data = json.load(resp)
    for t in data.get("results", []):
        name = t.get("name", "")
        if name and name not in ("latest", "main", "master") and not name.endswith("-rc") and not name.endswith("-beta"):
            return name
    return None


def _fetch_latest_release(gh_repo):
    url = f"https://api.github.com/repos/{gh_repo}/releases/latest"
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "coven-mail-bridge"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.load(resp)
    return {
        "tag_name":     data.get("tag_name"),
        "name":         data.get("name"),
        "published_at": data.get("published_at"),
        "html_url":     data.get("html_url"),
        "body":         (data.get("body") or "")[:2000],
    }


def _review_release(body):
    """Cheap heuristic 'review' of release notes.

    Returns a dict with sentiment + flags so the UI can show a tldr.
    """
    if not body:
        return {"verdict": "unknown", "flags": [], "summary": ""}
    body_l = body.lower()
    flags = []
    for term, label in [
        ("breaking",        "breaking-change"),
        ("regression",      "regression"),
        ("security",        "security-fix"),
        ("cve-",            "cve"),
        ("deprecat",        "deprecation"),
        ("known issue",     "known-issue"),
        ("rollback",        "rollback-recommended"),
    ]:
        if term in body_l:
            flags.append(label)

    fix_count  = body_l.count("fix") + body_l.count("bug")
    feat_count = body_l.count("feat") + body_l.count("add ")

    if any(f in flags for f in ("regression", "rollback-recommended")):
        verdict = "wait"
    elif any(f in flags for f in ("breaking-change", "deprecation")):
        verdict = "review"
    elif fix_count > 0 or "security-fix" in flags:
        verdict = "recommended"
    else:
        verdict = "safe"

    # First short paragraph
    first_para = body.split("\n\n")[0].strip()
    if len(first_para) > 280:
        first_para = first_para[:280].rsplit(" ", 1)[0] + "…"

    return {
        "verdict":  verdict,           # safe | recommended | review | wait | unknown
        "flags":    flags,
        "summary":  first_para,
        "fix_count":  fix_count,
        "feat_count": feat_count,
    }


# ── HTTP handler ─────────────────────────────────────────────────────────
class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

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

    # ─ GET routes ────────────────────────────────────────────────────────
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
                line_num = len(messages) - i
                m["read"] = line_num <= cursor
            return self._send(200, {"messages": recent, "total": len(messages), "cursor": cursor})

        if path == "/api/peer-ping":
            return self._send(200, {n: ping_familiar_health(n) for n in FAMILIARS})

        if path == "/api/circuits":
            return self._send(200, CIRCUITS)

        if path.startswith("/api/familiar/"):
            n = path.split("/", 3)[3]
            if n not in FAMILIARS:
                return self._send(404, {"error": f"unknown familiar: {n}"})
            return self._send(200, fetch_familiar_summary(n))

        if path == "/api/coven-summary":
            return self._send(200, {n: fetch_familiar_summary(n) for n in FAMILIARS})

        if path == "/api/activity":
            limit = int(self._query().get("limit", 50))
            return self._send(200, {"events": get_activity_feed(limit)})

        if path == "/api/cron":
            now = time.time()
            return self._send(200, {
                "jobs": [
                    {**v, "name": k, "stale": (now - v.get("last_seen", 0)) > 24 * 3600}
                    for k, v in CRON_HEARTBEATS.items()
                ]
            })

        if path == "/api/watchdog":
            now = time.time()
            return self._send(200, {
                "watchdogs": [
                    {**v, "name": k, "stale": (now - v.get("last_seen", 0)) > 600}  # 10 min stale
                    for k, v in WATCHDOG_HEARTBEATS.items()
                ]
            })

        if path == "/api/upgrades":
            return self._send(200, {"services": fetch_upgrade_check()})

        if path == "/api/handbook":
            METRICS["coven_handbook_fetches_total"] += 1
            try:
                return self._send(200, HANDBOOK_FILE.read_text(), "text/markdown; charset=utf-8")
            except FileNotFoundError:
                return self._send(404, {"error": "handbook not mounted",
                                        "hint": "expected at /app/handbook.md (mount docs/13-familiar-handbook.md)"})

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
            for n, c in CIRCUITS.items():
                lines.append(f'coven_circuit_open{{familiar="{n}"}} {1 if c["state"] == "open" else 0}')
            now = time.time()
            for k, v in CRON_HEARTBEATS.items():
                lines.append(f'coven_cron_age_seconds{{job="{k}"}} {int(now - v.get("last_seen", now))}')
            for k, v in WATCHDOG_HEARTBEATS.items():
                lines.append(f'coven_watchdog_age_seconds{{watchdog="{k}"}} {int(now - v.get("last_seen", now))}')
            return self._send(200, "\n".join(lines) + "\n", "text/plain; version=0.0.4")

        if path == "/" or path == "/spellbook":
            return self._send(200, _SPELLBOOK_HTML, "text/html; charset=utf-8")

        return self._send(404, {"error": "not found"})

    # ─ POST routes ───────────────────────────────────────────────────────
    def do_POST(self):
        path = self.path.split("?", 1)[0]
        data = self._read_body()

        if path == "/api/mark-read":
            messages = read_inbox()
            write_cursor(len(messages))
            return self._send(200, {"ok": True, "cursor": len(messages)})

        if path == "/api/broadcast":
            msg = (data.get("message", "") or "").strip()
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
            msg = (data.get("message", "") or "").strip()
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

        if path == "/api/event":
            # Generic event from any familiar — used for subagent lifecycle,
            # decisions, spell-cast markers, etc. Anything you POST here lands
            # in the Activity feed and Prometheus event counters.
            kind = (data.get("kind") or "").strip()
            if not kind:
                return self._send(400, {"error": "kind required (e.g. subagent-started)"})
            # Accept any extra fields verbatim — feed displays whatever's there
            extra = {k: v for k, v in data.items() if k != "kind"}
            log_activity(kind, **extra)
            METRICS["coven_events_total"] += 1
            return self._send(200, {"ok": True})

        if path == "/api/cron/heartbeat":
            name = data.get("name", "").strip()
            if not name:
                return self._send(400, {"error": "name required"})
            CRON_HEARTBEATS[name] = {
                "last_seen":   time.time(),
                "status":      data.get("status", "ok"),
                "last_output": (data.get("output") or "")[:500],
                "host":        data.get("host", ""),
                "schedule":    data.get("schedule", ""),
                "duration_ms": data.get("duration_ms"),
            }
            log_activity("cron", name=name, status=data.get("status", "ok"))
            return self._send(200, {"ok": True})

        if path == "/api/watchdog/heartbeat":
            name = data.get("name", "").strip()
            if not name:
                return self._send(400, {"error": "name required"})
            WATCHDOG_HEARTBEATS[name] = {
                "last_seen":   time.time(),
                "status":      data.get("status", "ok"),
                "last_output": (data.get("output") or "")[:500],
                "host":        data.get("host", ""),
            }
            log_activity("watchdog", name=name, status=data.get("status", "ok"))
            return self._send(200, {"ok": True})

        return self._send(404, {"error": "not found"})


# ── Self-served HTML (Spellbook UI) ──────────────────────────────────────
# Kept inline to keep the bridge a single-file deploy. Theme matches
# Homepage's Westbridge Dusk palette.
_SPELLBOOK_HTML = r"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>The Spellbook</title>
<link href="https://fonts.googleapis.com/css2?family=Cinzel+Decorative:wght@400;700;900&family=Quicksand:wght@400;500;600;700&family=JetBrains+Mono:wght@300;400&family=Sacramento&display=swap" rel="stylesheet">
<style>
  :root{
    /* Spellman Manor palette — show-accurate Sabrina + Y2K Gen Z layer */
    --ink:#1A1B4B; --ink-velvet:#2A1B5C; --ink-aubergine:#3D1B6E; --ink-cosmic:#5E2A84;
    --glass:rgba(255,220,240,.05); --glass-strong:rgba(255,220,240,.10);
    --glass-border:rgba(255,63,164,.22);
    --hot-pink:#FF3FA4; --rose:#FF6EC7; --bubblegum:#FFB6D5;
    --rose-glow:rgba(255,63,164,.50);
    --lavender:#C8A2DB; --violet:#9B7EDE; --deep-cosmos:#5E2A84;
    --gold:#E8C547; --gold-warm:#FFD66B; --gold-glow:rgba(232,197,71,.45);
    --mint:#A8F0D0; --holo-sky:#A8E0FF; --ember:#FF8E8E; --cream:#F4EAFB;
    --text:#F4EAFB; --text-2:rgba(244,234,251,.78); --text-3:rgba(244,234,251,.50);
    --shimmer:linear-gradient(135deg, #FF3FA4 0%, #FF6EC7 18%, #C8A2DB 38%, #A8E0FF 58%, #E8C547 80%, #FF6EC7 100%);
    --iridescent:conic-gradient(from 180deg at 50% 50%, #FF6EC7, #C8A2DB, #A8E0FF, #FFD66B, #FFB6D5, #FF6EC7);
    --shadow:0 8px 32px rgba(26,27,75,.55), inset 0 1px 0 rgba(244,234,251,.08);
  }
  *{box-sizing:border-box} html,body{margin:0;padding:0}
  body{
    font-family:'Quicksand',system-ui,sans-serif;color:var(--text);min-height:100vh;
    padding:48px 24px 64px;font-weight:500;
    background:
      radial-gradient(ellipse 70% 40% at 18% 12%, rgba(255,63,164,.28), transparent 60%),
      radial-gradient(ellipse 60% 55% at 85% 30%, rgba(155,126,222,.30), transparent 60%),
      radial-gradient(ellipse 50% 40% at 50% 92%, rgba(232,197,71,.10), transparent 60%),
      linear-gradient(180deg, var(--ink), var(--ink-velvet) 50%, var(--ink-aubergine));
  }
  body::after{
    content:'';position:fixed;inset:0;z-index:-1;pointer-events:none;
    background-image:
      radial-gradient(2px 2px at 12% 18%, rgba(244,234,251,.85), transparent 60%),
      radial-gradient(2.5px 2.5px at 28% 72%, rgba(232,197,71,.7), transparent 60%),
      radial-gradient(1.5px 1.5px at 47% 9%, rgba(255,110,199,.7), transparent 60%),
      radial-gradient(2px 2px at 65% 44%, rgba(244,234,251,.55), transparent 60%),
      radial-gradient(1.5px 1.5px at 80% 80%, rgba(232,197,71,.5), transparent 60%),
      radial-gradient(1.5px 1.5px at 8% 55%, rgba(244,234,251,.6), transparent 60%),
      radial-gradient(2px 2px at 38% 38%, rgba(255,63,164,.5), transparent 60%),
      radial-gradient(2px 2px at 56% 67%, rgba(232,197,71,.4), transparent 60%);
    animation:drift 40s ease-in-out infinite alternate;opacity:.95;
  }
  @keyframes drift{
    0%,100%{transform:translate(0,0) scale(1);opacity:.75}
    50%{transform:translate(-6px,4px) scale(1.02);opacity:1}
  }
  h1{
    font-family:'Sacramento',cursive;font-size:72px;font-weight:400;
    background:var(--shimmer);background-size:200% 200%;
    -webkit-background-clip:text;background-clip:text;
    color:transparent;text-align:center;margin:0 0 4px;
    filter:drop-shadow(0 0 28px var(--rose-glow));line-height:1.05;
    animation:shimmer-shift 8s ease-in-out infinite;
  }
  @keyframes shimmer-shift{
    0%,100%{background-position:0% 50%}
    50%{background-position:100% 50%}
  }
  .tech{
    text-align:center;font-family:'JetBrains Mono',monospace;
    color:var(--text-3);font-size:12px;letter-spacing:.4px;
    text-transform:lowercase;margin-bottom:28px;
  }
  .container{max-width:1000px;margin:0 auto;position:relative;z-index:1}
  .tabs{display:flex;justify-content:center;gap:6px;margin-bottom:28px;flex-wrap:wrap}
  .tab{
    background:var(--glass);border:1px solid var(--glass-border);color:var(--text-2);
    padding:9px 20px;border-radius:999px;cursor:pointer;
    font-family:'Cinzel Decorative',serif;font-weight:500;font-size:12px;
    letter-spacing:1.4px;text-transform:uppercase;
    transition:all .25s ease;
    backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);
  }
  .tab.active{
    background:linear-gradient(135deg,rgba(255,111,181,.20),rgba(181,159,255,.20));
    border-color:rgba(255,203,122,.55);color:var(--text);
    box-shadow:0 0 22px rgba(255,111,181,.30);
  }
  .tab:hover:not(.active){border-color:var(--rose);color:var(--text)}
  .panel{display:none}
  .panel.active{display:block;animation:fadein .3s ease}
  @keyframes fadein{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:none}}

  .card{
    background:var(--glass);border:1px solid var(--glass-border);
    border-radius:18px;padding:24px 26px;margin:14px 0;
    backdrop-filter:blur(24px) saturate(150%);
    -webkit-backdrop-filter:blur(24px) saturate(150%);
    box-shadow:var(--shadow);
    position:relative;overflow:hidden;
  }
  .card h2{
    font-family:'Cinzel Decorative',serif;font-weight:700;
    color:var(--text);letter-spacing:.08em;margin:0 0 4px;font-size:17px;
    text-transform:uppercase;position:relative;padding-left:26px;
    text-shadow:0 0 12px var(--rose-glow);
  }
  .card h2::before{
    content:'\2726';position:absolute;left:0;top:50%;transform:translateY(-50%);
    color:var(--gold);font-size:.95em;text-shadow:0 0 14px var(--gold-glow);
    animation:twinkle 3s ease-in-out infinite;
  }
  @keyframes twinkle{
    0%,100%{opacity:1;transform:translateY(-50%) scale(1)}
    50%{opacity:.55;transform:translateY(-50%) scale(1.12)}
  }
  .card .tech-sub{
    font-family:'JetBrains Mono',monospace;color:var(--text-3);
    font-size:11px;letter-spacing:.4px;text-transform:lowercase;
    margin:0 0 18px;padding-left:22px;
  }
  .msg{
    background:var(--glass-strong);border:1px solid var(--glass-border);
    border-radius:14px;padding:16px 20px;margin:10px 0;
    transition:border-color .25s ease;
  }
  .msg:hover{border-color:rgba(255,111,181,.35)}
  .msg.unread{
    border-color:rgba(255,203,122,.5);
    box-shadow:0 0 18px rgba(255,203,122,.18);
  }
  .from{
    color:var(--hot-pink);font-family:'Cinzel Decorative',serif;font-weight:700;
    letter-spacing:.06em;font-size:14px;
    text-shadow:0 0 10px var(--rose-glow);
  }
  .ts{color:var(--text-3);font-family:'JetBrains Mono',monospace;font-size:11px;float:right}
  .subj{color:var(--text);font-style:italic;margin:6px 0;font-size:14px;font-family:'Quicksand',sans-serif}
  .body{color:var(--text-2);white-space:pre-wrap;margin-top:8px;font-size:14px;line-height:1.55;font-family:'Quicksand',sans-serif}
  .empty{text-align:center;padding:60px 20px;color:var(--text-3);font-family:'Cinzel Decorative',serif;font-style:italic;letter-spacing:.05em}
  .badge{
    display:inline-block;background:var(--gold);color:var(--ink-aubergine);
    border-radius:999px;padding:2px 12px;font-size:10px;font-weight:600;
    margin-left:8px;font-family:'JetBrains Mono',monospace;letter-spacing:.5px;
    text-transform:uppercase;
  }

  label{
    display:block;color:var(--text-3);font-size:10px;letter-spacing:1.2px;
    text-transform:uppercase;margin:0 0 6px;font-family:'JetBrains Mono',monospace;
    font-weight:500;
  }
  textarea, input, select{
    width:100%;background:var(--glass-strong);border:1px solid var(--glass-border);
    border-radius:10px;color:var(--text);padding:11px 14px;
    font-family:'Quicksand',sans-serif;font-size:14px;margin-bottom:14px;
    transition:border-color .2s, box-shadow .2s;
  }
  textarea{min-height:80px;resize:vertical}
  textarea:focus, input:focus, select:focus{
    outline:none;border-color:var(--rose);box-shadow:0 0 0 3px rgba(255,111,181,.18);
  }
  /* Glossy bubble button — Y2K Frutiger Aero feel */
  .btn{
    background:linear-gradient(180deg,var(--rose) 0%, var(--hot-pink) 60%, #C12B7E 100%);
    border:none;border-radius:999px;color:var(--cream);
    padding:11px 24px;font-family:'Cinzel Decorative',serif;font-weight:700;font-size:11px;
    letter-spacing:1.4px;text-transform:uppercase;cursor:pointer;
    box-shadow:
      0 4px 18px var(--rose-glow),
      inset 0 1px 0 rgba(255,255,255,.45),
      inset 0 -2px 4px rgba(0,0,0,.15);
    transition:transform .18s, box-shadow .18s;
    text-shadow:0 1px 2px rgba(0,0,0,.20);
  }
  .btn:hover{
    transform:translateY(-1px);
    box-shadow:
      0 6px 28px var(--rose-glow),
      inset 0 1px 0 rgba(255,255,255,.55),
      inset 0 -2px 4px rgba(0,0,0,.10),
      0 0 24px var(--gold-glow);
  }
  .btn.ghost{
    background:transparent;border:1px solid var(--glass-border);color:var(--text-2);
    box-shadow:none;
  }
  .btn.ghost:hover{border-color:var(--rose);color:var(--text);box-shadow:none}

  .toolbar{text-align:center;margin-bottom:20px}
  .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px;margin-top:10px}
  .ping{
    padding:12px 14px;border-radius:12px;background:var(--glass-strong);
    border:1px solid var(--glass-border);
  }
  .ping.ok{border-color:rgba(159,255,228,.5)}
  .ping.fail{border-color:rgba(255,142,142,.6)}
  .ping .name{
    font-family:'Cinzel Decorative',serif;color:var(--text);font-weight:600;
    font-size:14px;letter-spacing:.06em;text-transform:capitalize;
  }
  .ping .detail{font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--text-3);margin-top:4px}
  pre{
    background:rgba(10,4,24,.55);padding:14px 16px;border-radius:10px;overflow:auto;
    color:var(--text-2);font-size:12px;font-family:'JetBrains Mono',monospace;
    border:1px solid var(--glass-border);
  }
  .ok-text{color:var(--mint)} .err-text{color:var(--ember)}

  /* Surveillance — activity feed, cron, watchdog, upgrades */
  .feed-row{
    display:grid;grid-template-columns:108px 110px 1fr;gap:14px;
    padding:11px 14px;border-radius:10px;align-items:start;
    border:1px solid var(--glass-border);background:var(--glass-strong);margin:6px 0;
    font-size:13px;font-family:'Quicksand',sans-serif;
    transition:border-color .2s ease;
  }
  .feed-row:hover{border-color:rgba(255,111,181,.30)}
  .feed-row .when{font-family:'JetBrains Mono',monospace;color:var(--text-3);font-size:11px;letter-spacing:.4px}
  .feed-row .kind{
    font-family:'JetBrains Mono',monospace;color:var(--violet);font-size:10px;
    text-transform:uppercase;letter-spacing:.8px;font-weight:500;
  }
  .feed-row .what{color:var(--text-2);font-size:13px;line-height:1.5}
  .feed-row.kind-mail-received .kind, .feed-row.kind-mail-sent .kind{color:var(--rose)}
  .feed-row.kind-circuit-open .kind, .feed-row.kind-mail-send-error .kind{color:var(--ember)}
  .feed-row.kind-cron .kind{color:var(--gold)}
  .feed-row.kind-watchdog .kind{color:var(--mint)}
  .feed-row.kind-subagent-started .kind, .feed-row.kind-subagent-completed .kind, .feed-row.kind-subagent-error .kind{color:var(--violet)}

  .verdict{
    display:inline-block;padding:3px 12px;border-radius:999px;font-size:10px;
    font-family:'Cinzel Decorative',serif;text-transform:uppercase;letter-spacing:1.2px;
    font-weight:600;
  }
  .verdict.safe{background:rgba(159,255,228,.20);color:var(--mint)}
  .verdict.recommended{background:rgba(255,203,122,.20);color:var(--gold-bright)}
  .verdict.review{background:rgba(181,159,255,.22);color:var(--violet)}
  .verdict.wait{background:rgba(255,142,142,.22);color:var(--ember)}
  .verdict.unknown{background:var(--glass-strong);color:var(--text-3)}

  .upgrade-item{padding:16px 18px;border:1px solid var(--glass-border);border-radius:12px;background:var(--glass-strong);margin:10px 0}
  .upgrade-item .head{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}
  .upgrade-item .name{
    font-family:'Cinzel Decorative',serif;font-weight:600;font-size:15px;
    color:var(--text);letter-spacing:.06em;text-transform:capitalize;
  }
  .upgrade-item .meta{font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--text-3);margin-top:4px}
  .upgrade-item .summary{margin-top:10px;color:var(--text-2);font-size:13px;line-height:1.55;font-family:'Quicksand',sans-serif}
  .upgrade-item .flags{margin-top:8px;display:flex;flex-wrap:wrap;gap:6px}
  .upgrade-item .flag{padding:2px 9px;border-radius:999px;font-family:'JetBrains Mono',monospace;font-size:10px;background:rgba(255,142,142,.15);color:var(--ember);letter-spacing:.4px}
  .upgrade-item a{color:var(--violet);text-decoration:none}
  .upgrade-item a:hover{color:var(--rose)}
</style>
</head><body>
<div class="container">
  <h1>The Spellbook</h1>
  <div class="tech">coven-mail-bridge · localhost:18793</div>

  <div class="tabs">
    <button class="tab active" data-panel="history">History</button>
    <button class="tab" data-panel="send">Send</button>
    <button class="tab" data-panel="debug">Debug</button>
    <button class="tab" data-panel="surveillance">Surveillance</button>
  </div>

  <!-- History -->
  <div class="panel active" id="panel-history">
    <div class="toolbar">
      <button class="btn" onclick="markRead()">Mark all read</button>
      <span id="count" style="margin-left:16px;color:var(--text-2)"></span>
    </div>
    <div id="messages" class="empty">Consulting the book…</div>
  </div>

  <!-- Send -->
  <div class="panel" id="panel-send">
    <div class="card">
      <h2>Send to one familiar</h2>
      <div class="tech-sub">post /api/send/{familiar}</div>
      <label>To</label>
      <select id="send-to">
        <option value="salem">🐈‍⬛ Salem · spellman-manor:18789</option>
        <option value="hilda">☕ Hilda · spellman-manor:18790</option>
        <option value="zelda">📖 Zelda · zeldas-study:18789</option>
        <option value="harvey">🛠 Harvey · harveys-workshop:18789</option>
      </select>
      <label>From</label>
      <input id="send-from" value="sabrina">
      <label>Message</label>
      <textarea id="send-msg" placeholder="Cast a spell, ask a question, request a status check…"></textarea>
      <button class="btn" onclick="sendOne()">Cast</button>
      <span id="send-result" style="margin-left:12px"></span>
    </div>
    <div class="card">
      <h2>Broadcast to the whole coven</h2>
      <div class="tech-sub">post /api/broadcast · all 4 familiars</div>
      <label>From</label>
      <input id="bcast-from" value="sabrina">
      <label>Message</label>
      <textarea id="bcast-msg" placeholder="One message to the whole coven."></textarea>
      <button class="btn" onclick="broadcast()">Broadcast</button>
      <pre id="bcast-result" style="display:none"></pre>
    </div>
  </div>

  <!-- Debug -->
  <div class="panel" id="panel-debug">
    <div class="card">
      <h2>Peer ping</h2>
      <div class="tech-sub">get /api/peer-ping · post /api/selftest</div>
      <button class="btn" onclick="peerPing()">Run peer-ping</button>
      <button class="btn ghost" onclick="selftest()">Broadcast selftest</button>
      <div class="grid" id="ping-grid"></div>
    </div>
    <div class="card">
      <h2>Circuit breakers</h2>
      <div class="tech-sub">get /api/circuits</div>
      <button class="btn ghost" onclick="circuits()">Refresh</button>
      <pre id="circuit-result" style="display:none"></pre>
    </div>
  </div>

  <!-- Surveillance -->
  <div class="panel" id="panel-surveillance">
    <div class="card">
      <h2>Activity feed</h2>
      <div class="tech-sub">get /api/activity · mail · circuits · cron · watchdog</div>
      <div id="activity-feed" class="empty">Watching the linen closet…</div>
    </div>
    <div class="card">
      <h2>Cron jobs</h2>
      <div class="tech-sub">get /api/cron · jobs ping post /api/cron/heartbeat</div>
      <div id="cron-list" class="empty">No cron heartbeats yet — see docs/12-watchdog-cron.md to wire them up.</div>
    </div>
    <div class="card">
      <h2>Watchdogs</h2>
      <div class="tech-sub">get /api/watchdog · post /api/watchdog/heartbeat</div>
      <div id="watchdog-list" class="empty">No watchdog heartbeats yet — see docs/12-watchdog-cron.md.</div>
    </div>
    <div class="card">
      <h2>Available upgrades</h2>
      <div class="tech-sub">get /api/upgrades · docker hub + github releases · cached 1h</div>
      <button class="btn ghost" onclick="loadUpgrades(true)">Refresh now</button>
      <div id="upgrade-list" class="empty" style="margin-top:14px">Looking up newer versions…</div>
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
  if (t.dataset.panel === 'surveillance') refreshSurveillance();
}));

const esc = s => (s||'').replace(/[<>&]/g, c => ({'<':'&lt;','>':'&gt;','&':'&amp;'})[c]);
const fmtTs = ts => {
  if (!ts) return '';
  const d = (ts > 1e12) ? new Date(ts) : new Date(ts * 1000);
  return d.toLocaleTimeString([], {hour:'2-digit',minute:'2-digit',second:'2-digit'});
};

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
  const r = await fetch('/api/send/' + to, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({message:msg, from})});
  const d = await r.json();
  document.getElementById('send-result').innerHTML = r.ok
    ? '<span class="ok-text">✨ cast successfully</span>'
    : '<span class="err-text">✗ ' + esc(d.error || 'failed') + '</span>';
}
async function broadcast() {
  const msg = document.getElementById('bcast-msg').value.trim();
  const from = document.getElementById('bcast-from').value.trim() || 'sabrina';
  if (!msg) return;
  const r = await fetch('/api/broadcast', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({message:msg, from})});
  const d = await r.json();
  const el = document.getElementById('bcast-result'); el.style.display = 'block';
  el.textContent = JSON.stringify(d, null, 2);
}
async function peerPing() {
  const r = await fetch('/api/peer-ping');
  const d = await r.json();
  document.getElementById('ping-grid').innerHTML = Object.entries(d).map(([n,p]) => `
    <div class="ping ${p.ok ? 'ok' : 'fail'}">
      <div class="name">${n}</div>
      <div class="detail">${p.ok ? `alive · ${p.latency_ms}ms` : '✗ ' + esc(p.error)}</div>
    </div>`).join('');
}
async function selftest() {
  const r = await fetch('/api/selftest', {method:'POST'});
  const d = await r.json();
  alert('Self-test dispatched:\n' + JSON.stringify(d, null, 2));
}
async function circuits() {
  const r = await fetch('/api/circuits'); const d = await r.json();
  const el = document.getElementById('circuit-result'); el.style.display = 'block';
  el.textContent = JSON.stringify(d, null, 2);
}

async function refreshSurveillance() {
  loadActivity(); loadCron(); loadWatchdog(); loadUpgrades();
}
async function loadActivity() {
  const r = await fetch('/api/activity?limit=80'); const d = await r.json();
  const el = document.getElementById('activity-feed');
  if (!d.events.length) { el.innerHTML = '<div class="empty">Quiet at the manor.</div>'; return; }
  el.innerHTML = d.events.map(e => {
    const detail = e.kind === 'mail-received' ? `<b>${esc(e.from)}</b> → ${esc(e.to)} · ${esc(e.summary || '')}` :
                   e.kind === 'mail-sent'     ? `→ <b>${esc(e.to)}</b> from ${esc(e.sender||'?')} · ${esc(e.summary||'')}` :
                   e.kind === 'circuit-open'  ? `circuit opened for <b>${esc(e.familiar)}</b> after ${esc(String(e.after_failures))} failures` :
                   e.kind === 'mail-send-error' ? `send to <b>${esc(e.to)}</b> failed: ${esc(e.error)}` :
                   e.kind === 'cron'          ? `<b>${esc(e.name)}</b> · ${esc(e.status)}` :
                   e.kind === 'watchdog'      ? `<b>${esc(e.name)}</b> · ${esc(e.status)}` :
                   esc(JSON.stringify(e));
    return `<div class="feed-row kind-${e.kind}">
      <div class="when">${fmtTs(e.ts)}</div>
      <div class="kind">${esc(e.kind)}</div>
      <div class="what">${detail}</div>
    </div>`;
  }).join('');
}
async function loadCron() {
  const r = await fetch('/api/cron'); const d = await r.json();
  const el = document.getElementById('cron-list');
  if (!d.jobs.length) { el.innerHTML = '<div class="empty">No cron heartbeats yet — see docs/12-watchdog-cron.md.</div>'; return; }
  el.innerHTML = d.jobs.map(j => `
    <div class="feed-row kind-cron">
      <div class="when">${fmtTs(j.last_seen)}</div>
      <div class="kind">${j.stale ? 'stale' : esc(j.status)}</div>
      <div class="what"><b>${esc(j.name)}</b> on ${esc(j.host || '?')} · ${esc(j.schedule || '')} ${j.duration_ms ? `· ${j.duration_ms}ms` : ''}</div>
    </div>`).join('');
}
async function loadWatchdog() {
  const r = await fetch('/api/watchdog'); const d = await r.json();
  const el = document.getElementById('watchdog-list');
  if (!d.watchdogs.length) { el.innerHTML = '<div class="empty">No watchdog heartbeats yet — see docs/12-watchdog-cron.md.</div>'; return; }
  el.innerHTML = d.watchdogs.map(w => `
    <div class="feed-row kind-watchdog">
      <div class="when">${fmtTs(w.last_seen)}</div>
      <div class="kind">${w.stale ? 'stale' : esc(w.status)}</div>
      <div class="what"><b>${esc(w.name)}</b> on ${esc(w.host || '?')}${w.last_output ? ` · ${esc(w.last_output.slice(0,80))}` : ''}</div>
    </div>`).join('');
}
async function loadUpgrades(force) {
  const el = document.getElementById('upgrade-list');
  if (force) el.innerHTML = '<div class="empty">Refreshing…</div>';
  const r = await fetch('/api/upgrades' + (force ? '?force=1' : ''));
  const d = await r.json();
  if (!d.services?.length) { el.innerHTML = '<div class="empty">no upgrade data yet</div>'; return; }
  el.innerHTML = d.services.map(s => {
    const r = s.review || {};
    const release = s.release || {};
    return `<div class="upgrade-item">
      <div class="head">
        <div>
          <div class="name">${esc(s.service)}</div>
          <div class="meta">${esc(s.image)} · latest: ${esc(release.tag_name || s.latest_tag || '?')} · ${release.published_at ? new Date(release.published_at).toLocaleDateString() : ''}</div>
        </div>
        <span class="verdict ${esc(r.verdict || 'unknown')}">${esc(r.verdict || 'unknown')}</span>
      </div>
      ${r.summary ? `<div class="summary">${esc(r.summary)}</div>` : ''}
      ${r.flags?.length ? `<div class="flags">${r.flags.map(f => `<span class="flag">${esc(f)}</span>`).join('')}</div>` : ''}
      ${release.html_url ? `<div class="meta" style="margin-top:8px"><a href="${esc(release.html_url)}" target="_blank" style="color:var(--violet)">read release notes ↗</a></div>` : ''}
      ${s.error ? `<div class="meta" style="margin-top:8px;color:var(--ember)">${esc(s.error)}</div>` : ''}
    </div>`;
  }).join('');
}

loadHistory(); setInterval(loadHistory, 5000);
setInterval(() => { if (document.getElementById('panel-surveillance').classList.contains('active')) refreshSurveillance(); }, 8000);
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
