# 🔔 Alerts — what each themed name means
*alertmanager · :9093 · routing config in `alertmanager/config.yml`*

Every alert has four parts:
- **Themed name** — what shows up in Howling Hat / mail / push
- **Tech subtitle** — the actual condition (PromQL or Beszel rule)
- **Severity** — `spellbook` (info) / `hex` (warn) / `backfire` (critical)
- **What to do** — the action a familiar (or you) should take

## 🐈‍⬛ Salem's Napping
*`up{job=~"salem|hilda|zelda|harvey"} == 0` for 2m · severity: backfire*

Any familiar's gateway has been unreachable for 2 minutes.

**What to do:** SSH to that host, check `tail -50 ~/.openclaw/openclaw.log`. Most often: process crashed, restart it via launchd. If the host itself is asleep, that's the cause — check `pmset -g`.

## 🌑 Trapped in the Linen Closet
*`count(up{job=~"salem|hilda|zelda|harvey"} == 0) == 4` for 1m · severity: backfire*

All 4 familiars unreachable simultaneously.

**What to do:** Almost always Tailscale, not the familiars. Run `tailscale status` on Spellman Manor; reconnect with `tailscale up` if disconnected. If Tailscale is fine, the hub itself may be down.

## 🌙 Westbridge Calm
*`min_over_time(up{...}[1h]) == 1` for 5m · severity: spellbook*

All familiars up for 1 hour.

**What to do:** Nothing — this is the all-clear. Suppressed by default; useful for daily reports.

## 💥 Backfired Spell
*`rate(openclaw_gateway_requests_total{status=~"5.."}[5m]) > 0.5` for 3m · severity: hex*

A familiar returns 5xx > 0.5/sec for 3 minutes.

**What to do:** Check OpenClaw logs on that host. Often: model crashed, gateway misconfigured, or downstream service (Anthropic/OpenAI key) failing. Look at `openclaw_request_duration_seconds` to see if requests are *slow* or *fast-failing*.

## ⏳ Time Ball Slowdown
*`histogram_quantile(0.95, sum by (familiar, le) (rate(openclaw_request_duration_seconds_bucket[5m]))) > 5` for 5m · severity: hex*

p95 request latency > 5 seconds for 5 minutes.

**What to do:** Familiar is overloaded or the LLM backend is slow. Check Beszel — is the Mac CPU pegged? RAM full? Possibly switch to a smaller model temporarily.

## 🥤 Pop's Soda Fountain Dry
*`rate(openclaw_tokens_generated_total[5m]) == 0 and openclaw_gateway_active_sessions > 0` for 5m · severity: hex*

Sessions are open but token throughput is 0.

**What to do:** The familiar is "stuck" — sessions exist but it's not generating. Likely a deadlock or model load failure. Compare `openclaw_gateway_active_sessions` vs `rate(openclaw_tokens_generated_total)`.

## 💌 Howling Hat Delivery
*`coven_mailbox_unread > 5` for 1m · severity: spellbook*

Unread coven-mail crosses 5.

**What to do:** Open the Spellbook (http://localhost:18793). Read the messages. Mark as read.

## 🐈‍⬛ Salem Ate the Spellbook
*`rate(coven_mail_send_errors_total[5m]) > 0.2` for 3m · severity: hex*

Mail send error rate > 0.2/sec.

**What to do:** The bridge can't deliver mail. Check `coven_circuit_open` to see which familiar is the problem. Likely the same root cause as "Salem's Napping" for that familiar.

## 🚫 Witch's License Revoked
*`coven_circuit_open{familiar!=""} == 1` for 30s · severity: backfire*

A circuit breaker is open (3+ consecutive send failures).

**What to do:** The bridge has stopped trying to send to that familiar. Once you fix the underlying issue, the circuit auto-recovers in 60s. Force-close manually: restart the bridge (`docker compose restart coven-mail`).

---

## Beszel-only alerts (configure in Beszel UI)
*beszel · :8090 → settings → alerts*

These are *not* in `prometheus/alerts.yml` — Beszel has its own alerts. In Beszel UI → Settings → Alerts, add:

| Themed name | Tech condition |
|---|---|
| 🔥 **Hot Flash Hex** | `cpu > 90% for 10m` per host |
| 🧠 **Brain in a Jar** | `memory > 90% for 5m` per host |
| 🥞 **Pancake House Buffet** | `disk > 90%` per host |
| ⚖️ **Drell's Tantrum** | `load avg > 8 for 15m` per host |

Beszel can send to webhooks, ntfy, Telegram, Slack, etc.

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
