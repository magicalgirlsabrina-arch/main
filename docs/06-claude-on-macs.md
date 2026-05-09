# 🤖 Claude Code on the Macs (OPTIONAL)
*claude bridge · `:18794` per mac · launchd service · not installed by default*

> **You probably don't need this.** Coven coordination works without
> Claude Code — see [`13-familiar-handbook.md`](13-familiar-handbook.md).
> The familiars talk to the bridge directly over plain HTTP.
>
> Keep this doc as a reference if you ever want to layer Claude on top
> later (e.g. a familiar wants to ask Claude for heavy reasoning).
> The setup script's `--with-claude` flag opts into installing it.

Each familiar host (the 3 Macs) can run Anthropic's Claude Code CLI, and the
dashboard makes it easy for one familiar to "borrow" another's Claude.

## Why this matters

OpenClaw familiars run their own LLM locally (cheap, fast, private). But
sometimes a familiar needs heavier reasoning — e.g. Salem's watchdog spots
a stack trace and wants Claude to triage it. Instead of every familiar
needing its own Anthropic API key, we expose Claude Code on each Mac as
a local HTTP endpoint that other familiars can call.

## How `setup-familiar-host.sh --with-claude` wires it up

If you pass `--with-claude` AND `claude` is in PATH on a Mac, the
setup script installs a tiny **Claude Bridge** at `:18794`:

```
~/.openclaw/workspace/claude-bridge/bridge.py
~/Library/LaunchAgents/ai.openclaw.claude-bridge.plist
```

This is just an HTTP wrapper around `claude -p`. It runs as a launchd agent
(starts at login, restarts on crash).

## API

```http
GET /health
  → {"ok":true,"service":"claude-bridge"}

POST /ask
  Authorization: Bearer <CLAUDE_BRIDGE_TOKEN>     (optional; off by default)
  Content-Type: application/json
  body: {"prompt":"explain this stack trace ..."}

  → JSON output from `claude -p --output-format json`
    {"session_id":"...","total_cost_usd":0.0021,"result":"..."}
```

## Idiomatic usage from a familiar

Add a small tool to any familiar that lets it ask Claude:

```python
import urllib.request, json

def ask_claude_on(host, prompt, port=18794, token=None):
    req = urllib.request.Request(
        f"http://{host}:{port}/ask",
        data=json.dumps({"prompt": prompt}).encode(),
        method="POST",
        headers={
            "Content-Type": "application/json",
            **({"Authorization": f"Bearer {token}"} if token else {}),
        },
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)

# Salem (on the Mac mini) wants Claude on the Mac Pro to triage a log:
result = ask_claude_on("100.79.115.101", "Triage this error: ...")
print(result["result"])
```

## Adding Claude Code hooks for telemetry

Claude Code supports lifecycle hooks. To capture session data centrally,
add to `~/.claude/settings.json` on each Mac:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [{
          "type": "command",
          "command": "curl -s -X POST http://100.106.134.96:18793/api/send/salem -H 'Content-Type: application/json' -d '{\"from\":\"claude-bridge\",\"message\":\"Session started: '$CLAUDE_SESSION_ID'\"}'"
        }]
      }
    ],
    "Stop": [
      {
        "hooks": [{
          "type": "command",
          "command": "curl -s -X POST http://100.106.134.96:18793/api/send/salem -H 'Content-Type: application/json' -d '{\"from\":\"claude-bridge\",\"message\":\"Session ended.\"}'"
        }]
      }
    ]
  }
}
```

This drops a coven-mail message every time a Claude session starts/stops
on that Mac, so the activity shows up in the Spellbook history.

## Authoritative reference impl

Sabrina, if you want to go deeper later, this is the canonical "Claude
Code as a multi-agent observability backend" repo:
https://github.com/disler/claude-code-hooks-multi-agent-observability

It's overkill for now but worth bookmarking when you outgrow the simple
mailbox approach.

## Cost & safety

- Each Claude Code call costs API credits (anthropic.com/console). The
  `total_cost_usd` field comes back in the JSON response — log it to mail.
- The bridge has *no* auth by default. Set `CLAUDE_BRIDGE_TOKEN` in the
  launchd plist to require a bearer token if you ever expose this.
- `claude -p` runs with default tool permissions. To restrict it, change
  the bridge to pass `--allowedTools Read,Grep` (or whatever you need).
