# 💌 Coven Mail — how it works

Coven Mail is Sabrina's existing inter-familiar messaging system. The
dashboard adds a friendlier UI on top of it without changing the underlying
infrastructure.

## What was already there

- A Python HTTP server (`mailbox-server.py`) running on the Mac mini at
  `:18792`, managed by launchd.
- An append-only `inbox.jsonl` file at `~/.openclaw/workspace/coven-mailbox/`.
- A `cursor.txt` integer file tracking how many messages have been read.
- `coven-talk.sh` — a CLI for sending mail to other familiars.

## What the dashboard adds

A new service called **The Coven Mail Bridge** (`coven-mail-bridge/server.py`)
that runs in Docker and:

1. Mounts the existing mailbox folder read+write.
2. Exposes a JSON API for the dashboard UI to read mail and send mail.
3. Tracks circuit-breaker state per familiar (so if a familiar is unreachable,
   the bridge stops hammering it for 60s).
4. Serves a small web UI at `:18793/` — **The Spellbook** — with three tabs:
   History, Send Mail, Debug.

The original mailbox server keeps running unchanged. Both can write to
`inbox.jsonl` simultaneously (it's append-only).

## Bridge API reference

All endpoints are unauthenticated within the tailnet. Don't expose `:18793`
to the internet.

### Read endpoints (cheap — pure file reads)

```http
GET /health                    → {"ok":true,"service":"coven-mail-bridge"}

GET /api/unread-count          → {"total":int,"cursor":int,"unread":int}

GET /api/messages?limit=N      → {"messages":[{ts,from,subject,body,read},...],
                                  "total":int,"cursor":int}

GET /metrics                   → Prometheus exposition (counters + circuit state)
```

### Mutating endpoints

```http
POST /api/mark-read
   → advances cursor.txt to len(inbox.jsonl); marks all as read
   → {"ok":true,"cursor":int}

POST /api/send/{familiar}
   body: {"message":"...","from":"sabrina"}
   → POSTs to the familiar's /hooks/agent with bearer auth
   → {"ok":true}  or  {"error":"..."}

POST /api/broadcast
   body: {"message":"...","from":"sabrina"}
   → calls /api/send/{familiar} for all four
   → {"salem":"sent","hilda":"sent","zelda":"sent","harvey":"error: ..."}
```

### Debug endpoints

```http
GET /api/peer-ping
   → calls each familiar's /health endpoint with a 5s timeout
   → {"salem":{"ok":true,"latency_ms":12}, "hilda":{"ok":false,"error":"..."}}

GET /api/circuits
   → state, failure count, last success/failure timestamp per familiar

POST /api/selftest
   → broadcasts "respond with 'alive'" to all familiars
   → useful before debugging — confirms hooks are working
```

## How to use it from a familiar's process

Any familiar can drop mail into Salem's mailbox by POSTing directly to
the existing mailbox server (this is what the registry already supports):

```sh
curl -X POST http://100.106.134.96:18792/mail \
  -H "Authorization: Bearer 4b78943f6520f5ec990e10281cad6ff81ace9b4f90435565" \
  -H "Content-Type: application/json" \
  -d '{"from":"hilda","subject":"status","body":"Cauldron at 92% RAM."}'
```

Or, if a familiar wants to broadcast something to *all* peers without each
of them having to POST individually, it can hit the bridge:

```sh
curl -X POST http://100.106.134.96:18793/api/broadcast \
  -H "Content-Type: application/json" \
  -d '{"from":"zelda","message":"Coven sync — please report your model."}'
```

(The bridge is on the tailnet too, so this works from any familiar.)

## Mail format on disk

```jsonl
{"ts":"2026-05-09T...","from":"zelda","subject":"watchdog","body":"Hey..."}
{"ts":"2026-05-09T...","from":"harvey","subject":"","body":"all clear"}
```

Append-only, never edited. The Spellbook UI just reads + reverses + paginates.

## Mark-as-read semantics

`cursor.txt` holds the count of read messages, 0-N where N = total messages.
"Mark all read" sets cursor to N. There's no per-message read state — only
"line 1..N is read, line N+1..end is unread."

If you want to reset to "all unread" (e.g. for testing), just write `0`:

```sh
echo -n "0" > ~/.openclaw/workspace/coven-mailbox/cursor.txt
```
