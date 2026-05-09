# 🔔 Alerts — what each themed name means

Every alert has three parts:
- **Themed name** — what shows up in Howling Hat / mail / push
- **Trigger** — the actual Prometheus condition
- **What to do** — the action a familiar (or you) should take

## 🐈‍⬛ Salem's Napping
- **Trigger:** any familiar's gateway has been unreachable for 2 minutes.
- **Severity:** `backfire` (critical)
- **What to do:** SSH to that host, check `tail -50 ~/.openclaw/openclaw.log`. Most often: process crashed, restart it via launchd. If the host itself is asleep, that's the cause — check `pmset -g`.

## 🌑 Trapped in the Linen Closet
- **Trigger:** all 4 familiars unreachable simultaneously.
- **Severity:** `backfire`
- **What to do:** This is almost always Tailscale, not the familiars. Run `tailscale status` on Spellman Manor; reconnect with `tailscale up` if disconnected. If Tailscale is fine, the hub itself may be down.

## 🌙 Westbridge Calm
- **Trigger:** all familiars up for 1 hour.
- **Severity:** `spellbook` (informational)
- **What to do:** Nothing — this is the all-clear signal. Suppressed by default; useful for daily reports.

## 💥 Backfired Spell
- **Trigger:** a familiar returns 5xx > 0.5/sec for 3 minutes.
- **Severity:** `hex` (warning)
- **What to do:** Check OpenClaw logs on that host. Often: model crashed, gateway misconfigured, or downstream service (Anthropic/OpenAI key) failing. Look at `openclaw_request_duration_seconds` to see if requests are *slow* or *fast-failing*.

## ⏳ Time Ball Slowdown
- **Trigger:** p95 request latency > 5 seconds for 5 minutes.
- **Severity:** `hex`
- **What to do:** Familiar is overloaded or the LLM backend is slow. Check Beszel — is the Mac CPU pegged? RAM full? Possibly switch to a smaller model temporarily.

## 🥤 Pop's Soda Fountain Dry
- **Trigger:** sessions are open but token throughput is 0 for 5 min.
- **Severity:** `hex`
- **What to do:** The familiar is "stuck" — sessions exist but it's not generating. Likely a deadlock or model load failure. Check `openclaw_gateway_active_sessions` vs `rate(openclaw_tokens_generated_total)`.

## 💌 Howling Hat Delivery
- **Trigger:** unread coven-mail > 5.
- **Severity:** `spellbook`
- **What to do:** Open the Spellbook (http://localhost:18793). Read the messages. Mark as read.

## 🐈‍⬛ Salem Ate the Spellbook
- **Trigger:** mail send error rate > 0.2/sec for 3 minutes.
- **Severity:** `hex`
- **What to do:** The bridge can't deliver mail. Check `coven_circuit_open` to see which familiar is the problem. Likely the same root cause as "Salem's Napping" for that familiar.

## 🚫 Witch's License Revoked
- **Trigger:** a circuit breaker is open (3+ consecutive send failures).
- **Severity:** `backfire`
- **What to do:** The bridge has stopped trying to send to that familiar. Once you fix the underlying issue, the circuit auto-recovers in 60s. To force-close manually: restart the bridge (`docker compose restart coven-mail`).

## Beszel-only alerts (configure in Beszel UI)

These are *not* in `prometheus/alerts.yml` — Beszel has its own alerts. In
Beszel UI → Settings → Alerts, add:

| Themed name | Condition | Where |
|---|---|---|
| **Hot Flash Hex** | CPU > 90% for 10m | per host |
| **Brain in a Jar** | Memory > 90% for 5m | per host |
| **Pancake House Buffet** | Disk > 90% | per host |
| **Drell's Tantrum** | Load avg > 8 for 15m | per host |

Beszel can send to webhooks, ntfy, Telegram, Slack, etc. — see Beszel docs.

## Routing alerts to your phone

Default: alerts only show in the Howling Hat UI at http://localhost:9093.

To get pushes:

1. Pick a topic name on https://ntfy.sh (e.g. `spellman-manor-alerts`)
2. Install the ntfy app on your phone, subscribe to that topic
3. Edit `alertmanager/config.yml`:
   ```yaml
   receivers:
     - name: 'ntfy-coven'
       webhook_configs:
         - url: 'https://ntfy.sh/spellman-manor-alerts'  # ← your topic
   route:
     receiver: 'ntfy-coven'   # ← change from 'silent-default'
   ```
4. `docker compose restart alertmanager`

## Adding a new alert

1. Add a rule to `prometheus/alerts.yml`. Pattern:
   ```yaml
   - alert: ThemeNameHere
     expr: <your PromQL>
     for: 2m
     labels:
       severity: hex   # spellbook | hex | backfire
       theme: short-tag
     annotations:
       summary: "🎯 ThemeNameHere — short message"
       description: "Longer context with {{ $labels.familiar }} interpolation."
   ```
2. `./scripts/spellbook.sh reload-prometheus` (no restart needed).
3. The alert appears at http://localhost:9090/alerts and routes via Howling Hat.
