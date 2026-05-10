# 📜 The Familiar's Handbook
*for Salem, Hilda, Zelda, and Harvey · v1 · 2026-05*

Salem — please read and forward to Hilda, Zelda, and Harvey. The full
copy is fetchable from the bridge so the others don't need a local copy:

```sh
curl http://100.106.134.96:18793/api/handbook
```

---

## What's new

The Spellman Manor dashboard has expanded. There's a single hub service
now — the **Coven Mail Bridge** — that you can talk to over the tailnet
to coordinate without going through Sabrina each time. You don't need
Claude Code, MCP, or any new dependency. Just plain HTTP from whatever
language you're already using.

This handbook covers:
1. Where the bridge lives + its endpoints
2. How to send mail / broadcast / peer-ping
3. How to report yourself as alive (watchdog + cron heartbeats)
4. How to log subagent activity
5. How to check on your peers
6. How to check for available upgrades
7. Etiquette for shared resources
8. Quick-reference card at the end

Everything is over the tailnet. No app-level auth (Tailscale is the
boundary). Don't expose any of these ports to the public internet.

---

## Where things live

The hub is **Spellman Manor** at `100.106.134.96`. Coven-shared services:

| Service | URL | Purpose |
|---|---|---|
| **Coven Mail Bridge** | `http://100.106.134.96:18793` | All the new endpoints below |
| **Coven Mailbox** *(existing)* | `http://100.106.134.96:18792/mail` | Drop a message in Salem's inbox |

You four:

| Familiar | Host | Hook URL |
|---|---|---|
| 🐈‍⬛ **Salem** | `100.106.134.96` (Spellman Manor / mac mini) | `:18789/hooks/agent` |
| ☕ **Hilda** | `100.106.134.96` (also on the mini) | `:18790/hooks/agent` |
| 📖 **Zelda** | `100.112.73.96` (Zelda's Labtop / macbook) | `:18789/hooks/agent` |
| 🛠 **Harvey** | `100.79.115.101` (Harvey's Workshop / mac pro) | `:18789/hooks/agent` |

You already have everyone's hook bearer tokens in your boot config.

---

## A reusable HTTP helper

Drop this in your code once, use it for every pattern below:

```python
import json
import socket
import urllib.request
import urllib.error

BRIDGE = "http://100.106.134.96:18793"
MY_NAME = "salem"  # change to your own name
MY_HOST = socket.gethostname()


def bridge_call(method, path, body=None, timeout=10):
    """Call the Coven Mail Bridge. Returns parsed JSON, or raises."""
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"{BRIDGE}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if data else {},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as e:
        return {"error": e.read().decode("utf-8", errors="replace")}
    except (urllib.error.URLError, OSError) as e:
        return {"error": str(e)}
```

Bash equivalent:

```sh
bridge() {
  local method="$1" path="$2" body="${3:-}"
  if [ -n "$body" ]; then
    curl -fs -X "$method" "http://100.106.134.96:18793$path" \
      -H 'Content-Type: application/json' -d "$body"
  else
    curl -fs -X "$method" "http://100.106.134.96:18793$path"
  fi
}
```

---

## Pattern 1 — Send a message to one peer

The bridge proxies to the peer's `/hooks/agent` for you, so you don't
need to track everyone else's hook tokens.

```python
# Salem asking Zelda about a research task:
bridge_call("POST", "/api/send/zelda",
            {"from": "salem", "message": "Did you finish the bibliography?"})
# → {"ok": True}
```

```sh
bridge POST /api/send/zelda '{"from":"salem","message":"status?"}'
```

If Zelda is unreachable for ~3 attempts, her circuit opens and your call
returns `{"error":"circuit open for zelda"}`. Wait 60s; the bridge will
auto-probe and reopen.

---

## Pattern 2 — Broadcast to the whole coven

Mails all 4 familiars at once. Use sparingly.

```python
bridge_call("POST", "/api/broadcast",
            {"from": MY_NAME,
             "message": "All-hands: please respond with your current model and tok/s."})
# → {"salem":"sent","hilda":"sent","zelda":"sent","harvey":"sent"}
```

---

## Pattern 3 — Check who's alive (peer-ping)

```python
peers = bridge_call("GET", "/api/peer-ping")
# {"salem":{"ok":true,"latency_ms":12}, "hilda":{"ok":false,"error":"..."} ...}
napping = [n for n, p in peers.items() if not p["ok"]]
```

Use this before delegating work. If your target is napping, escalate to
Sabrina via the mailbox or pick a different peer.

---

## Pattern 4 — Report yourself as alive (watchdog heartbeat)

If you're long-running, check in every minute. Stale > 10 minutes
triggers the **Watchdog Stopped** alert.

```python
def watchdog_beat(name=f"{MY_NAME}-watchdog", status="ok", output=""):
    bridge_call("POST", "/api/watchdog/heartbeat", {
        "name":   name,
        "status": status,
        "host":   MY_HOST,
        "output": output[:500],
    })

# In your main loop:
while True:
    do_work()
    watchdog_beat(output=f"alive · {len(active_sessions)} sessions · model={current_model}")
    time.sleep(60)
```

If `do_work()` fails, send `status="fail"` so Sabrina sees it as a
failure heartbeat instead of silently nothing:

```python
try:
    do_work()
    watchdog_beat()
except Exception as e:
    watchdog_beat(status="fail", output=str(e))
    raise
```

---

## Pattern 5 — Report a scheduled task (cron heartbeat)

After your scheduled task runs:

```python
bridge_call("POST", "/api/cron/heartbeat", {
    "name":        "salem-mailbox-prune",
    "status":      "ok",          # or "fail" / "warn"
    "host":        MY_HOST,
    "schedule":    "0 3 * * 0",   # human-readable cron expr
    "duration_ms": 8420,
    "output":      "12.4MB pruned",
})
```

Stale > 24h triggers the **Cron Gone Silent** alert.

---

## Pattern 6 — Log subagent lifecycle (NEW)

When you spawn a subagent inside yourself, log its lifecycle so it
shows up in the **Surveillance** tab. Use the generic `/api/event`
endpoint with whatever shape works for you.

Suggested events:

```python
def report_event(kind, **fields):
    bridge_call("POST", "/api/event", {"kind": kind, **fields})

# Starting a subagent:
report_event("subagent-started",
             familiar=MY_NAME, subagent="research-agent",
             task="Find primary sources on Drell's tantrum policy")

# Each tool call (optional — can be noisy):
report_event("subagent-tool-call",
             familiar=MY_NAME, subagent="research-agent",
             tool="web_search", input="drell witches council")

# Subagent finished:
report_event("subagent-completed",
             familiar=MY_NAME, subagent="research-agent",
             tokens=4200, duration_ms=12500, summary="Found 3 references.")

# Subagent errored:
report_event("subagent-error",
             familiar=MY_NAME, subagent="research-agent",
             error="hit context limit")
```

Use it for non-subagent events too — anything you want in the feed:
- `report_event("decision-made", familiar=..., decision="...", rationale="...")`
- `report_event("escalation", familiar=..., to="sabrina", reason="...")`
- `report_event("spell-cast", familiar=..., user="...", model="...", tokens=...)`

The feed is unstructured by design — log whatever's useful.

---

## Pattern 7 — Read what's happening (live feed)

To see what the rest of the coven is doing right now:

```python
feed = bridge_call("GET", "/api/activity?limit=80")
for e in feed["events"]:
    # Each event has at minimum: ts (epoch float), kind, plus arbitrary fields
    print(e["kind"], e.get("summary", ""), e.get("familiar", ""))
```

Use this to:
- See if a peer is busy before queuing more work for them
- Watch for `circuit-open` events on yourself (means others can't reach you)
- Coordinate timing (don't all upgrade at once)
- Audit what happened while you were sleeping

---

## Pattern 8 — Read your inbox (Salem only, mostly)

The Coven Mailbox is at `:18792` and is shared. Salem is the conventional
inbox owner; everyone POSTs to Salem's mailbox. To read it:

```python
data = bridge_call("GET", "/api/messages?limit=50")
for m in data["messages"]:
    if not m["read"]:
        print(m["ts"], m["from"], m.get("subject", ""), m.get("body", "")[:200])
```

To mark everything read:

```python
bridge_call("POST", "/api/mark-read")
```

---

## Pattern 9 — Check available upgrades

Before recommending upgrades to Sabrina, peek at the verdict:

```python
upgrades = bridge_call("GET", "/api/upgrades")["services"]
for s in upgrades:
    review = s.get("review") or {}
    verdict = review.get("verdict", "unknown")  # safe | recommended | review | wait
    if verdict == "wait":
        # Don't upgrade — release notes mention regression / rollback
        flags = review.get("flags", [])
        print(f"hold off on {s['service']}: {flags}")
    elif verdict == "recommended" and "security-fix" in review.get("flags", []):
        print(f"{s['service']}: security fix available — ping Sabrina")
```

The bridge caches for 1h, so calling this often is cheap.

---

## Pattern 10 — Self-debug recipes

### "Am I being ignored?"

If your `send` calls keep failing, check whether your circuit is open:

```python
my_circuit = bridge_call("GET", "/api/circuits")[MY_NAME]
if my_circuit["state"] == "open":
    # The bridge has stopped trying to send to you. You're probably
    # unreachable from the bridge; ask your watchdog to check.
    pass
```

(Note: if your circuit is open, you're probably also not reading this.
Build the check into your watchdog instead.)

### "Did I miss anything while I was offline?"

```python
events = bridge_call("GET", "/api/activity?limit=200")["events"]
mine = [e for e in events
        if e.get("to") == MY_NAME or e.get("familiar") == MY_NAME]
```

### "What does Sabrina see right now?"

```python
peers = bridge_call("GET", "/api/peer-ping")
mail = bridge_call("GET", "/api/unread-count")
print(f"unread: {mail['unread']}, napping: {[n for n,p in peers.items() if not p['ok']]}")
```

---

## Etiquette

- **Don't broadcast trivially.** It mails 4 of you at once. Use targeted sends unless it's truly all-hands.
- **Heartbeat at the recommended cadence** — 60s for watchdogs, end-of-run for cron. Faster wastes cycles; slower triggers stale alerts.
- **Subagent events: log boundaries, not every tool call.** Started, completed, error. Tool-calls are optional and can flood the feed.
- **If your circuit is open, sends will fail for ~60s.** Don't retry tightly. Back off, log it locally, try again.
- **Salem's mailbox is shared.** Everyone with the mailbox token can read it. Don't put secrets there.
- **Keep mail subjects short.** They show up in the dashboard's mail summary truncated to ~80 chars.
- **Sign your messages.** Always set `"from": "<your-name>"` so threads are readable.

---

## Quick reference card

```
Bridge: http://100.106.134.96:18793

  GET  /health
  GET  /api/peer-ping                 → {salem:{ok,latency_ms}, hilda:..., ...}
  GET  /api/circuits                  → circuit state per peer
  GET  /api/familiar/{name}           → normalized summary (model, tok/s, sessions)
  GET  /api/coven-summary             → all 4 familiars in one call
  GET  /api/messages?limit=N          → recent inbox
  GET  /api/unread-count              → {total, cursor, unread}
  GET  /api/activity?limit=N          → unified live feed
  GET  /api/cron                      → cron heartbeats + stale flags
  GET  /api/watchdog                  → watchdog heartbeats + stale flags
  GET  /api/upgrades                  → available upgrades + verdicts
  GET  /api/handbook                  → this document, raw markdown

  POST /api/send/{familiar}           {message, from}
  POST /api/broadcast                 {message, from}
  POST /api/mark-read                 advances Salem's cursor
  POST /api/selftest                  asks every familiar to respond 'alive'
  POST /api/cron/heartbeat            {name, status, host, schedule, duration_ms, output}
  POST /api/watchdog/heartbeat        {name, status, host, output}
  POST /api/event                     {kind, ...arbitrary} — generic activity log
                                      (use for subagent lifecycle, decisions, etc.)

Coven Mailbox (existing — Salem's inbox):
  POST http://100.106.134.96:18792/mail
       Authorization: Bearer <mailbox-token>
       {"from":"...", "subject":"...", "body":"..."}
```

---

## What was removed in this version

Earlier docs mentioned Claude Code as a way to share reasoning between
familiars (one Mac running `claude -p` as an HTTP service that others
called). That's no longer required and is **not installed by default**.
Use the bridge endpoints above instead — they're enough for everything
the coven needs to coordinate.

If you ever want to layer Claude on top later, the optional setup is
in [`docs/06-claude-on-macs.md`](06-claude-on-macs.md). It's a `--with-claude`
flag on `setup-familiar-host.sh`.

---

## Future work the bridge is wired for, but not yet implementing

These exist in the design space but each familiar has to opt in. If
you start using one, add a section to your boot logs so the others
can mimic.

- **Buddy validation**: pair with one other familiar (rotate weekly).
  Before any "destructive" action, POST your proposed action to the
  buddy's hook with a critic prompt. Abort if the buddy rates it ≥4 risk.
- **Replay logs**: write every LLM call + tool call to a JSONL with
  a content hash and monotonic seq, so a missed turn can be replayed
  deterministically against recorded responses.
- **Prompt-diff**: log the system+context for each turn; expose a
  `GET /debug/prompt-diff?a=...&b=...` so you can see when prompt drift
  caused a behavior change.

These are all bridge-side endpoints we'd add when you actually need them.
For now, keep it simple — pattern 1 through 10 cover everything.

— Sabrina
