# 🔍 Peer debugging — how familiars debug each other
*coven-mail-bridge endpoints · circuit breakers · claude bridge*

The Coven Mail Bridge ships with debug primitives drawn from production
multi-agent systems (LangSmith, Langfuse, Laminar). Each one has a
specific job; they compose into useful debug workflows.

## The 8 primitives currently shipped

| # | Endpoint | What it does |
|---|---|---|
| 1 | `GET /api/peer-ping` | Hits each familiar's `/health` with a 5s timeout. Returns latency per peer. |
| 2 | `GET /api/circuits` | Per-peer circuit-breaker state (closed / half-open / open). |
| 3 | `POST /api/selftest` | Broadcasts "respond with alive" to all 4 familiars. |
| 4 | `POST /api/send/{f}` | Send a debug request to one familiar. |
| 5 | `POST /api/broadcast` | Send a debug request to all familiars. |
| 6 | `GET /api/messages` | Read the recent coven-mail history (replies show up here). |
| 7 | `POST /api/mark-read` | Reset cursor — useful before debugging to see only new replies. |
| 8 | `GET /metrics` | Prometheus exposition (counters + circuit state for Grafana). |

## Common debug workflows

### "Is the whole coven OK right now?"

Open http://localhost:18793/, click **Debug → Run peer-ping**. Or terminal:

```sh
./scripts/coven-status.sh
```

Output:
```
🩺 Pinging the coven...
  🐈‍⬛ salem    ✨ alive · 12ms
  ☕ hilda    ✨ alive · 8ms
  📖 zelda    ✨ alive · 24ms
  🛠 harvey   ✗ Connection refused
```

### "Get every familiar to report its model and token-count"

```sh
./scripts/coven-broadcast.sh "STATUS — please reply with: model, total tokens this hour, last error if any."
```

Replies arrive in Salem's mailbox over the next ~30s. Open Spellbook
History to read.

### "Harvey is slow — get a triage"

Two options:

**Option A — broadcast triage to peers:**
```sh
./scripts/coven-broadcast.sh "TRIAGE: Harvey p95 at 8s. What would you check first? Reply concise."
```
Hilda, Zelda, Salem will reply with their hypotheses. Compare answers.

**Option B — borrow Harvey's own Claude:**
```sh
curl -X POST http://harveys-big-game.tailXXXX.ts.net:18794/ask \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"Read ~/.openclaw/openclaw.log last 200 lines and tell me what is slow."}'
```
This invokes `claude -p` on Harvey's Mac directly. Costs API credits but
cuts straight to the answer.

### "I want to see what each familiar 'thinks' about a question"

```sh
./scripts/coven-broadcast.sh --from sabrina "If you were going to debug the coven mail backlog, what would you check first?"
```

Three different "perspectives" come back — Hilda's chaotic-but-useful,
Zelda's methodical, Harvey's pragmatic. Salem will say "world domination."

### "A familiar's circuit is OPEN — what do I do?"

```sh
./scripts/coven-status.sh   # see which one
docker compose logs coven-mail | grep <familiar>   # see why
# fix the underlying issue (likely the familiar is down)
# circuit auto-recovers in 60s; force-restart:
docker compose restart coven-mail
```

## What's *not* yet shipped (but designed for)

The research notes outlined 12 primitives total. The 4 not yet in the
bridge — leaving them as documented stubs you can add later:

| Primitive | What it would do |
|---|---|
| **context-dump** | `GET /debug/context/{turn_id}` — return the exact prompt + tools sent for a given turn. Requires familiars to log this. |
| **decision-tail** | `GET /debug/decisions?n=N` — last N tool calls per familiar with rationale. |
| **trace-replay** | `POST /debug/replay` — re-run a recorded turn against logged LLM/tool responses (no live calls). |
| **prompt-diff** | `GET /debug/prompt-diff?a=...&b=...` — compare system+context between two turns. |

These need each familiar to write structured logs in JSONL with a content
hash + monotonic seq. The reference implementation pattern:

```python
# in each familiar's request handler:
log_entry = {
    "seq": next(seq_counter),
    "ts": datetime.now(timezone.utc).isoformat(),
    "turn_id": turn_id,
    "kind": "llm_call",  # or "tool_call" or "agent_message"
    "prompt_hash": hashlib.sha256(prompt.encode()).hexdigest()[:12],
    "input": prompt,
    "output": result,
    "duration_ms": ms,
    "cost_usd": cost,
}
log_jsonl(log_entry)
```

Then the bridge reads the JSONL files (mounted via Tailscale or a shared
volume) and serves the debug endpoints. See
https://github.com/disler/claude-code-hooks-multi-agent-observability
for a worked-out reference impl.

## Buddy validation pattern

For "destructive" actions (file writes, external POSTs, state changes), the
research suggests pairing each familiar with a buddy that validates the
proposed action before it executes.

Pattern, adapted for the coven:
1. Salem about to write a file. Salem POSTs to Hilda's
   `/hooks/agent`: "About to write X to Y. Is this destructive?"
2. Hilda runs a critic prompt (e.g. "rate this 1-5 risk, explain").
3. If Hilda rates ≥4, Salem aborts and mails Sabrina.
4. Pairs: salem↔hilda, zelda↔harvey (rotate weekly).

Implementation: add a `/api/validate` endpoint to each familiar's hook
service. The bridge already has the wiring — `call_familiar_hook(name, msg)`
is enough to start.

## Observability TLDR

- **Cheap, always-on:** Prometheus metrics (`/metrics` on the bridge),
  Grafana dashboards, Beszel for system stats.
- **On-demand:** peer-ping, selftest, broadcast — under 1s each.
- **Heavy:** Claude bridge round-trip (~5–30s, costs API credits).
- **Future:** structured per-turn logs + replay (when you outgrow mail).
